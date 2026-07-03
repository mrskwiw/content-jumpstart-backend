"""
End-to-end workflow integration tests.

Simulates real operator workflows:
1. Create client → create project → verify linkage
2. Project status lifecycle
3. Brief creation tied to projects
4. Deliverable listing and 404 handling

All tests use the db_session fixture for full isolation (in-memory SQLite).
Anthropic API calls are mocked via the mock_anthropic_client fixture
imported automatically in conftest.py.

TR-021: Authorization tests verify that users can only access their own data.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Deliverable
from backend.utils.auth import get_password_hash, create_access_token
from tests.fixtures.model_factories import (
    create_test_client,
    create_test_project,
    create_test_deliverable,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(db_session):
    """Create test client backed by the isolated test database."""
    return TestClient(app)


@pytest.fixture
def user_a(db_session: Session):
    """Primary operator user (User A)."""
    user = User(
        id="user-workflow-a01",
        email="workflow_a@example.com",
        hashed_password=get_password_hash("TestPass1!secure"),  # pragma: allowlist secret
        full_name="Workflow User A",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session: Session):
    """Secondary operator user (User B) for cross-user authorization tests."""
    user = User(
        id="user-workflow-b01",
        email="workflow_b@example.com",
        hashed_password=get_password_hash("TestPass1!secure"),  # pragma: allowlist secret
        full_name="Workflow User B",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def headers_a(user_a):
    """JWT Bearer headers for User A."""
    token = create_access_token(data={"sub": user_a.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_b(user_b):
    """JWT Bearer headers for User B."""
    token = create_access_token(data={"sub": user_b.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_client_a(db_session: Session, user_a):
    """A Client record owned by User A, created directly in the database."""
    data = create_test_client(name="Client A Corp", user_id=user_a.id)
    record = Client(**data)
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


@pytest.fixture
def db_client_b(db_session: Session, user_b):
    """A Client record owned by User B."""
    data = create_test_client(name="Client B Inc", user_id=user_b.id)
    record = Client(**data)
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


@pytest.fixture
def db_project_a(db_session: Session, user_a, db_client_a):
    """A Project owned by User A, linked to db_client_a."""
    data = create_test_project(
        name="Project Alpha",
        client_id=db_client_a.id,
        user_id=user_a.id,
        status="draft",
    )
    record = Project(**data)
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


@pytest.fixture
def db_project_b(db_session: Session, user_b, db_client_b):
    """A Project owned by User B."""
    data = create_test_project(
        name="Project Beta",
        client_id=db_client_b.id,
        user_id=user_b.id,
        status="draft",
    )
    record = Project(**data)
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# TestClientProjectWorkflow
# ---------------------------------------------------------------------------


class TestClientProjectWorkflow:
    """End-to-end tests: create clients and projects via the HTTP API."""

    def test_create_client_and_project(self, client, db_session, headers_a, user_a):
        """
        Full happy path: POST /api/clients/ → POST /api/projects/.
        The created project must reference the new client's id.
        """
        # Step 1 — create client
        client_resp = client.post(
            "/api/clients/",
            headers=headers_a,
            json={
                "name": "Happy Path Client",
                "business_description": "We help companies automate repetitive tasks.",
                "ideal_customer": "SMBs with 10-50 employees",
            },
        )
        assert client_resp.status_code == 201
        client_id = client_resp.json()["id"]
        assert client_id.startswith("client-")

        # Step 2 — create project linked to that client
        project_resp = client.post(
            "/api/projects/",
            headers=headers_a,
            json={
                "name": "Linked Project",
                "client_id": client_id,
                "num_posts": 30,
            },
        )
        assert project_resp.status_code == 201
        project_data = project_resp.json()
        assert project_data.get("clientId", project_data.get("client_id")) == client_id

    def test_project_requires_valid_client(self, client, db_session, headers_a):
        """
        Creating a project with a non-existent client_id must be rejected.
        The server returns 400, 404, or 422 depending on where validation occurs.
        """
        response = client.post(
            "/api/projects/",
            headers=headers_a,
            json={
                "name": "Orphan Project",
                "client_id": "client-doesnotexist",
                "num_posts": 30,
            },
        )
        assert response.status_code in [400, 404, 422]

    def test_update_client_name(self, client, db_session, headers_a, db_client_a):
        """
        PATCH /api/clients/{id} with a new name, then GET to confirm the update
        was persisted.  The response name must match the patched value.
        """
        new_name = "Renamed Corp"
        patch_resp = client.patch(
            f"/api/clients/{db_client_a.id}",
            headers=headers_a,
            json={"name": new_name},
        )
        assert patch_resp.status_code == 200
        # ClientResponse serializes 'name' as 'companyName' via serialization_alias
        resp_data = patch_resp.json()
        assert resp_data.get("companyName", resp_data.get("name")) == new_name

        # Confirm persistence via GET
        get_resp = client.get(f"/api/clients/{db_client_a.id}", headers=headers_a)
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data.get("companyName", get_data.get("name")) == new_name

    def test_list_clients_shows_created_client(self, client, db_session, headers_a, db_client_a):
        """
        GET /api/clients/ for User A must include the client that was seeded
        into the database for User A.  User isolation (TR-021) means only
        User A's clients appear.
        """
        response = client.get("/api/clients/", headers=headers_a)

        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        ids = [item["id"] for item in items]
        assert db_client_a.id in ids

    def test_list_clients_does_not_show_other_users_clients(
        self, client, db_session, headers_a, db_client_a, db_client_b, enforce_ownership
    ):
        """
        TR-021: User A's client list must not contain any clients belonging to
        User B, even if both exist in the same database.
        """
        response = client.get("/api/clients/", headers=headers_a)

        assert response.status_code == 200
        ids = [item["id"] for item in response.json()]
        assert db_client_b.id not in ids

    def test_list_projects_shows_created_project(self, client, db_session, headers_a, db_project_a):
        """
        GET /api/projects/ for User A must include the project that was seeded
        for User A.
        """
        response = client.get("/api/projects/", headers=headers_a)

        assert response.status_code == 200
        data = response.json()
        # Endpoint returns paginated dict {"items": [...]} or a plain list
        items = data.get("items", data) if isinstance(data, dict) else data
        ids = [item["id"] for item in items]
        assert db_project_a.id in ids

    def test_list_projects_does_not_show_other_users_projects(
        self, client, db_session, headers_a, db_project_a, db_project_b, enforce_ownership
    ):
        """
        TR-021: User A must not see User B's projects in the project list.
        """
        response = client.get("/api/projects/", headers=headers_a)

        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        ids = [item["id"] for item in items]
        assert db_project_b.id not in ids


# ---------------------------------------------------------------------------
# TestProjectStatusWorkflow
# ---------------------------------------------------------------------------


class TestProjectStatusWorkflow:
    """Test project status field behavior."""

    def test_new_project_has_draft_status(self, client, db_session, headers_a, db_client_a):
        """
        A newly created project should default to 'draft' status when no
        status field is supplied in the creation payload.
        """
        response = client.post(
            "/api/projects/",
            headers=headers_a,
            json={
                "name": "Status Test Project",
                "client_id": db_client_a.id,
                "num_posts": 30,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"

    def test_update_project_name(self, client, db_session, headers_a, db_project_a):
        """
        PATCH /api/projects/{id} with a new name should return 200 and the
        response body must reflect the updated name.
        """
        new_name = "Renamed Alpha Project"
        response = client.patch(
            f"/api/projects/{db_project_a.id}",
            headers=headers_a,
            json={"name": new_name},
        )

        assert response.status_code == 200
        assert response.json()["name"] == new_name

    def test_update_project_status_to_active(self, client, db_session, headers_a, db_project_a):
        """
        PATCH /api/projects/{id} with status='active' should succeed and the
        returned project must have status 'active'.
        """
        response = client.patch(
            f"/api/projects/{db_project_a.id}",
            headers=headers_a,
            json={"status": "active"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_get_project_returns_correct_client_link(
        self, client, db_session, headers_a, db_project_a, db_client_a
    ):
        """
        GET /api/projects/{id} must return the project with clientId matching
        the client that was used when the project was created.
        """
        response = client.get(f"/api/projects/{db_project_a.id}", headers=headers_a)

        assert response.status_code == 200
        data = response.json()
        returned_client_id = data.get("clientId", data.get("client_id"))
        assert returned_client_id == db_client_a.id

    def test_user_b_cannot_update_user_a_project(
        self, client, db_session, headers_b, db_project_a, enforce_ownership
    ):
        """
        TR-021: User B must not be allowed to PATCH a project owned by User A.
        The server must return 403.
        """
        response = client.patch(
            f"/api/projects/{db_project_a.id}",
            headers=headers_b,
            json={"name": "Hijacked Name"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# TestBriefWorkflow
# ---------------------------------------------------------------------------


class TestBriefWorkflow:
    """Test brief creation and retrieval tied to projects."""

    def test_create_brief_for_project(self, client, db_session, headers_a, db_project_a):
        """
        POST /api/briefs/create with a valid project_id and content should
        return 201 and create a brief linked to that project.
        """
        response = client.post(
            "/api/briefs/create",
            headers=headers_a,
            json={
                "project_id": db_project_a.id,
                "content": (
                    "Company Name: Test Corp\n"
                    "Business Description: We build software tools for small teams.\n"
                    "Ideal Customer: Founders and solopreneurs needing productivity help.\n"
                    "Main Problem Solved: Fragmented tooling and context switching.\n"
                ),
            },
        )

        assert response.status_code == 201
        data = response.json()
        project_id_field = data.get("projectId", data.get("project_id"))
        assert project_id_field == db_project_a.id

    def test_create_brief_duplicate_returns_400(self, client, db_session, headers_a, db_project_a):
        """
        Creating a second brief for the same project should fail with 400 because
        the system enforces one brief per project.
        """
        payload = {
            "project_id": db_project_a.id,
            "content": "Company Name: Test\nBusiness Description: A business description here.",
        }

        first = client.post("/api/briefs/create", headers=headers_a, json=payload)
        assert first.status_code == 201

        second = client.post("/api/briefs/create", headers=headers_a, json=payload)
        assert second.status_code == 400

    def test_brief_requires_project_ownership(self, client, db_session, headers_b, db_project_a):
        """
        TR-021: User B must not be able to create a brief for a project owned by
        User A.  The server must return 403 Forbidden.
        """
        response = client.post(
            "/api/briefs/create",
            headers=headers_b,
            json={
                "project_id": db_project_a.id,
                "content": "Unauthorized brief content attempt.",
            },
        )
        assert response.status_code in [403, 404]

    def test_brief_missing_content_returns_422(self, client, db_session, headers_a, db_project_a):
        """
        Omitting the required 'content' field from the brief creation payload
        must return 422 Unprocessable Entity.
        """
        response = client.post(
            "/api/briefs/create",
            headers=headers_a,
            json={"project_id": db_project_a.id},
        )
        assert response.status_code == 422

    def test_brief_missing_project_id_returns_422(self, client, db_session, headers_a):
        """
        Omitting the required 'project_id' field from the brief creation payload
        must return 422 Unprocessable Entity.
        """
        response = client.post(
            "/api/briefs/create",
            headers=headers_a,
            json={"content": "Some content without a project id."},
        )
        assert response.status_code == 422

    def test_create_brief_for_nonexistent_project_returns_404(self, client, db_session, headers_a):
        """
        Creating a brief for a project that does not exist must return 404.
        """
        response = client.post(
            "/api/briefs/create",
            headers=headers_a,
            json={
                "project_id": "proj-doesnotexist",
                "content": "Brief for a ghost project.",
            },
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestDeliverableWorkflow
# ---------------------------------------------------------------------------


class TestDeliverableWorkflow:
    """Test deliverable listing and retrieval."""

    def test_list_deliverables_requires_auth(self, client, db_session):
        """
        GET /api/deliverables/ without authentication must return 401.
        """
        response = client.get("/api/deliverables/")
        assert response.status_code == 401

    def test_list_deliverables_for_user_returns_200(self, client, db_session, headers_a):
        """
        An authenticated request to GET /api/deliverables/ must return 200
        and a list (which may be empty if the user has no deliverables yet).
        """
        response = client.get("/api/deliverables/", headers=headers_a)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_deliverables_for_project(
        self, client, db_session, headers_a, user_a, db_client_a, db_project_a
    ):
        """
        After seeding a Deliverable in the database, GET /api/deliverables/ must
        include that deliverable in the response list for the owning user.
        """
        # Seed a deliverable directly into the test database
        deliv_data = create_test_deliverable(
            project_id=db_project_a.id,
            client_id=db_client_a.id,
        )
        deliverable = Deliverable(**deliv_data)
        db_session.add(deliverable)
        db_session.commit()
        db_session.refresh(deliverable)

        response = client.get("/api/deliverables/", headers=headers_a)

        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        ids = [item["id"] for item in items]
        assert deliverable.id in ids

    def test_get_nonexistent_deliverable_returns_404(self, client, db_session, headers_a):
        """
        GET /api/deliverables/{id} with an id that does not exist in the database
        must return 404 Not Found.
        """
        response = client.get("/api/deliverables/deliv-doesnotexist", headers=headers_a)
        assert response.status_code == 404

    def test_user_b_cannot_see_user_a_deliverables(
        self, client, db_session, headers_b, user_a, db_client_a, db_project_a, enforce_ownership
    ):
        """
        TR-021: A deliverable created under User A's project must not be visible
        to User B.  The list endpoint filters by the authenticated user's ownership.
        """
        # Seed deliverable for User A's project
        deliv_data = create_test_deliverable(
            project_id=db_project_a.id,
            client_id=db_client_a.id,
        )
        deliverable = Deliverable(**deliv_data)
        db_session.add(deliverable)
        db_session.commit()
        db_session.refresh(deliverable)

        # User B should not see User A's deliverable
        response = client.get("/api/deliverables/", headers=headers_b)

        assert response.status_code == 200
        ids = [item["id"] for item in response.json()]
        assert deliverable.id not in ids

    def test_deliverable_filter_by_client_id(
        self, client, db_session, headers_a, db_client_a, db_project_a
    ):
        """
        GET /api/deliverables/?client_id={id} should only return deliverables
        that belong to the specified client.
        """
        deliv_data = create_test_deliverable(
            project_id=db_project_a.id,
            client_id=db_client_a.id,
        )
        deliverable = Deliverable(**deliv_data)
        db_session.add(deliverable)
        db_session.commit()
        db_session.refresh(deliverable)

        response = client.get(
            f"/api/deliverables/?client_id={db_client_a.id}",
            headers=headers_a,
        )

        assert response.status_code == 200
        items = response.json()
        # All returned items must belong to the requested client
        for item in items:
            assert item.get("clientId", item.get("client_id")) == db_client_a.id
