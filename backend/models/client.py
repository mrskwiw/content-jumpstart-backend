"""
Client model.
"""
from sqlalchemy import Column, DateTime, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Client(Base):
    """Client company"""

    __tablename__ = "clients"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ClientBrief fields (from wizard)
    business_description = Column(Text, nullable=True)
    ideal_customer = Column(Text, nullable=True)
    main_problem_solved = Column(Text, nullable=True)
    tone_preference = Column(String, nullable=True, default='professional')
    platforms = Column(JSON, nullable=True)
    customer_pain_points = Column(JSON, nullable=True)
    customer_questions = Column(JSON, nullable=True)

    # Relationships
    projects = relationship("Project", back_populates="client", cascade="all, delete-orphan")
    deliverables = relationship("Deliverable", back_populates="client")

    def __repr__(self):
        return f"<Client {self.name}>"
