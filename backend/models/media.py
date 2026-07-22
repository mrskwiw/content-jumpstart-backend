"""
Phase 12 — Media Generation models.

A `MediaJob` is one stage of work (a single provider call — TTS, avatar render,
clip gen, master, lip-sync, …). A pipeline (talking-head / cinematic / audio) is
an ordered chain of jobs linked by `parent_job_id`; each finished stage produces
a `MediaAsset` that feeds the next. Renders are long-running, so jobs are async:
`queued → processing → done|failed`, advanced by webhook or the poll worker.

See docs/explore-media-generation.md + docs/explore-audio-operations.md.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from backend.database import Base

# Job lifecycle states.
JOB_STATUSES = (
    "queued",  # ready to submit to its provider
    "processing",  # submitted; awaiting async completion (poll/webhook)
    "awaiting_dependency",  # a later pipeline stage; unblocks when its parent finishes
    "done",
    "failed",
    "canceled",
)


class MediaJob(Base):
    """One provider call in a media pipeline (or a standalone single op)."""

    __tablename__ = "media_jobs"
    __table_args__ = ({"extend_existing": True},)

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)

    # Pipeline this stage belongs to (talking_head | cinematic | audio_only | single).
    pipeline = Column(String, nullable=True)
    stage_index = Column(Integer, nullable=False, default=0)
    # Self-referential chain (plain String, not FK, to avoid create-order cycles).
    parent_job_id = Column(String, nullable=True, index=True)

    kind = Column(String, nullable=False)  # MediaKind value
    provider = Column(String, nullable=False)  # provider name (stub in dry-run)
    status = Column(String, nullable=False, default="queued", index=True)
    external_id = Column(String, nullable=True, index=True)  # provider job id (async)

    input_json = Column(Text, nullable=True)  # JSON spec for the provider
    output_asset_id = Column(String, nullable=True)  # MediaAsset produced (plain str)
    cost_cents = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MediaAsset(Base):
    """A produced audio/video artifact (a stage output or the final deliverable)."""

    __tablename__ = "media_assets"
    __table_args__ = ({"extend_existing": True},)

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("media_jobs.id"), nullable=False, index=True)
    kind = Column(String, nullable=False)  # audio | clip | video | final
    url = Column(String, nullable=False)  # location (stub URL in dry-run)
    duration_s = Column(Integer, nullable=True)
    mime = Column(String, nullable=True)
    bytes = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
