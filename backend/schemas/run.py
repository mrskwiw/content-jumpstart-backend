"""
Pydantic schemas for Run API.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    """Schema for creating a run"""

    project_id: str
    is_batch: bool = False


class RunUpdate(BaseModel):
    """Schema for updating a run"""

    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    logs: Optional[List[str]] = None
    error_message: Optional[str] = None


class RunResponse(BaseModel):
    """Schema for run response"""

    id: str
    project_id: str
    is_batch: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # pending, running, succeeded, failed
    logs: Optional[List[str]] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        ),  # Convert snake_case to camelCase
    )
