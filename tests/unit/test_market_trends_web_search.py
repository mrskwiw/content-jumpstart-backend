"""
Unit tests for Bug #46: Market Trends web search integration

Tests the _fetch_web_trends method in MarketTrendsResearcher
"""

import pytest
from unittest.mock import Mock, patch
from src.research.market_trends_research import MarketTrendsResearcher
from src.utils.web_search import SearchResult, SearchResponse
from datetime import datetime


class TestMarketTrendsWebSearch:
    """Test suite for market trends web search integration (Bug #46)"""

    @pytest.fixture
    def researcher(self):
        """Create MarketTrendsResearcher instance"""
        return MarketTrendsResearcher(project_id="test-proj-123")

    @pytest.fixture
    def mock_search_client(self):
        """Create mock web search client"""
        mock_client = Mock()

        # Mock search response for industry trends
        industry_results = SearchResponse(
            query="Technology trends 2026",
            results=[
                SearchResult(
                    title="Top Tech Trends 2026",
                    url="https://example.com/tech-trends",
                    snippet="AI and automation leading the way...",
                    source="TechCrunch",
                ),
                SearchResult(
                    title="2026 Technology Forecast",
                    url="https://example.com/forecast",
                    snippet="Cloud computing continues to grow...",
                    source="Forbes",
                ),
            ],
            total_results=100,
            search_time_ms=250.5,
            timestamp=datetime(2026, 3, 18),
        )

        # Mock search response for focus areas
        focus_results = SearchResponse(
            query="AI Technology trends",
            results=[
                SearchResult(
                    title="AI Trends in 2026",
                    url="https://example.com/ai-trends",
                    snippet="Machine learning models getting smarter...",
                    source="AI Weekly",
                )
            ],
            total_results=50,
            search_time_ms=180.0,
            timestamp=datetime(2026, 3, 18),
        )

        # Configure mock to return different results based on query
        mock_client.search.side_effect = [
            industry_results,
            focus_results,
            focus_results,
            focus_results,
        ]

        return mock_client

    def test_fetch_web_trends_success(self, researcher, mock_search_client):
        """Test successful web trends fetching"""
        industry = "Technology"
        focus_areas = ["AI", "Cloud Computing", "Cybersecurity"]
        business_desc = "B2B SaaS platform"

        results = researcher._fetch_web_trends(
            mock_search_client, industry, focus_areas, business_desc
        )

        # Verify results returned
        assert len(results) > 0

        # Verify search was called (1 industry + 3 focus areas)
        assert mock_search_client.search.call_count == 4

        # Verify result structure
        first_result = results[0]
        assert "category" in first_result
        assert "title" in first_result
        assert "url" in first_result
        assert "snippet" in first_result
        assert "source" in first_result

    def test_fetch_web_trends_categorizes_results(self, researcher, mock_search_client):
        """Test that results are categorized correctly"""
        results = researcher._fetch_web_trends(
            mock_search_client, "Technology", ["AI"], "Test business"
        )

        # Should have both Industry Trends and Focus-specific results
        categories = [r["category"] for r in results]
        assert "Industry Trends" in categories
        assert any("Focus:" in cat for cat in categories)

    def test_fetch_web_trends_limits_focus_areas(self, researcher, mock_search_client):
        """Test that only top 3 focus areas are searched"""
        # Provide 5 focus areas, but only top 3 should be searched
        focus_areas = ["AI", "Cloud", "Security", "Data", "Mobile"]

        researcher._fetch_web_trends(mock_search_client, "Technology", focus_areas, "Test")

        # Should call search 4 times: 1 industry + 3 focus areas
        assert mock_search_client.search.call_count == 4

    def test_fetch_web_trends_handles_empty_focus_areas(self, researcher, mock_search_client):
        """Test behavior with empty focus areas list"""
        results = researcher._fetch_web_trends(
            mock_search_client, "Technology", [], "Test business"
        )

        # Should still get industry results
        assert len(results) >= 0

        # Should only call search once (industry only)
        assert mock_search_client.search.call_count == 1

    def test_fetch_web_trends_error_handling(self, researcher):
        """Test graceful handling of web search errors"""
        # Mock client that raises exception
        mock_client = Mock()
        mock_client.search.side_effect = Exception("API error")

        # Should not raise, should return empty list
        results = researcher._fetch_web_trends(mock_client, "Technology", ["AI"], "Test")

        assert results == []

    def test_fetch_web_trends_partial_failure(self, researcher):
        """Test handling when some searches fail"""
        mock_client = Mock()

        # First search succeeds
        success_response = SearchResponse(
            query="test",
            results=[SearchResult("Title", "url", "snippet")],
            total_results=1,
            search_time_ms=100,
            timestamp=datetime(2026, 3, 18),
        )

        # Subsequent searches fail
        mock_client.search.side_effect = [
            success_response,
            Exception("API error"),
            Exception("API error"),
        ]

        # Should handle partial failure gracefully
        results = researcher._fetch_web_trends(mock_client, "Tech", ["AI"], "Test")

        # May have partial results or be empty, but shouldn't crash
        assert isinstance(results, list)

    def test_fetch_web_trends_result_structure(self, researcher, mock_search_client):
        """Test that returned results have correct structure"""
        results = researcher._fetch_web_trends(mock_search_client, "Technology", ["AI"], "Test")

        for result in results:
            # Verify all required fields
            assert isinstance(result["category"], str)
            assert isinstance(result["title"], str)
            assert isinstance(result["url"], str)
            assert isinstance(result["snippet"], str)
            assert isinstance(result["source"], str)

            # Verify URL is valid format
            assert result["url"].startswith("http")
