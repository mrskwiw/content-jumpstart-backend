"""Unit tests for backend.utils.db_monitor (connection pool monitoring)."""

import pytest
from unittest.mock import MagicMock, patch

from backend.utils.db_monitor import (
    _database_type_from_url,
    get_pool_status,
    _get_recommendations,
    get_pool_events,
)


class TestDatabaseTypeFromUrl:
    def test_sqlite(self):
        assert _database_type_from_url("sqlite:///test.db") == "sqlite"

    def test_sqlite_memory(self):
        assert _database_type_from_url("sqlite:///:memory:") == "sqlite"

    def test_postgresql(self):
        assert _database_type_from_url("postgresql://user:pass@host/db") == "postgresql"

    def test_postgresql_psycopg2(self):
        assert _database_type_from_url("postgresql+psycopg2://user:pass@host/db") == "postgresql"

    def test_mysql(self):
        assert _database_type_from_url("mysql://user:pass@host/db") == "mysql"

    def test_unknown_driver(self):
        result = _database_type_from_url("unknown+driver://host/db")
        assert result == "unknown"


class TestGetPoolStatus:
    def _make_engine(self, db_url="sqlite:///:memory:"):
        engine = MagicMock()
        engine.url = db_url
        return engine

    def test_sqlite_returns_no_pool(self):
        engine = self._make_engine("sqlite:///:memory:")
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            status = get_pool_status()
        assert status["has_pool"] is False
        assert status["database_type"] == "sqlite"
        assert status["health_status"] == "healthy"

    def test_postgresql_with_pool(self):
        engine = self._make_engine("postgresql://user:pass@host/db")
        pool = MagicMock()
        pool.checkedout.return_value = 2
        pool.checkedin.return_value = 8
        pool.size.return_value = 10
        pool.overflow.return_value = 0
        engine.pool = pool
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            status = get_pool_status()
        assert status["has_pool"] is True
        assert status["database_type"] == "postgresql"
        assert status["checked_out"] == 2
        assert status["pool_size"] == 10

    def test_healthy_status_at_low_utilization(self):
        engine = self._make_engine("postgresql://user:pass@host/db")
        pool = MagicMock()
        pool.checkedout.return_value = 1
        pool.checkedin.return_value = 9
        pool.size.return_value = 10
        pool.overflow.return_value = 0
        engine.pool = pool
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            status = get_pool_status()
        assert status["health_status"] == "healthy"

    def test_warning_at_80_percent(self):
        engine = self._make_engine("postgresql://user:pass@host/db")
        pool = MagicMock()
        pool.checkedout.return_value = 8
        pool.checkedin.return_value = 2
        pool.size.return_value = 10
        pool.overflow.return_value = 0
        engine.pool = pool
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            status = get_pool_status()
        assert status["health_status"] == "warning"

    def test_critical_at_95_percent(self):
        engine = self._make_engine("postgresql://user:pass@host/db")
        pool = MagicMock()
        pool.checkedout.return_value = 10
        pool.checkedin.return_value = 0
        pool.size.return_value = 10
        pool.overflow.return_value = 0
        engine.pool = pool
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            status = get_pool_status()
        assert status["health_status"] == "critical"

    def test_exception_returns_error_status(self):
        with patch("backend.utils.db_monitor.get_engine", side_effect=RuntimeError("boom")):
            status = get_pool_status()
        assert status["health_status"] == "error"
        assert "error" in status

    def test_includes_recommendations(self):
        engine = self._make_engine("sqlite:///:memory:")
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            status = get_pool_status()
        assert "recommendations" in status
        assert isinstance(status["recommendations"], list)


class TestGetRecommendations:
    def test_no_pool_gives_info(self):
        recs = _get_recommendations({"has_pool": False, "database_type": "sqlite"})
        assert len(recs) == 1
        assert recs[0]["severity"] == "info"

    def test_critical_utilization(self):
        recs = _get_recommendations(
            {
                "has_pool": True,
                "utilization_percent": 97,
                "pool_size": 10,
                "max_overflow": 0,
                "checked_out": 9,
            }
        )
        severities = [r["severity"] for r in recs]
        assert "critical" in severities

    def test_warning_utilization(self):
        recs = _get_recommendations(
            {
                "has_pool": True,
                "utilization_percent": 85,
                "pool_size": 10,
                "max_overflow": 0,
                "checked_out": 8,
            }
        )
        severities = [r["severity"] for r in recs]
        assert "warning" in severities

    def test_healthy_utilization(self):
        recs = _get_recommendations(
            {
                "has_pool": True,
                "utilization_percent": 20,
                "pool_size": 10,
                "max_overflow": 0,
                "checked_out": 2,
            }
        )
        severities = [r["severity"] for r in recs]
        assert "info" in severities

    def test_overflow_warning(self):
        recs = _get_recommendations(
            {
                "has_pool": True,
                "utilization_percent": 30,
                "pool_size": 10,
                "max_overflow": 5,
                "checked_out": 3,
            }
        )
        messages = [r["message"] for r in recs]
        assert any("overflow" in m.lower() or "overflow" in m for m in messages)


class TestGetPoolEvents:
    def test_sqlite_returns_no_listener(self):
        engine = MagicMock()
        engine.url = "sqlite:///:memory:"
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            events = get_pool_events()
        assert events["has_listener"] is False

    def test_postgresql_no_listener(self):
        engine = MagicMock()
        engine.url = "postgresql://user:pass@host/db"
        pool = MagicMock()
        pool._poollistener = None
        engine.pool = pool
        with patch("backend.utils.db_monitor.get_engine", return_value=engine):
            events = get_pool_events()
        assert events["has_listener"] is False

    def test_exception_returns_error(self):
        with patch("backend.utils.db_monitor.get_engine", side_effect=RuntimeError("err")):
            events = get_pool_events()
        assert "error" in events
