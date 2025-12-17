"""
Pydantic schemas for Post API.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class PostBase(BaseModel):
    """Base post schema"""

    content: str
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    variant: Optional[int] = None
    target_platform: Optional[str] = "linkedin"


class PostResponse(PostBase):
    """Schema for post response"""

    id: str
    project_id: str
    run_id: str
    word_count: Optional[int] = None
    readability_score: Optional[float] = None
    has_cta: Optional[bool] = None
    status: str
    flags: Optional[List[str]] = []
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        ),  # Convert snake_case to camelCase
    )
