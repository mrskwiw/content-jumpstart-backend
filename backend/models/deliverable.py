"""
Deliverable model for exported content packages.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Deliverable(Base):
    """Exported deliverable package"""

    __tablename__ = "deliverables"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)
    run_id = Column(String, ForeignKey("runs.id"), index=True)
    format = Column(String, nullable=False)  # txt, docx, pdf
    path = Column(String, nullable=False)  # File path
    status = Column(String, nullable=False, default="draft", index=True)  # draft, ready, delivered - indexed for filtering
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))
    proof_url = Column(String)  # URL to delivery proof
    proof_notes = Column(String)  # Notes about delivery
    checksum = Column(String)  # File checksum for verification
    file_size_bytes = Column(Integer)  # Actual file size in bytes

    # Relationships
    project = relationship("Project", back_populates="deliverables")
    client = relationship("Client", back_populates="deliverables")

    def __repr__(self):
        return f"<Deliverable {self.id} ({self.status})>"
