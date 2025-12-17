"""File upload schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Schema for file upload response."""

    file_id: str
    project_id: str
    file_type: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class FileListResponse(BaseModel):
    """Schema for listing uploaded files."""

    total: int = Field(..., description="Total number of files")
    files: list[FileUploadResponse] = Field(..., description="List of uploaded files")
