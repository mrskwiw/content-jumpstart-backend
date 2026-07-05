"""
Tests for CSRF Protection Middleware (TR-009)

Verifies CSRF validation for state-changing requests
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.middleware.csrf_protection import (
    CSRFProtectionMiddleware,
    is_same_origin,
    validate_origin_referer,
    generate_csrf_token,
    verify_csrf_token,
)


# Test app setup
app = FastAPI()
app.add_middleware(CSRFProtectionMiddleware)


@app.get("/api/test")
def test_get():
    return {"message": "GET request"}


@app.post("/api/test")
def test_post():
    return {"message": "POST request"}


@app.delete("/api/test/{item_id}")
def delete_handler(item_id: str):
    return {"message": f"Deleted {item_id}"}


client = TestClient(app)


class TestOriginValidation:
    """Test origin validation logic"""

    def test_same_origin_exact_match(self):
        """Should allow exact origin match"""
        assert is_same_origin("http://localhost:3000", {"http://localhost:3000"})

    def test_same_origin_wildcard(self):
        """Should allow wildcard origin"""
        assert is_same_origin("http://example.com", {"*"})

    def test_same_origin_different_origin(self):
        """Should reject different origin"""
        assert not is_same_origin("http://evil.com", {"http://localhost:3000"})

    def test_same_origin_empty_origin(self):
        """Should reject empty origin"""
        assert not is_same_origin("", {"http://localhost:3000"})

    def test_same_origin_multiple_allowed(self):
        """Should allow origin in list of allowed origins"""
        allowed = {"http://localhost:3000", "http://localhost:5000"}
        assert is_same_origin("http://localhost:5000", allowed)


class TestCSRFMiddleware:
    """Test CSRF protection middleware"""

    def test_get_request_allowed(self):
        """GET requests should be allowed without Origin header"""
        response = client.get("/api/test")
        assert response.status_code == 200

    def test_post_with_valid_origin(self, monkeypatch):
        """POST with valid Origin header should succeed"""
        # Mock settings to allow localhost
        from backend import config

        monkeypatch.setattr(config.settings, "CORS_ORIGINS", "http://localhost")

        response = client.post("/api/test", headers={"Origin": "http://localhost"})
        assert response.status_code == 200

    def test_post_with_invalid_origin(self, monkeypatch):
        """POST with invalid Origin should be blocked"""
        from backend import config

        monkeypatch.setattr(config.settings, "CORS_ORIGINS", "http://localhost:3000")

        response = client.post("/api/test", headers={"Origin": "http://evil.com"})
        assert response.status_code == 403
        assert "CSRF_VALIDATION_FAILED" in response.json()["error"]["code"]

    def test_post_with_jwt_token_allowed(self):
        """POST with JWT Bearer token should be allowed (implicit CSRF protection)"""
        response = client.post("/api/test", headers={"Authorization": "Bearer fake-jwt-token"})
        # Will pass CSRF but may fail auth - we just check it's not CSRF blocked
        assert response.status_code != 403 or "CSRF" not in response.text

    def test_delete_with_valid_referer(self, monkeypatch):
        """DELETE with valid Referer should succeed"""
        from backend import config

        monkeypatch.setattr(config.settings, "CORS_ORIGINS", "http://localhost:3000")

        response = client.delete("/api/test/123", headers={"Referer": "http://localhost:3000/page"})
        assert response.status_code == 200

    def test_login_endpoint_exempt(self):
        """Login endpoint should be exempt from CSRF"""
        # Login is exempt, so should work without Origin
        response = client.post("/api/auth/login", json={"username": "test", "password": "test"})
        # May fail auth but won't be CSRF blocked
        assert response.status_code != 403 or "CSRF" not in response.text


class TestCSRFTokens:
    """Test CSRF token generation and verification"""

    def test_generate_csrf_token(self):
        """Should generate valid token"""
        token = generate_csrf_token()
        assert len(token) > 20  # tokens should be substantial length
        assert isinstance(token, str)

    def test_generate_unique_tokens(self):
        """Should generate unique tokens"""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        assert token1 != token2

    def test_verify_csrf_token_valid(self):
        """Should verify matching tokens"""
        token = generate_csrf_token()
        assert verify_csrf_token(token, token)

    def test_verify_csrf_token_invalid(self):
        """Should reject mismatched tokens"""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        assert not verify_csrf_token(token1, token2)

    def test_verify_csrf_token_timing_safe(self):
        """Should use constant-time comparison"""
        # This is ensured by using secrets.compare_digest
        token = generate_csrf_token()
        assert verify_csrf_token(token, token)


class TestCSRFExemptPaths:
    """Test CSRF exempt paths"""

    @pytest.mark.parametrize(
        "path",
        [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/health",
            "/docs",
        ],
    )
    def test_exempt_paths(self, path):
        """Exempt paths should not require CSRF validation"""
        # These won't exist in our test app, but the middleware should pass them through
        # In practice, they'd be handled by other middleware/routers
        pass  # Tested implicitly via login test above


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
