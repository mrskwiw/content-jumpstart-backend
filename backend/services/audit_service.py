"""Audit logging service — write immutable AuditLog entries after successful operations."""

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from backend.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For when behind a proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def log_action(
    db: Session,
    *,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None,
    action: str,
    action_type: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
    raise_on_error: bool = False,
) -> None:
    """Write a single AuditLog entry.

    By default this is fire-and-forget: errors are caught and logged but never
    raised, so audit failures never break the underlying operation.

    Set ``raise_on_error=True`` when the audit entry is itself load-bearing and
    the operation must be **fail-closed** (e.g. recording checkout consent — if we
    cannot persist that the buyer accepted the Terms, the purchase must not
    proceed). In that mode a write failure rolls back and re-raises.

    Args:
        db: SQLAlchemy session. A new commit is issued for the audit entry.
        user_id: ID of the acting user (None for system events).
        user_email: User email — denormalised for display after account deletion.
        user_name: User full name — denormalised.
        action: Human-readable action string, e.g. "Created client".
        action_type: Enum-style string: create|update|delete|export|security|system.
        resource_type: Affected resource category: client|project|post|deliverable|brief.
        resource_id: Primary key of the affected resource.
        resource_name: Display-only label (no raw PII stored).
        details: Longer description or context.
        ip_address: Requester IP address.
        status: Outcome — success|failed|warning.
        metadata: Arbitrary JSON (before/after diffs, counts, reasons, etc.).
    """
    try:
        entry = AuditLog(
            id=f"al-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            action=action,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            status=status,
            extra_metadata=metadata,
        )
        db.add(entry)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        if raise_on_error:
            logger.error("audit_service.log_action: failed to write required entry — re-raising")
            raise
        logger.exception("audit_service.log_action: failed to write entry — suppressing")
