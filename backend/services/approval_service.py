"""Post approval workflow operations (COLLAB-01, GAP-UI-03). Access checks are in the router."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models import PostApproval
from backend.models.post_approval import APPROVAL_APPROVED, APPROVAL_PENDING, APPROVAL_REJECTED


class ApprovalError(Exception):
    """An approval operation was invalid (surfaced as 4xx)."""


def get_approval(db: Session, post_id: str) -> Optional[PostApproval]:
    return db.query(PostApproval).filter(PostApproval.post_id == post_id).first()


def _reset_to_pending(approval: PostApproval, submitter_user_id: str) -> None:
    approval.status = APPROVAL_PENDING
    approval.submitted_by_user_id = submitter_user_id
    approval.decided_by_user_id = None
    approval.decided_at = None
    approval.note = None


def submit_for_approval(db: Session, post_id: str, submitter_user_id: str) -> PostApproval:
    """Submit a post for review (create or reset its approval record to pending).

    Conflict-safe: ``post_id`` is unique, so two near-simultaneous submits could both see
    no row and both insert. The loser's ``IntegrityError`` is caught — we re-fetch the
    row the winner created and reset it to pending, so a duplicate submit returns a
    stable result instead of a 500.
    """
    from sqlalchemy.exc import IntegrityError

    approval = get_approval(db, post_id)
    if approval is not None:
        _reset_to_pending(approval, submitter_user_id)
        db.commit()
        db.refresh(approval)
        return approval

    approval = PostApproval(
        post_id=post_id, submitted_by_user_id=submitter_user_id, status=APPROVAL_PENDING
    )
    db.add(approval)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        approval = get_approval(db, post_id)
        if approval is None:  # truly gone (not the expected race) — surface it
            raise
        _reset_to_pending(approval, submitter_user_id)
        db.commit()
    db.refresh(approval)
    return approval


def decide(
    db: Session, post_id: str, decider_user_id: str, approve: bool, note: Optional[str] = None
) -> PostApproval:
    """Approve or reject a post that is awaiting review."""
    approval = get_approval(db, post_id)
    if approval is None or approval.status != APPROVAL_PENDING:
        raise ApprovalError("this post is not awaiting approval")
    approval.status = APPROVAL_APPROVED if approve else APPROVAL_REJECTED
    approval.decided_by_user_id = decider_user_id
    approval.decided_at = datetime.now(timezone.utc)
    approval.note = note
    db.commit()
    db.refresh(approval)
    return approval
