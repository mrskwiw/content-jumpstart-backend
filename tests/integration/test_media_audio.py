"""
Integration tests for Phase 12 P12.4 — standalone audio utilities.

Voice Isolator (A1, sync), Auphonic master (A2, async), Dubbing (B3, async),
exposed via /api/media/generate with `kind=`. Source resolution + ownership, and
the real (mocked) provider paths. No network.
"""

from backend.models import User
from backend.models.media import MediaAsset, MediaJob
from backend.utils.auth import create_access_token, get_password_hash

PW = "Zx9!qWmp7Kt#"  # pragma: allowlist secret
SRC = "https://example.com/in.mp3"


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

    cases = [("audio_clean", {}), ("audio_master", {}), ("dub", {"target_lang": "es"})]
    for kind, extra in cases:
        r = client.post(
            "/api/media/generate",
            json={"kind": kind, "spec": {"source_url": SRC, **extra}, "confirm": True},
            headers=_hdr(u),
        )
        assert r.status_code == 200, (kind, r.text)
        root = r.json()["root_job"]
        assert root["pipeline"] == kind
        client.post("/api/media/process-due", headers=_hdr(admin))
        detail = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(u)).json()
        assert detail["status"] == "done", (kind, detail)
        assert detail["assets"][0]["mime"].startswith("audio")


def test_standalone_audio_requires_source(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "nosrc@example.com", "user-nosrc")
    r = client.post(
        "/api/media/generate",
        json={"kind": "audio_clean", "spec": {}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 400
    assert "source" in r.json()["detail"].lower()


def test_generate_requires_pipeline_or_kind(client, db_session):
    u = _make_user(db_session, "neither@example.com", "user-neither")
    r = client.post("/api/media/generate", json={"spec": {}, "confirm": False}, headers=_hdr(u))
    assert r.status_code == 400


# ── Source asset ownership ────────────────────────────────────────────────────


def test_standalone_audio_source_asset_ownership(client, db_session, monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    u = _make_user(db_session, "srcowner@example.com", "user-srcowner")
    other = _make_user(db_session, "srcother@example.com", "user-srcother")
    db_session.add(
        MediaJob(
            id="j0", user_id=u.id, kind="tts", provider="stub", status="done", pipeline_run_id="r0"
        )
    )
    db_session.add(
        MediaAsset(id="a0", user_id=u.id, job_id="j0", kind="final", url="media/u/j0/a0.mp3")
    )
    db_session.commit()

    # Owner can master their own asset.
    ok = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "a0"}, "confirm": True},
        headers=_hdr(u),
    )
    assert ok.status_code == 200, ok.text
    # Another user cannot reference it.
    denied = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_asset_id": "a0"}, "confirm": True},
        headers=_hdr(other),
    )
    assert denied.status_code == 400
    assert "not found or not owned" in denied.json()["detail"].lower()


# ── Real (mocked) provider paths ──────────────────────────────────────────────


def _real_env(monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")  # pragma: allowlist secret
    monkeypatch.setenv("AUPHONIC_API_KEY", "au")  # pragma: allowlist secret
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")  # pragma: allowlist secret


def test_isolator_real_mocked(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    import requests

    def fake_post(url, **kw):
        if "audio-isolation" in url:
            return _Resp(status=200, content=b"CLEANED")
        if "/storage/v1/object/sign/" in url:
            return _Resp(status=200, json_body={"signedURL": "/object/sign/media/x?token=t"})
        if "/storage/v1/object/" in url:
            return _Resp(status=200, json_body={"Key": "ok"})
        return _Resp(status=404, text=f"unmatched {url}")

    monkeypatch.setattr(requests, "post", fake_post)
    # The isolator downloads the source via net_guard, then uploads it.
    monkeypatch.setattr(
        "backend.services.distribution.net_guard.safe_stream_get", lambda url, **kw: _Stream()
    )
    u = _make_user(db_session, "iso@example.com", "user-iso")
    r = client.post(
        "/api/media/generate",
        json={"kind": "audio_clean", "spec": {"source_url": SRC}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    root = r.json()["root_job"]
    assert root["status"] == "done"  # isolator is synchronous
    detail = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(u)).json()
    assert detail["assets"][0]["mime"] == "audio/mpeg"


def test_auphonic_real_mocked(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    import requests

    def fake_post(url, **kw):
        if "auphonic.com/api/simple/productions" in url:
            return _Resp(status=200, json_body={"data": {"uuid": "prod1"}})
        if "/storage/v1/object/sign/" in url:
            return _Resp(status=200, json_body={"signedURL": "/object/sign/media/x?token=t"})
        if "/storage/v1/object/" in url:
            return _Resp(status=200, json_body={"Key": "ok"})
        return _Resp(status=404, text=f"unmatched {url}")

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
    r = client.post(
        "/api/media/generate",
        json={"kind": "audio_master", "spec": {"source_url": SRC}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    root = r.json()["root_job"]
    assert root["status"] == "processing"  # async
    client.post("/api/media/process-due", headers=_hdr(admin))
    detail = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(u)).json()
    assert detail["status"] == "done"
    assert detail["assets"][0]["mime"] == "audio/mpeg"


def test_dub_real_mocked(client, db_session, monkeypatch):
    _real_env(monkeypatch)
    import requests

    def fake_post(url, **kw):
        if url.endswith("/dubbing"):
            return _Resp(status=200, json_body={"dubbing_id": "dub1"})
        if "/storage/v1/object/sign/" in url:
            return _Resp(status=200, json_body={"signedURL": "/object/sign/media/x?token=t"})
        if "/storage/v1/object/" in url:
            return _Resp(status=200, json_body={"Key": "ok"})
        return _Resp(status=404, text=f"unmatched {url}")

    def fake_get(url, **kw):
        if "/audio/" in url:  # dubbed audio bytes — check before the status url
            return _Resp(status=200, content=b"DUBBED")
        if "/dubbing/" in url:
            return _Resp(status=200, json_body={"status": "dubbed"})
        return _Resp(status=404)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)
    u = _make_user(db_session, "dub@example.com", "user-dub")
    admin = _make_user(db_session, "dub-adm@example.com", "user-dubadm", is_superuser=True)
    r = client.post(
        "/api/media/generate",
        json={"kind": "dub", "spec": {"source_url": SRC, "target_lang": "es"}, "confirm": True},
        headers=_hdr(u),
    )
    assert r.status_code == 200, r.text
    root = r.json()["root_job"]
    assert root["status"] == "processing"  # async
    client.post("/api/media/process-due", headers=_hdr(admin))
    detail = client.get(f"/api/media/jobs/{root['id']}", headers=_hdr(u)).json()
    assert detail["status"] == "done"
    assert detail["assets"][0]["mime"] == "audio/mpeg"
