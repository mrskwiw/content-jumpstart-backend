"""
Integration tests for Phase 12 — P12.2 real providers + Supabase Storage.

No network: ElevenLabs, HeyGen, the Supabase Storage REST API, and the SSRF-guarded
asset download are all mocked (the repo norm — cf. test_analytics_collectors). Runs
OUTSIDE MEDIA_DRY_RUN so the real provider + storage code paths are exercised:

- ElevenLabs TTS (synchronous → bytes → Supabase upload)
- HeyGen avatar (async submit → poll → CDN URL → re-host to Supabase)
- talking-head chain (TTS audio injected into the HeyGen stage)
- Deliverable creation, HeyGen webhook ingest, fail-closed on missing creds.
"""

import hashlib
import hmac
import json


from backend.models import User
from backend.models.client import Client
from backend.models.deliverable import Deliverable
from backend.models.media import MediaJob
from backend.services.media.storage import StubStorage, SupabaseStorage, get_storage
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


# ── Mock HTTP harness ─────────────────────────────────────────────────────────


class _Resp:
    def __init__(self, *, status=200, json_body=None, content=b"", text=""):
        self.status_code = status
        self._json = {} if json_body is None else json_body
        self.content = content
        self.text = text
        self.headers = {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Stream:
    """Fake safe_stream_get context manager returning canned video bytes."""

    def __init__(self):
        self.content = b"VIDEOBYTES"
        self.headers = {"Content-Type": "video/mp4"}

    def raise_for_status(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_post(url, **kw):
    if "api.elevenlabs.io" in url:
        return _Resp(status=200, content=b"MP3BYTES")
    if "api.heygen.com/v2/video/generate" in url:
        return _Resp(status=200, json_body={"data": {"video_id": "hg_123"}})
    if "/storage/v1/object/sign/" in url:  # must precede the generic object check
        return _Resp(status=200, json_body={"signedURL": "/object/sign/media/x?token=t"})
    if "/storage/v1/object/" in url:  # upload
        return _Resp(status=200, json_body={"Key": "ok"})
    return _Resp(status=404, text=f"unmatched {url}")


def _fake_get(url, **kw):
    if "video_status.get" in url:
        return _Resp(
            status=200,
            json_body={
                "data": {
                    "status": "completed",
                    "video_url": "https://cdn.heygen.test/x.mp4",
                    "duration": 12,
                }
            },
        )
    return _Resp(status=404, text=f"unmatched {url}")


def _real_env(monkeypatch):
    """Non-dry-run with all provider + storage creds set."""
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el_key")  # pragma: allowlist secret
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_1")
    monkeypatch.setenv("HEYGEN_API_KEY", "hg_key")  # pragma: allowlist secret
    monkeypatch.setenv("HEYGEN_AVATAR_ID", "avatar_1")
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc_key")  # pragma: allowlist secret


def _patch_http(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "post", _fake_post)
    monkeypatch.setattr(requests, "get", _fake_get)
    monkeypatch.setattr(
        "backend.services.media.storage.safe_stream_get", lambda url, **kw: _Stream()
    )


# ── Storage backend selection ─────────────────────────────────────────────────


def test_get_storage_selects_backend(monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    assert isinstance(get_storage(), StubStorage)
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")  # pragma: allowlist secret
    assert isinstance(get_storage(), SupabaseStorage)


# ── ElevenLabs (synchronous) ──────────────────────────────────────────────────


def test_audio_only_elevenlabs_stores_audio(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    _patch_http(monkeypatch)
    u = _make_user(db_session, "tts@example.com", "user-tts")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "audio_only", "spec": {"script": "hello world"}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    root = r.json()["root_job"]
    # TTS is synchronous — the stage completes on submit.
    assert root["status"] == "done", root
    detail = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(u)).json()
    asset = detail["assets"][0]
    assert asset["mime"] == "audio/mpeg"
    assert asset["url"].endswith(".mp3")
    assert asset["url"].startswith(f"media/{u.id}/")


def test_real_provider_missing_key_fails_closed(client, db_session, monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    u = _make_user(db_session, "nokey@example.com", "user-nokey")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "audio_only", "spec": {"script": "x"}, "confirm": True},
        headers=_hdr(u),
    )
    root = r.json()["root_job"]
    assert root["status"] == "failed"
    assert "ELEVENLABS_API_KEY" in (root["error_message"] or "")


# ── HeyGen (asynchronous) + full chain ────────────────────────────────────────


def test_talking_head_chain_stores_video(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    _patch_http(monkeypatch)
    u = _make_user(db_session, "th@example.com", "user-th")
    admin = _make_user(db_session, "th-adm@example.com", "user-thadm", is_superuser=True)

    r = client.post(
        "/api/media/generate",
        json={"pipeline": "talking_head", "spec": {"script": "hello"}, "confirm": True},
        headers=_hdr(u),
    )
    root = r.json()["root_job"]
    assert root["status"] == "done"  # stage 0 (TTS) done on submit

    # Worker drives the async HeyGen stage: submit → poll(completed) → re-host.
    client.post("/api/media/process-due", headers=_hdr(admin))

    jobs = client.get("/api/media/jobs?pipeline=talking_head", headers=_hdr(u)).json()
    assert len(jobs) == 2 and all(j["status"] == "done" for j in jobs)
    last = next(j for j in jobs if j["stage_index"] == 1)
    detail = client.get(f"/api/media/jobs/{last['id']}", headers=_hdr(u)).json()
    assert detail["assets"][0]["mime"] == "video/mp4"
    assert detail["assets"][0]["url"].endswith(".mp4")


def test_deliverable_created_for_client(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    _patch_http(monkeypatch)
    u = _make_user(db_session, "deliv@example.com", "user-deliv")
    admin = _make_user(db_session, "deliv-adm@example.com", "user-delivadm", is_superuser=True)
    db_session.add(Client(id="client-1", user_id=u.id, name="Acme"))
    db_session.commit()

    client.post(
        "/api/media/generate",
        json={
            "pipeline": "talking_head",
            "spec": {"script": "hi"},
            "client_id": "client-1",
            "confirm": True,
        },
        headers=_hdr(u),
    )
    client.post("/api/media/process-due", headers=_hdr(admin))

    delivs = db_session.query(Deliverable).filter(Deliverable.client_id == "client-1").all()
    assert len(delivs) == 1
    assert delivs[0].format == "video"
    assert delivs[0].status == "ready"


def test_heygen_webhook_completes_job(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    _patch_http(monkeypatch)
    monkeypatch.setenv("MEDIA_WEBHOOK_SECRET", "whsec")  # pragma: allowlist secret
    u = _make_user(db_session, "wh2@example.com", "user-wh2")
    db_session.add(
        MediaJob(
            id="hgjob",
            user_id=u.id,
            kind="avatar_video",
            provider="heygen",
            status="processing",
            external_id="hg_x",
            input_json="{}",
        )
    )
    db_session.commit()

    body = json.dumps(
        {
            "event_type": "avatar_video.success",
            "event_data": {
                "video_id": "hg_x",
                "status": "completed",
                "video_url": "https://cdn.heygen.test/x.mp4",
                "duration": 10,
            },
        }
    ).encode("utf-8")
    sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()

    r = client.post(
        "/api/media/webhooks/heygen",
        content=body,
        headers={"X-Media-Signature": sig, "Content-Type": "application/json"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["accepted"] is True
    job = db_session.get(MediaJob, "hgjob")
    assert job.status == "done"


def test_storage_error_makes_stage_retryable(client, db_session, monkeypatch):
    """If the storage upload fails, the stage goes back to failed (retryable), not lost."""
    _real_env(monkeypatch)
    import requests

    def failing_post(url, **kw):
        if "/storage/v1/object/" in url and "/sign/" not in url:
            return _Resp(status=500, text="boom")
        return _fake_post(url, **kw)

    monkeypatch.setattr(requests, "post", failing_post)
    monkeypatch.setattr(requests, "get", _fake_get)
    u = _make_user(db_session, "sterr@example.com", "user-sterr")
    r = client.post(
        "/api/media/generate",
        json={"pipeline": "audio_only", "spec": {"script": "x"}, "confirm": True},
        headers=_hdr(u),
    )
    root = r.json()["root_job"]
    assert root["status"] == "failed"
    assert "storage" in (root["error_message"] or "").lower()
    assert root["retry_count"] == 1  # transient → retryable, not terminal
