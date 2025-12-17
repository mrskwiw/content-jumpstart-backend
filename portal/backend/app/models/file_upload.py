"""File upload model for client files."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..db.database import Base


def generate_uuid():
    """Generate a lowercase hex UUID."""
    return uuid.uuid4().hex


class FileUpload(Base):
    """
    File upload model for client-uploaded files.

    Tracks voice samples, brand assets, brief attachments, etc.

    Attributes:
        file_id: Unique file identifier
        project_id: Foreign key to project
        user_id: Foreign key to user (uploader)
        file_type: Type of file (voice_sample, brand_asset, brief_attachment)
        original_filename: Original filename from upload
        stored_filename: Unique stored filename (UUID + extension)
        file_path: Full path to stored file
        file_size: File size in bytes
        mime_type: MIME type of file
        uploaded_at: Upload timestamp
    """

    __tablename__ = "file_uploads"

    file_id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)

    file_type = Column(String, nullable=False)  # voice_sample, brand_asset, brief_attachment
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    mime_type = Column(String, nullable=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="file_uploads")
    user = relationship("User", back_populates="file_uploads")

    def __repr__(self):
        return f"<FileUpload(file_id={self.file_id}, filename={self.original_filename}, type={self.file_type})>"
