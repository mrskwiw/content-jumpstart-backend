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


# ---------------------------------------------------------------------------
# redact_dsn — Bug #238 (DB password printed in plaintext to Render logs)
# ---------------------------------------------------------------------------

_SUPABASE_DSN = (
    "postgresql://postgres.abcdefghijklmnop:SuperSecret123"
    "@aws-1-us-west-1.pooler.supabase.com:6543/postgres"
)


def test_redact_dsn_removes_password_but_keeps_diagnostics():
    """The password must go; everything that makes the line useful must stay."""
    out = db.redact_dsn(_SUPABASE_DSN)

    assert "SuperSecret123" not in out
    # Host/port/user/db are what distinguish "wrong Supabase project" from
    # "fell back to SQLite" — the reason this log line exists at all.
    assert "aws-1-us-west-1.pooler.supabase.com" in out
    assert "6543" in out
    assert "postgres.abcdefghijklmnop" in out


def test_redact_dsn_handles_password_containing_at_and_colon():
    """The old split("@")/split(":") masking leaked a fragment of such passwords."""
    out = db.redact_dsn("postgresql://user:pa%40ss%3Aword@host:5432/db")

    assert "pa@ss" not in out
    assert "ss:word" not in out
    assert "user" in out and "host" in out


def test_redact_dsn_truncation_would_not_have_saved_us():
    """Regression for the exact defect: the first 80 chars contain the password."""
    assert "SuperSecret123" in _SUPABASE_DSN[:80]
    assert "SuperSecret123" not in db.redact_dsn(_SUPABASE_DSN)


@pytest.mark.parametrize("value", ["", "NOT_SET"])
def test_redact_dsn_absent_values(value):
    assert db.redact_dsn(value) == "NOT_SET"


def test_redact_dsn_unparseable_value_is_not_echoed():
    """An unparseable value may itself be a credential — never print it back."""
    out = db.redact_dsn("this-is-not-a-url-but-might-be-a-secret")

    assert "might-be-a-secret" not in out
    assert out == "<unparseable DATABASE_URL>"
