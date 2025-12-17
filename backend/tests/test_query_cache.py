"""
Unit tests for query caching utility (Week 3).

Tests cover:
- Cache decorator functionality
- Cache hit/miss tracking
- Cache invalidation
- Cache statistics
- TTL tiers
"""
import pytest
import time
from unittest.mock import Mock, patch
from utils.query_cache import (
    cached,
    cache_short,
    cache_medium,
    cache_long,
    clear_cache,
    invalidate_related_caches,
    get_cache_info,
    reset_cache_stats,
    _make_cache_key,
    _caches,
    _cache_stats,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before each test."""
    for cache in _caches.values():
        cache.clear()
    reset_cache_stats()
    yield
    # Cleanup after test
    for cache in _caches.values():
        cache.clear()
    reset_cache_stats()


class TestCacheDecorator:
    """Test @cached decorator functionality"""

    def test_cache_basic_functionality(self):
        """Test basic cache hit and miss"""
        call_count = 0

        @cached(ttl="short")
        def get_data(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - cache miss
        result1 = get_data(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - cache hit
        result2 = get_data(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again

        # Different argument - cache miss
        result3 = get_data(10)
        assert result3 == 20
        assert call_count == 2

    def test_cache_with_kwargs(self):
        """Test caching with keyword arguments"""
        call_count = 0

        @cached(ttl="short")
        def get_data(x: int, multiply_by: int = 2) -> int:
            nonlocal call_count
            call_count += 1
            return x * multiply_by

        # First call
        result1 = get_data(5, multiply_by=3)
        assert result1 == 15
        assert call_count == 1

        # Same call - cache hit
        result2 = get_data(5, multiply_by=3)
        assert result2 == 15
        assert call_count == 1

        # Different kwargs - cache miss
        result3 = get_data(5, multiply_by=4)
        assert result3 == 20
        assert call_count == 2

    def test_cache_filters_db_session(self):
        """Test that db session is filtered from cache key"""
        call_count = 0
        mock_db = Mock()

        @cached(ttl="short")
        def get_data(db, user_id: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"User {user_id}"

        # First call with db session
        result1 = get_data(mock_db, user_id=123)
        assert result1 == "User 123"
        assert call_count == 1

        # Second call with different db session - should still hit cache
        mock_db2 = Mock()
        result2 = get_data(mock_db2, user_id=123)
        assert result2 == "User 123"
        assert call_count == 1  # Cache hit despite different db object

    def test_cache_with_key_prefix(self):
        """Test cache namespacing with key_prefix"""
        call_count = 0

        @cached(ttl="short", key_prefix="projects")
        def get_data(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result = get_data(5)
        assert result == 10
        assert call_count == 1

        # Verify cache key includes prefix
        cache = _caches["short"]
        keys = list(cache.keys())
        assert len(keys) == 1
        assert keys[0].startswith("projects:")

    def test_cache_statistics_tracking(self):
        """Test that cache hits/misses are tracked"""
        @cached(ttl="short")
        def get_data(x: int) -> int:
            return x * 2

        # Initial stats should be zero
        stats = _cache_stats["short"]
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["sets"] == 0

        # First call - miss
        get_data(5)
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["hits"] == 0

        # Second call - hit
        get_data(5)
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["hits"] == 1


class TestCacheTiers:
    """Test different cache TTL tiers"""

    def test_short_cache_tier(self):
        """Test short TTL cache (5 minutes)"""
        @cache_short()
        def get_data(x: int) -> int:
            return x * 2

        result = get_data(5)
        assert result == 10

        # Verify stored in short cache
        assert len(_caches["short"]) == 1
        assert len(_caches["medium"]) == 0
        assert len(_caches["long"]) == 0

    def test_medium_cache_tier(self):
        """Test medium TTL cache (10 minutes)"""
        @cache_medium()
        def get_data(x: int) -> int:
            return x * 2

        result = get_data(5)
        assert result == 10

        # Verify stored in medium cache
        assert len(_caches["short"]) == 0
        assert len(_caches["medium"]) == 1
        assert len(_caches["long"]) == 0

    def test_long_cache_tier(self):
        """Test long TTL cache (1 hour)"""
        @cache_long()
        def get_data(x: int) -> int:
            return x * 2

        result = get_data(5)
        assert result == 10

        # Verify stored in long cache
        assert len(_caches["short"]) == 0
        assert len(_caches["medium"]) == 0
        assert len(_caches["long"]) == 1

    def test_invalid_tier_defaults_to_short(self):
        """Test that invalid tier defaults to short"""
        @cached(ttl="invalid")
        def get_data(x: int) -> int:
            return x * 2

        result = get_data(5)
        assert result == 10

        # Should use short cache
        assert len(_caches["short"]) == 1


class TestCacheClearing:
    """Test cache invalidation"""

    def test_clear_all_caches(self):
        """Test clearing all cache tiers"""
        # Populate all caches
        @cache_short()
        def get_short(x: int) -> int:
            return x

        @cache_medium()
        def get_medium(x: int) -> int:
            return x

        @cache_long()
        def get_long(x: int) -> int:
            return x

        get_short(1)
        get_medium(2)
        get_long(3)

        # Verify all populated
        assert len(_caches["short"]) == 1
        assert len(_caches["medium"]) == 1
        assert len(_caches["long"]) == 1

        # Clear all
        clear_cache()

        # Verify all cleared
        assert len(_caches["short"]) == 0
        assert len(_caches["medium"]) == 0
        assert len(_caches["long"]) == 0

    def test_clear_specific_tier(self):
        """Test clearing specific cache tier"""
        @cache_short()
        def get_short(x: int) -> int:
            return x

        @cache_medium()
        def get_medium(x: int) -> int:
            return x

        get_short(1)
        get_medium(2)

        # Clear only short
        clear_cache(ttl="short")

        assert len(_caches["short"]) == 0
        assert len(_caches["medium"]) == 1

    def test_clear_with_key_prefix(self):
        """Test selective clearing by key prefix"""
        @cached(ttl="short", key_prefix="projects")
        def get_projects(x: int) -> int:
            return x

        @cached(ttl="short", key_prefix="posts")
        def get_posts(x: int) -> int:
            return x

        get_projects(1)
        get_posts(2)

        # Both should be cached
        assert len(_caches["short"]) == 2

        # Clear only projects
        clear_cache(ttl="short", key_prefix="projects")

        # Only projects should be cleared
        assert len(_caches["short"]) == 1

        # Verify posts still cached
        keys = list(_caches["short"].keys())
        assert keys[0].startswith("posts:")

    def test_invalidate_related_caches(self):
        """Test invalidating multiple related cache namespaces"""
        @cached(ttl="short", key_prefix="projects")
        def get_projects(x: int) -> int:
            return x

        @cached(ttl="medium", key_prefix="clients")
        def get_clients(x: int) -> int:
            return x

        @cached(ttl="short", key_prefix="posts")
        def get_posts(x: int) -> int:
            return x

        get_projects(1)
        get_clients(2)
        get_posts(3)

        # Invalidate projects and clients
        invalidate_related_caches("projects", "clients")

        # Projects and clients should be cleared
        assert len(_caches["short"]) == 1  # posts remains
        assert len(_caches["medium"]) == 0  # clients cleared

    def test_cache_clear_updates_statistics(self):
        """Test that cache clearing updates invalidation stats"""
        @cache_short(key_prefix="test")
        def get_data(x: int) -> int:
            return x

        get_data(1)
        get_data(2)

        # Clear cache
        clear_cache(ttl="short", key_prefix="test")

        # Verify invalidation count
        stats = _cache_stats["short"]
        assert stats["invalidations"] == 2


class TestCacheStatistics:
    """Test cache statistics and info"""

    def test_get_cache_info_single_tier(self):
        """Test getting stats for single cache tier"""
        @cache_short()
        def get_data(x: int) -> int:
            return x * 2

        # Generate some cache activity
        get_data(1)  # miss
        get_data(1)  # hit
        get_data(2)  # miss

        info = get_cache_info(ttl="short")

        assert info["tier"] == "short"
        assert info["size"] == 2  # 2 unique entries
        assert info["hits"] == 1
        assert info["misses"] == 2
        assert info["sets"] == 2
        assert info["hit_rate_percent"] == 33.33  # 1/3 = 33.33%

    def test_get_cache_info_all_tiers(self):
        """Test getting stats for all cache tiers"""
        @cache_short()
        def get_short(x: int) -> int:
            return x

        @cache_medium()
        def get_medium(x: int) -> int:
            return x

        get_short(1)
        get_medium(2)

        info = get_cache_info()

        assert "short" in info
        assert "medium" in info
        assert "long" in info
        assert info["short"]["size"] == 1
        assert info["medium"]["size"] == 1
        assert info["long"]["size"] == 0

    def test_get_cache_info_invalid_tier(self):
        """Test getting info for invalid tier"""
        info = get_cache_info(ttl="invalid")

        assert "error" in info
        assert "Unknown cache tier" in info["error"]

    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation"""
        @cache_short()
        def get_data(x: int) -> int:
            return x

        # 2 misses, 8 hits = 80% hit rate
        get_data(1)  # miss
        get_data(2)  # miss
        for _ in range(4):
            get_data(1)  # hit
            get_data(2)  # hit

        info = get_cache_info(ttl="short")
        assert info["hits"] == 8
        assert info["misses"] == 2
        assert info["hit_rate_percent"] == 80.0

    def test_zero_requests_hit_rate(self):
        """Test hit rate when no requests made"""
        info = get_cache_info(ttl="short")

        assert info["hits"] == 0
        assert info["misses"] == 0
        assert info["hit_rate_percent"] == 0.0

    def test_reset_cache_stats(self):
        """Test resetting cache statistics"""
        @cache_short()
        def get_data(x: int) -> int:
            return x

        # Generate activity
        get_data(1)
        get_data(1)

        # Verify stats exist
        stats = _cache_stats["short"]
        assert stats["hits"] > 0 or stats["misses"] > 0

        # Reset
        reset_cache_stats()

        # Verify all zeroed
        for tier_stats in _cache_stats.values():
            assert tier_stats["hits"] == 0
            assert tier_stats["misses"] == 0
            assert tier_stats["sets"] == 0
            assert tier_stats["invalidations"] == 0


class TestCacheKeyGeneration:
    """Test cache key generation"""

    def test_make_cache_key_basic(self):
        """Test basic cache key generation"""
        key1 = _make_cache_key("test_func", (1, 2), {})
        key2 = _make_cache_key("test_func", (1, 2), {})

        # Same inputs should generate same key
        assert key1 == key2
        assert key1.startswith("test_func:")

    def test_make_cache_key_different_args(self):
        """Test that different args generate different keys"""
        key1 = _make_cache_key("test_func", (1, 2), {})
        key2 = _make_cache_key("test_func", (3, 4), {})

        assert key1 != key2

    def test_make_cache_key_filters_db_session(self):
        """Test that db/session/engine are filtered from key"""
        mock_db = Mock()

        key1 = _make_cache_key("test_func", (), {"db": mock_db, "user_id": 123})
        key2 = _make_cache_key("test_func", (), {"db": Mock(), "user_id": 123})

        # Different db objects should generate same key
        assert key1 == key2

    def test_make_cache_key_kwargs_order(self):
        """Test that kwargs order doesn't affect key"""
        key1 = _make_cache_key("test_func", (), {"a": 1, "b": 2})
        key2 = _make_cache_key("test_func", (), {"b": 2, "a": 1})

        # Same kwargs in different order should generate same key
        assert key1 == key2


class TestCacheWrapperMethods:
    """Test wrapper methods added to cached functions"""

    def test_cache_clear_method(self):
        """Test wrapper.cache_clear() method"""
        call_count = 0

        @cache_short(key_prefix="test")
        def get_data(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # Populate cache
        get_data(1)
        get_data(2)
        assert call_count == 2

        # Clear via wrapper method
        get_data.cache_clear()

        # Should be cache miss now
        get_data(1)
        assert call_count == 3

    def test_cache_info_method(self):
        """Test wrapper.cache_info() method"""
        @cache_short()
        def get_data(x: int) -> int:
            return x * 2

        get_data(1)

        # Get info via wrapper method
        info = get_data.cache_info()

        assert info["tier"] == "short"
        assert info["size"] >= 1
