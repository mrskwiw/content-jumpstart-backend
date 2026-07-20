"""
Phase 10 — Multi-Platform Distribution models.

Persists connected platform accounts (encrypted tokens), the scheduled-post
queue, and a record of what was actually published. Adapted from the original
SQLite plan (docs/archive/planning/PHASE_10_DISTRIBUTION_PLAN.md) to the current
Postgres/SQLAlchemy + per-user multi-tenant model.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from backend.database import Base

# Platforms the distribution layer knows about.
SUPPORTED_PLATFORMS = (
    "linkedin",
    "twitter",
    "facebook",
    "instagram",
    "tiktok",
    "youtube",
    "stub",  # dry-run / demo target — never touches a real network
)


class PlatformCredential(Base):
    """A connected social account for a user (optionally scoped to a client)."""

    __tablename__ = "platform_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", "platform", name="uq_platform_credential"),
        {"extend_existing": True},
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=True, index=True)
    platform = Column(String, nullable=False)
    # Fernet-encrypted at the service layer; never store plaintext tokens.
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Facebook Page id / Instagram business account id / LinkedIn org id, etc.
    account_ref = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ScheduledPost(Base):
    """A post queued for publishing to one platform (the post_queue)."""

    __tablename__ = "scheduled_posts"
    __table_args__ = ({"extend_existing": True},)

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=True, index=True)
    post_id = Column(String, ForeignKey("posts.id"), nullable=True)
    platform = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    media_url = Column(String, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    # pending | posting | posted | failed | canceled
    status = Column(String, nullable=False, default="pending", index=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    platform_post_id = Column(String, nullable=True)
    platform_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PostedContent(Base):
    """An immutable record of a successful publish (for analytics + dedup)."""

    __tablename__ = "posted_content"
    __table_args__ = ({"extend_existing": True},)

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    scheduled_post_id = Column(String, ForeignKey("scheduled_posts.id"), nullable=False, index=True)
    platform = Column(String, nullable=False)
    platform_post_id = Column(String, nullable=False)
    platform_url = Column(String, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    posted_at = Column(DateTime(timezone=True), server_default=func.now())
