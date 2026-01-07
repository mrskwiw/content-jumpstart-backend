"""
Client model.
"""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class Client(Base):
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

    # Relationships (using fully qualified paths to avoid conflicts with Pydantic models in src.models)
    user = relationship("backend.models.user.User", foreign_keys=[user_id])  # TR-021: Client owner
    projects = relationship(
        "backend.models.project.Project", back_populates="client", cascade="all, delete-orphan"
    )
    deliverables = relationship("backend.models.deliverable.Deliverable", back_populates="client")

    def __repr__(self):
        return f"<Client {self.name}>"
