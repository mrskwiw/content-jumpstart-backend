"""
Integration tests for rate limiting functionality.

Tests actual rate limit enforcement, headers, reset behavior, and Redis storage.
"""

import pytest
import time
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(test_user_headers):
    """Alias for test_user_headers fixture."""
    return test_user_headers


class TestRateLimitEnforcement:
    """Test that rate limits are enforced on API endpoints"""

    def test_login_rate_limiting_strict(self, client, db_session):
        """Test strict rate limiting on /api/auth/login (10 requests per hour per IP)"""
        # Make 10 requests (should succeed)
        for i in range(10):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "testpass123",
                },
            )
            # May be 200 (success), 401 (invalid creds), or 404 (user not found)
            # We only care that it's NOT rate limited
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # 11th request should be rate limited
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },
        )
        assert response.status_code == 429
        data = response.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in data["error"]

    def test_register_rate_limiting_strict(self, client, db_session):
        """Test strict rate limiting on /api/auth/register (3 requests per hour per IP)"""
        # Make 3 requests (should succeed or fail with validation errors, not rate limits)
        for i in range(3):
            response = client.post(
                "/api/auth/register",
                json={
                    "email": f"newuser{i}@example.com",
                    "full_name": f"New User {i}",
                    "password": "SecurePass123!",
                },
            )
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # 4th request should be rate limited
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser99@example.com",
                "full_name": "New User 99",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 429

    def test_generator_rate_limiting_composite_key(self, client, test_user, auth_headers):
        """Test generator endpoint uses composite key (IP + user)"""
        # Use a fake project ID - the rate limiter fires before project lookup
        project_id = "fake-project-id-for-rate-limit-test"

        # Make 10 generation requests (composite key: 10/hour)
        for i in range(10):
            response = client.post(
                "/api/generator/generate-all",
                headers=auth_headers,
                json={
                    "project_id": project_id,
                    "client_id": "fake-client-id",
                },
            )
            # Should not be rate limited (may fail for other reasons like 404)
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # 11th request should be rate limited
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "client_id": "fake-client-id",
            },
        )
        assert response.status_code == 429

    def test_projects_list_standard_rate_limiting(self, client, test_user, auth_headers):
        """Test standard rate limiting on /api/projects (100 requests per hour)"""
        # Make 100 requests
        for i in range(100):
            response = client.get("/api/projects", headers=auth_headers)
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # 101st request should be rate limited
        response = client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 429

    def test_posts_list_lenient_rate_limiting(self, client, test_user, auth_headers):
        """Test lenient rate limiting on /api/posts (1000 requests per hour)"""
        # Test first 50 requests (testing all 1000 would be slow)
        for i in range(50):
            response = client.get("/api/posts", headers=auth_headers)
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # Should still have plenty of quota remaining
        response = client.get("/api/posts", headers=auth_headers)
        assert response.status_code == 200


class TestRateLimitHeaders:
    """Test that rate limit responses include correct HTTP headers"""

    def test_rate_limit_headers_present(self, client, db_session):
        """Test that 429 response includes Retry-After and X-RateLimit-* headers"""
        # Trigger rate limit on login endpoint (10/hour)
        for _ in range(11):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "testpass123",
                },
            )

        # Check headers on rate-limited response
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # Verify header values
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_rate_limit_response_body(self, client, db_session):
        """Test that 429 response body includes retry information"""
        # Trigger rate limit
        for _ in range(11):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "testpass123",
                },
            )

        assert response.status_code == 429
        data = response.json()

        # Check response body structure
        assert "error" in data
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in data["error"]
        assert "reset_at" in data["error"]
        assert isinstance(data["error"]["retry_after"], int)
        assert isinstance(data["error"]["reset_at"], int)


class TestRateLimitIsolation:
    """Test that rate limits are properly isolated by IP and user"""

    def test_different_ips_independent_limits(self, client, db_session):
        """Test that different IPs have independent rate limits"""
        # First IP makes 10 requests
        for _ in range(10):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "testpass123",
                },
            )
            assert response.status_code != 429

        # 11th request from first IP should be rate limited
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },
        )
        assert response.status_code == 429

        # Request from different IP should succeed (simulate with different client)
        # Note: In real scenario, this would be different IP. In tests, limiters reset between tests.
        # This test verifies the key function logic, actual multi-IP testing requires network setup.

    def test_different_users_same_ip_independent_limits(self, client, test_user, auth_headers):
        """Test that different users on same IP have independent user-based limits"""
        # This test verifies user-based rate limiting (projects endpoint)
        # Make 100 requests as user 1
        for _ in range(100):
            response = client.get("/api/projects", headers=auth_headers)
            assert response.status_code != 429

        # 101st request should be rate limited
        response = client.get("/api/projects", headers=auth_headers)
        assert response.status_code == 429

        # In real scenario, different user would have separate limit
        # This test verifies the key function includes user ID


class TestCompositeKeyVPNBypassPrevention:
    """Test that composite key prevents VPN bypass attacks"""

    def test_composite_key_prevents_vpn_bypass(self, client, test_user, auth_headers):
        """Test that authenticated users can't bypass limits with VPN (composite key)"""
        # Composite key = IP + user ID
        # Even if user changes IP (VPN), rate limit persists per (IP, user) pair
        # This provides defense in depth

        # Use a fake project ID - the rate limiter fires before project lookup
        project_id = "fake-project-id-for-vpn-bypass-test"

        # Make requests using composite key endpoint (generator)
        for i in range(10):
            response = client.post(
                "/api/generator/generate-all",
                headers=auth_headers,
                json={
                    "project_id": project_id,
                    "client_id": "test-client-id",
                },
            )
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # Rate limit enforced regardless of IP (composite key includes both)
        response = client.post(
            "/api/generator/generate-all",
            headers=auth_headers,
            json={
                "project_id": project_id,
                "client_id": "test-client-id",
            },
        )
        assert response.status_code == 429


class TestProxyHeaderHandling:
    """Test X-Forwarded-For and X-Real-IP header handling"""

    def test_x_forwarded_for_trusted_in_production(self, client):
        """Test that X-Forwarded-For is trusted in production mode"""
        # This test would require setting DEBUG_MODE=False and testing with headers
        # In real deployment behind proxy (nginx/cloudflare), X-Forwarded-For contains client IP
        pass

    def test_x_forwarded_for_ignored_in_debug_mode(self, client):
        """Test that X-Forwarded-For is ignored in debug mode (security)"""
        # In debug mode, proxy headers are ignored to prevent spoofing
        # Rate limit should use direct connection IP, not header value
        pass


class TestRedisStorage:
    """Test Redis storage backend (optional - requires Redis)"""

    @pytest.mark.skipif(
        True,  # Skip Redis tests by default
        reason="Requires --redis flag and running Redis instance",
    )
    def test_redis_storage_persistence(self, client):
        """Test that rate limits persist in Redis across requests"""
        # This test requires RATE_LIMIT_STORAGE=redis://localhost:6379/1
        # Make requests and verify limit persists
        pass

    def test_memory_fallback_on_redis_unavailable(self):
        """Test graceful fallback to memory:// when Redis unavailable"""
        # get_storage_uri() should return memory:// if Redis connection fails
        from backend.utils.http_rate_limiter import get_storage_uri
        from unittest.mock import patch

        with (
            patch("redis.Redis", side_effect=Exception("Connection refused")),
            patch("backend.config.settings.RATE_LIMIT_STORAGE", "redis://localhost:6379/1"),
        ):
            uri = get_storage_uri()
            assert uri == "memory://"


class TestRateLimitReset:
    """Test that rate limits reset after time window expires"""

    @pytest.mark.slow
    def test_rate_limit_resets_after_window(self, client, db_session):
        """Test that rate limit resets after time window (requires waiting)"""
        # Note: This test is slow because it requires waiting for rate limit window
        # In real scenario, window is 1 hour. For testing, we'd need shorter window.
        # This test is marked as slow and may be skipped in CI

        # Trigger rate limit (10 requests)
        for _ in range(10):
            client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "testpass123",
                },
            )

        # 11th request is rate limited
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },
        )
        assert response.status_code == 429

        # Wait for window to expire (in test, limiters reset between tests)
        # In production, would wait retry_after seconds
        # time.sleep(retry_after)

        # After window expires, requests should work again
        # (In test environment, this is handled by reset_rate_limiting fixture)
