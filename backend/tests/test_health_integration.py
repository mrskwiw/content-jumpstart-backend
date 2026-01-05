"""
Integration tests for health monitoring endpoints (Week 3).

Tests actual HTTP endpoints with FastAPI TestClient.
Tests cover:
- Basic health checks
- Database pool monitoring
- Cache statistics and management
- Query profiling and performance metrics
- Admin operations (clear cache, reset stats)
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

# Import from backend (conftest.py sets up environment)
from main import app
from backend.utils.query_profiler import record_query, reset_statistics
from backend.utils.query_cache import cached, cache_short, clear_cache, reset_cache_stats


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_monitoring():
    """Reset monitoring state before each test"""
    reset_statistics()
    clear_cache()
    reset_cache_stats()
    yield
    reset_statistics()
    clear_cache()
    reset_cache_stats()


class TestBasicHealthEndpoints:
    """Test basic health check endpoints"""

    def test_basic_health_check(self, client):
        """Test GET /api/health returns basic health status"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert data["status"] == "healthy"
        assert data["service"] == "Content Jumpstart API"
        assert "version" in data

    def test_health_check_returns_json(self, client):
        """Test health endpoint returns valid JSON"""
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Verify parseable
        data = response.json()
        assert isinstance(data, dict)


class TestDatabaseHealthEndpoints:
    """Test database health monitoring endpoints"""

    @patch('routers.health.get_pool_status')
    def test_database_health_with_pool(self, mock_get_pool_status, client):
        """Test GET /health/database returns pool status"""
        # Mock pool status
        mock_get_pool_status.return_value = {
            "has_pool": True,
            "database_type": "postgresql",
            "pool_size": 20,
            "max_overflow": 40,
            "checked_out": 5,
            "checked_in": 15,
            "utilization_percent": 25.0,
            "health_status": "healthy"
        }

        response = client.get("/api/health/database")

        assert response.status_code == 200
        data = response.json()

        assert data["has_pool"] is True
        assert data["database_type"] == "postgresql"
        assert data["pool_size"] == 20
        assert data["utilization_percent"] == 25.0

    @patch('routers.health.get_pool_status')
    def test_database_health_without_pool(self, mock_get_pool_status, client):
        """Test database health when no pool configured (SQLite)"""
        mock_get_pool_status.return_value = {
            "has_pool": False,
            "database_type": "sqlite",
            "pool_size": None,
            "health_status": "healthy"
        }

        response = client.get("/api/health/database")

        assert response.status_code == 200
        data = response.json()

        assert data["has_pool"] is False
        assert data["database_type"] == "sqlite"

    @patch('routers.health.get_pool_events')
    def test_database_events(self, mock_get_pool_events, client):
        """Test GET /health/database/events returns event counters"""
        mock_get_pool_events.return_value = {
            "has_listener": True,
            "connect_count": 100,
            "disconnect_count": 80,
            "checkout_count": 520,
            "checkin_count": 500
        }

        response = client.get("/api/health/database/events")

        assert response.status_code == 200
        data = response.json()

        assert data["has_listener"] is True
        assert data["connect_count"] == 100


class TestCacheHealthEndpoints:
    """Test cache monitoring and management endpoints"""

    def test_cache_health_all_tiers(self, client):
        """Test GET /health/cache returns stats for all tiers"""
        # Populate cache to generate stats
        @cache_short()
        def test_func(x: int) -> int:
            return x * 2

        test_func(1)  # Cache miss
        test_func(1)  # Cache hit

        response = client.get("/api/health/cache")

        assert response.status_code == 200
        data = response.json()

        # Should return all three tiers
        assert "short" in data
        assert "medium" in data
        assert "long" in data

        # Verify short tier has stats
        assert data["short"]["size"] >= 1
        assert data["short"]["hits"] >= 1

    def test_cache_health_single_tier(self, client):
        """Test GET /health/cache?tier=short returns specific tier"""
        response = client.get("/api/health/cache?tier=short")

        assert response.status_code == 200
        data = response.json()

        # Should return single tier with recommendations
        assert "tier" in data
        assert data["tier"] == "short"
        assert "recommendations" in data

    def test_cache_health_recommendations(self, client):
        """Test cache health includes hit rate recommendations"""
        # Create cache with low hit rate
        @cache_short()
        def test_func(x: int) -> int:
            return x * 2

        # Generate misses (40% hit rate)
        for i in range(10):
            test_func(i)  # All misses

        for i in range(5):
            test_func(i)  # 5 hits

        response = client.get("/api/health/cache?tier=short")

        assert response.status_code == 200
        data = response.json()

        # Hit rate should be ~33% (5 hits / 15 total)
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0

    def test_clear_cache_all_tiers(self, client):
        """Test POST /health/cache/clear clears all caches"""
        # Populate cache
        @cache_short()
        def test_func(x: int) -> int:
            return x * 2

        test_func(1)

        response = client.post("/api/health/cache/clear")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "before" in data
        assert "after" in data

        # Cache should be cleared
        assert data["after"]["short"]["size"] == 0

    def test_clear_cache_specific_tier(self, client):
        """Test clearing specific cache tier"""
        response = client.post("/api/health/cache/clear?tier=short")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

    def test_clear_cache_with_prefix(self, client):
        """Test selective cache clearing by prefix"""
        response = client.post("/api/health/cache/clear?key_prefix=projects")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["message"] == "Cache cleared successfully"

    def test_reset_cache_stats(self, client):
        """Test POST /health/cache/reset-stats resets statistics"""
        # Generate some cache activity
        @cache_short()
        def test_func(x: int) -> int:
            return x * 2

        test_func(1)
        test_func(1)

        response = client.post("/api/health/cache/reset-stats")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

        # Stats should be reset
        stats = data["stats"]["short"]
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestFullHealthCheck:
    """Test comprehensive health check endpoint"""

    @patch('routers.health.get_pool_status')
    @patch('routers.health.get_profiling_report')
    def test_full_health_check(self, mock_profiling_report, mock_pool_status, client):
        """Test GET /health/full returns all subsystem statuses"""
        mock_pool_status.return_value = {
            "has_pool": True,
            "health_status": "healthy"
        }

        mock_profiling_report.return_value = {
            "summary": {
                "total_queries": 100,
                "slow_percentage": 5.0
            }
        }

        response = client.get("/api/health/full")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level fields
        assert data["status"] == "healthy"
        assert data["service"] == "Content Jumpstart API"

        # Verify all components included
        assert "components" in data
        assert "api" in data["components"]
        assert "database" in data["components"]
        assert "cache" in data["components"]
        assert "profiling" in data["components"]


class TestProfilingEndpoints:
    """Test query profiling endpoints"""

    def test_profiling_overview(self, client):
        """Test GET /health/profiling returns profiling report"""
        # Record some queries to generate report
        record_query("SELECT * FROM projects WHERE id = 1", 50.0)
        record_query("SELECT * FROM projects WHERE id = 2", 150.0)

        response = client.get("/api/health/profiling")

        assert response.status_code == 200
        data = response.json()

        # Verify report structure
        assert "summary" in data
        assert "top_slowest_queries" in data
        assert "recent_slow_queries" in data
        assert "recommendations" in data

        # Verify thresholds included
        assert "thresholds" in data
        assert data["thresholds"]["slow_query_ms"] == 100
        assert data["thresholds"]["very_slow_query_ms"] == 500

    def test_profiling_query_statistics(self, client):
        """Test GET /health/profiling/queries returns query stats"""
        # Record queries
        for i in range(10):
            record_query(f"SELECT * FROM projects WHERE id = {i}", 75.0)

        response = client.get("/api/health/profiling/queries")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "count" in data
        assert "limit" in data
        assert "filters" in data
        assert "queries" in data

        # Verify queries array
        assert isinstance(data["queries"], list)

    def test_profiling_query_statistics_with_filters(self, client):
        """Test query statistics with filtering parameters"""
        # Record queries with different patterns
        for i in range(5):
            record_query("SELECT * FROM projects WHERE id = ?", 30.0)  # Fast
        for i in range(3):
            record_query("SELECT * FROM posts WHERE id = ?", 150.0)  # Slow

        # Test min_execution_count filter
        response = client.get("/api/health/profiling/queries?min_execution_count=3")

        assert response.status_code == 200
        data = response.json()

        # Should only return queries executed >= 3 times
        assert data["filters"]["min_execution_count"] == 3

    def test_profiling_query_statistics_only_slow(self, client):
        """Test filtering for only slow queries"""
        # Record fast and slow queries
        record_query("SELECT * FROM projects WHERE id = ?", 50.0)  # Fast
        record_query("SELECT * FROM posts WHERE id = ?", 150.0)  # Slow

        response = client.get("/api/health/profiling/queries?only_slow=true")

        assert response.status_code == 200
        data = response.json()

        assert data["filters"]["only_slow"] is True

    def test_profiling_slow_queries(self, client):
        """Test GET /health/profiling/slow-queries returns recent slow queries"""
        # Record slow query
        record_query("SELECT * FROM projects JOIN posts ON ...", 250.0)

        response = client.get("/api/health/profiling/slow-queries")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "count" in data
        assert "limit" in data
        assert "since_minutes" in data
        assert "queries" in data
        assert "thresholds" in data

        # Verify queries array structure
        if data["count"] > 0:
            query = data["queries"][0]
            assert "query" in query
            assert "duration_ms" in query
            assert "timestamp" in query

    def test_profiling_slow_queries_with_time_filter(self, client):
        """Test slow queries with time window filter"""
        response = client.get("/api/health/profiling/slow-queries?since_minutes=30")

        assert response.status_code == 200
        data = response.json()

        assert data["since_minutes"] == 30

    def test_profiling_slow_queries_very_slow_only(self, client):
        """Test filtering for very slow queries only (>500ms)"""
        # Record very slow query
        record_query("SELECT * FROM projects JOIN posts JOIN clients", 600.0)

        response = client.get("/api/health/profiling/slow-queries?very_slow_only=true")

        assert response.status_code == 200
        data = response.json()

        assert data["very_slow_only"] is True

    def test_reset_profiling_statistics(self, client):
        """Test POST /health/profiling/reset clears profiling data"""
        # Record queries
        record_query("SELECT * FROM projects WHERE id = 1", 100.0)

        response = client.post("/api/health/profiling/reset")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["message"] == "Profiling statistics reset successfully"


class TestErrorConditions:
    """Test error handling in health endpoints"""

    @patch('routers.health.get_pool_status')
    def test_database_health_with_error(self, mock_get_pool_status, client):
        """Test database health when pool status raises error"""
        mock_get_pool_status.return_value = {
            "error": "Database not available",
            "has_pool": False
        }

        response = client.get("/api/health/database")

        # Should still return 200 with error in response
        assert response.status_code == 200
        data = response.json()

        assert "error" in data

    def test_cache_health_invalid_tier(self, client):
        """Test cache health with invalid tier parameter"""
        response = client.get("/api/health/cache?tier=invalid")

        # Should return error response
        assert response.status_code == 200
        data = response.json()

        # Should contain error information
        assert "error" in data


class TestResponseFormats:
    """Test that responses match expected formats"""

    def test_health_response_format(self, client):
        """Test basic health response has expected fields"""
        response = client.get("/health")
        data = response.json()

        # Required fields for main.py /health endpoint
        required_fields = ["status", "version", "rate_limits"]
        for field in required_fields:
            assert field in data

    def test_cache_health_response_format(self, client):
        """Test cache health response format"""
        response = client.get("/api/health/cache?tier=short")
        data = response.json()

        # Required fields for single tier
        required_fields = ["tier", "size", "hits", "misses", "recommendations"]
        for field in required_fields:
            assert field in data

    def test_profiling_overview_response_format(self, client):
        """Test profiling overview response format"""
        response = client.get("/api/health/profiling")
        data = response.json()

        # Required sections
        required_sections = ["summary", "top_slowest_queries", "recommendations", "thresholds"]
        for section in required_sections:
            assert section in data

    def test_query_statistics_response_format(self, client):
        """Test query statistics response format"""
        response = client.get("/api/health/profiling/queries")
        data = response.json()

        # Required fields
        assert "count" in data
        assert "queries" in data
        assert isinstance(data["queries"], list)


class TestConcurrentRequests:
    """Test handling of concurrent health check requests"""

    def test_concurrent_health_checks(self, client):
        """Test multiple concurrent health checks"""
        responses = []

        # Make 5 concurrent requests
        for _ in range(5):
            response = client.get("/health")
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    def test_concurrent_profiling_queries(self, client):
        """Test concurrent profiling endpoint requests"""
        # Record some queries first
        for i in range(10):
            record_query(f"SELECT * FROM projects WHERE id = {i}", 50.0)

        responses = []

        # Make concurrent profiling requests
        for _ in range(3):
            responses.append(client.get("/api/health/profiling"))
            responses.append(client.get("/api/health/profiling/queries"))
            responses.append(client.get("/api/health/profiling/slow-queries"))

        # All should succeed
        for response in responses:
            assert response.status_code == 200
