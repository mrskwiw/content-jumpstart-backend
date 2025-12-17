"""Data models for content audit analysis"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ContentHealth(str, Enum):
    """Health status of content piece"""

    EXCELLENT = "excellent"  # High performance, no action needed
    GOOD = "good"  # Performing well, minor optimizations
    NEEDS_UPDATE = "needs_update"  # Outdated or underperforming
    NEEDS_REFRESH = "needs_refresh"  # Needs significant revision
    ARCHIVE = "archive"  # Remove or consolidate


class ContentType(str, Enum):
    """Type of content"""

    BLOG_POST = "blog_post"
    SOCIAL_POST = "social_post"
    EMAIL = "email"
    LANDING_PAGE = "landing_page"
    GUIDE = "guide"
    CASE_STUDY = "case_study"
    VIDEO = "video"
    INFOGRAPHIC = "infographic"
    WEBINAR = "webinar"
    OTHER = "other"


class PerformanceLevel(str, Enum):
    """Performance classification"""

    TOP_PERFORMER = "top_performer"  # Top 20%
    GOOD_PERFORMER = "good_performer"  # 20-50%
    AVERAGE = "average"  # 50-80%
    UNDERPERFORMING = "underperforming"  # Bottom 20%


class ContentPiece(BaseModel):
    """Individual content piece analysis"""

    title: str = Field(..., description="Content title")
    url: Optional[str] = Field(None, description="Content URL if available")
    content_type: ContentType = Field(..., description="Type of content")
    publish_date: Optional[str] = Field(None, description="When published")
    last_updated: Optional[str] = Field(None, description="Last update date")

    # Performance metrics
    performance_level: PerformanceLevel = Field(..., description="Performance classification")
    engagement_score: Optional[float] = Field(None, description="0-100 engagement score")
    traffic_estimate: Optional[str] = Field(
        None, description="Traffic estimate (e.g., 'Medium: 500/mo')"
    )

    # Content quality
    health_status: ContentHealth = Field(..., description="Overall health status")
    word_count: Optional[int] = Field(None, description="Content length")
    readability_score: Optional[str] = Field(None, description="Readability level")

    # SEO
    target_keyword: Optional[str] = Field(None, description="Primary keyword")
    keyword_ranking: Optional[str] = Field(None, description="Current ranking if known")
    seo_score: Optional[str] = Field(None, description="SEO optimization score")

    # Analysis
    strengths: List[str] = Field(default_factory=list, description="What works well")
    weaknesses: List[str] = Field(default_factory=list, description="What needs improvement")

    # Recommendation
    recommended_action: str = Field(
        ..., description="Keep, Update, Refresh, Archive, or Consolidate"
    )
    action_priority: str = Field(..., description="High, Medium, Low")
    specific_updates_needed: List[str] = Field(
        default_factory=list, description="Specific improvements to make"
    )


class TopicPerformance(BaseModel):
    """Performance analysis by topic"""

    topic: str = Field(..., description="Topic name")
    content_count: int = Field(..., description="Number of pieces on this topic")
    avg_performance: str = Field(..., description="Average performance level")
    top_performing_piece: str = Field(..., description="Best performing content")
    underperforming_pieces: List[str] = Field(
        default_factory=list, description="Pieces that need attention"
    )
    recommendation: str = Field(..., description="Topic strategy recommendation")


class ContentGap(BaseModel):
    """Gap in content coverage"""

    gap_description: str = Field(..., description="What's missing")
    content_type_needed: str = Field(..., description="Format to create")
    priority: str = Field(..., description="High, Medium, Low")
    reason: str = Field(..., description="Why this gap matters")


class RefreshOpportunity(BaseModel):
    """Content refresh opportunity"""

    content_title: str = Field(..., description="Content to refresh")
    last_updated: str = Field(..., description="When it was last updated")
    why_refresh: str = Field(..., description="Why it needs refresh")
    refresh_approach: str = Field(..., description="How to refresh it")
    estimated_impact: str = Field(..., description="Expected impact (High/Medium/Low)")
    estimated_effort: str = Field(..., description="Effort required (Small/Medium/Large)")


class RepurposeOpportunity(BaseModel):
    """Content repurposing opportunity"""

    source_content: str = Field(..., description="Original content")
    repurpose_into: str = Field(..., description="New format (e.g., 'Blog to LinkedIn carousel')")
    target_platform: str = Field(..., description="Where to publish")
    why_repurpose: str = Field(..., description="Value of repurposing")
    estimated_reach: str = Field(..., description="Potential audience size")


class ArchiveRecommendation(BaseModel):
    """Content to archive or consolidate"""

    content_title: str = Field(..., description="Content to archive")
    reason: str = Field(..., description="Why archive")
    action: str = Field(..., description="Archive, Consolidate, or Redirect")
    consolidate_into: Optional[str] = Field(None, description="If consolidating, into which piece")


class ContentAuditAnalysis(BaseModel):
    """Complete content audit report"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    analysis_date: str = Field(..., description="Date of analysis")
    total_content_pieces: int = Field(..., description="Total pieces analyzed")

    # Executive summary
    executive_summary: str = Field(..., description="High-level findings")
    overall_health_score: float = Field(..., description="0-100 overall content health")

    # Content inventory
    content_inventory: List[ContentPiece] = Field(
        default_factory=list, description="All content pieces analyzed"
    )

    # Performance analysis
    top_performers: List[ContentPiece] = Field(
        default_factory=list, description="Top 20% of content (5-10 pieces)"
    )
    underperformers: List[ContentPiece] = Field(
        default_factory=list, description="Bottom 20% needing attention (5-10 pieces)"
    )

    # Topic analysis
    topic_performance: List[TopicPerformance] = Field(
        default_factory=list, description="Performance by topic area"
    )

    # Gaps and opportunities
    content_gaps: List[ContentGap] = Field(
        default_factory=list, description="Missing content opportunities (5-10 items)"
    )

    refresh_opportunities: List[RefreshOpportunity] = Field(
        default_factory=list, description="Content to update (5-10 items)"
    )

    repurpose_opportunities: List[RepurposeOpportunity] = Field(
        default_factory=list, description="Repurposing opportunities (5-10 items)"
    )

    archive_recommendations: List[ArchiveRecommendation] = Field(
        default_factory=list, description="Content to archive or consolidate (3-5 items)"
    )

    # Strategic insights
    content_strengths: List[str] = Field(
        default_factory=list, description="What's working well (3-5 items)"
    )
    content_weaknesses: List[str] = Field(
        default_factory=list, description="What needs improvement (3-5 items)"
    )

    # Recommendations
    immediate_actions: List[str] = Field(
        default_factory=list, description="What to do first (3-5 items)"
    )

    thirty_day_plan: List[str] = Field(
        default_factory=list, description="30-day action plan (8-10 items)"
    )

    ninety_day_plan: List[str] = Field(
        default_factory=list, description="90-day strategic plan (10-12 items)"
    )

    # Metrics
    content_by_type: dict = Field(default_factory=dict, description="Count by content type")
    content_by_health: dict = Field(default_factory=dict, description="Count by health status")
    content_by_performance: dict = Field(
        default_factory=dict, description="Count by performance level"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Analytics",
                "industry": "B2B SaaS",
                "total_content_pieces": 45,
                "overall_health_score": 72.5,
                "top_performers": [
                    {
                        "title": "Complete Guide to Churn Prediction",
                        "performance_level": "top_performer",
                        "health_status": "excellent",
                    }
                ],
            }
        }
