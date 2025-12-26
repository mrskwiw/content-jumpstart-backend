"""
Pydantic schemas for Run API.
"""
from datetime import datetime
from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LogEntry(BaseModel):
    """Schema for structured log entry"""

    timestamp: str
    message: str


class RunCreate(BaseModel):
    """Schema for creating a run"""

    project_id: str
    is_batch: bool = False


class RunUpdate(BaseModel):
    """Schema for updating a run"""

    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    logs: Optional[List[LogEntry]] = None
    error_message: Optional[str] = None


class RunResponse(BaseModel):
    """Schema for run response"""

    id: str
    project_id: str
    is_batch: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # pending, running, succeeded, failed
    logs: Optional[List[LogEntry]] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        alias_generator=lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        ),  # Convert snake_case to camelCase
    )

    @field_validator('logs', mode='before')
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
                    converted.append(LogEntry(
                        timestamp=datetime.now().isoformat(),
                        message=item
                    ))
                elif isinstance(item, dict):
                    # Already a dict - convert to LogEntry
                    converted.append(LogEntry(**item))
                elif isinstance(item, LogEntry):
                    # Already a LogEntry
                    converted.append(item)
            return converted
        return value
