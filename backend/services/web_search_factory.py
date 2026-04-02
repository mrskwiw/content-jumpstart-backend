"""Factory for creating web search clients with user-specific API keys"""

import os
from sqlalchemy.orm import Session
from src.utils.web_search import WebSearchClient
from . import settings_service


def get_user_search_client(db: Session, user_id: int) -> WebSearchClient:
    """
    Get web search client configured with user's API keys from database.

    Falls back to environment variables if not configured in database.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Configured WebSearchClient
    """
    # Get user's web search configuration from database
    config = settings_service.get_web_search_config(db, user_id)

    provider = config["provider"]
    api_key = None

    # Get the appropriate API key based on provider
    if provider == "brave" and config["brave_api_key"]:
        api_key = config["brave_api_key"]
    elif provider == "tavily" and config["tavily_api_key"]:
        api_key = config["tavily_api_key"]
    elif provider == "serpapi" and config["serpapi_api_key"]:
        api_key = config["serpapi_api_key"]

    # If no key in database, check environment variables
    if not api_key and provider != "stub":
        if provider == "brave":
            api_key = os.getenv("BRAVE_API_KEY")
        elif provider == "tavily":
            api_key = os.getenv("TAVILY_API_KEY")
        elif provider == "serpapi":
            api_key = os.getenv("SERPAPI_API_KEY")

    # If still no key, fall back to stub mode
    if not api_key:
        provider = "stub"

    return WebSearchClient(provider=provider, api_key=api_key)
