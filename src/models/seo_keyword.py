"""SEO Keyword Models

Defines data structures for SEO keywords and their usage in content generation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KeywordIntent(str, Enum):
    """SEO keyword search intent"""

    INFORMATIONAL = "informational"  # How-to, guides, education
    COMMERCIAL = "commercial"  # Product comparisons, reviews
    TRANSACTIONAL = "transactional"  # Buy, sign up, get demo
    NAVIGATIONAL = "navigational"  # Brand searches


class KeywordDifficulty(str, Enum):
    """Keyword competition difficulty"""

    EASY = "easy"  # Low competition
    MEDIUM = "medium"  # Medium competition
    HARD = "hard"  # High competition


class SEOKeyword(BaseModel):
    """Individual SEO keyword with metadata"""

    keyword: str = Field(..., description="The keyword phrase")
    search_volume: Optional[int] = Field(None, description="Monthly search volume")
    intent: KeywordIntent = Field(..., description="Search intent")
    difficulty: KeywordDifficulty = Field(
        KeywordDifficulty.MEDIUM, description="Competition difficulty"
    )
    priority: int = Field(1, description="Priority for usage (1=highest, 5=lowest)")

    # Context
    related_keywords: List[str] = Field(default_factory=list, description="Related keyword phrases")
    notes: Optional[str] = Field(None, description="Additional context or notes")


class KeywordStrategy(BaseModel):
    """SEO keyword strategy for a client"""

    # Primary Keywords (target 3-5)
    primary_keywords: List[SEOKeyword] = Field(
        default_factory=list, description="Primary target keywords"
    )

    # Secondary Keywords (target 10-15)
    secondary_keywords: List[SEOKeyword] = Field(
        default_factory=list, description="Secondary supporting keywords"
    )

    # Long-tail Keywords (unlimited)
    longtail_keywords: List[SEOKeyword] = Field(
        default_factory=list, description="Long-tail keyword variations"
    )

    # Strategy settings
    keyword_density_target: float = Field(
        0.015, description="Target keyword density (1.5% = 0.015)"
    )
    natural_integration: bool = Field(
        True, description="Prioritize natural integration over density"
    )

    def get_all_keywords(self) -> List[SEOKeyword]:
        """Get all keywords across all tiers"""
        return self.primary_keywords + self.secondary_keywords + self.longtail_keywords

    def get_keywords_by_intent(self, intent: KeywordIntent) -> List[SEOKeyword]:
        """Filter keywords by search intent"""
        return [kw for kw in self.get_all_keywords() if kw.intent == intent]

    def get_keywords_by_priority(self, max_priority: int = 3) -> List[SEOKeyword]:
        """Get high-priority keywords (priority <= max_priority)"""
        return [kw for kw in self.get_all_keywords() if kw.priority <= max_priority]


class KeywordUsage(BaseModel):
    """Track keyword usage in a post"""

    keyword: str = Field(..., description="The keyword used")
    count: int = Field(0, description="Number of times used")
    locations: List[str] = Field(
        default_factory=list, description="Where used (e.g., 'headline', 'body', 'cta')"
    )
    density: float = Field(0.0, description="Keyword density in post")
    natural: bool = Field(True, description="Whether integration appears natural")


class PostKeywordAnalysis(BaseModel):
    """Keyword analysis for a generated post"""

    post_id: int = Field(..., description="Post identifier")
    template_name: str = Field(..., description="Template used")

    # Keyword usage
    primary_keywords_used: List[KeywordUsage] = Field(
        default_factory=list, description="Primary keywords detected"
    )
    secondary_keywords_used: List[KeywordUsage] = Field(
        default_factory=list, description="Secondary keywords detected"
    )
    longtail_keywords_used: List[KeywordUsage] = Field(
        default_factory=list, description="Long-tail keywords detected"
    )

    # Metrics
    total_keyword_count: int = Field(0, description="Total keyword occurrences")
    overall_keyword_density: float = Field(0.0, description="Overall keyword density")
    has_primary_keyword: bool = Field(False, description="Contains at least 1 primary keyword")

    # Quality flags
    keyword_stuffing_detected: bool = Field(False, description="Excessive keyword density detected")
    missing_primary_keywords: bool = Field(True, description="No primary keywords detected")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "post_id": self.post_id,
            "template": self.template_name,
            "primary_keywords": [kw.keyword for kw in self.primary_keywords_used],
            "total_keywords": self.total_keyword_count,
            "density": f"{self.overall_keyword_density:.2%}",
            "has_primary": self.has_primary_keyword,
            "issues": {
                "stuffing": self.keyword_stuffing_detected,
                "missing_primary": self.missing_primary_keywords,
            },
        }
