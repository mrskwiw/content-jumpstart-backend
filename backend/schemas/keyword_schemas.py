"""Pydantic schemas for client keyword CRUD."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class KeywordType(str, Enum):
    primary = "primary"
    secondary = "secondary"
    negative = "negative"
    quick_win = "quick_win"


class KeywordSource(str, Enum):
    research_tool = "research_tool"
    manual = "manual"


class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=200)
    keyword_type: KeywordType
    search_intent: Optional[str] = None
    difficulty: Optional[str] = None
    monthly_volume: Optional[str] = None
    relevance_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_negative_keyword_length(self) -> "KeywordCreate":
        # Negative keywords have a tighter 100-char cap (mirrors SEOKeywordParams).
        # Must run as a model_validator so keyword_type is available.
        if self.keyword_type == KeywordType.negative and len(self.keyword) > 100:
            raise ValueError("Negative keywords must be 100 characters or fewer")
        return self


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = Field(None, min_length=2, max_length=200)
    search_intent: Optional[str] = None
    difficulty: Optional[str] = None
    monthly_volume: Optional[str] = None
    relevance_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    notes: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class KeywordBulkUpsert(BaseModel):
    keywords: List[KeywordCreate] = Field(..., max_length=50)


class KeywordResponse(BaseModel):
    id: int
    client_id: str
    research_result_id: Optional[str] = None
    keyword: str
    keyword_type: str
    search_intent: Optional[str] = None
    difficulty: Optional[str] = None
    monthly_volume: Optional[str] = None
    relevance_score: Optional[float] = None
    quality_score: Optional[float] = None
    source: str
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KeywordListResponse(BaseModel):
    primary: List[KeywordResponse] = []
    secondary: List[KeywordResponse] = []
    negative: List[KeywordResponse] = []
    quick_win: List[KeywordResponse] = []
    total: int = 0


class KeywordImportResponse(BaseModel):
    imported: int
    skipped: int
    deactivated: int = 0
    message: str
