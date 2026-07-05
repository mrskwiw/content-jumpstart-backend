"""
Unit tests for backend cache and rate-limiting utilities.
"""

from types import SimpleNamespace
from unittest.mock import Mock
import sys
from types import ModuleType

import pytest

from backend.utils import cache as cache_module
from backend.utils.cache import CacheEntry, InMemoryCache, cache_key, cached, get_cache
from backend.utils.http_rate_limiter import (
    get_composite_key,
    get_real_ip,
    get_storage_uri,
    get_user_id_or_ip,
    rate_limit_exceeded_handler,
)
from backend.utils.research_rate_limiter import ResearchRateLimiter


@pytest.fixture(autouse=True)
def reset_global_cache():
    cache_module._cache = None
    yield
    cache_module._cache = None


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_set_get_delete_and_stats(self):
        cache = InMemoryCache(max_size=2, default_ttl=60)

        await cache.set("a", 1)
        await cache.set("b", 2)

        assert await cache.get("a") == 1
        assert await cache.get("missing") is None

        await cache.delete("a")
        assert await cache.get("a") is None

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] >= 1
        assert stats["misses"] >= 2

    @pytest.mark.asyncio
    async def test_expired_entry_is_removed(self, monkeypatch):
        cache = InMemoryCache(max_size=2, default_ttl=1)
        entry = CacheEntry("value", ttl=1)
        entry.created_at = 0
        cache._cache["expired"] = entry

        monkeypatch.setattr(cache_module.time, "time", lambda: 100)

        assert await cache.get("expired") is None
        assert "expired" not in cache._cache

    @pytest.mark.asyncio
    async def test_lru_and_pattern_invalidation(self):
        cache = InMemoryCache(max_size=2, default_ttl=60)

        await cache.set("first", 1)
        await cache.set("second", 2)
        await cache.set("third", 3)

        assert "first" not in cache._cache
        assert "second" in cache._cache
        assert "third" in cache._cache

        await cache.invalidate_pattern("th*")
        assert "third" not in cache._cache

    @pytest.mark.asyncio
    async def test_clear(self):
        cache = InMemoryCache(max_size=2, default_ttl=60)
        await cache.set("a", 1)
        await cache.clear()
        assert len(cache._cache) == 0


class TestCacheHelpers:
    def test_cache_key_is_stable(self):
        assert cache_key(1, "x", foo="bar") == cache_key(1, "x", foo="bar")
        assert cache_key(1, "x", foo="bar") != cache_key(2, "x", foo="bar")

    def test_global_cache_singleton(self):
        first = get_cache()
        second = get_cache()
        assert first is second

    @pytest.mark.asyncio
    async def test_cached_decorator_caches_async_results(self):
        calls = 0

        @cached(ttl=30, key_prefix="demo")
        async def double(value: int) -> int:
            nonlocal calls
            calls += 1
            return value * 2

        assert await double(3) == 6
        assert await double(3) == 6
        assert calls == 1


class TestRateLimiterHelpers:
    def test_get_real_ip_uses_remote_address_in_debug(self, monkeypatch):
        from backend.utils import http_rate_limiter

        monkeypatch.setattr(http_rate_limiter.settings, "DEBUG_MODE", True, raising=False)
        monkeypatch.setattr(http_rate_limiter, "get_remote_address", lambda request: "127.0.0.1")

        request = SimpleNamespace(headers={})
        assert get_real_ip(request) == "127.0.0.1"

    def test_get_real_ip_uses_forwarded_headers_in_prod(self, monkeypatch):
        from backend.utils import http_rate_limiter

        monkeypatch.setattr(http_rate_limiter.settings, "DEBUG_MODE", False, raising=False)
        monkeypatch.setattr(http_rate_limiter, "get_remote_address", lambda request: "127.0.0.1")

        request = SimpleNamespace(headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
        assert get_real_ip(request) == "1.2.3.4"

        request = SimpleNamespace(headers={"X-Real-IP": "9.9.9.9"})
        assert get_real_ip(request) == "9.9.9.9"

    def test_get_storage_uri_memory_fallback(self, monkeypatch):
        from backend.utils import http_rate_limiter

        monkeypatch.setattr(
            http_rate_limiter.settings, "RATE_LIMIT_STORAGE", "memory://", raising=False
        )
        assert get_storage_uri() == "memory://"

    def test_get_storage_uri_redis_success_and_failure(self, monkeypatch):
        from backend.utils import http_rate_limiter

        class FakeRedis:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def ping(self):
                return None

            def close(self):
                return None

        fake_module = ModuleType("redis")
        fake_module.Redis = FakeRedis
        monkeypatch.setitem(sys.modules, "redis", fake_module)
        monkeypatch.setattr(
            http_rate_limiter.settings,
            "RATE_LIMIT_STORAGE",
            "redis://localhost:6379/1",
            raising=False,
        )
        assert get_storage_uri() == "redis://localhost:6379/1"

        class BrokenRedis(FakeRedis):
            def ping(self):
                raise RuntimeError("redis down")

        fake_module.Redis = BrokenRedis
        assert get_storage_uri() == "memory://"

    def test_get_user_and_composite_keys(self, monkeypatch):
        from backend.utils import http_rate_limiter

        monkeypatch.setattr(http_rate_limiter.settings, "DEBUG_MODE", False, raising=False)
        monkeypatch.setattr(http_rate_limiter, "get_remote_address", lambda request: "10.0.0.1")
        user = SimpleNamespace(id=7)
        request = SimpleNamespace(headers={}, state=SimpleNamespace(user=user))

        assert get_user_id_or_ip(request) == "user:7"
        assert get_composite_key(request) == "10.0.0.1:user-7"

        anonymous = SimpleNamespace(headers={}, state=SimpleNamespace())
        assert get_user_id_or_ip(anonymous) == "10.0.0.1"
        assert get_composite_key(anonymous) == "10.0.0.1:anonymous"

    def test_rate_limit_handler_sets_retry_headers(self):
        request = SimpleNamespace()
        exc = SimpleNamespace(detail="10 per 1 hour")

        response = rate_limit_exceeded_handler(request, exc)

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "3600"
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_rate_limit_handler_minute_second_and_exception_fallback(self, monkeypatch):
        request = SimpleNamespace()
        minute = rate_limit_exceeded_handler(request, SimpleNamespace(detail="10 per 1 minute"))
        second = rate_limit_exceeded_handler(request, SimpleNamespace(detail="10 per 1 second"))

        class BrokenExc:
            @property
            def detail(self):
                raise RuntimeError("broken")

        broken = rate_limit_exceeded_handler(request, BrokenExc())

        assert minute.headers["Retry-After"] == "60"
        assert second.headers["Retry-After"] == "1"
        assert broken.status_code == 429


class TestResearchRateLimiter:
    def test_memory_fallback_check_and_increment(self, monkeypatch):
        from backend.utils import research_rate_limiter as rrl_module

        class FailingRedis:
            def ping(self):
                raise RuntimeError("redis down")

        monkeypatch.setattr(
            rrl_module.redis, "Redis", Mock(from_url=lambda *args, **kwargs: FailingRedis())
        )
        limiter = ResearchRateLimiter()
        limiter.use_redis = False
        limiter.memory_store = {}

        user = SimpleNamespace(id=3, email="user@example.com")
        usage = limiter.check_and_increment(user, "tool-a")

        assert usage["hourly"]["current"] == 1
        assert limiter.get_usage_stats(3)["daily"] == 1

    def test_memory_limit_exceeded(self, monkeypatch):
        from backend.utils import research_rate_limiter as rrl_module

        class FailingRedis:
            def ping(self):
                raise RuntimeError("redis down")

        monkeypatch.setattr(
            rrl_module.redis, "Redis", Mock(from_url=lambda *args, **kwargs: FailingRedis())
        )
        limiter = ResearchRateLimiter()
        limiter.use_redis = False
        limiter.memory_store = {
            "research_limit:user:3:hourly": 1000,
            "research_limit:user:3:daily": 1000,
            "research_limit:user:3:monthly": 1000,
        }

        user = SimpleNamespace(id=3, email="user@example.com")
        with pytest.raises(Exception):
            limiter.check_and_increment(user, "tool-a")
