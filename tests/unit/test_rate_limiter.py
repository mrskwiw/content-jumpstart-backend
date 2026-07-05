"""Unit tests for backend.utils.rate_limiter (Anthropic API rate tracking)."""

import pytest
from datetime import datetime, timedelta

from backend.utils.rate_limiter import RateLimitTracker, QueuedRequest, rate_limiter


@pytest.fixture
def tracker():
    return RateLimitTracker()


class TestGetCurrentUsage:
    def test_empty_returns_zeros(self, tracker):
        usage = tracker._get_current_usage()
        assert usage["requests"] == 0
        assert usage["tokens"] == 0

    def test_cleanup_removes_old_entries(self, tracker):
        old_ts = datetime.now() - timedelta(minutes=2)
        tracker.requests_log.append((old_ts, 100))
        usage = tracker._get_current_usage()
        assert usage["requests"] == 0

    def test_recent_entries_kept(self, tracker):
        now = datetime.now()
        tracker.requests_log.append((now, 500))
        usage = tracker._get_current_usage()
        assert usage["requests"] == 1
        assert usage["tokens"] == 500

    def test_available_counts(self, tracker):
        usage = tracker._get_current_usage()
        assert usage["requests_available"] == tracker.request_limit
        assert usage["tokens_available"] == tracker.token_limit


class TestCanMakeRequest:
    @pytest.mark.asyncio
    async def test_allows_when_under_limit(self, tracker):
        assert await tracker.can_make_request(100) is True

    @pytest.mark.asyncio
    async def test_blocks_when_request_limit_reached(self, tracker):
        # Fill requests log to the limit
        now = datetime.now()
        for _ in range(tracker.request_limit):
            tracker.requests_log.append((now, 1))
        assert await tracker.can_make_request(100) is False

    @pytest.mark.asyncio
    async def test_blocks_when_token_limit_would_exceed(self, tracker):
        now = datetime.now()
        tracker.requests_log.append((now, tracker.token_limit - 50))
        # Requesting 100 more tokens would exceed limit
        assert await tracker.can_make_request(100) is False

    @pytest.mark.asyncio
    async def test_allows_when_just_under_token_limit(self, tracker):
        now = datetime.now()
        tracker.requests_log.append((now, tracker.token_limit - 500))
        assert await tracker.can_make_request(499) is True


class TestRecordRequest:
    @pytest.mark.asyncio
    async def test_records_to_log(self, tracker):
        await tracker.record_request(tokens_used=1000)
        assert len(tracker.requests_log) == 1
        _, tokens = tracker.requests_log[0]
        assert tokens == 1000

    @pytest.mark.asyncio
    async def test_multiple_records(self, tracker):
        await tracker.record_request(100)
        await tracker.record_request(200)
        assert len(tracker.requests_log) == 2


class TestQueue:
    @pytest.mark.asyncio
    async def test_add_to_queue(self, tracker):
        await tracker.add_to_queue("req-1", estimated_tokens=500)
        assert len(tracker.queue) == 1

    @pytest.mark.asyncio
    async def test_remove_from_queue(self, tracker):
        await tracker.add_to_queue("req-1", 500)
        await tracker.remove_from_queue("req-1")
        assert len(tracker.queue) == 0

    @pytest.mark.asyncio
    async def test_get_queue_position(self, tracker):
        await tracker.add_to_queue("req-1", 500)
        await tracker.add_to_queue("req-2", 500)
        assert await tracker.get_queue_position("req-1") == 0
        assert await tracker.get_queue_position("req-2") == 1

    @pytest.mark.asyncio
    async def test_not_in_queue_returns_minus_one(self, tracker):
        assert await tracker.get_queue_position("no-such") == -1

    @pytest.mark.asyncio
    async def test_priority_ordering(self, tracker):
        await tracker.add_to_queue("low", 100, priority=0)
        await tracker.add_to_queue("high", 100, priority=10)
        # High priority should be first
        assert tracker.queue[0].id == "high"

    @pytest.mark.asyncio
    async def test_remove_nonexistent_is_safe(self, tracker):
        await tracker.remove_from_queue("no-such")  # should not raise


class TestGetEstimatedWaitTime:
    @pytest.mark.asyncio
    async def test_not_in_queue_returns_none(self, tracker):
        result = await tracker.get_estimated_wait_time("no-such")
        assert result is None

    @pytest.mark.asyncio
    async def test_queued_returns_estimate(self, tracker):
        await tracker.add_to_queue("req-1", 500)
        wait = await tracker.get_estimated_wait_time("req-1")
        assert wait is not None
        assert isinstance(wait, int)
        assert wait >= 0


class TestGetUsageStats:
    def test_returns_stats_dict(self, tracker):
        stats = tracker.get_usage_stats()
        assert "requests" in stats
        assert "tokens" in stats
        assert "queue_length" in stats
        assert "requests_utilization" in stats
        assert "tokens_utilization" in stats

    def test_empty_utilization_is_zero(self, tracker):
        stats = tracker.get_usage_stats()
        assert stats["requests_utilization"] == 0.0
        assert stats["tokens_utilization"] == 0.0


def test_singleton_import():
    assert isinstance(rate_limiter, RateLimitTracker)
