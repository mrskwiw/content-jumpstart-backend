"""
Distribution orchestrator (Phase 10).

Owns the schedule → publish → track lifecycle. Publishing is driven by
`process_due()` (a DB-polling worker meant to be called every minute by a Render
Cron Job hitting the protected /api/distribution/process-due endpoint) — chosen
over an in-process APScheduler because the app runs on ephemeral, potentially
multi-worker Render instances where an in-process scheduler would double-fire.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.distribution import (
    SUPPORTED_PLATFORMS,
    PlatformCredential,
    PostedContent,
    ScheduledPost,
)
from backend.services.distribution.oauth import ensure_fresh_token
from backend.services.distribution.publishers import dry_run_enabled, get_publisher
from backend.services.platform_compliance import check_compliance
from backend.services.settings_service import encrypt_value
from backend.services.tracking import tag_urls_in_text
from src.models.client_brief import Platform

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _utm_tagging_enabled() -> bool:
    """Whether published links get UTM attribution params (opt-in, default off).

    Off by default so enabling it is an explicit per-instance choice — it rewrites
    the URLs in a user's post, which should never happen silently.
    """
    return os.getenv("DISTRIBUTION_UTM_TAGGING", "").strip().lower() in ("1", "true", "yes")


def _publishable_content(sp: ScheduledPost) -> str:
    """The exact text that will be sent to the platform (UTM-tagged when enabled)."""
    if not _utm_tagging_enabled():
        return sp.content
    return tag_urls_in_text(
        sp.content,
        source=sp.platform,
        campaign=(sp.project_id or sp.id),
        medium="social",
    )


def _gate_compliance(platform: str, content: str) -> None:
    """Reject content the platform API would hard-reject, at schedule time.

    Uses the API-rejection-only compliance check (char ceiling + hashtag over-cap;
    word counts are advisory), so a deliberately short scheduled post is allowed but
    an oversized one (e.g. an X post past 280 chars) fails fast with a 400 instead of
    a silent worker failure at publish time. Platforms without a compliance spec
    (instagram/tiktok/youtube/stub) are skipped — there is nothing to check.

    Empty content is always rejected: every publisher in this codebase sends a
    text-only request (LinkedIn is a UGC text post; the rest are stub/not-implemented),
    so there is no media-only path a blank caption could be valid for. A per-platform
    media-only exemption belongs with the media-capable publisher that introduces it
    (BUGS.md Decision #205).
    """
    try:
        plat = Platform(platform)
    except ValueError:
        return  # no length/hashtag spec for this platform — nothing to gate
    report = check_compliance(content, plat, api_only=True)
    if not report.publishable:
        raise ValueError(f"Content fails {platform} limits: {'; '.join(report.hard)}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Credentials ───────────────────────────────────────────────────────────────


def save_credential(
    db: Session,
    user_id: str,
    platform: str,
    access_token: str,
    *,
    client_id: Optional[str] = None,
    refresh_token: Optional[str] = None,
    account_ref: Optional[str] = None,
    display_name: Optional[str] = None,
    token_expires_at: Optional[datetime] = None,
) -> PlatformCredential:
    """Create/replace a connected account (tokens stored Fernet-encrypted)."""
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")

    cred = (
        db.query(PlatformCredential)
        .filter(
            PlatformCredential.user_id == user_id,
            PlatformCredential.client_id == client_id,
            PlatformCredential.platform == platform,
        )
        .first()
    )
    enc_access = encrypt_value(access_token)
    enc_refresh = encrypt_value(refresh_token) if refresh_token else None
    if cred:
        # Refresh/reconnect: rotate tokens + reactivate, but PRESERVE operator-managed
        # metadata unless a new value is explicitly supplied. The OAuth callback carries no
        # account_ref and only a generic display_name, so overwriting here would clear the
        # Facebook/Instagram account_ref publishers need and clobber an operator-set name.
        cred.access_token = enc_access
        # Preserve the existing refresh token when the reconnect response omits one — many
        # providers only issue a refresh token on first consent, so overwriting with None
        # would strand the credential once the access token expires (ensure_fresh_token
        # could no longer renew it).
        if enc_refresh is not None:
            cred.refresh_token = enc_refresh
        if account_ref is not None:
            cred.account_ref = account_ref
        if display_name is not None:
            cred.display_name = display_name
        # The expiry must describe the NEW access token. When the reconnect response omits
        # one we can't know its lifetime, so mark it already-due: ensure_fresh_token then
        # refreshes it on the NEXT use (via the preserved refresh token), learning the real
        # expiry before the token is relied on. This beats every guess — None (treated as
        # non-expiring → stranded), the stale prior deadline (suppressed refresh), and a
        # synthetic future TTL (can outlive a shorter real token). A rare provider that also
        # omits expiry on refresh degrades to a refresh-per-use (an extra call, never a
        # failure). See BUGS.md Decision #228.
        cred.token_expires_at = (
            token_expires_at if token_expires_at is not None else datetime.now(timezone.utc)
        )
        cred.is_active = True
    else:
        cred = PlatformCredential(
            id=_uuid(),
            user_id=user_id,
            client_id=client_id,
            platform=platform,
            access_token=enc_access,
            refresh_token=enc_refresh,
            account_ref=account_ref,
            display_name=display_name or f"{platform} account",
            token_expires_at=token_expires_at,
            is_active=True,
        )
        db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


def _load_credential(
    db: Session, user_id: str, platform: str, client_id: Optional[str]
) -> Optional[PlatformCredential]:
    """Prefer a client-scoped credential, then fall back to a user-level one."""
    q = db.query(PlatformCredential).filter(
        PlatformCredential.user_id == user_id,
        PlatformCredential.platform == platform,
        PlatformCredential.is_active.is_(True),
    )
    if client_id:
        cred = q.filter(PlatformCredential.client_id == client_id).first()
        if cred:
            return cred
    return q.filter(PlatformCredential.client_id.is_(None)).first()


# ── Scheduling ────────────────────────────────────────────────────────────────


def schedule_post(
    db: Session,
    user_id: str,
    platform: str,
    content: str,
    scheduled_for: datetime,
    *,
    project_id: Optional[str] = None,
    client_id: Optional[str] = None,
    post_id: Optional[str] = None,
    media_url: Optional[str] = None,
) -> ScheduledPost:
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}")
    # Validate a media-asset reference up front so a bad/unowned id fails fast (400)
    # at schedule time, not silently as a delayed worker failure.
    _owned_media_asset(db, user_id, media_url)
    sp = ScheduledPost(
        id=_uuid(),
        user_id=user_id,
        project_id=project_id,
        client_id=client_id,
        post_id=post_id,
        platform=platform,
        content=content,
        media_url=media_url,
        scheduled_for=scheduled_for,
        status="pending",
        retry_count=0,
    )
    # Gate the EXACT payload that will be published — the UTM-tagged content when
    # tagging is enabled — so a post that passes here also passes at publish time.
    # Otherwise tagging could push a borderline post over the char limit and turn a
    # valid scheduled post into a silent publish-time failure.
    _gate_compliance(platform, _publishable_content(sp))
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return sp


# ── Publishing ────────────────────────────────────────────────────────────────


_MEDIA_REF_PREFIX = "media-asset://"


def _owned_media_asset(db: Session, user_id: str, media_url: Optional[str]):
    """Look up the owned MediaAsset a `media-asset://<id>` media_url refers to.

    Returns None for a plain (non-reference) media_url. Raises ValueError if the
    reference points at an asset that is missing or not owned by `user_id`."""
    if not media_url or not media_url.startswith(_MEDIA_REF_PREFIX):
        return None
    from backend.models.media import MediaAsset

    asset_id = media_url[len(_MEDIA_REF_PREFIX) :]
    asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == asset_id, MediaAsset.user_id == user_id)
        .first()
    )
    if asset is None:
        raise ValueError(f"Media asset {asset_id} not found or not owned by you")
    return asset


def _resolve_media_ref(db: Session, sp: ScheduledPost) -> Optional[str]:
    """Resolve a `media-asset://<id>` media_url to a FRESH signed storage URL at
    publish time (never stale). A plain media_url passes through unchanged; an
    absolute asset URL is passed through, a storage key is signed."""
    asset = _owned_media_asset(db, sp.user_id, sp.media_url)
    if asset is None:
        return sp.media_url
    from backend.services.media.storage import StorageError, signed_url_for

    try:
        return signed_url_for(asset.url)
    except StorageError as e:
        raise ValueError(f"Storage unavailable to sign media asset: {e}")


def _publish(db: Session, sp: ScheduledPost) -> ScheduledPost:
    """Publish one scheduled post and record the outcome."""
    # Resolve the exact payload first (UTM tagging adds characters), then gate THAT —
    # a tweet near 280 chars could tip over once links are tagged, so the gate must
    # see what is actually sent, not the authored text.
    content_to_publish = _publishable_content(sp)

    # Compliance gate — this is the single choke point every publish path flows
    # through (worker process_due + publish_now), so it catches content that never
    # went through schedule_post's gate. A post the platform API would reject is
    # failed here instead of making a doomed API call.
    try:
        _gate_compliance(sp.platform, content_to_publish)
    except ValueError as e:
        sp.status = "failed"
        sp.error_message = str(e)
        sp.retry_count += 1
        db.commit()
        return sp

    sp.status = "posting"
    db.commit()

    cred = _load_credential(db, sp.user_id, sp.platform, sp.client_id)
    can_dry_run = sp.platform == "stub" or dry_run_enabled()
    if cred is None and not can_dry_run:
        sp.status = "failed"
        sp.error_message = f"No active credential connected for '{sp.platform}'"
        sp.retry_count += 1
        db.commit()
        return sp

    # Refresh the token first if it's expiring and a refresh path exists; falls
    # back to the current token otherwise (the live call surfaces any auth error).
    token = ensure_fresh_token(db, cred) if cred else ""
    account_ref = cred.account_ref if cred else None
    publisher = get_publisher(sp.platform, token, account_ref)

    # Resolve a durable media reference to a FRESH signed URL at publish time — a
    # scheduled post may fire hours after it was queued, long after any URL captured
    # at schedule time would have expired.
    try:
        media_url = _resolve_media_ref(db, sp)
    except ValueError as e:
        sp.status = "failed"
        sp.error_message = str(e)
        sp.retry_count += 1
        db.commit()
        return sp

    result = publisher.publish(content_to_publish, media_url)

    if result.success:
        sp.status = "posted"
        sp.posted_at = _now()
        sp.platform_post_id = result.platform_post_id
        sp.platform_url = result.platform_url
        sp.error_message = None
        db.add(
            PostedContent(
                id=_uuid(),
                user_id=sp.user_id,
                scheduled_post_id=sp.id,
                platform=sp.platform,
                platform_post_id=result.platform_post_id or "",
                platform_url=result.platform_url,
                content_hash=hashlib.sha256(content_to_publish.encode("utf-8")).hexdigest(),
                posted_at=_now(),
            )
        )
    else:
        sp.status = "failed"
        sp.error_message = result.error
        sp.retry_count += 1
    db.commit()
    db.refresh(sp)
    return sp


def publish_now(db: Session, sp: ScheduledPost) -> ScheduledPost:
    """Immediately publish a scheduled post (ownership enforced by the router)."""
    return _publish(db, sp)


def _due_query(db: Session, statuses):
    q = db.query(ScheduledPost).filter(ScheduledPost.status.in_(statuses))
    # Row-lock on Postgres so concurrent cron ticks don't double-publish.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    return q


#: How long after its scheduled time a failed post remains eligible for retry.
RETRY_WINDOW = timedelta(hours=24)


def scheduled_post_is_active(sp: ScheduledPost, now: Optional[datetime] = None) -> bool:
    """Whether the worker will still act on this scheduled post (Decision #220).

    The single source of truth for the retry policy so the frontend/calendar can distinguish
    "will still be attempted" from "gave up" WITHOUT reimplementing it. Kept exactly in sync
    with ``process_due``'s selection:
      * ``pending``  → active (awaiting its scheduled time)
      * ``posted``   → inactive (terminal success)
      * ``failed``   → active only if still retryable — under the retry cap AND within the
        retry window (``scheduled_for >= now - RETRY_WINDOW``); otherwise exhausted.
      * anything else → inactive (terminal/unknown).

    No ``next_attempt_at`` is exposed: the worker retries on its next tick with no per-post
    backoff schedule, so any such timestamp would be fabricated/misleading.
    """
    if sp.status == "pending":
        return True
    if sp.status == "failed":
        now = now or _now()
        scheduled_for = sp.scheduled_for
        if scheduled_for is None:
            return False
        if scheduled_for.tzinfo is None:  # normalize a naive (e.g. SQLite) timestamp to UTC
            scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
        within_window = scheduled_for >= now - RETRY_WINDOW
        return sp.retry_count < MAX_RETRIES and within_window
    return False


def process_due(db: Session, limit: int = 25) -> dict:
    """Publish pending posts whose time has come, and retry recent failures.

    Intended to be called ~every minute by a scheduled worker. Returns a summary.
    """
    now = _now()
    summary = {"published": 0, "failed": 0, "retried": 0, "processed": 0}

    pending: List[ScheduledPost] = (
        _due_query(db, ["pending"])
        .filter(ScheduledPost.scheduled_for <= now)
        .order_by(ScheduledPost.scheduled_for.asc())
        .limit(limit)
        .all()
    )
    for sp in pending:
        _publish(db, sp)
        summary["processed"] += 1
        summary["published" if sp.status == "posted" else "failed"] += 1

    # Retry recent failures under the retry cap (same window as scheduled_post_is_active).
    cutoff = now - RETRY_WINDOW
    failed: List[ScheduledPost] = (
        _due_query(db, ["failed"])
        .filter(ScheduledPost.retry_count < MAX_RETRIES, ScheduledPost.scheduled_for >= cutoff)
        .order_by(ScheduledPost.scheduled_for.asc())
        .limit(limit)
        .all()
    )
    for sp in failed:
        before = sp.status
        _publish(db, sp)
        summary["processed"] += 1
        summary["retried"] += 1
        if sp.status == "posted" and before == "failed":
            summary["published"] += 1
    return summary
