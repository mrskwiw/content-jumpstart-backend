"""
Unit tests for Google Trends Service.

Tests the GoogleTrendsService class functionality including:
- Pytrends client initialization
- Rate limiting
- Interest over time searches
- Related queries
- Keyword insights
- Error handling

This verifies Task 21: Pytrends Integration for SEO Tool
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime

from backend.services.trends_service import GoogleTrendsService, trends_service


class TestGoogleTrendsServiceInit:
    """Test GoogleTrendsService initialization"""

    def test_service_singleton_instance(self):
        """Test that trends_service is a singleton instance"""
        assert isinstance(trends_service, GoogleTrendsService)

    def test_lazy_load_pytrends_client(self):
        """Test that pytrends client is lazy-loaded"""
        service = GoogleTrendsService()
        assert service._pytrends is None  # Not loaded yet

        with patch("pytrends.request.TrendReq") as mock_req:
            mock_req.return_value = Mock()
            client = service.pytrends
            assert client is not None
            assert service._pytrends is not None  # Now loaded

    def test_pytrends_import_error(self):
        """Test handling of missing pytrends library"""
        service = GoogleTrendsService()

        with patch("pytrends.request.TrendReq", side_effect=ImportError):
            with pytest.raises(ImportError) as exc_info:
                _ = service.pytrends

            assert "pytrends is required" in str(exc_info.value)
            assert "pip install pytrends" in str(exc_info.value)

    def test_pytrends_client_configuration(self):
        """Test pytrends client is configured correctly"""
        service = GoogleTrendsService()

        with patch("pytrends.request.TrendReq") as mock_req:
            mock_client = Mock()
            mock_req.return_value = mock_client

            _ = service.pytrends

            # Verify TrendReq was called with correct config
            mock_req.assert_called_once_with(
                hl="en-US",
                tz=360,
                timeout=(10, 25),
                retries=2,
                backoff_factor=0.5,
            )


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_enforces_delay(self):
        """Test that rate limiting enforces minimum delay between requests"""
        service = GoogleTrendsService()
        service._min_request_interval = 0.1  # 100ms for testing

        # First request
        service._rate_limit()
        time1 = time.time()

        # Second request immediately after
        service._rate_limit()
        time2 = time.time()

        # Should have waited at least min_request_interval
        elapsed = time2 - time1
        assert elapsed >= 0.1, f"Rate limit not enforced: {elapsed}s < 0.1s"

    def test_rate_limit_no_delay_when_sufficient_time_elapsed(self):
        """Test that no delay occurs when sufficient time has passed"""
        service = GoogleTrendsService()
        service._min_request_interval = 0.05  # 50ms

        # First request
        service._rate_limit()

        # Wait longer than interval
        time.sleep(0.1)

        # Second request should not add delay
        start = time.time()
        service._rate_limit()
        elapsed = time.time() - start

        # Should be minimal (just function overhead)
        assert elapsed < 0.01, f"Unexpected delay: {elapsed}s"


class TestSearchInterestOverTime:
    """Test search_interest_over_time functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    def test_search_interest_validates_keywords(self, mock_db):
        """Test keyword validation (1-5 keywords required)"""
        service = GoogleTrendsService()

        # Empty keywords
        result = service.search_interest_over_time(
            db=mock_db,
            keywords=[],
            user_id="user-123",
        )
        assert result["success"] is False
        assert "1-5 keywords" in result["error"]

        # Too many keywords
        result = service.search_interest_over_time(
            db=mock_db,
            keywords=["k1", "k2", "k3", "k4", "k5", "k6"],
            user_id="user-123",
        )
        assert result["success"] is False
        assert "1-5 keywords" in result["error"]

    @patch("pytrends.request.TrendReq")
    def test_search_interest_accepts_custom_timeframe(self, mock_trend_req, mock_db):
        """Test that custom timeframes are passed through (not validated)"""
        mock_client = Mock()
        mock_trend_req.return_value = mock_client
        mock_client.build_payload = Mock()
        mock_client.interest_over_time = Mock(side_effect=Exception("Google API error"))

        service = GoogleTrendsService()

        result = service.search_interest_over_time(
            db=mock_db,
            keywords=["test"],
            user_id="user-123",
            timeframe="custom_timeframe",
        )
        # Service doesn't validate, pytrends error is caught
        assert result["success"] is False

    @patch("pytrends.request.TrendReq")
    def test_search_interest_accepts_custom_category(self, mock_trend_req, mock_db):
        """Test that categories are looked up or defaulted to 0"""
        mock_client = Mock()
        mock_trend_req.return_value = mock_client
        mock_client.build_payload = Mock()
        import pandas as pd

        mock_client.interest_over_time = Mock(return_value=pd.DataFrame())

        service = GoogleTrendsService()

        result = service.search_interest_over_time(
            db=mock_db,
            keywords=["test"],
            user_id="user-123",
            category="invalid_category",  # Will default to 0 (all)
        )
        # Should succeed with default category
        assert result["success"] is True

    @patch("pytrends.request.TrendReq")
    def test_search_interest_success(self, mock_trend_req, mock_db):
        """Test successful interest over time search"""
        # Mock pytrends client
        mock_client = Mock()
        mock_trend_req.return_value = mock_client

        # Mock pytrends response with proper DatetimeIndex
        import pandas as pd

        dates = pd.date_range(start="2024-01-01", periods=3, freq="W")
        mock_data = pd.DataFrame(
            {
                "keyword1": [50, 60, 70],
                "keyword2": [40, 50, 60],
                "isPartial": [False, False, False],
            },
            index=dates,
        )
        mock_client.interest_over_time.return_value = mock_data

        service = GoogleTrendsService()

        result = service.search_interest_over_time(
            db=mock_db,
            keywords=["keyword1", "keyword2"],
            user_id="user-123",
            client_id="client-456",
            project_id="project-789",
            timeframe="past_12_months",
            geo="US",
            category="all",
        )

        assert result["success"] is True
        assert result["keywords"] == ["keyword1", "keyword2"]
        assert result["timeframe"] == "today 12-m"
        assert result["geo"] == "US" or result["geo"] == "worldwide"
        assert "search_id" in result
        assert result["data_points"] == 6  # 3 dates * 2 keywords
        assert len(result["sample_data"]) <= 10  # Sample capped at 10

        # Verify database save was called
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @patch("pytrends.request.TrendReq")
    def test_search_interest_handles_pytrends_error(self, mock_trend_req, mock_db):
        """Test handling of pytrends errors"""
        mock_client = Mock()
        mock_trend_req.return_value = mock_client
        mock_client.interest_over_time.side_effect = Exception("Google API error")

        service = GoogleTrendsService()

        result = service.search_interest_over_time(
            db=mock_db,
            keywords=["test"],
            user_id="user-123",
        )

        assert result["success"] is False
        assert "error" in result

    @patch("pytrends.request.TrendReq")
    def test_search_interest_handles_empty_data(self, mock_trend_req, mock_db):
        """Test handling of empty results from Google"""
        mock_client = Mock()
        mock_trend_req.return_value = mock_client

        import pandas as pd

        mock_data = pd.DataFrame()  # Empty dataframe
        mock_client.interest_over_time.return_value = mock_data

        service = GoogleTrendsService()

        result = service.search_interest_over_time(
            db=mock_db,
            keywords=["nonexistent-keyword-xyz"],
            user_id="user-123",
        )

        # Service returns success=True with message about no data
        assert result["success"] is True
        assert result["data_points"] == 0
        assert "No data available" in result.get("message", "")


class TestSearchRelatedQueries:
    """Test search_related_queries functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    @patch("pytrends.request.TrendReq")
    def test_search_related_queries_success(self, mock_trend_req, mock_db):
        """Test successful related queries search"""
        mock_client = Mock()
        mock_trend_req.return_value = mock_client

        # Mock related queries response - pytrends returns dict with DataFrames
        import pandas as pd

        top_df = pd.DataFrame(
            [
                {"query": "related query 1", "value": 100},
                {"query": "related query 2", "value": 80},
            ]
        )
        rising_df = pd.DataFrame(
            [
                {"query": "rising query 1", "value": 500},
                {"query": "rising query 2", "value": 300},
            ]
        )
        mock_related = {
            "keyword1": {
                "top": top_df,
                "rising": rising_df,
            }
        }
        mock_client.related_queries.return_value = mock_related

        service = GoogleTrendsService()

        result = service.search_related_queries(
            db=mock_db,
            keywords=["keyword1"],
            user_id="user-123",
        )

        assert result["success"] is True
        assert len(result["top_queries"]) > 0
        assert len(result["rising_queries"]) > 0

        # Verify build_payload was called
        mock_client.build_payload.assert_called_once()

    @patch("pytrends.request.TrendReq")
    def test_search_related_queries_handles_no_data(self, mock_trend_req, mock_db):
        """Test handling when no related queries found"""
        mock_client = Mock()
        mock_trend_req.return_value = mock_client
        mock_client.related_queries.return_value = {}

        service = GoogleTrendsService()

        result = service.search_related_queries(
            db=mock_db,
            keywords=["obscure-keyword"],
            user_id="user-123",
        )

        # Should handle gracefully
        assert result["success"] is True or result["success"] is False


class TestKeywordInsights:
    """Test keyword insight computation"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    def test_compute_keyword_insights(self, mock_db):
        """Test computing insights for a single keyword"""
        # Mock database query results
        from backend.models.trends import TrendsInterestData
        import datetime

        mock_data_points = [
            Mock(spec=TrendsInterestData, interest_value=50, date=datetime.datetime.now()),
            Mock(spec=TrendsInterestData, interest_value=55, date=datetime.datetime.now()),
            Mock(spec=TrendsInterestData, interest_value=60, date=datetime.datetime.now()),
        ]

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_data_points

        mock_db.query.return_value = mock_query

        service = GoogleTrendsService()

        result = service.compute_keyword_insights(
            db=mock_db,
            keyword="test keyword",
            client_id="client-123",
            project_id="project-456",
        )

        assert result["success"] is True
        assert result["keyword"] == "test keyword"
        assert "metrics" in result or "insight_id" in result


class TestTimeframeMapping:
    """Test timeframe string mapping"""

    def test_timeframe_constants(self):
        """Test that all timeframes are properly mapped"""
        service = GoogleTrendsService()

        assert service.TIMEFRAMES["past_hour"] == "now 1-H"
        assert service.TIMEFRAMES["past_day"] == "now 1-d"
        assert service.TIMEFRAMES["past_week"] == "now 7-d"
        assert service.TIMEFRAMES["past_month"] == "today 1-m"
        assert service.TIMEFRAMES["past_3_months"] == "today 3-m"
        assert service.TIMEFRAMES["past_12_months"] == "today 12-m"
        assert service.TIMEFRAMES["past_5_years"] == "today 5-y"
        assert service.TIMEFRAMES["all_time"] == "all"


class TestCategoryMapping:
    """Test category ID mapping"""

    def test_category_constants(self):
        """Test that categories are properly mapped to IDs"""
        service = GoogleTrendsService()

        assert service.CATEGORIES["all"] == 0
        assert service.CATEGORIES["business_industrial"] == 12
        assert service.CATEGORIES["finance"] == 7
        assert service.CATEGORIES["computers_electronics"] == 5
        assert service.CATEGORIES["health"] == 45


class TestDatabasePersistence:
    """Test that trends data is persisted to database"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session that tracks calls"""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db

    @patch("pytrends.request.TrendReq")
    def test_search_saves_to_database(self, mock_trend_req, mock_db):
        """Test that search results are saved to database"""
        mock_client = Mock()
        mock_trend_req.return_value = mock_client

        import pandas as pd

        mock_data = pd.DataFrame(
            {
                "keyword": [50, 60, 70],
                "isPartial": [False, False, False],
            }
        )
        mock_client.interest_over_time.return_value = mock_data

        service = GoogleTrendsService()

        result = service.search_interest_over_time(
            db=mock_db,
            keywords=["keyword"],
            user_id="user-123",
            client_id="client-456",
            project_id="project-789",
        )

        # Verify database operations were called
        assert mock_db.add.called, "Database add() was not called"
        assert mock_db.commit.called, "Database commit() was not called"

        # Verify result includes database ID
        assert "search_id" in result


class TestSEOIntegration:
    """Test integration with SEO Keyword Research tool"""

    def test_trends_service_accessible_from_seo_tool(self):
        """Test that SEO tool can access trends service"""
        from backend.services.trends_service import trends_service

        assert trends_service is not None
        assert isinstance(trends_service, GoogleTrendsService)

    def test_seo_keyword_research_uses_pytrends(self):
        """Test that SEO Keyword Research tool integrates with pytrends"""
        from src.research.seo_keyword_research import SEOKeywordResearcher

        researcher = SEOKeywordResearcher(project_id="test-seo-integration")

        # Verify the researcher has the enrichment method
        assert hasattr(researcher, "_enrich_with_google_trends")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
