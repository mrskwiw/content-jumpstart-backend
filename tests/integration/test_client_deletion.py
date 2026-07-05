"""
Integration tests for client deletion endpoint.

Tests DELETE /api/clients/{client_id} endpoint including:
- Basic deletion
- Cascade deletion with force=true
- Authorization checks (TR-021)
- Validation of associated data
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Brief, Post, Run
from backend.utils.auth import get_password_hash


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-delete-test",
        email="delete@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Delete Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_b(db_session: Session):
    """Create second test user for authorization tests"""
    user = User(
        id="user-delete-b",
        email="deleteb@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Delete Test User B",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get auth headers for test user"""
    response = client.post(
        "/api/auth/login",
        json={"email": "delete@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_b(client, test_user_b):
    """Get auth headers for user B"""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "deleteb@example.com",
            "password": "testpass123",
        },  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_client_record(db_session: Session, test_user):
    """Create a test client record"""
    client_record = Client(
        id="client-delete-test",
        name="Delete Test Client",
        user_id=test_user.id,
    )
    db_session.add(client_record)
    db_session.commit()
    db_session.refresh(client_record)
    return client_record


@pytest.fixture
def test_client_with_project(db_session: Session, test_user):
    """Create a test client with associated project"""
    client_record = Client(
        id="client-with-project",
        name="Client With Project",
        user_id=test_user.id,
    )
    db_session.add(client_record)
    db_session.commit()

    project = Project(
        id="project-for-deletion",
        name="Test Project",
        user_id=test_user.id,
        client_id=client_record.id,
        status="draft",
    )
    db_session.add(project)
    db_session.commit()

    db_session.refresh(client_record)
    return client_record


class TestClientDeletion:
    """Test DELETE /api/clients/{client_id}"""

    def test_delete_client_no_projects(self, client, auth_headers, test_client_record, db_session):
        """Test deleting a client with no associated projects"""
        response = client.delete(
            f"/api/clients/{test_client_record.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify client is deleted
        deleted_client = db_session.query(Client).filter(Client.id == test_client_record.id).first()
        assert deleted_client is None

    def test_delete_client_with_projects_no_force(
        self, client, auth_headers, test_client_with_project, db_session
    ):
        """Test deleting a client with projects without force flag fails"""
        response = client.delete(
            f"/api/clients/{test_client_with_project.id}",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "associated project" in response.json()["detail"].lower()

        # Verify client still exists
        existing_client = (
            db_session.query(Client).filter(Client.id == test_client_with_project.id).first()
        )
        assert existing_client is not None

    def test_delete_client_with_projects_force(
        self, client, auth_headers, test_client_with_project, db_session
    ):
        """Test deleting a client with projects using force=true"""
        response = client.delete(
            f"/api/clients/{test_client_with_project.id}?force=true",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify client is deleted
        deleted_client = (
            db_session.query(Client).filter(Client.id == test_client_with_project.id).first()
        )
        assert deleted_client is None

        # Verify associated project is also deleted
        deleted_project = (
            db_session.query(Project).filter(Project.id == "project-for-deletion").first()
        )
        assert deleted_project is None

    def test_delete_client_unauthorized(
        self, client, auth_headers_b, test_client_record, enforce_ownership
    ):
        """Test TR-021: Cannot delete another user's client"""
        response = client.delete(
            f"/api/clients/{test_client_record.id}",
            headers=auth_headers_b,
        )

        assert response.status_code == 403

    def test_delete_client_not_found(self, client, auth_headers):
        """Test deleting non-existent client"""
        response = client.delete(
            "/api/clients/nonexistent-client-id",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_delete_client_unauthenticated(self, client, test_client_record):
        """Test deleting client without authentication"""
        response = client.delete(
            f"/api/clients/{test_client_record.id}",
        )

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
