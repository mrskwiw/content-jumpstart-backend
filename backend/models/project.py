"""
Project model.
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Project(Base):
    """Content generation project"""

    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="draft"
    )  # draft, processing, qa_review, ready, delivered
    templates = Column(JSON)  # Array of template IDs
    platforms = Column(JSON)  # Array of platform names
    tone = Column(String)  # professional, casual, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    client = relationship("Client", back_populates="projects")
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="project", cascade="all, delete-orphan")
    deliverables = relationship(
        "Deliverable", back_populates="project", cascade="all, delete-orphan"
    )
    brief = relationship(
        "Brief", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )

    # Composite indexes for cursor pagination (Week 3 optimization)
    __table_args__ = (
        # Cursor pagination index: (created_at DESC, id DESC)
        # Enables O(1) performance for deep pagination
        Index('ix_projects_created_at_id', 'created_at', 'id', postgresql_using='btree'),
    )

    def __repr__(self):
        return f"<Project {self.name} ({self.status})>"
