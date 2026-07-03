"""Unit tests for backend.utils.research_rate_limiter (in-memory path)."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from backend.utils.research_rate_limiter import ResearchRateLimiter


def _make_user(id="user-1", email="test@example.com"):
    u = MagicMock()
    u.id = id
    u.email = email
    return u


@pytest.fixture
def limiter():
    """ResearchRateLimiter wired to in-memory storage (no Redis required)."""
    with patch("redis.Redis.from_url") as mock_redis:
        # Make Redis.ping() raise so the limiter falls back to in-memory
        mock_redis.return_value.ping.side_effect = ConnectionError("no redis")
        lim = ResearchRateLimiter()
    assert not lim.use_redis
    lim.memory_store.clear()
    return lim


class TestGetKey:
    def test_key_format(self):
        lim = ResearchRateLimiter.__new__(ResearchRateLimiter)
        key = lim._get_key("user-42", "hourly")
        assert "user-42" in key
        assert "hourly" in key
        assert key.startswith("research_limit:")


class TestCheckAndIncrementInMemory:
    def test_first_call_succeeds(self, limiter):
        user = _make_user()
        result = limiter.check_and_increment(user, "seo_keyword_research")
        assert "hourly" in result
        assert result["hourly"]["current"] == 1

    def test_increments_on_repeated_calls(self, limiter):
        user = _make_user()
        limiter.check_and_increment(user, "tool_a")
        result = limiter.check_and_increment(user, "tool_a")
        assert result["hourly"]["current"] == 2

    def test_different_users_isolated(self, limiter):
        ua = _make_user("user-a")
        ub = _make_user("user-b")
        limiter.check_and_increment(ua, "tool_x")
        result = limiter.check_and_increment(ub, "tool_x")
        assert result["hourly"]["current"] == 1  # user-b's first call

    def test_raises_429_when_hourly_limit_exceeded(self, limiter):
        from backend.config import settings

        user = _make_user()
        hourly_key = limiter._get_key(user.id, "hourly")

        # Patch debug mode off so production limits (20) apply
        with patch.object(settings, "DEBUG_MODE", False):
            limiter.memory_store[hourly_key] = 20  # at production limit
            with pytest.raises(HTTPException) as exc_info:
                limiter.check_and_increment(user, "expensive_tool")
        assert exc_info.value.status_code == 429

    def test_production_mode_has_lower_limits(self, limiter):
        from backend.config import settings

        user = _make_user()
        # Debug mode limit is 1000; production limit is 20
        # Verify that patching to False gives limit 20
        hourly_key = limiter._get_key(user.id, "hourly")
        limiter.memory_store[hourly_key] = 19  # one below production limit

        with patch.object(settings, "DEBUG_MODE", False):
            result = limiter.check_and_increment(user, "tool")
        # Should succeed at count 19 → 20 (production limit not yet exceeded)
        assert result["hourly"]["current"] == 20
        assert result["hourly"]["limit"] == 20

    def test_returns_remaining_count(self, limiter):
        user = _make_user()
        result = limiter.check_and_increment(user, "tool")
        assert "remaining" in result["hourly"]
        assert result["hourly"]["remaining"] >= 0


class TestGetUsageStats:
    def test_empty_stats_all_zero(self, limiter):
        stats = limiter.get_usage_stats("user-empty")
        assert stats["hourly"] == 0
        assert stats["daily"] == 0
        assert stats["monthly"] == 0

    def test_reflects_increments(self, limiter):
        user = _make_user("user-stats")
        limiter.check_and_increment(user, "tool")
        limiter.check_and_increment(user, "tool")
        stats = limiter.get_usage_stats("user-stats")
        assert stats["hourly"] == 2
        assert stats["daily"] == 2

    def test_different_windows_tracked_separately(self, limiter):
        user = _make_user("user-windows")
        # Manually set different values per window
        for w in ["hourly", "daily", "monthly"]:
            limiter.memory_store[limiter._get_key("user-windows", w)] = 5
        stats = limiter.get_usage_stats("user-windows")
        assert all(stats[w] == 5 for w in ["hourly", "daily", "monthly"])
