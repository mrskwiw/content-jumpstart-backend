"""
Pydantic schemas for Brief API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BriefCreate(BaseModel):
    """
    Schema for creating a brief from pasted text.

    TR-022: Mass assignment protection
    - Only allows: project_id, content
    - Protected fields set by system: id, source, file_path, created_at
    """

    project_id: str
    content: str

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields


class BriefUpdate(BaseModel):
    """
    Schema for updating a brief.

    TR-022: Mass assignment protection
    - Only allows: content
    - Protected fields (never updatable): id, project_id, source, file_path, created_at
    """

    content: Optional[str] = None

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields


class BriefResponse(BaseModel):
    """
    Schema for brief response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    project_id: str
    content: str
    source: str  # "upload" or "paste"
    file_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),  # Convert snake_case to camelCase
    )
