"""Unit tests for backend.database._build_engine.

Focus on the production guard: a failed PostgreSQL connection must fail loudly
by default, and only fall back to ephemeral SQLite when explicitly opted in via
ALLOW_SQLITE_FALLBACK. Regression coverage for DATA-01 / Bug #185.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

import backend.database as db


def _failing_pg_engine() -> MagicMock:
    """A stand-in Postgres engine whose connect() raises, as a dead DB would."""
    eng = MagicMock()
    eng.connect.side_effect = OperationalError("SELECT 1", {}, Exception("connection refused"))
    return eng


def test_postgres_failure_raises_when_fallback_disabled(monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", "postgresql://u:p@h:6543/db")
    monkeypatch.setattr(db.settings, "ALLOW_SQLITE_FALLBACK", False)
    monkeypatch.setattr(db, "create_engine", lambda url, **kw: _failing_pg_engine())

    with pytest.raises(RuntimeError, match="ALLOW_SQLITE_FALLBACK is disabled"):
        db._build_engine()


def test_postgres_failure_falls_back_when_enabled(monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", "postgresql://u:p@h:6543/db")
    monkeypatch.setattr(db.settings, "ALLOW_SQLITE_FALLBACK", True)

    real_create_engine = db.create_engine

    def fake_create_engine(url, **kwargs):
        if str(url).startswith("postgresql"):
            return _failing_pg_engine()
        return real_create_engine(url, **kwargs)  # real in-memory SQLite fallback

    monkeypatch.setattr(db, "create_engine", fake_create_engine)

    engine = db._build_engine()
    assert engine.dialect.name == "sqlite"


def test_sqlite_url_builds_engine(monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", "sqlite:///:memory:")
    engine = db._build_engine()
    assert engine.dialect.name == "sqlite"
