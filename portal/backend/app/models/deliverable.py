"""Deliverable model for generated content."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class Deliverable(Base):
    """
    Deliverable model for generated content files.

    Attributes:
        deliverable_id: Unique deliverable identifier
        project_id: Foreign key to project
        deliverable_type: Type of deliverable (posts, brand_guide, analytics_report)
        file_path: Path to deliverable file
        file_format: File format (docx, txt, pdf)
        download_count: Number of times downloaded
        created_at: Deliverable creation timestamp
        last_downloaded_at: Last download timestamp
    """

    __tablename__ = "deliverables"

    deliverable_id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False, index=True)

    deliverable_type = Column(String, nullable=False)  # posts, brand_guide, analytics_report
    file_path = Column(String, nullable=False)
    file_format = Column(String, nullable=True)  # docx, txt, pdf
    download_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_downloaded_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="deliverables")

    def __repr__(self):
        return f"<Deliverable(deliverable_id={self.deliverable_id}, type={self.deliverable_type}, format={self.file_format})>"
