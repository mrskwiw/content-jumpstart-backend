"""
Client model.
"""
from sqlalchemy import Column, DateTime, String
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

    # Relationships
    projects = relationship("Project", back_populates="client", cascade="all, delete-orphan")
    deliverables = relationship("Deliverable", back_populates="client")

    def __repr__(self):
        return f"<Client {self.name}>"
