"""Tests for the research spend monitor (GAP-PAY-02).

Dollar-based, cache-exempt, soft-alert guardrail over ResearchResult.actual_cost_usd.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.models  # noqa: F401 — register all models on Base
from backend.config import settings
from backend.database import Base
from backend.models.audit_log import AuditLog
from backend.models.research_result import ResearchResult
from backend.services import research_spend_monitor as mon

USER = "user-1"
NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _add(db, *, cost, cached=False, tool="voice_analysis", when=NOW, user=USER):
    db.add(
        ResearchResult(
            id=f"res-{uuid.uuid4().hex[:10]}",
            user_id=user,
            client_id="cl-1",
            tool_name=tool,
            actual_cost_usd=cost,
            is_cached_result=cached,
            created_at=when,
        )
    )
    db.commit()


# --------------------------------------------------------------------------- #
# spend summation
# --------------------------------------------------------------------------- #


def test_sum_excludes_cache_hits_and_null_cost(db):
    _add(db, cost=400.0)  # counts
    _add(db, cost=250.0)  # counts
    _add(db, cost=300.0, cached=True)  # cache hit → excluded
    _add(db, cost=None)  # no recorded cost → excluded
    day_start, _ = mon._window_starts(NOW)
    assert mon.get_user_spend_usd(db, USER, day_start) == pytest.approx(650.0)


def test_spend_is_per_user(db):
    _add(db, cost=500.0, user="user-1")
    _add(db, cost=999.0, user="user-2")
    day_start, _ = mon._window_starts(NOW)
    assert mon.get_user_spend_usd(db, "user-1", day_start) == pytest.approx(500.0)


def test_daily_vs_monthly_windows(db):
    _add(db, cost=100.0, when=NOW)  # today
    _add(db, cost=200.0, when=NOW - timedelta(days=3))  # earlier this month
    _add(db, cost=999.0, when=NOW - timedelta(days=40))  # last month → neither window
    status = mon.get_spend_status(db, USER, now=NOW)
    assert status.daily_spend_usd == pytest.approx(100.0)
    assert status.monthly_spend_usd == pytest.approx(300.0)


def test_per_tool_breakdown(db):
    _add(db, cost=400.0, tool="voice_analysis")
    _add(db, cost=250.0, tool="icp_workshop")
    _add(db, cost=150.0, tool="voice_analysis")
    _, month_start = mon._window_starts(NOW)
    breakdown = mon.get_spend_by_tool(db, USER, month_start)
    assert breakdown == {
        "voice_analysis": pytest.approx(550.0),
        "icp_workshop": pytest.approx(250.0),
    }


# --------------------------------------------------------------------------- #
# check_and_alert (soft alert)
# --------------------------------------------------------------------------- #


def test_alert_written_when_over_daily_cap(db, monkeypatch):
    monkeypatch.setattr(settings, "RESEARCH_DAILY_SPEND_CAP_USD", 500.0)
    monkeypatch.setattr(settings, "RESEARCH_MONTHLY_SPEND_CAP_USD", 100000.0)
    _add(db, cost=600.0)  # over the 500 daily cap

    status = mon.check_and_alert(db, USER, user_email="u@x.com", now=NOW)

    assert status.daily_over is True and status.over_cap is True
    entries = db.query(AuditLog).filter(AuditLog.action == "Research spend cap exceeded").all()
    assert len(entries) == 1
    e = entries[0]
    assert e.status == "warning" and e.action_type == "system" and e.user_id == USER
    assert e.extra_metadata["daily_over"] is True
    assert e.extra_metadata["spend_by_tool_month"]["voice_analysis"] == pytest.approx(600.0)


def test_no_alert_when_under_caps(db, monkeypatch):
    monkeypatch.setattr(settings, "RESEARCH_DAILY_SPEND_CAP_USD", 5000.0)
    monkeypatch.setattr(settings, "RESEARCH_MONTHLY_SPEND_CAP_USD", 10000.0)
    _add(db, cost=600.0)

    status = mon.check_and_alert(db, USER, now=NOW)

    assert status.over_cap is False
    assert db.query(AuditLog).count() == 0


def test_cache_hits_do_not_trigger_alert(db, monkeypatch):
    monkeypatch.setattr(settings, "RESEARCH_DAILY_SPEND_CAP_USD", 500.0)
    _add(db, cost=5000.0, cached=True)  # huge, but cached → $0 real spend
    status = mon.check_and_alert(db, USER, now=NOW)
    assert status.daily_spend_usd == pytest.approx(0.0)
    assert status.over_cap is False
    assert db.query(AuditLog).count() == 0


def test_check_and_alert_never_raises_on_bad_session():
    class _BrokenDB:
        def query(self, *a, **k):
            raise RuntimeError("db down")

    # Must not raise; returns a safe default status.
    status = mon.check_and_alert(_BrokenDB(), USER, now=NOW)
    assert status.daily_spend_usd == 0.0 and status.over_cap is False
