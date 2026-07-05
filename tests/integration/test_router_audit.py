"""Integration tests for the audit trail router (GET /api/audit/*)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.models.audit_log import AuditLog
from backend.utils.auth import get_password_hash


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    user = User(
        id="audit-user-001",
        email="audituser@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Audit Tester",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session: Session):
    user = User(
        id="audit-other-002",
        email="otheraudit@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Other User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user, client, db_session):
    db_session.commit()
    response = client.post(
        "/api/auth/login",
        json={
            "email": "audituser@example.com",
            "password": "testpass123",
        },  # pragma: allowlist secret
    )
    data = response.json()
    if "access_token" not in data:
        raise ValueError(f"Login failed: {data}")
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture
def sample_entries(db_session: Session, test_user):
    """Seed three audit log entries for test_user and one for other_user."""
    entries = [
        AuditLog(
            id="al-test-create",
            user_id=test_user.id,
            user_email=test_user.email,
            user_name=test_user.full_name,
            action="Created client",
            action_type="create",
            resource_type="client",
            resource_id="client-001",
            resource_name="Acme Corp",
            status="success",
        ),
        AuditLog(
            id="al-test-update",
            user_id=test_user.id,
            user_email=test_user.email,
            user_name=test_user.full_name,
            action="Updated project",
            action_type="update",
            resource_type="project",
            resource_id="proj-001",
            resource_name="Spring Campaign",
            status="success",
        ),
        AuditLog(
            id="al-test-delete",
            user_id=test_user.id,
            user_email=test_user.email,
            user_name=test_user.full_name,
            action="Deleted client",
            action_type="delete",
            resource_type="client",
            resource_id="client-002",
            resource_name="Old Corp",
            status="success",
        ),
        # Entry belonging to a different user — must NOT appear in test_user's results
        AuditLog(
            id="al-other-user",
            user_id="audit-other-002",
            user_email="otheraudit@example.com",
            user_name="Other User",
            action="Created project",
            action_type="create",
            resource_type="project",
            resource_id="proj-999",
            resource_name="Hidden",
            status="success",
        ),
    ]
    for e in entries:
        db_session.add(e)
    db_session.commit()
    return entries


class TestAuditListEndpoint:
    def test_list_requires_auth(self, client):
        response = client.get("/api/audit/")
        assert response.status_code == 401

    def test_list_returns_only_own_entries(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        ids = {e["id"] for e in data}
        # Own entries present
        assert "al-test-create" in ids
        assert "al-test-update" in ids
        assert "al-test-delete" in ids
        # Other user's entry absent
        assert "al-other-user" not in ids

    def test_list_entry_has_required_fields(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/", headers=auth_headers)
        assert response.status_code == 200
        entry = next(e for e in response.json() if e["id"] == "al-test-create")
        assert "timestamp" in entry
        assert entry["action"] == "Created client"
        assert entry["actionType"] == "create"
        assert entry["resourceType"] == "client"
        assert entry["resource"] == "Client: Acme Corp"
        assert entry["status"] == "success"
        assert "user" in entry
        assert entry["user"]["email"] == "audituser@example.com"

    def test_filter_by_action_type(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/?action_type=create", headers=auth_headers)
        assert response.status_code == 200
        entries = response.json()
        assert all(e["actionType"] == "create" for e in entries)
        ids = {e["id"] for e in entries}
        assert "al-test-create" in ids
        assert "al-test-update" not in ids

    def test_filter_by_resource_type(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/?resource_type=project", headers=auth_headers)
        assert response.status_code == 200
        entries = response.json()
        assert all(e["resourceType"] == "project" for e in entries)
        ids = {e["id"] for e in entries}
        assert "al-test-update" in ids
        assert "al-test-create" not in ids

    def test_pagination_skip_limit(self, client, auth_headers, sample_entries):
        # There are 3 own entries; skip=1 limit=1 should return exactly one
        response = client.get("/api/audit/?skip=1&limit=1", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestAuditStatsEndpoint:
    def test_stats_requires_auth(self, client):
        response = client.get("/api/audit/stats")
        assert response.status_code == 401

    def test_stats_returns_expected_shape(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for key in (
            "totalEvents",
            "todayEvents",
            "failedActions",
            "securityEvents",
            "avgEventsPerDay",
            "retentionDays",
        ):
            assert key in data, f"Missing key: {key}"

    def test_stats_total_events_counts_own_entries(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/stats", headers=auth_headers)
        data = response.json()
        # 3 own entries; other-user entry should NOT count
        assert data["totalEvents"] == 3

    def test_stats_retention_days_is_90(self, client, auth_headers):
        response = client.get("/api/audit/stats", headers=auth_headers)
        assert response.json()["retentionDays"] == 90


class TestAuditExportEndpoints:
    def test_csv_export_requires_auth(self, client):
        response = client.get("/api/audit/export.csv")
        assert response.status_code == 401

    def test_csv_export_returns_csv_content_type(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/export.csv", headers=auth_headers)
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_csv_export_has_header_row(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/export.csv", headers=auth_headers)
        first_line = response.text.splitlines()[0]
        assert "id" in first_line
        assert "action" in first_line
        assert "status" in first_line

    def test_json_export_requires_auth(self, client):
        response = client.get("/api/audit/export.json")
        assert response.status_code == 401

    def test_json_export_returns_list(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/export.json", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3  # Only own entries


class TestSuperuserVisibility:
    """Superusers see all users' entries; regular users see only their own."""

    @pytest.fixture
    def superuser(self, db_session: Session):
        user = User(
            id="audit-admin-999",
            email="admin@example.com",
            hashed_password=get_password_hash("adminpass123"),
            full_name="Admin User",
            is_active=True,
            is_superuser=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def admin_headers(self, superuser, client, db_session):
        db_session.commit()
        response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@example.com",
                "password": "adminpass123",
            },  # pragma: allowlist secret
        )
        data = response.json()
        if "access_token" not in data:
            raise ValueError(f"Admin login failed: {data}")
        return {"Authorization": f"Bearer {data['access_token']}"}

    def test_superuser_sees_all_entries(self, client, admin_headers, sample_entries):
        response = client.get("/api/audit/", headers=admin_headers)
        assert response.status_code == 200
        ids = {e["id"] for e in response.json()}
        # Entries from both test_user and other_user are visible
        assert "al-test-create" in ids
        assert "al-other-user" in ids

    def test_superuser_stats_include_all_users(self, client, admin_headers, sample_entries):
        response = client.get("/api/audit/stats", headers=admin_headers)
        assert response.status_code == 200
        # 4 total entries (3 from test_user + 1 from other_user)
        assert response.json()["totalEvents"] == 4

    def test_regular_user_still_scoped(self, client, auth_headers, sample_entries):
        response = client.get("/api/audit/", headers=auth_headers)
        ids = {e["id"] for e in response.json()}
        assert "al-other-user" not in ids
