"""
Integration tests for Phase 12 P12.4 — standalone audio utilities.

Voice Isolator (A1, sync), Auphonic master (A2, async), Dubbing (B3, async),
exposed via /api/media/generate with `kind=`. Standalone ops require an OWNED
source asset (source_asset_id) — never a raw external URL (SSRF + duration safety).
Budget is derived from the source's real duration. No network.
"""

from backend.models import User
from backend.models.media import MediaAsset, MediaJob
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


def _add_source(db, user_id, asset_id, duration_s=60):
    """Create an owned source MediaAsset (+ its producing job) to process."""
    jid = f"job-{asset_id}"
    db.add(
        MediaJob(
            id=jid,
            user_id=user_id,
            kind="tts",
            provider="stub",
            status="done",
            pipeline_run_id=f"run-{asset_id}",
        )
    )
    db.add(
        MediaAsset(
            id=asset_id,
            user_id=user_id,
            job_id=jid,
            kind="final",
            url=f"media/{user_id}/{jid}/{asset_id}.mp3",
            mime="audio/mpeg",
            duration_s=duration_s,
        )
    )
    db.commit()


class _Resp:
    def __init__(self, *, status=200, json_body=None, content=b"", text=""):
        self.status_code = status
        self._json = {} if json_body is None else json_body
        self.content = content
        self.text = text

    def json(self):
        return self._json


class _Stream:
    def __init__(self, content=b"AUDIO"):
        self.content = content
        self.headers = {"Content-Type": "audio/mpeg"}

    def raise_for_status(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# ── Dry-run standalone ops via kind= ──────────────────────────────────────────


def test_standalone_audio_ops_dry_run(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "aud@example.com", "user-aud")
    admin = _make_user(db_session, "aud-adm@example.com", "user-audadm", is_superuser=True)

    for i, (kind, extra) in enumerate(
        [("audio_clean", {}), ("audio_master", {}), ("dub", {"target_lang": "es"})]
    ):
        _add_source(db_session, u.id, f"src{i}")
        r = client.post(
            "/api/media/generate",
            json={"kind": kind, "spec": {"source_asset_id": f"src{i}", **extra}, "confirm": True},
            headers=_hdr(u),
        )
        assert r.status_code == 200, (kind, r.text)
        root = r.json()["root_job"]
        assert root["pipeline"] == kind
        client.post("/api/media/process-due", headers=_hdr(admin))
        detail = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(u)).json()
        assert detail["status"] == "done", (kind, detail)
        assert detail["assets"][0]["mime"].startswith("audio")


def test_standalone_audio_requires_owned_source(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "nosrc@example.com", "user-nosrc")
    # No source at all → 400.
    r = client.post(
        "/api/media/generate",
        json={"kind": "audio_clean", "spec": {}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 400 and "source_asset_id" in r.json()["detail"]
    # A raw external URL is rejected (SSRF / duration safety).
    r2 = client.post(
        "/api/media/generate",
        json={
            "kind": "audio_clean",
            "spec": {"source_url": "https://evil.example/x.mp3"},
            "confirm": True,
        },
        headers=_hdr(u),
    )
    assert r2.status_code == 400 and "source_asset_id" in r2.json()["detail"]


def test_source_asset_ownership(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "owner@example.com", "user-owner")
    other = _make_user(db_session, "other@example.com", "user-other")
    _add_source(db_session, u.id, "owned")
    ok = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "owned"}, "confirm": True},
        headers=_hdr(u),
    )
    assert ok.status_code == 200, ok.text
    denied = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "owned"}, "confirm": True},
        headers=_hdr(other),
    )
    assert denied.status_code == 400 and "not found or not owned" in denied.json()["detail"].lower()


def test_generate_requires_pipeline_or_kind(client, db_session):
    u = _make_user(db_session, "neither@example.com", "user-neither")
    r = client.post("/api/media/generate", json={"spec": {}, "confirm": False}, headers=_hdr(u))
    assert r.status_code == 400


# ── Budget uses REAL source duration (no under-pricing bypass) ────────────────


def test_budget_uses_real_source_duration(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    monkeypatch.setenv("MEDIA_MAX_JOB_COST_CENTS", "100")
    u = _make_user(db_session, "dur@example.com", "user-dur")

    # A 2-hour master (auphonic 0.3¢/s × 7200 = 2160¢) blows the 100¢ cap → 402.
    _add_source(db_session, u.id, "long", duration_s=7200)
    over = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "long"}, "confirm": True},
        headers=_hdr(u),
    )
    assert over.status_code == 402

    # A 60s master (18¢) fits.
    _add_source(db_session, u.id, "short", duration_s=60)
    ok = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "short"}, "confirm": True},
        headers=_hdr(u),
    )
    assert ok.status_code == 200, ok.text


def test_unknown_duration_priced_high(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    monkeypatch.setenv("MEDIA_MAX_JOB_COST_CENTS", "100")
    u = _make_user(db_session, "unk@example.com", "user-unk")
    # duration unknown → fail-safe high default → over the cap (not under-priced).
    _add_source(db_session, u.id, "nodur", duration_s=None)
    r = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "nodur"}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 402


# ── Real (mocked) provider paths ──────────────────────────────────────────────


def _real_env(monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")  # pragma: allowlist secret
    monkeypatch.setenv("AUPHONIC_API_KEY", "au")  # pragma: allowlist secret
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")  # pragma: allowlist secret


def _storage_post(url):
    if "/storage/v1/object/sign/" in url:
        return _Resp(status=200, json_body={"signedURL": "/object/sign/media/x?token=t"})
    if "/storage/v1/object/" in url:
        return _Resp(status=200, json_body={"Key": "ok"})
    return None


def test_isolator_real_mocked(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    import requests

    def fake_post(url, **kw):
        if "audio-isolation" in url:
            return _Resp(status=200, content=b"CLEANED")
        return _storage_post(url) or _Resp(status=404, text=url)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(
        "backend.services.distribution.net_guard.safe_stream_get", lambda url, **kw: _Stream()
    )
    u = _make_user(db_session, "iso@example.com", "user-iso")
    _add_source(db_session, u.id, "isosrc")
    r = client.post(
        "/api/media/generate",
        json={"kind": "audio_clean", "spec": {"source_asset_id": "isosrc"}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    assert r.json()["root_job"]["status"] == "done"  # synchronous
    detail = client.get(f"/api/media/jobs/{r.json()['root_job']['id']}", headers=_hdr(u)).json()
    assert detail["assets"][0]["mime"] == "audio/mpeg"


def test_auphonic_real_mocked(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    import requests

    def fake_post(url, **kw):
        if "auphonic.com/api/simple/productions" in url:
            return _Resp(status=200, json_body={"data": {"uuid": "prod1"}})
        return _storage_post(url) or _Resp(status=404, text=url)

    def fake_get(url, **kw):
        if "auphonic.com/api/production/" in url:
            return _Resp(
                status=200,
                json_body={
                    "data": {
                        "status_string": "Done",
                        "output_files": [{"download_url": "https://au/out.mp3"}],
                    }
                },
            )
        return _Resp(status=404)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(
        "backend.services.media.storage.safe_stream_get", lambda url, **kw: _Stream()
    )
    u = _make_user(db_session, "auph@example.com", "user-auph")
    admin = _make_user(db_session, "auph-adm@example.com", "user-auphadm", is_superuser=True)
    _add_source(db_session, u.id, "auphsrc")
    r = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "auphsrc"}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    assert r.json()["root_job"]["status"] == "processing"  # async
    client.post("/api/media/process-due", headers=_hdr(admin))
    detail = client.get(f"/api/media/jobs/{r.json()['root_job']['id']}", headers=_hdr(u)).json()
    assert detail["status"] == "done"
    assert detail["assets"][0]["mime"] == "audio/mpeg"


def test_dub_real_mocked(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    import requests

    def fake_post(url, **kw):
        if url.endswith("/dubbing"):
            return _Resp(status=200, json_body={"dubbing_id": "dub1"})
        return _storage_post(url) or _Resp(status=404, text=url)

    def fake_get(url, **kw):
        if "/audio/" in url:
            return _Resp(status=200, content=b"DUBBED")
        if "/dubbing/" in url:
            return _Resp(status=200, json_body={"status": "dubbed"})
        return _Resp(status=404)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)
    u = _make_user(db_session, "dub@example.com", "user-dub")
    admin = _make_user(db_session, "dub-adm@example.com", "user-dubadm", is_superuser=True)
    _add_source(db_session, u.id, "dubsrc")
    r = client.post(
        "/api/media/generate",
        json={
            "kind": "dub",
            "spec": {"source_asset_id": "dubsrc", "target_lang": "es"},
            "confirm": True,
        },
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    assert r.json()["root_job"]["status"] == "processing"  # async
    client.post("/api/media/process-due", headers=_hdr(admin))
    detail = client.get(f"/api/media/jobs/{r.json()['root_job']['id']}", headers=_hdr(u)).json()
    assert detail["status"] == "done"
    assert detail["assets"][0]["mime"] == "audio/mpeg"
