"""
Run model for generation executions.
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Run(Base):
    """Generation execution run"""

    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    is_batch = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(
        String, nullable=False, default="pending"
    )  # pending, running, succeeded, failed
    logs = Column(JSON)  # Array of log messages
    error_message = Column(String)  # Error details if failed

    # Relationships
    project = relationship("Project", back_populates="runs")
    posts = relationship("Post", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Run {self.id} ({self.status})>"
