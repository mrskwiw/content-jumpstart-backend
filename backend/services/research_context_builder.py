"""
Research Context Builder Service

Fetches and formats research results for inclusion in content generation context.
Provides concise, actionable insights from completed research tools with usage guidance.

Phase 1 Implementation - Research Context Integration Feature
"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from backend.models.research_result import ResearchResult
from backend.services import crud
from src.utils.response_cache import ResponseCache
from backend.utils.logger import logger


# Initialize cache (48-hour TTL for research context)
cache = ResponseCache()
CACHE_TTL = 48 * 3600  # 48 hours
CACHE_PREFIX = "research_context"

# Token limits
MAX_TOTAL_TOKENS = 500  # Maximum tokens for all research insights
MAX_TOOL_TOKENS = 150  # Maximum tokens per tool summary
PRIORITY_TOOLS = ["voice_analysis", "seo_keyword_research", "brand_archetype"]


def build_research_context(db: Session, client_id: str) -> Dict[str, Any]:
    """
    Build formatted research context for a client.

    Fetches all completed research results for the client and formats them
    as concise, actionable insights for content generation.

    Args:
        db: Database session
        client_id: Client ID to fetch research for

    Returns:
        Dict with:
        - formatted_text: String of formatted research insights
        - tool_count: Number of tools included
        - total_tokens: Approximate token count
        - tools_included: List of tool names included
    """
    # Check cache first
    cache_key = f"{CACHE_PREFIX}_{client_id}"
    cached = cache.get_by_key(cache_key)
    if cached:
        logger.info(f"Using cached research context for client {client_id}")
        return cached

    # Fetch research results from database
    results = crud.get_research_results_by_client(db, client_id)

    # Filter to completed results only
    completed_results = [r for r in results if r.status == "completed"]

    if not completed_results:
        logger.info(f"No completed research results found for client {client_id}")
        return {
            "formatted_text": "",
            "research_summary": "",
            "formatted_research": "",
            "tool_count": 0,
            "total_tokens": 0,
            "tools_included": [],
        }

    # Group by tool name and keep most recent for each tool
    tool_results = {}
    for result in completed_results:
        if result.tool_name not in tool_results:
            tool_results[result.tool_name] = result
        else:
            # Keep most recent
            if result.created_at > tool_results[result.tool_name].created_at:
                tool_results[result.tool_name] = result

    # Format all results
    formatted = _format_all_results(tool_results)

    # Cache result
    cache.put_by_key(cache_key, formatted)
    logger.info(
        f"Formatted research context for client {client_id}: "
        f"{formatted['tool_count']} tools, ~{formatted['total_tokens']} tokens"
    )

    return formatted


# Alias for backwards compatibility
build_structured_context = build_research_context


# Maps the 12 Jungian archetypes returned by the brand_archetype research tool
# to the 5 content archetypes understood by get_archetype_guidance() in
# brand_frameworks.py. Without this mapping, get_archetype_guidance() silently
# returns "" for any research-sourced archetype name.
_JUNGIAN_TO_CONTENT_ARCHETYPE: Dict[str, str] = {
    "sage": "Expert",
    "ruler": "Expert",
    "hero": "Motivator",
    "explorer": "Innovator",
    "creator": "Innovator",
    "magician": "Innovator",
    "outlaw": "Innovator",
    "caregiver": "Guide",
    "innocent": "Guide",
    "everyman": "Friend",
    "jester": "Friend",
    "lover": "Friend",
}


def get_brand_archetype_from_research(session: Any, client_id: str) -> Optional[str]:
    """Return the content archetype ('Expert', 'Guide', etc.) derived from the most
    recent completed brand_archetype research run for this client, or None.

    The brand_archetype tool stores Jungian archetype IDs ('caregiver', 'sage', …).
    This function maps those to the 5 content archetypes that get_archetype_guidance()
    understands so the guidance is actually injected into the generation prompt.
    """
    try:
        from backend.services.crud import get_research_results_by_client

        results = get_research_results_by_client(
            session, client_id, tool_name="brand_archetype", status="completed"
        )
        if results:
            primary = (results[0].data or {}).get("primary_archetype")
            if primary:
                jungian = str(primary).lower()
                content_archetype = _JUNGIAN_TO_CONTENT_ARCHETYPE.get(jungian)
                if content_archetype:
                    return content_archetype
                # If the stored value is already a content archetype name, use it directly
                if jungian.capitalize() in {"Expert", "Friend", "Innovator", "Guide", "Motivator"}:
                    return jungian.capitalize()
    except Exception:
        pass
    return None


def _format_all_results(tool_results: Dict[str, ResearchResult]) -> Dict[str, Any]:
    """
    Format all research results into concise context string.

    Args:
        tool_results: Dict mapping tool_name to ResearchResult

    Returns:
        Dict with formatted_text, tool_count, total_tokens, tools_included
    """
    formatted_sections = []
    total_tokens = 0
    tools_included = []

    # Prioritize tools: voice, SEO, archetype first
    priority_tools = [name for name in PRIORITY_TOOLS if name in tool_results]
    other_tools = [name for name in tool_results.keys() if name not in PRIORITY_TOOLS]
    ordered_tools = priority_tools + other_tools

    for tool_name in ordered_tools:
        result = tool_results[tool_name]

        # Format this tool's result
        formatted = _format_tool_result(tool_name, result)

        if not formatted:
            continue

        # Estimate tokens (rough: 4 chars = 1 token)
        tool_tokens = len(formatted) // 4

        # Check if adding this would exceed limit
        if total_tokens + tool_tokens > MAX_TOTAL_TOKENS:
            # Skip if not priority tool
            if tool_name not in PRIORITY_TOOLS:
                logger.info(f"Skipping {tool_name} - would exceed token limit")
                continue
            # Truncate if priority tool
            truncate_to = (MAX_TOTAL_TOKENS - total_tokens) * 4
            formatted = formatted[:truncate_to] + "..."
            tool_tokens = len(formatted) // 4

        formatted_sections.append(formatted)
        total_tokens += tool_tokens
        tools_included.append(tool_name)

        # Stop if we hit the limit
        if total_tokens >= MAX_TOTAL_TOKENS:
            break

    # Assemble final text
    if not formatted_sections:
        formatted_text = ""
    else:
        header = "RESEARCH INSIGHTS (from completed research tools):\n\n"
        formatted_text = header + "\n\n".join(formatted_sections)

    return {
        "formatted_text": formatted_text,
        "research_summary": formatted_text,
        "formatted_research": formatted_text,
        "tool_count": len(tools_included),
        "total_tokens": total_tokens,
        "tools_included": tools_included,
    }


def _format_tool_result(tool_name: str, result: ResearchResult) -> str:
    """Format a single research tool result."""
    try:
        formatters = {
            "voice_analysis": _format_voice_analysis,
            "seo_keyword_research": _format_seo_keywords,
            "brand_archetype": _format_brand_archetype,
            "determine_competitors": _format_determine_competitors,
            "competitive_analysis": _format_competitive_analysis,
            "content_gap_analysis": _format_content_gap,
            "market_trends_research": _format_market_trends,
            "platform_strategy": _format_platform_strategy,
            "content_calendar": _format_content_calendar,
            "audience_research": _format_audience_research,
            "icp_workshop": _format_icp_workshop,
            "story_mining": _format_story_mining,
            "content_audit": _format_content_audit,
            "business_report": _format_business_report,
        }
        formatter = formatters.get(tool_name)
        if not formatter:
            logger.warning(f"No formatter found for tool: {tool_name}")
            return ""
        return formatter(result)
    except Exception as e:
        logger.error(f"Error formatting {tool_name}: {e}")
        return ""


def _format_voice_analysis(result):
    """Format voice analysis for content generation context.

    Provides concise but actionable voice guidance for AI content generation.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Summary (most important - sets overall voice)
    if data.get("summary"):
        summary = data["summary"][:150]  # Limit length
        parts.append(f"Voice: {summary}")

    # Tone & personality
    tone_parts = []
    primary_tone = data.get("primary_tone", data.get("tone"))
    if primary_tone:
        tone_parts.append(primary_tone)
    if data.get("secondary_tone"):
        tone_parts.append(data["secondary_tone"])

    # Add formality level
    formality = data.get("formality_score")
    if formality:
        if formality >= 7:
            tone_parts.append("formal")
        elif formality <= 4:
            tone_parts.append("casual")

    # Add confidence level
    confidence = data.get("confidence_score")
    if confidence and confidence >= 7:
        tone_parts.append("confident")

    if tone_parts:
        parts.append(f"Tone: {', '.join(tone_parts)}")

    # Key personality traits (top 3)
    if data.get("personality_traits"):
        traits = [str(t).replace("_", " ") for t in data["personality_traits"][:3]]
        parts.append(f"Personality: {', '.join(traits)}")

    # Writing style indicators
    style_parts = []

    # Sentence length
    if data.get("sentence_analysis", {}).get("avg_length"):
        avg_len = data["sentence_analysis"]["avg_length"]
        if avg_len < 12:
            style_parts.append("short sentences")
        elif avg_len > 20:
            style_parts.append("long sentences")

    # Pronoun focus
    pronoun_focus = data.get("pronoun_focus")
    if pronoun_focus == "you":
        style_parts.append("reader-focused")
    elif pronoun_focus == "we":
        style_parts.append("collaborative voice")
    elif pronoun_focus == "I":
        style_parts.append("personal voice")

    # Data usage
    if data.get("uses_data"):
        freq = data.get("data_frequency", "sometimes")
        if freq in ["frequently", "always"]:
            style_parts.append("data-driven")

    # Formatting preferences
    if data.get("uses_bullets"):
        style_parts.append("uses bullets")
    if data.get("uses_emojis"):
        style_parts.append("uses emojis")

    if style_parts:
        parts.append(f"Style: {', '.join(style_parts[:4])}")  # Max 4 style elements

    # Signature phrases (top 2 most distinctive)
    if data.get("signature_phrases"):
        phrases = [f'"{p.get("phrase")}"' for p in data["signature_phrases"][:2] if p.get("phrase")]
        if phrases:
            parts.append(f"Signature: {', '.join(phrases)}")

    # Readability target
    readability = data.get("readability_score")
    if readability:
        if readability >= 70:
            parts.append("Readability: Easy (conversational)")
        elif readability >= 50:
            parts.append("Readability: Standard")
        else:
            parts.append("Readability: Advanced")

    # Opening pattern hint (most common)
    if data.get("opening_patterns"):
        opening_type = data["opening_patterns"][0].get("pattern_type")
        if opening_type:
            parts.append(f"Opens with: {opening_type}")

    # CTA style hint (most common)
    if data.get("cta_patterns"):
        cta_type = data["cta_patterns"][0].get("cta_type")
        if cta_type:
            parts.append(f"CTA style: {cta_type}")

    # Assemble final context string
    if parts:
        context = f"Voice Analysis ({date}): {' | '.join(parts)}"
    else:
        # Fallback to minimal format if no data
        context = f"Voice Analysis ({date}): Tone={primary_tone or '?'}, Readability={data.get('readability_grade','?')}"

    return context


def _format_seo_keywords(result):
    """Format SEO keywords for content generation context.

    Provides concise but actionable SEO guidance for AI content generation.
    Fixes crash by properly extracting keyword names from dict objects.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Extract primary keywords (fix crash - keywords are dicts, not strings)
    primary_keywords = data.get("primary_keywords", [])
    if primary_keywords:
        # Extract keyword names from dict objects
        keyword_names = [
            kw.get("keyword", "") for kw in primary_keywords[:5] if isinstance(kw, dict)
        ]
        if keyword_names:
            parts.append(f"Primary: {', '.join(keyword_names[:3])}")

            # Add search intent distribution
            intents = [
                kw.get("search_intent", "") for kw in primary_keywords[:10] if isinstance(kw, dict)
            ]
            if intents:
                # Count intent types
                from collections import Counter

                intent_counts = Counter(intents)
                dominant_intent = intent_counts.most_common(1)[0][0] if intent_counts else None
                if dominant_intent:
                    parts.append(f"Intent: {dominant_intent}")

            # Add difficulty mix
            difficulties = [
                kw.get("difficulty", "") for kw in primary_keywords if isinstance(kw, dict)
            ]
            if difficulties:
                low_count = sum(1 for d in difficulties if d == "low")
                medium_count = sum(1 for d in difficulties if d == "medium")
                if low_count > 0:
                    parts.append(f"Quick wins: {low_count} low-difficulty")
                elif medium_count > 0:
                    parts.append(f"Difficulty: {medium_count} medium")

    # Add quick wins if available
    quick_wins = data.get("quick_win_keywords", [])
    if quick_wins and len(quick_wins) > 0:
        parts.append(f"Quick wins: {len(quick_wins)} opportunities")

    # Add trending keywords indicator
    if primary_keywords:
        trending = [
            kw.get("keyword", "")
            for kw in primary_keywords[:5]
            if isinstance(kw, dict) and kw.get("trend_direction") == "rising"
        ]
        if trending:
            parts.append(f"Trending: {trending[0]}")

    # Add content priorities hint
    priorities = data.get("content_priorities", [])
    if priorities and len(priorities) > 0:
        # Extract priority type from first priority (e.g., "[HIGH]", "[QUICK WIN]")
        first_priority = priorities[0]
        if "[" in first_priority and "]" in first_priority:
            priority_type = first_priority[
                first_priority.index("[") + 1 : first_priority.index("]")
            ]
            parts.append(f"Focus: {priority_type}")

    # Add negative keywords (excluded keywords to avoid in content)
    negative_keywords = data.get("negative_keywords", [])
    if negative_keywords and len(negative_keywords) > 0:
        parts.append(f"Avoid in content: {', '.join(negative_keywords[:10])}")

    # Assemble final context
    if parts:
        context = f"SEO Keywords ({date}): {' | '.join(parts)}"
    else:
        # Fallback
        context = f"SEO Keywords ({date}): Available"

    return context


def _format_brand_archetype(result):
    """Format brand archetype for content generation context.

    Provides concise but actionable archetype guidance for AI content generation.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    # Import archetypes to get full details
    from src.research.brand_archetype import ARCHETYPES

    parts = []

    # Get primary archetype (fix wrong field name)
    primary_id = data.get("primary_archetype")
    if not primary_id:
        return f"Brand Archetype ({date}): Not determined"

    primary_arch = ARCHETYPES.get(primary_id)
    if not primary_arch:
        return f"Brand Archetype ({date}): {primary_id}"

    # Start with archetype name
    parts.append(f"Archetype: {primary_arch.name}")

    # Add secondary if present
    secondary_id = data.get("secondary_archetype")
    if secondary_id:
        secondary_arch = ARCHETYPES.get(secondary_id)
        if secondary_arch:
            parts.append(f"Secondary: {secondary_arch.name}")

    # Voice characteristics (top 2 for brevity)
    voice_chars = primary_arch.voice_characteristics[:2]
    if voice_chars:
        parts.append(f"Voice: {', '.join(voice_chars).lower()}")

    # Key traits (top 3)
    traits = primary_arch.traits[:3]
    if traits:
        parts.append(f"Traits: {', '.join(traits).lower()}")

    # Content themes (top 2)
    themes = primary_arch.content_themes[:2]
    if themes:
        parts.append(f"Themes: {', '.join(themes).lower()}")

    # Confidence score if available
    confidence = data.get("confidence_score")
    if confidence and confidence >= 0.7:
        parts.append(f"Confidence: {confidence:.0%}")

    # Assemble final context
    context = f"Brand Archetype ({date}): {' | '.join(parts)}"
    return context


def _format_determine_competitors(result):
    """Extract competitor insights for content generation context"""
    data = result.data if hasattr(result, "data") else result

    parts = []

    # Primary competitors (names only, concise)
    if data.get("primary_competitors"):
        names = [
            c.get("name", c) if isinstance(c, dict) else c for c in data["primary_competitors"][:3]
        ]
        parts.append(f"Main Competitors: {', '.join(names)}")

    # Market gaps (opportunities)
    if data.get("market_gaps"):
        gaps = data["market_gaps"][:2]
        parts.append(f"Market Gaps: {', '.join(gaps)}")

    # Positioning recommendation (how to differentiate)
    if data.get("recommended_positioning"):
        positioning = data["recommended_positioning"][:80]  # First 80 chars
        parts.append(f"Positioning: {positioning}")

    return " | ".join(parts) if parts else "Competitors: Identified"


def _format_competitive_analysis(result):
    """Extract key competitive insights for content generation.

    Provides concise but actionable competitive guidance for AI content generation.
    Fixed field names to match actual model schema.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Competitor count (context)
    competitors = data.get("competitors", [])
    if competitors:
        parts.append(f"{len(competitors)} competitors analyzed")

    # Quick wins (immediate opportunities)
    quick_wins = data.get("quick_wins", [])
    if quick_wins:
        wins = quick_wins[:2]  # Top 2
        parts.append(f"Quick Wins: {', '.join(wins)}")

    # Content gaps (opportunity areas)
    content_gaps = data.get("content_gaps", [])
    if content_gaps:
        gap_topics = []
        for g in content_gaps[:2]:
            if isinstance(g, dict):
                topic = g.get("topic", "")
                opp_score = g.get("opportunity_score")
                if topic:
                    if opp_score and opp_score >= 8:
                        gap_topics.append(f"{topic} (high)")
                    else:
                        gap_topics.append(topic)
            else:
                gap_topics.append(str(g))

        if gap_topics:
            parts.append(f"Gaps: {', '.join(gap_topics)}")

    # Differentiation strategies (positioning) - FIXED field name
    diff_strategies = data.get("differentiation_strategies", [])
    if diff_strategies:
        strategy_names = []
        for s in diff_strategies[:2]:
            if isinstance(s, dict):
                # Fixed: use "strategy_name" not "strategy" or "title"
                name = s.get("strategy_name", "")
                if name:
                    strategy_names.append(name)
            else:
                strategy_names.append(str(s))

        if strategy_names:
            parts.append(f"Differentiate: {', '.join(strategy_names)}")

    # Recommended position (market positioning) - FIXED field name
    recommended_position = data.get("recommended_position", {})
    if recommended_position and isinstance(recommended_position, dict):
        # Fixed: use "positioning_statement" not "statement"
        positioning = recommended_position.get("positioning_statement", "")
        if positioning:
            # Truncate for brevity
            parts.append(f"Position: {positioning[:60]}...")

    # Competitive threats (what to watch)
    competitive_threats = data.get("competitive_threats", [])
    if competitive_threats:
        threats = competitive_threats[:1]  # Just 1 for brevity
        if threats:
            parts.append(f"Watch: {threats[0]}")

    # Assemble final context
    if parts:
        context = f"Competitive Analysis ({date}): {' | '.join(parts)}"
    else:
        context = f"Competitive Analysis ({date}): Available"

    return context


def _format_content_gap(result):
    """Format content gap analysis for content generation context.

    Provides concise but actionable gap guidance for AI content generation.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Total gaps (high-level context)
    total = data.get("total_gaps_identified")
    if total:
        parts.append(f"{total} gaps")

    # Critical gaps (most important)
    critical = data.get("critical_gaps", [])
    if critical:
        critical_titles = [g.get("gap_title", "") for g in critical[:2] if isinstance(g, dict)]
        if critical_titles:
            parts.append(f"Critical: {', '.join(critical_titles)}")

    # Quick wins (actionable)
    quick_wins = data.get("quick_wins", [])
    if quick_wins and len(quick_wins) > 0:
        parts.append(f"Quick wins: {len(quick_wins)} available")

    # Buyer journey gaps (strategic context)
    buyer_gaps = data.get("buyer_journey_gaps", [])
    if buyer_gaps:
        missing_stages = [g.get("stage", "") for g in buyer_gaps if isinstance(g, dict)]
        if missing_stages:
            parts.append(f"Missing stages: {', '.join(missing_stages[:2])}")

    # Immediate actions (next steps)
    actions = data.get("immediate_actions", [])
    if actions and len(actions) > 0:
        parts.append(f"Next: {actions[0][:40]}...")

    # Assemble final context
    if parts:
        context = f"Content Gap ({date}): {' | '.join(parts)}"
    else:
        context = f"Content Gap ({date}): Available"

    return context


def _format_market_trends(result):
    """Extract key market trends insights for content generation.

    Provides concise but actionable trend guidance for AI content generation.
    Fixes wrong field name (title -> topic) and adds momentum indicators.
    """
    data = result.data if hasattr(result, "data") else result
    date = (
        result.created_at.strftime("%b %d")
        if hasattr(result, "created_at") and result.created_at
        else "recently"
    )

    parts = []

    # Top rising trends (most actionable - show with momentum)
    if data.get("top_rising_trends"):
        trends = []
        for t in data["top_rising_trends"][:3]:
            if isinstance(t, dict):
                topic = t.get("topic", "")  # Fixed: was "title"
                momentum = t.get("momentum", "")
                if topic and momentum == "rising":
                    trends.append(f"{topic} ↗")
                elif topic:
                    trends.append(topic)
            else:
                trends.append(str(t))

        if trends:
            parts.append(f"Rising: {', '.join(trends[:2])}")  # Top 2 for brevity

    # Immediate opportunities (most actionable for content)
    if data.get("immediate_opportunities"):
        opps = data["immediate_opportunities"]
        if opps and len(opps) > 0:
            parts.append(f"Opportunities: {len(opps)} immediate")

    # Key themes (overarching narratives)
    if data.get("key_themes"):
        themes = data["key_themes"][:2]
        if themes:
            parts.append(f"Themes: {', '.join(themes)}")

    # Emerging conversations (new debates)
    if data.get("emerging_conversations"):
        conv = data["emerging_conversations"]
        if conv and len(conv) > 0:
            first_conv = conv[0]
            if isinstance(first_conv, dict):
                topic = first_conv.get("topic", "")
                if topic:
                    parts.append(f"Emerging: {topic}")

    # Declining topics (what to avoid)
    if data.get("declining_topics"):
        declining = data["declining_topics"]
        if declining and len(declining) > 0:
            parts.append(f"Avoid: {declining[0]}")  # Just 1 for brevity

    # Assemble final context
    if parts:
        context = f"Market Trends ({date}): {' | '.join(parts)}"
    else:
        context = f"Market Trends ({date}): Available"

    return context


def _format_platform_strategy(result):
    """Format platform strategy for content generation context.

    Provides concise but actionable platform guidance for AI content generation.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Recommended platform mix (core strategy)
    platform_mix = data.get("recommended_platform_mix", {})
    if platform_mix and isinstance(platform_mix, dict):
        primary = platform_mix.get("primary_platforms", [])
        secondary = platform_mix.get("secondary_platforms", [])

        if primary:
            primary_names = [str(p).replace("_", " ").title() for p in primary[:2]]
            parts.append(f"Primary: {', '.join(primary_names)}")

        if secondary:
            secondary_names = [str(p).replace("_", " ").title() for p in secondary[:2]]
            parts.append(f"Secondary: {', '.join(secondary_names)}")

    # Quick wins (immediate actions)
    quick_wins = data.get("quick_wins", [])
    if quick_wins and len(quick_wins) > 0:
        first_win = quick_wins[0]
        if isinstance(first_win, dict):
            platform = str(first_win.get("platform", "")).replace("_", " ").title()
            action = first_win.get("action", "")
            if platform and action:
                parts.append(f"Quick win: {platform} - {action[:30]}...")
        else:
            parts.append(f"Quick wins: {len(quick_wins)} identified")

    # Content distribution (efficiency strategy)
    content_dist = data.get("content_distribution", {})
    if content_dist and isinstance(content_dist, dict):
        source = content_dist.get("source_platform", "")
        if source:
            source_name = str(source).replace("_", " ").title()
            parts.append(f"Hub: {source_name}")

    # Key insights (strategic context)
    key_insights = data.get("key_insights", [])
    if key_insights and len(key_insights) > 0:
        parts.append(f"Insight: {key_insights[0][:50]}...")

    # Assemble final context
    if parts:
        context = f"Platform Strategy ({date}): {' | '.join(parts)}"
    else:
        context = f"Platform Strategy ({date}): Available"

    return context


def _format_content_calendar(result):
    """Format content calendar for content generation context.

    Provides concise but actionable calendar guidance for AI content generation.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Calendar overview (scope)
    total_posts = data.get("total_posts_90_days", 0)
    if total_posts:
        parts.append(f"{total_posts} posts planned")

    # Content pillars (what to create)
    content_pillars = data.get("content_pillars", [])
    if content_pillars and len(content_pillars) > 0:
        pillars = [str(p).replace("_", " ").title() for p in content_pillars[:3]]
        parts.append(f"Pillars: {', '.join(pillars)}")

    # Primary goals (why we're creating)
    primary_goals = data.get("primary_goals", [])
    if primary_goals and len(primary_goals) > 0:
        goals = [str(g).replace("_", " ").title() for g in primary_goals[:2]]
        parts.append(f"Goals: {', '.join(goals)}")

    # Posting frequency (how often)
    recommended_freq = data.get("recommended_frequency", "")
    if recommended_freq:
        freq = str(recommended_freq).replace("_", " ").replace("x", "×")
        parts.append(f"Frequency: {freq}")

    # Current week theme (what to focus on now)
    weekly_calendar = data.get("weekly_calendar", [])
    if weekly_calendar and len(weekly_calendar) > 0:
        first_week = weekly_calendar[0]
        if isinstance(first_week, dict):
            theme = first_week.get("theme", "")
            if theme:
                parts.append(f"This week: {theme[:30]}...")

    # Assemble final context
    if parts:
        context = f"Content Calendar ({date}): {' | '.join(parts)}"
    else:
        context = f"Content Calendar ({date}): Available"

    return context


def _format_audience_research(result):
    """Format audience research for content generation context.

    Provides concise but actionable audience guidance for AI content generation.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Demographics (who they are)
    demographics = data.get("demographics", {})
    if demographics and isinstance(demographics, dict):
        age_ranges = demographics.get("primary_age_ranges", [])
        job_titles = demographics.get("job_titles", [])

        if age_ranges:
            ages = ", ".join([str(age) for age in age_ranges[:2]])
            parts.append(f"Ages: {ages}")

        if job_titles:
            parts.append(f"Roles: {', '.join(job_titles[:2])}")

    # Pain points (what they struggle with)
    pain_points = data.get("pain_points", [])
    if pain_points and len(pain_points) > 0:
        parts.append(f"Pain: {pain_points[0][:40]}...")

    # Goals (what they want)
    goals = data.get("goals_aspirations", [])
    if goals and len(goals) > 0:
        parts.append(f"Goal: {goals[0][:40]}...")

    # Content preferences (how to reach them)
    behavioral = data.get("behavioral_profile", {})
    if behavioral and isinstance(behavioral, dict):
        platforms = behavioral.get("preferred_platforms", [])
        if platforms and len(platforms) > 0:
            parts.append(f"Platforms: {', '.join(platforms[:2])}")

    # Key insight (strategic context)
    key_insights = data.get("key_insights", [])
    if key_insights and len(key_insights) > 0:
        parts.append(f"Insight: {key_insights[0][:50]}...")

    # Assemble final context
    if parts:
        context = f"Audience Research ({date}): {' | '.join(parts)}"
    else:
        context = f"Audience Research ({date}): Available"

    return context


def _format_icp_workshop(result):
    """Format ICP workshop for content generation context."""
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Profile summary
    summary = data.get("one_sentence_summary", "")
    if summary:
        parts.append(f"ICP: {summary[:60]}...")

    # Company size
    demographics = data.get("demographics", {})
    if demographics:
        company_size = demographics.get("company_size", "")
        if company_size:
            parts.append(f"Size: {company_size}")

    # Top goal
    psycho = data.get("psychographics", {})
    if psycho:
        goals = psycho.get("goals", [])
        if goals and len(goals) > 0:
            parts.append(f"Goal: {goals[0][:40]}...")

        # Top challenge
        challenges = psycho.get("challenges", [])
        if challenges and len(challenges) > 0:
            parts.append(f"Challenge: {challenges[0][:40]}...")

    if parts:
        context = f"ICP Workshop ({date}): {' | '.join(parts)}"
    else:
        context = f"ICP Workshop ({date}): Available"

    return context


def _format_story_mining(result):
    """Format story mining for content generation context."""
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Story count
    story_count = data.get("total_stories", 0)
    if story_count:
        parts.append(f"{story_count} stories")

    # Key transformation
    journey = data.get("customer_journey", {})
    if journey:
        before = journey.get("before", {})
        after = journey.get("after", {})

        if before and after:
            pain = before.get("situation", "")
            results = after.get("results", [])

            if pain:
                parts.append(f"Pain: {pain[:30]}...")
            if results and len(results) > 0:
                parts.append(f"Result: {results[0][:30]}...")

    # Top quote
    quotes = data.get("key_quotes", [])
    if quotes and len(quotes) > 0:
        parts.append(f'Quote: "{quotes[0][:40]}..."')

    if parts:
        context = f"Story Mining ({date}): {' | '.join(parts)}"
    else:
        context = f"Story Mining ({date}): Available"

    return context


def _format_content_audit(result):
    """Format content audit for content generation context.

    Provides concise but actionable content audit guidance for AI content generation.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Total pieces and health score (high-level context)
    total = data.get("total_content_pieces", 0)
    health_score = data.get("overall_health_score")

    if total:
        parts.append(f"{total} pieces analyzed")

    if health_score is not None:
        health_label = (
            "excellent" if health_score >= 80 else "good" if health_score >= 60 else "needs work"
        )
        parts.append(f"Health: {health_score:.0f}/100 ({health_label})")

    # Top performers (what's working)
    top_performers = data.get("top_performers", [])
    if top_performers and len(top_performers) > 0:
        top_titles = [p.get("title", "") for p in top_performers[:2] if isinstance(p, dict)]
        if top_titles:
            parts.append(f"Top: {', '.join(top_titles[:1])}")  # Just 1 for brevity

    # Content gaps (opportunities)
    content_gaps = data.get("content_gaps", [])
    if content_gaps and len(content_gaps) > 0:
        gap_count = len(content_gaps)
        high_priority = sum(
            1
            for g in content_gaps
            if isinstance(g, dict) and g.get("priority", "").lower() == "high"
        )
        if high_priority > 0:
            parts.append(f"Gaps: {gap_count} ({high_priority} high priority)")
        else:
            parts.append(f"Gaps: {gap_count} identified")

    # Refresh opportunities (quick wins)
    refresh_opps = data.get("refresh_opportunities", [])
    if refresh_opps and len(refresh_opps) > 0:
        high_impact = sum(
            1
            for r in refresh_opps
            if isinstance(r, dict) and r.get("estimated_impact", "").lower() == "high"
        )
        if high_impact > 0:
            parts.append(f"Refresh: {high_impact} high-impact updates")
        else:
            parts.append(f"Refresh: {len(refresh_opps)} opportunities")

    # Immediate actions (next steps)
    immediate_actions = data.get("immediate_actions", [])
    if immediate_actions and len(immediate_actions) > 0:
        parts.append(f"Priority: {immediate_actions[0][:40]}...")

    # Assemble final context
    if parts:
        context = f"Content Audit ({date}): {' | '.join(parts)}"
    else:
        context = f"Content Audit ({date}): Available"

    return context


def _format_business_report(result):
    """Format business report for content generation context.

    Provides key insights about company perception, strengths, and positioning
    to inform content strategy and messaging.
    """
    data = result.data or {}
    date = result.created_at.strftime("%b %d") if result.created_at else "recently"

    parts = []

    # Company info
    company_name = data.get("company_name", "Company")

    # Perception score (high-level indicator)
    perception_score = data.get("perception_score", 0)
    if perception_score > 0:
        parts.append(f"Perception: {perception_score}/100")

    # Top 2-3 strengths to advertise
    top_strengths = data.get("top_strengths", [])
    if top_strengths:
        strength_names = [s.get("strength", "") for s in top_strengths[:3] if isinstance(s, dict)]
        if strength_names:
            parts.append(f"Strengths: {', '.join(strength_names)}")

    # Top pain points (2-3)
    pain_points = data.get("customer_pain_points", [])
    if pain_points:
        pain_texts = [p.get("pain_point", "")[:40] for p in pain_points[:2] if isinstance(p, dict)]
        if pain_texts:
            parts.append(f"Pain Points: {pain_texts[0]}")

    # Problems solved (value propositions)
    problems_solved = data.get("problems_solved", [])
    if problems_solved:
        value_props = [
            p.get("value_proposition", "")[:50] for p in problems_solved[:2] if isinstance(p, dict)
        ]
        if value_props:
            parts.append(f"Value: {value_props[0]}")

    # Assemble final context
    if parts:
        context = f"Business Report - {company_name} ({date}): {' | '.join(parts)}"
    else:
        context = f"Business Report - {company_name} ({date}): Available"

    return context


def invalidate_cache(client_id):
    cache_key = f"{CACHE_PREFIX}_{client_id}"
    cache.delete(cache_key)
    logger.info(f"Invalidated cache for {client_id}")


def get_story_context_for_template(
    db: Session, client_id: str, template_name: str, project_id: str
) -> Dict[str, Any]:
    """
    Fetch an available story for a story-based template and format it as generation context.

    Args:
        db: Database session
        client_id: Client whose stories to query
        template_name: Template slug (personal_story, things_i_got_wrong, milestone)
        project_id: Current project ID (used to exclude already-used stories)

    Returns:
        Dict with:
        - story_id (str | None): ID of the selected story, or None if none available
        - formatted_text (str): Story context ready to inject into generation prompt
        - available_count (int): Total number of eligible stories for this template
    """
    from backend.services.story_service import story_service

    available = story_service.get_available_stories_for_template(
        db, client_id, template_name, project_id, limit=5
    )

    if not available:
        return {"story_id": None, "formatted_text": "", "available_count": 0}

    # Pick the most recent eligible story
    story = available[0]
    full = story.full_story or {}

    parts = []
    if story.title:
        parts.append(f"Story: {story.title}")
    if story.summary:
        parts.append(f"Summary: {story.summary}")
    challenge = (full.get("challenge") or {}).get("problem_description") or (
        full.get("challenge") if isinstance(full.get("challenge"), str) else None
    )
    if challenge:
        parts.append(f"Challenge: {challenge}")
    if story.key_metrics:
        metrics = list(story.key_metrics.values())[:3]
        parts.append(f"Key results: {chr(44).join(str(m) for m in metrics)}")
    if story.emotional_hook:
        parts.append(f"Emotional hook: {story.emotional_hook}")

    formatted = "USE THIS STORY:\n" + "\n".join(parts) + f"\n[STORY_ID:{story.id}]"

    logger.info(
        f"Story context for template={template_name} project={project_id}: story {story.id} ({len(available)} available)"
    )

    return {
        "story_id": story.id,
        "formatted_text": formatted,
        "available_count": len(available),
    }
