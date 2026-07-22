"""
Unit tests for Phase 12 P12.2 real providers — error/edge branches.

Direct provider calls with mocked `requests` (no DB, no app). Covers the failure
paths the happy-path integration tests don't: missing creds/inputs, HTTP errors,
network exceptions, HeyGen still-processing / failed states, and webhook fail events.
"""

from backend.services.media.providers import (
    ElevenLabsTTSProvider,
    HeyGenProvider,
    MediaKind,
    NotImplementedProvider,
)


class _Resp:
    def __init__(self, *, status=200, json_body=None, content=b"", text=""):
        self.status_code = status
        self._json = {} if json_body is None else json_body
        self.content = content
        self.text = text

    def json(self):
        return self._json


def _patch(monkeypatch, *, post=None, get=None):
    import requests

    if post:
        monkeypatch.setattr(requests, "post", post)
    if get:
        monkeypatch.setattr(requests, "get", get)


# ── ElevenLabs ────────────────────────────────────────────────────────────────


def test_elevenlabs_missing_credential(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    r = ElevenLabsTTSProvider(MediaKind.TTS).start({"script": "hi"})
    assert not r.ok and "ELEVENLABS_API_KEY" in r.error


def test_elevenlabs_missing_voice_id(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    r = ElevenLabsTTSProvider(MediaKind.TTS).start({"script": "hi"})
    assert not r.ok and "voice_id" in r.error


def test_elevenlabs_missing_text(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    r = ElevenLabsTTSProvider(MediaKind.TTS).start({})
    assert not r.ok and ("script" in r.error.lower() or "text" in r.error.lower())


def test_elevenlabs_http_error(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=422, text="bad"))
    r = ElevenLabsTTSProvider(MediaKind.TTS).start({"script": "hi"})
    assert not r.ok and "422" in r.error


def test_elevenlabs_network_exception(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")

    def boom(url, **kw):
        raise RuntimeError("net down")

    _patch(monkeypatch, post=boom)
    r = ElevenLabsTTSProvider(MediaKind.TTS).start({"script": "hi"})
    assert not r.ok and "net down" in r.error


# ── HeyGen ────────────────────────────────────────────────────────────────────


def test_heygen_missing_avatar(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.delenv("HEYGEN_AVATAR_ID", raising=False)
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).start({"script": "hi"})
    assert not r.ok and "avatar_id" in r.error


def test_heygen_start_text_voice_http_error(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.setenv("HEYGEN_AVATAR_ID", "a")
    monkeypatch.setenv("HEYGEN_VOICE_ID", "v")
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=400, text="nope"))
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).start({"script": "hi"})  # text-voice branch
    assert not r.ok and "400" in r.error


def test_heygen_start_no_video_id(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.setenv("HEYGEN_AVATAR_ID", "a")
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={"data": {}}))
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).start({"voice_id": "v", "script": "hi"})
    assert not r.ok and "video_id" in r.error


def test_heygen_start_audio_branch_success(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.setenv("HEYGEN_AVATAR_ID", "a")
    _patch(
        monkeypatch,
        post=lambda url, **kw: _Resp(status=200, json_body={"data": {"video_id": "vv"}}),
    )
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).start({"_parent_asset_url": "https://x/a.mp3"})
    assert r.ok and r.external_id == "vv" and not r.done


def test_heygen_poll_processing(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(status=200, json_body={"data": {"status": "processing"}}),
    )
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).poll("vv")
    assert r.ok and not r.done


def test_heygen_poll_http_error(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=500, text="err"))
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).poll("vv")
    assert not r.ok and "500" in r.error


def test_heygen_poll_exception(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret

    def boom(url, **kw):
        raise RuntimeError("down")

    _patch(monkeypatch, get=boom)
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).poll("vv")
    assert not r.ok and "down" in r.error


def test_heygen_missing_credential(monkeypatch):
    monkeypatch.delenv("HEYGEN_API_KEY", raising=False)
    assert not HeyGenProvider(MediaKind.AVATAR_VIDEO).poll("x").ok


def test_heygen_webhook_fail_event():
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).parse_webhook(
        {"event_type": "avatar_video.fail", "event_data": {"video_id": "vv", "msg": "boom"}}, {}
    )
    assert not r.ok and "boom" in r.error


def test_heygen_status_failed_and_success():
    p = HeyGenProvider(MediaKind.AVATAR_VIDEO)
    assert not p._from_status("vv", {"status": "failed", "error": "x"}).ok
    done = p._from_status(
        "vv", {"status": "completed", "video_url": "https://c/x.mp4", "duration": 5}
    )
    assert done.ok and done.done and done.asset_url.endswith(".mp4")


# ── NotImplementedProvider (still-unwired names) ──────────────────────────────


def test_not_implemented_poll_and_webhook():
    p = NotImplementedProvider(MediaKind.GEN_CLIP, "kling")
    assert not p.poll("x").ok
    assert not p.parse_webhook({}, {}).ok
