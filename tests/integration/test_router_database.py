"""
Integration tests for the database administration router.

The router no longer manages SQLite backups — it returns Supabase instructions
for GET /backup and 501 Not Implemented for the old SQLite-only endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(db_session):
    return TestClient(app)


@pytest.fixture
def admin_user(db_session: Session):
    user = User(
        id="admin-db-001",
        email="dbadmin@example.com",
        hashed_password=get_password_hash("DbAdmin123!"),
        full_name="DB Admin",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session: Session):
    user = User(
        id="user-db-001",
        email="dbuser@example.com",
        hashed_password=get_password_hash("DbUser123!"),
        full_name="DB User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user, client, db_session):
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "dbadmin@example.com", "password": "DbAdmin123!"},
    )
    data = resp.json()
    if "access_token" not in data:
        raise ValueError(f"Admin login failed: {data}")
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture
def regular_headers(regular_user, client, db_session):
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "dbuser@example.com", "password": "DbUser123!"},
    )
    data = resp.json()
    if "access_token" not in data:
        raise ValueError(f"User login failed: {data}")
    return {"Authorization": f"Bearer {data['access_token']}"}


# ---------------------------------------------------------------------------
# GET /api/database/status
# ---------------------------------------------------------------------------


class TestDatabaseStatus:
    def test_admin_can_get_status(self, client, admin_headers):
        resp = client.get("/api/database/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "connected"
        assert "schema_version" in data
        assert "database_host" in data
        assert "engine" in data

    def test_regular_user_gets_403(self, client, regular_headers):
        resp = client.get("/api/database/status", headers=regular_headers)
        assert resp.status_code == 403
        assert "Admin privileges required" in resp.json()["detail"]

    def test_unauthenticated_gets_401(self, client):
        resp = client.get("/api/database/status")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/database/backup  — returns Supabase instructions, not a file
# ---------------------------------------------------------------------------


class TestBackupInstructions:
    def test_admin_gets_instructions(self, client, admin_headers):
        resp = client.get("/api/database/backup", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "options" in data
        assert "pg_dump" in data["options"]
        assert "dashboard" in data["options"]

    def test_admin_backup_contains_pg_dump_command(self, client, admin_headers):
        resp = client.get("/api/database/backup", headers=admin_headers)
        assert resp.status_code == 200
        assert "pg_dump" in str(resp.json())

    def test_regular_user_gets_403(self, client, regular_headers):
        resp = client.get("/api/database/backup", headers=regular_headers)
        assert resp.status_code == 403
        assert "Admin privileges required" in resp.json()["detail"]

    def test_unauthenticated_gets_401(self, client):
        resp = client.get("/api/database/backup")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/database/restore  — returns 501 (SQLite restore removed)
# ---------------------------------------------------------------------------


class TestRestoreNotAvailable:
    def test_admin_gets_501(self, client, admin_headers):
        resp = client.post("/api/database/restore", headers=admin_headers)
        assert resp.status_code == 501
        assert "SQLite restore is not available" in resp.json()["detail"]

    def test_regular_user_gets_403(self, client, regular_headers):
        resp = client.post("/api/database/restore", headers=regular_headers)
        assert resp.status_code == 403

    def test_unauthenticated_gets_401(self, client):
        resp = client.post("/api/database/restore")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/database/merge  — returns 501 (SQLite merge removed)
# ---------------------------------------------------------------------------


class TestMergeNotAvailable:
    def test_admin_gets_501(self, client, admin_headers):
        resp = client.post("/api/database/merge", headers=admin_headers)
        assert resp.status_code == 501
        assert "SQLite merge is not available" in resp.json()["detail"]

    def test_regular_user_gets_403(self, client, regular_headers):
        resp = client.post("/api/database/merge", headers=regular_headers)
        assert resp.status_code == 403

    def test_unauthenticated_gets_401(self, client):
        resp = client.post("/api/database/merge")
        assert resp.status_code == 401
