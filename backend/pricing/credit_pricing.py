"""
Credit pricing configuration.

Defines credit costs for all content types and research tools.
Costs are based on human labor replacement value and complexity.

Pricing Philosophy (credit COUNTS are labor-replacement value; $/credit is set by
BILLING-01 — subscription $0.50/credit, top-up $1/credit):
- Social posts: 5 credits (flagship short-form); blog posts: 20 credits
- Research tools: 150-300 credits based on labor savings
  - 150 credits: Replaces 3-4 hours of work (dollar300)
  - 200 credits: Replaces 4-8 hours of work (dollar400)
  - 250 credits: Replaces 6-10 hours of work (dollar500)
  - 300 credits: Replaces 8-12 hours of work (dollar600)
"""

# Content generation costs (charged on GENERATION; publishing is free — BILLING-01)
CONTENT_COSTS = {
    "blog_post": 20,  # Long-form blog content (500-1500 words)
    "social_post": 5,  # Flagship short-form social post (~¼ of a blog)
}

# Research tool costs (150-300 credits based on labor replacement)
RESEARCH_TOOL_COSTS = {
    # Light research (50 credits ~ $100-125)
    "platform_strategy": 150,  # Platform-specific recommendations (3-4 hours)
    "content_calendar": 150,  # 30-day content calendar generation (3-4 hours)
    "market_trends_research": 200,  # Industry trends and insights (3-4 hours)
    "business_report": 200,  # Business perception analysis with web+Maps data (3-4 hours)
    # Medium research (75 credits ~ $150-187.50)
    "brand_archetype": 150,  # Brand personality analysis (4-6 hours)
    "audience_research": 250,  # Demographic and psychographic profiling (4-6 hours)
    "content_audit": 200,  # Content performance analysis (4-6 hours)
    # Heavy research (100 credits ~ $200-250)
    "voice_analysis": 200,  # Brand voice documentation (6-8 hours)
    "competitive_analysis": 250,  # Competitor content strategy (6-8 hours)
    "content_gap_analysis": 250,  # Gap analysis and opportunities (6-8 hours)
    "story_mining": 250,  # Anecdote extraction and categorization (6-8 hours)
    "determine_competitors": 250,  # AI-powered competitor discovery (6-8 hours)
    # Very heavy research (150 credits ~ $300-375)
    "seo_keyword_research": 200,  # Comprehensive SEO keyword research (8-12 hours)
    "icp_workshop": 300,  # Ideal Customer Profile workshop (8-12 hours)
}

# Credit → dollar rates (BILLING-01, locked 2026-07-30). Subscription credits are
# 2 per $1 ($0.50/credit); purchased top-ups are $1/credit and never expire.
STANDARD_PACKAGE_RATE = 0.50  # $0.50 per credit (2 credits/$) — subscription rate
ADDITIONAL_CREDIT_RATE = 1.0  # $1.00 per credit — non-expiring top-up rate

# Minimum credits required for research tools
MIN_RESEARCH_TOOL_CREDITS = 50

# Maximum credits for a single operation
MAX_OPERATION_CREDITS = 200


def get_research_tool_cost(tool_name: str) -> int:
    """
    Get credit cost for a research tool.

    Args:
        tool_name: Research tool identifier

    Returns:
        Credit cost (0 if tool not found)
    """
    return RESEARCH_TOOL_COSTS.get(tool_name, 0)


def get_content_cost(content_type: str) -> int:
    """
    Get credit cost for content generation.

    Args:
        content_type: Content type identifier

    Returns:
        Credit cost (0 if content type not found)
    """
    return CONTENT_COSTS.get(content_type, 0)


def calculate_project_cost(
    num_blog_posts: int = 0,
    research_tools: list[str] | None = None,
) -> dict:
    """
    Calculate total credit cost for a project.

    Args:
        num_blog_posts: Number of blog posts to generate
        research_tools: List of research tool names

    Returns:
        Dictionary with cost breakdown
    """
    research_tools = research_tools or []

    # Blog post costs
    blog_cost = num_blog_posts * CONTENT_COSTS["blog_post"]

    # Research tool costs
    research_cost = 0
    research_breakdown = {}

    for tool_name in research_tools:
        cost = get_research_tool_cost(tool_name)
        if cost > 0:
            research_cost += cost
            research_breakdown[tool_name] = cost

    total_credits = blog_cost + research_cost

    return {
        "blog_posts": {"count": num_blog_posts, "credits_per_post": 20, "total": blog_cost},
        "research_tools": {"breakdown": research_breakdown, "total": research_cost},
        "total_credits": total_credits,
        "estimated_cost": {
            "standard_rate": total_credits * STANDARD_PACKAGE_RATE,
            "additional_rate": total_credits * ADDITIONAL_CREDIT_RATE,
        },
    }
