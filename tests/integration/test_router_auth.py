"""
Integration tests for auth router.

Tests all authentication endpoints including:
- Login (POST /api/auth/login)
- Token refresh (POST /api/auth/refresh)
- User creation (POST /api/auth/users)
- Rate limiting enforcement
- Authorization checks
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


@pytest.fixture
def client(db_session):
    """Create test client with test database"""
    # db_session fixture sets up the database and dependency override
    # before TestClient is created
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user in the database"""
    user = User(
        id="user-test-123",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session):
    """Create an inactive test user"""
    user = User(
        id="user-inactive-456",
        email="inactive@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Inactive User",
        is_active=False,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestLoginEndpoint:
    """Test POST /api/auth/login"""

    def test_login_success(self, client, test_user):
        """Test successful login with valid credentials"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },  # pragma: allowlist secret
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"

    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypass",
            },  # pragma: allowlist secret
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },  # pragma: allowlist secret
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_inactive_user(self, client, inactive_user):
        """Test login with inactive user account"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "testpass123",
            },  # pragma: allowlist secret
        )

        assert response.status_code in [401, 403]  # Could be 401 or 403 depending on implementation
        assert "inactive" in response.json()["detail"].lower()

    def test_login_missing_fields(self, client):
        """Test login with missing required fields"""
        # Missing password
        response = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422

        # Missing email
        response = client.post(
            "/api/auth/login", json={"password": "testpass123"}
        )  # pragma: allowlist secret
        assert response.status_code == 422

        # Empty body
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format"""
        response = client.post(
            "/api/auth/login",
            json={"email": "not-an-email", "password": "testpass123"},  # pragma: allowlist secret
        )

        assert response.status_code == 422

    def test_login_rate_limiting(self, client, test_user):
        """Test rate limiting (10 requests per hour per IP)"""
        # Make 11 login attempts
        for i in range(11):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "testpass123",
                },  # pragma: allowlist secret
            )

            if i < 10:
                # First 10 should go through (may fail with 200, 401, or 404 but not 429)
                assert response.status_code != 429, f"Request {i+1} was prematurely rate limited"
            else:
                # 11th should be rate limited
                assert response.status_code == 429
                data = response.json()
                assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
                assert "retry_after" in data["error"]

                # Verify headers
                assert "Retry-After" in response.headers
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert response.headers["X-RateLimit-Remaining"] == "0"
                assert "X-RateLimit-Reset" in response.headers


class TestRefreshTokenEndpoint:
    """Test POST /api/auth/refresh"""

    def test_refresh_token_success(self, client, test_user):
        """Test refreshing valid token"""
        # First, login to get tokens
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },  # pragma: allowlist secret
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new access token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """Test refreshing with invalid token"""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token-12345"},
        )

        assert response.status_code == 401

    def test_refresh_token_using_access_token(self, client, test_user):
        """Test using access token instead of refresh token (should fail)"""
        # Login to get access token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },  # pragma: allowlist secret
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token as refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )

        # Should fail because token type is wrong
        assert response.status_code == 401

    def test_refresh_token_missing(self, client):
        """Test refresh without providing token"""
        response = client.post("/api/auth/refresh", json={})
        assert response.status_code == 422


class TestUserCreationEndpoint:
    """Test POST /api/auth/users (if it exists)"""

    @pytest.mark.skip(reason="User creation endpoint may not exist yet")
    def test_create_user_success(self, client):
        """Test creating new user"""
        response = client.post(
            "/api/auth/users",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",  # pragma: allowlist secret
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "password" not in data  # Password should not be returned
        assert "hashed_password" not in data

    @pytest.mark.skip(reason="User creation endpoint may not exist yet")
    def test_create_user_duplicate_email(self, client, test_user):
        """Test creating user with existing email"""
        response = client.post(
            "/api/auth/users",
            json={
                "email": "test@example.com",  # Already exists
                "password": "SecurePass123!",  # pragma: allowlist secret
                "full_name": "Duplicate User",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.skip(reason="User creation endpoint may not exist yet")
    def test_create_user_weak_password(self, client):
        """Test password validation"""
        # Too short
        response = client.post(
            "/api/auth/users",
            json={
                "email": "user@example.com",
                "password": "123",
                "full_name": "User",
            },  # pragma: allowlist secret
        )
        assert response.status_code == 422

        # No special characters (if required)
        response = client.post(
            "/api/auth/users",
            json={
                "email": "user@example.com",
                "password": "password123",
                "full_name": "User",
            },  # pragma: allowlist secret
        )
        # May pass or fail depending on password policy
        assert response.status_code in [201, 422]


class TestAuthenticationHeaders:
    """Test authentication header handling"""

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/clients/")
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        response = client.get(
            "/api/clients/",
            headers={"Authorization": "Bearer invalid-token-12345"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client, test_user):
        """Test accessing protected endpoint with valid token"""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },  # pragma: allowlist secret
        )
        access_token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/api/clients/",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Should succeed (200) or fail with 403 if no clients (not 401)
        assert response.status_code in [200, 403]

    def test_malformed_authorization_header(self, client):
        """Test with malformed Authorization header"""
        # Missing 'Bearer' prefix
        response = client.get(
            "/api/clients/",
            headers={"Authorization": "token-12345"},
        )
        assert response.status_code == 401

        # Wrong prefix
        response = client.get(
            "/api/clients/",
            headers={"Authorization": "Basic token-12345"},
        )
        assert response.status_code == 401


class TestTokenExpiration:
    """Test token expiration handling"""

    @pytest.mark.skip(reason="Requires time manipulation or short-lived tokens")
    def test_expired_access_token(self, client):
        """Test that expired access tokens are rejected"""
        # This would require creating a token with very short expiry
        # or mocking the current time
        pass

    @pytest.mark.skip(reason="Requires time manipulation or short-lived tokens")
    def test_expired_refresh_token(self, client):
        """Test that expired refresh tokens are rejected"""
        pass


class TestPasswordSecurity:
    """Test password hashing and security"""

    def test_password_not_returned_in_response(self, client, test_user):
        """Test that password is never returned in API responses"""
        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },  # pragma: allowlist secret
        )

        data = response.json()

        # Check for an actual leak, not the substring "password": the response legitimately
        # carries `mustChangePassword` (S-01.4f), which made the old blanket substring
        # assertion fail on a boolean flag while proving nothing about secrecy.
        blob = str(data)
        assert "testpass123" not in blob  # the plaintext we just sent
        assert "$2b$" not in blob and "$2a$" not in blob  # a bcrypt hash
        user = data["user"]
        leaky = [k for k in user if "password" in k.lower() and k != "mustChangePassword"]
        assert not leaky, f"user payload exposes password-ish fields: {leaky}"

    def test_password_hash_different_for_same_password(self, db_session):
        """Test that same password hashes to different values (salted)"""
        from backend.utils.auth import get_password_hash

        hash1 = get_password_hash("samepassword")
        hash2 = get_password_hash("samepassword")

        # Hashes should be different due to salt
        assert hash1 != hash2

    def test_password_verification(self, db_session):
        """Test password verification function"""
        from backend.utils.auth import get_password_hash, verify_password

        password = "testpass123"  # pragma: allowlist secret
        hashed = get_password_hash(password)

        # Correct password should verify
        assert verify_password(password, hashed) is True

        # Wrong password should not verify
        assert verify_password("wrongpassword", hashed) is False
