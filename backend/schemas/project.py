"""
Pydantic schemas for Project API.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    """Base project schema"""

    name: str
    client_id: str
    templates: Optional[List[str]] = []
    platforms: Optional[List[str]] = []
    tone: Optional[str] = "professional"


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""



class ProjectUpdate(BaseModel):
    """Schema for updating a project"""

    name: Optional[str] = None
    status: Optional[str] = None
    templates: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    tone: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Schema for project response"""

    id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        ),  # Convert snake_case to camelCase
    )
