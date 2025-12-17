"""Data models for content gap analysis"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class GapPriority(str, Enum):
    """Priority level for addressing content gap"""

    CRITICAL = "critical"  # High search volume, no coverage
    HIGH = "high"  # Strong opportunity, easy win
    MEDIUM = "medium"  # Good opportunity, moderate effort
    LOW = "low"  # Nice to have, lower impact


class GapType(str, Enum):
    """Type of content gap"""

    TOPIC = "topic"  # Missing topic entirely
    FORMAT = "format"  # Have topic, missing format (video, checklist, etc.)
    DEPTH = "depth"  # Have topic, need more depth
    FRESHNESS = "freshness"  # Content outdated
    STAGE = "stage"  # Missing buyer journey stage
    AUDIENCE_SEGMENT = "audience_segment"  # Missing segment coverage


class ContentGap(BaseModel):
    """Individual content gap"""

    gap_title: str = Field(..., description="What's missing")
    gap_type: GapType = Field(..., description="Type of gap")
    priority: GapPriority = Field(..., description="Priority level")

    # Context
    description: str = Field(..., description="Why this gap matters")
    search_volume: str = Field(..., description="Estimated search volume (e.g., 'High: 5K/mo')")
    competition: str = Field(
        ..., description="Competitor coverage (e.g., '3 of 5 competitors cover this')"
    )

    # Opportunity
    business_impact: str = Field(..., description="How this helps business")
    target_audience: str = Field(..., description="Who needs this content")
    buyer_stage: str = Field(..., description="Awareness/Consideration/Decision")

    # Implementation
    content_angle: str = Field(..., description="Recommended approach")
    example_topics: List[str] = Field(
        default_factory=list, description="3-5 specific topics to cover"
    )
    estimated_effort: str = Field(..., description="Small/Medium/Large")


class CompetitorContentAnalysis(BaseModel):
    """Competitor's content strengths"""

    competitor_name: str = Field(..., description="Competitor name")
    content_strengths: List[str] = Field(default_factory=list, description="What they do well")
    popular_topics: List[str] = Field(
        default_factory=list, description="Their top-performing topics"
    )
    formats_used: List[str] = Field(default_factory=list, description="Content formats they use")
    gaps_in_their_content: List[str] = Field(
        default_factory=list, description="What they're missing (your advantage)"
    )


class BuyerJourneyGap(BaseModel):
    """Missing content for buyer journey stage"""

    stage: str = Field(..., description="Awareness/Consideration/Decision")
    current_coverage: str = Field(..., description="What you have now")
    gap_description: str = Field(..., description="What's missing")
    recommended_content: List[str] = Field(
        default_factory=list, description="3-5 content pieces to create"
    )
    priority: GapPriority = Field(..., description="Priority level")


class FormatGap(BaseModel):
    """Missing content format"""

    format_name: str = Field(..., description="Blog, video, checklist, template, etc.")
    why_needed: str = Field(..., description="Why this format matters")
    topics_to_cover: List[str] = Field(
        default_factory=list, description="Topics that work well in this format"
    )
    estimated_impact: str = Field(..., description="Expected impact (High/Medium/Low)")


class ContentGapAnalysis(BaseModel):
    """Complete content gap analysis report"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    analysis_date: str = Field(..., description="Date of analysis")

    # Critical gaps
    critical_gaps: List[ContentGap] = Field(
        default_factory=list, description="Must-create content (3-5 items)"
    )

    # High-priority gaps
    high_priority_gaps: List[ContentGap] = Field(
        default_factory=list, description="Strong opportunities (5-7 items)"
    )

    # Medium-priority gaps
    medium_priority_gaps: List[ContentGap] = Field(
        default_factory=list, description="Good opportunities (5-7 items)"
    )

    # Competitor analysis
    competitor_analysis: List[CompetitorContentAnalysis] = Field(
        default_factory=list, description="Analysis of each competitor's content"
    )

    # Buyer journey gaps
    buyer_journey_gaps: List[BuyerJourneyGap] = Field(
        default_factory=list, description="Gaps by buyer journey stage"
    )

    # Format gaps
    format_gaps: List[FormatGap] = Field(
        default_factory=list, description="Missing content formats"
    )

    # Quick wins
    quick_wins: List[str] = Field(
        default_factory=list, description="Easy content to create with high impact (5-7 items)"
    )

    # Long-term opportunities
    long_term_opportunities: List[str] = Field(
        default_factory=list, description="Strategic content initiatives (3-5 items)"
    )

    # Executive summary
    executive_summary: str = Field(..., description="Overview of gap analysis")
    total_gaps_identified: int = Field(..., description="Total number of gaps")
    estimated_opportunity: str = Field(
        ..., description="Business opportunity (e.g., '$50K+ annual traffic value')"
    )

    # Recommendations
    immediate_actions: List[str] = Field(
        default_factory=list, description="What to do first (3-5 items)"
    )

    ninety_day_roadmap: List[str] = Field(
        default_factory=list, description="90-day content creation plan (10-12 items)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Analytics",
                "industry": "B2B SaaS",
                "total_gaps_identified": 23,
                "critical_gaps": [
                    {
                        "gap_title": "Getting Started Guide",
                        "gap_type": "topic",
                        "priority": "critical",
                        "search_volume": "High: 4.5K/mo",
                        "business_impact": "Main entry point for new users",
                    }
                ],
            }
        }
