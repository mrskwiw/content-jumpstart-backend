"""
Unit tests for database pool monitoring utility (Week 3).

Tests cover:
- Pool status retrieval
- Pool recommendations
- Health status detection
- Metric formatting
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.utils.db_monitor import get_pool_status, get_pool_events, _get_recommendations


class TestGetPoolStatus:
    """Test get_pool_status() function"""

    @patch('utils.db_monitor.get_engine')
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

    @patch('utils.db_monitor.get_engine')
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

    @patch('utils.db_monitor.get_engine')
    def test_pool_status_with_exception(self, mock_get_engine):
        """Test pool status when engine raises exception"""
        mock_get_engine.side_effect = Exception("Database not available")

        result = get_pool_status()

        assert result["error"] is not None
        assert "Database not available" in result["error"]
        assert result["has_pool"] is False


class TestGetPoolEvents:
    """Test get_pool_events() function"""

    @patch('utils.db_monitor.get_engine')
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

    @patch('utils.db_monitor.get_engine')
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

    @patch('utils.db_monitor.get_engine')
    def test_postgresql_detection(self, mock_get_engine):
        """Test PostgreSQL database type detection"""
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="postgresql://user:pass@localhost/db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["database_type"] == "postgresql"

    @patch('utils.db_monitor.get_engine')
    def test_sqlite_detection(self, mock_get_engine):
        """Test SQLite database type detection"""
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="sqlite:///./test.db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["database_type"] == "sqlite"

    @patch('utils.db_monitor.get_engine')
    def test_mysql_detection(self, mock_get_engine):
        """Test MySQL database type detection"""
        mock_engine = Mock()
        mock_engine.pool = None
        mock_engine.url.__str__ = Mock(return_value="mysql+pymysql://user:pass@localhost/db")
        mock_get_engine.return_value = mock_engine

        result = get_pool_status()

        assert result["database_type"] == "mysql"
