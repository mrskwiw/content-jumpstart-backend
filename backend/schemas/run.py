"""
Pydantic schemas for Run API.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator, field_serializer

from backend.utils.logger import logger


class LogEntry(BaseModel):
    """Schema for structured log entry"""

    timestamp: str
    message: str


class RunCreate(BaseModel):
    """
    Schema for creating a run.

    TR-022: Mass assignment protection
    - Only allows: project_id, is_batch
    - Protected fields set by system: id, started_at, completed_at, status, logs, error_message
    """

    project_id: str = Field(..., validation_alias=AliasChoices("project_id", "projectId"))
    is_batch: bool = Field(default=False, validation_alias=AliasChoices("is_batch", "isBatch"))

    model_config = ConfigDict(
        populate_by_name=True, extra="forbid"  # TR-022: Reject unknown fields
    )


class RunUpdate(BaseModel):
    """
    Schema for updating a run.

    TR-022: Mass assignment protection
    - Only allows: status, completed_at, logs, error_message
    - Protected fields (never updatable): id, project_id, is_batch, started_at
    - Note: Typically used by system to update run status and logs
    """

    status: Optional[str] = None
    completed_at: Optional[datetime] = Field(
        default=None, validation_alias=AliasChoices("completed_at", "completedAt")
    )
    logs: Optional[List[LogEntry]] = None
    error_message: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("error_message", "errorMessage")
    )

    model_config = ConfigDict(
        populate_by_name=True, extra="forbid"  # TR-022: Reject unknown fields
    )


class RunResponse(BaseModel):
    """
    Schema for run response.

    TR-022: Includes all fields including read-only ones
    """

    id: str
    project_id: str = Field(..., serialization_alias="projectId")
    is_batch: bool = Field(..., serialization_alias="isBatch")
    started_at: datetime = Field(..., serialization_alias="startedAt")
    completed_at: Optional[datetime] = Field(default=None, serialization_alias="completedAt")
    status: str  # pending, running, succeeded, failed
    logs: Optional[List[LogEntry]] = None
    error_message: Optional[str] = Field(default=None, serialization_alias="errorMessage")

    # Token usage tracking (cumulative for all posts in this run)
    total_input_tokens: Optional[int] = Field(default=None, serialization_alias="totalInputTokens")
    total_output_tokens: Optional[int] = Field(
        default=None, serialization_alias="totalOutputTokens"
    )
    total_cache_creation_tokens: Optional[int] = Field(
        default=None, serialization_alias="totalCacheCreationTokens"
    )
    total_cache_read_tokens: Optional[int] = Field(
        default=None, serialization_alias="totalCacheReadTokens"
    )
    total_cost_usd: Optional[float] = Field(default=None, serialization_alias="totalCostUsd")
    estimated_cost_usd: Optional[float] = Field(
        default=None, serialization_alias="estimatedCostUsd"
    )
    qa_score: Optional[float] = Field(default=None, serialization_alias="qaScore")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    @field_validator("logs", mode="before")
    @classmethod
    def convert_logs(cls, value: Any) -> Optional[List[LogEntry]]:
        """Convert plain string logs to LogEntry objects"""
        if value is None:
            return None
        if isinstance(value, list):
            # Convert plain strings to LogEntry objects
            converted = []
            for item in value:
                if isinstance(item, str):
                    # Plain string - convert to LogEntry with current timestamp
                    converted.append(LogEntry(timestamp=datetime.now().isoformat(), message=item))
                elif isinstance(item, dict):
                    # Already a dict - convert to LogEntry
                    converted.append(LogEntry(**item))
                elif isinstance(item, LogEntry):
                    # Already a LogEntry
                    converted.append(item)
            return converted
        logger.warning(f"Unexpected logs value type: {type(value)}, returning empty list")
        return []

    @field_serializer("started_at", "completed_at")
    def serialize_datetime(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize datetime with UTC timezone.

        Ensures all datetime fields include timezone information (Z or +00:00)
        to match frontend Zod validation requirements.
        """
        if value is None:
            return None

        # If timezone-naive, treat as UTC
        from datetime import timezone

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        # Serialize to ISO format with timezone
        return value.isoformat()
