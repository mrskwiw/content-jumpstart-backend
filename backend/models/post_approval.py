"""Post approval workflow — team content review gate (COLLAB-01, GAP-UI-03).

A PostApproval is the review state of a post: a member submits it for approval, and a
team manager (owner/admin) approves or rejects it. One approval record per post
(``post_id`` unique); resubmitting updates the same row back to pending. Access is
team-scoped in the router. Cascades with the post so a deleted post/project can't strand
an approval row.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from backend.database import Base

APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"


class PostApproval(Base):
    """The review/approval state of a single post."""

    __tablename__ = "post_approvals"

    id = Column(String, primary_key=True, default=lambda: f"pa-{uuid.uuid4().hex[:12]}")
    post_id = Column(
        String,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String, nullable=False, default=APPROVAL_PENDING)  # pending|approved|rejected
    submitted_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    decided_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)  # optional reviewer note (e.g. rejection reason)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    post = relationship(
        "Post", backref=backref("approval", uselist=False, cascade="all, delete-orphan")
    )
