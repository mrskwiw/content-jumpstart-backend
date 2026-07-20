"""
Phase 11 — Multi-Platform Analytics models.

Stores per-post engagement metrics collected from platforms. A plain Postgres
table with indexes (the plan called for a TimescaleDB hypertable; standard
Supabase has no TimescaleDB, so we use a regular time-indexed table — partition
later if volume warrants). Metrics hang off Phase 10's `posted_content`.
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from backend.database import Base


class PostMetric(Base):
    """One day's engagement snapshot for a published post on one platform."""

    __tablename__ = "post_metrics"
    __table_args__ = (
        UniqueConstraint("posted_content_id", "metric_date", name="uq_post_metric_day"),
        {"extend_existing": True},
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    posted_content_id = Column(String, ForeignKey("posted_content.id"), nullable=True, index=True)
    scheduled_post_id = Column(String, ForeignKey("scheduled_posts.id"), nullable=True)
    platform = Column(String, nullable=False, index=True)
    template_name = Column(String, nullable=True)
    metric_date = Column(Date, nullable=False, index=True)
    likes = Column(Integer, nullable=False, default=0)
    comments = Column(Integer, nullable=False, default=0)
    shares = Column(Integer, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    reach = Column(Integer, nullable=False, default=0)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
