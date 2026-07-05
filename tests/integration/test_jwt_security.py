"""
JWT Security Integration Tests

Tests authentication token security including:
- Missing/invalid/tampered tokens
- SQL injection in login
- Brute-force login attempts
- Tokens with nonexistent users
- Weak password registration

OWASP Top 10 2021: A07:2021 - Identification and Authentication Failures
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.models import User
from backend.utils.auth import get_password_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def http_client(db_session):
    """FastAPI TestClient wired to the test database."""
    return TestClient(app)


@pytest.fixture
def registered_user(db_session: Session) -> User:
    """Create a valid user for JWT tests."""
    user = User(
        id="jwt-test-user-001",
        email="jwt_test@example.com",
        hashed_password=get_password_hash("ValidPass123!"),  # pragma: allowlist secret
        full_name="JWT Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# JWT Security Tests
# ---------------------------------------------------------------------------


class TestJWTAuthentication:
    """JWT token validation security tests."""

    def test_no_token_returns_401(self, http_client, db_session):
        """GET /api/clients/ with no auth header returns 401."""
        resp = http_client.get("/api/clients/")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    def test_invalid_token_returns_401(self, http_client, db_session):
        """Bearer with a garbage/random token string returns 401."""
        headers = {"Authorization": "Bearer this_is_not_a_real_jwt_token_garbage_xyz_123"}
        resp = http_client.get("/api/clients/", headers=headers)
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    def test_tampered_token_payload_returns_401(self, http_client, db_session):
        """Token re-signed with wrong secret should be rejected as 401."""
        from jose import jwt

        # Create a token signed with a DIFFERENT secret (attacker does not know real secret)
        wrong_secret = "tampered_secret_that_is_definitely_wrong_and_not_the_real_one"  # pragma: allowlist secret
        payload = {
            "sub": "fake-user-id-attacker",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "type": "access",
        }
        tampered_token = jwt.encode(payload, wrong_secret, algorithm="HS256")

        headers = {"Authorization": f"Bearer {tampered_token}"}
        resp = http_client.get("/api/clients/", headers=headers)
        assert (
            resp.status_code == 401
        ), f"Expected 401 for tampered token, got {resp.status_code}: {resp.text}"

    def test_token_with_none_algorithm_returns_401(self, http_client, db_session):
        """Token constructed with alg:none attack should be rejected with 401."""
        import base64, json

        # Manually craft a JWT with alg=none (classic bypass attempt)
        header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
            .rstrip(b"=")
            .decode()
        )
        payload_data = {
            "sub": "fake-user-id",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "type": "access",
        }
        payload_enc = (
            base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
        )
        # alg=none means empty signature
        none_token = f"{header}.{payload_enc}."

        headers = {"Authorization": f"Bearer {none_token}"}
        resp = http_client.get("/api/clients/", headers=headers)
        assert (
            resp.status_code == 401
        ), f"Expected 401 for alg=none token, got {resp.status_code}: {resp.text}"

    def test_token_with_nonexistent_user_id_returns_401(self, http_client, db_session):
        """Valid-looking JWT with a user ID that does not exist in the DB returns 401."""
        from backend.utils.auth import create_access_token

        # Create a syntactically valid token for a user that does not exist in DB
        token = create_access_token(data={"sub": "nonexistent-user-id-99999"})
        headers = {"Authorization": f"Bearer {token}"}
        resp = http_client.get("/api/clients/", headers=headers)
        assert (
            resp.status_code == 401
        ), f"Expected 401 for nonexistent user token, got {resp.status_code}: {resp.text}"


class TestLoginSecurity:
    """Login endpoint security tests."""

    def test_sql_injection_in_email_returns_422(self, http_client, db_session):
        """POST /api/auth/login with SQL injection payload in email returns 400 or 422.

        The server must either reject the malformed email (422 Unprocessable Entity)
        or treat it as invalid credentials (401). It must not return 200 or 500.
        """
        payload = {
            "email": "' ; DROP TABLE users; --",
            "password": "irrelevant",  # pragma: allowlist secret
        }
        resp = http_client.post("/api/auth/login", json=payload)
        # 422 = Pydantic validation rejected invalid email
        # 401 = Passed validation but no matching user (still safe)
        # Anything but 200 and 500 is acceptable secure behavior
        assert resp.status_code in (
            400,
            401,
            422,
        ), f"SQL injection should be rejected or return 401, got {resp.status_code}: {resp.text}"
        assert resp.status_code != 200, "SQL injection must not result in successful login"
        assert resp.status_code != 500, "SQL injection must not cause internal server error"

    def test_brute_force_login_returns_non_500(self, http_client, db_session):
        """10 rapid failed logins on the same endpoint should not cause 500 errors.

        Acceptable responses: 401 (invalid creds) or 429 (rate limited).
        The key requirement is the server does not crash.
        """
        bad_payload = {
            "email": "brute_force_target@example.com",
            "password": "wrongpassword",  # pragma: allowlist secret
        }
        statuses = []
        for i in range(10):
            resp = http_client.post("/api/auth/login", json=bad_payload)
            statuses.append(resp.status_code)

        for status in statuses:
            assert status in (
                401,
                429,
                422,
            ), f"Expected 401/429/422 during brute force, got {status}"
            assert status != 500, "Server must not crash under brute force"

    def test_register_with_weak_password_returns_422(self, http_client, db_session):
        """POST /api/auth/register with a trivially weak password returns 422.

        Password policy should reject passwords that are too short.
        """
        payload = {
            "email": "newuser_weak@example.com",
            "password": "123",  # pragma: allowlist secret  -- too short
            "full_name": "Weak Password User",
        }
        resp = http_client.post("/api/auth/register", json=payload)
        # 422 = Pydantic/server rejected weak password
        # 400 = Application-level validation rejected it
        assert resp.status_code in (
            400,
            422,
        ), f"Expected 400 or 422 for weak password, got {resp.status_code}: {resp.text}"
        assert resp.status_code != 200, "Server must not accept trivially weak password"

    def test_valid_login_returns_access_and_refresh_tokens(
        self, http_client, db_session, registered_user
    ):
        """Baseline: a valid login should return access_token and refresh_token."""
        resp = http_client.post(
            "/api/auth/login",
            json={
                "email": "jwt_test@example.com",
                "password": "ValidPass123!",
            },  # pragma: allowlist secret
        )
        assert (
            resp.status_code == 200
        ), f"Expected 200 for valid login, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data, "Response must include access_token"
        assert "refresh_token" in data, "Response must include refresh_token"
        assert data["access_token"], "access_token must not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
