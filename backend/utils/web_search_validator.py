"""Web Search Configuration Validator

Validates that web search API keys are configured before allowing
research tools that require real web data to execute.
"""

import os
from sqlalchemy.orm import Session
from typing import Dict, Tuple

from ..services import settings_service


def is_web_search_configured(db: Session, user_id: int) -> Tuple[bool, str]:
    """
    Check if user has web search configured (real API key, not stub).

    Args:
        db: Database session
        user_id: User ID to check configuration for

    Returns:
        Tuple of (is_configured, provider_name or error_message)

    Examples:
        >>> is_configured, msg = is_web_search_configured(db, user_id)
        >>> if is_configured:
        ...     print(f"Using {msg}")  # "brave" or "tavily"
        ... else:
        ...     print(f"Error: {msg}")  # Error message
    """
    # Get user's web search configuration
    config = settings_service.get_web_search_config(db, user_id)

    provider = config["provider"]

    # Check if stub mode (not configured)
    if provider == "stub":
        # Check if any API keys available in database or environment
        has_brave = config.get("brave_api_key") or os.getenv("BRAVE_API_KEY")
        has_tavily = config.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")

        if not (has_brave or has_tavily):
            return (
                False,
                "No web search API key configured. Please add BRAVE_API_KEY or TAVILY_API_KEY in Settings.",
            )

        # Has keys but provider set to stub - still not configured for real use
        return (
            False,
            "Web search provider set to 'stub'. Please select a real provider (Brave or Tavily) in Settings.",
        )

    # Check that the selected provider has an API key
    if provider == "brave":
        api_key = config.get("brave_api_key") or os.getenv("BRAVE_API_KEY")
        if not api_key:
            return (
                False,
                "Brave Search selected but no API key configured. Please add BRAVE_API_KEY in Settings.",
            )
        return True, "brave"

    elif provider == "tavily":
        api_key = config.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")
        if not api_key:
            return (
                False,
                "Tavily Search selected but no API key configured. Please add TAVILY_API_KEY in Settings.",
            )
        return True, "tavily"

    elif provider == "serpapi":
        api_key = config.get("serpapi_api_key") or os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return (
                False,
                "SerpAPI selected but no API key configured. Please add your SerpAPI key in Settings.",
            )
        return True, "serpapi"

    # Unknown provider
    return False, f"Unknown web search provider: {provider}"


def get_web_search_setup_instructions() -> Dict[str, Dict[str, str]]:
    """
    Get setup instructions for web search API providers.

    Returns:
        Dictionary with provider setup information
    """
    return {
        "brave": {
            "name": "Brave Search API",
            "url": "https://brave.com/search/api/",
            "pricing": "$5/month for 2,000 queries",
            "free_tier": "Yes - 2,000 queries/month",
            "setup": "1. Sign up at brave.com/search/api/\n2. Get API key from dashboard\n3. Add to Settings page",
        },
        "tavily": {
            "name": "Tavily Search API",
            "url": "https://tavily.com/",
            "pricing": "$0.001 per search",
            "free_tier": "Yes - 1,000 searches/month",
            "setup": "1. Sign up at tavily.com\n2. Get API key from dashboard\n3. Add to Settings page",
        },
    }
