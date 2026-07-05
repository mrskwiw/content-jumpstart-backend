"""
Integration tests for run logs endpoint.

Tests GET /api/runs/{run_id}/logs endpoint including:
- Retrieving logs for a run
- Authorization checks (TR-021)
- Empty logs handling
- Log entry format
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User, Client, Project, Run
from backend.utils.auth import get_password_hash


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user"""
    user = User(
        id="user-logs-test",
        email="logs@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Logs Test User",
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
        id="user-logs-b",
        email="logsb@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Logs Test User B",
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
        json={"email": "logs@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_b(client, test_user_b):
    """Get auth headers for user B"""
    response = client.post(
        "/api/auth/login",
        json={"email": "logsb@example.com", "password": "testpass123"},  # pragma: allowlist secret
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_project(db_session: Session, test_user):
    """Create a test project"""
    # Create client first
    client_record = Client(
        id="client-logs-test",
        name="Logs Test Client",
        user_id=test_user.id,
    )
    db_session.add(client_record)
    db_session.commit()

    project = Project(
        id="project-logs-test",
        name="Logs Test Project",
        user_id=test_user.id,
        client_id=client_record.id,
        status="draft",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_run_with_logs(db_session: Session, test_user, test_project):
    """Create a test run with logs"""
    run = Run(
        id="run-with-logs",
        project_id=test_project.id,
        status="completed",
        logs=[
            {"timestamp": "2025-01-15T10:00:00", "message": "Starting generation", "level": "info"},
            {
                "timestamp": "2025-01-15T10:01:00",
                "message": "Processing templates",
                "level": "info",
            },
            {
                "timestamp": "2025-01-15T10:02:00",
                "message": "Generation completed",
                "level": "info",
            },
        ],
        started_at=datetime.utcnow(),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


@pytest.fixture
def test_run_no_logs(db_session: Session, test_user, test_project):
    """Create a test run without logs"""
    run = Run(
        id="run-no-logs",
        project_id=test_project.id,
        status="completed",
        logs=None,
        started_at=datetime.utcnow(),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


class TestRunLogs:
    """Test GET /api/runs/{run_id}/logs"""

    def test_get_run_logs_success(self, client, auth_headers, test_run_with_logs):
        """Test retrieving logs for a run"""
        response = client.get(
            f"/api/runs/{test_run_with_logs.id}/logs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        logs = response.json()

        assert isinstance(logs, list)
        assert len(logs) == 3

        # Check log entry structure
        first_log = logs[0]
        assert "timestamp" in first_log
        assert "message" in first_log

    def test_get_run_logs_empty(self, client, auth_headers, test_run_no_logs):
        """Test retrieving logs for a run with no logs"""
        response = client.get(
            f"/api/runs/{test_run_no_logs.id}/logs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        logs = response.json()
        assert logs == []

    def test_get_run_logs_unauthorized(
        self, client, auth_headers_b, test_run_with_logs, enforce_ownership
    ):
        """Test TR-021: Cannot view another user's run logs"""
        response = client.get(
            f"/api/runs/{test_run_with_logs.id}/logs",
            headers=auth_headers_b,
        )

        assert response.status_code == 403

    def test_get_run_logs_not_found(self, client, auth_headers):
        """Test retrieving logs for non-existent run"""
        response = client.get(
            "/api/runs/nonexistent-run-id/logs",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_run_logs_unauthenticated(self, client, test_run_with_logs):
        """Test retrieving logs without authentication"""
        response = client.get(
            f"/api/runs/{test_run_with_logs.id}/logs",
        )

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
