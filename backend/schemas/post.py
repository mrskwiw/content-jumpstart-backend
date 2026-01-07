"""
Pydantic schemas for Post API.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from src.models.client_brief import Platform


class PostBase(BaseModel):
    """Base post schema"""

    content: str
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    variant: Optional[int] = None
    target_platform: Optional[Platform] = Platform.LINKEDIN


class PostCreate(PostBase):
    """
    Schema for creating a post.

    TR-022: Mass assignment protection
    - Only allows: content, template_id, template_name, variant, target_platform
    - Protected fields set by system: id, project_id, run_id, word_count, readability_score,
                                       has_cta, status, flags, created_at
    """

    project_id: str  # Required when creating
    run_id: str  # Required when creating

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields


class PostUpdate(BaseModel):
    """
    Schema for updating a post.

    TR-022: Mass assignment protection
    - Only allows: content
    - Protected fields (never updatable): id, project_id, run_id, template_id, template_name,
                                           variant, target_platform, word_count, readability_score,
                                           has_cta, status, flags, created_at
    - Note: Quality metrics (word_count, readability_score, has_cta, flags) are calculated fields
    """

    content: str

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",  # TR-022: Reject unknown fields like status, quality_score
    )


class PostResponse(PostBase):
    """
    Schema for post response.

    TR-022: Includes all fields including read-only and calculated ones
    """

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
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),  # Convert snake_case to camelCase
    )
