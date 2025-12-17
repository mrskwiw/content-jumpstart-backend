"""Research tools for client analysis and intelligence gathering

This module provides automated research tools for the content generation system.
Each tool can be purchased as an add-on service ($300-600).

Available research tools:
- Voice Analysis ($400): Analyze existing content to extract voice patterns
- Brand Archetype Assessment ($300): Identify brand personality and archetype
- SEO Keyword Research ($400): Find target keywords and opportunities
- Competitive Analysis ($500): Research competitors and identify gaps
- Market Trends Research ($400): Discover trending topics and data
- Content Gap Analysis ($500): Identify content opportunities
- Content Audit ($400): Analyze existing content performance
- Platform Strategy ($300): Recommend optimal platform mix
- Content Calendar Strategy ($300): Create strategic 90-day calendar
- Audience Research ($500): Research target audience demographics
- ICP Workshop ($600): Facilitate ideal customer profile definition
- Story Mining ($500): Extract customer success stories
"""

from .audience_research import AudienceResearcher
from .base import ResearchResult, ResearchTool
from .brand_archetype import BrandArchetypeAnalyzer
from .competitive_analysis import CompetitiveAnalyzer
from .content_audit import ContentAuditor
from .content_calendar_strategy import ContentCalendarStrategist
from .content_gap_analysis import ContentGapAnalyzer
from .market_trends_research import MarketTrendsResearcher
from .platform_strategy import PlatformStrategist
from .seo_keyword_research import SEOKeywordResearcher
from .voice_analysis import VoiceAnalyzer

__all__ = [
    "ResearchTool",
    "ResearchResult",
    "VoiceAnalyzer",
    "BrandArchetypeAnalyzer",
    "SEOKeywordResearcher",
    "CompetitiveAnalyzer",
    "MarketTrendsResearcher",
    "ContentGapAnalyzer",
    "ContentAuditor",
    "PlatformStrategist",
    "ContentCalendarStrategist",
    "AudienceResearcher",
]
