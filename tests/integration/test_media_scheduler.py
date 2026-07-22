"""
Tests for the in-process media scheduler (Phase 12) and orchestrator edge paths.

Covers env gating, interval parsing, a single tick delegating to process_due on
SQLite (no advisory lock), the loop running until stopped, plus the orchestrator
branches the happy-path integration test doesn't hit: fail-then-retry in the
worker, per-stage budget rejection, terminal-job advance, and dry-run assembly
guard.
"""

import asyncio

import pytest

from backend.models import User
from backend.models.media import MediaAsset, MediaJob
from backend.services.media import orchestrator
from backend.services.media import scheduler
from backend.utils.auth import get_password_hash

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


def _user(db, uid="u-sched"):
    u = User(
        id=uid, email=f"{uid}@example.com", hashed_password=get_password_hash(PW), is_active=True
    )
    db.add(u)
    db.commit()
    return u


# ── Scheduler ─────────────────────────────────────────────────────────────────


def test_enabled_env_gating(monkeypatch):
    monkeypatch.delenv("RUN_SCHEDULER", raising=False)
    assert scheduler.enabled() is False
    monkeypatch.setenv("RUN_SCHEDULER", "true")
    assert scheduler.enabled() is True
    monkeypatch.setenv("RUN_SCHEDULER", "0")
    assert scheduler.enabled() is False


def test_interval_parsing(monkeypatch):
    monkeypatch.delenv("MEDIA_SCHEDULER_INTERVAL_SECONDS", raising=False)
    assert scheduler._interval_seconds() == 60
    monkeypatch.setenv("MEDIA_SCHEDULER_INTERVAL_SECONDS", "5")  # clamped to floor of 10
    assert scheduler._interval_seconds() == 10
    monkeypatch.setenv("MEDIA_SCHEDULER_INTERVAL_SECONDS", "90")
    assert scheduler._interval_seconds() == 90
    monkeypatch.setenv("MEDIA_SCHEDULER_INTERVAL_SECONDS", "not-a-number")
    assert scheduler._interval_seconds() == 60


def test_tick_delegates_to_process_due_on_sqlite(db_session, monkeypatch):
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)  # keep fixture session open
    calls = {"n": 0}

    def spy(db, **kw):
        calls["n"] += 1
        return {"processed": 1}

    monkeypatch.setattr(orchestrator, "process_due", spy)
    scheduler._tick()
    assert calls["n"] == 1


def test_scheduler_loop_runs_until_stopped(monkeypatch):
    stop = asyncio.Event()
    calls = {"n": 0}

    def fake_tick():
        calls["n"] += 1
        stop.set()

    monkeypatch.setattr(scheduler, "_tick", fake_tick)
    monkeypatch.setenv("MEDIA_SCHEDULER_INTERVAL_SECONDS", "10")
    asyncio.run(scheduler.scheduler_loop(stop))
    assert calls["n"] >= 1


# ── Orchestrator edge paths ───────────────────────────────────────────────────


def test_submit_pipeline_unknown_raises(db_session):
    _user(db_session, "u-unknownp")
    with pytest.raises(ValueError):
        orchestrator.submit_pipeline(db_session, "u-unknownp", pipeline="nope", spec={})


def test_advance_noop_on_terminal_job(db_session):
    job = MediaJob(id="j-term", user_id="u", kind="tts", provider="stub", status="done")
    db_session.add(job)
    db_session.commit()
    assert orchestrator.advance(db_session, job).status == "done"


def test_worker_retries_failed_job(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    _user(db_session, "u-retry")
    # A previously-failed, still-retryable job.
    job = MediaJob(
        id="j-retry",
        user_id="u-retry",
        kind="tts",
        provider="elevenlabs_tts",
        status="failed",
        input_json="{}",
        retry_count=1,
    )
    db_session.add(job)
    db_session.commit()

    summary = orchestrator.process_due(db_session)
    db_session.refresh(job)
    # Re-queued → submitted to the stub → now in flight.
    assert job.status == "processing"
    assert summary["submitted"] >= 1


def test_submit_job_budget_rejection_marks_failed(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    monkeypatch.setenv("MEDIA_MAX_JOB_COST_CENTS", "1")
    _user(db_session, "u-rej")
    job = MediaJob(
        id="j-rej",
        user_id="u-rej",
        kind="gen_clip",
        provider="kling",  # ~96¢ for the default 8s, over the 1¢ cap
        status="queued",
        input_json="{}",
    )
    db_session.add(job)
    db_session.commit()
    orchestrator._submit_job(db_session, job)
    assert job.status == "failed"
    assert "cap" in (job.error_message or "").lower()
    # Budget rejection is non-transient → retries exhausted immediately.
    assert job.retry_count == orchestrator.MAX_RETRIES


def test_budget_failed_job_not_requeued_by_worker(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    monkeypatch.setenv("MEDIA_MAX_JOB_COST_CENTS", "1")
    _user(db_session, "u-bt")
    job = MediaJob(
        id="j-bt",
        user_id="u-bt",
        kind="gen_clip",
        provider="kling",
        status="queued",
        input_json="{}",
    )
    db_session.add(job)
    db_session.commit()
    orchestrator._submit_job(db_session, job)  # terminal budget failure

    # The worker must NOT requeue a terminally budget-failed job every tick.
    summary = orchestrator.process_due(db_session)
    db_session.refresh(job)
    assert job.status == "failed"
    assert summary["submitted"] == 0


def test_terminal_failure_cascades_to_descendants(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    _user(db_session, "u-casc2")
    root = orchestrator.submit_pipeline(
        db_session, "u-casc2", pipeline="cinematic", spec={"prompt": "x"}
    )
    # Force the in-flight root stage to fail terminally.
    orchestrator._mark_failed(db_session, root, "boom", terminal=True)

    stages = (
        db_session.query(MediaJob)
        .filter(MediaJob.pipeline == "cinematic", MediaJob.user_id == "u-casc2")
        .all()
    )
    assert len(stages) == 3
    # No stage is left stranded in awaiting_dependency.
    assert all(s.status == "failed" for s in stages)


def test_assemble_requires_dry_run(db_session, monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    _user(db_session, "u-asm")
    db_session.add(
        MediaJob(id="j-asm", user_id="u-asm", kind="tts", provider="stub", status="done")
    )
    db_session.add(
        MediaAsset(id="a-asm", user_id="u-asm", job_id="j-asm", kind="clip", url="https://x/y.mp4")
    )
    db_session.commit()
    with pytest.raises(NotImplementedError):
        orchestrator.assemble(db_session, "u-asm", ["a-asm"])


def test_assemble_unknown_asset_raises(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    _user(db_session, "u-asm2")
    with pytest.raises(ValueError):
        orchestrator.assemble(db_session, "u-asm2", ["does-not-exist"])


def test_cancel_cascades_to_children(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    _user(db_session, "u-casc")
    root = orchestrator.submit_pipeline(
        db_session, "u-casc", pipeline="talking_head", spec={"script": "x"}
    )
    orchestrator.cancel_job(db_session, root)
    child = db_session.query(MediaJob).filter(MediaJob.parent_job_id == root.id).first()
    assert root.status == "canceled"
    assert child.status == "canceled"
