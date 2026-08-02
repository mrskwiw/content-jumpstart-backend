"""
Pydantic schemas for Post API.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_serializer

from src.models.client_brief import Platform


class PostBase(BaseModel):
    """Base post schema with camelCase/snake_case bidirectional support"""

    content: str = Field(..., validation_alias=AliasChoices("content"))
    template_id: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("template_id", "templateId")
    )
    template_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("template_name", "templateName")
    )
    variant: Optional[int] = Field(default=None, validation_alias=AliasChoices("variant"))
    target_platform: Optional[Platform] = Field(
        default=Platform.LINKEDIN,
        validation_alias=AliasChoices("target_platform", "targetPlatform"),
    )

    model_config = ConfigDict(
        populate_by_name=True,  # Accept both snake_case and camelCase
    )


class PostCreate(PostBase):
    """
    Schema for creating a post.

    TR-022: Mass assignment protection
    - Only allows: content, template_id, template_name, variant, target_platform
    - Protected fields set by system: id, project_id, run_id, word_count, readability_score,
                                       has_cta, status, flags, created_at
    """

    project_id: str = Field(..., validation_alias=AliasChoices("project_id", "projectId"))
    run_id: str = Field(..., validation_alias=AliasChoices("run_id", "runId"))

    model_config = ConfigDict(
        populate_by_name=True, extra="forbid"  # TR-022: Reject unknown fields
    )


class PostUpdate(BaseModel):
    """
    Schema for updating a post.

    TR-022: Mass assignment protection
    - Updatable: content, approve_override
    - Protected fields (never updatable): id, project_id, run_id, template_id, template_name,
                                           variant, target_platform, word_count, readability_score,
                                           has_cta, status, flags, created_at
    - Note: Quality metrics (word_count, readability_score, has_cta, flags) are calculated fields.
            approve_override=True clears flags and forces status="approved" after save.
    """

    content: str = Field(..., validation_alias=AliasChoices("content"))
    approve_override: bool = Field(
        False,
        description="When True, clears validation flags and forces status to 'approved'",
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",  # TR-022: Reject unknown fields like status, quality_score
    )


class PostResponse(BaseModel):
    """
    Schema for post response.

    TR-022: Includes all fields including read-only and calculated ones
    """

    id: str
    content: str
    template_id: Optional[str] = Field(default=None, serialization_alias="templateId")
    template_name: Optional[str] = Field(default=None, serialization_alias="templateName")
    variant: Optional[int] = None
    target_platform: Optional[Platform] = Field(
        default=Platform.LINKEDIN, serialization_alias="targetPlatform"
    )
    project_id: str = Field(..., serialization_alias="projectId")
    run_id: str = Field(..., serialization_alias="runId")
    word_count: Optional[int] = Field(default=None, serialization_alias="wordCount")
    readability_score: Optional[float] = Field(default=None, serialization_alias="readabilityScore")
    has_cta: Optional[bool] = Field(default=None, serialization_alias="hasCta")
    status: str
    flags: Optional[List[str]] = Field(default_factory=list)
    created_at: datetime = Field(..., serialization_alias="createdAt")

    # Token usage tracking (for individual post generation)
    input_tokens: Optional[int] = Field(default=None, serialization_alias="inputTokens")
    output_tokens: Optional[int] = Field(default=None, serialization_alias="outputTokens")
    cache_read_tokens: Optional[int] = Field(default=None, serialization_alias="cacheReadTokens")
    cost_usd: Optional[float] = Field(default=None, serialization_alias="costUsd")

    # Twitter/X share copy for blog posts
    twitter_share_copy: Optional[str] = Field(default=None, serialization_alias="twitterShareCopy")
    # Team review/approval state (COLLAB-01): "pending" | "approved" | "rejected", or None when
    # the post was never submitted for review. Populated by the list endpoint (batched) so the
    # content review grid can show status per-row without a per-post fetch.
    approval_status: Optional[str] = Field(default=None, serialization_alias="approvalStatus")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    @field_serializer("created_at")
    def serialize_datetime(self, value, _info):
        """Serialize datetime with UTC timezone."""
        if value is None:
            return None
        from datetime import timezone

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
