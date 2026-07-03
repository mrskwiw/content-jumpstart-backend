"""Unit tests for backend.utils.query_profiler."""

import pytest
from backend.utils.query_profiler import (
    _normalize_query,
    _hash_query,
    record_query,
    get_query_statistics,
    get_slow_queries,
    reset_statistics,
    _query_stats,
    _slow_queries,
    SLOW_QUERY_THRESHOLD_MS,
    VERY_SLOW_QUERY_THRESHOLD_MS,
)


@pytest.fixture(autouse=True)
def clean_stats():
    """Reset global profiler state before and after each test."""
    reset_statistics()
    yield
    reset_statistics()


class TestNormalizeQuery:
    def test_collapses_whitespace(self):
        result = _normalize_query("SELECT  *  FROM   users")
        assert "  " not in result

    def test_replaces_numeric_literals(self):
        result = _normalize_query("WHERE id = 42")
        assert "42" not in result
        assert "?" in result

    def test_replaces_string_literals(self):
        result = _normalize_query("WHERE name = 'Alice'")
        assert "Alice" not in result

    def test_strips_leading_trailing_whitespace(self):
        result = _normalize_query("  SELECT 1  ")
        assert result == result.strip()


class TestHashQuery:
    def test_same_query_same_hash(self):
        q = "SELECT * FROM users WHERE id = 1"
        assert _hash_query(q) == _hash_query(q)

    def test_different_values_same_hash(self):
        # Two queries with different IDs should hash the same (params replaced)
        h1 = _hash_query("SELECT * FROM users WHERE id = 1")
        h2 = _hash_query("SELECT * FROM users WHERE id = 999")
        assert h1 == h2

    def test_different_tables_different_hash(self):
        assert _hash_query("SELECT * FROM users") != _hash_query("SELECT * FROM projects")

    def test_returns_string(self):
        assert isinstance(_hash_query("SELECT 1"), str)


class TestRecordQuery:
    def test_records_fast_query(self):
        record_query("SELECT 1", duration_ms=5.0)
        stats = get_query_statistics()
        assert len(stats) == 1
        assert stats[0].execution_count == 1

    def test_accumulates_multiple_calls(self):
        record_query("SELECT * FROM users", duration_ms=10.0)
        record_query("SELECT * FROM users", duration_ms=20.0)
        stats = get_query_statistics()
        assert stats[0].execution_count == 2
        assert stats[0].total_time_ms == pytest.approx(30.0)

    def test_records_slow_query_flag(self):
        record_query("SELECT * FROM huge", duration_ms=SLOW_QUERY_THRESHOLD_MS + 1)
        slow = get_slow_queries()
        assert len(slow) == 1

    def test_does_not_record_fast_as_slow(self):
        record_query("SELECT 1", duration_ms=5.0)
        assert len(get_slow_queries()) == 0

    def test_records_very_slow_flag(self):
        record_query("SELECT * FROM big", duration_ms=VERY_SLOW_QUERY_THRESHOLD_MS + 1)
        slow = get_slow_queries()
        assert slow[0]["is_very_slow"] is True

    def test_accepts_optional_params_and_endpoint(self):
        record_query(
            "SELECT * FROM users WHERE id = :id",
            duration_ms=5.0,
            params={"id": 1},
            endpoint="/api/users/1",
        )
        stats = get_query_statistics()
        assert len(stats) == 1


class TestGetQueryStatistics:
    def test_empty_returns_empty(self):
        assert get_query_statistics() == []

    def test_sorted_by_total_time_desc(self):
        record_query("fast_query", duration_ms=10.0)
        record_query("slow_query", duration_ms=500.0)
        stats = get_query_statistics()
        assert stats[0].total_time_ms >= stats[1].total_time_ms

    def test_filter_by_min_execution_count(self):
        record_query("once", duration_ms=10.0)
        for _ in range(3):
            record_query("many_times", duration_ms=10.0)
        stats = get_query_statistics(min_execution_count=2)
        assert all(s.execution_count >= 2 for s in stats)

    def test_filter_only_slow(self):
        record_query("fast", duration_ms=5.0)
        record_query("slow", duration_ms=SLOW_QUERY_THRESHOLD_MS + 1)
        stats = get_query_statistics(only_slow=True)
        assert all(s.slow_count > 0 for s in stats)


class TestGetSlowQueries:
    def test_empty_when_no_slow_queries(self):
        record_query("fast", duration_ms=5.0)
        assert get_slow_queries() == []

    def test_returns_slow_queries(self):
        record_query("slow1", duration_ms=SLOW_QUERY_THRESHOLD_MS + 10)
        record_query("slow2", duration_ms=SLOW_QUERY_THRESHOLD_MS + 20)
        slow = get_slow_queries()
        assert len(slow) == 2


class TestResetStatistics:
    def test_clears_all(self):
        record_query("q", duration_ms=200.0)
        reset_statistics()
        assert get_query_statistics() == []
        assert get_slow_queries() == []
