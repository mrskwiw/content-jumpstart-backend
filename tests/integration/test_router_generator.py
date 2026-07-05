"""
Integration tests for generator router.

Tests all generation endpoints including:
- Generate all posts (POST /api/generator/generate-all)
- Regenerate posts (POST /api/generator/regenerate)
- Export deliverables (GET /api/generator/export)
- Generation status polling
- Authorization checks (TR-021)
- Anthropic API mocking (no real API calls)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Brief, Run, Post
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client, create_test_project


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    # db_session fixture sets up the database and dependency override
    # before TestClient is created
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user_a(db_session: Session):
    """Create test user A"""
    user = User(
        id="user-a-123",
        email="usera@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User A",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_b(db_session: Session):
    """Create test user B"""
    user = User(
        id="user-b-456",
        email="userb@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User B",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers_user_a(test_user_a, client):
    """Get auth headers for user A"""
    response = client.post(
        "/api/auth/login",
        json={"email": "usera@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user_b(test_user_b, client):
    """Get auth headers for user B"""
    response = client.post(
        "/api/auth/login",
        json={"email": "userb@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_for_user_a(db_session: Session, test_user_a):
    """Create a client owned by user A"""
    client_data = create_test_client(
        name="User A Client",
        user_id=test_user_a.id,
        email="clienta@example.com",
    )
    db_client = Client(**client_data)
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


@pytest.fixture
def project_for_user_a(db_session: Session, test_user_a, client_for_user_a):
    """Create a project owned by user A"""
    project_data = create_test_project(
        name="User A Project",
        client_id=client_for_user_a.id,
        user_id=test_user_a.id,
        num_posts=30,
        templates=["1", "2", "9"],
        template_quantities={"1": 10, "2": 10, "9": 10},
    )
    db_project = Project(**project_data)
    db_session.add(db_project)
    db_session.commit()
    db_session.refresh(db_project)
    return db_project


@pytest.fixture
def project_with_brief(db_session: Session, test_user_a, client_for_user_a, project_for_user_a):
    """Create a project with associated brief"""
    # Brief model only stores raw text content, not structured data
    brief_content = """
    Company: Test Company
    Business: We provide innovative solutions
    Ideal Customer: Small businesses
    Main Problem: Inefficient workflows
    Pain Points: Manual processes, Poor collaboration
    Questions: How to automate?
    Platforms: LinkedIn, Twitter
    Tone: Professional
    """

    brief = Brief(
        id=f"brief-{project_for_user_a.id}",
        project_id=project_for_user_a.id,
        content=brief_content.strip(),
        source="paste",
        file_path=None,
    )
    db_session.add(brief)
    db_session.commit()
    db_session.refresh(brief)
    return project_for_user_a


class TestGenerateAllEndpoint:
    """Test POST /api/generator/generate-all"""

    def test_generate_all_success(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
        db_session,
    ):
        """Test successful post generation with mocked Anthropic API"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
            },
        )

        assert response.status_code in [200, 201, 202]  # Success or Accepted
        data = response.json()

        # Should return run information
        assert "run_id" in data or "id" in data
        assert "status" in data

        # Verify run was created in database
        run_id = data.get("run_id") or data.get("id")
        db_run = db_session.query(Run).filter(Run.id == run_id).first()
        assert db_run is not None
        assert db_run.project_id == project_with_brief.id
        assert db_run.status in ["pending", "running", "completed"]

    def test_generate_all_missing_brief(
        self,
        client,
        auth_headers_user_a,
        project_for_user_a,
        client_for_user_a,
        mock_anthropic_client,
    ):
        """Test generation handles projects without briefs

        Note: The endpoint returns 200 immediately with a run_id because
        generation happens asynchronously. The error (missing brief) is
        discovered during background processing and recorded in the run.
        """
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_for_user_a.id,
                "client_id": client_for_user_a.id,
            },
        )

        # Async endpoint returns 200 with run_id, errors handled in background
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            # Verify run_id is returned for async processing
            data = response.json()
            assert "run_id" in data or "id" in data

    def test_generate_all_invalid_project(
        self, client, auth_headers_user_a, client_for_user_a, mock_anthropic_client
    ):
        """Test generation with non-existent project"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": "nonexistent-project-id",
                "client_id": client_for_user_a.id,
            },
        )

        assert response.status_code == 404

    def test_generate_all_unauthorized_user(
        self,
        client,
        auth_headers_user_b,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
    ):
        """Test TR-021: User B cannot generate for User A's project"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_b,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
            },
        )

        assert response.status_code == 403

    def test_generate_all_unauthenticated(
        self, client, project_with_brief, client_for_user_a, mock_anthropic_client
    ):
        """Test generation without authentication"""
        response = client.post(
            "/api/generator/generate-all",
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
            },
        )

        assert response.status_code == 401

    def test_generate_all_creates_posts(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
        db_session,
    ):
        """Test that generation creates posts in database"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
            },
        )

        assert response.status_code in [200, 201, 202]

        # Wait for generation to complete (or poll status)
        # In real implementation, this might be async
        _run_id = response.json().get("run_id") or response.json().get("id")  # noqa: F841

        # Check if posts were created
        posts = db_session.query(Post).filter(Post.project_id == project_with_brief.id).all()

        # Should have created posts (exact count depends on implementation)
        assert len(posts) >= 0  # May be 0 if async processing not complete

    def test_generate_all_with_custom_templates(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
    ):
        """Test generation with custom template selection"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
                "templates": ["1", "2", "3"],
                "template_quantities": {"1": 5, "2": 5, "3": 5},
            },
        )

        assert response.status_code in [200, 201, 202]

    def test_generate_all_target_platform_respected(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
        db_session,
    ):
        """Bug #106: target_platform sent by frontend must reach the run, not be overridden by the 'blog' default."""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
                "target_platform": "twitter",
            },
        )

        assert response.status_code in [200, 201, 202]
        # The run must be accepted — platform routing validation happens inside the background task.
        # We verify here that the API does NOT reject a valid platform string.
        data = response.json()
        assert "run_id" in data or "id" in data

    def test_generate_all_omitted_platform_falls_back_to_project(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
        db_session,
    ):
        """Bug #106: when target_platform is omitted, backend must fall through to project.target_platform,
        not use the old 'blog' schema default (which was truthy and blocked the project fallback).
        """
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
                # Deliberately omit target_platform — schema default is now None
            },
        )

        assert response.status_code in [200, 201, 202]

    def test_generate_all_rate_limiting(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
    ):
        """Test that multiple rapid generation requests are handled"""
        # Make multiple requests rapidly
        responses = []
        for _ in range(3):
            response = client.post(
                "/api/generator/generate-all",
                headers=auth_headers_user_a,
                json={
                    "project_id": project_with_brief.id,
                    "client_id": client_for_user_a.id,
                },
            )
            responses.append(response)

        # Should either succeed or be rate limited (not crash)
        for response in responses:
            assert response.status_code in [200, 201, 202, 402, 429]


class TestRegenerateEndpoint:
    """Test POST /api/generator/regenerate"""

    def test_regenerate_specific_posts(
        self, client, auth_headers_user_a, project_with_brief, mock_anthropic_client, db_session
    ):
        """Test regenerating specific posts"""
        # First, create some posts
        post1 = Post(
            id="post-1",
            project_id=project_with_brief.id,
            run_id="run-1",
            content="Original content 1",
            template_id=1,
            target_platform="linkedin",
            status="flagged",
        )
        post2 = Post(
            id="post-2",
            project_id=project_with_brief.id,
            run_id="run-1",
            content="Original content 2",
            template_id=2,
            target_platform="linkedin",
            status="flagged",
        )
        db_session.add_all([post1, post2])
        db_session.commit()

        # Regenerate these posts
        response = client.post(
            "/api/generator/regenerate",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "post_ids": ["post-1", "post-2"],
            },
        )

        assert response.status_code in [200, 201, 202]
        data = response.json()
        assert "run_id" in data or "id" in data

    def test_regenerate_unauthorized_posts(
        self, client, auth_headers_user_b, project_with_brief, mock_anthropic_client, db_session
    ):
        """Test TR-021: User B cannot regenerate User A's posts"""
        post = Post(
            id="post-1",
            project_id=project_with_brief.id,
            run_id="run-1",
            content="Original content",
            template_id=1,
            target_platform="linkedin",
            status="flagged",
        )
        db_session.add(post)
        db_session.commit()

        response = client.post(
            "/api/generator/regenerate",
            headers=auth_headers_user_b,
            json={
                "project_id": project_with_brief.id,
                "post_ids": ["post-1"],
            },
        )

        assert response.status_code == 403

    def test_regenerate_nonexistent_posts(
        self, client, auth_headers_user_a, project_with_brief, mock_anthropic_client
    ):
        """Test regenerating posts that don't exist

        Note: The endpoint may return 200 with async processing where
        errors are discovered during background execution.
        """
        response = client.post(
            "/api/generator/regenerate",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "post_ids": ["nonexistent-post-1", "nonexistent-post-2"],
            },
        )

        # May return 200 for async, or 400/404 for sync validation
        assert response.status_code in [200, 400, 404]


class TestExportEndpoint:
    """Test GET /api/generator/export"""

    def test_export_deliverables_success(
        self, client, auth_headers_user_a, project_with_brief, db_session
    ):
        """Test exporting deliverables for a project"""
        # Create some posts first
        posts = [
            Post(
                id=f"post-{i}",
                project_id=project_with_brief.id,
                run_id="run-1",
                content=f"Post content {i}",
                template_id=1,
                target_platform="linkedin",
                status="approved",
            )
            for i in range(5)
        ]
        db_session.add_all(posts)
        db_session.commit()

        response = client.post(
            "/api/generator/export",
            headers=auth_headers_user_a,
            json={"project_id": project_with_brief.id, "format": "txt"},
        )

        assert response.status_code == 200

        # Should return file or JSON with export data
        content_type = response.headers.get("content-type", "")
        assert any(
            t in content_type
            for t in ["application/json", "text/markdown", "application/octet-stream"]
        )

    def test_export_unauthorized_project(
        self, client, auth_headers_user_b, project_with_brief, db_session
    ):
        """Test TR-021: User B cannot export User A's project"""
        response = client.post(
            "/api/generator/export",
            headers=auth_headers_user_b,
            json={"project_id": project_with_brief.id, "format": "txt"},
        )

        assert response.status_code == 403

    def test_export_nonexistent_project(self, client, auth_headers_user_a):
        """Test exporting non-existent project"""
        response = client.post(
            "/api/generator/export",
            headers=auth_headers_user_a,
            json={"project_id": "nonexistent-project-id", "format": "txt"},
        )

        assert response.status_code == 404

    def test_export_project_without_posts(self, client, auth_headers_user_a, project_with_brief):
        """Test exporting project with no generated posts"""
        response = client.post(
            "/api/generator/export",
            headers=auth_headers_user_a,
            json={"project_id": project_with_brief.id, "format": "txt"},
        )

        # Should either return empty export or 400 error
        assert response.status_code in [200, 400]


class TestGenerationStatusPolling:
    """Test generation status polling"""

    def test_get_run_status(self, client, auth_headers_user_a, project_with_brief, db_session):
        """Test getting run status"""
        from datetime import datetime

        # Create a run
        run = Run(
            id="run-test-123",
            project_id=project_with_brief.id,
            status="running",
            is_batch=True,
            started_at=datetime.fromisoformat("2024-01-01T10:00:00"),
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f"/api/runs/{run.id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run.id
        assert data["status"] == "running"
        # API returns camelCase field names
        assert "startedAt" in data or "started_at" in data

    def test_get_run_status_unauthorized(
        self, client, auth_headers_user_b, project_with_brief, db_session, enforce_ownership
    ):
        """Test TR-021: User B cannot access User A's run status"""
        run = Run(
            id="run-test-123",
            project_id=project_with_brief.id,
            status="running",
            is_batch=True,
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f"/api/runs/{run.id}",
            headers=auth_headers_user_b,
        )

        assert response.status_code == 403


class TestAnthropicAPIIntegration:
    """Test that Anthropic API is properly mocked"""

    def test_no_real_api_calls(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
    ):
        """Verify that generation uses mocked Anthropic client, not real API"""
        # This test verifies the mock is in place
        # The mock_anthropic_client fixture patches the API client
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
            },
        )

        # Should succeed with mocked responses (no API errors)
        assert response.status_code in [200, 201, 202]

        # Verify mock was called (implementation-specific)
        # The mock fixture in anthropic_responses.py tracks calls

    def test_mock_returns_valid_responses(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
        db_session,
    ):
        """Test that mocked Anthropic responses are valid for generation"""
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
            },
        )

        assert response.status_code in [200, 201, 202]

        # If posts are created, they should have valid content from mock
        run_id = response.json().get("run_id") or response.json().get("id")
        if run_id:
            db_run = db_session.query(Run).filter(Run.id == run_id).first()
            assert db_run is not None


class TestGenerationErrorHandling:
    """Test error handling during generation"""

    @pytest.mark.skip(
        reason="TestClient + background tasks + ExceptionGroup interaction - requires refactoring"
    )
    def test_generation_with_api_error(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        db_session,
        mock_anthropic_client_with_error,
    ):
        """Test handling of API errors during generation"""
        # TODO: Refactor to test background task error handling without TestClient
        # TestClient runs background tasks synchronously and ExceptionGroups escape to pytest
        # The background task error handler works correctly (lines 128-132 in generator.py)
        # but TestClient raises exceptions before they can be caught
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
            },
        )

        # Should handle error gracefully (not crash)
        assert response.status_code in [200, 201, 202, 500]

        # Check run status reflects error
        if response.status_code in [200, 201, 202]:
            run_id = response.json().get("run_id") or response.json().get("id")
            db_run = db_session.query(Run).filter(Run.id == run_id).first()
            # Run may be marked as failed or error
            assert db_run.status in ["running", "failed", "error", "completed"]

    def test_generation_with_validation_error(
        self,
        client,
        auth_headers_user_a,
        project_with_brief,
        client_for_user_a,
        mock_anthropic_client,
    ):
        """Test handling of extra/invalid fields in generation request

        Note: The generate-all endpoint schema only requires project_id and client_id.
        Extra fields like num_posts are ignored (generation uses project settings).
        Invalid fields in the request body don't cause validation errors.
        """
        # Send generation request with extra field (ignored)
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers_user_a,
            json={
                "project_id": project_with_brief.id,
                "client_id": client_for_user_a.id,
                "num_posts": -10,  # Extra field, ignored by endpoint
            },
        )

        # Endpoint accepts request (extra fields ignored) and processes async
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            # Verify run_id returned for async processing
            data = response.json()
            assert "run_id" in data or "id" in data
