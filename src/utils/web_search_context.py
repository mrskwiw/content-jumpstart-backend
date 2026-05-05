"""
Web Search Context Builder for Content Generation

Fetches live web data for templates that benefit from real-time factual grounding.
Falls back gracefully — never blocks post generation.

Templates enabled:
  2 — Statistic + Insight (needs real, citable stats)
  3 — Contrarian Take (needs a real mainstream claim to push back against)
 13 — Future Thinking (needs emerging trends and forward-looking data)
"""

from __future__ import annotations

import os
from typing import Dict, Optional

from .web_search import SearchResponse, WebSearchClient
from .logger import logger


# Per-template web search configuration
# Keys are template IDs (integers matching Template.template_id)
TEMPLATE_WEB_SEARCH_CONFIG: Dict[int, Dict] = {
    2: {  # Statistic + Insight
        "query_template": "latest {industry} statistics data research 2025",
        "fallback_query": "latest business statistics trends data 2025",
        "focus": "statistics and data",
        "max_results": 5,
    },
    3: {  # Contrarian Take
        "query_template": "conventional wisdom {industry} trends common advice 2025",
        "fallback_query": "conventional business wisdom common advice trends 2025",
        "focus": "mainstream trends and conventional wisdom",
        "max_results": 5,
    },
    13: {  # Future Thinking
        "query_template": "emerging {industry} trends predictions future 2025 2026",
        "fallback_query": "emerging business trends predictions 2025 2026",
        "focus": "emerging trends and predictions",
        "max_results": 5,
    },
}

# Hard cap: at most this many web searches per generation run (cost control)
MAX_SEARCHES_PER_RUN = 5


def build_web_search_context(
    template_id: int,
    industry: Optional[str],
    web_search_client: Optional[WebSearchClient] = None,
) -> Optional[str]:
    """
    Fetch live web data for a template that benefits from real-time factual grounding.

    Args:
        template_id: Template ID (must be in TEMPLATE_WEB_SEARCH_CONFIG)
        industry: Client industry string (used to tailor the search query)
        web_search_client: Optional pre-configured client; if None, one is created
            from environment variables.  If the resolved provider is "stub", returns
            None rather than injecting synthetic data as facts.

    Returns:
        Formatted context string ready for prompt injection, or None when:
        - template_id is not in TEMPLATE_WEB_SEARCH_CONFIG
        - no real search provider is configured (stub mode)
        - the search returns no results
        - any exception occurs during the search
    """
    config = TEMPLATE_WEB_SEARCH_CONFIG.get(template_id)
    if not config:
        return None

    if web_search_client is None:
        web_search_client = _create_default_client()

    # Do not inject stub/synthetic data as "live facts"
    if web_search_client.provider == "stub":
        return None

    query = (
        config["query_template"].format(industry=industry) if industry else config["fallback_query"]
    )

    try:
        response = web_search_client.search(query, max_results=config["max_results"])
        # Brave (and other providers) fall back to stub results on 429; the
        # provider attribute stays unchanged so the check above misses it.
        # Detect stub results by source field and refuse to inject fake data.
        if response.results and all(r.source == "stub" for r in response.results):
            logger.warning(
                f"Web search returned stub results for template {template_id} "
                f"(likely provider rate-limit) — skipping context injection"
            )
            return None
        return _format_results(response, config["focus"])
    except Exception as exc:
        logger.warning(f"Web search failed for template {template_id} (query={query!r}): {exc}")
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _create_default_client() -> WebSearchClient:
    """Return a WebSearchClient configured from environment variables."""
    for provider in ("brave", "tavily", "serpapi"):
        if os.getenv(f"{provider.upper()}_API_KEY"):
            return WebSearchClient(provider=provider)
    return WebSearchClient(provider="stub")


def _format_results(response: SearchResponse, focus: str) -> Optional[str]:
    """Format search results into a concise, prompt-ready block (≤ ~300 tokens)."""
    if not response.results:
        return None

    lines = [f"LIVE WEB DATA ({focus}, fetched at generation time):"]
    for i, result in enumerate(response.results[:5], start=1):
        date_part = f" [{result.published_date}]" if result.published_date else ""
        source_part = f" — {result.source}" if result.source else ""
        snippet = result.snippet.strip()
        # Trim long snippets to keep token budget reasonable
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        lines.append(f"{i}. {result.title}{date_part}{source_part}: {snippet}")

    return "\n".join(lines)
