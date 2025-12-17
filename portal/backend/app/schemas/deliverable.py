"""Deliverable schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeliverableResponse(BaseModel):
    """Schema for deliverable response."""

    deliverable_id: str
    project_id: str
    deliverable_type: str
    file_path: str
    file_format: Optional[str]
    download_count: int
    created_at: datetime
    last_downloaded_at: Optional[datetime]

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class DeliverableListResponse(BaseModel):
    """Schema for listing deliverables."""

    total: int = Field(..., description="Total number of deliverables")
    deliverables: list[DeliverableResponse] = Field(..., description="List of deliverables")
