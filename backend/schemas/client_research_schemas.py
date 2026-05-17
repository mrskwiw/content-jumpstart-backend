"""Pydantic schemas for the Client Research API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ClientResearchRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Business name")
    location: str = Field(..., min_length=1, max_length=200, description="City, state or region")
    website: Optional[str] = Field(
        None, max_length=500, description="Optional — adds a site-specific search"
    )


class ClientResearchResponse(BaseModel):
    brief: Dict[str, Any]  # snake_case ClientBrief fields
    confidence: Dict[str, float]  # field_name → 0.0–1.0
    sources: List[str]  # unique URLs used
    duration_seconds: float
    stub_mode: bool = False
    warning: Optional[str] = None
    credit_cost: int = 200
