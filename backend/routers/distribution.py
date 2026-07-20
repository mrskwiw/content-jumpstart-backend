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
    model_config = ConfigDict(from_attributes=True)


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
    return {
        "configured": oauth.configured_platforms(),
        "all": [p for p in SUPPORTED_PLATFORMS if p != "stub"],
    }


@router.get("/oauth/{platform}/start")
def oauth_start(
    platform: str,
    client_id: Optional[str] = None,
    current_user=Depends(get_current_user),
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
    state_data = {"sub": current_user.id, "oauth_platform": platform, "cid": client_id}
    code_challenge = None
    if provider.use_pkce:
        pkce = oauth.make_pkce_pair()
        state_data["cv"] = pkce["verifier"]
        code_challenge = pkce["challenge"]
    state = create_access_token(state_data, expires_delta=_OAUTH_STATE_TTL)
    try:
        url = oauth.build_authorize_url(platform, state, code_challenge=code_challenge)
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
    frontend = os.getenv("OAUTH_REDIRECT_BASE_URL", "").rstrip("/")
    path = "/dashboard/settings/connections"
    done = f"{frontend}{path}" if frontend else path

    if error:
        return RedirectResponse(f"{done}?error={error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    payload = decode_token(state)
    if not payload or payload.get("oauth_platform") != platform or not payload.get("sub"):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        token = oauth.exchange_code(platform, code, code_verifier=payload.get("cv"))
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
        display_name=f"{platform} account",
    )
    return RedirectResponse(f"{done}?connected={platform}")


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
    return sp


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
    return q.order_by(ScheduledPost.scheduled_for.asc()).limit(200).all()


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
    return orchestrator.publish_now(db, sp)


@router.post("/process-due")
def process_due(
    limit: int = 25,
    db: Session = Depends(get_db),
    current_user=Depends(require_superuser),
):
    """Publish due posts + retry recent failures. Call ~every minute from a
    scheduled worker (Render Cron Job) authenticated as an admin."""
    return orchestrator.process_due(db, limit=min(limit, 100))
