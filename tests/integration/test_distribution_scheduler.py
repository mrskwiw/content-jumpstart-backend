"""
Tests for the in-process distribution scheduler (Phase 10).

Covers env gating, interval parsing, a single tick delegating to process_due on
SQLite (no advisory lock), and the loop running until its stop event is set.
"""

import asyncio

from backend.services.distribution import orchestrator, scheduler


def test_enabled_env_gating(monkeypatch):
    monkeypatch.delenv("RUN_SCHEDULER", raising=False)
    assert scheduler.enabled() is False
    monkeypatch.setenv("RUN_SCHEDULER", "true")
    assert scheduler.enabled() is True
    monkeypatch.setenv("RUN_SCHEDULER", "0")
    assert scheduler.enabled() is False


def test_interval_parsing(monkeypatch):
    monkeypatch.delenv("SCHEDULER_INTERVAL_SECONDS", raising=False)
    assert scheduler._interval_seconds() == 60
    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "5")  # clamped to floor of 10
    assert scheduler._interval_seconds() == 10
    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "120")
    assert scheduler._interval_seconds() == 120
    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "not-a-number")
    assert scheduler._interval_seconds() == 60


def test_tick_delegates_to_process_due_on_sqlite(db_session, monkeypatch):
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)  # keep fixture session open
    calls = {"n": 0}

    def spy(db, **kw):
        calls["n"] += 1
        return {"processed": 0}

    monkeypatch.setattr(orchestrator, "process_due", spy)
    scheduler._tick()
    assert calls["n"] == 1


def test_scheduler_loop_runs_until_stopped(monkeypatch):
    stop = asyncio.Event()
    calls = {"n": 0}

    def fake_tick():
        calls["n"] += 1
        stop.set()  # stop after the first tick so the loop exits promptly

    monkeypatch.setattr(scheduler, "_tick", fake_tick)
    monkeypatch.setenv("SCHEDULER_INTERVAL_SECONDS", "10")

    asyncio.run(scheduler.scheduler_loop(stop))
    assert calls["n"] >= 1
