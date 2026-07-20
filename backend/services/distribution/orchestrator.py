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
from backend.services.distribution.publishers import dry_run_enabled, get_publisher
from backend.services.settings_service import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


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
        cred.access_token = enc_access
        cred.refresh_token = enc_refresh
        cred.account_ref = account_ref
        cred.display_name = display_name
        cred.token_expires_at = token_expires_at
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
            display_name=display_name,
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
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return sp


# ── Publishing ────────────────────────────────────────────────────────────────


def _publish(db: Session, sp: ScheduledPost) -> ScheduledPost:
    """Publish one scheduled post and record the outcome."""
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

    token = decrypt_value(cred.access_token) if cred else ""
    account_ref = cred.account_ref if cred else None
    publisher = get_publisher(sp.platform, token, account_ref)
    result = publisher.publish(sp.content, sp.media_url)

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
                content_hash=hashlib.sha256(sp.content.encode("utf-8")).hexdigest(),
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

    # Retry recent failures under the retry cap.
    cutoff = now - timedelta(hours=24)
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
