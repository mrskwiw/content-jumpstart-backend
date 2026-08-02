"""
Phase 10 — Multi-Platform Distribution API.

Connect social accounts, schedule posts, publish, and run the due-post worker.
All read/write endpoints are scoped to the authenticated user; `process-due` is
superuser-gated (called by a scheduled worker with an admin token).
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user, require_superuser
from backend.models.distribution import (
    SUPPORTED_PLATFORMS,
    PlatformCredential,
    ScheduledPost,
)
from backend.services.distribution import oauth, orchestrator
from backend.services.runtime_config import resolved_oauth_redirect_base
from backend.utils.auth import create_access_token, decode_token

router = APIRouter(prefix="/api/distribution", tags=["Distribution"])

# Signed OAuth `state` tokens are short-lived — the user has minutes to complete
# the consent screen. They carry the initiating user id + PKCE verifier so the
# (unauthenticated) provider callback can be tied back to a user securely.
_OAUTH_STATE_TTL = timedelta(minutes=15)


# ── Schemas ───────────────────────────────────────────────────────────────────


class CredentialCreate(BaseModel):
    platform: str
    access_token: str
    refresh_token: Optional[str] = None
    account_ref: Optional[str] = None
    display_name: Optional[str] = None
    client_id: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


class CredentialOut(BaseModel):
    id: str
    platform: str
    client_id: Optional[str] = None
    account_ref: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class ScheduleCreate(BaseModel):
    platform: str
    content: str
    scheduled_for: datetime
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    post_id: Optional[str] = None
    media_url: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


class ScheduledPostOut(BaseModel):
    id: str
    platform: str
    content: str
    status: str
    scheduled_for: datetime
    posted_at: Optional[datetime] = None
    platform_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    # Server-computed: whether the worker will still act on this post (pending, or a failed
    # post still under the retry cap AND within the retry window). A failed post with
    # is_active=False has exhausted retries — lets the calendar distinguish "will retry" from
    # "gave up" without reimplementing the retry policy. See Decision #220.
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


def _post_out(sp: ScheduledPost) -> ScheduledPostOut:
    """Serialize a ScheduledPost, stamping the server-computed ``is_active`` (the retry policy
    lives only in the orchestrator)."""
    out = ScheduledPostOut.model_validate(sp)
    out.is_active = orchestrator.scheduled_post_is_active(sp)
    return out


# ── Credentials ───────────────────────────────────────────────────────────────


@router.get("/platforms")
def list_platforms():
    """Platforms the distribution layer supports."""
    return {"platforms": list(SUPPORTED_PLATFORMS)}


@router.post("/credentials", response_model=CredentialOut, status_code=201)
def connect_account(
    body: CredentialCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Prove a manually-entered credential authenticates BEFORE persisting it, so a bad
    # handle / app password is rejected now (400) instead of creating a false "connected"
    # state that only surfaces at publish time. OAuth platforms no-op (already validated by
    # their consent handshake); Bluesky (app-password) does a real createSession round-trip;
    # dry-run resolves to the stub verifier (no network). Unimplemented platforms fail closed.
    from backend.services.distribution.publishers import get_publisher

    check = get_publisher(
        body.platform, access_token=body.access_token, account_ref=body.account_ref
    ).verify()
    if not check.success:
        # A transient/upstream failure (provider timeout, 5xx, rate limit) is NOT the
        # operator's bad input — return 502 so retries/monitoring don't treat an outage as a
        # bad-credential error. Only a definitive rejection maps to 400.
        status = 502 if check.retryable else 400
        raise HTTPException(
            status_code=status, detail=check.error or "Credential verification failed"
        )
    try:
        cred = orchestrator.save_credential(
            db,
            current_user.id,
            body.platform,
            body.access_token,
            client_id=body.client_id,
            refresh_token=body.refresh_token,
            account_ref=body.account_ref,
            display_name=body.display_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return cred


@router.get("/credentials", response_model=List[CredentialOut])
def list_credentials(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(PlatformCredential).filter(PlatformCredential.user_id == current_user.id).all()


@router.delete("/credentials/{credential_id}")
def delete_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cred = (
        db.query(PlatformCredential)
        .filter(
            PlatformCredential.id == credential_id,
            PlatformCredential.user_id == current_user.id,
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(cred)
    db.commit()
    return {"status": "deleted", "id": credential_id}


class CredentialPatch(BaseModel):
    account_ref: Optional[str] = None
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    model_config = ConfigDict(extra="forbid")


@router.patch("/credentials/{credential_id}", response_model=CredentialOut)
def update_credential(
    credential_id: str,
    body: CredentialPatch,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Set the account reference (FB Page id / IG user id / LinkedIn org id),
    display name, or active flag on a connected account."""
    cred = (
        db.query(PlatformCredential)
        .filter(
            PlatformCredential.id == credential_id,
            PlatformCredential.user_id == current_user.id,
        )
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    for field_name in ("account_ref", "display_name", "is_active"):
        value = getattr(body, field_name)
        if value is not None:
            setattr(cred, field_name, value)
    db.commit()
    db.refresh(cred)
    return cred


# ── OAuth connect flow ────────────────────────────────────────────────────────


@router.get("/oauth/status")
def oauth_status():
    """Which platforms have their OAuth app credentials configured in the
    environment (i.e. can be connected right now)."""
    # `all` = platforms connectable via THIS OAuth flow. Exclude the stub and any
    # supported platform that isn't OAuth-based (e.g. Bluesky uses app-password auth and is
    # connected via the manual credential API), so the OAuth connect grid isn't misleading.
    return {
        "configured": oauth.configured_platforms(),
        "all": [p for p in SUPPORTED_PLATFORMS if p != "stub" and p in oauth.PROVIDERS],
    }


@router.get("/oauth/{platform}/start")
def oauth_start(
    platform: str,
    client_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the provider authorize URL to redirect the user to. The signed
    `state` binds this consent to the current user (+ PKCE verifier if required)."""
    if platform not in oauth.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown OAuth platform '{platform}'")
    provider = oauth.PROVIDERS[platform]
    if not provider.is_configured:
        raise HTTPException(
            status_code=400,
            detail=f"{platform} OAuth is not configured on this server "
            f"({provider.client_id_env}/{provider.client_secret_env} unset).",
        )
    # Resolve the callback URL once and PIN it in the signed state, so the exchange
    # leg reuses the identical redirect_uri even if instance_config changes mid-flow
    # (OAuth rejects a mismatch between the authorize and token legs).
    try:
        redirect_uri = oauth.redirect_uri_for(platform, db)
    except oauth.OAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    state_data = {
        "sub": current_user.id,
        "oauth_platform": platform,
        "cid": client_id,
        "ru": redirect_uri,
    }
    code_challenge = None
    if provider.use_pkce:
        pkce = oauth.make_pkce_pair()
        state_data["cv"] = pkce["verifier"]
        code_challenge = pkce["challenge"]
    state = create_access_token(state_data, expires_delta=_OAUTH_STATE_TTL)
    try:
        url = oauth.build_authorize_url(
            platform, state, code_challenge=code_challenge, redirect_uri=redirect_uri
        )
    except oauth.OAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"authorize_url": url}


@router.get("/oauth/{platform}/callback")
def oauth_callback(
    platform: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Provider redirect target. Verifies the signed state, exchanges the code for
    tokens, stores the (encrypted) credential, then bounces back to the UI."""
    path = "/dashboard/settings/connections"
    # Canonical instance UI base (instance_config custom domain when set) resolved
    # DEFENSIVELY — _bounce_base never raises, so the config read gives the right
    # domain when the DB is healthy yet an OAuth-error redirect still succeeds if the
    # read fails (env fallback). Satisfies both robustness and canonical-domain.
    base = _bounce_base(db)
    done = f"{base}{path}" if base else path

    if error:
        return RedirectResponse(f"{done}?error={error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    payload = decode_token(state)
    if not payload or payload.get("oauth_platform") != platform or not payload.get("sub"):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        # Reuse the redirect_uri pinned in the signed state (falls back to db/env for
        # any state issued before pinning existed).
        token = oauth.exchange_code(
            platform,
            code,
            code_verifier=payload.get("cv"),
            redirect_uri=payload.get("ru"),
            db=db,
        )
    except oauth.OAuthError as e:
        return RedirectResponse(f"{done}?error={requests_quote(str(e))}")

    orchestrator.save_credential(
        db,
        payload["sub"],
        platform,
        token["access_token"],
        client_id=payload.get("cid"),
        refresh_token=token.get("refresh_token"),
        token_expires_at=token.get("expires_at"),
        # Don't pass a name here — save_credential defaults it for a NEW credential and
        # preserves an operator-set name on a reconnect/refresh (account_ref likewise).
    )
    return RedirectResponse(f"{done}?connected={platform}")


def _bounce_base(db: Session) -> str:
    """Canonical UI base for post-OAuth redirects, resolved defensively.

    Returns the instance's custom domain (``instance_config``) when available, else
    the env base. NEVER raises — a config-read failure must not break an OAuth-error
    redirect, so any error falls back to the env value. This resolves the tension
    between "use the canonical domain" and "don't add a failing DB read to the error
    path" (BUGS.md Decision #209): canonical when the DB is healthy, robust always.
    """
    try:
        return resolved_oauth_redirect_base(db)
    except Exception:  # noqa: BLE001 - a redirect must never fail on a config read
        return os.getenv("OAUTH_REDIRECT_BASE_URL", "").rstrip("/")


def requests_quote(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


# ── Queue ─────────────────────────────────────────────────────────────────────


@router.post("/schedule", response_model=ScheduledPostOut, status_code=201)
def schedule(
    body: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        sp = orchestrator.schedule_post(
            db,
            current_user.id,
            body.platform,
            body.content,
            body.scheduled_for,
            project_id=body.project_id,
            client_id=body.client_id,
            post_id=body.post_id,
            media_url=body.media_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _post_out(sp)


@router.get("/queue", response_model=List[ScheduledPostOut])
def list_queue(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(ScheduledPost).filter(ScheduledPost.user_id == current_user.id)
    if status:
        q = q.filter(ScheduledPost.status == status)
    if project_id:
        q = q.filter(ScheduledPost.project_id == project_id)
    rows = q.order_by(ScheduledPost.scheduled_for.asc()).limit(200).all()
    return [_post_out(sp) for sp in rows]


@router.post("/publish/{scheduled_post_id}", response_model=ScheduledPostOut)
def publish_now(
    scheduled_post_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sp = (
        db.query(ScheduledPost)
        .filter(
            ScheduledPost.id == scheduled_post_id,
            ScheduledPost.user_id == current_user.id,
        )
        .first()
    )
    if not sp:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if sp.status == "posted":
        raise HTTPException(status_code=409, detail="Already posted")
    return _post_out(orchestrator.publish_now(db, sp))


@router.post("/process-due")
def process_due(
    limit: int = 25,
    db: Session = Depends(get_db),
    current_user=Depends(require_superuser),
):
    """Publish due posts + retry recent failures. Call ~every minute from a
    scheduled worker (Render Cron Job) authenticated as an admin."""
    return orchestrator.process_due(db, limit=min(limit, 100))
