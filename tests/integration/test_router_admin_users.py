"""Integration tests for Admin User Management router endpoints (TR-023)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client(db_session):
    """Create test client with database dependency override."""
    return TestClient(app)


@pytest.fixture
def admin_user(db_session: Session):
    """Create an admin user (superuser)."""
    user = User(
        id="admin-001",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session: Session):
    """Create a regular (non-admin) user."""
    user = User(
        id="user-001",
        email="user@example.com",
        hashed_password=get_password_hash("user123"),
        full_name="Regular User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session):
    """Create an inactive user."""
    user = User(
        id="user-002",
        email="inactive@example.com",
        hashed_password=get_password_hash("inactive123"),
        full_name="Inactive User",
        is_active=False,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user, client, db_session):
    """Get auth headers for admin user."""
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin123",  # pragma: allowlist secret
        },
    )

    if response.status_code != 200:
        print(f"[DEBUG] Admin login failed: {response.status_code}, {response.json()}")

    data = response.json()
    if "access_token" not in data:
        raise ValueError(f"Admin login failed: {data}")

    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture
def regular_headers(regular_user, client, db_session):
    """Get auth headers for regular user."""
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "user@example.com",
            "password": "user123",  # pragma: allowlist secret
        },
    )

    if response.status_code != 200:
        print(f"[DEBUG] User login failed: {response.status_code}, {response.json()}")

    data = response.json()
    if "access_token" not in data:
        raise ValueError(f"User login failed: {data}")

    return {"Authorization": f"Bearer {data['access_token']}"}


# ============================================================================
# Test POST /api/admin/users/{user_id}/activate - Activate User
# ============================================================================


class TestActivateUser:
    """Test activating user accounts."""

    def test_activate_user_as_admin(self, client, admin_headers, inactive_user, db_session):
        """Test admin can activate an inactive user."""
        response = client.post(
            f"/api/admin/users/{inactive_user.id}/activate",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == inactive_user.id
        assert data["isActive"] is True
        assert data["email"] == "inactive@example.com"

    def test_activate_user_as_regular_user(self, client, regular_headers, inactive_user):
        """Test regular user cannot activate users (403 forbidden)."""
        response = client.post(
            f"/api/admin/users/{inactive_user.id}/activate",
            headers=regular_headers,
        )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_activate_user_unauthenticated(self, client, inactive_user):
        """Test unauthenticated request fails."""
        response = client.post(f"/api/admin/users/{inactive_user.id}/activate")

        assert response.status_code == 401

    def test_activate_nonexistent_user(self, client, admin_headers):
        """Test activating non-existent user returns 404."""
        response = client.post(
            "/api/admin/users/nonexistent-id/activate",
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


# ============================================================================
# Test POST /api/admin/users/{user_id}/deactivate - Deactivate User
# ============================================================================


class TestDeactivateUser:
    """Test deactivating user accounts."""

    def test_deactivate_user_as_admin(self, client, admin_headers, regular_user, db_session):
        """Test admin can deactivate an active user."""
        response = client.post(
            f"/api/admin/users/{regular_user.id}/deactivate",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == regular_user.id
        assert data["isActive"] is False
        assert data["email"] == "user@example.com"

    def test_deactivate_user_as_regular_user(self, client, regular_headers, admin_user):
        """Test regular user cannot deactivate users (403 forbidden)."""
        response = client.post(
            f"/api/admin/users/{admin_user.id}/deactivate",
            headers=regular_headers,
        )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_deactivate_self(self, client, admin_headers, admin_user):
        """Test admin cannot deactivate their own account."""
        response = client.post(
            f"/api/admin/users/{admin_user.id}/deactivate",
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "Cannot deactivate your own account" in response.json()["detail"]

    def test_deactivate_unauthenticated(self, client, regular_user):
        """Test unauthenticated request fails."""
        response = client.post(f"/api/admin/users/{regular_user.id}/deactivate")

        assert response.status_code == 401

    def test_deactivate_nonexistent_user(self, client, admin_headers):
        """Test deactivating non-existent user returns 404."""
        response = client.post(
            "/api/admin/users/nonexistent-id/deactivate",
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


# ============================================================================
# Test POST /api/admin/users/{user_id}/promote - Promote to Admin
# ============================================================================


class TestPromoteToAdmin:
    """Test promoting users to admin status."""

    def test_promote_user_as_admin(self, client, admin_headers, regular_user, db_session):
        """Test admin can promote a regular user to admin."""
        response = client.post(
            f"/api/admin/users/{regular_user.id}/promote",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == regular_user.id
        assert data["isSuperuser"] is True
        assert data["email"] == "user@example.com"

    def test_promote_user_as_regular_user(self, client, regular_headers, inactive_user):
        """Test regular user cannot promote users (403 forbidden)."""
        response = client.post(
            f"/api/admin/users/{inactive_user.id}/promote",
            headers=regular_headers,
        )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_promote_already_admin(self, client, admin_headers, admin_user):
        """Test promoting a user who is already admin returns 400."""
        # Create another admin
        response = client.post(
            f"/api/admin/users/{admin_user.id}/promote",
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "already an admin" in response.json()["detail"]

    def test_promote_unauthenticated(self, client, regular_user):
        """Test unauthenticated request fails."""
        response = client.post(f"/api/admin/users/{regular_user.id}/promote")

        assert response.status_code == 401

    def test_promote_nonexistent_user(self, client, admin_headers):
        """Test promoting non-existent user returns 404."""
        response = client.post(
            "/api/admin/users/nonexistent-id/promote",
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


# ============================================================================
# Test POST /api/admin/users/{user_id}/demote - Demote from Admin
# ============================================================================


class TestDemoteFromAdmin:
    """Test demoting users from admin status."""

    def test_demote_user_as_admin(self, client, admin_headers, db_session):
        """Test admin can demote another admin to regular user."""
        # Create a second admin to demote
        second_admin = User(
            id="admin-002",
            email="admin2@example.com",
            hashed_password=get_password_hash("admin2"),
            full_name="Second Admin",
            is_active=True,
            is_superuser=True,
        )
        db_session.add(second_admin)
        db_session.commit()

        response = client.post(
            f"/api/admin/users/{second_admin.id}/demote",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == second_admin.id
        assert data["isSuperuser"] is False

    def test_demote_user_as_regular_user(self, client, regular_headers, admin_user):
        """Test regular user cannot demote admins (403 forbidden)."""
        response = client.post(
            f"/api/admin/users/{admin_user.id}/demote",
            headers=regular_headers,
        )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_demote_self(self, client, admin_headers, admin_user):
        """Test admin cannot demote themselves."""
        response = client.post(
            f"/api/admin/users/{admin_user.id}/demote",
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "Cannot demote your own admin privileges" in response.json()["detail"]

    def test_demote_non_admin(self, client, admin_headers, regular_user):
        """Test demoting a user who is not an admin returns 400."""
        response = client.post(
            f"/api/admin/users/{regular_user.id}/demote",
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "not an admin" in response.json()["detail"]

    def test_demote_unauthenticated(self, client, admin_user):
        """Test unauthenticated request fails."""
        response = client.post(f"/api/admin/users/{admin_user.id}/demote")

        assert response.status_code == 401

    def test_demote_nonexistent_user(self, client, admin_headers):
        """Test demoting non-existent user returns 404."""
        response = client.post(
            "/api/admin/users/nonexistent-id/demote",
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


# ============================================================================
# Test GET /api/admin/users - List All Users
# ============================================================================


class TestListAllUsers:
    """Test listing all users."""

    def test_list_users_as_admin(
        self, client, admin_headers, admin_user, regular_user, inactive_user
    ):
        """Test admin can list all users."""
        response = client.get("/api/admin/users", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least admin, regular, and inactive users

        # Verify users are in the list
        emails = [user["email"] for user in data]
        assert "admin@example.com" in emails
        assert "user@example.com" in emails
        assert "inactive@example.com" in emails

    def test_list_users_as_regular_user(self, client, regular_headers):
        """Test regular user cannot list users (403 forbidden)."""
        response = client.get("/api/admin/users", headers=regular_headers)

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_list_users_unauthenticated(self, client):
        """Test unauthenticated request fails."""
        response = client.get("/api/admin/users")

        assert response.status_code == 401

    def test_list_users_with_pagination(self, client, admin_headers, db_session):
        """Test pagination works correctly."""
        # Create additional users
        for i in range(5):
            user = User(
                id=f"user-{100+i}",
                email=f"user{i}@example.com",
                hashed_password=get_password_hash("pass123"),
                full_name=f"User {i}",
                is_active=True,
                is_superuser=False,
            )
            db_session.add(user)
        db_session.commit()

        # Test with limit
        response = client.get("/api/admin/users?limit=3", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Test with skip
        response = client.get("/api/admin/users?skip=2&limit=3", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


# ============================================================================
# Test GET /api/admin/users/inactive - List Inactive Users
# ============================================================================


class TestListInactiveUsers:
    """Test listing inactive users."""

    def test_list_inactive_users_as_admin(self, client, admin_headers, inactive_user):
        """Test admin can list inactive users."""
        response = client.get("/api/admin/users/inactive", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # All returned users should be inactive
        for user in data:
            assert user["isActive"] is False

        # Verify our inactive user is in the list
        emails = [user["email"] for user in data]
        assert "inactive@example.com" in emails

    def test_list_inactive_users_as_regular_user(self, client, regular_headers):
        """Test regular user cannot list inactive users (403 forbidden)."""
        response = client.get("/api/admin/users/inactive", headers=regular_headers)

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_list_inactive_users_unauthenticated(self, client):
        """Test unauthenticated request fails."""
        response = client.get("/api/admin/users/inactive")

        assert response.status_code == 401


# ============================================================================
# Test GET /api/admin/users/stats - Get User Statistics
# ============================================================================


class TestGetUserStats:
    """Test getting user statistics."""

    def test_get_stats_as_admin(
        self, client, admin_headers, admin_user, regular_user, inactive_user
    ):
        """Test admin can get user statistics."""
        response = client.get("/api/admin/users/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "total" in data
        assert "active" in data
        assert "inactive" in data
        assert "admins" in data

        # Verify counts make sense
        assert data["total"] >= 3  # At least admin, regular, inactive
        assert data["active"] >= 2  # At least admin and regular
        assert data["inactive"] >= 1  # At least inactive user
        assert data["admins"] >= 1  # At least one admin

        # Verify total equals sum of active + inactive
        assert data["total"] == data["active"] + data["inactive"]

    def test_get_stats_as_regular_user(self, client, regular_headers):
        """Test regular user cannot get stats (403 forbidden)."""
        response = client.get("/api/admin/users/stats", headers=regular_headers)

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_get_stats_unauthenticated(self, client):
        """Test unauthenticated request fails."""
        response = client.get("/api/admin/users/stats")

        assert response.status_code == 401


# ============================================================================
# Test POST /api/admin/users - Create User
# ============================================================================


class TestCreateUser:
    """Test creating new users."""

    def test_create_user_as_admin(self, client, admin_headers):
        """Test admin can create a new user."""
        response = client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "email": "newuser@example.com",
                "password": "NewPass123!",  # pragma: allowlist secret
                "full_name": "New User",
                "is_superuser": False,
            },
        )

        if response.status_code != 201:
            print(f"[DEBUG] Create user failed: {response.status_code}, {response.json()}")

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["fullName"] == "New User"
        assert data["isActive"] is True
        assert data["isSuperuser"] is False

    def test_create_admin_user(self, client, admin_headers):
        """Test admin can create a new admin user."""
        response = client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "email": "newadmin@example.com",
                "password": "AdminPass123!",  # pragma: allowlist secret
                "full_name": "New Admin",
                "is_superuser": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newadmin@example.com"
        assert data["isSuperuser"] is True

    def test_create_user_as_regular_user(self, client, regular_headers):
        """Test regular user cannot create users (403 forbidden)."""
        response = client.post(
            "/api/admin/users",
            headers=regular_headers,
            json={
                "email": "another@example.com",
                "password": "Pass123!",  # pragma: allowlist secret
                "full_name": "Another User",
                "is_superuser": False,
            },
        )

        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_create_user_duplicate_email(self, client, admin_headers, regular_user):
        """Test creating user with existing email returns 400."""
        response = client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "email": "user@example.com",  # Already exists
                "password": "Pass123!",  # pragma: allowlist secret
                "full_name": "Duplicate User",
                "is_superuser": False,
            },
        )

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_create_user_unauthenticated(self, client):
        """Test unauthenticated request fails."""
        response = client.post(
            "/api/admin/users",
            json={
                "email": "test@example.com",
                "password": "Pass123!",  # pragma: allowlist secret
                "full_name": "Test User",
                "is_superuser": False,
            },
        )

        assert response.status_code == 401

    def test_create_user_validation(self, client, admin_headers):
        """Test validation errors for invalid data."""
        # Missing required fields
        response = client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "email": "incomplete@example.com",
                # Missing password and full_name
            },
        )

        assert response.status_code == 422  # Validation error
