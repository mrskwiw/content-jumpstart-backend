"""Data models for market trends research"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class TrendMomentum(str, Enum):
    """Trend momentum classification"""

    RISING = "rising"  # Growing rapidly
    EMERGING = "emerging"  # Just starting to gain traction
    STABLE = "stable"  # Consistent interest over time
    DECLINING = "declining"  # Losing momentum
    SEASONAL = "seasonal"  # Cyclical pattern


class TrendRelevance(str, Enum):
    """How relevant is this trend to the business"""

    HIGH = "high"  # Directly relevant
    MEDIUM = "medium"  # Somewhat relevant
    LOW = "low"  # Tangentially relevant


class Trend(BaseModel):
    """Individual trend or topic"""

    topic: str = Field(..., description="Trend topic or keyword")
    description: str = Field(..., description="What this trend is about")
    momentum: TrendMomentum = Field(..., description="Trend momentum/trajectory")
    relevance: TrendRelevance = Field(..., description="Relevance to business")

    # Metrics
    popularity_score: float = Field(..., ge=0.0, le=10.0, description="Popularity score (1-10)")
    growth_rate: str = Field(..., description="Growth rate estimate (e.g., '+150% YoY')")

    # Context
    key_drivers: List[str] = Field(default_factory=list, description="What's driving this trend")
    target_audience: List[str] = Field(default_factory=list, description="Who cares about this")
    related_keywords: List[str] = Field(default_factory=list, description="Related search terms")

    # Opportunity
    content_angles: List[str] = Field(
        default_factory=list, description="How to create content around this"
    )
    urgency: str = Field(..., description="Time sensitivity (High/Medium/Low)")


class TrendCategory(BaseModel):
    """Group of related trends"""

    category_name: str = Field(..., description="Category name")
    description: str = Field(..., description="What this category covers")
    trends: List[Trend] = Field(default_factory=list, description="Trends in this category")
    category_momentum: TrendMomentum = Field(..., description="Overall category momentum")


class EmergingConversation(BaseModel):
    """New conversation or debate emerging in industry"""

    topic: str = Field(..., description="Conversation topic")
    description: str = Field(..., description="What people are discussing")
    key_perspectives: List[str] = Field(default_factory=list, description="Different viewpoints")
    thought_leaders: List[str] = Field(default_factory=list, description="Who's talking about this")
    content_opportunity: str = Field(..., description="How to contribute to conversation")


class SeasonalTrend(BaseModel):
    """Recurring seasonal trend"""

    topic: str = Field(..., description="Seasonal topic")
    timing: str = Field(..., description="When it peaks (e.g., 'Q4', 'January-February')")
    description: str = Field(..., description="What happens during this season")
    preparation_timeline: str = Field(..., description="When to start creating content")


class TrendReport(BaseModel):
    """Complete market trends research report"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    analysis_date: str = Field(..., description="Date of analysis")

    # Trends by category
    trend_categories: List[TrendCategory] = Field(
        default_factory=list, description="Categorized trends"
    )

    # Top trends
    top_rising_trends: List[Trend] = Field(
        default_factory=list, description="Fastest growing trends"
    )
    top_relevant_trends: List[Trend] = Field(
        default_factory=list, description="Most relevant trends"
    )

    # Emerging conversations
    emerging_conversations: List[EmergingConversation] = Field(
        default_factory=list, description="New industry conversations"
    )

    # Seasonal trends
    seasonal_trends: List[SeasonalTrend] = Field(
        default_factory=list, description="Recurring seasonal patterns"
    )

    # Content recommendations
    immediate_opportunities: List[str] = Field(
        default_factory=list, description="Trends to capitalize on now (3-5 items)"
    )

    upcoming_opportunities: List[str] = Field(
        default_factory=list, description="Trends to prepare for (3-5 items)"
    )

    # Insights
    market_summary: str = Field(..., description="Overview of market trends")
    key_themes: List[str] = Field(default_factory=list, description="Overarching themes")

    # Warnings
    declining_topics: List[str] = Field(default_factory=list, description="Topics losing relevance")

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Analytics",
                "industry": "B2B SaaS",
                "top_rising_trends": [
                    {
                        "topic": "AI-powered customer analytics",
                        "momentum": "rising",
                        "relevance": "high",
                        "popularity_score": 8.5,
                        "growth_rate": "+200% YoY",
                    }
                ],
            }
        }
