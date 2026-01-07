"""
Unit tests for query profiling utility (Week 3).

Tests cover:
- Query recording and normalization
- Slow query detection
- Statistics aggregation
- Profiling reports
- N+1 detection
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from backend.utils.query_profiler import (
    record_query,
    get_query_statistics,
    get_slow_queries,
    get_profiling_report,
    reset_statistics,
    _normalize_query,
    _hash_query,
    QueryProfile,
    QueryStatistics,
    SLOW_QUERY_THRESHOLD_MS,
    VERY_SLOW_QUERY_THRESHOLD_MS,
    _query_stats,
    _slow_queries,
)


@pytest.fixture(autouse=True)
def reset_profiler():
    """Reset profiler state before each test."""
    reset_statistics()
    yield
    reset_statistics()


class TestQueryNormalization:
    """Test query normalization for grouping"""

    def test_normalize_basic_query(self):
        """Test normalization of basic SELECT query"""
        query = "SELECT * FROM projects WHERE id = 123"
        normalized = _normalize_query(query)

        # Numbers should be replaced with ?
        assert "123" not in normalized
        assert "?" in normalized

    def test_normalize_removes_whitespace_variations(self):
        """Test that extra whitespace is normalized"""
        query1 = "SELECT  *  FROM   projects"
        query2 = "SELECT * FROM projects"

        normalized1 = _normalize_query(query1)
        normalized2 = _normalize_query(query2)

        assert normalized1 == normalized2

    def test_normalize_replaces_numeric_literals(self):
        """Test that numeric literals are replaced"""
        query = "SELECT * FROM projects WHERE id = 456 AND status = 1"
        normalized = _normalize_query(query)

        assert "456" not in normalized
        assert "1" not in normalized
        # Should have ? in place of numbers
        assert normalized.count("?") >= 2

    def test_normalize_replaces_string_literals(self):
        """Test that string literals are replaced"""
        query = "SELECT * FROM projects WHERE name = 'Test Project' AND status = 'active'"
        normalized = _normalize_query(query)

        assert "Test Project" not in normalized
        assert "active" not in normalized
        # Strings should be replaced with ?
        assert "?" in normalized

    def test_normalize_groups_similar_queries(self):
        """Test that similar queries normalize to same pattern"""
        query1 = "SELECT * FROM projects WHERE id = 123"
        query2 = "SELECT * FROM projects WHERE id = 456"
        query3 = "SELECT * FROM projects WHERE id = 789"

        norm1 = _normalize_query(query1)
        norm2 = _normalize_query(query2)
        norm3 = _normalize_query(query3)

        # All should normalize to same pattern
        assert norm1 == norm2 == norm3

    def test_normalize_distinguishes_different_queries(self):
        """Test that different query structures remain different"""
        query1 = "SELECT * FROM projects WHERE id = 123"
        query2 = "SELECT * FROM posts WHERE project_id = 123"

        norm1 = _normalize_query(query1)
        norm2 = _normalize_query(query2)

        # Different table names should produce different normalized queries
        assert norm1 != norm2


class TestQueryHashing:
    """Test query hash generation"""

    def test_hash_query_consistency(self):
        """Test that same query produces same hash"""
        query = "SELECT * FROM projects WHERE id = 123"

        hash1 = _hash_query(query)
        hash2 = _hash_query(query)

        assert hash1 == hash2

    def test_hash_query_groups_similar(self):
        """Test that similar queries produce same hash"""
        query1 = "SELECT * FROM projects WHERE id = 123"
        query2 = "SELECT * FROM projects WHERE id = 456"

        hash1 = _hash_query(query1)
        hash2 = _hash_query(query2)

        # Should produce same hash (normalized to same pattern)
        assert hash1 == hash2

    def test_hash_query_length(self):
        """Test that hash is truncated to 12 characters"""
        query = "SELECT * FROM projects"
        hash_value = _hash_query(query)

        assert len(hash_value) == 12


class TestQueryRecording:
    """Test query execution recording"""

    def test_record_query_basic(self):
        """Test recording a basic query"""
        query = "SELECT * FROM projects WHERE id = 123"
        duration = 50.0

        record_query(query, duration)

        # Verify query was recorded
        query_hash = _hash_query(query)
        assert query_hash in _query_stats
        assert _query_stats[query_hash]["count"] == 1
        assert _query_stats[query_hash]["total_time_ms"] == 50.0

    def test_record_query_aggregates_stats(self):
        """Test that repeated queries aggregate statistics"""
        query = "SELECT * FROM projects WHERE id = ?"

        record_query("SELECT * FROM projects WHERE id = 123", 50.0)
        record_query("SELECT * FROM projects WHERE id = 456", 75.0)
        record_query("SELECT * FROM projects WHERE id = 789", 100.0)

        query_hash = _hash_query(query)
        stats = _query_stats[query_hash]

        assert stats["count"] == 3
        assert stats["total_time_ms"] == 225.0
        assert stats["min_time_ms"] == 50.0
        assert stats["max_time_ms"] == 100.0

    def test_record_query_tracks_slow_queries(self):
        """Test that slow queries are flagged"""
        query = "SELECT * FROM projects WHERE id = 123"

        # Record slow query (>= SLOW_QUERY_THRESHOLD_MS)
        record_query(query, SLOW_QUERY_THRESHOLD_MS + 10)

        query_hash = _hash_query(query)
        stats = _query_stats[query_hash]

        assert stats["slow_count"] == 1
        assert len(_slow_queries) == 1

    def test_record_query_tracks_very_slow_queries(self):
        """Test that very slow queries are flagged"""
        query = "SELECT * FROM projects WHERE id = 123"

        # Record very slow query (>= VERY_SLOW_QUERY_THRESHOLD_MS)
        record_query(query, VERY_SLOW_QUERY_THRESHOLD_MS + 10)

        query_hash = _hash_query(query)
        stats = _query_stats[query_hash]

        assert stats["slow_count"] == 1
        assert stats["very_slow_count"] == 1
        assert _slow_queries[0]["is_very_slow"] is True

    def test_record_query_with_params(self):
        """Test recording query with parameters"""
        query = "SELECT * FROM projects WHERE id = ?"
        params = {"id": 123}

        record_query(query, 50.0, params=params)

        query_hash = _hash_query(query)
        stats = _query_stats[query_hash]

        # Verify sample includes params
        assert len(stats["samples"]) == 1
        assert stats["samples"][0].params == params

    def test_record_query_with_endpoint(self):
        """Test recording query with API endpoint"""
        query = "SELECT * FROM projects"
        endpoint = "/api/projects"

        record_query(query, 50.0, endpoint=endpoint)

        query_hash = _hash_query(query)
        stats = _query_stats[query_hash]

        assert stats["samples"][0].endpoint == endpoint

    def test_record_query_limits_samples(self):
        """Test that sample list is limited to 5"""
        query = "SELECT * FROM projects WHERE id = ?"

        # Record 10 queries
        for i in range(10):
            record_query(f"SELECT * FROM projects WHERE id = {i}", 50.0)

        query_hash = _hash_query(query)
        stats = _query_stats[query_hash]

        # Should only keep last 5 samples
        assert len(stats["samples"]) == 5

    def test_record_query_slow_queries_circular_buffer(self):
        """Test that slow queries list is limited"""
        from utils.query_profiler import MAX_SLOW_QUERIES

        # Record more than MAX_SLOW_QUERIES slow queries
        for i in range(MAX_SLOW_QUERIES + 10):
            record_query(f"SELECT * FROM table{i}", SLOW_QUERY_THRESHOLD_MS + 10)

        # Should be limited to MAX_SLOW_QUERIES
        assert len(_slow_queries) == MAX_SLOW_QUERIES


class TestQueryStatistics:
    """Test query statistics retrieval"""

    def test_get_query_statistics_basic(self):
        """Test getting basic query statistics"""
        query = "SELECT * FROM projects WHERE id = ?"

        record_query("SELECT * FROM projects WHERE id = 123", 50.0)
        record_query("SELECT * FROM projects WHERE id = 456", 75.0)

        stats = get_query_statistics()

        assert len(stats) == 1
        assert stats[0].execution_count == 2
        assert stats[0].total_time_ms == 125.0
        assert stats[0].avg_time_ms == 62.5
        assert stats[0].min_time_ms == 50.0
        assert stats[0].max_time_ms == 75.0

    def test_get_query_statistics_filters_by_execution_count(self):
        """Test filtering by minimum execution count"""
        record_query("SELECT * FROM projects WHERE id = 1", 50.0)
        record_query("SELECT * FROM posts WHERE id = 2", 50.0)
        record_query("SELECT * FROM posts WHERE id = 3", 50.0)

        # Only posts query should be returned (2 executions)
        stats = get_query_statistics(min_execution_count=2)

        assert len(stats) == 1
        assert "posts" in stats[0].query_sample

    def test_get_query_statistics_filters_by_avg_time(self):
        """Test filtering by minimum average time"""
        record_query("SELECT * FROM fast WHERE id = 1", 10.0)
        record_query("SELECT * FROM slow WHERE id = 2", 100.0)

        stats = get_query_statistics(min_avg_time_ms=50.0)

        assert len(stats) == 1
        assert "slow" in stats[0].query_sample

    def test_get_query_statistics_only_slow(self):
        """Test filtering to only slow queries"""
        record_query("SELECT * FROM fast WHERE id = 1", 50.0)
        record_query("SELECT * FROM slow WHERE id = 2", SLOW_QUERY_THRESHOLD_MS + 10)

        stats = get_query_statistics(only_slow=True)

        assert len(stats) == 1
        assert stats[0].slow_count == 1

    def test_get_query_statistics_sorted_by_total_time(self):
        """Test that results are sorted by total time"""
        # Record queries with different total times
        for i in range(5):
            record_query(f"SELECT * FROM table{i} WHERE id = 1", 10.0 * (i + 1))
            record_query(f"SELECT * FROM table{i} WHERE id = 2", 10.0 * (i + 1))

        stats = get_query_statistics()

        # Should be sorted by total_time_ms descending
        for i in range(len(stats) - 1):
            assert stats[i].total_time_ms >= stats[i + 1].total_time_ms

    def test_get_query_statistics_includes_recent_samples(self):
        """Test that statistics include recent samples"""
        for i in range(10):
            record_query(f"SELECT * FROM projects WHERE id = {i}", 50.0)

        stats = get_query_statistics()

        # Should include last 3 samples
        assert len(stats[0].recent_samples) == 3


class TestSlowQueries:
    """Test slow query retrieval"""

    def test_get_slow_queries_basic(self):
        """Test getting slow queries"""
        record_query("SELECT * FROM slow1", SLOW_QUERY_THRESHOLD_MS + 10)
        record_query("SELECT * FROM slow2", SLOW_QUERY_THRESHOLD_MS + 20)

        slow = get_slow_queries()

        assert len(slow) == 2

    def test_get_slow_queries_limit(self):
        """Test limiting number of results"""
        for i in range(100):
            record_query(f"SELECT * FROM table{i}", SLOW_QUERY_THRESHOLD_MS + 10)

        slow = get_slow_queries(limit=10)

        assert len(slow) == 10

    def test_get_slow_queries_since_timestamp(self):
        """Test filtering by timestamp"""
        past = datetime.utcnow() - timedelta(hours=2)
        recent = datetime.utcnow() - timedelta(minutes=5)

        with patch('utils.query_profiler.datetime') as mock_datetime:
            # Record old query
            mock_datetime.utcnow.return_value = past
            record_query("SELECT * FROM old", SLOW_QUERY_THRESHOLD_MS + 10)

            # Record recent query
            mock_datetime.utcnow.return_value = recent
            record_query("SELECT * FROM recent", SLOW_QUERY_THRESHOLD_MS + 10)

        # Get queries since 1 hour ago
        since = datetime.utcnow() - timedelta(hours=1)
        slow = get_slow_queries(since=since)

        # Should only include recent query
        assert len(slow) == 1
        assert "recent" in slow[0]["query"]

    def test_get_slow_queries_very_slow_only(self):
        """Test filtering to only very slow queries"""
        record_query("SELECT * FROM slow", SLOW_QUERY_THRESHOLD_MS + 10)
        record_query("SELECT * FROM very_slow", VERY_SLOW_QUERY_THRESHOLD_MS + 10)

        slow = get_slow_queries(very_slow_only=True)

        assert len(slow) == 1
        assert slow[0]["is_very_slow"] is True

    def test_get_slow_queries_sorted_by_timestamp(self):
        """Test that results are sorted by timestamp"""
        with patch('utils.query_profiler.datetime') as mock_datetime:
            times = [
                datetime.utcnow() - timedelta(minutes=30),
                datetime.utcnow() - timedelta(minutes=20),
                datetime.utcnow() - timedelta(minutes=10),
            ]

            for i, time in enumerate(times):
                mock_datetime.utcnow.return_value = time
                record_query(f"SELECT * FROM table{i}", SLOW_QUERY_THRESHOLD_MS + 10)

        slow = get_slow_queries()

        # Should be sorted by timestamp descending (most recent first)
        assert slow[0]["timestamp"] > slow[1]["timestamp"]
        assert slow[1]["timestamp"] > slow[2]["timestamp"]


class TestProfilingReport:
    """Test profiling report generation"""

    def test_get_profiling_report_basic(self):
        """Test generating basic profiling report"""
        # Record some queries
        record_query("SELECT * FROM projects WHERE id = 1", 50.0)
        record_query("SELECT * FROM projects WHERE id = 2", 75.0)
        record_query("SELECT * FROM posts WHERE id = 1", 30.0)

        report = get_profiling_report()

        assert "summary" in report
        assert report["summary"]["total_queries"] == 3
        assert report["summary"]["total_time_ms"] == 155.0
        assert report["summary"]["unique_query_patterns"] == 2

    def test_get_profiling_report_slow_query_percentage(self):
        """Test slow query percentage calculation"""
        # Record mix of fast and slow queries
        for i in range(7):
            record_query(f"SELECT * FROM fast WHERE id = {i}", 50.0)
        for i in range(3):
            record_query(f"SELECT * FROM slow WHERE id = {i}", SLOW_QUERY_THRESHOLD_MS + 10)

        report = get_profiling_report()

        assert report["summary"]["total_queries"] == 10
        assert report["summary"]["slow_queries"] == 3
        assert report["summary"]["slow_percentage"] == 30.0

    def test_get_profiling_report_recommendations_high_slow_percentage(self):
        """Test recommendations for high slow query percentage"""
        # Record 15% slow queries
        for i in range(85):
            record_query(f"SELECT * FROM fast WHERE id = {i}", 50.0)
        for i in range(15):
            record_query(f"SELECT * FROM slow WHERE id = {i}", SLOW_QUERY_THRESHOLD_MS + 10)

        report = get_profiling_report()

        # Should have warning about slow queries
        recommendations = report["recommendations"]
        assert any("slow" in r["message"].lower() for r in recommendations)
        assert any(r["severity"] == "warning" for r in recommendations)

    def test_get_profiling_report_recommendations_very_slow(self):
        """Test critical recommendations for very slow queries"""
        # Record 2% very slow queries
        for i in range(98):
            record_query(f"SELECT * FROM fast WHERE id = {i}", 50.0)
        for i in range(2):
            record_query(f"SELECT * FROM very_slow WHERE id = {i}", VERY_SLOW_QUERY_THRESHOLD_MS + 10)

        report = get_profiling_report()

        # Should have critical warning
        recommendations = report["recommendations"]
        assert any(r["severity"] == "critical" for r in recommendations)

    def test_get_profiling_report_n_plus_1_detection(self):
        """Test detection of potential N+1 queries"""
        # Record high-frequency, low-latency query (N+1 pattern)
        for i in range(150):
            record_query(f"SELECT * FROM posts WHERE project_id = {i}", 5.0)

        report = get_profiling_report()

        # Should detect potential N+1
        recommendations = report["recommendations"]
        assert any("N+1" in r["message"] for r in recommendations)

    def test_get_profiling_report_top_slowest_queries(self):
        """Test top slowest queries in report"""
        # Record queries with different total times
        for i in range(15):
            for j in range(i + 1):
                record_query(f"SELECT * FROM table{i} WHERE id = {j}", 10.0)

        report = get_profiling_report()

        # Should include top 10 slowest
        top_slowest = report["top_slowest_queries"]
        assert len(top_slowest) == 10

        # Should be sorted by total_time_ms
        for i in range(len(top_slowest) - 1):
            assert top_slowest[i]["total_time_ms"] >= top_slowest[i + 1]["total_time_ms"]

    def test_get_profiling_report_recent_slow_queries(self):
        """Test recent slow queries in report"""
        for i in range(25):
            record_query(f"SELECT * FROM slow{i}", SLOW_QUERY_THRESHOLD_MS + 10)

        report = get_profiling_report()

        # Should include recent 20 slow queries
        recent_slow = report["recent_slow_queries"]
        assert len(recent_slow) == 20

    def test_get_profiling_report_truncates_long_queries(self):
        """Test that long queries are truncated in report"""
        long_query = "SELECT * FROM projects WHERE " + " AND ".join([f"col{i} = {i}" for i in range(100)])
        record_query(long_query, 50.0)

        report = get_profiling_report()

        query_sample = report["top_slowest_queries"][0]["query_sample"]
        # Should be truncated to 200 chars + "..."
        assert len(query_sample) <= 203
        if len(long_query) > 200:
            assert query_sample.endswith("...")


class TestStatisticsReset:
    """Test statistics reset"""

    def test_reset_statistics_clears_query_stats(self):
        """Test that reset clears query statistics"""
        record_query("SELECT * FROM projects", 50.0)
        record_query("SELECT * FROM posts", 50.0)

        assert len(_query_stats) > 0

        reset_statistics()

        assert len(_query_stats) == 0

    def test_reset_statistics_clears_slow_queries(self):
        """Test that reset clears slow queries"""
        record_query("SELECT * FROM slow", SLOW_QUERY_THRESHOLD_MS + 10)

        assert len(_slow_queries) > 0

        reset_statistics()

        assert len(_slow_queries) == 0


class TestQueryProfileModel:
    """Test QueryProfile dataclass"""

    def test_query_profile_creation(self):
        """Test creating QueryProfile instance"""
        profile = QueryProfile(
            query="SELECT * FROM projects",
            params={"id": 123},
            duration_ms=50.0,
            timestamp=datetime.utcnow(),
            endpoint="/api/projects",
            is_slow=False,
            is_very_slow=False
        )

        assert profile.query == "SELECT * FROM projects"
        assert profile.params == {"id": 123}
        assert profile.duration_ms == 50.0
        assert profile.is_slow is False


class TestQueryStatisticsModel:
    """Test QueryStatistics dataclass"""

    def test_query_statistics_creation(self):
        """Test creating QueryStatistics instance"""
        stats = QueryStatistics(
            query_hash="abc123def456",
            query_sample="SELECT * FROM projects WHERE id = ?",
            execution_count=10,
            total_time_ms=500.0,
            avg_time_ms=50.0,
            min_time_ms=30.0,
            max_time_ms=100.0,
            slow_count=2,
            very_slow_count=0
        )

        assert stats.query_hash == "abc123def456"
        assert stats.execution_count == 10
        assert stats.avg_time_ms == 50.0
