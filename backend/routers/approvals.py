"""Post approval-gate endpoints — team content review (COLLAB-01, GAP-UI-03).

Team-scoped through the post's project:
- read the approval state: any member of the post's team;
- submit for approval: a member with write access (editor+; a viewer is read-only);
- approve / reject: a team manager (owner/admin) — the gate.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.middleware.authorization import _check_ownership
from backend.models import Post, User
from backend.services import approval_service, crud, team_service

router = APIRouter()


class ApprovalResponse(BaseModel):
    post_id: str
    status: str
    submitted_by_user_id: str
    decided_by_user_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DecisionRequest(BaseModel):
    note: Optional[str] = None


def _post_and_project(post_id: str, db: Session):
    """Load a live (non-soft-deleted) post + its project, or 404."""
    post = crud.get_post(db, post_id)
    if not post or getattr(post, "is_deleted", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    project = crud.get_project(db, post.project_id)
    if not project or getattr(project, "is_deleted", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post's project not found"
        )
    return post, project


def _require_post_access(post_id: str, db: Session, user: User, *, is_write: bool) -> Post:
    post, project = _post_and_project(post_id, db)
    if not _check_ownership("Project", project, user, db, is_write=is_write):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return post


def _require_post_manager(post_id: str, db: Session, user: User) -> Post:
    post, project = _post_and_project(post_id, db)
    if user.is_superuser:
        return post
    # Legacy team-less project (team_id IS NULL): mirror the authorization layer's
    # creator fallback — the creator is effectively the manager of their own solo
    # content, so they can approve/reject it (otherwise legacy posts strand: submittable
    # via the creator check but never approvable).
    if project.team_id is None:
        if project.user_id == user.id:
            return post
    elif team_service.is_manager(db, user.id, project.team_id):
        return post
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only a team owner or admin can approve or reject",
    )


@router.get("/posts/{post_id}/approval", response_model=Optional[ApprovalResponse])
def get_post_approval(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The post's approval state (null if never submitted). Any team member."""
    _require_post_access(post_id, db, current_user, is_write=False)
    approval = approval_service.get_approval(db, post_id)
    return ApprovalResponse.model_validate(approval) if approval else None


@router.post("/posts/{post_id}/approval/submit", response_model=ApprovalResponse)
def submit_post_for_approval(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a post for team review (editor+; sets it pending)."""
    _require_post_access(post_id, db, current_user, is_write=True)
    approval = approval_service.submit_for_approval(db, post_id, current_user.id)
    return ApprovalResponse.model_validate(approval)


@router.post("/posts/{post_id}/approval/approve", response_model=ApprovalResponse)
def approve_post(
    post_id: str,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a pending post (owner/admin only)."""
    _require_post_manager(post_id, db, current_user)
    try:
        approval = approval_service.decide(db, post_id, current_user.id, True, body.note)
    except approval_service.ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ApprovalResponse.model_validate(approval)


@router.post("/posts/{post_id}/approval/reject", response_model=ApprovalResponse)
def reject_post(
    post_id: str,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a pending post (owner/admin only)."""
    _require_post_manager(post_id, db, current_user)
    try:
        approval = approval_service.decide(db, post_id, current_user.id, False, body.note)
    except approval_service.ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ApprovalResponse.model_validate(approval)
