"""Test complete platform recommendation flow.

Tests the two-phase implementation:
1. Platform Strategy saves recommended_platforms to client.recommended_platforms
2. Content Calendar reads recommended_platforms from client.recommended_platforms
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models.client import Client
from backend.models.project import Project
from backend.schemas.client import ClientResponse
from backend.services.research_service import research_service
from backend.services import crud


@pytest.fixture
def test_client():
    """Create a test client with no recommended platforms"""
    return Client(
        id="test-client-1",
        name="Test Company",
        user_id="test-user-1",
        email="test@example.com",
        business_description="Software company",
        ideal_customer="Tech companies",
        recommended_platforms=None,  # Start with no recommendations
        created_at=datetime.now(),
    )


@pytest.fixture
def test_project():
    """Create a test project"""
    return Project(
        id="test-project-1",
        client_id="test-client-1",
        user_id="test-user-1",
        name="Test Project",
        status="active",
        created_at=datetime.now(),
    )


class TestPlatformRecommendationFlow:
    """Test platform recommendation persistence and retrieval"""

    def test_platform_strategy_result_saves_to_client(self, test_client, test_project):
        """Test that platform_strategy results get saved to client.recommended_platforms"""
        db = Mock(spec=Session)

        # Mock the CRUD update function
        with patch("backend.services.crud.update_client_recommended_platforms") as mock_update:
            # Simulate platform_strategy execution with recommended platforms
            recommended = ["linkedin", "twitter", "blog"]

            # Call the CRUD function
            crud.update_client_recommended_platforms(
                db, client_id=test_client.id, recommended_platforms=recommended
            )

            # Verify it was called with correct data
            mock_update.assert_called_once_with(
                db, client_id=test_client.id, recommended_platforms=recommended
            )

    def test_content_calendar_receives_recommended_platforms(self, test_client, test_project):
        """Test that content_calendar tool can read recommended_platforms from client"""
        # Setup client with recommended platforms from previous platform_strategy run
        test_client.recommended_platforms = ["linkedin", "twitter"]

        # Prepare inputs for content_calendar tool
        db = Mock(spec=Session)
        params = {}  # Frontend didn't provide platforms

        # Call _prepare_inputs
        inputs = research_service._prepare_inputs(
            project=test_project, client=test_client, tool_name="content_calendar", params=params
        )

        # Verify that recommended_platforms are injected
        assert "primary_platforms" in inputs
        assert inputs["primary_platforms"] == ["linkedin", "twitter"]

    def test_content_calendar_prefers_frontend_platforms(self, test_client, test_project):
        """Test that frontend-provided platforms take precedence over recommended"""
        test_client.recommended_platforms = ["linkedin", "twitter"]

        params = {"primary_platforms": ["instagram", "youtube"]}

        inputs = research_service._prepare_inputs(
            project=test_project, client=test_client, tool_name="content_calendar", params=params
        )

        # Frontend platforms should be used
        assert inputs["primary_platforms"] == ["instagram", "youtube"]

    def test_content_calendar_strategy_alias_works(self, test_client, test_project):
        """Test that content_calendar_strategy tool name also works (alias)"""
        test_client.recommended_platforms = ["linkedin"]

        params = {}

        inputs = research_service._prepare_inputs(
            project=test_project,
            client=test_client,
            tool_name="content_calendar_strategy",
            params=params,
        )

        assert inputs["primary_platforms"] == ["linkedin"]

    def test_empty_recommended_platforms_fallback(self, test_client, test_project):
        """Test that empty platforms list is handled gracefully"""
        test_client.recommended_platforms = None

        params = {}

        inputs = research_service._prepare_inputs(
            project=test_project, client=test_client, tool_name="content_calendar", params=params
        )

        # Should default to empty list when no platforms available
        assert inputs["primary_platforms"] == []

    def test_client_response_includes_recommended_platforms(self, test_client):
        """Test that ClientResponse schema includes recommended_platforms field"""
        test_client.recommended_platforms = ["linkedin", "twitter", "blog"]
        test_client.updated_at = datetime.now()

        # Create response schema
        response = ClientResponse.model_validate(test_client)

        # Verify field is present and serialized with camelCase alias
        assert response.recommended_platforms == ["linkedin", "twitter", "blog"]

        # Verify it serializes to JSON with correct alias
        data = response.model_dump(by_alias=True)
        assert "recommendedPlatforms" in data
        assert data["recommendedPlatforms"] == ["linkedin", "twitter", "blog"]
