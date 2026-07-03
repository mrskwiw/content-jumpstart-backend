"""
Integration tests for proxy header security.

Tests X-Forwarded-For and X-Real-IP handling, spoofing prevention,
and production vs development mode behavior.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestProxyHeadersSecurity:
    """Test security of proxy header handling"""

    def test_proxy_headers_trusted_in_production_mode(self, client):
        """Test that X-Forwarded-For is trusted when DEBUG_MODE=False"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        # Simulate production mode
        with patch("backend.config.settings.DEBUG_MODE", False):
            request = Mock(spec=Request)
            request.headers = {"X-Forwarded-For": "198.51.100.50"}

            ip = get_real_ip(request)
            assert ip == "198.51.100.50"

    def test_proxy_headers_ignored_in_debug_mode(self, client):
        """Test that X-Forwarded-For is ignored when DEBUG_MODE=True"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        # Simulate debug mode
        with (
            patch("backend.config.settings.DEBUG_MODE", True),
            patch("backend.utils.http_rate_limiter.get_remote_address", return_value="127.0.0.1"),
        ):
            request = Mock(spec=Request)
            request.headers = {"X-Forwarded-For": "198.51.100.50"}  # Should be ignored

            ip = get_real_ip(request)
            assert ip == "127.0.0.1"  # Uses direct IP, not header

    def test_x_real_ip_fallback(self, client):
        """Test X-Real-IP header fallback when X-Forwarded-For not present"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        with patch("backend.config.settings.DEBUG_MODE", False):
            request = Mock(spec=Request)
            request.headers = {"X-Real-IP": "198.51.100.75"}

            ip = get_real_ip(request)
            assert ip == "198.51.100.75"

    def test_proxy_chain_extracts_first_ip(self, client):
        """Test that first IP in X-Forwarded-For chain is used (client IP)"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        with patch("backend.config.settings.DEBUG_MODE", False):
            request = Mock(spec=Request)
            # Client -> Proxy1 -> Proxy2 -> Server
            request.headers = {"X-Forwarded-For": "198.51.100.50, 203.0.113.1, 203.0.113.2"}

            ip = get_real_ip(request)
            assert ip == "198.51.100.50"  # First IP = client


class TestHeaderSpoofingPrevention:
    """Test prevention of IP spoofing via proxy headers"""

    def test_spoofed_headers_rejected_in_debug_mode(self, client, db_session):
        """Test that spoofed X-Forwarded-For headers are rejected in debug mode"""
        # In development (DEBUG_MODE=True), proxy headers should be ignored
        # This prevents attackers from bypassing rate limits by setting fake headers

        # Attempt to spoof IP via header
        headers_with_spoofed_ip = {
            "X-Forwarded-For": "1.2.3.4",  # Attacker claims to be from this IP
            "X-Real-IP": "5.6.7.8",
        }

        # Make requests with spoofed headers
        for _ in range(11):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "testpass123"},
                headers=headers_with_spoofed_ip,
            )

        # Should be rate limited based on real IP, not spoofed header
        assert response.status_code == 429

    def test_rate_limiting_uses_real_ip_not_spoofed(self, client, db_session):
        """Test that rate limiting uses real IP, not spoofed header in debug mode"""
        # Make 10 requests with different spoofed IPs
        for i in range(10):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "testpass123"},
                headers={"X-Forwarded-For": f"1.2.3.{i}"},  # Different IP each time
            )
            # Should not be rate limited yet (real IP is the same)
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # 11th request should be rate limited (based on real IP, not headers)
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
            headers={"X-Forwarded-For": "1.2.3.99"},
        )
        assert response.status_code == 429


class TestInvalidIPFormats:
    """Test handling of invalid/malformed IP addresses"""

    def test_malformed_x_forwarded_for_gracefully_handled(self, client):
        """Test that malformed X-Forwarded-For doesn't crash"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        with (
            patch("backend.config.settings.DEBUG_MODE", False),
            patch("backend.utils.http_rate_limiter.get_remote_address", return_value="127.0.0.1"),
        ):
            request = Mock(spec=Request)
            request.headers = {"X-Forwarded-For": "invalid-ip-format"}

            # Should not crash, extracts first element
            ip = get_real_ip(request)
            assert ip == "invalid-ip-format"  # Returns as-is, validation happens elsewhere

    def test_empty_x_forwarded_for_falls_back(self, client):
        """Test that empty X-Forwarded-For falls back to direct IP"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        with (
            patch("backend.config.settings.DEBUG_MODE", False),
            patch("backend.utils.http_rate_limiter.get_remote_address", return_value="127.0.0.1"),
        ):
            request = Mock(spec=Request)
            request.headers = {"X-Forwarded-For": ""}

            ip = get_real_ip(request)
            # Empty header should fall back to X-Real-IP or direct IP
            assert ip == "127.0.0.1"

    def test_whitespace_only_x_forwarded_for(self, client):
        """Test that whitespace-only X-Forwarded-For is handled"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        with (
            patch("backend.config.settings.DEBUG_MODE", False),
            patch("backend.utils.http_rate_limiter.get_remote_address", return_value="127.0.0.1"),
        ):
            request = Mock(spec=Request)
            request.headers = {"X-Forwarded-For": "   "}

            ip = get_real_ip(request)
            assert ip.strip() == "" or ip == "127.0.0.1"  # Either stripped empty or fallback


class TestRateLimitBypassAttempts:
    """Test that rate limit bypass attempts are prevented"""

    def test_cannot_bypass_with_changing_x_forwarded_for(self, client, db_session):
        """Test that changing X-Forwarded-For doesn't bypass rate limits in debug mode"""
        # Attacker tries to bypass by changing X-Forwarded-For on each request
        for i in range(11):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "testpass123"},
                headers={"X-Forwarded-For": f"10.0.0.{i}"},  # Different IP each time
            )

            if i < 10:
                # First 10 requests succeed (not rate limited)
                assert response.status_code != 429, f"Request {i+1} was prematurely rate limited"
            else:
                # 11th request is rate limited (header ignored in debug mode)
                assert response.status_code == 429, "Rate limit bypass succeeded (security issue!)"

    def test_cannot_bypass_with_multiple_headers(self, client, db_session):
        """Test that setting multiple proxy headers doesn't bypass limits"""
        # Attacker tries to confuse parser with multiple headers
        headers = {
            "X-Forwarded-For": "10.0.0.1",
            "X-Real-IP": "10.0.0.2",
            "Forwarded": "for=10.0.0.3",
            "X-Originating-IP": "10.0.0.4",
        }

        for i in range(11):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "testpass123"},
                headers=headers,
            )

        # Should still be rate limited
        assert response.status_code == 429


class TestProductionVsDebugMode:
    """Test differences between production and debug mode behavior"""

    def test_production_mode_trusts_proxy(self):
        """Test that production mode trusts X-Forwarded-For"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        with patch("backend.config.settings.DEBUG_MODE", False):
            request = Mock(spec=Request)
            request.headers = {"X-Forwarded-For": "203.0.113.50"}

            ip = get_real_ip(request)
            assert ip == "203.0.113.50"  # Trusts header

    def test_debug_mode_ignores_proxy(self):
        """Test that debug mode ignores X-Forwarded-For"""
        from backend.utils.http_rate_limiter import get_real_ip
        from fastapi import Request
        from unittest.mock import Mock

        with (
            patch("backend.config.settings.DEBUG_MODE", True),
            patch("backend.utils.http_rate_limiter.get_remote_address", return_value="127.0.0.1"),
        ):
            request = Mock(spec=Request)
            request.headers = {"X-Forwarded-For": "203.0.113.50"}

            ip = get_real_ip(request)
            assert ip == "127.0.0.1"  # Ignores header, uses direct IP

    def test_security_rationale_documented(self):
        """Test that security rationale is documented in code"""
        from backend.utils.http_rate_limiter import get_real_ip
        import inspect

        # Check that function docstring mentions security rationale
        docstring = inspect.getdoc(get_real_ip)
        assert "Security" in docstring or "production" in docstring.lower()
        assert "DEBUG_MODE" in docstring or "development" in docstring.lower()
