"""
Integration tests for Phase 12 — Media Generation (P12.1 backbone).

Exercises the full estimate → confirm → submit → poll → chain lifecycle via the
dry-run StubProvider, the superuser `process-due` worker, DAG chaining across
pipeline stages, the budget gate (HTTP 402), fail-closed behaviour without
dry-run, per-user ownership, cancellation, webhook HMAC verification, and manual
assembly. No real provider is ever contacted.
"""

from backend.models import User
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
    db.refresh(u)
    return u


def _hdr(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def _dry_run(monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")


# ── Pipelines & estimation ────────────────────────────────────────────────────


def test_list_pipelines(client, db_session):
    r = client.get("/api/media/pipelines")
    assert r.status_code == 200, r.text
    pipelines = r.json()["pipelines"]
    assert "talking_head" in pipelines and "cinematic" in pipelines
    # talking_head is TTS → avatar.
    kinds = [s["kind"] for s in pipelines["talking_head"]]
    assert kinds == ["tts", "avatar_video"]


def test_estimate_without_confirm_does_not_submit(client, db_session, monkeypatch):
    u = _make_user(db_session, "media-est@example.com", "user-mediaest")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "cinematic", "spec": {"prompt": "a sunset"}, "confirm": False},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["confirmed"] is False
    assert body["estimate"]["total_cost_cents"] > 0
    # Nothing was created.
    assert client.get("/api/media/jobs", headers=_hdr(u)).json() == []


def test_unknown_pipeline_400(client, db_session):
    u = _make_user(db_session, "media-unk@example.com", "user-mediaunk")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "nope", "spec": {}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 400, r.text


# ── Submit → worker → chain ───────────────────────────────────────────────────


def test_generate_and_process_due_completes_pipeline(client, db_session, monkeypatch):
    _dry_run(monkeypatch)
    user = _make_user(db_session, "media-gen@example.com", "user-mediagen")
    admin = _make_user(db_session, "media-admin@example.com", "user-mediaadmin", is_superuser=True)

    r = client.post(
        "/api/media/generate",
        json={"pipeline": "talking_head", "spec": {"script": "hello"}, "confirm": True},
        headers=_hdr(user),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["confirmed"] is True
    root = body["root_job"]
    # Stage 0 was submitted to the stub and is now in flight.
    assert root["status"] == "processing"
    assert root["external_id"]

    # The worker (superuser) drives every user's in-flight jobs to completion.
    proc = client.post("/api/media/process-due", headers=_hdr(admin))
    assert proc.status_code == 200, proc.text

    jobs = client.get("/api/media/jobs?pipeline=talking_head", headers=_hdr(user)).json()
    assert len(jobs) == 2
    assert all(j["status"] == "done" for j in jobs)

    # The last stage produced a `final` asset; earlier stages produced clips.
    last = next(j for j in jobs if j["stage_index"] == 1)
    detail = client.get(f"/api/media/jobs/{last['id']}", headers=_hdr(user)).json()
    assert detail["assets"]
    asset = detail["assets"][0]
    assert asset["kind"] == "final"
    # url is now a durable storage key; the download endpoint mints a signed URL.
    assert asset["url"].startswith("media/")
    dl = client.get(
        f"/api/media/assets/{asset['id']}/download",
        headers=_hdr(user),
        follow_redirects=False,
    )
    assert dl.status_code in (302, 307)
    assert "stub.local" in dl.headers["location"]
    # JSON variant for the SPA (a link can't carry the auth header).
    signed = client.get(f"/api/media/assets/{asset['id']}/url", headers=_hdr(user))
    assert signed.status_code == 200
    assert "stub.local" in signed.json()["url"]


def test_generate_over_budget_returns_402(client, db_session, monkeypatch):
    _dry_run(monkeypatch)
    monkeypatch.setenv("MEDIA_MAX_JOB_COST_CENTS", "1")  # anything real is over budget
    user = _make_user(db_session, "media-budget@example.com", "user-mediabudget")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "cinematic", "spec": {"prompt": "expensive"}, "confirm": True},
        headers=_hdr(user),
    )
    assert r.status_code == 402, r.text
    # Fail-closed: no jobs created.
    assert client.get("/api/media/jobs", headers=_hdr(user)).json() == []


def test_fail_closed_without_dry_run(client, db_session, monkeypatch):
    # A real provider without credentials fails closed (no silent fallback). The
    # cinematic clip stage (kling) fails at submit; the terminal stage stays waiting.
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.delenv("KLING_API_KEY", raising=False)
    user = _make_user(db_session, "media-real@example.com", "user-mediareal")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "cinematic", "spec": {"prompt": "x"}, "confirm": True},
        headers=_hdr(user),
    )
    assert r.status_code == 200, r.text
    jobs = client.get("/api/media/jobs?pipeline=cinematic", headers=_hdr(user)).json()
    clip = next(j for j in jobs if j["kind"] == "gen_clip")
    assert clip["status"] == "failed"
    assert "KLING_API_KEY" in (clip["error_message"] or "")


# ── Ownership, cancel ─────────────────────────────────────────────────────────


def test_job_not_visible_to_other_user(client, db_session, monkeypatch):
    _dry_run(monkeypatch)
    owner = _make_user(db_session, "media-own@example.com", "user-mediaown")
    other = _make_user(db_session, "media-oth@example.com", "user-mediaoth")
    root = client.post(
        "/api/media/generate",
        json={"pipeline": "audio_only", "spec": {"script": "x"}, "confirm": True},
        headers=_hdr(owner),
    ).json()["root_job"]
    r = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(other))
    assert r.status_code == 404


def test_cancel_job(client, db_session, monkeypatch):
    _dry_run(monkeypatch)
    user = _make_user(db_session, "media-cancel@example.com", "user-mediacancel")
    root = client.post(
        "/api/media/generate",
        json={"pipeline": "audio_only", "spec": {"script": "x"}, "confirm": True},
        headers=_hdr(user),
    ).json()["root_job"]
    c = client.post(f"/api/media/jobs/{root['id']}/cancel", headers=_hdr(user))
    assert c.status_code == 200, c.text
    assert c.json()["status"] == "canceled"
    # Cancelling a terminal job conflicts.
    again = client.post(f"/api/media/jobs/{root['id']}/cancel", headers=_hdr(user))
    assert again.status_code == 409


# ── Webhooks ──────────────────────────────────────────────────────────────────


def test_webhook_bad_signature_rejected(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_WEBHOOK_SECRET", "shh")  # pragma: allowlist secret
    r = client.post(
        "/api/media/webhooks/heygen",
        json={"external_id": "whatever"},
        headers={"X-Media-Signature": "wrong"},
    )
    assert r.status_code == 401, r.text


def test_webhook_fails_closed_without_secret_in_prod(client, db_session, monkeypatch):
    # No secret + not dev/dry-run == misconfiguration; reject rather than trust.
    monkeypatch.delenv("MEDIA_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.delenv("DEBUG_MODE", raising=False)
    r = client.post("/api/media/webhooks/heygen", json={"external_id": "x"})
    assert r.status_code == 401, r.text


def test_webhook_no_secret_completes_job(client, db_session, monkeypatch):
    _dry_run(monkeypatch)
    monkeypatch.delenv("MEDIA_WEBHOOK_SECRET", raising=False)
    user = _make_user(db_session, "media-wh@example.com", "user-mediawh")
    root = client.post(
        "/api/media/generate",
        json={"pipeline": "audio_only", "spec": {"script": "x"}, "confirm": True},
        headers=_hdr(user),
    ).json()["root_job"]

    r = client.post(
        "/api/media/webhooks/stub",
        json={"external_id": root["external_id"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["accepted"] is True

    detail = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(user)).json()
    assert detail["status"] == "done"


# ── Assemble ──────────────────────────────────────────────────────────────────


def test_assemble_dry_run_and_ownership(client, db_session, monkeypatch):
    _dry_run(monkeypatch)
    user = _make_user(db_session, "media-asm@example.com", "user-mediaasm")
    other = _make_user(db_session, "media-asm2@example.com", "user-mediaasm2")
    admin = _make_user(
        db_session, "media-asm-adm@example.com", "user-mediaasmadm", is_superuser=True
    )

    client.post(
        "/api/media/generate",
        json={"pipeline": "talking_head", "spec": {"script": "hi"}, "confirm": True},
        headers=_hdr(user),
    )
    client.post("/api/media/process-due", headers=_hdr(admin))

    # Collect a produced asset id.
    jobs = client.get("/api/media/jobs", headers=_hdr(user)).json()
    detail = client.get(f"/api/media/jobs/{jobs[0]['id']}", headers=_hdr(user)).json()
    asset_id = detail["assets"][0]["id"]

    ok = client.post("/api/media/assemble", json={"asset_ids": [asset_id]}, headers=_hdr(user))
    assert ok.status_code == 201, ok.text
    assert ok.json()["kind"] == "final"

    # Another user cannot assemble assets they don't own.
    denied = client.post("/api/media/assemble", json={"asset_ids": [asset_id]}, headers=_hdr(other))
    assert denied.status_code == 400


# ── Worker authz ──────────────────────────────────────────────────────────────


def test_process_due_requires_superuser(client, db_session):
    u = _make_user(db_session, "media-noadm@example.com", "user-medianoadm")
    r = client.post("/api/media/process-due", headers=_hdr(u))
    assert r.status_code == 403
