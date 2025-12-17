"""Activity log model for audit trail."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from ..db.database import Base


class ActivityLog(Base):
    """
    Activity log model for audit trail and security monitoring.

    Tracks all user actions for security and debugging.

    Attributes:
        activity_id: Auto-incrementing activity ID
        user_id: Foreign key to user (nullable for anonymous actions)
        project_id: Foreign key to project (nullable)
        activity_type: Type of activity (login, project_created, etc.)
        description: Human-readable description
        extra_data: JSON string with additional context
        ip_address: Client IP address
        created_at: Activity timestamp
    """

    __tablename__ = "activity_log"

    activity_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=True, index=True)

    activity_type = Column(String, nullable=False, index=True)
    # Activity types: login, logout, project_created, brief_submitted,
    #                payment_received, revision_requested, file_uploaded, etc.

    description = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON for additional context
    ip_address = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ActivityLog(activity_id={self.activity_id}, type={self.activity_type}, user_id={self.user_id})>"
