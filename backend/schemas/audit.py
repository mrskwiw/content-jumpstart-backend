"""Pydantic schemas for audit log API responses."""

from datetime import timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditUserSchema(BaseModel):
    """Denormalised user snapshot embedded in each audit log entry."""

    id: Optional[str] = None
    name: str = ""
    email: str = ""
    role: str = "User"


class AuditLogResponse(BaseModel):
    """Single audit log entry returned by GET /api/audit."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    timestamp: str = Field(alias="created_at")
    user: AuditUserSchema
    action: str
    action_type: str = Field(serialization_alias="actionType")
    resource: str  # composed: "Client: Acme Corp"
    resource_type: str = Field(serialization_alias="resourceType")
    details: str = ""
    ip_address: str = Field(default="", serialization_alias="ipAddress")
    status: str = "success"
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="extra_metadata")

    @classmethod
    def from_orm_entry(cls, entry: Any) -> "AuditLogResponse":
        """Build response from an AuditLog ORM row."""
        ts = entry.created_at
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        resource_label = entry.resource_type.capitalize()
        resource_name = entry.resource_name or ""
        resource = f"{resource_label}: {resource_name}" if resource_name else resource_label

        return cls.model_construct(
            id=entry.id,
            timestamp=ts.isoformat() if ts else "",
            user=AuditUserSchema(
                id=entry.user_id or "",
                name=entry.user_name or entry.user_email or "Unknown",
                email=entry.user_email or "",
                role="User",
            ),
            action=entry.action,
            action_type=entry.action_type,
            resource=resource,
            resource_type=entry.resource_type,
            details=entry.details or "",
            ip_address=entry.ip_address or "",
            status=entry.status or "success",
            metadata=entry.extra_metadata,
        )

    def model_dump_api(self) -> Dict[str, Any]:
        """Serialise to camelCase dict for API response."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "user": {
                "id": self.user.id,
                "name": self.user.name,
                "email": self.user.email,
                "role": self.user.role,
            },
            "action": self.action,
            "actionType": self.action_type,
            "resource": self.resource,
            "resourceType": self.resource_type,
            "details": self.details,
            "ipAddress": self.ip_address,
            "status": self.status,
            "metadata": self.metadata,
        }


class ComplianceStatsResponse(BaseModel):
    """Aggregate stats for the audit trail compliance dashboard."""

    total_events: int = Field(serialization_alias="totalEvents")
    today_events: int = Field(serialization_alias="todayEvents")
    failed_actions: int = Field(serialization_alias="failedActions")
    security_events: int = Field(serialization_alias="securityEvents")
    avg_events_per_day: float = Field(serialization_alias="avgEventsPerDay")
    retention_days: int = Field(serialization_alias="retentionDays", default=90)
