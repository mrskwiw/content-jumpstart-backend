"""
Deliverable model for exported content packages.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class Deliverable(Base):
    """Exported deliverable package"""

    __tablename__ = "deliverables"

    id = Column(String, primary_key=True)
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

    # Relationships (using fully qualified paths to avoid conflicts with Pydantic models in src.models)
    project = relationship("backend.models.project.Project")
    client = relationship("backend.models.client.Client")

    # Composite indexes for common query patterns (Performance optimization - December 25, 2025)
    __table_args__ = (
        # Most common filter combinations
        Index('ix_deliverables_client_status', 'client_id', 'status'),  # Filter by client AND status
        Index('ix_deliverables_project_status', 'project_id', 'status'),  # Filter by project AND status
        Index('ix_deliverables_status_created', 'status', 'created_at'),  # Filter by status, sort by date
        # Cursor pagination index (enables O(1) performance for deep pagination)
        Index('ix_deliverables_created_at_id', 'created_at', 'id', postgresql_using='btree'),
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<Deliverable {self.id} ({self.status})>"
