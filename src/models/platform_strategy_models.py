"""Data models for platform strategy analysis"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class PlatformName(str, Enum):
    """Social media and content platforms"""

    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    MEDIUM = "medium"
    SUBSTACK = "substack"
    BLOG = "blog"
    EMAIL = "email"
    PODCAST = "podcast"


class ContentFormat(str, Enum):
    """Content format types"""

    SHORT_FORM = "short_form"  # <500 words, tweets, etc.
    LONG_FORM = "long_form"  # Articles, blog posts
    VIDEO = "video"  # Video content
    AUDIO = "audio"  # Podcasts, audio
    VISUAL = "visual"  # Images, infographics
    CAROUSEL = "carousel"  # Multi-image posts
    LIVE = "live"  # Live streams


class PlatformFit(str, Enum):
    """How well platform fits the business"""

    ESSENTIAL = "essential"  # Must-have platform
    RECOMMENDED = "recommended"  # Should use
    OPTIONAL = "optional"  # Nice to have
    NOT_RECOMMENDED = "not_recommended"  # Skip for now


class AudienceBehavior(BaseModel):
    """Target audience platform behavior"""

    platform: PlatformName = Field(..., description="Platform name")
    audience_present: bool = Field(..., description="Target audience is active here")
    activity_level: str = Field(..., description="High, Medium, Low")
    content_consumption_pattern: str = Field(..., description="How they consume content")
    engagement_style: str = Field(..., description="How they engage (comments, shares, DMs)")
    decision_maker_presence: str = Field(..., description="Are decision-makers here?")


class PlatformRecommendation(BaseModel):
    """Individual platform recommendation"""

    platform: PlatformName = Field(..., description="Platform name")
    fit_level: PlatformFit = Field(..., description="How essential this platform is")
    priority: str = Field(..., description="High, Medium, Low")

    # Rationale
    why_use: List[str] = Field(default_factory=list, description="Reasons to use this platform")
    why_not_use: List[str] = Field(default_factory=list, description="Concerns or limitations")

    # Strategy
    recommended_formats: List[ContentFormat] = Field(
        default_factory=list, description="Best content formats for this platform"
    )
    posting_frequency: str = Field(..., description="How often to post (e.g., '3-4x per week')")
    content_approach: str = Field(..., description="What type of content works here")

    # Expected outcomes
    primary_goal: str = Field(..., description="Main objective (awareness, leads, community)")
    success_metrics: List[str] = Field(default_factory=list, description="KPIs to track")
    estimated_effort: str = Field(..., description="Time/effort required (Small/Medium/Large)")
    expected_roi: str = Field(..., description="Expected return (High/Medium/Low)")


class PlatformMix(BaseModel):
    """Recommended platform portfolio"""

    primary_platforms: List[PlatformName] = Field(
        default_factory=list, description="Core platforms (1-2) - focus 70% of effort"
    )
    secondary_platforms: List[PlatformName] = Field(
        default_factory=list, description="Supporting platforms (1-2) - 25% of effort"
    )
    experimental_platforms: List[PlatformName] = Field(
        default_factory=list, description="Test platforms (0-1) - 5% of effort"
    )
    avoid_platforms: List[PlatformName] = Field(
        default_factory=list, description="Platforms to skip for now"
    )
    rationale: str = Field(..., description="Why this mix")


class ContentDistribution(BaseModel):
    """How to distribute content across platforms"""

    source_platform: PlatformName = Field(..., description="Where content originates")
    distribution_flow: List[str] = Field(
        default_factory=list, description="How content flows (e.g., 'Blog → LinkedIn → Twitter')"
    )
    repurposing_strategy: str = Field(..., description="How to adapt content for each platform")
    time_savings: str = Field(..., description="Efficiency gains from this approach")


class QuickWin(BaseModel):
    """Immediate action to get started"""

    platform: PlatformName = Field(..., description="Which platform")
    action: str = Field(..., description="Specific action to take")
    timeframe: str = Field(..., description="When to complete (e.g., 'This week')")
    expected_outcome: str = Field(..., description="What success looks like")


class PlatformStrategyAnalysis(BaseModel):
    """Complete platform strategy report"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    target_audience: str = Field(..., description="Primary audience")
    analysis_date: str = Field(..., description="Date of analysis")

    # Executive summary
    executive_summary: str = Field(..., description="High-level platform recommendations")
    recommended_platform_mix: PlatformMix = Field(..., description="Core platform portfolio")

    # Audience analysis
    audience_behavior: List[AudienceBehavior] = Field(
        default_factory=list, description="Where target audience is active"
    )

    # Platform recommendations
    platform_recommendations: List[PlatformRecommendation] = Field(
        default_factory=list, description="Detailed recommendations for each relevant platform"
    )

    # Content strategy
    content_distribution: ContentDistribution = Field(
        ..., description="How to distribute and repurpose content"
    )

    # Current state analysis (if provided)
    current_platforms: List[str] = Field(
        default_factory=list, description="Platforms currently using"
    )
    current_strengths: List[str] = Field(
        default_factory=list, description="What's working in current strategy"
    )
    current_gaps: List[str] = Field(
        default_factory=list, description="What's missing in current strategy"
    )

    # Implementation
    quick_wins: List[QuickWin] = Field(
        default_factory=list, description="Immediate actions to take (3-5 items)"
    )

    thirty_day_plan: List[str] = Field(
        default_factory=list, description="30-day implementation plan (5-7 items)"
    )

    ninety_day_plan: List[str] = Field(
        default_factory=list, description="90-day strategic plan (8-10 items)"
    )

    # Strategic insights
    key_insights: List[str] = Field(
        default_factory=list, description="Strategic insights about platform selection (3-5 items)"
    )

    common_mistakes_to_avoid: List[str] = Field(
        default_factory=list, description="Platform mistakes to avoid (3-5 items)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Analytics",
                "industry": "B2B SaaS",
                "target_audience": "Customer success teams",
                "recommended_platform_mix": {
                    "primary_platforms": ["linkedin"],
                    "secondary_platforms": ["blog", "email"],
                    "experimental_platforms": [],
                    "avoid_platforms": ["tiktok", "instagram"],
                },
            }
        }
