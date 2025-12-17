"""Project model for content generation requests."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class Project(Base):
    """
    Project model representing a client content generation request.

    Status Flow:
        brief_submitted → processing → qa_review → ready_for_delivery →
        delivered → revision_requested → completed

    Attributes:
        project_id: Unique project identifier
        user_id: Foreign key to user
        client_name: Client/business name for this project
        status: Current project status
        package_tier: Package level (starter, professional, premium)
        package_price: Price paid for package
        posts_count: Number of posts to generate (default 30)
        revision_limit: Number of revisions allowed
        revisions_used: Number of revisions consumed
        brief_file_path: Path to uploaded brief file
        voice_sample_path: Path to voice sample file
        deliverable_path: Path to final deliverable
        submitted_at: Project submission timestamp
        processing_started_at: When generation started
        completed_at: When generation completed
        delivered_at: When delivered to client
    """

    __tablename__ = "projects"

    project_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    client_name = Column(String, nullable=False)
    client_company = Column(String, nullable=False)
    client_email = Column(String, nullable=False)

    # Status tracking
    status = Column(String, default="brief_submitted")
    # Possible values: brief_submitted, processing, qa_review,
    #                  ready_for_delivery, delivered, revision_requested, completed

    # Package details
    package_tier = Column(String, nullable=False)  # starter, professional, premium
    package_price = Column(Float, nullable=False)
    posts_count = Column(Integer, default=30)

    # Revision tracking
    revision_limit = Column(Integer, default=1)
    revisions_used = Column(Integer, default=0)

    # Files & outputs
    brief_file_path = Column(String, nullable=True)
    voice_sample_path = Column(String, nullable=True)
    deliverable_path = Column(String, nullable=True)

    # Timeline
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)
    processing_started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="projects")
    brief = relationship(
        "Brief", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    file_uploads = relationship(
        "FileUpload", back_populates="project", cascade="all, delete-orphan"
    )
    posts = relationship("Post", back_populates="project", cascade="all, delete-orphan")
    revisions = relationship("Revision", back_populates="project", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="project", cascade="all, delete-orphan")
    deliverables = relationship(
        "Deliverable", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(project_id={self.project_id}, client={self.client_name}, status={self.status})>"
