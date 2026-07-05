"""
Unit tests for HTTP rate limiter utility functions.

Tests IP detection, composite key generation, and Redis storage fallback.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request


@pytest.fixture
def mock_request():
    """Create mock FastAPI Request"""
    request = Mock(spec=Request)
    request.headers = {}
    request.state = Mock()
    request.state.user = None
    return request


@pytest.fixture
def mock_authenticated_request(mock_request):
    """Create mock authenticated FastAPI Request"""
    mock_request.state.user = Mock(id=123)
    return mock_request


class TestGetRealIP:
    """Test get_real_ip() function with various proxy scenarios"""

    def test_direct_connection_no_proxy_headers(self, mock_request):
        """Test IP detection with no proxy headers (direct connection)"""
        from backend.utils.http_rate_limiter import get_real_ip

        with patch(
            "backend.utils.http_rate_limiter.get_remote_address", return_value="203.0.113.42"
        ):
            ip = get_real_ip(mock_request)
            assert ip == "203.0.113.42"

    def test_x_forwarded_for_single_proxy_production(self, mock_request):
        """Test X-Forwarded-For with single proxy in production mode"""
        from backend.utils.http_rate_limiter import get_real_ip

        mock_request.headers = {"X-Forwarded-For": "198.51.100.50"}

        with patch("backend.config.settings.DEBUG_MODE", False):
            ip = get_real_ip(mock_request)
            assert ip == "198.51.100.50"

    def test_x_forwarded_for_proxy_chain_production(self, mock_request):
        """Test X-Forwarded-For with proxy chain (takes first IP)"""
        from backend.utils.http_rate_limiter import get_real_ip

        # First IP is client, rest are proxies
        mock_request.headers = {"X-Forwarded-For": "198.51.100.50, 203.0.113.1, 203.0.113.2"}

        with patch("backend.config.settings.DEBUG_MODE", False):
            ip = get_real_ip(mock_request)
            assert ip == "198.51.100.50"

    def test_x_real_ip_fallback_production(self, mock_request):
        """Test X-Real-IP fallback when X-Forwarded-For not present"""
        from backend.utils.http_rate_limiter import get_real_ip

        mock_request.headers = {"X-Real-IP": "198.51.100.75"}

        with patch("backend.config.settings.DEBUG_MODE", False):
            ip = get_real_ip(mock_request)
            assert ip == "198.51.100.75"

    def test_x_forwarded_for_ignored_in_debug_mode(self, mock_request):
        """Test that proxy headers are ignored in debug mode (security)"""
        from backend.utils.http_rate_limiter import get_real_ip

        mock_request.headers = {"X-Forwarded-For": "198.51.100.50", "X-Real-IP": "198.51.100.75"}

        with (
            patch("backend.config.settings.DEBUG_MODE", True),
            patch("backend.utils.http_rate_limiter.get_remote_address", return_value="127.0.0.1"),
        ):
            ip = get_real_ip(mock_request)
            assert ip == "127.0.0.1"  # Uses direct IP, not headers

    def test_whitespace_trimming(self, mock_request):
        """Test that IPs are properly trimmed"""
        from backend.utils.http_rate_limiter import get_real_ip

        mock_request.headers = {"X-Forwarded-For": "  198.51.100.50  "}

        with patch("backend.config.settings.DEBUG_MODE", False):
            ip = get_real_ip(mock_request)
            assert ip == "198.51.100.50"


class TestGetUserIdOrIP:
    """Test get_user_id_or_ip() function"""

    def test_authenticated_user_returns_user_id(self, mock_authenticated_request):
        """Test that authenticated user returns user ID"""
        from backend.utils.http_rate_limiter import get_user_id_or_ip

        key = get_user_id_or_ip(mock_authenticated_request)
        assert key == "user:123"

    def test_anonymous_user_returns_ip(self, mock_request):
        """Test that anonymous user returns IP address"""
        from backend.utils.http_rate_limiter import get_user_id_or_ip

        with patch("backend.utils.http_rate_limiter.get_real_ip", return_value="203.0.113.42"):
            key = get_user_id_or_ip(mock_request)
            assert key == "203.0.113.42"

    def test_no_user_attribute_returns_ip(self, mock_request):
        """Test that missing user attribute returns IP"""
        from backend.utils.http_rate_limiter import get_user_id_or_ip

        del mock_request.state.user  # Remove user attribute

        with patch("backend.utils.http_rate_limiter.get_real_ip", return_value="203.0.113.42"):
            key = get_user_id_or_ip(mock_request)
            assert key == "203.0.113.42"


class TestGetCompositeKey:
    """Test get_composite_key() function (IP + user)"""

    def test_authenticated_user_returns_ip_plus_user(self, mock_authenticated_request):
        """Test composite key for authenticated user"""
        from backend.utils.http_rate_limiter import get_composite_key

        with patch("backend.utils.http_rate_limiter.get_real_ip", return_value="203.0.113.42"):
            key = get_composite_key(mock_authenticated_request)
            assert key == "203.0.113.42:user-123"

    def test_anonymous_user_returns_ip_plus_anonymous(self, mock_request):
        """Test composite key for anonymous user"""
        from backend.utils.http_rate_limiter import get_composite_key

        with patch("backend.utils.http_rate_limiter.get_real_ip", return_value="203.0.113.42"):
            key = get_composite_key(mock_request)
            assert key == "203.0.113.42:anonymous"

    def test_no_user_attribute_returns_ip_plus_anonymous(self, mock_request):
        """Test composite key when user attribute missing"""
        from backend.utils.http_rate_limiter import get_composite_key

        del mock_request.state.user

        with patch("backend.utils.http_rate_limiter.get_real_ip", return_value="203.0.113.42"):
            key = get_composite_key(mock_request)
            assert key == "203.0.113.42:anonymous"


class TestGetStorageURI:
    """Test get_storage_uri() function with Redis fallback"""

    def test_memory_storage_default(self):
        """Test that memory:// is used by default"""
        from backend.utils.http_rate_limiter import get_storage_uri

        with patch("backend.config.settings.RATE_LIMIT_STORAGE", "memory://"):
            uri = get_storage_uri()
            assert uri == "memory://"

    def test_redis_available_returns_redis_uri(self):
        """Test that Redis URI is returned when Redis is available"""
        from backend.utils.http_rate_limiter import get_storage_uri

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with (
            patch("backend.config.settings.RATE_LIMIT_STORAGE", "redis://localhost:6379/1"),
            patch("redis.Redis", return_value=mock_redis),
        ):
            uri = get_storage_uri()
            assert uri == "redis://localhost:6379/1"
            mock_redis.ping.assert_called_once()
            mock_redis.close.assert_called_once()

    def test_redis_unavailable_falls_back_to_memory(self):
        """Test fallback to memory:// when Redis unavailable"""
        from backend.utils.http_rate_limiter import get_storage_uri

        with (
            patch("backend.config.settings.RATE_LIMIT_STORAGE", "redis://localhost:6379/1"),
            patch("redis.Redis", side_effect=Exception("Connection refused")),
        ):
            uri = get_storage_uri()
            assert uri == "memory://"

    def test_redis_custom_host_port_db(self):
        """Test Redis with custom host, port, and database"""
        from backend.utils.http_rate_limiter import get_storage_uri

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with (
            patch("backend.config.settings.RATE_LIMIT_STORAGE", "redis://192.168.1.100:6380/5"),
            patch("redis.Redis", return_value=mock_redis) as mock_redis_cls,
        ):
            uri = get_storage_uri()
            assert uri == "redis://192.168.1.100:6380/5"

            # Verify correct connection parameters
            mock_redis_cls.assert_called_once_with(
                host="192.168.1.100", port=6380, db=5, socket_connect_timeout=1
            )

    def test_redis_default_port_and_db(self):
        """Test Redis URI parsing with default port and db"""
        from backend.utils.http_rate_limiter import get_storage_uri

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with (
            patch("backend.config.settings.RATE_LIMIT_STORAGE", "redis://localhost"),
            patch("redis.Redis", return_value=mock_redis) as mock_redis_cls,
        ):
            uri = get_storage_uri()
            assert uri == "redis://localhost"

            # Should use defaults (6379, db 0)
            mock_redis_cls.assert_called_once_with(
                host="localhost", port=6379, db=0, socket_connect_timeout=1
            )


class TestLimiterCreation:
    """Test that limiter instances are created with correct configuration"""

    def test_limiter_uses_storage_uri(self):
        """Test that all limiters use the storage URI from get_storage_uri()"""
        from backend.utils.http_rate_limiter import _storage_uri

        # Verify storage URI was set during module import
        assert _storage_uri in ["memory://", "redis://localhost:6379/1"]
