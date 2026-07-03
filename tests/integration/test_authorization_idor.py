"""
Integration tests for Authorization / IDOR Protection (TR-021)

Tests that users can only access their own resources and cannot access
resources owned by other users (Insecure Direct Object Reference prevention).

OWASP Top 10 2021: A01:2021 - Broken Access Control
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project
from backend.services import crud
from backend.schemas.client import ClientCreate
from backend.schemas.project import ProjectCreate
from backend.utils.auth import get_password_hash
from tests.fixtures.model_factories import create_test_client


@pytest.fixture(autouse=True)
def _idor_enforce_ownership(monkeypatch):
    """Enable per-user ownership enforcement for all IDOR tests."""
    monkeypatch.setattr(
        "backend.middleware.authorization._ownership_enforcement_enabled",
        lambda: True,
    )


# ---------------------------------------------------------------------------
# HTTP TestClient fixture (shared by all HTTP-level tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def http_client(db_session):
    """FastAPI TestClient wired to the test database."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# User fixtures -- direct User(...) model pattern (not crud.create_user)
# ---------------------------------------------------------------------------


@pytest.fixture
def user_a(db_session: Session) -> User:
    """Create test user A."""
    user = User(
        id="idor-user-a-001",
        email="user_a_idor@example.com",
        hashed_password=get_password_hash("Password123!"),  # pragma: allowlist secret
        full_name="User A",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session: Session) -> User:
    """Create test user B."""
    user = User(
        id="idor-user-b-002",
        email="user_b_idor@example.com",
        hashed_password=get_password_hash("Password123!"),  # pragma: allowlist secret
        full_name="User B",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def superuser(db_session: Session) -> User:
    """Create superuser."""
    user = User(
        id="idor-admin-003",
        email="admin_idor@example.com",
        hashed_password=get_password_hash("Admin123!"),  # pragma: allowlist secret
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Resource fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_a(db_session: Session, user_a: User) -> Client:
    """Create client owned by user A."""
    client_data = ClientCreate(
        name="Client A",
        email="client_a@example.com",
        business_description="Business A",
        ideal_customer="Customer A",
        main_problem_solved="Problem A",
    )
    return crud.create_client(db_session, client_data, user_id=user_a.id)


@pytest.fixture
def client_b(db_session: Session, user_b: User) -> Client:
    """Create client owned by user B."""
    client_data = ClientCreate(
        name="Client B",
        email="client_b@example.com",
        business_description="Business B",
        ideal_customer="Customer B",
        main_problem_solved="Problem B",
    )
    return crud.create_client(db_session, client_data, user_id=user_b.id)


@pytest.fixture
def project_a(db_session: Session, user_a: User, client_a: Client) -> Project:
    """Create project owned by user A."""
    project_data = ProjectCreate(
        name="Project A",
        client_id=client_a.id,
        num_posts=30,
    )
    return crud.create_project(db_session, project_data, user_id=user_a.id)


@pytest.fixture
def project_b(db_session: Session, user_b: User, client_b: Client) -> Project:
    """Create project owned by user B."""
    project_data = ProjectCreate(
        name="Project B",
        client_id=client_b.id,
        num_posts=30,
    )
    return crud.create_project(db_session, project_data, user_id=user_b.id)


# ---------------------------------------------------------------------------
# Auth-header helper
# ---------------------------------------------------------------------------


def _login(http_client, email: str, password: str) -> dict:
    """Return Authorization headers for the given credentials."""
    resp = http_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},  # pragma: allowlist secret
    )
    if resp.status_code != 200:
        raise ValueError(f"Login failed for {email}: {resp.status_code} {resp.text}")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Original unit-level IDOR tests (middleware helpers)
# ===========================================================================


class TestClientIDORPrevention:
    """Test client ownership authorization prevents IDOR attacks."""

    def test_cannot_access_other_user_client(self, db_session, user_a, user_b, client_a, client_b):
        """User cannot access another user client via IDOR attack."""
        from backend.middleware.authorization import _check_ownership

        assert _check_ownership("Client", client_a, user_a) is True
        assert _check_ownership("Client", client_b, user_a) is False


class TestProjectIDORPrevention:
    """Test project ownership authorization prevents IDOR attacks."""

    def test_cannot_access_other_user_project(
        self, db_session, user_a, user_b, project_a, project_b
    ):
        """User cannot access another user project via IDOR attack."""
        from backend.middleware.authorization import _check_ownership

        assert _check_ownership("Project", project_a, user_a) is True
        assert _check_ownership("Project", project_b, user_a) is False


class TestSuperuserBypass:
    """Test superuser can bypass ownership checks."""

    def test_superuser_can_access_all_resources(self, db_session, superuser, client_a, project_a):
        """Superuser can access resources from any user."""
        from backend.middleware.authorization import _check_ownership

        assert _check_ownership("Client", client_a, superuser) is True
        assert _check_ownership("Project", project_a, superuser) is True


class TestOwnershipFiltering:
    """Test list operations filter by ownership."""

    def test_filter_user_clients_only_shows_own(
        self, db_session, user_a, user_b, client_a, client_b
    ):
        """Filter should only return user own clients."""
        from backend.middleware.authorization import filter_user_clients

        query_a = filter_user_clients(db_session, user_a)
        clients_a = query_a.all()
        assert len(clients_a) == 1
        assert clients_a[0].id == client_a.id

        query_b = filter_user_clients(db_session, user_b)
        clients_b = query_b.all()
        assert len(clients_b) == 1
        assert clients_b[0].id == client_b.id

    def test_filter_user_projects_only_shows_own(
        self, db_session, user_a, user_b, project_a, project_b
    ):
        """Filter should only return user own projects."""
        from backend.middleware.authorization import filter_user_projects

        query_a = filter_user_projects(db_session, user_a)
        projects_a = query_a.all()
        assert len(projects_a) == 1
        assert projects_a[0].id == project_a.id

        query_b = filter_user_projects(db_session, user_b)
        projects_b = query_b.all()
        assert len(projects_b) == 1
        assert projects_b[0].id == project_b.id


# ===========================================================================
# HTTP-level IDOR tests (10 additional tests)
# ===========================================================================


class TestClientIDORHTTP:
    """HTTP-level IDOR tests against /api/clients/ endpoints."""

    def test_get_client_returns_403_for_wrong_user(
        self, http_client, db_session, user_a, user_b, client_b
    ):
        """GET /api/clients/{id} returns 403/404 when user reads another user client."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.get(f"/api/clients/{client_b.id}", headers=headers_a)
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403 or 404, got {resp.status_code}: {resp.text}"

    def test_update_client_returns_403_for_wrong_user(
        self, http_client, db_session, user_a, user_b, client_b
    ):
        """PATCH /api/clients/{id} returns 403/404 when user updates another user client."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.patch(
            f"/api/clients/{client_b.id}",
            json={"name": "Hacked Name"},
            headers=headers_a,
        )
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403 or 404, got {resp.status_code}: {resp.text}"

    def test_delete_client_returns_403_for_wrong_user(
        self, http_client, db_session, user_a, user_b, client_b
    ):
        """DELETE /api/clients/{id} returns 403/404 when user deletes another user client."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.delete(f"/api/clients/{client_b.id}", headers=headers_a)
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403 or 404, got {resp.status_code}: {resp.text}"

    def test_list_clients_does_not_show_other_users_clients(
        self, http_client, db_session, user_a, user_b, client_a, client_b
    ):
        """GET /api/clients/ only returns the authenticated user own clients."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.get("/api/clients/", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", data.get("clients", []))
        ids_returned = [c.get("id") for c in items]
        assert (
            client_b.id not in ids_returned
        ), f"User A should not see Client B ({client_b.id}) in list. Got: {ids_returned}"

    def test_archive_client_returns_403_for_wrong_user(
        self, http_client, db_session, user_a, user_b, client_b
    ):
        """POST /api/clients/{id}/archive returns 403/404 when user archives another user client."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.post(f"/api/clients/{client_b.id}/archive", headers=headers_a)
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403 or 404, got {resp.status_code}: {resp.text}"

    def test_cannot_forge_client_ownership_via_create(
        self, http_client, db_session, user_a, user_b
    ):
        """POST /api/clients/ does not accept user_id in request body (extra fields forbidden).

        Two secure behaviors are acceptable:
        1. Schema rejects extra field user_id with 422 (Pydantic extra=forbid).
        2. Server accepts but ignores user_id, assigning authenticated user as owner.
        In either case the attack does not succeed.
        """
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret

        # Attempt 1: try to forge ownership by passing user_id in body
        payload_with_userid = {
            "name": "Forged Client",
            "email": "forged@example.com",
            "user_id": user_b.id,
            "business_description": "An attempt to forge ownership.",
            "ideal_customer": "Hackers",
            "main_problem_solved": "IDOR",
        }
        resp = http_client.post("/api/clients/", json=payload_with_userid, headers=headers_a)
        # 422 means schema rejected extra field (secure), 200/201 means server accepted but must assign correct owner
        assert resp.status_code in (
            200,
            201,
            422,
        ), f"Unexpected status {resp.status_code}: {resp.text}"
        if resp.status_code == 422:
            # Pydantic extra=forbid -- this is the preferred secure outcome
            return

        created = resp.json()
        assert (
            created.get("user_id") != user_b.id
        ), "Server accepted forged user_id -- IDOR vulnerability!"
        assert (
            created.get("user_id") == user_a.id
        ), f"Expected user_id={user_a.id}, got {created.get('user_id')}"

        # Attempt 2: create without user_id -- server must assign authenticated user
        payload_clean = {
            "name": "Clean Forged Client",
            "email": "clean_forged@example.com",
            "business_description": "Clean ownership test.",
            "ideal_customer": "Normal users",
            "main_problem_solved": "Testing",
        }
        resp2 = http_client.post("/api/clients/", json=payload_clean, headers=headers_a)
        assert resp2.status_code in (
            200,
            201,
        ), f"Expected 200/201, got {resp2.status_code}: {resp2.text}"
        created2 = resp2.json()
        assert (
            created2.get("user_id") == user_a.id
        ), f"Server must assign authenticated user as owner. Expected {user_a.id}, got {created2.get('user_id')}"


class TestProjectIDORHTTP:
    """HTTP-level IDOR tests against /api/projects/ endpoints."""

    def test_get_project_returns_403_for_wrong_user(
        self, http_client, db_session, user_a, user_b, project_b
    ):
        """GET /api/projects/{id} returns 403/404 when user reads another user project."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.get(f"/api/projects/{project_b.id}", headers=headers_a)
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403 or 404, got {resp.status_code}: {resp.text}"

    def test_update_project_returns_403_for_wrong_user(
        self, http_client, db_session, user_a, user_b, project_b
    ):
        """PATCH /api/projects/{id} returns 403/404 when user updates another user project."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.patch(
            f"/api/projects/{project_b.id}",
            json={"name": "Hacked Project"},
            headers=headers_a,
        )
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403 or 404, got {resp.status_code}: {resp.text}"

    def test_delete_project_returns_403_for_wrong_user(
        self, http_client, db_session, user_a, user_b, project_b
    ):
        """DELETE /api/projects/{id} returns 403/404 when user deletes another user project."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.delete(f"/api/projects/{project_b.id}", headers=headers_a)
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403 or 404, got {resp.status_code}: {resp.text}"

    def test_list_projects_does_not_show_other_users_projects(
        self, http_client, db_session, user_a, user_b, project_a, project_b
    ):
        """GET /api/projects/ only returns the authenticated user own projects."""
        headers_a = _login(
            http_client, "user_a_idor@example.com", "Password123!"
        )  # pragma: allowlist secret
        resp = http_client.get("/api/projects/", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", data.get("projects", []))
        ids_returned = [p.get("id") for p in items]
        assert (
            project_b.id not in ids_returned
        ), f"User A should not see Project B ({project_b.id}) in list. Got: {ids_returned}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
