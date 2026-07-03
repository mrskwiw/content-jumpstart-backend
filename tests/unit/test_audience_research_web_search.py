"""
Unit tests for Bug #47: Audience Research web search integration

Tests the _fetch_web_audience_data method in AudienceResearcher
"""

import pytest
from unittest.mock import Mock
from src.research.audience_research import AudienceResearcher
from src.utils.web_search import SearchResult, SearchResponse
from datetime import datetime


class TestAudienceResearchWebSearch:
    """Test suite for audience research web search integration (Bug #47)"""

    @pytest.fixture
    def researcher(self):
        """Create AudienceResearcher instance"""
        return AudienceResearcher(project_id="test-proj-456")

    @pytest.fixture
    def mock_search_client(self):
        """Create mock web search client"""
        mock_client = Mock()

        # Mock demographics search results
        demographics_results = SearchResponse(
            query="Tech professionals demographics behavior Technology",
            results=[
                SearchResult(
                    title="Tech Professional Demographics 2026",
                    url="https://example.com/tech-demographics",
                    snippet="Tech professionals aged 25-44, high education levels...",
                    source="LinkedIn Research",
                ),
                SearchResult(
                    title="Software Developer Survey Results",
                    url="https://example.com/dev-survey",
                    snippet="Remote work preferences, tool usage patterns...",
                    source="Stack Overflow",
                ),
            ],
            total_results=200,
            search_time_ms=300.0,
            timestamp=datetime(2026, 3, 18),
        )

        # Mock trends search results
        trends_results = SearchResponse(
            query="Technology audience trends 2026",
            results=[
                SearchResult(
                    title="Technology Audience Trends 2026",
                    url="https://example.com/trends",
                    snippet="Rising interest in AI, declining interest in blockchain...",
                    source="Gartner",
                )
            ],
            total_results=100,
            search_time_ms=250.0,
            timestamp=datetime(2026, 3, 18),
        )

        mock_client.search.side_effect = [demographics_results, trends_results]

        return mock_client

    def test_fetch_web_audience_data_success(self, researcher, mock_search_client):
        """Test successful web audience data fetching"""
        industry = "Technology"
        target_audience = "Tech professionals and software developers"
        business_desc = "B2B SaaS platform for developers"

        results = researcher._fetch_web_audience_data(
            mock_search_client, industry, target_audience, business_desc
        )

        # Verify results returned
        assert len(results) > 0

        # Verify search was called twice (demographics + trends)
        assert mock_search_client.search.call_count == 2

        # Verify result structure
        first_result = results[0]
        assert "category" in first_result
        assert "title" in first_result
        assert "url" in first_result
        assert "snippet" in first_result
        assert "source" in first_result

    def test_fetch_web_audience_data_categorizes_results(self, researcher, mock_search_client):
        """Test that results are categorized correctly"""
        results = researcher._fetch_web_audience_data(
            mock_search_client, "Technology", "Developers", "Dev tools"
        )

        # Should have both demographics and trends categories
        categories = [r["category"] for r in results]
        assert "Audience Demographics" in categories
        assert "Industry Audience Trends" in categories

    def test_fetch_web_audience_data_error_handling(self, researcher):
        """Test graceful handling of web search errors"""
        # Mock client that raises exception
        mock_client = Mock()
        mock_client.search.side_effect = Exception("Network error")

        # Should not raise, should return empty list
        results = researcher._fetch_web_audience_data(mock_client, "Tech", "Developers", "SaaS")

        assert results == []

    def test_fetch_web_audience_data_result_structure(self, researcher, mock_search_client):
        """Test that returned results have correct structure"""
        results = researcher._fetch_web_audience_data(
            mock_search_client, "Technology", "Tech professionals", "B2B SaaS"
        )

        for result in results:
            # Verify all required fields
            assert isinstance(result["category"], str)
            assert isinstance(result["title"], str)
            assert isinstance(result["url"], str)
            assert isinstance(result["snippet"], str)
            assert isinstance(result["source"], str)

            # Verify URL format
            assert result["url"].startswith("http")

    def test_fetch_web_audience_data_census_note(self, researcher):
        """Test that census integration note is documented in method"""
        # Verify the method docstring mentions census integration
        import inspect

        docstring = inspect.getdoc(researcher._fetch_web_audience_data)

        assert "Census" in docstring or "census" in docstring
        assert "Task #46" in docstring or "pending" in docstring.lower()

    def test_fetch_web_audience_data_with_special_characters(self, researcher, mock_search_client):
        """Test handling of target audience with special characters"""
        # Target audience with special characters
        target_audience = "C-Suite Executives (CEO, CTO, CFO) & Decision-Makers"

        results = researcher._fetch_web_audience_data(
            mock_search_client, "Enterprise Software", target_audience, "Enterprise SaaS"
        )

        # Should handle special characters gracefully
        assert isinstance(results, list)
        assert mock_search_client.search.called
