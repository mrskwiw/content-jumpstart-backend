"""Integration tests for Google Trends router endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client(db_session):
    """Create test client with database dependency override."""
    return TestClient(app)


@pytest.fixture
def test_user_a(db_session: Session):
    """Create a test user A."""
    user = User(
        id="user-trends-a",
        email="trends_a@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Trends User A",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers_user_a(test_user_a, client, db_session):
    """Get auth headers for user A."""
    # Ensure user is committed
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "trends_a@example.com",
            "password": "testpass123",  # pragma: allowlist secret
        },
    )

    # Debug: print response if login fails
    if response.status_code != 200:
        print(f"[DEBUG] Login failed: status={response.status_code}, body={response.json()}")

    data = response.json()
    if "access_token" not in data:
        raise ValueError(f"Login failed: {data}")

    return {"Authorization": f"Bearer {data['access_token']}"}


# ============================================================================
# Test POST /api/trends/search/interest - Interest Over Time
# ============================================================================


class TestSearchInterestOverTime:
    """Test searching Google Trends for interest over time."""

    @patch("backend.services.trends_service.trends_service.search_interest_over_time")
    def test_search_interest_authenticated(self, mock_search, client, auth_headers_user_a):
        """Test searching interest over time with valid authentication."""
        mock_search.return_value = {
            "success": True,
            "search_id": "search-123",
            "keywords": ["content marketing", "seo"],
            "timeframe": "past_12_months",
            "geo": "US",
            "data_points": 52,
            "sample_data": [
                {"date": "2024-01-01", "content marketing": 75, "seo": 80},
                {"date": "2024-01-08", "content marketing": 78, "seo": 82},
            ],
        }

        response = client.post(
            "/api/trends/search/interest",
            headers=auth_headers_user_a,
            json={
                "keywords": ["content marketing", "seo"],
                "timeframe": "past_12_months",
                "geo": "US",
                "category": "all",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["keywords"] == ["content marketing", "seo"]
        assert data["timeframe"] == "past_12_months"
        assert data["geo"] == "US"
        assert data["data_points"] == 52
        assert len(data["sample_data"]) == 2

    def test_search_interest_unauthenticated(self, client):
        """Test searching without authentication returns 401."""
        response = client.post(
            "/api/trends/search/interest",
            json={
                "keywords": ["content marketing"],
                "timeframe": "past_12_months",
            },
        )

        assert response.status_code == 401

    def test_search_interest_empty_keywords(self, client, auth_headers_user_a):
        """Test searching with empty keywords list fails validation."""
        response = client.post(
            "/api/trends/search/interest",
            headers=auth_headers_user_a,
            json={
                "keywords": [],
                "timeframe": "past_12_months",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_search_interest_too_many_keywords(self, client, auth_headers_user_a):
        """Test searching with >5 keywords fails validation."""
        response = client.post(
            "/api/trends/search/interest",
            headers=auth_headers_user_a,
            json={
                "keywords": [
                    "keyword1",
                    "keyword2",
                    "keyword3",
                    "keyword4",
                    "keyword5",
                    "keyword6",
                ],
                "timeframe": "past_12_months",
            },
        )

        assert response.status_code == 422  # Validation error

    @patch("backend.services.trends_service.trends_service.search_interest_over_time")
    def test_search_interest_with_client_id(self, mock_search, client, auth_headers_user_a):
        """Test searching with optional client_id parameter."""
        mock_search.return_value = {
            "success": True,
            "search_id": "search-456",
            "keywords": ["b2b saas"],
            "timeframe": "past_3_months",
            "geo": "",
            "data_points": 13,
        }

        response = client.post(
            "/api/trends/search/interest",
            headers=auth_headers_user_a,
            json={
                "keywords": ["b2b saas"],
                "timeframe": "past_3_months",
                "client_id": "client-123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["keywords"] == ["b2b saas"]

        # Verify client_id was passed to service
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["client_id"] == "client-123"

    @patch("backend.services.trends_service.trends_service.search_interest_over_time")
    def test_search_interest_pytrends_unavailable(self, mock_search, client, auth_headers_user_a):
        """Test error when pytrends library not installed."""
        mock_search.side_effect = ImportError("No module named 'pytrends'")

        response = client.post(
            "/api/trends/search/interest",
            headers=auth_headers_user_a,
            json={
                "keywords": ["content marketing"],
                "timeframe": "past_12_months",
            },
        )

        assert response.status_code == 503
        assert "pytrends" in response.json()["detail"]

    @patch("backend.services.trends_service.trends_service.search_interest_over_time")
    def test_search_interest_service_error(self, mock_search, client, auth_headers_user_a):
        """Test handling of service errors."""
        mock_search.side_effect = Exception("Google Trends API error")

        response = client.post(
            "/api/trends/search/interest",
            headers=auth_headers_user_a,
            json={
                "keywords": ["content marketing"],
                "timeframe": "past_12_months",
            },
        )

        assert response.status_code == 500
        assert "Trends search failed" in response.json()["detail"]


# ============================================================================
# Test POST /api/trends/search/related - Related Queries
# ============================================================================


class TestSearchRelatedQueries:
    """Test searching Google Trends for related queries."""

    @patch("backend.services.trends_service.trends_service.search_related_queries")
    def test_search_related_authenticated(self, mock_search, client, auth_headers_user_a):
        """Test searching related queries with valid authentication."""
        mock_search.return_value = {
            "success": True,
            "search_id": "related-123",
            "keywords": ["content marketing"],
            "total_queries": 50,
            "top_queries": [
                {"query": "content marketing strategy", "value": 100},
                {"query": "content marketing examples", "value": 85},
            ],
            "rising_queries": [
                {"query": "ai content marketing", "value": "Breakout"},
                {"query": "content marketing automation", "value": "+250%"},
            ],
        }

        response = client.post(
            "/api/trends/search/related",
            headers=auth_headers_user_a,
            json={
                "keywords": ["content marketing"],
                "timeframe": "past_12_months",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["keywords"] == ["content marketing"]
        assert data["total_queries"] == 50
        assert len(data["top_queries"]) == 2
        assert len(data["rising_queries"]) == 2

    def test_search_related_unauthenticated(self, client):
        """Test searching related queries without authentication."""
        response = client.post(
            "/api/trends/search/related",
            json={
                "keywords": ["content marketing"],
            },
        )

        assert response.status_code == 401

    @patch("backend.services.trends_service.trends_service.search_related_queries")
    def test_search_related_pytrends_unavailable(self, mock_search, client, auth_headers_user_a):
        """Test error when pytrends library not installed."""
        mock_search.side_effect = ImportError("No module named 'pytrends'")

        response = client.post(
            "/api/trends/search/related",
            headers=auth_headers_user_a,
            json={
                "keywords": ["content marketing"],
            },
        )

        assert response.status_code == 503

    @patch("backend.services.trends_service.trends_service.search_related_queries")
    def test_search_related_service_error(self, mock_search, client, auth_headers_user_a):
        """Test handling of service errors."""
        mock_search.side_effect = Exception("API error")

        response = client.post(
            "/api/trends/search/related",
            headers=auth_headers_user_a,
            json={
                "keywords": ["content marketing"],
            },
        )

        assert response.status_code == 500


# ============================================================================
# Test POST /api/trends/insights/compute - Compute Keyword Insights
# ============================================================================


class TestComputeKeywordInsight:
    """Test computing insights for keywords."""

    @patch("backend.services.trends_service.trends_service.compute_keyword_insights")
    def test_compute_insight_success(self, mock_compute, client, auth_headers_user_a):
        """Test successful insight computation."""
        mock_compute.return_value = {
            "success": True,
            "keyword": "content marketing",
            "insight_id": "insight-123",
            "metrics": {
                "average_interest": 75,
                "peak_interest": 95,
                "current_interest": 78,
            },
            "trend": {
                "direction": "rising",
                "change_percent": 12.5,
            },
            "seasonality": {
                "pattern": "monthly",
                "peak_months": ["September", "October"],
            },
            "recommendation": "Strong keyword - rising interest with clear seasonality",
            "priority_score": 8.5,
        }

        response = client.post(
            "/api/trends/insights/compute",
            headers=auth_headers_user_a,
            json={
                "keyword": "content marketing",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["keyword"] == "content marketing"
        assert data["priority_score"] == 8.5
        assert data["trend"]["direction"] == "rising"

    def test_compute_insight_unauthenticated(self, client):
        """Test computing insights without authentication."""
        response = client.post(
            "/api/trends/insights/compute",
            json={
                "keyword": "content marketing",
            },
        )

        assert response.status_code == 401

    @patch("backend.services.trends_service.trends_service.compute_keyword_insights")
    def test_compute_insight_with_client_id(self, mock_compute, client, auth_headers_user_a):
        """Test computing insights with client_id filter."""
        mock_compute.return_value = {
            "success": True,
            "keyword": "b2b saas",
            "priority_score": 7.5,
        }

        response = client.post(
            "/api/trends/insights/compute",
            headers=auth_headers_user_a,
            json={
                "keyword": "b2b saas",
                "client_id": "client-456",
            },
        )

        assert response.status_code == 200
        mock_compute.assert_called_once()
        call_kwargs = mock_compute.call_args.kwargs
        assert call_kwargs["client_id"] == "client-456"

    @patch("backend.services.trends_service.trends_service.compute_keyword_insights")
    def test_compute_insight_service_error(self, mock_compute, client, auth_headers_user_a):
        """Test handling of service errors."""
        mock_compute.side_effect = Exception("Computation failed")

        response = client.post(
            "/api/trends/insights/compute",
            headers=auth_headers_user_a,
            json={
                "keyword": "content marketing",
            },
        )

        assert response.status_code == 500
        assert "Insight computation failed" in response.json()["detail"]


# ============================================================================
# Test GET /api/trends/history - Search History
# ============================================================================


class TestGetSearchHistory:
    """Test retrieving trends search history."""

    @patch("backend.services.trends_service.trends_service.get_search_history")
    def test_get_history_authenticated(self, mock_history, client, auth_headers_user_a):
        """Test getting search history with authentication."""
        mock_history.return_value = {
            "success": True,
            "count": 3,
            "searches": [
                {
                    "search_id": "search-1",
                    "keywords": ["content marketing", "seo"],
                    "timeframe": "past_12_months",
                    "created_at": "2024-01-15T10:00:00",
                },
                {
                    "search_id": "search-2",
                    "keywords": ["b2b saas"],
                    "timeframe": "past_3_months",
                    "created_at": "2024-01-14T15:30:00",
                },
                {
                    "search_id": "search-3",
                    "keywords": ["social media marketing"],
                    "timeframe": "past_6_months",
                    "created_at": "2024-01-10T09:15:00",
                },
            ],
        }

        response = client.get(
            "/api/trends/history",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 3
        assert len(data["searches"]) == 3

    def test_get_history_unauthenticated(self, client):
        """Test getting history without authentication."""
        response = client.get("/api/trends/history")

        assert response.status_code == 401

    @patch("backend.services.trends_service.trends_service.get_search_history")
    def test_get_history_with_client_filter(self, mock_history, client, auth_headers_user_a):
        """Test getting history filtered by client_id."""
        mock_history.return_value = {
            "success": True,
            "count": 1,
            "searches": [
                {
                    "search_id": "search-1",
                    "keywords": ["b2b saas"],
                    "client_id": "client-123",
                }
            ],
        }

        response = client.get(
            "/api/trends/history?client_id=client-123",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

        # Verify filter was passed to service
        mock_history.assert_called_once()
        call_kwargs = mock_history.call_args.kwargs
        assert call_kwargs["client_id"] == "client-123"

    @patch("backend.services.trends_service.trends_service.get_search_history")
    def test_get_history_with_limit(self, mock_history, client, auth_headers_user_a):
        """Test getting history with custom limit."""
        mock_history.return_value = {
            "success": True,
            "count": 10,
            "searches": [{"search_id": f"search-{i}"} for i in range(10)],
        }

        response = client.get(
            "/api/trends/history?limit=10",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 10

        # Verify limit was passed to service
        mock_history.assert_called_once()
        call_kwargs = mock_history.call_args.kwargs
        assert call_kwargs["limit"] == 10

    @patch("backend.services.trends_service.trends_service.get_search_history")
    def test_get_history_service_error(self, mock_history, client, auth_headers_user_a):
        """Test handling of service errors."""
        mock_history.side_effect = Exception("Database error")

        response = client.get(
            "/api/trends/history",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 500
        assert "Failed to get search history" in response.json()["detail"]


# ============================================================================
# Test GET /api/trends/insights - Get Keyword Insights
# ============================================================================


class TestGetKeywordInsights:
    """Test retrieving computed keyword insights."""

    @patch("backend.services.trends_service.trends_service.get_keyword_insights")
    def test_get_insights_authenticated(self, mock_insights, client, auth_headers_user_a):
        """Test getting insights with authentication."""
        mock_insights.return_value = {
            "success": True,
            "count": 2,
            "insights": [
                {
                    "insight_id": "insight-1",
                    "keyword": "content marketing",
                    "priority_score": 8.5,
                    "recommendation": "Strong keyword",
                },
                {
                    "insight_id": "insight-2",
                    "keyword": "seo",
                    "priority_score": 7.2,
                    "recommendation": "Good keyword",
                },
            ],
        }

        response = client.get(
            "/api/trends/insights",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["insights"]) == 2

    def test_get_insights_unauthenticated(self, client):
        """Test getting insights without authentication."""
        response = client.get("/api/trends/insights")

        assert response.status_code == 401

    @patch("backend.services.trends_service.trends_service.get_keyword_insights")
    def test_get_insights_with_min_priority(self, mock_insights, client, auth_headers_user_a):
        """Test getting insights with minimum priority filter."""
        mock_insights.return_value = {
            "success": True,
            "count": 1,
            "insights": [
                {
                    "insight_id": "insight-1",
                    "keyword": "content marketing",
                    "priority_score": 8.5,
                }
            ],
        }

        response = client.get(
            "/api/trends/insights?min_priority=8.0",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

        # Verify filter was passed to service
        mock_insights.assert_called_once()
        call_kwargs = mock_insights.call_args.kwargs
        assert call_kwargs["min_priority"] == 8.0

    @patch("backend.services.trends_service.trends_service.get_keyword_insights")
    def test_get_insights_with_filters(self, mock_insights, client, auth_headers_user_a):
        """Test getting insights with client and project filters."""
        mock_insights.return_value = {
            "success": True,
            "count": 1,
            "insights": [{"insight_id": "insight-1"}],
        }

        response = client.get(
            "/api/trends/insights?client_id=client-123&project_id=project-456",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200

        # Verify filters were passed to service
        mock_insights.assert_called_once()
        call_kwargs = mock_insights.call_args.kwargs
        assert call_kwargs["client_id"] == "client-123"
        assert call_kwargs["project_id"] == "project-456"

    @patch("backend.services.trends_service.trends_service.get_keyword_insights")
    def test_get_insights_service_error(self, mock_insights, client, auth_headers_user_a):
        """Test handling of service errors."""
        mock_insights.side_effect = Exception("Database error")

        response = client.get(
            "/api/trends/insights",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 500
        assert "Failed to get insights" in response.json()["detail"]


# ============================================================================
# Test GET /api/trends/timeframes - Get Available Timeframes
# ============================================================================


class TestGetAvailableTimeframes:
    """Test getting available timeframe options."""

    def test_get_timeframes_no_auth_required(self, client):
        """Test getting timeframes without authentication."""
        response = client.get("/api/trends/timeframes")

        assert response.status_code == 200
        data = response.json()
        assert "timeframes" in data
        assert "default" in data
        assert isinstance(data["timeframes"], dict)

    def test_get_timeframes_returns_options(self, client):
        """Test timeframes endpoint returns expected structure."""
        response = client.get("/api/trends/timeframes")

        assert response.status_code == 200
        data = response.json()
        assert data["default"] == "past_12_months"
        assert "timeframes" in data


# ============================================================================
# Test GET /api/trends/categories - Get Available Categories
# ============================================================================


class TestGetAvailableCategories:
    """Test getting available category options."""

    def test_get_categories_no_auth_required(self, client):
        """Test getting categories without authentication."""
        response = client.get("/api/trends/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "default" in data
        assert isinstance(data["categories"], dict)

    def test_get_categories_returns_options(self, client):
        """Test categories endpoint returns expected structure."""
        response = client.get("/api/trends/categories")

        assert response.status_code == 200
        data = response.json()
        assert data["default"] == "all"
        assert "categories" in data
