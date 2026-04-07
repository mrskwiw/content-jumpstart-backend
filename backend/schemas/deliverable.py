"""
Pydantic schemas for Deliverable API.
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_serializer


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

    project_id: str = Field(..., validation_alias=AliasChoices("project_id", "projectId"))
    run_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("run_id", "runId"))

    model_config = ConfigDict(
        populate_by_name=True, extra="forbid"  # TR-022: Reject unknown fields
    )


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


class DeliverableResponse(BaseModel):
    """
    Schema for deliverable response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    format: str
    project_id: str = Field(..., serialization_alias="projectId")
    client_id: str = Field(..., serialization_alias="clientId")
    run_id: Optional[str] = Field(default=None, serialization_alias="runId")
    path: str
    status: str
    created_at: datetime = Field(..., serialization_alias="createdAt")
    delivered_at: Optional[datetime] = Field(default=None, serialization_alias="deliveredAt")
    proof_url: Optional[str] = Field(default=None, serialization_alias="proofUrl")
    proof_notes: Optional[str] = Field(default=None, serialization_alias="proofNotes")
    checksum: Optional[str] = None
    file_size_bytes: Optional[int] = Field(default=None, serialization_alias="fileSizeBytes")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    @field_serializer("created_at", "delivered_at", when_used="always")
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Serialize datetime to ISO 8601 with timezone (Z suffix for UTC)"""
        if dt is None:
            return None
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class MarkDeliveredRequest(BaseModel):
    """Schema for marking deliverable as delivered"""

    delivered_at: datetime = Field(
        ..., validation_alias=AliasChoices("delivered_at", "deliveredAt")
    )
    proof_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("proof_url", "proofUrl")
    )
    proof_notes: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("proof_notes", "proofNotes")
    )

    model_config = ConfigDict(populate_by_name=True)


# Extended schemas for deliverable details endpoint


class PostSummary(BaseModel):
    """Summary of a post for deliverable details"""

    id: str
    template_name: Optional[str] = Field(default=None, serialization_alias="templateName")
    word_count: Optional[int] = Field(default=None, serialization_alias="wordCount")
    readability_score: Optional[float] = Field(default=None, serialization_alias="readabilityScore")
    status: str
    flags: Optional[List[str]] = None
    content: str = ""  # Full post content
    content_preview: str = Field(..., serialization_alias="contentPreview")  # First 150 chars

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class QASummary(BaseModel):
    """Quality assurance summary"""

    avg_readability: Optional[float] = Field(default=None, serialization_alias="avgReadability")
    avg_word_count: Optional[float] = Field(default=None, serialization_alias="avgWordCount")
    total_posts: int = Field(default=0, serialization_alias="totalPosts")
    flagged_count: int = Field(default=0, serialization_alias="flaggedCount")
    approved_count: int = Field(default=0, serialization_alias="approvedCount")
    cta_percentage: Optional[float] = Field(default=None, serialization_alias="ctaPercentage")
    common_flags: List[str] = Field(default_factory=list, serialization_alias="commonFlags")

    model_config = ConfigDict(
        populate_by_name=True,
    )


class ResearchResultSummary(BaseModel):
    """Research result summary for deliverable details"""

    id: str
    user_id: str = Field(..., serialization_alias="userId")
    client_id: str = Field(..., serialization_alias="clientId")
    project_id: Optional[str] = Field(default=None, serialization_alias="projectId")
    tool_name: str = Field(..., serialization_alias="toolName")
    tool_label: Optional[str] = Field(default=None, serialization_alias="toolLabel")
    tool_price: Optional[float] = Field(default=None, serialization_alias="toolPrice")
    actual_cost_usd: Optional[float] = Field(default=None, serialization_alias="actualCostUsd")
    summary: Optional[str] = None
    status: str
    error_message: Optional[str] = Field(default=None, serialization_alias="errorMessage")
    duration_seconds: Optional[float] = Field(default=None, serialization_alias="durationSeconds")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    @field_serializer("created_at", when_used="always")
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Serialize datetime to ISO 8601 with timezone (Z suffix for UTC)"""
        if dt is None:
            return None
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class DeliverableDetailResponse(DeliverableResponse):
    """Extended deliverable response with all details for drawer"""

    file_preview: Optional[str] = Field(
        default=None, serialization_alias="filePreview"
    )  # First 5000 chars
    file_preview_truncated: bool = Field(default=False, serialization_alias="filePreviewTruncated")
    posts: List[PostSummary] = Field(default_factory=list)
    qa_summary: Optional[QASummary] = Field(default=None, serialization_alias="qaSummary")
    file_modified_at: Optional[datetime] = Field(default=None, serialization_alias="fileModifiedAt")
    research_results: List[ResearchResultSummary] = Field(
        default_factory=list, serialization_alias="researchResults"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    @field_serializer("created_at", "delivered_at", "file_modified_at", when_used="always")
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Serialize all datetime fields to ISO 8601 with timezone (Z suffix for UTC)"""
        if dt is None:
            return None
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
