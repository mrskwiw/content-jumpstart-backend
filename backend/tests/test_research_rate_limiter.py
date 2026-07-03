import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 20)

import backend.utils.research_rate_limiter as rrl_mod


class _FakePipeline:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def incr(self, key):
        self.redis_client.store[key] = int(self.redis_client.store.get(key, 0)) + 1
        return self

    def expire(self, key, ttl):
        self.redis_client.ttls[key] = ttl
        return self

    def execute(self):
        return None


class _FakeRedis:
    def __init__(self, store=None):
        self.store = store or {}
        self.ttls = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def pipeline(self):
        return _FakePipeline(self)

    def ttl(self, key):
        return self.ttls.get(key, 120)


def _patch_redis_success(monkeypatch, redis_client):
    class _RedisFactory:
        @staticmethod
        def from_url(*args, **kwargs):
            return redis_client

    monkeypatch.setattr(rrl_mod, "redis", SimpleNamespace(Redis=_RedisFactory))


def _patch_redis_failure(monkeypatch):
    class _BrokenRedisFactory:
        @staticmethod
        def from_url(*args, **kwargs):
            raise RuntimeError("redis down")

    monkeypatch.setattr(rrl_mod, "redis", SimpleNamespace(Redis=_BrokenRedisFactory))


def test_research_rate_limiter_redis_success_and_limits(monkeypatch):
    redis_client = _FakeRedis()
    _patch_redis_success(monkeypatch, redis_client)
    monkeypatch.setattr(rrl_mod.settings, "DEBUG_MODE", False)

    limiter = rrl_mod.ResearchRateLimiter()
    user = SimpleNamespace(id=7, email="user@example.com")

    usage = limiter.check_and_increment(user, "keyword-research", cost_credits=3)
    assert limiter.use_redis is True
    assert usage["hourly"]["current"] == 1
    assert usage["hourly"]["limit"] == 20
    assert limiter.get_usage_stats(user.id) == {"hourly": 1, "daily": 1, "monthly": 1}

    hourly_key = limiter._get_key(user.id, "hourly")
    redis_client.store[hourly_key] = 20
    redis_client.ttls[hourly_key] = 99

    with pytest.raises(HTTPException) as exc_info:
        limiter.check_and_increment(user, "keyword-research")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["error"] == "RESEARCH_RATE_LIMIT_EXCEEDED"
    assert exc_info.value.detail["window"] == "hour"
    assert exc_info.value.detail["current_usage"] == 20
    assert "reset_at" in exc_info.value.detail


def test_research_rate_limiter_memory_fallback(monkeypatch):
    _patch_redis_failure(monkeypatch)
    monkeypatch.setattr(rrl_mod.settings, "DEBUG_MODE", False)

    limiter = rrl_mod.ResearchRateLimiter()
    user = SimpleNamespace(id=11, email="user@example.com")

    usage = limiter.check_and_increment(user, "trend-analysis")
    assert limiter.use_redis is False
    assert usage["daily"]["current"] == 1
    assert limiter.get_usage_stats(user.id) == {"hourly": 1, "daily": 1, "monthly": 1}

    hourly_key = limiter._get_key(user.id, "hourly")
    limiter.memory_store[hourly_key] = 20

    with pytest.raises(HTTPException) as exc_info:
        limiter.check_and_increment(user, "trend-analysis")

    assert exc_info.value.status_code == 429
    assert "calls per hour" in exc_info.value.detail


def test_research_rate_limiter_debug_limits(monkeypatch):
    redis_client = _FakeRedis()
    _patch_redis_success(monkeypatch, redis_client)
    monkeypatch.setattr(rrl_mod.settings, "DEBUG_MODE", True)

    limiter = rrl_mod.ResearchRateLimiter()
    user = SimpleNamespace(id=3, email="debug@example.com")

    usage = limiter.check_and_increment(user, "debug-tool")
    assert usage["hourly"]["limit"] == 1000
    assert usage["daily"]["limit"] == 1000
    assert usage["monthly"]["limit"] == 1000
