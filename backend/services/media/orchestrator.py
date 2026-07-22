"""
Media generation orchestrator (Phase 12 — P12.1 backbone).

Owns the async job lifecycle: a pipeline (talking-head / cinematic / audio) is an
ordered chain of `MediaJob`s linked by `parent_job_id`. Each stage submits to its
provider (`queued → processing`), completes via poll or webhook (`→ done`),
produces a `MediaAsset`, then unblocks the next stage (`awaiting_dependency →
queued`). Renders take minutes, so job state lives in Postgres, never memory.

Advancement is driven by `process_due()` — a DB-polling worker meant to be run
every minute (in-process `scheduler.py`, or an external Render Cron Job hitting
the protected `/api/media/process-due` endpoint). Mirrors the Phase 10
distribution worker: `with_for_update(skip_locked=True)` so concurrent ticks
never double-advance a job.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.media import MediaAsset, MediaJob
from backend.services.media import cost
from backend.services.media.providers import MediaKind, get_provider

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# Ordered provider chains per pipeline. (kind, provider_name) per stage. In
# dry-run every provider resolves to the stub; the real name is persisted so the
# chain reads truthfully and P12.2+ can swap in real integrations unchanged.
PIPELINES: dict[str, list[tuple[MediaKind, str]]] = {
    "talking_head": [
        (MediaKind.TTS, "elevenlabs_tts"),
        (MediaKind.AVATAR_VIDEO, "heygen"),
    ],
    "cinematic": [
        (MediaKind.GEN_CLIP, "kling"),
        (MediaKind.TTS, "elevenlabs_tts"),
        (MediaKind.ASSEMBLE, "ffmpeg"),
    ],
    "audio_only": [
        (MediaKind.TTS, "elevenlabs_tts"),
    ],
}

# Statuses a job can be advanced from by the worker.
_ACTIVE_STATUSES = ("queued", "processing")
_TERMINAL_STATUSES = ("done", "failed", "canceled")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Estimation ────────────────────────────────────────────────────────────────


def estimate_pipeline(pipeline: str, spec: dict) -> dict:
    """Projected per-stage + total cost (cents) for a pipeline, without spending."""
    stages = PIPELINES.get(pipeline)
    if stages is None:
        raise ValueError(f"Unknown pipeline '{pipeline}'")
    seconds = spec.get("seconds")
    breakdown = [
        {
            "kind": kind.value,
            "provider": provider,
            "cost_cents": cost.estimate_cost(kind, provider, seconds=seconds),
        }
        for kind, provider in stages
    ]
    return {
        "pipeline": pipeline,
        "stages": breakdown,
        "total_cost_cents": sum(s["cost_cents"] for s in breakdown),
    }


# ── Pipeline submission ───────────────────────────────────────────────────────


def submit_pipeline(
    db: Session,
    user_id: str,
    *,
    pipeline: str,
    spec: dict,
    client_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> MediaJob:
    """Create every stage of a pipeline and submit the first one.

    The whole pipeline's projected cost is budget-checked up front (fail-closed:
    nothing is created if the pipeline is over-budget). Returns the root job.
    """
    stages = PIPELINES.get(pipeline)
    if stages is None:
        raise ValueError(f"Unknown pipeline '{pipeline}'")

    # Enforce the full pipeline's projected spend before creating any jobs.
    est = estimate_pipeline(pipeline, spec)
    cost.enforce_budget(db, user_id, client_id, est["total_cost_cents"])

    jobs: List[MediaJob] = []
    parent_id: Optional[str] = None
    for idx, (kind, provider) in enumerate(stages):
        job = MediaJob(
            id=_uuid(),
            user_id=user_id,
            client_id=client_id,
            project_id=project_id,
            pipeline=pipeline,
            stage_index=idx,
            parent_job_id=parent_id,
            kind=kind.value,
            provider=provider,
            # Stage 0 is ready to submit; later stages wait on their parent.
            status="queued" if idx == 0 else "awaiting_dependency",
            input_json=json.dumps(spec),
            cost_cents=0,
            retry_count=0,
        )
        db.add(job)
        jobs.append(job)
        parent_id = job.id
    db.commit()

    root = jobs[0]
    _submit_job(db, root)
    db.refresh(root)
    return root


def _stage_seconds(job: MediaJob) -> Optional[float]:
    try:
        return (json.loads(job.input_json) or {}).get("seconds") if job.input_json else None
    except (TypeError, ValueError):
        return None


def _submit_job(db: Session, job: MediaJob) -> MediaJob:
    """Budget-gate, then submit a single queued stage to its provider."""
    kind = MediaKind(job.kind)
    est = cost.estimate_cost(kind, job.provider, seconds=_stage_seconds(job))
    try:
        cost.enforce_budget(db, job.user_id, job.client_id, est)
    except cost.BudgetExceededError as e:
        # Budget rejection is non-transient — retrying can't make it pass, so mark
        # it terminal (don't let the worker requeue it every tick).
        return _mark_failed(db, job, str(e), terminal=True)

    provider = get_provider(kind, job.provider, credential=None)
    result = provider.start(json.loads(job.input_json or "{}"))
    return _apply_result(db, job, result)


# ── Advancement (poll / webhook) ──────────────────────────────────────────────


def advance(db: Session, job: MediaJob) -> MediaJob:
    """Move one job forward: submit if queued, else poll an in-flight render."""
    if job.status == "queued":
        return _submit_job(db, job)
    if job.status == "processing":
        provider = get_provider(MediaKind(job.kind), job.provider, credential=None)
        result = provider.poll(job.external_id or "")
        return _apply_result(db, job, result)
    return job


def _mark_failed(db: Session, job: MediaJob, error: Optional[str], *, terminal: bool) -> MediaJob:
    """Mark a job failed, then orphan-proof the pipeline once it's terminal.

    `terminal=True` exhausts the retry budget immediately (non-transient errors
    like budget rejection). Transient failures bump `retry_count`; either way,
    once a job can no longer be retried its downstream stages are failed too so
    the pipeline never strands descendants in `awaiting_dependency`.
    """
    job.status = "failed"
    job.error_message = error
    job.retry_count = MAX_RETRIES if terminal else job.retry_count + 1
    db.commit()
    if job.retry_count >= MAX_RETRIES:
        _fail_descendants(db, job)
    return job


def _fail_descendants(db: Session, job: MediaJob) -> None:
    """Terminally fail downstream stages still waiting on a failed job."""
    child = (
        db.query(MediaJob)
        .filter(
            MediaJob.parent_job_id == job.id,
            MediaJob.status == "awaiting_dependency",
        )
        .first()
    )
    if child is None:
        return
    child.status = "failed"
    child.error_message = f"Upstream stage {job.id} failed; pipeline cannot continue."
    child.retry_count = MAX_RETRIES
    db.commit()
    _fail_descendants(db, child)


def _apply_result(db: Session, job: MediaJob, result) -> MediaJob:
    """Fold a provider `MediaResult` into a job's state (+ chain on completion)."""
    if not result.ok:
        return _mark_failed(db, job, result.error, terminal=False)

    if result.external_id:
        job.external_id = result.external_id

    if result.done and result.asset_url:
        _finalize(db, job, result)
    else:
        job.status = "processing"
        db.commit()
    return job


def _finalize(db: Session, job: MediaJob, result) -> None:
    """Record the produced asset, mark the job done, and unblock the next stage."""
    asset = MediaAsset(
        id=_uuid(),
        user_id=job.user_id,
        job_id=job.id,
        kind="final" if _is_last_stage(db, job) else "clip",
        url=result.asset_url,
        duration_s=result.duration_s,
        mime=result.mime,
        content_hash=hashlib.sha256(result.asset_url.encode("utf-8")).hexdigest(),
    )
    db.add(asset)
    job.output_asset_id = asset.id
    job.cost_cents = int(result.cost_cents or 0)
    job.status = "done"
    job.error_message = None
    db.commit()

    # Unblock the next stage in the chain, if any.
    child = (
        db.query(MediaJob)
        .filter(MediaJob.parent_job_id == job.id, MediaJob.status == "awaiting_dependency")
        .first()
    )
    if child is not None:
        child.status = "queued"
        db.commit()


def _is_last_stage(db: Session, job: MediaJob) -> bool:
    """True when no downstream stage depends on this job."""
    return db.query(MediaJob).filter(MediaJob.parent_job_id == job.id).first() is None


# ── Webhook ingest ────────────────────────────────────────────────────────────


def _dev_mode() -> bool:
    """True only in an explicit dev/dry-run context (never in a real deployment)."""
    from backend.services.media.providers import dry_run_enabled

    debug = os.getenv("DEBUG_MODE", "false").strip().lower() in ("1", "true", "yes")
    return debug or dry_run_enabled()


def verify_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """HMAC-verify a provider callback against MEDIA_WEBHOOK_SECRET.

    Fails **closed**: with a secret set, the signature must match. With no secret
    configured, callbacks are rejected in a real deployment (an unset secret is a
    misconfiguration, not consent to trust anyone) and accepted only in explicit
    DEBUG_MODE / MEDIA_DRY_RUN, where no real provider is wired.
    """
    secret = os.getenv("MEDIA_WEBHOOK_SECRET", "").strip()
    if not secret:
        return _dev_mode()
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def ingest_webhook(
    db: Session, provider_name: str, payload: dict, headers: dict
) -> Optional[MediaJob]:
    """Advance the job a provider callback refers to (looked up by external_id)."""
    external_id = str(payload.get("external_id") or payload.get("id") or "")
    if not external_id:
        return None
    job = db.query(MediaJob).filter(MediaJob.external_id == external_id).first()
    if job is None or job.status in _TERMINAL_STATUSES:
        return job
    provider = get_provider(MediaKind(job.kind), provider_name, credential=None)
    result = provider.parse_webhook(payload, headers)
    return _apply_result(db, job, result)


# ── Cancellation & assembly ───────────────────────────────────────────────────


def cancel_job(db: Session, job: MediaJob) -> MediaJob:
    """Cancel a job (and its not-yet-started descendants)."""
    if job.status in _TERMINAL_STATUSES:
        return job
    job.status = "canceled"
    db.commit()
    # Cancel any downstream stages still waiting on this one.
    child = db.query(MediaJob).filter(MediaJob.parent_job_id == job.id).first()
    if child is not None and child.status not in _TERMINAL_STATUSES:
        cancel_job(db, child)
    return job


def assemble(
    db: Session,
    user_id: str,
    asset_ids: List[str],
    *,
    mux_audio: Optional[str] = None,
) -> MediaAsset:
    """Combine chosen assets into a single final asset.

    P12.1 backbone: real ffmpeg concat/mux lands in P12.3, so this is fail-closed
    outside dry-run. In dry-run it deterministically produces a `final` asset that
    references the inputs, proving the manual-assembly surface end-to-end.
    """
    from backend.services.media.providers import dry_run_enabled

    assets = (
        db.query(MediaAsset)
        .filter(MediaAsset.id.in_(asset_ids), MediaAsset.user_id == user_id)
        .all()
    )
    if len(assets) != len(set(asset_ids)) or not assets:
        raise ValueError("One or more assets were not found or are not owned by you.")

    if not dry_run_enabled():
        raise NotImplementedError(
            "Server-side assembly (ffmpeg concat/mux) is not implemented yet — it "
            "lands in P12.3. Set MEDIA_DRY_RUN=true to exercise the assembly surface."
        )

    digest = hashlib.sha256(
        ("|".join(sorted(asset_ids)) + (mux_audio or "")).encode("utf-8")
    ).hexdigest()
    final = MediaAsset(
        id=_uuid(),
        user_id=user_id,
        job_id=assets[0].job_id,
        kind="final",
        url=f"https://stub.local/media/assembled_{digest[:16]}.mp4",
        duration_s=sum(a.duration_s or 0 for a in assets) or None,
        mime="video/mp4",
        content_hash=digest,
    )
    db.add(final)
    db.commit()
    db.refresh(final)
    return final


# ── Worker ────────────────────────────────────────────────────────────────────


def _active_query(db: Session, statuses):
    q = db.query(MediaJob).filter(MediaJob.status.in_(statuses))
    # Row-lock on Postgres so concurrent cron ticks don't double-advance a job.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    return q


def process_due(db: Session, limit: int = 25) -> dict:
    """Advance queued/processing jobs and retry recent failures.

    One provider poll per in-flight job per pass; the pass repeats while jobs keep
    changing state so a fully-synchronous provider (the dry-run stub) can drive a
    whole chain to completion in a single tick, while a real async provider (whose
    poll returns "still processing") advances exactly one step. Bounded by the
    number of jobs so it always terminates.
    """
    summary = {"submitted": 0, "completed": 0, "failed": 0, "processed": 0}

    for _ in range(limit + 1):
        jobs: List[MediaJob] = (
            _active_query(db, list(_ACTIVE_STATUSES))
            .order_by(MediaJob.created_at.asc())
            .limit(limit)
            .all()
        )
        if not jobs:
            break
        changed = False
        for job in jobs:
            before = job.status
            advance(db, job)
            summary["processed"] += 1
            if job.status != before:
                changed = True
                if job.status == "processing" and before == "queued":
                    summary["submitted"] += 1
                elif job.status == "done":
                    summary["completed"] += 1
                elif job.status == "failed":
                    summary["failed"] += 1
        if not changed:
            break  # nothing advanced (real async jobs still rendering) — stop

    # Retry recent failures under the retry cap.
    cutoff = _now() - timedelta(hours=24)
    failed: List[MediaJob] = (
        _active_query(db, ["failed"])
        .filter(MediaJob.retry_count < MAX_RETRIES, MediaJob.created_at >= cutoff)
        .order_by(MediaJob.created_at.asc())
        .limit(limit)
        .all()
    )
    for job in failed:
        job.status = "queued"
        job.error_message = None
        db.commit()
        _submit_job(db, job)
        summary["processed"] += 1
        if job.status == "processing":
            summary["submitted"] += 1
        elif job.status == "failed":
            summary["failed"] += 1
    return summary
