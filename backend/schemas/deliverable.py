"""
Pydantic schemas for Deliverable API.
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_serializer


class DeliverableBase(BaseModel):
    """Base deliverable schema"""

    format: str  # txt, docx, pdf


class DeliverableCreate(DeliverableBase):
    """
    Schema for creating a deliverable.

    TR-022: Mass assignment protection
    - Only allows: format, project_id, run_id
    - Protected fields set by system: id, client_id, path, status, created_at, delivered_at,
                                       proof_url, proof_notes, checksum, file_size_bytes
    """

    project_id: str
    run_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields


class DeliverableUpdate(BaseModel):
    """
    Schema for updating a deliverable.

    TR-022: Mass assignment protection
    - Only allows: status
    - Protected fields (never updatable): id, project_id, client_id, run_id, format, path,
                                           created_at, delivered_at, proof_url, proof_notes,
                                           checksum, file_size_bytes
    - Note: Use MarkDeliveredRequest for delivery status updates
    """

    status: Optional[str] = None

    model_config = ConfigDict(extra="forbid")  # TR-022: Reject unknown fields


class DeliverableResponse(DeliverableBase):
    """
    Schema for deliverable response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    project_id: str
    client_id: str
    run_id: Optional[str] = None
    path: str
    status: str
    created_at: datetime
    delivered_at: Optional[datetime] = None
    proof_url: Optional[str] = None
    proof_notes: Optional[str] = None
    checksum: Optional[str] = None
    file_size_bytes: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),  # Convert snake_case to camelCase
    )

    @field_serializer("created_at", "delivered_at", when_used="always")
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Serialize datetime to ISO 8601 with timezone (Z suffix for UTC)"""
        if dt is None:
            return None
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class MarkDeliveredRequest(BaseModel):
    """Schema for marking deliverable as delivered"""

    delivered_at: datetime
    proof_url: Optional[str] = None
    proof_notes: Optional[str] = None


# Extended schemas for deliverable details endpoint


class PostSummary(BaseModel):
    """Summary of a post for deliverable details"""

    id: str
    template_name: Optional[str] = None
    word_count: Optional[int] = None
    readability_score: Optional[float] = None
    status: str
    flags: Optional[List[str]] = None
    content_preview: str  # First 150 chars

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),
    )


class QASummary(BaseModel):
    """Quality assurance summary"""

    avg_readability: Optional[float] = None
    avg_word_count: Optional[float] = None
    total_posts: int = 0
    flagged_count: int = 0
    approved_count: int = 0
    cta_percentage: Optional[float] = None
    common_flags: List[str] = []

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),
    )


class DeliverableDetailResponse(DeliverableResponse):
    """Extended deliverable response with all details for drawer"""

    file_preview: Optional[str] = None  # First 5000 chars
    file_preview_truncated: bool = False
    posts: List[PostSummary] = []
    qa_summary: Optional[QASummary] = None
    file_modified_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))
        ),
    )

    @field_serializer("created_at", "delivered_at", "file_modified_at", when_used="always")
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Serialize all datetime fields to ISO 8601 with timezone (Z suffix for UTC)"""
        if dt is None:
            return None
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
