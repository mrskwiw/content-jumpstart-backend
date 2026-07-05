"""Unit tests for the PostgreSQL-backed CostTracker."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.utils.cost_tracker import APICall, CostTracker, ProjectCost, get_default_tracker


# ---------------------------------------------------------------------------
# DDL for the tables CostTracker touches (mirrors schema.sql)
# ---------------------------------------------------------------------------
_DDL = """
CREATE TABLE IF NOT EXISTS api_calls (
    call_id   TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    operation  TEXT NOT NULL,
    model      TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0,
    timestamp DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_alerts (
    alert_id  TEXT PRIMARY KEY,
    project_id TEXT UNIQUE NOT NULL,
    budget_limit REAL NOT NULL,
    alert_threshold REAL NOT NULL DEFAULT 0.8,
    enabled BOOLEAN NOT NULL DEFAULT 1
);
"""


@pytest.fixture
def mem_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        for stmt in _DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        conn.commit()
    return engine


@pytest.fixture
def mem_session(mem_engine):
    Session = sessionmaker(bind=mem_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def tracker(mem_session, monkeypatch):
    """CostTracker wired to an in-memory SQLite session via monkeypatch."""
    monkeypatch.setattr(
        "src.utils.cost_tracker._open_session",
        lambda: mem_session,
    )
    # Prevent double-close by the tracker (session is owned by the fixture)
    original_close = mem_session.close
    mem_session.close = lambda: None  # no-op; fixture tears down
    ct = CostTracker()
    yield ct
    mem_session.close = original_close


# ---------------------------------------------------------------------------
# calculate_cost — pure, no DB
# ---------------------------------------------------------------------------


class TestCalculateCost:
    def test_basic(self):
        ct = CostTracker()
        cost = ct.calculate_cost("claude-3-5-sonnet-20241022", 1_000, 500)
        expected = (1_000 / 1_000_000 * 3.0) + (500 / 1_000_000 * 15.0)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_with_cache(self):
        ct = CostTracker()
        cost = ct.calculate_cost(
            "claude-3-5-sonnet-20241022",
            1_000,
            500,
            cache_creation_tokens=2_000,
            cache_read_tokens=5_000,
        )
        expected = (
            (1_000 / 1_000_000 * 3.0)
            + (500 / 1_000_000 * 15.0)
            + (2_000 / 1_000_000 * 3.75)
            + (5_000 / 1_000_000 * 0.3)
        )
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_unknown_model_falls_back_to_sonnet(self):
        ct = CostTracker()
        cost_unknown = ct.calculate_cost("totally-made-up-model", 1_000, 500)
        cost_sonnet = ct.calculate_cost("claude-sonnet-4-5-20250929", 1_000, 500)
        assert cost_unknown == pytest.approx(cost_sonnet, rel=1e-6)

    def test_all_known_models_return_positive(self):
        ct = CostTracker()
        from src.utils.cost_tracker import MODEL_PRICING

        for model in MODEL_PRICING:
            assert ct.calculate_cost(model, 1_000, 500) > 0

    def test_zero_tokens_return_zero(self):
        ct = CostTracker()
        assert ct.calculate_cost("claude-3-5-sonnet-20241022", 0, 0) == 0.0


# ---------------------------------------------------------------------------
# track_api_call
# ---------------------------------------------------------------------------


class TestTrackApiCall:
    def test_returns_cost(self, tracker):
        cost = tracker.track_api_call(
            project_id="proj-1",
            operation="gen",
            model="claude-3-5-sonnet-20241022",
            input_tokens=1_000,
            output_tokens=500,
        )
        assert cost > 0

    def test_persists_to_db(self, tracker, mem_session):
        tracker.track_api_call("proj-2", "op", "claude-3-5-sonnet-20241022", 1_000, 500)
        row = mem_session.execute(
            text("SELECT COUNT(*) FROM api_calls WHERE project_id='proj-2'")
        ).scalar()
        assert row == 1

    def test_no_session_still_returns_cost(self):
        """If the DB is unavailable, cost is returned without crashing."""
        with patch("src.utils.cost_tracker._open_session", return_value=None):
            ct = CostTracker()
            cost = ct.track_api_call("proj-x", "op", "claude-3-5-sonnet-20241022", 100, 50)
        assert cost > 0

    def test_db_path_param_ignored(self):
        """db_path is accepted for backward compat but has no effect."""
        ct = CostTracker(db_path="/some/old/path.db")
        assert ct is not None


# ---------------------------------------------------------------------------
# get_project_cost
# ---------------------------------------------------------------------------


class TestGetProjectCost:
    def test_empty_project(self, tracker):
        pc = tracker.get_project_cost("nonexistent-proj")
        assert isinstance(pc, ProjectCost)
        assert pc.total_calls == 0
        assert pc.total_cost == 0.0

    def test_aggregates_multiple_calls(self, tracker):
        for op in ("a", "b"):
            tracker.track_api_call("proj-agg", op, "claude-3-5-sonnet-20241022", 1_000, 500)
        pc = tracker.get_project_cost("proj-agg")
        assert pc.total_calls == 2
        assert pc.total_input_tokens == 2_000
        assert pc.total_output_tokens == 1_000
        assert pc.total_cost > 0

    def test_no_session_returns_empty(self):
        with patch("src.utils.cost_tracker._open_session", return_value=None):
            ct = CostTracker()
            pc = ct.get_project_cost("proj-x")
        assert pc.total_calls == 0


# ---------------------------------------------------------------------------
# get_project_calls
# ---------------------------------------------------------------------------


class TestGetProjectCalls:
    def test_returns_api_call_objects(self, tracker):
        tracker.track_api_call("proj-calls", "op1", "claude-3-5-sonnet-20241022", 1_000, 500)
        tracker.track_api_call("proj-calls", "op2", "claude-3-5-sonnet-20241022", 2_000, 1_000)
        calls = tracker.get_project_calls("proj-calls")
        assert len(calls) == 2
        assert all(isinstance(c, APICall) for c in calls)

    def test_empty_returns_empty_list(self, tracker):
        assert tracker.get_project_calls("no-such-proj") == []

    def test_no_session_returns_empty(self):
        with patch("src.utils.cost_tracker._open_session", return_value=None):
            assert CostTracker().get_project_calls("x") == []


# ---------------------------------------------------------------------------
# get_all_projects
# ---------------------------------------------------------------------------


class TestGetAllProjects:
    def test_lists_distinct_projects(self, tracker):
        tracker.track_api_call("pa", "op", "claude-3-5-sonnet-20241022", 100, 50)
        tracker.track_api_call("pb", "op", "claude-3-5-sonnet-20241022", 100, 50)
        tracker.track_api_call("pa", "op", "claude-3-5-sonnet-20241022", 100, 50)
        projects = tracker.get_all_projects()
        assert set(projects) == {"pa", "pb"}

    def test_no_session_returns_empty(self):
        with patch("src.utils.cost_tracker._open_session", return_value=None):
            assert CostTracker().get_all_projects() == []


# ---------------------------------------------------------------------------
# get_total_costs
# ---------------------------------------------------------------------------


class TestGetTotalCosts:
    def test_basic(self, tracker):
        tracker.track_api_call("p1", "op", "claude-3-5-sonnet-20241022", 1_000, 500)
        tracker.track_api_call("p2", "op", "claude-3-5-sonnet-20241022", 2_000, 1_000)
        totals = tracker.get_total_costs()
        assert totals["total_projects"] == 2
        assert totals["total_calls"] == 2
        assert totals["total_input_tokens"] == 3_000
        assert totals["total_cost"] > 0

    def test_start_date_filter(self, tracker):
        tracker.track_api_call("p1", "op", "claude-3-5-sonnet-20241022", 1_000, 500)
        yesterday = datetime.utcnow() - timedelta(days=1)
        totals = tracker.get_total_costs(start_date=yesterday)
        assert totals["total_calls"] >= 1

    def test_end_date_filter(self, tracker):
        tracker.track_api_call("p1", "op", "claude-3-5-sonnet-20241022", 1_000, 500)
        tomorrow = datetime.utcnow() + timedelta(days=1)
        totals = tracker.get_total_costs(end_date=tomorrow)
        assert totals["total_calls"] >= 1

    def test_date_range_excludes_old(self, tracker):
        tracker.track_api_call("p1", "op", "claude-3-5-sonnet-20241022", 1_000, 500)
        week_ago = datetime.utcnow() - timedelta(days=7)
        six_days_ago = datetime.utcnow() - timedelta(days=6)
        totals = tracker.get_total_costs(start_date=week_ago, end_date=six_days_ago)
        assert totals["total_calls"] == 0

    def test_no_session_returns_zeros(self):
        with patch("src.utils.cost_tracker._open_session", return_value=None):
            totals = CostTracker().get_total_costs()
        assert totals["total_cost"] == 0.0


# ---------------------------------------------------------------------------
# set_budget_alert + _check_budget_alert
# ---------------------------------------------------------------------------


class TestBudgetAlert:
    def test_stores_alert(self, tracker, mem_session):
        tracker.set_budget_alert("proj-alert", budget_limit=5.0, alert_threshold=0.8)
        row = mem_session.execute(
            text(
                "SELECT budget_limit, alert_threshold FROM budget_alerts WHERE project_id='proj-alert'"
            )
        ).fetchone()
        assert row is not None
        assert row[0] == 5.0
        assert row[1] == 0.8

    def test_upserts_on_duplicate(self, tracker, mem_session):
        tracker.set_budget_alert("proj-dup", budget_limit=1.0)
        tracker.set_budget_alert("proj-dup", budget_limit=2.0)
        count = mem_session.execute(
            text("SELECT COUNT(*) FROM budget_alerts WHERE project_id='proj-dup'")
        ).scalar()
        assert count == 1
        limit = mem_session.execute(
            text("SELECT budget_limit FROM budget_alerts WHERE project_id='proj-dup'")
        ).scalar()
        assert limit == 2.0

    def test_alert_warning_logged(self, tracker, caplog):
        import logging

        tracker.set_budget_alert("proj-warn", budget_limit=0.001, alert_threshold=0.5)
        with caplog.at_level(logging.WARNING):
            tracker.track_api_call(
                "proj-warn",
                "op",
                "claude-3-5-sonnet-20241022",
                input_tokens=5_000,
                output_tokens=2_500,
            )
        assert any("BUDGET ALERT" in r.message for r in caplog.records)

    def test_no_session_does_not_raise(self):
        with patch("src.utils.cost_tracker._open_session", return_value=None):
            CostTracker().set_budget_alert("p", 10.0)


# ---------------------------------------------------------------------------
# export_to_json
# ---------------------------------------------------------------------------


class TestExportToJson:
    def test_exports_project_data(self, tracker, tmp_path):
        tracker.track_api_call("proj-exp", "op", "claude-3-5-sonnet-20241022", 1_000, 500)
        out = tmp_path / "export.json"
        tracker.export_to_json(out, project_id="proj-exp")
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["project_id"] == "proj-exp"
        assert "summary" in data
        assert len(data["calls"]) == 1

    def test_exports_all_projects(self, tracker, tmp_path):
        tracker.track_api_call("pa", "op", "claude-3-5-sonnet-20241022", 100, 50)
        tracker.track_api_call("pb", "op", "claude-3-5-sonnet-20241022", 100, 50)
        out = tmp_path / "all.json"
        tracker.export_to_json(out)
        data = json.loads(out.read_text())
        assert "total_summary" in data
        assert len(data["projects"]) == 2


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_default_tracker_returns_same_instance():
    t1 = get_default_tracker()
    t2 = get_default_tracker()
    assert t1 is t2
    assert isinstance(t1, CostTracker)
