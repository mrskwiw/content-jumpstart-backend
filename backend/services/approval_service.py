"""Post approval workflow operations (COLLAB-01, GAP-UI-03). Access checks are in the router."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models import PostApproval
from backend.models.post_approval import APPROVAL_APPROVED, APPROVAL_PENDING, APPROVAL_REJECTED


class ApprovalError(Exception):
    """An approval operation was invalid (surfaced as 4xx)."""


def get_approval(db: Session, post_id: str, *, for_update: bool = False) -> Optional[PostApproval]:
    q = db.query(PostApproval).filter(PostApproval.post_id == post_id)
    if for_update:
        q = q.with_for_update()  # row lock (Postgres) → serializes submit vs decide
    return q.first()


def _reset_to_pending(approval: PostApproval, submitter_user_id: str) -> None:
    approval.status = APPROVAL_PENDING
    approval.submitted_by_user_id = submitter_user_id
    approval.decided_by_user_id = None
    approval.decided_at = None
    approval.note = None


def _apply_submit(db: Session, approval: PostApproval, submitter_user_id: str) -> PostApproval:
    """Reset an existing (row-locked) approval to pending — UNLESS it's already approved,
    in which case submit is a no-op (never silently un-approve a decided post; a racing
    or duplicate submit can't clobber an approval). Rejected/pending → back to pending,
    so the reject→fix→resubmit flow works."""
    if approval.status != APPROVAL_APPROVED:
        _reset_to_pending(approval, submitter_user_id)
        db.commit()
        db.refresh(approval)
    return approval


def submit_for_approval(db: Session, post_id: str, submitter_user_id: str) -> PostApproval:
    """Submit a post for review (create or reset its approval record to pending).

    Race-safe: the read-modify-write is row-locked (``for_update``) so it can't interleave
    with a concurrent approve/reject. ``post_id`` is unique, so two near-simultaneous
    submits could both see no row and both insert; the loser's ``IntegrityError`` is
    caught and it re-locks + re-applies onto the winner's row instead of 500-ing.
    """
    from sqlalchemy.exc import IntegrityError

    approval = get_approval(db, post_id, for_update=True)
    if approval is not None:
        return _apply_submit(db, approval, submitter_user_id)

    approval = PostApproval(
        post_id=post_id, submitted_by_user_id=submitter_user_id, status=APPROVAL_PENDING
    )
    db.add(approval)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        approval = get_approval(db, post_id, for_update=True)
        if approval is None:  # truly gone (not the expected race) — surface it
            raise
        return _apply_submit(db, approval, submitter_user_id)
    db.refresh(approval)
    return approval


def decide(
    db: Session, post_id: str, decider_user_id: str, approve: bool, note: Optional[str] = None
) -> PostApproval:
    """Approve or reject a post that is awaiting review."""
    approval = get_approval(db, post_id, for_update=True)  # lock → no submit interleave
    if approval is None or approval.status != APPROVAL_PENDING:
        raise ApprovalError("this post is not awaiting approval")
    approval.status = APPROVAL_APPROVED if approve else APPROVAL_REJECTED
    approval.decided_by_user_id = decider_user_id
    approval.decided_at = datetime.now(timezone.utc)
    approval.note = note
    db.commit()
    db.refresh(approval)
    return approval
