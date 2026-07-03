"""Unit tests for backend.utils.cache (InMemoryCache + decorator)."""

import asyncio
import pytest
import time

from backend.utils.cache import (
    CacheEntry,
    InMemoryCache,
    get_cache,
    cache_key,
    cached,
)


class TestCacheEntry:
    def test_not_expired_immediately(self):
        entry = CacheEntry("value", ttl=60)
        assert entry.is_expired() is False

    def test_zero_ttl_never_expires(self):
        entry = CacheEntry("value", ttl=0)
        entry.created_at = time.time() - 9999
        assert entry.is_expired() is False

    def test_expired_when_past_ttl(self):
        entry = CacheEntry("value", ttl=1)
        entry.created_at = time.time() - 2  # 2 seconds ago, TTL is 1
        assert entry.is_expired() is True


class TestInMemoryCache:
    @pytest.fixture
    def cache(self):
        return InMemoryCache(max_size=10, default_ttl=60)

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        await cache.set("k1", "v1")
        assert await cache.get("k1") == "v1"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, cache):
        assert await cache.get("does-not-exist") is None

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, cache):
        await cache.set("k2", "v2")
        await cache.delete("k2")
        assert await cache.get("k2") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_safe(self, cache):
        await cache.delete("no-such-key")  # should not raise

    @pytest.mark.asyncio
    async def test_clear_removes_all(self, cache):
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.clear()
        assert await cache.get("a") is None
        assert await cache.get("b") is None

    @pytest.mark.asyncio
    async def test_custom_ttl(self, cache):
        await cache.set("short", "val", ttl=1)
        assert await cache.get("short") == "val"
        # Manually expire
        cache._cache["short"].created_at = time.time() - 2
        assert await cache.get("short") is None

    @pytest.mark.asyncio
    async def test_lru_eviction_at_max_size(self):
        c = InMemoryCache(max_size=3, default_ttl=60)
        await c.set("a", 1)
        await c.set("b", 2)
        await c.set("c", 3)
        await c.set("d", 4)  # should evict "a" (oldest)
        assert await c.get("a") is None
        assert await c.get("d") == 4

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache):
        await cache.set("project:123:data", "v1")
        await cache.set("project:123:posts", "v2")
        await cache.set("client:456:data", "v3")
        await cache.invalidate_pattern("project:123:*")
        assert await cache.get("project:123:data") is None
        assert await cache.get("project:123:posts") is None
        assert await cache.get("client:456:data") == "v3"

    @pytest.mark.asyncio
    async def test_stats_hit_rate(self, cache):
        await cache.set("k", "v")
        await cache.get("k")  # hit
        await cache.get("k")  # hit
        await cache.get("missing")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(66.67, abs=0.1)

    @pytest.mark.asyncio
    async def test_stats_empty_cache(self, cache):
        stats = cache.get_stats()
        assert stats["size"] == 0
        assert stats["hit_rate"] == 0

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self, cache):
        await cache.set("k", "v1")
        await cache.set("k", "v2")
        assert await cache.get("k") == "v2"


class TestGetCache:
    def test_returns_singleton(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_returns_inmemory_cache(self):
        assert isinstance(get_cache(), InMemoryCache)


class TestCacheKey:
    def test_deterministic(self):
        k1 = cache_key("a", "b", x=1)
        k2 = cache_key("a", "b", x=1)
        assert k1 == k2

    def test_different_args_different_keys(self):
        assert cache_key("a") != cache_key("b")

    def test_different_kwargs_different_keys(self):
        assert cache_key(x=1) != cache_key(x=2)

    def test_returns_string(self):
        assert isinstance(cache_key("test"), str)


class TestCachedDecorator:
    @pytest.mark.asyncio
    async def test_caches_result(self):
        call_count = 0

        @cached(ttl=60)
        async def expensive(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert await expensive(5) == 10
        assert await expensive(5) == 10
        assert call_count == 1  # second call used cache

    @pytest.mark.asyncio
    async def test_different_args_not_shared(self):
        @cached(ttl=60)
        async def double(x):
            return x * 2

        assert await double(3) == 6
        assert await double(7) == 14

    @pytest.mark.asyncio
    async def test_key_prefix_used(self):
        @cached(ttl=60, key_prefix="myprefix")
        async def fn(x):
            return x

        result = await fn(42)
        assert result == 42
