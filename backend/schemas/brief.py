"""
Pydantic schemas for Brief API.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BriefCreate(BaseModel):
    """Schema for creating a brief from pasted text"""

    project_id: str
    content: str


class BriefResponse(BaseModel):
    """Schema for brief response"""

    id: str
    project_id: str
    content: str
    source: str  # "upload" or "paste"
    file_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        ),  # Convert snake_case to camelCase
    )
