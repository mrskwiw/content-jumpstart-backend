"""
Post model for generated content.
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class Post(Base):
    """Generated social media post"""

    __tablename__ = "posts"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    template_id = Column(String)
    template_name = Column(String)
    variant = Column(Integer)  # Template variant number
    word_count = Column(Integer)
    readability_score = Column(Float)
    has_cta = Column(Boolean)
    status = Column(String, nullable=False, default="approved")  # approved, flagged
    flags = Column(JSON)  # Array of flag strings (e.g., ["too_short", "missing_cta"])
    target_platform = Column(String)  # linkedin, twitter, facebook, blog
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships (using fully qualified paths to avoid conflicts with Pydantic models in src.models)
    project = relationship("backend.models.project.Project", back_populates="posts")
    run = relationship("backend.models.run.Run", back_populates="posts")

    # Composite indexes for common query patterns
    __table_args__ = (
        # Most common filter combinations
        Index('ix_posts_project_status', 'project_id', 'status'),
        Index('ix_posts_status_created', 'status', 'created_at'),
        Index('ix_posts_platform_status', 'target_platform', 'status'),
        # Template name for ILIKE searches
        Index('ix_posts_template_name', 'template_name'),
        # Word count for range queries
        Index('ix_posts_word_count', 'word_count'),
        # Readability score for range queries
        Index('ix_posts_readability', 'readability_score'),
        # Cursor pagination index (Week 3 optimization)
        # Enables O(1) performance for deep pagination
        Index('ix_posts_created_at_id', 'created_at', 'id', postgresql_using='btree'),
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<Post {self.id} ({self.status})>"
