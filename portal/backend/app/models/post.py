"""Post model for generated social media content."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class Post(Base):
    """
    Post model for individual generated social media posts.

    Attributes:
        post_id: Unique post identifier
        project_id: Foreign key to project
        post_number: Sequential number in batch (1-30)
        content: Post text content
        template_name: Template used to generate
        platform: Target platform (LinkedIn, Twitter, etc.)
        word_count: Number of words in post
        status: Post status (draft, final, needs_revision)
        revision_of: Reference to original post if this is a revision
        version: Version number (1 for original, 2+ for revisions)
        generated_at: When post was generated
        last_edited_at: When post was last edited
        edited_by: User who last edited (for tracking)
    """

    __tablename__ = "posts"

    post_id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False, index=True)

    # Post content
    post_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    template_name = Column(String, nullable=True)
    platform = Column(String, default="LinkedIn")
    word_count = Column(Integer, default=0)

    # Status tracking
    status = Column(String, default="draft")  # draft, final, needs_revision
    revision_of = Column(String, ForeignKey("posts.post_id"), nullable=True)
    version = Column(Integer, default=1)

    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    last_edited_at = Column(DateTime, nullable=True)
    edited_by = Column(String, nullable=True)  # User ID who edited

    # Relationships
    project = relationship("Project", back_populates="posts")

    # Self-referential relationship for revisions
    original_post = relationship(
        "Post", remote_side=[post_id], foreign_keys=[revision_of], backref="revisions"
    )

    def __repr__(self):
        return f"<Post(post_id={self.post_id}, project_id={self.project_id}, number={self.post_number}, status={self.status})>"
