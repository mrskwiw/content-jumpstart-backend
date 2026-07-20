"""
Phase 10 — Multi-Platform Distribution API.

Connect social accounts, schedule posts, publish, and run the due-post worker.
All read/write endpoints are scoped to the authenticated user; `process-due` is
superuser-gated (called by a scheduled worker with an admin token).
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user, require_superuser
from backend.models.distribution import (
    SUPPORTED_PLATFORMS,
    PlatformCredential,
    ScheduledPost,
)
from backend.services.distribution import orchestrator

router = APIRouter(prefix="/api/distribution", tags=["Distribution"])


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
