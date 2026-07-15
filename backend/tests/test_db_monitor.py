"""
Unit tests for database pool monitoring utility (Week 3).

Tests cover:
- Pool status retrieval
- Pool recommendations
- Health status detection
- Metric formatting
"""

from unittest.mock import Mock, patch
from backend.utils.db_monitor import get_pool_status, get_pool_events, _get_recommendations
from backend.utils.db_monitor import get_engine, _database_type_from_url


class TestGetPoolStatus:
    """Test get_pool_status() function"""

    def test_get_engine_returns_shared_engine(self, monkeypatch):
        sentinel = object()
        monkeypatch.setattr("backend.database.engine", sentinel, raising=False)
        assert get_engine() is sentinel

    def test_database_type_fallback_from_url(self):
        assert (
            _database_type_from_url(
                "oracle+cx_oracle://user:pass@host/db"  # pragma: allowlist secret
            )
            == "oracle"
        )

    @patch("utils.db_monitor.get_engine")
    def test_pool_status_with_pool(self, mock_get_engine):
        """Test pool status when database has pool configured"""
        # Mock engine with pool
        mock_pool = Mock()
        mock_pool.size.return_value = 20
        mock_pool.timeout.return_value = 30
        mock_pool.overflow.return_value = 40
        mock_pool.checkedout.return_value = 5
        mock_pool.checkedin.return_value = 15

        mock_engine = Mock()
        mock_engine.pool = mock_pool
        mock_engine.url.__str__ = Mock(return_value="postgresql://user@host/db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["has_pool"] is True
        assert result["database_type"] == "postgresql"
        assert result["pool_size"] == 20
        assert result["max_overflow"] == 40
        assert result["checked_out"] == 5
        assert result["checked_in"] == 15
        assert result["utilization_percent"] == 25.0  # 5/20 * 100

    @patch("utils.db_monitor.get_engine")
    def test_pool_status_warning_and_critical_levels(self, mock_get_engine):
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.overflow.return_value = 0
        mock_pool.checkedin.return_value = 0

        warning_engine = Mock()
        warning_engine.pool = mock_pool
        warning_engine.url.__str__ = Mock(return_value="postgresql://user@host/db")

        mock_pool.checkedout.return_value = 8
        mock_get_engine.return_value = warning_engine
        warning = get_pool_status()
        assert warning["health_status"] == "warning"

        mock_pool.checkedout.return_value = 10
        critical = get_pool_status()
        assert critical["health_status"] == "critical"

    @patch("utils.db_monitor.get_engine")
    def test_pool_status_without_pool(self, mock_get_engine):
        """Test pool status when database doesn't have pool (SQLite)"""
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="sqlite:///test.db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["has_pool"] is False
        assert result["database_type"] == "sqlite"
        assert result["pool_size"] is None

    @patch("utils.db_monitor.get_engine")
    def test_pool_status_with_exception(self, mock_get_engine):
        """Test pool status when engine raises exception"""
        mock_get_engine.side_effect = Exception("Database not available")

        result = get_pool_status()

        assert result["error"] is not None
        # Security (py/stack-trace-exposure): the raw exception text must not be
        # returned in the response — a generic message is used instead.
        assert "Database not available" not in result["error"]
        assert result["has_pool"] is False


class TestGetPoolEvents:
    """Test get_pool_events() function"""

    @patch("utils.db_monitor.get_engine")
    def test_pool_events_sqlite_short_circuit(self, mock_get_engine):
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="sqlite:///test.db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_events()
        assert result["has_listener"] is False
        assert result["database_type"] == "sqlite"

    @patch("utils.db_monitor.get_engine")
    def test_pool_events_with_listener(self, mock_get_engine):
        """Test pool events when listener is configured"""
        # Mock pool with event listener
        mock_pool = Mock()
        mock_pool._poollistener = Mock()
        mock_pool._poollistener.connect_count = 100
        mock_pool._poollistener.disconnect_count = 80
        mock_pool._poollistener.checkin_count = 500
        mock_pool._poollistener.checkout_count = 520
        mock_pool._poollistener.reset_count = 5

        mock_engine = Mock()
        mock_engine.pool = mock_pool
        mock_get_engine.return_value = mock_engine

        result = get_pool_events()

        assert result["has_listener"] is True
        assert result["connect_count"] == 100
        assert result["disconnect_count"] == 80
        assert result["checkout_count"] == 520
        assert result["checkin_count"] == 500

    @patch("utils.db_monitor.get_engine")
    def test_pool_events_without_listener(self, mock_get_engine):
        """Test pool events when no listener configured"""
        mock_pool = Mock()
        mock_pool._poollistener = None

        mock_engine = Mock()
        mock_engine.pool = mock_pool
        mock_get_engine.return_value = mock_engine

        result = get_pool_events()

        assert result["has_listener"] is False
        assert result["message"] == "Pool event listener not configured"

    @patch("utils.db_monitor.get_engine")
    def test_pool_events_error_path(self, mock_get_engine):
        mock_get_engine.side_effect = Exception("boom")

        result = get_pool_events()
        assert result["has_listener"] is False
        assert result["database_type"] == "unknown"
        # Security (py/stack-trace-exposure): raw exception text must not leak.
        assert "boom" not in result["error"]


class TestGetRecommendations:
    """Test _get_recommendations() helper function"""

    def test_recommendations_high_utilization(self):
        """Test recommendations when pool utilization is high"""
        pool_status = {
            "utilization_percent": 85.0,
            "pool_size": 20,
            "max_overflow": 40,
        }

        recommendations = _get_recommendations(pool_status)

        assert len(recommendations) > 0
        assert any("high utilization" in r["message"].lower() for r in recommendations)
        assert any(r["severity"] == "warning" for r in recommendations)

    def test_recommendations_critical_utilization(self):
        """Test recommendations when pool utilization is critical"""
        pool_status = {
            "utilization_percent": 95.0,
            "pool_size": 20,
            "max_overflow": 40,
        }

        recommendations = _get_recommendations(pool_status)

        assert len(recommendations) > 0
        assert any("critical" in r["message"].lower() for r in recommendations)
        assert any(r["severity"] == "critical" for r in recommendations)

    def test_recommendations_healthy(self):
        """Test recommendations when pool is healthy"""
        pool_status = {
            "utilization_percent": 30.0,
            "pool_size": 20,
            "max_overflow": 40,
        }

        recommendations = _get_recommendations(pool_status)

        # Should have at least an "OK" recommendation
        assert any("healthy" in r["message"].lower() for r in recommendations)

    def test_recommendations_in_range_and_overflow(self):
        pool_status = {
            "utilization_percent": 60.0,
            "pool_size": 20,
            "max_overflow": 40,
            "checked_out": 2,
        }

        recommendations = _get_recommendations(pool_status, size=20, overflow=5)

        assert any("within expected bounds" in r["message"].lower() for r in recommendations)
        assert any("overflow connections" in r["message"].lower() for r in recommendations)

    def test_recommendations_without_pool(self):
        """Test recommendations when no pool configured"""
        pool_status = {
            "has_pool": False,
            "database_type": "sqlite",
        }

        recommendations = _get_recommendations(pool_status)

        assert any("sqlite" in r["message"].lower() for r in recommendations)


class TestDatabaseTypeDetection:
    """Test database type detection from URL"""

    @patch("utils.db_monitor.get_engine")
    def test_postgresql_detection(self, mock_get_engine):
        """Test PostgreSQL database type detection"""
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="postgresql://user:pass@localhost/db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["database_type"] == "postgresql"

    @patch("utils.db_monitor.get_engine")
    def test_sqlite_detection(self, mock_get_engine):
        """Test SQLite database type detection"""
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="sqlite:///./test.db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["database_type"] == "sqlite"

    @patch("utils.db_monitor.get_engine")
    def test_mysql_detection(self, mock_get_engine):
        """Test MySQL database type detection"""
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="mysql+pymysql://user:pass@localhost/db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["database_type"] == "mysql"
