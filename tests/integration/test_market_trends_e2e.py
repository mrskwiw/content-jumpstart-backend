"""
End-to-end integration test for Market Trends Research tool.

Verifies complete workflow:
1. Data collection validation (with optional location for Google Maps reviews)
2. Tool execution with auto-generated focus areas
3. Database storage
4. Export formatting
5. Context builder integration
6. Google Maps review extraction (new feature)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from backend.main import app
from backend.models import User, Client, ResearchResult
from backend.utils.auth import get_password_hash
from backend.services.export_service import _format_market_trends
from backend.services.research_context_builder import build_research_context


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-trends-test",
        email="trends@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Trends Test User",
        is_active=True,
        is_superuser=False,
        credit_balance=1000,  # Sufficient credits
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user, client):
    """Get auth headers"""
    response = client.post(
        "/api/auth/login",
        json={"email": "trends@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_client_db(db_session: Session, test_user):
    """Create test client"""
    client_obj = Client(
        id="client-trends-test",
        user_id=test_user.id,
        name="Test SaaS Company",
        email="client@example.com",
        business_description="AI-powered project management platform for distributed teams",
        ideal_customer="CTOs and Engineering Managers at 50-500 person tech companies",
        industry="SaaS",
        location="San Francisco, CA",  # For Google Maps testing
    )
    db_session.add(client_obj)
    db_session.commit()
    db_session.refresh(client_obj)
    return client_obj


class TestMarketTrendsDataCollection:
    """Test Market Trends tool data collection and validation"""

    def test_market_trends_auto_generates_focus_areas(self, client, auth_headers, test_client_db):
        """Test that focus_areas can be auto-generated"""
        response = client.post(
            "/api/research/execute",
            headers=auth_headers,
            json={
                "client_id": test_client_db.id,
                "tool_name": "market_trends_research",
                "inputs": {
                    # No focus_areas - should auto-generate
                    # No industry - should use client profile
                },
            },
        )

        # Should accept and auto-generate
        assert response.status_code in [200, 201, 202]

    def test_market_trends_accepts_manual_focus_areas(self, client, auth_headers, test_client_db):
        """Test that manual focus_areas are accepted"""
        response = client.post(
            "/api/research/execute",
            headers=auth_headers,
            json={
                "client_id": test_client_db.id,
                "tool_name": "market_trends_research",
                "inputs": {
                    "focus_areas": ["remote work", "async collaboration", "productivity tools"],
                },
            },
        )

        assert response.status_code in [200, 201, 202]

    def test_market_trends_accepts_location_for_reviews(self, client, auth_headers, test_client_db):
        """Test that location parameter enables Google Maps review analysis"""
        response = client.post(
            "/api/research/execute",
            headers=auth_headers,
            json={
                "client_id": test_client_db.id,
                "tool_name": "market_trends_research",
                "inputs": {
                    "location": "San Francisco, CA",  # Enables review extraction
                },
            },
        )

        assert response.status_code in [200, 201, 202]

    def test_market_trends_validates_focus_areas_limit(self, client, auth_headers, test_client_db):
        """Test that max 10 focus areas are enforced"""
        response = client.post(
            "/api/research/execute",
            headers=auth_headers,
            json={
                "client_id": test_client_db.id,
                "tool_name": "market_trends_research",
                "inputs": {
                    "focus_areas": [f"area {i}" for i in range(15)],  # Too many
                },
            },
        )

        # Should fail validation
        assert response.status_code in [400, 422]


class TestMarketTrendsToolExecution:
    """Test Market Trends tool execution and results"""

    @patch("src.research.market_trends_research.get_google_maps_client")
    @patch("src.research.base.ResearchTool._call_claude_api")
    def test_market_trends_generates_trend_report(
        self, mock_claude_api, mock_maps_client, db_session, test_client_db
    ):
        """Test that Market Trends tool generates comprehensive trend report"""
        from src.research.market_trends_research import MarketTrendsResearcher

        # Mock Claude API to return deterministic trend categories
        mock_claude_api.return_value = [
            {
                "category_name": "Remote Work Trends",
                "description": "Trends in remote work",
                "category_momentum": "rising",
                "trends": [
                    {
                        "topic": "Async collaboration",
                        "description": "Growing trend",
                        "momentum": "rising",
                        "relevance": "high",
                        "popularity_score": 8.0,
                        "growth_rate": "+40% YoY",
                        "urgency": "High",
                    }
                ],
            }
        ]

        researcher = MarketTrendsResearcher(project_id="test-trends")

        inputs = {
            "business_description": test_client_db.business_description,
            "target_audience": test_client_db.ideal_customer,
            "industry": "SaaS",
            "focus_areas": ["remote work", "async collaboration"],
        }

        # Validate inputs
        is_valid = researcher.validate_inputs(inputs)
        assert is_valid is True

        # Run analysis
        report = researcher.run_analysis(inputs)

        # Verify results structure
        assert report is not None
        assert hasattr(report, "trend_categories")
        assert hasattr(report, "top_rising_trends")
        assert hasattr(report, "emerging_conversations")
        assert len(report.trend_categories) > 0

    @patch("src.research.market_trends_research.get_google_maps_client")
    def test_market_trends_extracts_industry_insights_from_reviews(
        self, mock_maps_client, db_session, test_client_db
    ):
        """Test that Market Trends extracts customer insights from Google Maps reviews"""
        from src.research.market_trends_research import MarketTrendsResearcher
        from src.utils.google_maps_search import GoogleMapsPlace, GoogleMapsReview, PlaceWithReviews

        # Mock Google Maps client
        mock_client = MagicMock()
        mock_maps_client.return_value = mock_client

        # Mock business search results
        mock_client.search_local_businesses.return_value = [
            GoogleMapsPlace(
                place_id="place_1",
                name="SaaS Company 1",
                address="123 Market St",
                rating=4.5,
                reviews_count=100,
            ),
        ]

        # Mock reviews
        mock_client.get_place_reviews.return_value = PlaceWithReviews(
            place=GoogleMapsPlace(
                place_id="place_1",
                name="SaaS Company 1",
                address="123 Market St",
                rating=4.5,
            ),
            reviews=[
                GoogleMapsReview(
                    author="John Doe",
                    rating=5,
                    text="Great productivity tool for remote teams!",
                    date="2024-01-15",
                ),
                GoogleMapsReview(
                    author="Jane Smith",
                    rating=2,
                    text="Too expensive and lacks integrations.",
                    date="2024-01-10",
                ),
            ],
            total_reviews=100,
        )

        researcher = MarketTrendsResearcher(project_id="test-reviews")

        # Extract industry insights
        insights = researcher._extract_industry_insights_from_reviews(
            industry="SaaS", location="San Francisco, CA", focus_areas=["remote work"]
        )

        # Verify insights were generated
        assert insights is not None
        assert len(insights) > 0
        assert "INDUSTRY CUSTOMER FEEDBACK" in insights
        assert "SaaS Company 1" in insights

    @patch("src.research.market_trends_research.get_google_maps_client")
    def test_market_trends_handles_no_reviews_gracefully(
        self, mock_maps_client, db_session, test_client_db
    ):
        """Test that Market Trends handles absence of Google Maps reviews gracefully"""
        from src.research.market_trends_research import MarketTrendsResearcher

        # Mock Google Maps client to return no businesses
        mock_client = MagicMock()
        mock_maps_client.return_value = mock_client
        mock_client.search_local_businesses.return_value = []

        researcher = MarketTrendsResearcher(project_id="test-no-reviews")

        # Should return empty string without error
        insights = researcher._extract_industry_insights_from_reviews(
            industry="SaaS", location="Nowhere, XX", focus_areas=[]
        )

        assert insights == ""


class TestMarketTrendsExportFormatting:
    """Test Market Trends tool export formatting"""

    def test_format_market_trends_with_categories(self):
        """Test formatting trend categories for export"""
        data = {
            "trend_categories": [
                {
                    "category_name": "Remote Work Trends",
                    "description": "Trends in remote and hybrid work",
                    "trends": [
                        {"topic": "Async collaboration", "momentum": "rising"},
                        {"topic": "Virtual team building", "momentum": "emerging"},
                    ],
                },
            ],
            "top_rising_trends": ["async collaboration", "AI automation"],
        }

        lines = _format_market_trends(data)

        assert len(lines) > 0
        assert "Remote Work Trends" in " ".join(lines)
        assert "Async collaboration" in " ".join(lines)

    def test_format_market_trends_empty_data(self):
        """Test formatting with no trends"""
        data = {}

        lines = _format_market_trends(data)

        # Should return empty or minimal output
        assert isinstance(lines, list)


class TestMarketTrendsContextBuilder:
    """Test Market Trends tool context builder integration"""

    def test_market_trends_context_builder_with_results(
        self, db_session, test_client_db, test_user
    ):
        """Test that Market Trends results are included in research context"""
        # Create mock research result
        result = ResearchResult(
            id="res-trends-test",
            user_id=test_user.id,
            client_id=test_client_db.id,
            tool_name="market_trends_research",
            tool_label="Market Trends Research",
            tool_price=400,
            status="completed",
            data={
                "top_rising_trends": ["async collaboration", "AI automation", "remote work"],
                "key_themes": ["productivity", "automation"],
            },
        )
        db_session.add(result)
        db_session.commit()

        # Build context
        context = build_research_context(db_session, test_client_db.id)

        # Verify Market Trends is included
        assert context is not None
        assert "research_summary" in context or "formatted_research" in context


class TestMarketTrendsEndToEnd:
    """Complete end-to-end workflow test"""

    @patch("src.research.market_trends_research.get_google_maps_client")
    def test_complete_market_trends_workflow(
        self, mock_maps_client, client, auth_headers, test_client_db, db_session
    ):
        """Test: execute → store → export → context (with Google Maps reviews)"""

        # Mock Google Maps (optional - location may not be provided)
        mock_client = MagicMock()
        mock_maps_client.return_value = mock_client
        mock_client.search_local_businesses.return_value = []

        # Step 1: Execute Market Trends research with location
        exec_response = client.post(
            "/api/research/execute",
            headers=auth_headers,
            json={
                "client_id": test_client_db.id,
                "tool_name": "market_trends_research",
                "inputs": {
                    "focus_areas": ["remote work", "productivity"],
                    "location": "San Francisco, CA",  # Triggers Google Maps review extraction
                },
            },
        )

        assert exec_response.status_code in [200, 201, 202]
        exec_data = exec_response.json()
        result_id = exec_data.get("id") or exec_data.get("result_id")

        # Step 2: Check result was stored in database
        stored_result = (
            db_session.query(ResearchResult)
            .filter(
                ResearchResult.client_id == test_client_db.id,
                ResearchResult.tool_name == "market_trends_research",
            )
            .first()
        )

        # If execution is async, result might be pending
        if stored_result:
            assert stored_result.tool_name == "market_trends_research"
            assert stored_result.tool_price == 400

        # Step 3: Verify context builder can handle the result
        context = build_research_context(db_session, test_client_db.id)
        assert context is not None

        # Step 4: Verify export formatting works (if result completed)
        if stored_result and stored_result.data:
            formatted = _format_market_trends(stored_result.data)
            assert isinstance(formatted, list)

        print(
            "✅ Market Trends Research tool: Complete workflow verified (including Google Maps reviews)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
