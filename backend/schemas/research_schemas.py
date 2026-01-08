"""
Pydantic validation schemas for research tool parameters.

Provides type-safe input validation with length limits, sanitization,
and security constraints for all research tools.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class VoiceAnalysisParams(BaseModel):
    """Parameters for Voice Analysis research tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content_samples: List[str] = Field(
        ...,
        description="5-30 samples of client's existing writing (minimum 50 characters each)",
    )

    @field_validator("content_samples")
    @classmethod
    def validate_samples(cls, v: List[str]) -> List[str]:
        """Validate each sample meets minimum length and size limits."""
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

    main_topics: List[str] = Field(
        ...,
        description="1-10 main topics for keyword research",
    )

    @field_validator("main_topics")
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
        """Validate topics list."""
        if not 1 <= len(v) <= 10:
            raise ValueError("Must provide between 1-10 main topics")

        valid_topics = []
        for idx, topic in enumerate(v):
            topic = topic.strip()

            if len(topic) < 3:
                raise ValueError(f"Topic {idx + 1} is too short (minimum 3 characters)")

            if len(topic) > 100:
                raise ValueError(f"Topic {idx + 1} is too long (maximum 100 characters)")

            valid_topics.append(topic)

        return valid_topics


class CompetitiveAnalysisParams(BaseModel):
    """Parameters for Competitive Analysis tool."""

    model_config = ConfigDict(str_strip_whitespace=True)

    competitors: List[str] = Field(
        ...,
        description="1-5 competitor names to analyze",
    )

    @field_validator("competitors")
    @classmethod
    def validate_competitors(cls, v: List[str]) -> List[str]:
        """Validate competitors list."""
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
        ...,
        description="Description of current content topics (10-5000 characters)",
    )

    @field_validator("current_content_topics")
    @classmethod
    def validate_topics_text(cls, v: str) -> str:
        """Validate topics text length."""
        v = v.strip()

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

    content_inventory: List[ContentPiece] = Field(
        ...,
        description="1-100 content pieces to audit",
    )

    @field_validator("content_inventory")
    @classmethod
    def validate_inventory(cls, v: List[ContentPiece]) -> List[ContentPiece]:
        """Validate content inventory."""
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

        if len(v) < 10:
            raise ValueError("Content goals is too short (minimum 10 characters)")

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
