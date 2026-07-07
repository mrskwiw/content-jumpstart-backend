"""
Web Search Utility for Research Tools

Provides web search capabilities using Brave Search, Tavily, or SerpAPI.
Can be stubbed for development/testing.
"""

import os
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from .logger import logger


@dataclass
class SearchResult:
    """Individual search result"""

    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    source: Optional[str] = None


@dataclass
class SearchResponse:
    """Search API response"""

    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    timestamp: datetime


class WebSearchClient:
    """Web search client with support for multiple providers"""

    def __init__(
        self,
        provider: str = "stub",  # "brave", "tavily", "serpapi", or "stub"
        api_key: Optional[str] = None,
    ):
        """Initialize web search client

        Args:
            provider: Search provider ("brave", "tavily", "serpapi", or "stub")
            api_key: API key for the provider (not needed for stub)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")

        if provider not in ["stub", "brave", "tavily", "serpapi"]:
            raise ValueError(
                f"Unsupported provider: {provider}. Use 'brave', 'tavily', 'serpapi', or 'stub'"
            )

        if provider != "stub" and not self.api_key:
            logger.warning(
                f"No API key found for {provider}. "
                f"Set {provider.upper()}_API_KEY environment variable. "
                f"Falling back to stub mode."
            )
            self.provider = "stub"

        # Pre-load keys for every real provider so fallback dispatch uses the
        # correct credentials, not self.api_key (which belongs to the primary).
        # For the primary provider, prefer the explicitly-passed api_key.
        self._provider_keys: dict[str, Optional[str]] = {
            p: (self.api_key if p == provider else os.getenv(f"{p.upper()}_API_KEY"))
            for p in ("brave", "tavily", "serpapi")
        }

    def _available_fallbacks(self) -> list[str]:
        """Return configured fallback providers in priority order."""
        priority = ["brave", "tavily", "serpapi"]
        return [p for p in priority if p != self.provider and self._provider_keys.get(p)]

    def _redact(self, text: str) -> str:
        """Redact any known provider API key from *text* before logging.

        Provider errors (e.g. requests HTTPError from SerpAPI, which passes the
        key as a URL query param) can embed the API key in their string form.
        Strip every known key so secrets are never logged in clear text
        (Bug #180).
        """
        keys = [self.api_key, *self._provider_keys.values()]
        for key in keys:
            if key:
                text = text.replace(key, "***REDACTED***")
        return text

    def _dispatch(self, provider: str, query: str, max_results: int, **kwargs) -> SearchResponse:
        """Call the named provider with its own credentials; raises on error."""
        key = self._provider_keys.get(provider)
        if provider == "brave":
            return self._search_brave(query, max_results, api_key=key, **kwargs)
        elif provider == "tavily":
            return self._search_tavily(query, max_results, api_key=key, **kwargs)
        elif provider == "serpapi":
            return self._search_serpapi(query, max_results, api_key=key, **kwargs)
        raise ValueError(f"Unknown provider: {provider}")

    def search(
        self,
        query: str,
        max_results: int = 10,
        search_type: str = "web",  # "web", "news", "images"
        **kwargs,
    ) -> SearchResponse:
        """Execute web search

        Args:
            query: Search query
            max_results: Maximum number of results to return
            search_type: Type of search ("web", "news", "images")
            **kwargs: Provider-specific parameters

        Returns:
            SearchResponse with results
        """
        logger.info(f"Web search: '{query}' (provider={self.provider}, max={max_results})")

        if self.provider == "stub":
            return self._search_stub(query, max_results)

        providers_to_try = [self.provider] + self._available_fallbacks()

        for i, provider in enumerate(providers_to_try):
            is_last = i == len(providers_to_try) - 1
            try:
                return self._dispatch(provider, query, max_results, **kwargs)
            except Exception as e:
                if is_last:
                    logger.error(
                        f"All search providers exhausted. Last error ({provider}): "
                        f"{self._redact(str(e))}. Returning empty results."
                    )
                else:
                    next_provider = providers_to_try[i + 1]
                    logger.warning(
                        f"{provider} search failed: {self._redact(str(e))}. "
                        f"Falling back to {next_provider}."
                    )

        return SearchResponse(
            query=query,
            results=[],
            total_results=0,
            search_time_ms=0.0,
            timestamp=datetime.now(),
        )

    def _search_brave(
        self, query: str, max_results: int, api_key: Optional[str] = None, **kwargs
    ) -> SearchResponse:
        """Search using Brave Search API

        Brave Search API: https://brave.com/search/api/
        """
        import requests

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key if api_key is not None else self.api_key,
        }
        params: dict[str, str | int] = {
            "q": query,
            "count": max_results,
        }

        start_time = datetime.now()
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        search_time = (datetime.now() - start_time).total_seconds() * 1000

        data = response.json()

        # Parse Brave results
        results = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    published_date=item.get("age"),
                    source="brave",
                )
            )

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_time_ms=search_time,
            timestamp=datetime.now(),
        )

    def _search_tavily(
        self, query: str, max_results: int, api_key: Optional[str] = None, **kwargs
    ) -> SearchResponse:
        """Search using Tavily API

        Tavily API: https://tavily.com/
        """
        import requests

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key if api_key is not None else self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",  # "basic" or "advanced"
            "include_answer": False,
            "include_raw_content": False,
        }

        start_time = datetime.now()
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        search_time = (datetime.now() - start_time).total_seconds() * 1000

        data = response.json()

        # Parse Tavily results
        results = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    published_date=item.get("published_date"),
                    source="tavily",
                )
            )

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_time_ms=search_time,
            timestamp=datetime.now(),
        )

    def _search_serpapi(
        self, query: str, max_results: int, api_key: Optional[str] = None, **kwargs
    ) -> SearchResponse:
        """Search using SerpAPI (Google Search)

        SerpAPI: https://serpapi.com/
        Provides real-time Google search results with rich structured data.
        """
        import requests

        url = "https://serpapi.com/search"
        params: dict[str, str | int | None] = {
            "q": query,
            "api_key": api_key if api_key is not None else self.api_key,
            "num": max_results,
            "engine": "google",  # Use Google search engine
        }

        start_time = datetime.now()
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        search_time = (datetime.now() - start_time).total_seconds() * 1000

        data = response.json()

        # Parse SerpAPI results (organic_results key for Google)
        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    published_date=item.get("date"),
                    source="serpapi",
                )
            )

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_time_ms=search_time,
            timestamp=datetime.now(),
        )

    def _search_stub(self, query: str, max_results: int) -> SearchResponse:
        """Stub implementation for development/testing

        Returns realistic-looking but synthetic results.
        In production, this should never be used - always use real search API.
        """
        logger.warning(
            "Using STUB web search (not real results). "
            "Configure BRAVE_API_KEY, TAVILY_API_KEY, or SERPAPI_API_KEY for production use."
        )

        # Return realistic stub data based on query
        results = []

        # Generate stub results
        for i in range(min(max_results, 5)):
            results.append(
                SearchResult(
                    title=f"Search result {i+1} for: {query}",
                    url=f"https://example.com/result-{i+1}",
                    snippet=f"This is a stub search result for the query '{query}'. "
                    f"In production, this would contain real search data from Brave or Tavily.",
                    published_date=None,
                    source="stub",
                )
            )

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_time_ms=0.0,
            timestamp=datetime.now(),
        )

    def search_competitors(
        self,
        business_description: str,
        industry: str,
        location: Optional[str] = None,
    ) -> SearchResponse:
        """Specialized search for competitor discovery

        Args:
            business_description: Business description
            industry: Industry/vertical
            location: Geographic location (optional)

        Returns:
            SearchResponse with competitor results
        """
        # Build optimized search query for competitors
        query_parts = [f"{industry} companies"]

        # Extract key terms from business description
        key_terms = self._extract_key_terms(business_description)
        if key_terms:
            query_parts.append(key_terms)

        if location:
            query_parts.append(f"in {location}")

        query = " ".join(query_parts)

        return self.search(query, max_results=10, search_type="web")

    def _extract_key_terms(self, text: str, max_terms: int = 3) -> str:
        """Extract key terms from text for search query optimization

        Simple implementation - can be enhanced with NLP.
        """
        # Remove common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "we",
            "they",
            "our",
            "help",
        }

        words = text.lower().split()
        key_words = [w for w in words if len(w) > 4 and w not in stop_words]

        return " ".join(key_words[:max_terms])


# Default client instance
_default_client: Optional[WebSearchClient] = None


def set_default_client(client: WebSearchClient) -> None:
    """Override the global default search client.

    Called by the backend service layer to inject a user-configured client
    (with DB-stored API keys) before executing a research tool, so that
    tools calling ``get_search_client()`` pick up the correct provider and key.

    Args:
        client: Configured WebSearchClient instance to use as the default
    """
    global _default_client
    _default_client = client


def get_search_client(provider: Optional[str] = None) -> WebSearchClient:
    """Get or create default web search client

    Args:
        provider: Search provider ("brave", "tavily", or "stub")

    Returns:
        WebSearchClient instance
    """
    global _default_client

    if _default_client is None or (provider and provider != _default_client.provider):
        # Determine provider from environment or default to stub
        if provider is None:
            if os.getenv("BRAVE_API_KEY"):
                provider = "brave"
            elif os.getenv("TAVILY_API_KEY"):
                provider = "tavily"
            else:
                provider = "stub"
                logger.warning(
                    "No web search API key configured. Using stub mode. "
                    "Set BRAVE_API_KEY or TAVILY_API_KEY for production."
                )

        _default_client = WebSearchClient(provider=provider)

    return _default_client
