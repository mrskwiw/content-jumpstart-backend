"""Deletion audit log — immutable record of client data erasure events for GDPR/CCPA compliance."""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from backend.database import Base


class DeletionAuditLog(Base):
    """Immutable record written before every hard-delete of a client.

    Written in the same transaction as the delete so it either commits with
    the deletion or rolls back with it. Never modified after creation.
    """

    __tablename__ = "deletion_audit_log"

    id = Column(String, primary_key=True)
    deleted_by_user_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)  # always "client" for now
    resource_id = Column(String, nullable=False, index=True)
    resource_name = Column(String, nullable=True)  # display name only — no PII stored
    deletion_type = Column(String, nullable=False)  # "hard" | "soft"
    deleted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    projects_deleted = Column(Integer, nullable=True)
    records_deleted = Column(Integer, nullable=True)  # approximate total cascaded rows
