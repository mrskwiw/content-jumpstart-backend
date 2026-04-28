"""
Client model.
"""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.models.mixins import SoftDeleteMixin


class Client(Base, SoftDeleteMixin):
    """Client company"""

    __tablename__ = "clients"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    user_id = Column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )  # TR-021: Owner of client
    name = Column(String, nullable=False, index=True)
    email = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ClientBrief fields (from wizard)
    business_description = Column(Text, nullable=True)
    ideal_customer = Column(Text, nullable=True)
    main_problem_solved = Column(Text, nullable=True)
    tone_preference = Column(String, nullable=True, default="professional")
    platforms = Column(JSON, nullable=True)
    customer_pain_points = Column(JSON, nullable=True)
    customer_questions = Column(JSON, nullable=True)
    industry = Column(
        String, nullable=True
    )  # Specific industry/niche (e.g., "dental practice", "project management software") for competitive analysis
    keywords = Column(
        JSON, nullable=True
    )  # SEO keywords for content optimization (array of strings). If 5+ keywords provided, can skip SEO research tool.
    competitors = Column(
        JSON, nullable=True
    )  # List of competitor names (1-5) for competitive analysis. Auto-populates competitive analysis tool.
    location = Column(
        String, nullable=True
    )  # Geographic location/region (e.g., "San Francisco", "USA", "Global") for market context

    # Extended profile fields (from pre-call interview)
    founder_name = Column(String, nullable=True)  # Founder/owner name for personal brand content
    brand_personality = Column(
        JSON, nullable=True
    )  # Personality traits (e.g., ["direct", "witty"])
    tone_to_avoid = Column(Text, nullable=True)  # Tone/style the client does NOT want
    data_usage = Column(String, nullable=True, default="moderate")  # heavy / moderate / minimal
    stories = Column(JSON, nullable=True)  # Founder journey, customer wins, anecdotes
    misconceptions = Column(JSON, nullable=True)  # Industry myths / topics to avoid
    measurable_results = Column(
        Text, nullable=True
    )  # Stats and proof points (e.g., "90% success rate")
    posting_frequency = Column(
        String, nullable=True
    )  # Desired posting cadence (e.g., "3-4x weekly")
    main_cta = Column(String, nullable=True)  # Primary call-to-action text
    key_phrases = Column(JSON, nullable=True)  # Key brand/product phrases extracted from brief
    recommended_platforms = Column(
        JSON, nullable=True
    )  # Platform recommendations from platform_strategy research tool (e.g., ["linkedin", "twitter", "blog"])

    # Relationships (using fully qualified paths to avoid conflicts with Pydantic models in src.models)
    user = relationship("backend.models.user.User", foreign_keys=[user_id])  # TR-021: Client owner
    projects = relationship(
        "backend.models.project.Project",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    deliverables = relationship("backend.models.deliverable.Deliverable", back_populates="client")
    communications = relationship(
        "Communication", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Client {self.name}>"
