"""
Integration tests for Bug #48: Research results API endpoint

Tests that /api/research/results/project/{project_id} returns
properly formatted camelCase responses
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from sqlalchemy.orm import Session
from backend.main import app
from backend.models import ResearchResult, User, Client, Project
from backend.utils.auth import get_password_hash, create_access_token


@pytest.fixture
def db(db_session):
    """Alias for db_session."""
    return db_session


class _UserWithToken:
    """Wrapper for User with access_token."""

    def __init__(self, user, token):
        self._user = user
        self.access_token = token

    def __getattr__(self, name):
        return getattr(self._user, name)


@pytest.fixture
def sample_user(db_session: Session):
    """Create a test user with access token."""
    user = User(
        id="user-bug48-test",
        email="bug48@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Bug48 Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(data={"sub": user.id})
    return _UserWithToken(user, token)


@pytest.fixture
def sample_client(db_session: Session, sample_user):
    """Create a test client."""
    client_obj = Client(
        id="client-bug48-test",
        user_id=sample_user.id,
        name="Bug48 Test Client",
        email="client@bug48test.com",
        business_description="Test business for bug 48",
        ideal_customer="Test customers",
    )
    db_session.add(client_obj)
    db_session.commit()
    db_session.refresh(client_obj)
    return client_obj


@pytest.fixture
def sample_project(db_session: Session, sample_user, sample_client):
    """Create a test project."""
    project = Project(
        id="proj-bug48-test",
        user_id=sample_user.id,
        client_id=sample_client.id,
        name="Bug48 Test Project",
        templates=["1"],
        template_quantities={"1": 10},
        num_posts=10,
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


class TestResearchResultsEndpointIntegration:
    """Integration tests for research results endpoint (Bug #48)"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_get_project_research_results_returns_camel_case(
        self, client, db, sample_user, sample_client, sample_project
    ):
        """Test that API endpoint returns camelCase field names"""
        # Create a research result with snake_case fields in database
        research_result = ResearchResult(
            id="result-test-123",
            user_id=sample_user.id,
            client_id=sample_client.id,
            project_id=sample_project.id,
            tool_name="voice_analysis",
            tool_label="Voice Analysis",
            tool_price=300.0,
            params={"test": "param"},
            outputs={"summary": "test output"},
            data={"voice_score": 85},
            status="completed",
            error_message=None,
            duration_seconds=42.5,
            created_at=datetime(2026, 3, 18, 10, 0, 0),
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=200,
            actual_cost_usd=0.05,
        )
        db.add(research_result)
        db.commit()

        # Make API request
        response = client.get(
            f"/api/research/results/project/{sample_project.id}",
            headers={"Authorization": f"Bearer {sample_user.access_token}"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Verify top-level camelCase fields
        assert "projectId" in data
        assert "clientId" in data

        # Verify results array exists
        assert "results" in data
        assert len(data["results"]) > 0

        # Verify first result has camelCase fields
        first_result = data["results"][0]
        assert "userId" in first_result
        assert "clientId" in first_result
        assert "projectId" in first_result
        assert "toolName" in first_result
        assert "toolLabel" in first_result
        assert "toolPrice" in first_result
        assert "errorMessage" in first_result
        assert "durationSeconds" in first_result
        assert "createdAt" in first_result
        assert "inputTokens" in first_result
        assert "outputTokens" in first_result
        assert "cacheCreationTokens" in first_result
        assert "cacheReadTokens" in first_result
        assert "actualCostUsd" in first_result

        # Verify snake_case fields DO NOT exist
        assert "user_id" not in first_result
        assert "client_id" not in first_result
        assert "tool_name" not in first_result
        assert "created_at" not in first_result

    def test_get_project_research_results_preserves_values(
        self, client, db, sample_user, sample_client, sample_project
    ):
        """Test that alias_generator preserves actual values"""
        # Create research result
        research_result = ResearchResult(
            id="result-values-test",
            user_id=sample_user.id,
            client_id=sample_client.id,
            project_id=sample_project.id,
            tool_name="seo_keyword_research",
            tool_label="SEO Keywords",
            tool_price=400.0,
            params={},
            outputs={"keywords": ["test", "keywords"]},
            status="completed",
            created_at=datetime(2026, 3, 18, 11, 0, 0),
            duration_seconds=55.2,
            input_tokens=1500,
            output_tokens=800,
        )
        db.add(research_result)
        db.commit()

        # Make API request
        response = client.get(
            f"/api/research/results/project/{sample_project.id}",
            headers={"Authorization": f"Bearer {sample_user.access_token}"},
        )

        assert response.status_code == 200
        first_result = response.json()["results"][0]

        # Verify values are preserved correctly
        assert first_result["userId"] == sample_user.id
        assert first_result["clientId"] == sample_client.id
        assert first_result["projectId"] == sample_project.id
        assert first_result["toolName"] == "seo_keyword_research"
        assert first_result["toolPrice"] == 400.0
        assert first_result["durationSeconds"] == 55.2
        assert first_result["inputTokens"] == 1500
        assert first_result["outputTokens"] == 800
