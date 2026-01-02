"""
Brief model for client briefs.
"""
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class Brief(Base):
    """Client brief (uploaded file or pasted text)"""

    __tablename__ = "briefs"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, unique=True)
    content = Column(Text, nullable=False)  # Brief text content
    source = Column(String, nullable=False)  # "upload" or "paste"
    file_path = Column(String)  # Path to uploaded file (if source=upload)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("backend.models.project.Project")

    def __repr__(self):
        return f"<Brief for {self.project_id}>"
