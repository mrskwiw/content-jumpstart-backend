"""Data models for competitive analysis"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class CompetitorStrength(str, Enum):
    """Competitor strength categories"""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class ContentType(str, Enum):
    """Types of content competitors produce"""

    BLOG_POSTS = "blog_posts"
    SOCIAL_MEDIA = "social_media"
    VIDEO = "video"
    PODCASTS = "podcasts"
    WEBINARS = "webinars"
    EBOOKS = "ebooks"
    CASE_STUDIES = "case_studies"
    WHITEPAPERS = "whitepapers"


class CompetitorProfile(BaseModel):
    """Profile of a single competitor"""

    name: str = Field(..., description="Competitor name or URL")
    positioning: str = Field(..., description="How they position themselves")
    target_audience: str = Field(..., description="Who they target")

    # Content strategy
    content_types: List[ContentType] = Field(
        default_factory=list, description="Types of content they produce"
    )
    content_frequency: str = Field(
        ..., description="How often they publish (e.g., '3-4x per week')"
    )
    content_topics: List[str] = Field(default_factory=list, description="Main topics they cover")

    # Voice and tone
    brand_voice: str = Field(..., description="Their brand voice description")
    tone_descriptors: List[str] = Field(default_factory=list, description="Tone characteristics")

    # Strengths and weaknesses
    strengths: List[str] = Field(default_factory=list, description="What they do well")
    weaknesses: List[str] = Field(default_factory=list, description="Where they fall short")

    # Engagement indicators
    estimated_reach: str = Field(..., description="Estimated audience size/reach")
    engagement_level: CompetitorStrength = Field(..., description="Estimated engagement level")


class ContentGap(BaseModel):
    """Opportunity where competitors are weak"""

    topic: str = Field(..., description="Topic/area with gap")
    description: str = Field(..., description="Description of the gap")
    opportunity_score: float = Field(..., ge=0.0, le=10.0, description="Opportunity score (1-10)")
    competitors_missing: List[str] = Field(
        default_factory=list, description="Competitors not covering this"
    )
    suggested_content: List[str] = Field(
        default_factory=list, description="Content ideas to fill gap"
    )


class DifferentiationStrategy(BaseModel):
    """Way to differentiate from competitors"""

    strategy_name: str = Field(..., description="Name of strategy")
    description: str = Field(..., description="How to implement")
    difficulty: str = Field(..., description="Implementation difficulty (Low/Medium/High)")
    potential_impact: str = Field(..., description="Expected impact (Low/Medium/High)")
    examples: List[str] = Field(default_factory=list, description="Specific examples")


class MarketPosition(BaseModel):
    """Where you stand relative to competitors"""

    positioning_statement: str = Field(..., description="Your recommended positioning")
    unique_angles: List[str] = Field(default_factory=list, description="Unique angles to emphasize")
    competitive_advantages: List[str] = Field(default_factory=list, description="Your advantages")
    areas_to_improve: List[str] = Field(
        default_factory=list, description="Areas needing improvement"
    )


class CompetitiveAnalysis(BaseModel):
    """Complete competitive analysis results"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    analysis_date: str = Field(..., description="Date of analysis")

    # Competitor profiles
    competitors: List[CompetitorProfile] = Field(
        default_factory=list, description="Analyzed competitors"
    )

    # Market landscape
    market_summary: str = Field(..., description="Overview of competitive landscape")
    market_saturation: str = Field(..., description="How crowded the market is")

    # Opportunities
    content_gaps: List[ContentGap] = Field(
        default_factory=list, description="Content gap opportunities"
    )
    quick_wins: List[str] = Field(default_factory=list, description="Immediate opportunities")

    # Strategy recommendations
    differentiation_strategies: List[DifferentiationStrategy] = Field(
        default_factory=list, description="Ways to differentiate"
    )

    # Positioning
    recommended_position: MarketPosition = Field(..., description="Recommended market positioning")

    # Action items
    priority_actions: List[str] = Field(default_factory=list, description="Top 5 actions to take")

    # Threats
    competitive_threats: List[str] = Field(
        default_factory=list, description="Potential threats to watch"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Analytics",
                "industry": "B2B SaaS",
                "competitors": [
                    {
                        "name": "ChurnZero",
                        "positioning": "Customer success platform for SaaS",
                        "content_frequency": "2-3x per week",
                        "strengths": ["Strong brand", "Comprehensive features"],
                        "weaknesses": ["Generic content", "Limited thought leadership"],
                    }
                ],
            }
        }
