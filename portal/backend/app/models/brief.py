"""Brief model for client content requirements."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class Brief(Base):
    """
    Brief model storing client content requirements.

    Stores data from web form submission (CLIENT_BRIEF_TEMPLATE.md).
    JSON fields store arrays/objects as JSON strings.

    Attributes:
        brief_id: Unique brief identifier
        project_id: Foreign key to project (one-to-one)
        tone_descriptors: JSON array of tone descriptors
        voice_notes: Additional voice guidance
        audience_type: ICP audience type (e.g., "B2B SaaS Founders")
        audience_title: Job title (e.g., "VP of Marketing")
        audience_industry: Industry vertical
        pain_points: JSON array of pain points
        key_topics: JSON array of 5 topics
        content_examples: Links to existing content
        target_platforms: JSON array of platforms
        posting_frequency: Posting cadence
        conversion_goal: Main conversion objective
        cta_preference: CTA style preference
        customer_stories: JSON array of customer success stories
        personal_stories: JSON array of personal/founder stories
        created_at: Brief submission timestamp
    """

    __tablename__ = "briefs"

    brief_id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.project_id"), unique=True, nullable=False)

    # Voice & Tone
    tone_descriptors = Column(Text, nullable=True)  # JSON array
    voice_notes = Column(Text, nullable=True)

    # Audience (ICP)
    audience_type = Column(String, nullable=True)
    audience_title = Column(String, nullable=True)
    audience_industry = Column(String, nullable=True)
    pain_points = Column(Text, nullable=True)  # JSON array

    # Topics & Content
    key_topics = Column(Text, nullable=True)  # JSON array
    content_examples = Column(Text, nullable=True)

    # Platform & Goals
    target_platforms = Column(Text, nullable=True)  # JSON array
    posting_frequency = Column(String, nullable=True)
    conversion_goal = Column(String, nullable=True)
    cta_preference = Column(String, nullable=True)

    # Stories
    customer_stories = Column(Text, nullable=True)  # JSON array
    personal_stories = Column(Text, nullable=True)  # JSON array

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="brief")

    def __repr__(self):
        return f"<Brief(brief_id={self.brief_id}, project_id={self.project_id})>"
