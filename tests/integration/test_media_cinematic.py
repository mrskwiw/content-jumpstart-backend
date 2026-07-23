"""
Integration tests for Phase 12 P12.3 — cinematic fan-in pipeline.

Covers the DAG shape (N clips → concat → mux with VO), dry-run completion, the
real (mocked) Kling + ffmpeg + ElevenLabs path, fan-in failure propagation, cost
scaling with clip count, and the Veo premium gate. No network / no real ffmpeg.
"""

from backend.models import User
from backend.models.media import MediaJob
from backend.services.media import orchestrator
from backend.services.media.providers import MediaKind, VeoProvider
from backend.utils.auth import create_access_token, get_password_hash

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret


def _make_user(db, email, uid, is_superuser=False):
    u = User(
        id=uid,
        email=email,
        hashed_password=get_password_hash(PW),
        full_name="Op",
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(u)
    db.commit()
    return u


def _hdr(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


# ── DAG shape & estimation ────────────────────────────────────────────────────


def test_cinematic_estimate_scales_with_clips():
    one = orchestrator.estimate_pipeline("cinematic", {"scenes": ["a"], "script": "hi"})
    three = orchestrator.estimate_pipeline("cinematic", {"scenes": ["a", "b", "c"], "script": "hi"})
    # More scenes → more clip stages → higher projected cost.
    assert len(three["stages"]) > len(one["stages"])
    assert three["total_cost_cents"] > one["total_cost_cents"]


def test_cinematic_dag_has_clips_vo_concat_mux():
    stages = orchestrator._build_cinematic({"scenes": ["a", "b"], "script": "hi"})
    kinds = [s.kind for s in stages]
    assert kinds.count(MediaKind.GEN_CLIP) == 2
    assert MediaKind.TTS in kinds
    assert kinds.count(MediaKind.ASSEMBLE) == 2  # concat + mux
    # The mux (last) depends on the concat and the VO.
    assert len(stages[-1].deps) == 2


# ── Dry-run completion ────────────────────────────────────────────────────────


def test_cinematic_dry_run_completes(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "cine@example.com", "user-cine")
    admin = _make_user(db_session, "cine-adm@example.com", "user-cineadm", is_superuser=True)

    r = client.post(
        "/api/media/generate",
        json={
            "pipeline": "cinematic",
            "spec": {"scenes": ["a", "b"], "script": "hi"},
            "confirm": True,
        },
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    run_id = r.json()["root_job"]["pipeline_run_id"]
    assert run_id

    client.post("/api/media/process-due", headers=_hdr(admin))

    jobs = client.get(f"/api/media/jobs?run_id={run_id}", headers=_hdr(u)).json()
    # 2 clips + VO + concat + mux = 5 stages.
    assert len(jobs) == 5, [(j["kind"], j["status"]) for j in jobs]
    assert all(j["status"] == "done" for j in jobs), [(j["kind"], j["status"]) for j in jobs]

    mux = [j for j in jobs if j["kind"] == "assemble"][-1]
    detail = client.get(f"/api/media/jobs/{mux['id']}", headers=_hdr(u)).json()
    assert detail["assets"][0]["kind"] == "final"


# ── Fan-in failure propagation ────────────────────────────────────────────────


def test_cinematic_clip_failure_fails_assembly(db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    _make_user(db_session, "cf@example.com", "user-cf")
    terminal = orchestrator.submit_pipeline(
        db_session, "user-cf", pipeline="cinematic", spec={"scenes": ["a", "b"], "script": "hi"}
    )
    run_id = terminal.pipeline_run_id

    # One clip fails terminally.
    clip = (
        db_session.query(MediaJob)
        .filter(MediaJob.pipeline_run_id == run_id, MediaJob.kind == "gen_clip")
        .first()
    )
    orchestrator._mark_failed(db_session, clip, "kling exploded", terminal=True)

    # The worker's fan-in sweep fails the stages that depend on the failed clip.
    orchestrator.process_due(db_session)

    assemblers = (
        db_session.query(MediaJob)
        .filter(MediaJob.pipeline_run_id == run_id, MediaJob.kind == "assemble")
        .all()
    )
    assert assemblers and all(a.status == "failed" for a in assemblers)
    # Nothing is left stranded in awaiting_dependency.
    stranded = (
        db_session.query(MediaJob)
        .filter(MediaJob.pipeline_run_id == run_id, MediaJob.status == "awaiting_dependency")
        .count()
    )
    assert stranded == 0


# ── Real (mocked) pipeline ────────────────────────────────────────────────────


class _Resp:
    def __init__(self, *, status=200, json_body=None, content=b"", text=""):
        self.status_code = status
        self._json = {} if json_body is None else json_body
        self.content = content
        self.text = text

    def json(self):
        return self._json


class _Stream:
    def __init__(self):
        self.content = b"CLIPBYTES"
        self.headers = {"Content-Type": "video/mp4"}

    def raise_for_status(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_cinematic_real_pipeline_mocked(client, db_session, monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("KLING_API_KEY", "kl")  # pragma: allowlist secret
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")  # pragma: allowlist secret
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")  # pragma: allowlist secret

    import requests

    def fake_post(url, **kw):
        if "klingai.com" in url:
            return _Resp(status=200, json_body={"data": {"task_id": "kt1"}})
        if "api.elevenlabs.io" in url:
            return _Resp(status=200, content=b"MP3")
        if "/storage/v1/object/sign/" in url:
            return _Resp(status=200, json_body={"signedURL": "/object/sign/media/x?token=t"})
        if "/storage/v1/object/" in url:
            return _Resp(status=200, json_body={"Key": "ok"})
        return _Resp(status=404, text=f"unmatched {url}")

    def fake_get(url, **kw):
        if "klingai.com" in url:
            return _Resp(
                status=200,
                json_body={
                    "data": {
                        "task_status": "succeed",
                        "task_result": {"videos": [{"url": "https://cdn.kling/x.mp4"}]},
                    }
                },
            )
        return _Resp(status=404)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(
        "backend.services.media.storage.safe_stream_get", lambda url, **kw: _Stream()
    )
    # FfmpegProvider downloads via net_guard and shells out — mock both.
    monkeypatch.setattr(
        "backend.services.distribution.net_guard.safe_stream_get", lambda url, **kw: _Stream()
    )
    monkeypatch.setattr(
        "backend.services.media.ffmpeg.run", lambda op, paths, audio_path=None: b"FINALVIDEO"
    )

    u = _make_user(db_session, "cre@example.com", "user-cre")
    admin = _make_user(db_session, "cre-adm@example.com", "user-creadm", is_superuser=True)
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "cinematic", "spec": {"scenes": ["a"], "script": "hi"}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    run_id = r.json()["root_job"]["pipeline_run_id"]

    client.post("/api/media/process-due", headers=_hdr(admin))

    jobs = client.get(f"/api/media/jobs?run_id={run_id}", headers=_hdr(u)).json()
    assert all(j["status"] == "done" for j in jobs), [(j["kind"], j["status"]) for j in jobs]
    mux = [j for j in jobs if j["kind"] == "assemble"][-1]
    detail = client.get(f"/api/media/jobs/{mux['id']}", headers=_hdr(u)).json()
    assert detail["assets"][0]["mime"] == "video/mp4"


# ── Veo premium gate ──────────────────────────────────────────────────────────


def test_veo_premium_gated_without_vertex(monkeypatch):
    monkeypatch.delenv("GOOGLE_VERTEX_PROJECT", raising=False)
    r = VeoProvider(MediaKind.GEN_CLIP).start({"prompt": "x"})
    assert not r.ok and "veo" in r.error.lower()


def test_cinematic_premium_rejected_up_front(client, db_session, monkeypatch):
    # Veo isn't callable yet, so quality=premium is rejected before jobs are created
    # (rather than accepted then dead-ended on every clip).
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "prem@example.com", "user-prem")
    r = client.post(
        "/api/media/generate",
        json={
            "pipeline": "cinematic",
            "spec": {"scenes": ["a"], "quality": "premium"},
            "confirm": False,
        },
        headers=_hdr(u),
    )
    assert r.status_code == 400
    assert "premium" in r.json()["detail"].lower() or "veo" in r.json()["detail"].lower()


# ── Run-scoped cancellation ───────────────────────────────────────────────────


def test_cinematic_run_cancel_stops_whole_run(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "cxl@example.com", "user-cxl")
    r = client.post(
        "/api/media/generate",
        json={
            "pipeline": "cinematic",
            "spec": {"scenes": ["a", "b"], "script": "hi"},
            "confirm": True,
        },
        headers=_hdr(u),
    )
    run_id = r.json()["root_job"]["pipeline_run_id"]

    # The explicit run-cancel stops every stage (clips + VO + assembly).
    c = client.post(f"/api/media/runs/{run_id}/cancel", headers=_hdr(u))
    assert c.status_code == 200, c.text
    assert c.json()["canceled"] >= 1

    jobs = client.get(f"/api/media/jobs?run_id={run_id}", headers=_hdr(u)).json()
    assert jobs and all(j["status"] == "canceled" for j in jobs), [
        (j["kind"], j["status"]) for j in jobs
    ]


def test_run_cancel_not_found_for_other_user(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "owner@example.com", "user-owner")
    other = _make_user(db_session, "other@example.com", "user-other")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "cinematic", "spec": {"scenes": ["a"], "script": "hi"}, "confirm": True},
        headers=_hdr(u),
    )
    run_id = r.json()["root_job"]["pipeline_run_id"]
    assert client.post(f"/api/media/runs/{run_id}/cancel", headers=_hdr(other)).status_code == 404


def test_stage_cancel_scoped_to_downstream(client, db_session, monkeypatch):
    """Canceling one clip cancels only it + the assembly that needs it, NOT the
    sibling clip or the VO (use run-cancel to stop the whole run)."""
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    _make_user(db_session, "stagecxl@example.com", "user-stagecxl")
    terminal = orchestrator.submit_pipeline(
        db_session,
        "user-stagecxl",
        pipeline="cinematic",
        spec={"scenes": ["a", "b"], "script": "hi"},
    )
    run_id = terminal.pipeline_run_id
    clips = (
        db_session.query(MediaJob)
        .filter(MediaJob.pipeline_run_id == run_id, MediaJob.kind == "gen_clip")
        .all()
    )
    orchestrator.cancel_job(db_session, clips[0])

    # The other clip and the VO are untouched.
    assert db_session.get(MediaJob, clips[1].id).status != "canceled"
    vo = (
        db_session.query(MediaJob)
        .filter(MediaJob.pipeline_run_id == run_id, MediaJob.kind == "tts")
        .first()
    )
    assert vo.status != "canceled"
    # The assemblers depend on the canceled clip → canceled downstream.
    assemblers = (
        db_session.query(MediaJob)
        .filter(MediaJob.pipeline_run_id == run_id, MediaJob.kind == "assemble")
        .all()
    )
    assert all(a.status == "canceled" for a in assemblers)
