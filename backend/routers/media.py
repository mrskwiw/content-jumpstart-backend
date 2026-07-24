"""
Phase 12 — Media Generation API (P12.1 backbone).

Start a media pipeline (talking-head / cinematic / audio), track async jobs and
their produced assets, and run the poll worker. All read/write endpoints are
scoped to the authenticated user; `process-due` is superuser-gated (called by a
scheduled worker with an admin token). Webhooks are HMAC-verified, not tied to a
user session.

Everything runs in `MEDIA_DRY_RUN` for the backbone: no real provider spend.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth_dependency import get_current_user, require_superuser
from backend.models.media import MediaAsset, MediaJob
from backend.services.media import cost, orchestrator
from backend.services.media.storage import StorageError, get_storage

router = APIRouter(prefix="/api/media", tags=["Media Generation"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    pipeline: Optional[str] = Field(
        None,
        description="talking_head | cinematic | audio_only (or use `kind` for a standalone op)",
    )
    # Standalone audio op alias: audio_clean | audio_master | dub. Maps to the
    # single-op pipeline of the same name; spec carries source_asset_id / source_url.
    kind: Optional[str] = None
    spec: dict = Field(
        default_factory=dict, description="Provider inputs (script, prompt, source_asset_id…)"
    )
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    # A pipeline is only submitted (spend committed) when confirm=true; otherwise
    # the endpoint returns the cost estimate for the caller to approve.
    confirm: bool = False
    model_config = ConfigDict(extra="forbid")


class AssetOut(BaseModel):
    id: str
    kind: str
    url: str
    duration_s: Optional[int] = None
    mime: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class JobOut(BaseModel):
    id: str
    pipeline: Optional[str] = None
    pipeline_run_id: Optional[str] = None
    stage_index: int
    parent_job_id: Optional[str] = None
    kind: str
    provider: str
    status: str
    external_id: Optional[str] = None
    output_asset_id: Optional[str] = None
    cost_cents: int
    error_message: Optional[str] = None
    retry_count: int
    model_config = ConfigDict(from_attributes=True)


class JobDetail(JobOut):
    assets: List[AssetOut] = []


class AssembleRequest(BaseModel):
    asset_ids: List[str] = Field(..., min_length=1)
    mux_audio: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


# ── Pipelines & estimation ────────────────────────────────────────────────────


@router.get("/pipelines")
def list_pipelines():
    """The pipelines this subsystem can run, with their provider chains.

    Cinematic is a fan-in DAG built per request; a representative 1-clip shape is
    shown here for discovery.
    """
    pipelines = {
        name: [{"kind": kind.value, "provider": provider} for kind, provider in stages]
        for name, stages in orchestrator.PIPELINES.items()
    }
    sample = orchestrator._build_cinematic({"scenes": ["scene"], "script": "voiceover"})
    pipelines["cinematic"] = [{"kind": s.kind.value, "provider": s.provider} for s in sample]
    return {"pipelines": pipelines}


# ── Generate ──────────────────────────────────────────────────────────────────


@router.post("/generate")
def generate(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Estimate (confirm=false) or start (confirm=true) a media pipeline.

    Returns the cost estimate first; the caller must resend with `confirm=true`
    to actually spend. Over-budget submissions fail closed with HTTP 402.
    """
    pipeline = body.pipeline or body.kind
    if not pipeline:
        raise HTTPException(status_code=400, detail="Provide a 'pipeline' or a standalone 'kind'")

    # Strip reserved internal orchestration fields from untrusted input. `_`-prefixed
    # keys (`_source_key`, `_source_url`, `_depends_on`, …) are set by the orchestrator
    # itself; letting a caller inject them would bypass ownership checks and the SSRF
    # guard (e.g. a hand-set `_source_url`). Callers only supply real inputs.
    inbound = {k: v for k, v in (body.spec or {}).items() if not k.startswith("_")}

    # Resolve the source first (validates ownership + derives real duration) so the
    # estimate a caller confirms against reflects the actual source length, not a
    # fixed default. Idempotent — submit re-runs it harmlessly.
    try:
        spec = orchestrator.resolve_source(db, current_user.id, pipeline, inbound)
        est = orchestrator.estimate_pipeline(pipeline, spec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not body.confirm:
        return {"estimate": est, "confirmed": False}

    try:
        root = orchestrator.submit_pipeline(
            db,
            current_user.id,
            pipeline=pipeline,
            spec=spec,
            client_id=body.client_id,
            project_id=body.project_id,
        )
    except cost.BudgetExceededError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"estimate": est, "confirmed": True, "root_job": JobOut.model_validate(root)}


# ── Jobs ──────────────────────────────────────────────────────────────────────


@router.get("/jobs", response_model=List[JobOut])
def list_jobs(
    status: Optional[str] = None,
    pipeline: Optional[str] = None,
    run_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(MediaJob).filter(MediaJob.user_id == current_user.id)
    if status:
        q = q.filter(MediaJob.status == status)
    if pipeline:
        q = q.filter(MediaJob.pipeline == pipeline)
    if run_id:
        q = q.filter(MediaJob.pipeline_run_id == run_id)
    # Ascending by stage so a run reads in pipeline order.
    return q.order_by(MediaJob.stage_index.asc(), MediaJob.created_at.asc()).limit(200).all()


def _owned_job(db: Session, job_id: str, user_id: str) -> MediaJob:
    job = db.query(MediaJob).filter(MediaJob.id == job_id, MediaJob.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Media job not found")
    return job


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = _owned_job(db, job_id, current_user.id)
    assets = db.query(MediaAsset).filter(MediaAsset.job_id == job.id).all()
    detail = JobDetail.model_validate(job)
    detail.assets = [AssetOut.model_validate(a) for a in assets]
    return detail


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cancel one stage + its downstream dependents. To stop a whole cinematic run
    (its parallel clip/VO roots), use POST /runs/{run_id}/cancel."""
    job = _owned_job(db, job_id, current_user.id)
    if job.status in ("done", "failed", "canceled"):
        raise HTTPException(status_code=409, detail=f"Job already {job.status}")
    return orchestrator.cancel_job(db, job)


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cancel every non-terminal stage of a pipeline run (the explicit stop-the-run
    action). Owner-scoped; 404 if the run has no jobs owned by the caller."""
    owns = (
        db.query(MediaJob)
        .filter(MediaJob.pipeline_run_id == run_id, MediaJob.user_id == current_user.id)
        .first()
    )
    if not owns:
        raise HTTPException(status_code=404, detail="Run not found")
    canceled = orchestrator.cancel_run(db, run_id, current_user.id)
    return {"run_id": run_id, "canceled": canceled}


# ── Asset download ────────────────────────────────────────────────────────────


@router.get("/assets/{asset_id}/download")
def download_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Redirect to a short-lived signed URL for a produced asset (owner only).

    Assets live in object storage under a durable key; we never expose a permanent
    public link — each download mints a fresh time-limited signed URL.
    """
    asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == asset_id, MediaAsset.user_id == current_user.id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        url = get_storage().signed_url(asset.url)
    except StorageError as e:
        raise HTTPException(status_code=502, detail=f"Storage unavailable: {e}")
    return RedirectResponse(url)


@router.get("/assets/{asset_id}/url")
def asset_signed_url(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a fresh signed URL as JSON (owner only). For SPA/browser use, where an
    `<a href>` to the 302 /download endpoint can't carry the auth header."""
    asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == asset_id, MediaAsset.user_id == current_user.id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        return {"url": get_storage().signed_url(asset.url)}
    except StorageError as e:
        raise HTTPException(status_code=502, detail=f"Storage unavailable: {e}")


# ── Assemble ──────────────────────────────────────────────────────────────────


@router.post("/assemble", response_model=AssetOut, status_code=201)
def assemble(
    body: AssembleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        asset = orchestrator.assemble(db, current_user.id, body.asset_ids, mux_audio=body.mux_audio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    return asset


# ── Webhooks (async provider callbacks) ───────────────────────────────────────


@router.post("/webhooks/{provider}")
async def webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Ingest a signed provider completion callback (HMAC-verified)."""
    raw = await request.body()
    signature = request.headers.get("X-Media-Signature")
    if not orchestrator.verify_webhook_signature(raw, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(raw or b"{}")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    job = orchestrator.ingest_webhook(db, provider, payload, dict(request.headers))
    return {"accepted": job is not None, "job_id": job.id if job else None}


# ── Worker ────────────────────────────────────────────────────────────────────


@router.post("/process-due")
def process_due(
    limit: int = 25,
    db: Session = Depends(get_db),
    current_user=Depends(require_superuser),
):
    """Advance in-flight media jobs + retry recent failures. Call ~every minute
    from a scheduled worker (Render Cron Job) authenticated as an admin."""
    return orchestrator.process_due(db, limit=min(limit, 100))
