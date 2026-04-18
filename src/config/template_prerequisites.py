"""Template research tool prerequisites mapping.

Maps each post template to recommended and required research tools.
This helps users understand which research tools enhance specific template types.
"""

from typing import Any, Dict, List  # noqa: F401 — List used in TEMPLATE_PREREQUISITES values

# Template ID to research tool mapping
# Template IDs correspond to templates in 02_POST_TEMPLATE_LIBRARY.md
#
# PRIORITY LEVELS (Based on actual AI generation needs analysis):
# - P0 (required): Template CANNOT generate quality content without this research
# - P1 (recommended): Significantly improves quality, but brief CAN provide this data
# - P2 (optional): Marginal improvement, nice-to-have
#
# requires_web_search: True means the generator pre-fetches live web data before
# generation and injects it into the prompt. Templates without this flag never
# receive web search results (even when a provider is configured).
#
# NOTE: Prerequisites reassigned based on analysis of actual prompt usage in
# content_generator.py. Only research tools that provide data actually used by
# AI prompts are classified as required (P0).
TEMPLATE_PREREQUISITES: Dict[int, Dict[str, Any]] = {
    # Template 1: Problem Recognition Post
    # P1: audience_research validates pain points (brief already provides customer_pain_points)
    # P2: SEO keywords for search terms, voice_analysis for hook patterns
    1: {
        "required": [],  # P0: None - brief provides pain_points field
        "recommended": ["audience_research"],  # P1
        "optional": ["seo_keyword_research", "voice_analysis"],  # P2
    },
    # Template 2: Statistic + Insight Post
    # P0: market_trends CRITICAL - brief has NO statistics field, requires data
    # P2: story_mining, competitive_analysis provide supporting context
    # Web search: pre-fetches latest industry stats at generation time
    2: {
        "required": ["market_trends_research"],  # P0: CRITICAL for credible statistics
        "recommended": [],  # P1: None
        "optional": ["story_mining", "competitive_analysis"],  # P2
        "requires_web_search": True,
    },
    # Template 3: Contrarian Post
    # P1: competitive_analysis shows "conventional wisdom to challenge"
    # P1: market_trends provides trend data to contradict
    # P2: SEO keywords for search optimization
    # Web search: fetches mainstream claims/conventional wisdom to push back against
    3: {
        "required": [],  # P0: None
        "recommended": ["competitive_analysis", "market_trends_research"],  # P1
        "optional": ["seo_keyword_research"],  # P2
        "requires_web_search": True,
    },
    # Template 4: Evolution Post
    # P0: story_mining CRITICAL - requires transformation stories with before/after arc
    # Brief stories field often empty or lacks structure
    4: {
        "required": ["story_mining"],  # P0: CRITICAL for transformation narrative
        "recommended": [],  # P1: None
        "optional": ["brand_archetype"],  # P2: Guides narrative tone
    },
    # Template 5: Question Post
    # P1: audience_research validates but brief provides customer_questions field
    # P2: SEO keywords, brand_archetype for tone guidance
    5: {
        "required": [],  # P0: None - brief provides customer_questions
        "recommended": ["audience_research"],  # P1: Validates questions
        "optional": ["seo_keyword_research", "brand_archetype"],  # P2
    },
    # Template 6: Personal Story Post
    # P0: story_mining CRITICAL if brief lacks personal stories
    # P1: brand_archetype guides vulnerable, authentic tone
    # P2: voice_analysis for narrative patterns
    6: {
        "required": ["story_mining"],  # P0: CRITICAL for personal narratives
        "recommended": ["brand_archetype"],  # P1: Tone guidance
        "optional": ["voice_analysis"],  # P2
    },
    # Template 7: Myth-Busting Post
    # P1: market_trends shows prevalent myths/misconceptions
    # P2: competitive_analysis, SEO keywords for common beliefs
    7: {
        "required": [],  # P0: None - brief provides misconceptions field
        "recommended": ["market_trends_research"],  # P1
        "optional": ["competitive_analysis", "seo_keyword_research"],  # P2
    },
    # Template 8: Vulnerability Post
    # P1: story_mining provides vulnerable stories, brand_archetype guides tone
    # P2: voice_analysis for authentic patterns
    8: {
        "required": [],  # P0: None - brief can provide vulnerability stories
        "recommended": ["story_mining", "brand_archetype"],  # P1
        "optional": ["voice_analysis"],  # P2
    },
    # Template 9: How-To Guide
    # P1: seo_keyword_research for "how to" queries, content_gap for missing topics
    # P2: audience_research for skill level
    9: {
        "required": [],  # P0: None - how-to is process-based
        "recommended": ["seo_keyword_research", "content_gap_analysis"],  # P1
        "optional": ["audience_research"],  # P2
    },
    # Template 10: Comparison Post
    # P0: competitive_analysis CRITICAL - requires detailed alternatives analysis
    # Brief competitors field provides names but not feature comparisons
    10: {
        "required": ["competitive_analysis"],  # P0: CRITICAL for alternatives data
        "recommended": [],  # P1: None
        "optional": ["market_trends_research", "seo_keyword_research"],  # P2
    },
    # Template 11: Learning Post
    # P1: story_mining for learning journey stories
    # P2: brand_archetype for narrative tone, voice_analysis for patterns
    11: {
        "required": [],  # P0: None - learning can come from brief
        "recommended": ["story_mining"],  # P1
        "optional": ["brand_archetype", "voice_analysis"],  # P2
    },
    # Template 12: Behind-the-Scenes Post
    # P1: story_mining for process stories
    # P2: brand_archetype for transparency tone, voice_analysis for authenticity
    12: {
        "required": [],  # P0: None - behind-scenes from brief
        "recommended": ["story_mining"],  # P1
        "optional": ["brand_archetype", "voice_analysis"],  # P2
    },
    # Template 13: Future-Thinking Post
    # P0: market_trends CRITICAL - cannot make credible predictions without trend data
    # P2: competitive_analysis for industry direction
    # Web search: fetches emerging trends and predictions to ground forward-looking claims
    13: {
        "required": ["market_trends_research"],  # P0: CRITICAL for predictions
        "recommended": [],  # P1: None
        "optional": ["competitive_analysis"],  # P2
        "requires_web_search": True,
    },
    # Template 14: Q&A Post
    # P1: audience_research validates questions (brief provides customer_questions)
    # P2: content_gap for missing FAQ topics
    14: {
        "required": [],  # P0: None - brief provides customer_questions
        "recommended": ["audience_research"],  # P1: Validates questions
        "optional": ["content_gap_analysis"],  # P2
    },
    # Template 15: Milestone/Achievement Post
    # P1: story_mining for journey/milestone stories
    # P2: brand_archetype for celebratory tone
    15: {
        "required": [],  # P0: None - milestones from brief
        "recommended": ["story_mining"],  # P1
        "optional": ["brand_archetype"],  # P2
    },
}


def get_template_prerequisites(template_id: int) -> Dict[str, Any]:
    """Get prerequisites for a specific template.

    Args:
        template_id: Template ID (1-15)

    Returns:
        Dict with 'required', 'recommended', 'optional' tool lists and
        optional 'requires_web_search' boolean flag.
    """
    return TEMPLATE_PREREQUISITES.get(template_id, {"required": [], "recommended": []})
