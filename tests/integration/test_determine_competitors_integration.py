"""
Integration tests for Determine Competitors research tool.

Tests end-to-end functionality including:
- Full tool execution with mocked dependencies
- Auto-save to client.competitors field
- Validation requirements
- Optional parameters
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch

from backend.main import app
from backend.models import User, Client, Project
from backend.utils.auth import get_password_hash


@pytest.fixture
def client_app(db_session):
    """Create test client with test database"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-competitor-test-123",
        email="competitor_test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Competitor Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user, client_app, db_session):
    """Get auth headers for test user"""
    db_session.commit()

    response = client_app.post(
        "/api/auth/login",
        json={
            "email": "competitor_test@example.com",
            "password": "testpass123",  # pragma: allowlist secret
        },
    )

    assert response.status_code == 200, f"Login failed: {response.json()}"
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture
def test_client(db_session: Session, test_user):
    """Create test client"""
    client = Client(
        id="client-competitor-123",
        user_id=test_user.id,
        name="Test Competitor Client",
        business_description="We help B2B SaaS companies reduce customer churn through AI-powered analytics and personalized engagement strategies.",
        industry="B2B SaaS",
        competitors=None,  # Start with no competitors
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def test_project(db_session: Session, test_user, test_client):
    """Create test project"""
    project = Project(
        id="project-competitor-123",
        user_id=test_user.id,
        client_id=test_client.id,
        name="Test Competitor Project",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


class TestDetermineCompetitorsIntegration:
    """Test Determine Competitors tool end-to-end integration"""

    @patch(
        "backend.utils.web_search_validator.is_web_search_configured", return_value=(True, "mock")
    )
    @patch("src.research.base.get_default_client")
    @patch("src.research.determine_competitors.get_search_client")
    @patch("src.research.determine_competitors.get_default_client")
    def test_full_execution_with_web_search(
        self,
        mock_dc_claude_client,
        mock_search_client,
        mock_base_claude_client,
        mock_web_search_configured,
        client_app,
        auth_headers,
        test_project,
        test_client,
        db_session,
    ):
        """Test full execution of determine_competitors tool with web search"""
        # Mock web search results
        mock_search = Mock()
        mock_search.search.return_value = Mock(
            results=[
                Mock(
                    title="ChurnZero - Customer Success Platform",
                    url="https://churnzero.com",
                    snippet="Real-time customer success platform for B2B SaaS",
                    published_date=None,
                ),
                Mock(
                    title="Gainsight - Product Analytics",
                    url="https://gainsight.com",
                    snippet="Enterprise customer success with analytics",
                    published_date=None,
                ),
            ]
        )
        mock_search_client.return_value = mock_search

        # Mock Claude API - create_message returns string (base.py extracts text automatically)
        competitor_json = (
            '{"primary": ['
            '{"name": "ChurnZero", "market_position": "Customer success platform for SaaS companies",'
            ' "threat_level": "high", "strength_areas": ["Real-time alerts", "Health scoring", "Automation"],'
            ' "differentiation_opportunity": "Focus on AI-powered predictions",'
            ' "reasoning": "Direct competitor in B2B SaaS retention space"},'
            '{"name": "Gainsight", "market_position": "Enterprise customer success platform",'
            ' "threat_level": "high", "strength_areas": ["Product analytics", "Journey orchestration", "Surveys"],'
            ' "differentiation_opportunity": "Focus on SMB segment",'
            ' "reasoning": "Market leader in customer success category"}'
            '], "emerging": []}'
        )
        mock_claude = Mock()
        mock_claude.create_message.side_effect = [
            competitor_json,  # _discover_competitors_with_ai
            "Competitive landscape analysis text",  # _analyze_competitive_landscape
            '["AI predictions gap", "SMB underserved"]',  # _identify_market_gaps
            "Position as AI-first customer success platform",  # _generate_positioning_recommendation
        ]
        mock_base_claude_client.return_value = mock_claude

        # Execute tool
        response = client_app.post(
            "/api/research/run",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "determine_competitors",
                "params": {},
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["tool"] == "determine_competitors"
        assert "outputs" in data
        assert "metadata" in data
        assert "data" in data["metadata"]

        # Verify competitors were discovered
        competitors_data = data["metadata"]["data"]
        assert "primary_competitors" in competitors_data
        assert len(competitors_data["primary_competitors"]) >= 2

        # Verify competitor structure
        competitor = competitors_data["primary_competitors"][0]
        assert "name" in competitor
        assert "market_position" in competitor
        assert "threat_level" in competitor
        assert "strength_areas" in competitor
        assert "differentiation_opportunity" in competitor
        assert "reasoning" in competitor

        # Verify outputs were generated
        assert "json" in data["outputs"]
        assert "markdown" in data["outputs"]
        assert "text" in data["outputs"]

    @patch(
        "backend.utils.web_search_validator.is_web_search_configured", return_value=(True, "mock")
    )
    @patch("src.research.base.get_default_client")
    @patch("src.research.determine_competitors.get_search_client")
    @patch("src.research.determine_competitors.get_default_client")
    def test_auto_saves_competitors_to_client_profile(
        self,
        mock_dc_claude_client,
        mock_search_client,
        mock_base_claude_client,
        mock_web_search_configured,
        client_app,
        auth_headers,
        test_project,
        test_client,
        db_session,
    ):
        """Test that tool auto-saves discovered competitors to client.competitors field"""
        # Setup mocks
        mock_search = Mock()
        mock_search.search.return_value = Mock(results=[])
        mock_search_client.return_value = mock_search

        competitor_json = (
            '{"primary": ['
            '{"name": "Competitor Alpha", "market_position": "Market leader", "threat_level": "high",'
            ' "strength_areas": ["Feature A", "Feature B"], "differentiation_opportunity": "Focus on AI",'
            ' "reasoning": "Direct competitor"},'
            '{"name": "Competitor Beta", "market_position": "Challenger brand", "threat_level": "medium",'
            ' "strength_areas": ["Feature C"], "differentiation_opportunity": "Focus on pricing",'
            ' "reasoning": "Adjacent market player"},'
            '{"name": "Competitor Gamma", "market_position": "Niche specialist", "threat_level": "low",'
            ' "strength_areas": ["Feature D"], "differentiation_opportunity": "Focus on enterprise",'
            ' "reasoning": "Emerging threat in specific segment"}'
            '], "emerging": []}'
        )
        mock_claude = Mock()
        mock_claude.create_message.side_effect = [
            competitor_json,
            "Competitive landscape analysis",
            '["Gap A", "Gap B"]',
            "Positioning recommendation",
        ]
        mock_base_claude_client.return_value = mock_claude

        # Verify no competitors before execution
        assert test_client.competitors is None

        # Execute tool
        response = client_app.post(
            "/api/research/run",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "determine_competitors",
                "params": {},
            },
        )

        assert response.status_code == 200

        # Refresh client from database
        db_session.refresh(test_client)

        # Verify competitors were auto-saved to client profile
        assert test_client.competitors is not None
        assert len(test_client.competitors) == 3
        assert "Competitor Alpha" in test_client.competitors
        assert "Competitor Beta" in test_client.competitors
        assert "Competitor Gamma" in test_client.competitors

    @patch(
        "backend.utils.web_search_validator.is_web_search_configured", return_value=(True, "mock")
    )
    def test_validation_requires_business_description(
        self,
        mock_web_search_configured,
        client_app,
        auth_headers,
        test_project,
        test_client,
        db_session,
    ):
        """Test that tool requires business_description in client profile"""
        # Clear business description
        test_client.business_description = None
        db_session.commit()

        response = client_app.post(
            "/api/research/run",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "determine_competitors",
                "params": {},
            },
        )

        # Should fail validation
        assert response.status_code == 400
        data = response.json()
        assert "business description" in data["detail"].lower()

    @patch(
        "backend.utils.web_search_validator.is_web_search_configured", return_value=(True, "mock")
    )
    @patch("src.research.base.get_default_client")
    @patch("src.research.determine_competitors.get_search_client")
    @patch("src.research.determine_competitors.get_default_client")
    def test_optional_location_parameter(
        self,
        mock_dc_claude_client,
        mock_search_client,
        mock_base_claude_client,
        mock_web_search_configured,
        client_app,
        auth_headers,
        test_project,
        test_client,
        db_session,
    ):
        """Test that location parameter is optional and can be provided"""
        # Setup mocks
        mock_search = Mock()
        mock_search.search.return_value = Mock(results=[])
        mock_search_client.return_value = mock_search

        competitor_json = (
            '{"primary": [{"name": "Test Corp", "market_position": "Leader", "threat_level": "high",'
            ' "strength_areas": ["Feature A"], "differentiation_opportunity": "Focus B",'
            ' "reasoning": "Competitor"}], "emerging": []}'
        )
        mock_claude = Mock()
        mock_claude.create_message.return_value = competitor_json
        mock_base_claude_client.return_value = mock_claude

        # Execute with location parameter
        response = client_app.post(
            "/api/research/run",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "determine_competitors",
                "params": {"location": "United States"},
            },
        )

        assert response.status_code == 200

        # Execute without location parameter
        response2 = client_app.post(
            "/api/research/run",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "determine_competitors",
                "params": {},
            },
        )

        assert response2.status_code == 200

    @patch(
        "backend.utils.web_search_validator.is_web_search_configured", return_value=(True, "mock")
    )
    @patch("src.research.base.get_default_client")
    @patch("src.research.determine_competitors.get_search_client")
    @patch("src.research.determine_competitors.get_default_client")
    def test_optional_industry_parameter(
        self,
        mock_dc_claude_client,
        mock_search_client,
        mock_base_claude_client,
        mock_web_search_configured,
        client_app,
        auth_headers,
        test_project,
        test_client,
        db_session,
    ):
        """Test that industry parameter is optional and auto-populated from client"""
        # Setup mocks
        mock_search = Mock()
        mock_search.search.return_value = Mock(results=[])
        mock_search_client.return_value = mock_search

        competitor_json = (
            '{"primary": [{"name": "Test", "market_position": "Leader", "threat_level": "high",'
            ' "strength_areas": ["A"], "differentiation_opportunity": "B", "reasoning": "C"}],'
            ' "emerging": []}'
        )
        mock_claude = Mock()
        mock_claude.create_message.return_value = competitor_json
        mock_base_claude_client.return_value = mock_claude

        # Client already has industry set
        assert test_client.industry == "B2B SaaS"

        # Execute without industry parameter (should use client's industry)
        response = client_app.post(
            "/api/research/run",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "determine_competitors",
                "params": {},
            },
        )

        assert response.status_code == 200

        # Execute with custom industry parameter
        response2 = client_app.post(
            "/api/research/run",
            headers=auth_headers,
            json={
                "project_id": test_project.id,
                "client_id": test_client.id,
                "tool": "determine_competitors",
                "params": {"industry": "FinTech"},
            },
        )

        assert response2.status_code == 200
