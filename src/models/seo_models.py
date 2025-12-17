"""Data models for SEO keyword research"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class SearchIntent(str, Enum):
    """Types of search intent"""

    INFORMATIONAL = "informational"  # Learning, how-to, understanding
    NAVIGATIONAL = "navigational"  # Finding specific site/brand
    COMMERCIAL = "commercial"  # Researching before buying
    TRANSACTIONAL = "transactional"  # Ready to purchase/convert


class KeywordDifficulty(str, Enum):
    """Keyword competition difficulty"""

    LOW = "low"  # Easy to rank for
    MEDIUM = "medium"  # Moderate competition
    HIGH = "high"  # Highly competitive


class Keyword(BaseModel):
    """Individual keyword with metrics"""

    keyword: str = Field(..., description="The keyword or phrase")
    search_intent: SearchIntent = Field(..., description="Primary search intent")
    difficulty: KeywordDifficulty = Field(..., description="Estimated ranking difficulty")
    monthly_volume_estimate: str = Field(..., description="Estimated monthly searches (range)")
    relevance_score: float = Field(..., ge=0.0, le=10.0, description="Relevance to business (1-10)")
    long_tail: bool = Field(default=False, description="Is this a long-tail keyword?")
    question_based: bool = Field(default=False, description="Is this phrased as a question?")
    related_topics: List[str] = Field(
        default_factory=list, description="Content topics this supports"
    )


class KeywordCluster(BaseModel):
    """Group of related keywords around a theme"""

    theme: str = Field(..., description="Central theme/topic")
    primary_keyword: str = Field(..., description="Main target keyword for this cluster")
    secondary_keywords: List[str] = Field(default_factory=list, description="Supporting keywords")
    content_suggestions: List[str] = Field(
        default_factory=list, description="Content ideas for this cluster"
    )
    priority: str = Field(..., description="High/Medium/Low priority")


class CompetitorKeywords(BaseModel):
    """Keywords competitors are targeting"""

    competitor_name: str = Field(..., description="Competitor name or URL")
    estimated_keywords: List[str] = Field(
        default_factory=list, description="Keywords they likely target"
    )
    gaps: List[str] = Field(
        default_factory=list, description="Keywords we could target that they miss"
    )
    overlaps: List[str] = Field(default_factory=list, description="Keywords both target")


class KeywordStrategy(BaseModel):
    """Complete SEO keyword strategy"""

    business_name: str = Field(..., description="Client business name")
    industry: str = Field(..., description="Industry/vertical")
    target_audience: str = Field(..., description="Target audience description")

    # Primary keywords (5-10)
    primary_keywords: List[Keyword] = Field(
        default_factory=list, description="Main target keywords"
    )

    # Secondary keywords (20-30)
    secondary_keywords: List[Keyword] = Field(
        default_factory=list, description="Long-tail and supporting keywords"
    )

    # Keyword clusters for content planning
    keyword_clusters: List[KeywordCluster] = Field(
        default_factory=list, description="Thematic keyword groups"
    )

    # Competitor analysis (if provided)
    competitor_analysis: List[CompetitorKeywords] = Field(
        default_factory=list, description="Competitor keyword analysis"
    )

    # Quick wins
    quick_win_keywords: List[str] = Field(
        default_factory=list, description="Low-difficulty, high-relevance keywords to target first"
    )

    # Content recommendations
    content_priorities: List[str] = Field(
        default_factory=list, description="Top 5 content pieces to create based on keyword research"
    )

    # Strategy summary
    strategy_summary: str = Field(..., description="Executive summary of keyword strategy")

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Analytics",
                "industry": "B2B SaaS",
                "target_audience": "Customer success teams",
                "primary_keywords": [
                    {
                        "keyword": "customer churn prediction",
                        "search_intent": "informational",
                        "difficulty": "medium",
                        "monthly_volume_estimate": "1K-10K",
                        "relevance_score": 9.5,
                        "long_tail": False,
                        "question_based": False,
                        "related_topics": ["product analytics", "retention"],
                    }
                ],
                "strategy_summary": "Focus on mid-funnel commercial intent keywords...",
            }
        }
