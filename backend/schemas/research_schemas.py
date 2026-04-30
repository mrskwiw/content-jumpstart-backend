"""
Pydantic validation schemas for research tool parameters.

Provides type-safe input validation with length limits, sanitization,
and security constraints for all research tools.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict


class VoiceAnalysisParams(BaseModel):
    """Parameters for Voice Analysis research tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content_samples: Optional[List[str]] = Field(
        None,
        description="5-30 samples of client's existing writing (minimum 50 characters each). Auto-generates from business description if not provided.",
    )

    @field_validator("content_samples")
    @classmethod
    def validate_samples(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate each sample meets minimum length and size limits."""
        # Allow None - will auto-generate from business description
        if v is None or len(v) == 0:
            return None

        if not 5 <= len(v) <= 30:
            raise ValueError("Must provide between 5-30 content samples")

        valid_samples = []
        for idx, sample in enumerate(v):
            # Strip whitespace
            sample = sample.strip()

            # Check minimum length
            if len(sample) < 50:
                raise ValueError(f"Sample {idx + 1} is too short (minimum 50 characters)")

            # Check maximum length (prevent DoS)
            if len(sample) > 10000:
                raise ValueError(f"Sample {idx + 1} is too long (maximum 10,000 characters)")

            valid_samples.append(sample)

        return valid_samples


class SEOKeywordParams(BaseModel):
    """Parameters for SEO Keyword Research tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    main_topics: Optional[List[str]] = Field(
        None,
        description="1-10 main topics for keyword research (optional - auto-generates from business profile if not provided)",
    )

    negative_keywords: Optional[List[str]] = Field(
        None,
        description="Keywords, topics, or brand names to exclude from recommendations (optional, max 50)",
    )

    @field_validator("main_topics")
    @classmethod
    def validate_topics(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate topics list if provided."""
        # Allow None - will trigger auto-generation
        if v is None:
            return None
        if len(v) == 0:
            return None  # treat empty list same as None — auto-generate from business profile

        valid_topics = []
        for idx, topic in enumerate(v):
            topic = topic.strip()

            if len(topic) < 3:
                continue  # skip too-short topics rather than blocking the whole run

            if len(topic) > 100:
                topic = topic[:100]  # truncate rather than reject

            valid_topics.append(topic)

        if not valid_topics:
            return None  # all items were invalid — fall back to auto-generation

        # Silently cap at 10 — never raise; the tool itself also caps at 10
        return valid_topics[:10]

    @field_validator("negative_keywords")
    @classmethod
    def validate_negative_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate negative keywords list if provided."""
        if v is None or len(v) == 0:
            return None

        valid_keywords = []
        for idx, keyword in enumerate(v):
            keyword = keyword.strip()

            if len(keyword) < 2:
                continue  # skip too-short keywords

            if len(keyword) > 100:
                keyword = keyword[:100]  # truncate rather than reject

            valid_keywords.append(keyword)

        if not valid_keywords:
            return None  # all items were invalid

        # Silently cap at 50
        return valid_keywords[:50]


class CompetitiveAnalysisParams(BaseModel):
    """Parameters for Competitive Analysis tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    competitors: Optional[List[str]] = Field(
        None,
        description="1-5 competitor names to analyze (auto-populated from client profile if not provided)",
    )

    @field_validator("competitors")
    @classmethod
    def validate_competitors(cls, v: List[str]) -> Optional[List[str]]:
        """Validate competitors list."""
        if v is None:
            return None
        if len(v) == 0:
            return None  # treat empty list same as None — auto-populate from client profile
        if not 1 <= len(v) <= 5:
            raise ValueError("Must provide between 1-5 competitors")

        valid_competitors = []
        for idx, competitor in enumerate(v):
            competitor = competitor.strip()

            if len(competitor) < 2:
                raise ValueError(f"Competitor {idx + 1} is too short (minimum 2 characters)")

            if len(competitor) > 100:
                raise ValueError(f"Competitor {idx + 1} is too long (maximum 100 characters)")

            valid_competitors.append(competitor)

        return valid_competitors


class ContentGapParams(BaseModel):
    """Parameters for Content Gap Analysis tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    current_content_topics: str = Field(
        default="",
        description="Description of current content topics (optional - auto-generates from SEO keywords or business profile if empty)",
    )

    @field_validator("current_content_topics")
    @classmethod
    def validate_topics_text(cls, v: str) -> str:
        """Validate topics text length (optional field - empty is valid)."""
        v = v.strip()

        # Allow empty - will auto-generate from SEO keywords or business profile
        if len(v) == 0:
            return v

        # If provided, enforce minimum length
        if len(v) < 10:
            raise ValueError("Current content topics is too short (minimum 10 characters)")

        if len(v) > 5000:
            raise ValueError("Current content topics is too long (maximum 5,000 characters)")

        return v


class ContentPiece(BaseModel):
    """Individual content piece for Content Audit."""

    model_config = ConfigDict(str_strip_whitespace=True)

    url: Optional[str] = Field(None, description="URL of the content (optional, max 2000 chars)")
    title: str = Field(..., min_length=3, max_length=500, description="Content title")
    type: Optional[str] = Field(None, max_length=50, description="Content type (blog, video, etc.)")
    publish_date: Optional[str] = Field(
        None, max_length=50, description="Publish date (ISO format preferred)"
    )
    performance_metrics: Optional[str] = Field(
        None,
        max_length=1000,
        description="Performance metrics (views, engagement, etc.)",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format (basic check)."""
        if v is None:
            return None

        v = v.strip()

        # Basic URL validation
        if not v.startswith(("http://", "https://", "www.")):
            raise ValueError("URL must start with http://, https://, or www.")

        if len(v) > 2000:
            raise ValueError("URL is too long (maximum 2,000 characters)")

        return v


class ContentAuditParams(BaseModel):
    """Parameters for Content Audit tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content_inventory: Optional[List[ContentPiece]] = Field(
        None,
        description="1-100 content pieces to audit. Auto-generates placeholder from business description if not provided.",
    )

    @field_validator("content_inventory")
    @classmethod
    def validate_inventory(cls, v: Optional[List[ContentPiece]]) -> Optional[List[ContentPiece]]:
        """Validate content inventory."""
        # Allow None - will auto-generate placeholder
        if v is None:
            return None
        if len(v) == 0:
            raise ValueError("Must provide between 1-100 content pieces")

        if not 1 <= len(v) <= 100:
            raise ValueError("Must provide between 1-100 content pieces")

        return v


class MarketTrendsParams(BaseModel):
    """Parameters for Market Trends Research tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    industry: Optional[str] = Field(
        None,
        max_length=200,
        description="Industry for trend research (uses client profile if not provided)",
    )

    focus_areas: Optional[List[str]] = Field(
        None, description="Specific areas to emphasize (optional, max 10)"
    )

    location: Optional[str] = Field(
        None,
        max_length=200,
        description="Geographic location for industry review analysis (optional, e.g., 'San Francisco, CA')",
    )

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: Optional[str]) -> Optional[str]:
        """Validate industry field."""
        if v is None:
            return None

        v = v.strip()

        if len(v) < 3:
            raise ValueError("Industry is too short (minimum 3 characters)")

        if len(v) > 200:
            raise ValueError("Industry is too long (maximum 200 characters)")

        return v

    @field_validator("focus_areas")
    @classmethod
    def validate_focus_areas(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate focus areas list."""
        if v is None:
            return None

        if len(v) > 10:
            raise ValueError("Maximum 10 focus areas allowed")

        valid_areas = []
        for idx, area in enumerate(v):
            area = area.strip()

            if len(area) < 3:
                raise ValueError(f"Focus area {idx + 1} is too short (minimum 3 characters)")

            if len(area) > 100:
                raise ValueError(f"Focus area {idx + 1} is too long (maximum 100 characters)")

            valid_areas.append(area)

        return valid_areas


class PlatformStrategyParams(BaseModel):
    """Parameters for Platform Strategy tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    current_platforms: Optional[List[str]] = Field(
        None, description="Current platforms for content distribution (optional, max 10)"
    )

    content_goals: Optional[str] = Field(
        None,
        description="Specific business objectives for content (optional, max 1000 chars)",
    )

    @field_validator("current_platforms")
    @classmethod
    def validate_platforms(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate platforms list."""
        if v is None:
            return None

        if len(v) > 10:
            raise ValueError("Maximum 10 platforms allowed")

        valid_platforms = []
        for idx, platform in enumerate(v):
            platform = platform.strip()

            if len(platform) < 2:
                raise ValueError(f"Platform {idx + 1} is too short (minimum 2 characters)")

            if len(platform) > 50:
                raise ValueError(f"Platform {idx + 1} is too long (maximum 50 characters)")

            valid_platforms.append(platform)

        return valid_platforms

    @field_validator("content_goals")
    @classmethod
    def validate_goals(cls, v: Optional[str]) -> Optional[str]:
        """Validate content goals field."""
        if v is None:
            return None

        v = v.strip()

        if len(v) < 3:
            raise ValueError("Content goals is too short (minimum 3 characters)")

        if len(v) > 1000:
            raise ValueError("Content goals is too long (maximum 1,000 characters)")

        return v


class ContentCalendarParams(BaseModel):
    """Parameters for Content Calendar Strategy tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    calendar_length_days: Optional[int] = Field(
        90,  # Default 90 days
        ge=30,
        le=365,
        description="Length of content calendar in days (30-365)",
    )

    posting_frequency: Optional[str] = Field(
        None,
        max_length=100,
        description="Desired posting frequency (e.g., 'daily', '3x per week')",
    )


class AudienceResearchParams(BaseModel):
    """Parameters for Audience Research tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    additional_context: Optional[str] = Field(
        None,
        description="Additional context about target audience (optional, max 2000 chars)",
    )

    @field_validator("additional_context")
    @classmethod
    def validate_context(cls, v: Optional[str]) -> Optional[str]:
        """Validate additional context field."""
        if v is None:
            return None

        v = v.strip()

        if len(v) > 2000:
            raise ValueError("Additional context is too long (maximum 2,000 characters)")

        return v


class ICPWorkshopParams(BaseModel):
    """Parameters for ICP Development Workshop tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    workshop_focus: Optional[str] = Field(
        None,
        max_length=500,
        description="Specific areas to focus on during workshop (optional)",
    )


class StoryMiningParams(BaseModel):
    """Parameters for Story Mining Interview tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    story_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Type of stories to extract (e.g., 'customer success', 'transformation')",
    )

    customer_segment: Optional[str] = Field(
        None,
        max_length=200,
        description="Specific customer segment to focus on (optional)",
    )


class BrandArchetypeParams(BaseModel):
    """Parameters for Brand Archetype Assessment tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # No additional parameters needed - uses client profile
    pass


class DetermineCompetitorsParams(BaseModel):
    """Parameters for Determine Competitors tool"""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Optional fields - user can provide or override client profile
    industry: Optional[str] = Field(
        None,
        max_length=200,
        description="Industry/vertical (e.g., 'B2B SaaS', 'Healthcare')",
    )

    location: Optional[str] = Field(
        None,
        max_length=200,
        description="Geographic market/region (e.g., 'United States', 'Global', 'San Francisco Bay Area')",
    )

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: Optional[str]) -> Optional[str]:
        """Validate industry field"""
        if v is None:
            return None
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Industry is too short (minimum 3 characters)")
        if len(v) > 200:
            raise ValueError("Industry is too long (maximum 200 characters)")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        """Validate location field"""
        if v is None:
            return None
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Location is too short (minimum 2 characters)")
        if len(v) > 200:
            raise ValueError("Location is too long (maximum 200 characters)")
        return v


class BusinessReportInput(BaseModel):
    """Parameters for Business Report research tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: Optional[str] = Field(
        None,
        max_length=200,
        description="Name of the company to analyze. Auto-populates from client name if not provided.",
    )

    location: Optional[str] = Field(
        None,
        max_length=200,
        description="Location of the company (city, state or city, country). Auto-populates from client location if not provided.",
    )

    max_web_results: Optional[int] = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of web search results to analyze (default: 10)",
    )

    max_reviews: Optional[int] = Field(
        50,
        ge=1,
        le=200,
        description="Maximum number of Google Maps reviews to analyze (default: 50)",
    )

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate company name field."""
        # Allow None - will auto-populate from client name
        if v is None:
            return None

        v = v.strip()

        if len(v) == 0:
            return None  # Empty string becomes None for auto-population

        if len(v) < 2:
            raise ValueError("Company name is too short (minimum 2 characters)")

        if len(v) > 200:
            raise ValueError("Company name is too long (maximum 200 characters)")

        return v

    @field_validator("location")
    @classmethod
    def validate_location_field(cls, v: Optional[str]) -> Optional[str]:
        """Validate location field."""
        # Allow None - will auto-populate from client location
        if v is None:
            return None

        v = v.strip()

        if len(v) == 0:
            return None  # Empty string becomes None for auto-population

        if len(v) < 2:
            raise ValueError("Location is too short (minimum 2 characters)")

        if len(v) > 200:
            raise ValueError("Location is too long (maximum 200 characters)")

        return v


# ==================== Research Result Response Schemas ====================


class ResearchResultResponse(BaseModel):
    """Response schema for research result."""

    id: str
    user_id: str = Field(..., serialization_alias="userId")
    client_id: str = Field(..., serialization_alias="clientId")
    project_id: Optional[str] = Field(default=None, serialization_alias="projectId")
    tool_name: str = Field(..., serialization_alias="toolName")
    tool_label: Optional[str] = Field(default=None, serialization_alias="toolLabel")
    tool_price: Optional[float] = Field(
        default=None, serialization_alias="toolPrice"
    )  # Business model price
    params: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = Field(default=None, serialization_alias="errorMessage")
    duration_seconds: Optional[float] = Field(default=None, serialization_alias="durationSeconds")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    # Token usage tracking (actual API consumption)
    input_tokens: Optional[int] = Field(default=None, serialization_alias="inputTokens")
    output_tokens: Optional[int] = Field(default=None, serialization_alias="outputTokens")
    cache_creation_tokens: Optional[int] = Field(
        default=None, serialization_alias="cacheCreationTokens"
    )
    cache_read_tokens: Optional[int] = Field(default=None, serialization_alias="cacheReadTokens")
    actual_cost_usd: Optional[float] = Field(
        default=None, serialization_alias="actualCostUsd"
    )  # Actual API cost

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
    )

    @field_serializer("created_at")
    def serialize_datetime(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize datetime with UTC timezone."""
        if value is None:
            return None
        from datetime import timezone

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()


class ResearchResultListResponse(BaseModel):
    """Response schema for list of research results."""

    results: List[ResearchResultResponse]
    total: int
    project_id: Optional[str] = Field(default=None, serialization_alias="projectId")
    client_id: Optional[str] = Field(default=None, serialization_alias="clientId")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
    )
