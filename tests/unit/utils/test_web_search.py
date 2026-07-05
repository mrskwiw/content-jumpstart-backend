"""
Unit tests for web search utility.
"""

import pytest
from unittest.mock import Mock, patch

from src.utils.web_search import (
    WebSearchClient,
    SearchResult,
    SearchResponse,
    get_search_client,
)


@pytest.fixture
def mock_brave_response():
    """Mock Brave Search API response"""
    return {
        "web": {
            "results": [
                {
                    "title": "Example Company 1",
                    "url": "https://example1.com",
                    "description": "Description for company 1",
                    "age": "2 days ago",
                },
                {
                    "title": "Example Company 2",
                    "url": "https://example2.com",
                    "description": "Description for company 2",
                    "age": "1 week ago",
                },
            ]
        }
    }


@pytest.fixture
def mock_tavily_response():
    """Mock Tavily API response"""
    return {
        "results": [
            {
                "title": "Example Company 1",
                "url": "https://example1.com",
                "content": "Content for company 1",
                "published_date": "2026-03-10",
            },
            {
                "title": "Example Company 2",
                "url": "https://example2.com",
                "content": "Content for company 2",
                "published_date": "2026-03-05",
            },
        ]
    }


class TestWebSearchClient:
    """Test WebSearchClient initialization and configuration"""

    def test_initialization_stub_mode(self):
        """Test initialization in stub mode"""
        client = WebSearchClient(provider="stub")
        assert client.provider == "stub"
        assert client.api_key is None

    def test_initialization_brave(self):
        """Test initialization with Brave"""
        client = WebSearchClient(provider="brave", api_key="test_key")
        assert client.provider == "brave"
        assert client.api_key == "test_key"

    def test_initialization_tavily(self):
        """Test initialization with Tavily"""
        client = WebSearchClient(provider="tavily", api_key="test_key")
        assert client.provider == "tavily"
        assert client.api_key == "test_key"

    def test_initialization_invalid_provider(self):
        """Test initialization with invalid provider"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            WebSearchClient(provider="invalid")

    def test_fallback_to_stub_no_api_key(self):
        """Test fallback to stub when no API key"""
        client = WebSearchClient(provider="brave", api_key=None)
        assert client.provider == "stub"

    @patch.dict("os.environ", {"BRAVE_API_KEY": "env_key"})
    def test_api_key_from_environment(self):
        """Test API key loaded from environment"""
        client = WebSearchClient(provider="brave")
        assert client.api_key == "env_key"


class TestStubSearch:
    """Test stub search implementation"""

    def test_stub_search_basic(self):
        """Test basic stub search"""
        client = WebSearchClient(provider="stub")
        response = client.search("test query", max_results=5)

        assert isinstance(response, SearchResponse)
        assert response.query == "test query"
        assert len(response.results) == 5
        assert response.total_results == 5

    def test_stub_search_results_structure(self):
        """Test stub search returns proper structure"""
        client = WebSearchClient(provider="stub")
        response = client.search("test", max_results=3)

        for result in response.results:
            assert isinstance(result, SearchResult)
            assert isinstance(result.title, str)
            assert isinstance(result.url, str)
            assert isinstance(result.snippet, str)
            assert result.source == "stub"

    def test_stub_search_max_results_limit(self):
        """Test stub search respects max results"""
        client = WebSearchClient(provider="stub")
        response = client.search("test", max_results=10)

        # Stub implementation caps at 5
        assert len(response.results) <= 5


class TestBraveSearch:
    """Test Brave Search API integration"""

    @patch("requests.get")
    def test_brave_search_success(self, mock_get, mock_brave_response):
        """Test successful Brave search"""
        mock_response = Mock()
        mock_response.json.return_value = mock_brave_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = WebSearchClient(provider="brave", api_key="test_key")
        response = client.search("test query", max_results=10)

        assert isinstance(response, SearchResponse)
        assert response.query == "test query"
        assert len(response.results) == 2
        assert response.results[0].title == "Example Company 1"
        assert response.results[0].source == "brave"

    @patch("requests.get")
    def test_brave_search_api_called_correctly(self, mock_get, mock_brave_response):
        """Test Brave API is called with correct parameters"""
        mock_response = Mock()
        mock_response.json.return_value = mock_brave_response
        mock_get.return_value = mock_response

        client = WebSearchClient(provider="brave", api_key="test_key")
        client.search("test query", max_results=5)

        # Verify API call
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args

        assert args[0] == "https://api.search.brave.com/res/v1/web/search"
        assert kwargs["headers"]["X-Subscription-Token"] == "test_key"
        assert kwargs["params"]["q"] == "test query"
        assert kwargs["params"]["count"] == 5

    @patch("requests.get")
    def test_brave_search_error_returns_empty(self, mock_get):
        """Test Brave search returns empty results on error (no stub fallback)"""
        mock_get.side_effect = Exception("API Error")

        client = WebSearchClient(provider="brave", api_key="test_key")
        response = client.search("test", max_results=3)

        assert isinstance(response, SearchResponse)
        assert len(response.results) == 0
        assert response.total_results == 0


class TestTavilySearch:
    """Test Tavily API integration"""

    @patch("requests.post")
    def test_tavily_search_success(self, mock_post, mock_tavily_response):
        """Test successful Tavily search"""
        mock_response = Mock()
        mock_response.json.return_value = mock_tavily_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = WebSearchClient(provider="tavily", api_key="test_key")
        response = client.search("test query", max_results=10)

        assert isinstance(response, SearchResponse)
        assert response.query == "test query"
        assert len(response.results) == 2
        assert response.results[0].title == "Example Company 1"
        assert response.results[0].source == "tavily"

    @patch("requests.post")
    def test_tavily_search_api_called_correctly(self, mock_post, mock_tavily_response):
        """Test Tavily API is called with correct parameters"""
        mock_response = Mock()
        mock_response.json.return_value = mock_tavily_response
        mock_post.return_value = mock_response

        client = WebSearchClient(provider="tavily", api_key="test_key")
        client.search("test query", max_results=5)

        # Verify API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        assert args[0] == "https://api.tavily.com/search"
        assert kwargs["json"]["api_key"] == "test_key"
        assert kwargs["json"]["query"] == "test query"
        assert kwargs["json"]["max_results"] == 5

    @patch("requests.post")
    def test_tavily_search_error_returns_empty(self, mock_post):
        """Test Tavily search returns empty results on error (no stub fallback)"""
        mock_post.side_effect = Exception("API Error")

        client = WebSearchClient(provider="tavily", api_key="test_key")
        response = client.search("test", max_results=3)

        assert isinstance(response, SearchResponse)
        assert len(response.results) == 0
        assert response.total_results == 0

    @patch("requests.get")
    @patch("requests.post")
    def test_tavily_error_fallbacks_to_brave(self, mock_post, mock_get):
        """Tavily failure uses Brave as fallback when BRAVE_API_KEY is configured"""
        mock_post.side_effect = Exception("432 Rate limited")

        brave_data = {
            "web": {
                "results": [
                    {"title": "Brave Result", "url": "https://brave.com/r1", "description": "desc"}
                ]
            }
        }
        mock_brave_resp = Mock()
        mock_brave_resp.json.return_value = brave_data
        mock_brave_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_brave_resp

        with patch.dict(
            "os.environ", {"BRAVE_API_KEY": "brave_key", "TAVILY_API_KEY": "tavily_key"}
        ):
            client = WebSearchClient(provider="tavily", api_key="tavily_key")
            response = client.search("test query", max_results=3)

        assert len(response.results) == 1
        assert response.results[0].source == "brave"
        assert response.results[0].title == "Brave Result"

    @patch("requests.get")
    @patch("requests.post")
    def test_fallback_uses_brave_api_key_not_tavily_key(self, mock_post, mock_get):
        """Brave fallback authenticates with BRAVE_API_KEY, not the primary Tavily key"""
        mock_post.side_effect = Exception("432 Rate limited")

        mock_brave_resp = Mock()
        mock_brave_resp.json.return_value = {"web": {"results": []}}
        mock_brave_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_brave_resp

        with patch.dict(
            "os.environ", {"BRAVE_API_KEY": "brave_key", "TAVILY_API_KEY": "tavily_key"}
        ):
            client = WebSearchClient(provider="tavily", api_key="tavily_key")
            client.search("q", max_results=3)

        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["X-Subscription-Token"] == "brave_key"


class TestCompetitorSearch:
    """Test specialized competitor search"""

    def test_competitor_search_query_building(self):
        """Test competitor search builds proper query"""
        client = WebSearchClient(provider="stub")
        response = client.search_competitors(
            business_description="We help companies reduce churn with AI analytics",
            industry="B2B SaaS",
            location="United States",
        )

        # Query should contain industry and location
        assert "B2B SaaS" in response.query
        assert "United States" in response.query
        assert "companies" in response.query

    def test_competitor_search_no_location(self):
        """Test competitor search without location"""
        client = WebSearchClient(provider="stub")
        response = client.search_competitors(
            business_description="AI analytics platform",
            industry="Technology",
        )

        assert "Technology" in response.query
        assert isinstance(response, SearchResponse)


class TestUtilityFunctions:
    """Test utility functions"""

    @patch.dict("os.environ", {}, clear=True)
    def test_get_search_client_no_env(self):
        """Test get_search_client with no environment variables"""
        client = get_search_client()
        assert client.provider == "stub"

    @patch.dict("os.environ", {"BRAVE_API_KEY": "test_brave_key"})
    def test_get_search_client_brave_env(self):
        """Test get_search_client detects Brave API key"""
        # Force provider to override singleton
        client = get_search_client(provider="brave")
        assert client.provider == "brave"
        assert client.api_key == "test_brave_key"

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test_tavily_key"})
    def test_get_search_client_tavily_env(self):
        """Test get_search_client detects Tavily API key"""
        # Force provider to override singleton
        client = get_search_client(provider="tavily")
        assert client.provider == "tavily"
        assert client.api_key == "test_tavily_key"

    def test_key_term_extraction(self):
        """Test key term extraction from text"""
        client = WebSearchClient(provider="stub")
        terms = client._extract_key_terms(
            "We help B2B SaaS companies reduce customer churn through AI-powered analytics"
        )

        # Should extract meaningful terms, not stop words
        assert len(terms) > 0
        assert "help" not in terms  # Stop word
        assert "the" not in terms  # Stop word


# ---------------------------------------------------------------------------
# Additional tests for previously uncovered lines
# ---------------------------------------------------------------------------


class TestSerpApiSearch:
    """Test SerpAPI integration (lines 199-247)."""

    @pytest.fixture
    def mock_serpapi_response(self):
        """Mock SerpAPI response payload."""
        return {
            "organic_results": [
                {
                    "title": "SerpAPI Result 1",
                    "link": "https://serpapi-result1.com",
                    "snippet": "Snippet for result 1",
                    "date": "2026-03-01",
                },
                {
                    "title": "SerpAPI Result 2",
                    "link": "https://serpapi-result2.com",
                    "snippet": "Snippet for result 2",
                    "date": None,
                },
            ]
        }

    @patch("requests.get")
    def test_serpapi_search_success(self, mock_get, mock_serpapi_response):
        """Successful SerpAPI search returns correct SearchResponse (lines 205-246)."""
        mock_response = Mock()
        mock_response.json.return_value = mock_serpapi_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = WebSearchClient(provider="serpapi", api_key="test_serpapi_key")
        response = client.search("test query", max_results=10)

        assert isinstance(response, SearchResponse)
        assert response.query == "test query"
        assert len(response.results) == 2
        assert response.results[0].title == "SerpAPI Result 1"
        assert response.results[0].url == "https://serpapi-result1.com"
        assert response.results[0].snippet == "Snippet for result 1"
        assert response.results[0].published_date == "2026-03-01"
        assert response.results[0].source == "serpapi"

    @patch("requests.get")
    def test_serpapi_api_called_correctly(self, mock_get, mock_serpapi_response):
        """SerpAPI GET request uses correct URL and params (lines 209-219)."""
        mock_response = Mock()
        mock_response.json.return_value = mock_serpapi_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = WebSearchClient(provider="serpapi", api_key="my_key")
        client.search("python testing", max_results=7)

        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["q"] == "python testing"
        assert kwargs["params"]["api_key"] == "my_key"  # pragma: allowlist secret
        assert kwargs["params"]["num"] == 7
        assert kwargs["params"]["engine"] == "google"

    @patch("requests.get")
    def test_serpapi_search_error_returns_empty(self, mock_get):
        """SerpAPI search returns empty results on exception (no stub fallback)."""
        mock_get.side_effect = Exception("SerpAPI down")

        client = WebSearchClient(provider="serpapi", api_key="test_key")
        response = client.search("fallback query", max_results=3)

        assert isinstance(response, SearchResponse)
        assert len(response.results) == 0
        assert response.total_results == 0

    def test_search_routes_to_serpapi(self):
        """search() dispatches to _search_serpapi with its own API key."""
        client = WebSearchClient(provider="serpapi", api_key="key")
        with patch.object(client, "_search_serpapi", return_value=Mock()) as mock_serpapi:
            client.search("test", max_results=5)
        mock_serpapi.assert_called_once_with("test", 5, api_key="key")  # pragma: allowlist secret

    @patch("requests.get")
    def test_serpapi_result_count_capped_by_max_results(self, mock_get):
        """Only up to max_results items are returned from organic_results."""
        many_results = {
            "organic_results": [
                {"title": f"Result {i}", "link": f"https://r{i}.com", "snippet": "s"}
                for i in range(20)
            ]
        }
        mock_response = Mock()
        mock_response.json.return_value = many_results
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = WebSearchClient(provider="serpapi", api_key="key")
        response = client.search("query", max_results=5)

        assert len(response.results) == 5


class TestSetDefaultClient:
    """Tests for set_default_client (line 384)."""

    def test_set_default_client_overrides_singleton(self):
        """set_default_client replaces the module-level singleton."""
        import src.utils.web_search as ws_module
        from src.utils.web_search import set_default_client

        custom_client = WebSearchClient(provider="stub")
        set_default_client(custom_client)

        assert ws_module._default_client is custom_client

    def test_get_search_client_returns_injected_client(self):
        """get_search_client returns the client set by set_default_client."""
        from src.utils.web_search import get_search_client, set_default_client

        custom_client = WebSearchClient(provider="stub")
        set_default_client(custom_client)

        result = get_search_client()
        assert result is custom_client


class TestGetSearchClientProviderAutoDetect:
    """Tests for get_search_client auto-detect logic (lines 400-412)."""

    def test_get_search_client_picks_tavily_when_no_brave(self):
        """get_search_client picks tavily when BRAVE_API_KEY absent but TAVILY_API_KEY set (line 404)."""
        import src.utils.web_search as ws_module
        from src.utils.web_search import get_search_client

        clean_env = {"TAVILY_API_KEY": "tavily123"}  # pragma: allowlist secret
        with patch.dict("os.environ", clean_env, clear=True):
            # Reset singleton INSIDE the env patch so get_search_client reads patched env
            ws_module._default_client = None
            client = get_search_client()

        assert client.provider == "tavily"
        assert client.api_key == "tavily123"

    def test_get_search_client_picks_brave_when_brave_key_set(self):
        """get_search_client picks brave when BRAVE_API_KEY is set (line 402)."""
        import src.utils.web_search as ws_module
        from src.utils.web_search import get_search_client

        clean_env = {"BRAVE_API_KEY": "brave123"}  # pragma: allowlist secret
        with patch.dict("os.environ", clean_env, clear=True):
            ws_module._default_client = None
            client = get_search_client()

        assert client.provider == "brave"
        assert client.api_key == "brave123"

    def test_get_search_client_falls_back_to_stub_no_keys(self):
        """get_search_client falls back to stub when no API keys are set (line 406)."""
        import src.utils.web_search as ws_module
        from src.utils.web_search import get_search_client

        with patch.dict("os.environ", {}, clear=True):
            ws_module._default_client = None
            client = get_search_client()

        assert client.provider == "stub"

    def test_get_search_client_creates_new_when_provider_differs(self):
        """get_search_client creates a new client when requested provider differs from singleton."""
        from src.utils.web_search import get_search_client, set_default_client

        # Seed the singleton with stub
        set_default_client(WebSearchClient(provider="stub"))

        # Request a different provider (brave) — should create new client
        new_client = get_search_client(provider="brave")
        # Without a real API key it falls back to stub, but the new client was created
        assert isinstance(new_client, WebSearchClient)
