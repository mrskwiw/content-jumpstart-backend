"""Audit trail router — GET /api/audit and GET /api/audit/stats."""

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user
from backend.models import User
from backend.models.audit_log import AuditLog
from backend.schemas.audit import AuditLogResponse
from backend.utils.http_rate_limiter import standard_limiter

router = APIRouter()

_RETENTION_DAYS = 90


def _build_query(
    db: Session,
    user_id: str,
    action_type: Optional[str],
    resource_type: Optional[str],
    status: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
):
    """Return a filtered AuditLog query scoped to the given user."""
    q = db.query(AuditLog).filter(AuditLog.user_id == user_id)

    if action_type and action_type != "all":
        q = q.filter(AuditLog.action_type == action_type)
    if resource_type and resource_type != "all":
        q = q.filter(AuditLog.resource_type == resource_type)
    if status and status != "all":
        q = q.filter(AuditLog.status == status)
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            q = q.filter(AuditLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
            q = q.filter(AuditLog.created_at <= dt)
        except ValueError:
            pass

    return q.order_by(AuditLog.created_at.desc())


@router.get("/stats")
@standard_limiter.limit("100/hour")
async def get_audit_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return compliance dashboard aggregate stats for the current user."""
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)

    base = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)

    total_events = base.count()
    today_events = base.filter(AuditLog.created_at >= today_start).count()
    failed_actions = (
        base.filter(AuditLog.created_at >= thirty_days_ago)
        .filter(AuditLog.status == "failed")
        .count()
    )
    security_events = (
        base.filter(AuditLog.created_at >= thirty_days_ago)
        .filter(AuditLog.action_type == "security")
        .count()
    )

    # Average events per day over the last 30 days
    events_30d = base.filter(AuditLog.created_at >= thirty_days_ago).count()
    avg_events_per_day = round(events_30d / 30, 1)

    return {
        "totalEvents": total_events,
        "todayEvents": today_events,
        "failedActions": failed_actions,
        "securityEvents": security_events,
        "avgEventsPerDay": avg_events_per_day,
        "retentionDays": _RETENTION_DAYS,
    }


@router.get("/export.csv")
@standard_limiter.limit("20/hour")
async def export_audit_csv(
    request: Request,
    action_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export filtered audit log as CSV for compliance reporting."""
    q = _build_query(
        db, str(current_user.id), action_type, resource_type, status, date_from, date_to
    )
    entries = q.limit(10000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "timestamp",
            "user_email",
            "action",
            "action_type",
            "resource_type",
            "resource_id",
            "resource_name",
            "details",
            "ip_address",
            "status",
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.id,
                e.created_at.isoformat() if e.created_at else "",
                e.user_email or "",
                e.action,
                e.action_type,
                e.resource_type,
                e.resource_id or "",
                e.resource_name or "",
                e.details or "",
                e.ip_address or "",
                e.status,
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )


@router.get("/export.json")
@standard_limiter.limit("20/hour")
async def export_audit_json(
    request: Request,
    action_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export filtered audit log as JSON for compliance reporting."""
    q = _build_query(
        db, str(current_user.id), action_type, resource_type, status, date_from, date_to
    )
    entries = q.limit(10000).all()

    rows = [AuditLogResponse.from_orm_entry(e).model_dump_api() for e in entries]
    payload = json.dumps(rows, indent=2)

    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=audit_log.json"},
    )


@router.get("/")
@standard_limiter.limit("100/hour")
async def list_audit_logs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    action_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Return paginated audit log entries for the current user.

    Filters: action_type, resource_type, status, date_from (ISO), date_to (ISO).
    Authorization: Users see only their own entries.
    """
    q = _build_query(
        db, str(current_user.id), action_type, resource_type, status, date_from, date_to
    )
    entries = q.offset(skip).limit(limit).all()
    return [AuditLogResponse.from_orm_entry(e).model_dump_api() for e in entries]
