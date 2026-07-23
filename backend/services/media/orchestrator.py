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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, aliased

from backend.models.deliverable import Deliverable
from backend.models.media import MediaAsset, MediaJob
from backend.services.media import cost
from backend.services.media.providers import MediaKind, get_provider
from backend.services.media.storage import StorageError, StoredObject, get_storage

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
# A failed job is only retried within this window; past it, it is permanently
# terminal (used by both the retry loop and the orphan-reconciliation sweep so the
# two share one definition of "will this ever be retried?").
RETRY_HORIZON = timedelta(hours=24)

# Ordered provider chains per pipeline. (kind, provider_name) per stage. In
# dry-run every provider resolves to the stub; the real name is persisted so the
# chain reads truthfully and P12.2+ can swap in real integrations unchanged.
# Linear pipelines only. Cinematic is a fan-in DAG built dynamically per request
# (see `_build_cinematic`), so it isn't a static chain here.
PIPELINES: dict[str, list[tuple[MediaKind, str]]] = {
    "talking_head": [
        (MediaKind.TTS, "elevenlabs_tts"),
        (MediaKind.AVATAR_VIDEO, "heygen"),
    ],
    "audio_only": [
        (MediaKind.TTS, "elevenlabs_tts"),
    ],
}

# Statuses a job can be advanced from by the worker.
_ACTIVE_STATUSES = ("queued", "processing")
_TERMINAL_STATUSES = ("done", "failed", "canceled")


@dataclass
class _Stage:
    """A node in a pipeline DAG: one provider call + which stages it depends on."""

    kind: MediaKind
    provider: str
    deps: List[int]  # indices of upstream stages this one waits for (fan-in)
    extra: dict  # extra spec fields (prompt, _ffmpeg_op, and _*_from_stage refs)


def _build_cinematic(spec: dict) -> List[_Stage]:
    """Build the cinematic DAG from a spec.

    scenes → N Kling|Veo clips (parallel) → ffmpeg concat → (mux with an optional
    ElevenLabs voiceover) → (optional Sync.so lip-sync). The clips and the VO are
    roots; the concat fans them in. Veo is used only when quality=premium.
    """
    # Premium routes clips to Veo, which isn't callable yet (Vertex AI access
    # unconfirmed — spec §9). Reject up front rather than accept the request, create
    # jobs, and dead-end every clip. Flip this on once VeoProvider can complete.
    if spec.get("quality") == "premium":
        raise ValueError(
            "Premium (Veo) clips are not available yet — Vertex AI access is unconfirmed. "
            "Use the default quality (Kling)."
        )
    scenes = spec.get("scenes") or [spec.get("prompt") or ""]
    clip_provider = "kling"
    seconds = spec.get("seconds", 5)

    stages: List[_Stage] = []
    clip_idx: List[int] = []
    for scene in scenes:
        stages.append(
            _Stage(MediaKind.GEN_CLIP, clip_provider, [], {"prompt": scene, "seconds": seconds})
        )
        clip_idx.append(len(stages) - 1)

    vo_idx: Optional[int] = None
    vo_text = spec.get("script") or spec.get("voiceover")
    if vo_text:
        stages.append(_Stage(MediaKind.TTS, "elevenlabs_tts", [], {"script": vo_text}))
        vo_idx = len(stages) - 1

    # Stitch the clips.
    stages.append(
        _Stage(
            MediaKind.ASSEMBLE,
            "ffmpeg",
            list(clip_idx),
            {"_ffmpeg_op": "concat", "_clips_from_stages": list(clip_idx)},
        )
    )
    final_idx = len(stages) - 1

    # Marry the voiceover, if any.
    if vo_idx is not None:
        stages.append(
            _Stage(
                MediaKind.ASSEMBLE,
                "ffmpeg",
                [final_idx, vo_idx],
                {"_ffmpeg_op": "mux", "_video_from_stage": final_idx, "_audio_from_stage": vo_idx},
            )
        )
        final_idx = len(stages) - 1

    # Optional lip-sync (on-camera faces).
    if spec.get("lipsync") and vo_idx is not None:
        stages.append(
            _Stage(
                MediaKind.LIPSYNC,
                "sync",
                [final_idx, vo_idx],
                {"_video_from_stage": final_idx, "_audio_from_stage": vo_idx},
            )
        )

    return stages


def _pipeline_stages(pipeline: str, spec: dict) -> List[_Stage]:
    """Resolve a pipeline name to its stage DAG (cinematic is dynamic; others linear)."""
    if pipeline == "cinematic":
        return _build_cinematic(spec)
    linear = PIPELINES.get(pipeline)
    if linear is None:
        raise ValueError(f"Unknown pipeline '{pipeline}'")
    return [
        _Stage(kind, provider, [i - 1] if i else [], {})
        for i, (kind, provider) in enumerate(linear)
    ]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Estimation ────────────────────────────────────────────────────────────────


def estimate_pipeline(pipeline: str, spec: dict) -> dict:
    """Projected per-stage + total cost (cents) for a pipeline, without spending.

    Handles the cinematic DAG's dynamic clip count (one estimate per scene)."""
    stages = _pipeline_stages(pipeline, spec)
    breakdown = [
        {
            "kind": s.kind.value,
            "provider": s.provider,
            "cost_cents": cost.estimate_cost(
                s.kind, s.provider, seconds=s.extra.get("seconds") or spec.get("seconds")
            ),
        }
        for s in stages
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
    """Create every stage of a pipeline and submit its root(s).

    The whole pipeline's projected cost is budget-checked up front (fail-closed:
    nothing is created if it's over-budget). Linear pipelines chain via
    `parent_job_id`; cinematic fans in via `_depends_on` (see `_submit_dag`).
    Returns a representative job (the linear root, or the cinematic terminal stage).
    """
    if pipeline != "cinematic" and pipeline not in PIPELINES:
        raise ValueError(f"Unknown pipeline '{pipeline}'")

    est = estimate_pipeline(pipeline, spec)
    cost.enforce_budget(db, user_id, client_id, est["total_cost_cents"])

    if pipeline == "cinematic":
        return _submit_dag(db, user_id, pipeline, spec, client_id, project_id)

    # Linear path (talking_head / audio_only) — unchanged parent_job_id chain.
    run_id = _uuid()
    stages = PIPELINES[pipeline]
    jobs: List[MediaJob] = []
    parent_id: Optional[str] = None
    for idx, (kind, provider) in enumerate(stages):
        job = MediaJob(
            id=_uuid(),
            user_id=user_id,
            client_id=client_id,
            project_id=project_id,
            pipeline=pipeline,
            pipeline_run_id=run_id,
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


def _submit_dag(
    db: Session,
    user_id: str,
    pipeline: str,
    spec: dict,
    client_id: Optional[str],
    project_id: Optional[str],
) -> MediaJob:
    """Create a fan-in DAG (cinematic) and submit every root stage.

    Each stage's dependencies are recorded as `_depends_on` (job ids) in its
    input_json, plus role refs (`_clips_from`/`_video_from`/`_audio_from`) that the
    promotion sweep resolves to the produced asset keys. Roots (no deps) start now;
    the rest wait in `awaiting_dependency` for `_promote_fanin`.
    """
    stages = _build_cinematic(spec)
    run_id = _uuid()
    ids = [_uuid() for _ in stages]

    jobs: List[MediaJob] = []
    for idx, stage in enumerate(stages):
        stage_spec = dict(spec)
        stage_spec.update(
            {
                k: v
                for k, v in stage.extra.items()
                if not k.endswith("_from_stage") and k != "_clips_from_stages"
            }
        )
        if stage.deps:
            stage_spec["_depends_on"] = [ids[d] for d in stage.deps]
        # Resolve stage-index role refs → job-id role refs.
        if "_clips_from_stages" in stage.extra:
            stage_spec["_clips_from"] = [ids[d] for d in stage.extra["_clips_from_stages"]]
        if "_video_from_stage" in stage.extra:
            stage_spec["_video_from"] = ids[stage.extra["_video_from_stage"]]
        if "_audio_from_stage" in stage.extra:
            stage_spec["_audio_from"] = ids[stage.extra["_audio_from_stage"]]
        jobs.append(
            MediaJob(
                id=ids[idx],
                user_id=user_id,
                client_id=client_id,
                project_id=project_id,
                pipeline=pipeline,
                pipeline_run_id=run_id,
                stage_index=idx,
                kind=stage.kind.value,
                provider=stage.provider,
                status="queued" if not stage.deps else "awaiting_dependency",
                input_json=json.dumps(stage_spec),
                cost_cents=0,
                retry_count=0,
            )
        )
    db.add_all(jobs)
    db.commit()

    # Submit every root (clips + voiceover run in parallel).
    for job in jobs:
        if job.status == "queued":
            _submit_job(db, job)

    # Return the terminal stage as the tracker for this run.
    terminal = next((j for j in reversed(jobs)), jobs[-1])
    db.refresh(terminal)
    return terminal


def _past_retry_horizon(job: MediaJob) -> bool:
    """True if the job was created before the retry horizon (naive/aware safe)."""
    created = job.created_at
    if created is None:
        return False
    if created.tzinfo is None:  # SQLite returns naive UTC; Postgres returns aware
        created = created.replace(tzinfo=timezone.utc)
    return _now() - created > RETRY_HORIZON


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
    try:
        spec = _spec_with_fresh_parent_url(json.loads(job.input_json or "{}"))
    except StorageError as e:
        # No provider call happened (no spend). Don't burn the provider retry budget
        # on a transient storage/signing blip — keep the stage `queued` so the next
        # tick retries for free once storage recovers. But bound it by the shared
        # RETRY_HORIZON: if it's still blocked past that window, storage isn't
        # blipping, it's down — fail terminally (visible + unblocks descendants via
        # _fail_descendants) instead of looping forever. Same created_at+horizon
        # terminality rule as the retry loop / reconcile sweep (see Decision #193).
        if _past_retry_horizon(job):
            return _mark_failed(
                db,
                job,
                f"storage unavailable to sign parent asset past retry horizon: {e}",
                terminal=True,
            )
        job.error_message = f"waiting on storage to sign parent asset: {e}"
        db.commit()
        return job
    result = provider.start(spec)
    return _apply_result(db, job, result)


# Persisted durable-key spec fields → the fresh signed-URL field a provider reads.
_SIGNED_URL_FIELDS = {
    "_parent_asset_key": "_parent_asset_url",  # HeyGen (talking-head) audio
    "_video_key": "_video_url",  # ffmpeg mux / Sync.so video input
    "_audio_key": "_audio_url",  # ffmpeg mux / Sync.so audio input
}


def _spec_with_fresh_parent_url(spec: dict) -> dict:
    """Sign every persisted asset *key* into a fresh, short-lived URL *at submit
    time*. Only durable keys live in job state; the expiring signed URLs are minted
    here, immediately before the provider call, so a delayed/retried submission
    never carries a stale URL (Decision #195). Covers single refs and the ffmpeg
    clip list (`_input_keys` → `_input_urls`)."""
    if not any(spec.get(k) for k in _SIGNED_URL_FIELDS) and not spec.get("_input_keys"):
        return spec
    storage = get_storage()
    out = dict(spec)
    for key_field, url_field in _SIGNED_URL_FIELDS.items():
        if spec.get(key_field):
            out[url_field] = storage.signed_url(spec[key_field])
    if spec.get("_input_keys"):
        out["_input_urls"] = [storage.signed_url(k) for k in spec["_input_keys"] if k]
    return out


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
    """Terminally fail the whole downstream subtree waiting on a failed job.

    Walks breadth-first and marks every `awaiting_dependency` descendant in one
    transaction (a single commit), so the subtree can't be left half-updated. The
    `process_due` reconciliation sweep is the backstop if this is ever interrupted
    (crash) or if an orphan predates this code.
    """
    frontier = [job.id]
    marked = False
    while frontier:
        children = (
            db.query(MediaJob)
            .filter(
                MediaJob.parent_job_id.in_(frontier),
                MediaJob.status == "awaiting_dependency",
            )
            .all()
        )
        if not children:
            break
        for child in children:
            child.status = "failed"
            child.error_message = (
                f"Upstream stage {child.parent_job_id} failed; pipeline cannot continue."
            )
            child.retry_count = MAX_RETRIES
        marked = True
        frontier = [c.id for c in children]
    if marked:
        db.commit()


def _apply_result(db: Session, job: MediaJob, result) -> MediaJob:
    """Fold a provider `MediaResult` into a job's state (+ chain on completion)."""
    if not result.ok:
        return _mark_failed(db, job, result.error, terminal=False)

    if result.external_id:
        job.external_id = result.external_id

    # A stage is complete when the provider reports done AND handed us something to
    # persist — raw bytes (synchronous TTS) or a hosted URL to re-host (HeyGen).
    if result.done and (result.asset_url or result.content is not None):
        _finalize(db, job, result)
    else:
        job.status = "processing"
        db.commit()
    return job


_EXT_BY_MIME = {"video/mp4": ".mp4", "audio/mpeg": ".mp3", "audio/wav": ".wav"}


def _persist_result(job: MediaJob, result, asset_id: str) -> StoredObject:
    """Re-host a provider result to durable storage; return the stored object."""
    mime = result.content_mime or result.mime or "application/octet-stream"
    ext = _EXT_BY_MIME.get(mime, ".bin")
    key = f"media/{job.user_id}/{job.id}/{asset_id}{ext}"
    storage = get_storage()
    if result.content is not None:
        return storage.put_bytes(result.content, key, mime)
    return storage.put_from_url(result.asset_url, key, mime=result.mime)


def _finalize(db: Session, job: MediaJob, result) -> None:
    """Persist the produced asset to storage, mark the job done, and either unblock
    the next stage or (on the terminal stage) create a Deliverable."""
    is_last = _is_last_stage(db, job)
    asset_id = _uuid()
    try:
        stored = _persist_result(job, result, asset_id)
    except StorageError as e:
        # The provider already succeeded (and, for paid providers, already billed).
        # Never re-run it just because persistence failed — that would double-spend.
        if job.external_id:
            # Async provider (HeyGen): the render is still retrievable, so drop back
            # to `processing`. The next poll re-fetches it and retries ONLY storage —
            # no re-submit, no extra spend. Bounded by RETRY_HORIZON (same rule as the
            # signing path / Decision #195): a persistent outage terminates + unblocks
            # descendants instead of re-polling forever.
            if _past_retry_horizon(job):
                _mark_failed(
                    db,
                    job,
                    f"storage unavailable to persist asset past retry horizon: {e}",
                    terminal=True,
                )
            else:
                job.status = "processing"
                job.error_message = f"storage error (will retry persistence): {e}"
                db.commit()
        else:
            # Synchronous provider (TTS): its output bytes are already consumed and
            # can't be recovered without re-billing, so fail terminally for manual
            # re-trigger rather than silently regenerating and paying again.
            _mark_failed(
                db,
                job,
                f"storage failed after provider succeeded; not retried to avoid duplicate spend: {e}",
                terminal=True,
            )
        return

    hash_src = (
        result.content if result.content is not None else (result.asset_url or "").encode("utf-8")
    )
    asset = MediaAsset(
        id=asset_id,
        user_id=job.user_id,
        job_id=job.id,
        kind="final" if is_last else "clip",
        url=stored.key,  # durable storage key; sign on read via /assets/{id}/download
        duration_s=result.duration_s,
        mime=stored.mime or result.mime,
        bytes=stored.size_bytes,
        content_hash=hashlib.sha256(hash_src).hexdigest(),
    )
    db.add(asset)
    job.output_asset_id = asset.id
    job.cost_cents = int(result.cost_cents or 0)
    job.status = "done"
    job.error_message = None
    db.commit()

    if is_last:
        _create_deliverable(db, job, asset)
    else:
        _unblock_child(db, job, asset)


def _unblock_child(db: Session, job: MediaJob, asset: MediaAsset) -> None:
    """Queue the next stage, injecting the parent's asset so it can consume it
    (e.g. HeyGen renders an avatar over the TTS audio from the prior stage)."""
    child = (
        db.query(MediaJob)
        .filter(MediaJob.parent_job_id == job.id, MediaJob.status == "awaiting_dependency")
        .first()
    )
    if child is None:
        return
    try:
        spec = json.loads(child.input_json or "{}") or {}
    except (TypeError, ValueError):
        spec = {}
    # Persist only the durable key; the expiring signed URL is minted at submit
    # time in `_submit_job` so it can never go stale in job state.
    spec["_parent_asset_key"] = asset.url
    child.input_json = json.dumps(spec)
    child.status = "queued"
    db.commit()


def _create_deliverable(db: Session, job: MediaJob, asset: MediaAsset) -> None:
    """Catalog the finished pipeline as a Deliverable (served via the media asset
    download endpoint). Requires a client_id — Deliverable.client_id is NOT NULL."""
    if not job.client_id:
        return
    fmt = "video" if (asset.mime or "").startswith("video") else "audio"
    db.add(
        Deliverable(
            id=_uuid(),
            project_id=job.project_id,
            client_id=job.client_id,
            format=fmt,
            path=asset.url,  # storage key; download via /api/media/assets/{id}/download
            status="ready",
            checksum=asset.content_hash,
            file_size_bytes=asset.bytes,
        )
    )
    db.commit()


def _is_last_stage(db: Session, job: MediaJob) -> bool:
    """True when no downstream stage depends on this job (linear child OR fan-in)."""
    if db.query(MediaJob).filter(MediaJob.parent_job_id == job.id).first() is not None:
        return False
    if job.pipeline_run_id:
        siblings = (
            db.query(MediaJob)
            .filter(MediaJob.pipeline_run_id == job.pipeline_run_id, MediaJob.id != job.id)
            .all()
        )
        if any(job.id in _depends_on_of(s) for s in siblings):
            return False
    return True


# ── Fan-in dependency resolution (cinematic DAG) ──────────────────────────────


def _depends_on_of(job: MediaJob) -> List[str]:
    """The job ids a fan-in stage waits on (empty for linear/parent-chained jobs)."""
    try:
        spec = json.loads(job.input_json or "{}") or {}
    except (TypeError, ValueError):
        return []
    deps = spec.get("_depends_on")
    return [str(d) for d in deps] if isinstance(deps, list) else []


def _asset_key_of(db: Session, dep: Optional[MediaJob]) -> Optional[str]:
    if dep is None or not dep.output_asset_id:
        return None
    asset = db.query(MediaAsset).filter(MediaAsset.id == dep.output_asset_id).first()
    return asset.url if asset else None


def _promote_fanin(db: Session, limit: int = 100) -> int:
    """Advance fan-in stages whose dependencies have resolved.

    For each `awaiting_dependency` job that declares `_depends_on`: if any dep is
    terminally failed/canceled, fail this stage too (self-healing cascade — re-run
    every tick); if all deps are `done`, resolve the role refs
    (`_clips_from`/`_video_from`/`_audio_from`) to the produced asset keys and queue
    it. Linear (parent-chained) jobs have no `_depends_on` and are skipped here.
    """
    waiting = (
        db.query(MediaJob)
        .filter(MediaJob.status == "awaiting_dependency", MediaJob.pipeline_run_id.isnot(None))
        .limit(limit)
        .all()
    )
    promoted = 0
    for job in waiting:
        deps = _depends_on_of(job)
        if not deps:
            continue  # linear job — handled by _unblock_child, not the sweep
        dep_jobs = {d.id: d for d in db.query(MediaJob).filter(MediaJob.id.in_(deps)).all()}
        if any(
            dep_jobs.get(d) is None or dep_jobs[d].status in ("failed", "canceled") for d in deps
        ):
            _mark_failed(
                db, job, "an upstream stage failed; pipeline cannot assemble", terminal=True
            )
            promoted += 1
            continue
        if all(dep_jobs[d].status == "done" for d in deps):
            _resolve_refs_and_queue(db, job, dep_jobs)
            promoted += 1
    return promoted


def _resolve_refs_and_queue(db: Session, job: MediaJob, dep_jobs: dict) -> None:
    """Resolve a fan-in stage's role refs to produced asset keys, then queue it."""
    try:
        spec = json.loads(job.input_json or "{}") or {}
    except (TypeError, ValueError):
        spec = {}
    if spec.get("_clips_from"):
        spec["_input_keys"] = [_asset_key_of(db, dep_jobs.get(j)) for j in spec["_clips_from"]]
    if spec.get("_video_from"):
        spec["_video_key"] = _asset_key_of(db, dep_jobs.get(spec["_video_from"]))
    if spec.get("_audio_from"):
        spec["_audio_key"] = _asset_key_of(db, dep_jobs.get(spec["_audio_from"]))
    job.input_json = json.dumps(spec)
    job.status = "queued"
    db.commit()


# ── Webhook ingest ────────────────────────────────────────────────────────────


def verify_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """HMAC-verify a provider callback against MEDIA_WEBHOOK_SECRET.

    Fails **closed**: with a secret set, the signature must match. With no secret
    configured, callbacks are rejected in a real deployment (an unset secret is a
    misconfiguration, not consent to trust anyone) and accepted only under
    MEDIA_DRY_RUN — the media subsystem's own explicit "no real provider wired"
    switch. Deliberately gated on MEDIA_DRY_RUN rather than the app-wide DEBUG_MODE
    (whose config default is True) so a real deployment never silently trusts
    unsigned callbacks.
    """
    from backend.services.media.providers import dry_run_enabled

    secret = os.getenv("MEDIA_WEBHOOK_SECRET", "").strip()
    if not secret:
        return dry_run_enabled()
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def _extract_external_id(payload: dict) -> str:
    """Pull the provider job id from a webhook body, top-level or nested.

    Providers vary: some put it at the top (`external_id`/`id`), HeyGen nests
    `video_id` under `event_data`. Check both so the job lookup doesn't miss."""
    for v in (payload.get("external_id"), payload.get("id")):
        if v:
            return str(v)
    for nested_key in ("event_data", "data"):
        nested = payload.get(nested_key) or {}
        if isinstance(nested, dict):
            for k in ("video_id", "external_id", "id"):
                if nested.get(k):
                    return str(nested[k])
    return ""


def ingest_webhook(
    db: Session, provider_name: str, payload: dict, headers: dict
) -> Optional[MediaJob]:
    """Advance the job a provider callback refers to (looked up by external_id)."""
    external_id = _extract_external_id(payload)
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
    """Cancel one stage and everything **downstream** of it.

    Scoped to the stage: cancels this job plus its dependents that can no longer
    complete without it — linear children (`parent_job_id`) and fan-in dependents
    (a stage whose `_depends_on` includes this job). It deliberately does NOT touch
    upstream deps or unrelated sibling roots; to stop an entire cinematic run
    (all clips + VO), use `cancel_run()` / the run-level endpoint.
    """
    if job.status in _TERMINAL_STATUSES:
        return job
    job.status = "canceled"
    db.commit()
    _cancel_dependents(db, job)
    return job


def _cancel_dependents(db: Session, job: MediaJob) -> None:
    """Cancel stages that depend on `job` (linear children + fan-in dependents)."""
    for child in (
        db.query(MediaJob)
        .filter(MediaJob.parent_job_id == job.id, MediaJob.status.notin_(_TERMINAL_STATUSES))
        .all()
    ):
        cancel_job(db, child)
    if job.pipeline_run_id:
        siblings = (
            db.query(MediaJob)
            .filter(
                MediaJob.pipeline_run_id == job.pipeline_run_id,
                MediaJob.id != job.id,
                MediaJob.status.notin_(_TERMINAL_STATUSES),
            )
            .all()
        )
        for s in siblings:
            if job.id in _depends_on_of(s):
                cancel_job(db, s)


def cancel_run(db: Session, run_id: str, user_id: str) -> int:
    """Cancel every non-terminal stage of a pipeline run (owner-scoped). Returns the
    number of stages canceled. This is the explicit "stop the whole run" action —
    the only way to halt a cinematic run's parallel clip/VO roots."""
    jobs = (
        db.query(MediaJob)
        .filter(
            MediaJob.pipeline_run_id == run_id,
            MediaJob.user_id == user_id,
            MediaJob.status.notin_(_TERMINAL_STATUSES),
        )
        .all()
    )
    for j in jobs:
        j.status = "canceled"
    db.commit()
    return len(jobs)


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


def _reconcile_orphans(db: Session, limit: int = 25) -> int:
    """Fail stages waiting on a parent that already failed/canceled.

    The backstop for `_fail_descendants`: idempotent, catches subtrees left
    half-failed by an interrupted cascade as well as pre-existing orphans. Bounded
    re-scan so a whole stranded subtree drains in one call.
    """
    parent = aliased(MediaJob)
    horizon = _now() - RETRY_HORIZON
    reconciled = 0
    for _ in range(limit + 1):
        # Only reconcile behind a *permanently terminal* parent: canceled, or a
        # failed parent the worker will never retry — either retries exhausted OR
        # aged out of the retry horizon. A parent still eligible for retry may yet
        # succeed, so its descendants must stay in awaiting_dependency. This mirrors
        # the retry loop's own eligibility test, so the two never disagree.
        orphans: List[MediaJob] = (
            db.query(MediaJob)
            .join(parent, MediaJob.parent_job_id == parent.id)
            .filter(
                MediaJob.status == "awaiting_dependency",
                or_(
                    parent.status == "canceled",
                    and_(
                        parent.status == "failed",
                        or_(
                            parent.retry_count >= MAX_RETRIES,
                            parent.created_at < horizon,
                        ),
                    ),
                ),
            )
            .limit(limit)
            .all()
        )
        if not orphans:
            break
        for o in orphans:
            o.status = "failed"
            o.error_message = f"Upstream stage {o.parent_job_id} failed; pipeline cannot continue."
            o.retry_count = MAX_RETRIES
            reconciled += 1
        db.commit()
    return reconciled


def process_due(db: Session, limit: int = 25) -> dict:
    """Advance queued/processing jobs and retry recent failures.

    One provider poll per in-flight job per pass; the pass repeats while jobs keep
    changing state so a fully-synchronous provider (the dry-run stub) can drive a
    whole chain to completion in a single tick, while a real async provider (whose
    poll returns "still processing") advances exactly one step. Bounded by the
    number of jobs so it always terminates.
    """
    summary = {
        "submitted": 0,
        "completed": 0,
        "failed": 0,
        "processed": 0,
        "reconciled": 0,
        "promoted": 0,
    }

    # Self-healing sweep first: fail any linear stage stranded behind a parent that
    # has already terminally failed/canceled. Covers a cascade interrupted mid-walk
    # (crash) and orphans that predate the cascade logic — the pipeline reconciles
    # itself instead of relying on one uninterrupted transaction.
    summary["reconciled"] = _reconcile_orphans(db, limit)

    for _ in range(limit + 1):
        # Promote fan-in stages whose deps have resolved (cinematic), then advance
        # the newly-queued jobs in the same pass so a dry-run DAG can complete in one
        # tick. A pass that promotes something counts as progress.
        promoted = _promote_fanin(db, max(limit, 100))
        summary["promoted"] += promoted

        jobs: List[MediaJob] = (
            _active_query(db, list(_ACTIVE_STATUSES))
            .order_by(MediaJob.created_at.asc())
            .limit(limit)
            .all()
        )
        if not jobs and promoted == 0:
            break
        changed = promoted > 0
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

    # Retry recent failures under the retry cap (within the retry horizon).
    cutoff = _now() - RETRY_HORIZON
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
