"""Revision request model."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class Revision(Base):
    """
    Revision request model for content changes.

    Attributes:
        revision_id: Unique revision identifier
        project_id: Foreign key to project
        user_id: Foreign key to user (requester)
        revision_number: Sequential revision number (1st, 2nd, etc.)
        post_numbers: JSON array of post numbers to revise
        feedback_text: Client feedback/change requests
        status: Revision status (pending, in_progress, completed, rejected)
        admin_notes: Internal notes from admin
        completed_at: When revision was completed
        created_at: Revision request timestamp
    """

    __tablename__ = "revisions"

    revision_id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)

    revision_number = Column(Integer, nullable=False)
    post_numbers = Column(Text, nullable=True)  # JSON array: [3, 7, 12]
    feedback_text = Column(Text, nullable=False)

    # Status
    status = Column(String, default="pending")  # pending, in_progress, completed, rejected

    # Response
    admin_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="revisions")
    user = relationship("User", back_populates="revisions")

    def __repr__(self):
        return f"<Revision(revision_id={self.revision_id}, project_id={self.project_id}, number={self.revision_number}, status={self.status})>"
