"""Project schemas for request/response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    client_name: str = Field(..., min_length=1, description="Client/company name")
    client_company: str = Field(..., min_length=1, description="Client company name")
    client_email: str = Field(..., min_length=1, description="Client email address")
    package_tier: str = Field(
        ..., description="Package level (Starter, Professional, Premium, Enterprise)"
    )
    package_price: Optional[float] = Field(
        None, gt=0, description="Package price in USD (auto-set if not provided)"
    )
    posts_count: int = Field(default=30, description="Number of posts to generate")
    revision_limit: int = Field(default=1, description="Maximum number of revision rounds")
    brief_data: Optional[str] = Field(None, description="Brief content data")


class ProjectUpdate(BaseModel):
    """Schema for updating project fields."""

    status: Optional[str] = Field(None, description="Project status")
    processing_started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When generation completed")
    delivered_at: Optional[datetime] = Field(None, description="When delivered to client")


class ProjectResponse(BaseModel):
    """Schema for project response."""

    project_id: str
    user_id: str
    client_name: str
    client_company: str
    client_email: str
    status: str
    package_tier: str
    package_price: float
    posts_count: int
    revision_limit: int
    revisions_used: int
    submitted_at: datetime
    processing_started_at: Optional[datetime]
    completed_at: Optional[datetime]
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class ProjectListResponse(BaseModel):
    """Schema for listing projects."""

    total: int = Field(..., description="Total number of projects")
    projects: List[ProjectResponse] = Field(..., description="List of projects")


class ProjectStatusUpdate(BaseModel):
    """Schema for updating project status."""

    status: str = Field(
        ...,
        description="New project status (brief_submitted, processing, qa_review, ready_for_delivery, delivered, completed)",
    )
