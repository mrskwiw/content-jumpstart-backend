"""Integration tests for error paths across all major routers.

Covers the unhappy paths (4xx responses) that confirm the API rejects bad
input and enforces authorization boundaries correctly.  Every test class is
scoped to a single router so failures are easy to trace.

Fixtures used from conftest.py:
    client         – FastAPI TestClient
    db_session     – per-test in-memory SQLite session (sets up dependency override)
    test_user      – a committed User row
    test_client    – a committed Client row owned by test_user
    test_project   – a committed Project row owned by test_user
    test_user_headers – Authorization header dict for test_user
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Post, Run
from backend.utils.auth import get_password_hash, create_access_token


# ---------------------------------------------------------------------------
# Local fixtures (supplement the shared conftest fixtures where needed)
# ---------------------------------------------------------------------------


@pytest.fixture
def client(db_session):
    """TestClient that uses the per-test in-memory database."""
    return TestClient(app)


@pytest.fixture
def user_a(db_session: Session):
    """Create user A for cross-user authorization tests."""
    user = User(
        id="user-a-err-001",
        email="user_a_err@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User A Error Tests",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session: Session):
    """Create user B — owns resources that user A must not access."""
    user = User(
        id="user-b-err-002",
        email="user_b_err@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="User B Error Tests",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def headers_user_a(user_a):
    """JWT Authorization header for user A."""
    token = create_access_token(data={"sub": user_a.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_user_b(user_b):
    """JWT Authorization header for user B."""
    token = create_access_token(data={"sub": user_b.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_owned_by_b(db_session: Session, user_b):
    """A Client row owned by user B — should be invisible / forbidden to user A."""
    db_client = Client(
        id="client-b-err-001",
        user_id=user_b.id,
        name="User B Client",
        business_description=(
            "A test client owned by user B for error-path authorization checks "
            "with a description long enough for research tool validation."
        ),
        ideal_customer="IT professionals",
        main_problem_solved="Testing isolation",
    )
    db_session.add(db_client)
    db_session.commit()
    db_session.refresh(db_client)
    return db_client


@pytest.fixture
def project_owned_by_b(db_session: Session, user_b, client_owned_by_b):
    """A Project row owned by user B."""
    project = Project(
        id="proj-b-err-001",
        user_id=user_b.id,
        client_id=client_owned_by_b.id,
        name="User B Project",
        templates=["1"],
        template_quantities={"1": 30},
        num_posts=30,
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def post_owned_by_b(db_session: Session, user_b, project_owned_by_b):
    """A Post row owned (via project) by user B."""
    run = Run(
        id="run-b-err-001",
        project_id=project_owned_by_b.id,
        status="completed",
    )
    db_session.add(run)
    db_session.flush()

    post = Post(
        id="post-b-err-001",
        project_id=project_owned_by_b.id,
        run_id=run.id,
        template_id=1,
        template_name="Test Template",
        content="Sample post content for error path tests.",
        word_count=7,
        status="generated",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


# ---------------------------------------------------------------------------
# Auth errors — every protected route must return 401 without a valid token
# ---------------------------------------------------------------------------


class TestAuthErrors:
    """All protected routes must return 401 when the Authorization header is missing."""

    def test_clients_list_requires_auth(self, client):
        """GET /api/clients/ without a token must return 401."""
        response = client.get("/api/clients/")
        assert response.status_code == 401

    def test_clients_create_requires_auth(self, client):
        """POST /api/clients/ without a token must return 401."""
        response = client.post("/api/clients/", json={"name": "No Auth"})
        assert response.status_code == 401

    def test_clients_get_requires_auth(self, client):
        """GET /api/clients/{id} without a token must return 401."""
        response = client.get("/api/clients/client-nonexistent")
        assert response.status_code == 401

    def test_projects_list_requires_auth(self, client):
        """GET /api/projects/ without a token must return 401."""
        response = client.get("/api/projects/")
        assert response.status_code == 401

    def test_projects_create_requires_auth(self, client):
        """POST /api/projects/ without a token must return 401."""
        response = client.post("/api/projects/", json={"name": "No Auth"})
        assert response.status_code == 401

    def test_posts_get_requires_auth(self, client):
        """GET /api/posts/{id} without a token must return 401."""
        response = client.get("/api/posts/post-nonexistent")
        assert response.status_code == 401

    def test_generator_generate_all_requires_auth(self, client):
        """POST /api/generator/generate-all without a token must return 401."""
        response = client.post("/api/generator/generate-all", json={})
        assert response.status_code == 401

    def test_research_run_requires_auth(self, client):
        """POST /api/research/run without a token must return 401."""
        response = client.post("/api/research/run", json={})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Client route error paths
# ---------------------------------------------------------------------------


class TestClientRouteErrors:
    """Error paths for /api/clients/* routes."""

    def test_create_client_missing_required_field_name(self, client, headers_user_a, db_session):
        """POST /api/clients/ with missing 'name' must return 422."""
        # name is required by the schema — omit it entirely
        response = client.post(
            "/api/clients/",
            json={
                "business_description": "Some description",
            },
            headers=headers_user_a,
        )
        assert response.status_code == 422

    def test_get_nonexistent_client_returns_404(self, client, headers_user_a, db_session):
        """GET /api/clients/{id} with a non-existent id must return 404."""
        response = client.get(
            "/api/clients/client-does-not-exist-xyz",
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_update_nonexistent_client_returns_404(self, client, headers_user_a, db_session):
        """PATCH /api/clients/{id} for a non-existent id must return 404."""
        response = client.patch(
            "/api/clients/client-does-not-exist-xyz",
            json={"name": "Updated"},
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_get_client_owned_by_other_user_returns_404(
        self, client, headers_user_a, client_owned_by_b, db_session, enforce_ownership
    ):
        """GET /api/clients/{id} for a client owned by another user must return 404.

        The API must not leak the existence of other users' resources —
        404 is the expected response (same as non-existent).
        """
        response = client.get(
            f"/api/clients/{client_owned_by_b.id}",
            headers=headers_user_a,
        )
        assert response.status_code in (403, 404)

    def test_delete_nonexistent_client_returns_404(self, client, headers_user_a, db_session):
        """DELETE /api/clients/{id} for a non-existent id must return 404."""
        response = client.delete(
            "/api/clients/client-does-not-exist-xyz",
            headers=headers_user_a,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Project route error paths
# ---------------------------------------------------------------------------


class TestProjectRouteErrors:
    """Error paths for /api/projects/* routes."""

    def test_create_project_with_invalid_client_id_returns_error(
        self, client, headers_user_a, db_session
    ):
        """POST /api/projects/ referencing a non-existent client_id must return 422 or 404."""
        response = client.post(
            "/api/projects/",
            json={
                "client_id": "client-nonexistent-xyz",
                "name": "Ghost Project",
                "templates": ["1"],
                "template_quantities": {"1": 30},
                "num_posts": 30,
            },
            headers=headers_user_a,
        )
        assert response.status_code in (404, 422)

    def test_get_nonexistent_project_returns_404(self, client, headers_user_a, db_session):
        """GET /api/projects/{id} for a non-existent project must return 404."""
        response = client.get(
            "/api/projects/proj-does-not-exist-xyz",
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_get_project_owned_by_other_user_returns_403_or_404(
        self, client, headers_user_a, project_owned_by_b, db_session, enforce_ownership
    ):
        """GET /api/projects/{id} for a project owned by another user must return 403 or 404."""
        response = client.get(
            f"/api/projects/{project_owned_by_b.id}",
            headers=headers_user_a,
        )
        assert response.status_code in (403, 404)

    def test_update_nonexistent_project_returns_404(self, client, headers_user_a, db_session):
        """PATCH /api/projects/{id} for a non-existent project must return 404."""
        response = client.patch(
            "/api/projects/proj-does-not-exist-xyz",
            json={"name": "Ghost"},
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_create_project_missing_required_fields_returns_422(
        self, client, headers_user_a, db_session
    ):
        """POST /api/projects/ with an empty body must return 422."""
        response = client.post(
            "/api/projects/",
            json={},
            headers=headers_user_a,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Brief route error paths
# ---------------------------------------------------------------------------


class TestBriefRouteErrors:
    """Error paths for /api/briefs/* routes."""

    def test_parse_brief_with_empty_body_returns_422(self, client, headers_user_a, db_session):
        """POST /api/briefs/parse with an empty JSON body must return 422."""
        response = client.post(
            "/api/briefs/parse",
            json={},
            headers=headers_user_a,
        )
        assert response.status_code == 422

    def test_get_nonexistent_brief_returns_404(self, client, headers_user_a, db_session):
        """GET /api/briefs/{id} for a non-existent brief must return 404."""
        response = client.get(
            "/api/briefs/brief-does-not-exist-xyz",
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_upload_brief_without_file_returns_422(self, client, headers_user_a, db_session):
        """POST /api/briefs/upload without a multipart file must return 422."""
        response = client.post(
            "/api/briefs/upload",
            headers=headers_user_a,
            # No multipart data — should trigger validation error
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Post route error paths
# ---------------------------------------------------------------------------


class TestPostRouteErrors:
    """Error paths for /api/posts/* routes."""

    def test_get_nonexistent_post_returns_404(self, client, headers_user_a, db_session):
        """GET /api/posts/{id} for a non-existent post must return 404."""
        response = client.get(
            "/api/posts/post-does-not-exist-xyz",
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_get_post_owned_by_other_user_returns_403_or_404(
        self, client, headers_user_a, post_owned_by_b, db_session, enforce_ownership
    ):
        """GET /api/posts/{id} for a post owned by another user must return 403 or 404."""
        response = client.get(
            f"/api/posts/{post_owned_by_b.id}",
            headers=headers_user_a,
        )
        assert response.status_code in (403, 404)

    def test_update_nonexistent_post_returns_404(self, client, headers_user_a, db_session):
        """PATCH /api/posts/{id} for a non-existent post must return 404."""
        response = client.patch(
            "/api/posts/post-does-not-exist-xyz",
            json={"content": "Updated content"},
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_update_post_owned_by_other_user_returns_403_or_404(
        self, client, headers_user_a, post_owned_by_b, db_session, enforce_ownership
    ):
        """PATCH /api/posts/{id} for a post owned by another user must return 403 or 404."""
        response = client.patch(
            f"/api/posts/{post_owned_by_b.id}",
            json={"content": "Unauthorized update"},
            headers=headers_user_a,
        )
        assert response.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Generator route error paths
# ---------------------------------------------------------------------------


class TestGeneratorRouteErrors:
    """Error paths for /api/generator/* routes."""

    def test_generate_all_with_nonexistent_project_returns_404(
        self, client, headers_user_a, db_session
    ):
        """POST /api/generator/generate-all with a non-existent project_id must return 404."""
        response = client.post(
            "/api/generator/generate-all",
            json={"project_id": "proj-does-not-exist-xyz", "client_id": "client-does-not-exist"},
            headers=headers_user_a,
        )
        assert response.status_code == 404

    def test_generate_all_missing_project_id_returns_422(self, client, headers_user_a, db_session):
        """POST /api/generator/generate-all with an empty body must return 422."""
        response = client.post(
            "/api/generator/generate-all",
            json={},
            headers=headers_user_a,
        )
        assert response.status_code == 422

    def test_generate_all_for_project_owned_by_other_user_returns_403_or_404(
        self, client, headers_user_a, project_owned_by_b, db_session
    ):
        """POST /api/generator/generate-all for another user's project must return 403 or 404."""
        response = client.post(
            "/api/generator/generate-all",
            json={"project_id": project_owned_by_b.id, "client_id": "client-b-err-001"},
            headers=headers_user_a,
        )
        assert response.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Research route error paths
# ---------------------------------------------------------------------------


class TestResearchRouteErrors:
    """Error paths for /api/research/* routes."""

    def test_run_research_missing_required_fields_returns_422(
        self, client, headers_user_a, db_session
    ):
        """POST /api/research/run with an empty body must return 422."""
        response = client.post(
            "/api/research/run",
            json={},
            headers=headers_user_a,
        )
        assert response.status_code == 422

    def test_run_research_with_nonexistent_project_returns_404_or_422(
        self, client, headers_user_a, db_session
    ):
        """POST /api/research/run referencing a non-existent project must return 404 or 422."""
        response = client.post(
            "/api/research/run",
            json={
                "tool_name": "seo_keywords",
                "project_id": "proj-does-not-exist-xyz",
                "client_id": "client-does-not-exist-xyz",
            },
            headers=headers_user_a,
        )
        assert response.status_code in (404, 422)

    def test_execute_research_missing_required_fields_returns_422(
        self, client, headers_user_a, db_session
    ):
        """POST /api/research/execute with an empty body must return 422."""
        response = client.post(
            "/api/research/execute",
            json={},
            headers=headers_user_a,
        )
        assert response.status_code == 422

    def test_get_research_results_for_nonexistent_project_returns_404(
        self, client, headers_user_a, db_session
    ):
        """GET /api/research/results/project/{id} for a non-existent project must return 404."""
        response = client.get(
            "/api/research/results/project/proj-does-not-exist-xyz",
            headers=headers_user_a,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# General / cross-cutting error paths
# ---------------------------------------------------------------------------


class TestGeneralErrors:
    """Cross-cutting error behaviors: malformed JSON, non-existent routes, etc."""

    def test_malformed_json_body_returns_422(self, client, headers_user_a, db_session):
        """A request with a malformed JSON body must return 422.

        FastAPI / Starlette catches JSON decode errors and converts them to
        422 Unprocessable Entity responses.
        """
        response = client.post(
            "/api/clients/",
            data="this is { not valid json at all",
            headers={**headers_user_a, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_nonexistent_route_returns_404(self, client):
        """A GET request to an unknown route must return 404."""
        response = client.get("/api/route-that-does-not-exist")
        assert response.status_code == 404

    def test_wrong_http_method_returns_405(self, client):
        """A DELETE request to a GET-only route must return 405 Method Not Allowed."""
        response = client.delete("/api/health")
        assert response.status_code in (404, 405)

    def test_empty_auth_header_returns_401(self, client):
        """An Authorization header with an empty Bearer token must return 401."""
        response = client.get(
            "/api/clients/",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    def test_malformed_bearer_token_returns_401(self, client):
        """An Authorization header with a garbage token value must return 401."""
        response = client.get(
            "/api/clients/",
            headers={"Authorization": "Bearer this.is.not.a.real.jwt"},
        )
        assert response.status_code == 401

    def test_missing_required_field_returns_422(self, client, headers_user_a, db_session):
        """POST /api/clients/ with no body at all must return 422 (body required)."""
        response = client.post(
            "/api/clients/",
            json={},
            headers=headers_user_a,
        )
        assert response.status_code == 422

    def test_expired_token_returns_401(self, client):
        """An expired JWT must be rejected with 401.

        We craft a token with a past expiry using the internal helper.
        """
        from datetime import timedelta

        expired_token = create_access_token(
            data={"sub": "user-expired"},
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get(
            "/api/clients/",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
