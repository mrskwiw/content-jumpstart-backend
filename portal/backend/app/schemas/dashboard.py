"""Dashboard schemas for project overview."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """Statistics for dashboard overview."""

    total_files: int = Field(..., description="Total uploaded files")
    total_deliverables: int = Field(..., description="Total deliverables")
    brief_submitted: bool = Field(..., description="Whether brief is submitted")
    days_since_created: int = Field(..., description="Days since project creation")


class DashboardResponse(BaseModel):
    """Schema for project dashboard response."""

    # Project information
    project_id: str
    client_name: str
    package_tier: str
    package_price: float
    status: str
    created_at: datetime
    updated_at: datetime

    # Statistics
    stats: DashboardStats

    # Optional brief ID if exists
    brief_id: Optional[str] = None

    class Config:
        from_attributes = True
