"""Post comments — team review feedback (COLLAB-01, GAP-UI-03).

A Comment is a note a team member leaves on a Post for review/collaboration. Access is
team-scoped through the post's project (the same team that owns the post sees + adds
comments); a comment can be deleted by its author or a team manager (owner/admin).
Kept minimal: comments belong to a post and carry the author + body + timestamp.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from backend.database import Base


class Comment(Base):
    """A team member's comment on a post."""

    __tablename__ = "comments"

    id = Column(String, primary_key=True, default=lambda: f"cmt-{uuid.uuid4().hex[:12]}")
    post_id = Column(String, ForeignKey("posts.id"), nullable=False, index=True)
    author_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
