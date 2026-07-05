"""
Integration tests for projects router.

Tests all project endpoints including:
- List projects (GET /api/projects/)
- Get project (GET /api/projects/{project_id})
- Create project (POST /api/projects/)
- Update project (PATCH /api/projects/{project_id})
- Delete project (DELETE /api/projects/{project_id})
- Authorization checks (TR-021)
- Pagination (hybrid offset/cursor)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project
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
def client_for_user_b(db_session: Session, test_user_b):
    """Create a client owned by user B"""
    client_data = create_test_client(
        name="User B Client",
        user_id=test_user_b.id,
        email="clientb@example.com",
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
    )
    db_project = Project(**project_data)
    db_session.add(db_project)
    db_session.commit()
    db_session.refresh(db_project)
    return db_project


@pytest.fixture
def project_for_user_b(db_session: Session, test_user_b, client_for_user_b):
    """Create a project owned by user B"""
    project_data = create_test_project(
        name="User B Project",
        client_id=client_for_user_b.id,
        user_id=test_user_b.id,
    )
    db_project = Project(**project_data)
    db_session.add(db_project)
    db_session.commit()
    db_session.refresh(db_project)
    return db_project


class TestListProjects:
    """Test GET /api/projects/"""

    def test_list_projects_authenticated(self, client, auth_headers_user_a, project_for_user_a):
        """Test listing projects with authentication"""
        response = client.get("/api/projects/", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data
        # Should see own project
        if isinstance(data, list):
            assert len(data) >= 1
            assert any(p["id"] == project_for_user_a.id for p in data)
        else:
            assert len(data["items"]) >= 1
            assert any(p["id"] == project_for_user_a.id for p in data["items"])

    def test_list_projects_unauthenticated(self, client):
        """Test listing projects without authentication"""
        response = client.get("/api/projects/")
        assert response.status_code == 401

    def test_list_projects_filters_by_user(
        self,
        client,
        auth_headers_user_a,
        auth_headers_user_b,
        project_for_user_a,
        project_for_user_b,
        enforce_ownership,
    ):
        """Test TR-021: Users only see their own projects"""
        # User A should see only their project
        response = client.get("/api/projects/", headers=auth_headers_user_a)
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        assert len(items) >= 1
        assert all(p["id"] != project_for_user_b.id for p in items)
        assert any(p["id"] == project_for_user_a.id for p in items)

        # User B should see only their project
        response = client.get("/api/projects/", headers=auth_headers_user_b)
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        assert len(items) >= 1
        assert all(p["id"] != project_for_user_a.id for p in items)
        assert any(p["id"] == project_for_user_b.id for p in items)

    def test_list_projects_pagination_offset(self, client, auth_headers_user_a):
        """Test offset-based pagination"""
        response = client.get("/api/projects/?offset=0&limit=10", headers=auth_headers_user_a)
        assert response.status_code == 200
        data = response.json()
        # Should have pagination metadata if supported
        if isinstance(data, dict) and "items" in data:
            # Pagination metadata can be in different locations depending on implementation
            has_pagination = (
                "total" in data
                or "has_more" in data
                or (
                    "metadata" in data
                    and ("has_next" in data["metadata"] or "total" in data["metadata"])
                )
            )
            assert has_pagination

    def test_list_projects_pagination_cursor(self, client, auth_headers_user_a):
        """Test cursor-based pagination if supported"""
        response = client.get("/api/projects/?limit=10", headers=auth_headers_user_a)
        assert response.status_code == 200
        data = response.json()
        # Verify response structure
        if isinstance(data, dict):
            assert "items" in data or isinstance(data, list)

    def test_list_projects_filter_by_client(
        self, client, auth_headers_user_a, client_for_user_a, project_for_user_a
    ):
        """Test filtering projects by client_id"""
        response = client.get(
            f"/api/projects/?client_id={client_for_user_a.id}",
            headers=auth_headers_user_a,
        )
        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        # All returned projects should belong to the specified client
        # Note: API response uses camelCase (clientId) due to alias_generator
        if len(items) > 0:
            assert all(p.get("clientId", p.get("client_id")) == client_for_user_a.id for p in items)

    def test_list_projects_filter_by_status(self, client, auth_headers_user_a):
        """Test filtering projects by status"""
        response = client.get(
            "/api/projects/?status=active",
            headers=auth_headers_user_a,
        )
        assert response.status_code == 200
        data = response.json()
        items = data if isinstance(data, list) else data["items"]

        # All returned projects should have active status
        if len(items) > 0:
            assert all(p["status"] == "active" for p in items)


class TestGetProject:
    """Test GET /api/projects/{project_id}"""

    def test_get_project_success(self, client, auth_headers_user_a, project_for_user_a):
        """Test getting project by ID"""
        response = client.get(f"/api/projects/{project_for_user_a.id}", headers=auth_headers_user_a)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_for_user_a.id
        assert data["name"] == project_for_user_a.name
        # Note: API response uses camelCase due to alias_generator
        assert "clientId" in data or "client_id" in data
        assert "status" in data
        assert "numPosts" in data or "num_posts" in data
        assert "platforms" in data

    def test_get_project_unauthorized_user(
        self, client, auth_headers_user_b, project_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot access User A's project"""
        response = client.get(f"/api/projects/{project_for_user_a.id}", headers=auth_headers_user_b)
        assert response.status_code == 403

    def test_get_project_not_found(self, client, auth_headers_user_a):
        """Test getting non-existent project"""
        response = client.get("/api/projects/nonexistent-id", headers=auth_headers_user_a)
        assert response.status_code == 404

    def test_get_project_unauthenticated(self, client, project_for_user_a):
        """Test getting project without authentication"""
        response = client.get(f"/api/projects/{project_for_user_a.id}")
        assert response.status_code == 401


class TestCreateProject:
    """Test POST /api/projects/"""

    def test_create_project_success(self, client, auth_headers_user_a, client_for_user_a):
        """Test creating new project"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "New Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
                "platforms": ["linkedin", "twitter"],
                "templates": ["1", "2", "9"],
                "template_quantities": {"1": 10, "2": 10, "9": 10},
                "price_per_post": 40.0,
                "research_price_per_post": 0.0,
                "total_price": 1200.0,
                "tone": "professional",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        # Note: API response uses camelCase due to alias_generator
        assert data.get("clientId", data.get("client_id")) == client_for_user_a.id
        assert data.get("numPosts", data.get("num_posts")) == 30
        assert data["status"] == "draft"  # Default status
        assert "id" in data
        assert "createdAt" in data or "created_at" in data

    def test_create_project_minimal_fields(self, client, auth_headers_user_a, client_for_user_a):
        """Test creating project with minimal required fields"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Minimal Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Project"
        # Note: API response uses camelCase due to alias_generator
        assert data.get("numPosts", data.get("num_posts")) == 30

    def test_create_project_missing_required_field(
        self, client, auth_headers_user_a, client_for_user_a
    ):
        """Test creating project without required name field"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "client_id": client_for_user_a.id,
                "num_posts": 30,
            },
        )

        assert response.status_code == 422

    def test_create_project_invalid_client_id(self, client, auth_headers_user_a):
        """Test creating project with non-existent client"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Test Project",
                "client_id": "nonexistent-client-id",
                "num_posts": 30,
            },
        )

        assert response.status_code in [400, 404, 422]  # Depends on validation strategy

    def test_create_project_client_owned_by_different_user(
        self, client, auth_headers_user_a, client_for_user_b
    ):
        """Test TR-021: Cannot create project for another user's client"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Unauthorized Project",
                "client_id": client_for_user_b.id,
                "num_posts": 30,
            },
        )

        assert response.status_code in [403, 404]

    def test_create_project_unauthenticated(self, client, client_for_user_a):
        """Test creating project without authentication"""
        response = client.post(
            "/api/projects/",
            json={
                "name": "Test Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
            },
        )

        assert response.status_code == 401

    def test_create_project_assigns_to_current_user(
        self, client, auth_headers_user_a, test_user_a, client_for_user_a, db_session
    ):
        """Test TR-021: Created project is assigned to current user"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Ownership Test Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
            },
        )

        assert response.status_code == 201
        project_id = response.json()["id"]

        # Verify in database that project belongs to user A
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is not None
        assert db_project.user_id == test_user_a.id


class TestUpdateProject:
    """Test PATCH /api/projects/{project_id}"""

    def test_update_project_success(self, client, auth_headers_user_a, project_for_user_a):
        """Test updating project"""
        response = client.patch(
            f"/api/projects/{project_for_user_a.id}",
            headers=auth_headers_user_a,
            json={
                "name": "Updated Project Name",
                "status": "active",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["status"] == "active"

    def test_update_project_partial_update(self, client, auth_headers_user_a, project_for_user_a):
        """Test partial update (only some fields)"""
        original_name = project_for_user_a.name

        response = client.patch(
            f"/api/projects/{project_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"status": "completed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == original_name  # Name unchanged
        assert data["status"] == "completed"  # Status updated

    def test_update_project_unauthorized(
        self, client, auth_headers_user_b, project_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot update User A's project"""
        response = client.patch(
            f"/api/projects/{project_for_user_a.id}",
            headers=auth_headers_user_b,
            json={"name": "Hacked Name"},
        )

        assert response.status_code == 403

    def test_update_project_not_found(self, client, auth_headers_user_a):
        """Test updating non-existent project"""
        response = client.patch(
            "/api/projects/nonexistent-id",
            headers=auth_headers_user_a,
            json={"name": "New Name"},
        )

        assert response.status_code == 404

    def test_update_project_invalid_data(self, client, auth_headers_user_a, project_for_user_a):
        """Test updating with invalid data"""
        response = client.patch(
            f"/api/projects/{project_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"num_posts": -10},  # Invalid negative number
        )

        assert response.status_code == 422

    def test_update_project_status_transition(
        self, client, auth_headers_user_a, project_for_user_a
    ):
        """Test valid status transitions"""
        # Draft → Active
        response = client.patch(
            f"/api/projects/{project_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"status": "active"},
        )
        assert response.status_code == 200

        # Active → Completed
        response = client.patch(
            f"/api/projects/{project_for_user_a.id}",
            headers=auth_headers_user_a,
            json={"status": "completed"},
        )
        assert response.status_code == 200


class TestDeleteProject:
    """Test DELETE /api/projects/{project_id}"""

    def test_delete_project_success(
        self, client, auth_headers_user_a, project_for_user_a, db_session
    ):
        """Test deleting project"""
        project_id = project_for_user_a.id

        response = client.delete(
            f"/api/projects/{project_id}",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 204

        # Verify project is deleted from database
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is None

    def test_delete_project_unauthorized(
        self, client, auth_headers_user_b, project_for_user_a, enforce_ownership
    ):
        """Test TR-021: User B cannot delete User A's project"""
        response = client.delete(
            f"/api/projects/{project_for_user_a.id}",
            headers=auth_headers_user_b,
        )

        assert response.status_code == 403

    def test_delete_project_not_found(self, client, auth_headers_user_a):
        """Test deleting non-existent project"""
        response = client.delete(
            "/api/projects/nonexistent-id",
            headers=auth_headers_user_a,
        )

        assert response.status_code == 404

    def test_delete_project_unauthenticated(self, client, project_for_user_a):
        """Test deleting project without authentication"""
        response = client.delete(f"/api/projects/{project_for_user_a.id}")
        assert response.status_code == 401


class TestProjectDataValidation:
    """Test data validation for project fields"""

    def test_platforms_array_validation(self, client, auth_headers_user_a, client_for_user_a):
        """Test platforms field accepts array"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Test Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
                "platforms": ["linkedin", "twitter", "facebook"],
            },
        )

        assert response.status_code == 201
        assert response.json()["platforms"] == ["linkedin", "twitter", "facebook"]

    def test_templates_array_validation(self, client, auth_headers_user_a, client_for_user_a):
        """Test templates field accepts array of strings"""
        templates = ["1", "2", "3", "9", "10"]
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Test Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
                "templates": templates,
            },
        )

        assert response.status_code == 201
        assert response.json()["templates"] == templates

    def test_template_quantities_dict_validation(
        self, client, auth_headers_user_a, client_for_user_a
    ):
        """Test template_quantities accepts dict with string keys and int values"""
        quantities = {"1": 10, "2": 10, "9": 10}
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Test Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
                "template_quantities": quantities,
            },
        )

        assert response.status_code == 201
        # Note: API response uses camelCase due to alias_generator
        data = response.json()
        assert data.get("templateQuantities", data.get("template_quantities")) == quantities

    def test_pricing_fields_validation(self, client, auth_headers_user_a, client_for_user_a):
        """Test pricing fields accept float values"""
        response = client.post(
            "/api/projects/",
            headers=auth_headers_user_a,
            json={
                "name": "Test Project",
                "client_id": client_for_user_a.id,
                "num_posts": 30,
                "price_per_post": 45.50,
                "research_price_per_post": 5.25,
                "total_price": 1522.50,
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Note: API response uses camelCase due to alias_generator
        assert data.get("pricePerPost", data.get("price_per_post")) == 45.50
        assert data.get("researchPricePerPost", data.get("research_price_per_post")) == 5.25
        assert data.get("totalPrice", data.get("total_price")) == 1522.50
