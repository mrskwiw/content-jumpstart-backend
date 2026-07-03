"""
Integration tests for authentication flow.

Tests all authentication endpoints including:
- User registration (POST /api/auth/register)
- User login (POST /api/auth/login)
- Token refresh (POST /api/auth/refresh)
- Protected endpoint access with JWT tokens

Password policy (TR-013): min 12 chars, uppercase, lowercase, digit, special character.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash, create_access_token, create_refresh_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(db_session):
    """Create test client backed by the isolated test database."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Pre-create an active test user for login/token tests."""
    user = User(
        id="user-auth-test01",
        email="authtest@example.com",
        hashed_password=get_password_hash("TestPass1!secure"),  # pragma: allowlist secret
        full_name="Auth Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session):
    """Pre-create an inactive test user to verify login is blocked."""
    user = User(
        id="user-auth-inactive",
        email="inactive@example.com",
        hashed_password=get_password_hash("TestPass1!secure"),  # pragma: allowlist secret
        full_name="Inactive User",
        is_active=False,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session):
    """Pre-create a non-admin user for admin endpoint authorization tests."""
    user = User(
        id="user-non-admin-01",
        email="nonadmin@example.com",
        hashed_password=get_password_hash("TestPass1!secure"),  # pragma: allowlist secret
        full_name="Non-Admin User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def valid_registration_payload():
    """Return a valid registration payload that satisfies password policy."""
    return {
        "email": "newuser@example.com",
        "password": "Secur3P@ssWrd!",  # pragma: allowlist secret
        "full_name": "New User",
    }


# ---------------------------------------------------------------------------
# TestUserRegistration
# ---------------------------------------------------------------------------


class TestUserRegistration:
    """Test POST /api/auth/register"""

    def test_register_new_user(self, client, db_session, valid_registration_payload):
        """
        Registering with a valid payload should succeed and return token + user info.

        The endpoint returns 201 with access_token, refresh_token, and a user object
        containing id, email, full_name, and is_active.
        """
        response = client.post("/api/auth/register", json=valid_registration_payload)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

        # User object may use camelCase due to alias_generator
        user = data.get("user", {})
        email_field = user.get("email", "")
        assert email_field == valid_registration_payload["email"]

    def test_register_duplicate_email_returns_400_or_409(
        self, client, db_session, valid_registration_payload
    ):
        """
        Registering the same email twice should fail with 400 or 409.

        The first registration creates the account; the second must be rejected
        to prevent duplicate accounts.
        """
        # First registration succeeds
        first = client.post("/api/auth/register", json=valid_registration_payload)
        assert first.status_code == 201

        # Second registration with identical email must fail
        second = client.post("/api/auth/register", json=valid_registration_payload)
        assert second.status_code in [400, 409]

    def test_register_missing_email_returns_422(self, client, db_session):
        """
        Registration without an email field should return 422 Unprocessable Entity
        because email is a required field in the UserCreate schema.
        """
        response = client.post(
            "/api/auth/register",
            json={
                "password": "Secur3P@ssWrd!",
                "full_name": "No Email",
            },  # pragma: allowlist secret
        )
        assert response.status_code == 422

    def test_register_missing_password_returns_422(self, client, db_session):
        """
        Registration without a password field should return 422 Unprocessable Entity
        because password is a required field in the UserCreate schema.
        """
        response = client.post(
            "/api/auth/register",
            json={"email": "nopwd@example.com", "full_name": "No Password"},
        )
        assert response.status_code == 422

    def test_register_invalid_email_format_returns_422(self, client, db_session):
        """
        Registration with a malformed email (not a valid RFC-5321 address) should
        return 422 because Pydantic EmailStr rejects it during validation.
        """
        response = client.post(
            "/api/auth/register",
            json={
                "email": "notanemail",
                "password": "Secur3P@ssWrd!",  # pragma: allowlist secret
                "full_name": "Bad Email",
            },
        )
        assert response.status_code == 422

    def test_register_weak_password_returns_400(self, client, db_session):
        """
        Registration with a password that fails the password policy (TR-013)
        should return 400.  The policy requires 12+ chars, upper, lower, digit,
        and at least one special character.
        """
        response = client.post(
            "/api/auth/register",
            json={
                "email": "weakpwd@example.com",
                "password": "short",  # pragma: allowlist secret
                "full_name": "Weak Password",
            },
        )
        assert response.status_code in [400, 422]


# ---------------------------------------------------------------------------
# TestUserLogin
# ---------------------------------------------------------------------------


class TestUserLogin:
    """Test POST /api/auth/login"""

    def test_login_valid_credentials(self, client, test_user):
        """
        Logging in with correct email and password should return 200 and
        include both access_token and refresh_token in the response body.
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "authtest@example.com",
                "password": "TestPass1!secure",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_password_returns_401(self, client, test_user):
        """
        Logging in with the correct email but a wrong password must return 401
        to prevent information disclosure about account existence.
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "authtest@example.com",
                "password": "WrongPassword1!",  # pragma: allowlist secret
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client, db_session):
        """
        Logging in with an email that has never been registered must return 401
        rather than 404 to avoid leaking whether accounts exist.
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "ghost@example.com",
                "password": "AnyPass1!secure",  # pragma: allowlist secret
            },
        )
        assert response.status_code == 401

    def test_login_returns_jwt_token(self, client, test_user):
        """
        The access_token returned after a successful login must be a non-empty
        string (a valid JWT has three dot-separated base64url segments).
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "authtest@example.com",
                "password": "TestPass1!secure",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 200
        token = response.json()["access_token"]
        assert isinstance(token, str)
        assert len(token) > 0
        # A JWT has exactly two dots (three segments)
        assert token.count(".") == 2

    def test_login_missing_fields_returns_422(self, client, db_session):
        """
        Submitting an empty body to the login endpoint should return 422 because
        both email and password are required fields in LoginRequest.
        """
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_login_inactive_user_returns_403(self, client, inactive_user):
        """
        An inactive user account should be rejected with 403 even when the
        password is correct, because is_active must be True for access.
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "TestPass1!secure",  # pragma: allowlist secret
            },
        )
        assert response.status_code == 403

    def test_login_response_includes_user_info(self, client, test_user):
        """
        The login response should contain a 'user' object with id, email,
        and is_active so the frontend can populate the session without a
        separate /me request.
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": "authtest@example.com",
                "password": "TestPass1!secure",  # pragma: allowlist secret
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        user = data["user"]
        # email field — may be snake_case or camelCase depending on alias_generator
        assert "email" in user or "Email" in user
        assert "id" in user


# ---------------------------------------------------------------------------
# TestTokenRefresh
# ---------------------------------------------------------------------------


class TestTokenRefresh:
    """Test POST /api/auth/refresh"""

    def test_refresh_valid_token(self, client, test_user):
        """
        Providing a valid refresh token should return 200 with a new access_token
        and a new refresh_token (token rotation).
        """
        # Obtain a real refresh token via login
        login_resp = client.post(
            "/api/auth/login",
            json={
                "email": "authtest@example.com",
                "password": "TestPass1!secure",  # pragma: allowlist secret
            },
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_refresh_invalid_token_returns_401(self, client, db_session):
        """
        Providing a garbage string as the refresh token should return 401 because
        the server cannot verify its signature or token type claim.
        """
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "this.is.garbage"},
        )
        assert response.status_code == 401

    def test_refresh_missing_token_returns_422_or_401(self, client, db_session):
        """
        Omitting the refresh_token field from the request body should return
        422 (schema validation failure) or 401 (auth failure).
        """
        response = client.post("/api/auth/refresh", json={})
        assert response.status_code in [401, 422]

    def test_refresh_returns_new_token_pair(self, client, test_user):
        """
        The refresh response should contain both access_token and refresh_token,
        allowing clients to replace their stored token pair atomically.
        """
        login_resp = client.post(
            "/api/auth/login",
            json={
                "email": "authtest@example.com",
                "password": "TestPass1!secure",  # pragma: allowlist secret
            },
        )
        original_refresh = login_resp.json()["refresh_token"]

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": original_refresh},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_using_access_token_returns_401(self, client, test_user):
        """
        Passing an access token (token_type='access') to the refresh endpoint
        must be rejected with 401; the endpoint requires a refresh-type token.
        """
        # Get an access token
        login_resp = client.post(
            "/api/auth/login",
            json={
                "email": "authtest@example.com",
                "password": "TestPass1!secure",  # pragma: allowlist secret
            },
        )
        access_token = login_resp.json()["access_token"]

        # Attempt to refresh using the access token instead of refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestProtectedEndpoints
# ---------------------------------------------------------------------------


class TestProtectedEndpoints:
    """Test JWT-protected endpoint access behavior."""

    def test_authenticated_request_succeeds(self, client, test_user):
        """
        A valid Bearer token in the Authorization header should allow access to
        the clients list endpoint, which requires authentication (TR-021).
        """
        access_token = create_access_token(data={"sub": test_user.id})
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/clients/", headers=headers)
        assert response.status_code == 200

    def test_unauthenticated_request_returns_401(self, client, db_session):
        """
        A request to a protected endpoint without any Authorization header
        must return 401 Unauthorized.
        """
        response = client.get("/api/clients/")
        assert response.status_code == 401

    def test_malformed_bearer_token_returns_401(self, client, db_session):
        """
        A malformed token (not a valid JWT) in the Authorization header must
        return 401 and must not expose internal error details.
        """
        headers = {"Authorization": "Bearer this.is.not.a.real.jwt.token"}
        response = client.get("/api/clients/", headers=headers)
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client, test_user):
        """
        A token with an expiry timestamp in the past must be rejected with 401.
        The server checks the 'exp' claim on every request.
        """
        # Create a token that expired 1 hour ago
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_token = create_access_token(
            data={"sub": test_user.id},
            expires_delta=timedelta(seconds=-1),
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/clients/", headers=headers)
        assert response.status_code == 401

    def test_wrong_user_token_for_admin_endpoint_returns_403(self, client, admin_user):
        """
        A valid token belonging to a non-superuser account must be rejected with
        403 when it tries to access an admin-only endpoint (e.g., list all users).
        """
        access_token = create_access_token(data={"sub": admin_user.id})
        headers = {"Authorization": f"Bearer {access_token}"}

        # /api/admin/users/ requires is_superuser=True
        response = client.get("/api/admin/users/", headers=headers)
        assert response.status_code == 403
