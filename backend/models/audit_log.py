"""Audit log — immutable record of all CRUD operations for compliance."""

import uuid
from sqlalchemy import Column, DateTime, JSON, String, Text
from sqlalchemy.sql import func

from backend.database import Base


class AuditLog(Base):
    """Immutable compliance record for all create/update/delete operations.

    Written after each successful mutating API call. Never modified after creation.
    Field naming: resource_name stores display-only labels (no raw PII).
    """

    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=lambda: f"al-{uuid.uuid4().hex[:12]}")
    # Denormalised user fields — preserved even after account deletion
    user_id = Column(String, nullable=True, index=True)
    user_email = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    # Action description
    action = Column(String, nullable=False)  # e.g. "Created client"
    action_type = Column(String, nullable=False)  # create|update|delete|export|security|system
    # Affected resource
    resource_type = Column(String, nullable=False)  # client|project|post|deliverable|brief
    resource_id = Column(String, nullable=True, index=True)
    resource_name = Column(String, nullable=True)  # display label only — no sensitive PII
    # Context
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    status = Column(String, nullable=False, default="success")  # success|failed|warning
    extra_metadata = Column(JSON, nullable=True)  # e.g. {"before": {...}, "after": {...}}
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
