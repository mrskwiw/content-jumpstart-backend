"""
Unit tests for durable media storage (Phase 12 P12.2) — backend resolution and the
`signed_url_for` trust boundary.

No network: SupabaseStorage's HTTP methods are exercised elsewhere via the media
integration tests; here we pin the resolution logic (`get_storage`), the dry-run /
stub behavior, the fail-closed config guard, and the r3 security rule that
`signed_url_for` refuses an already-absolute URL (open-redirect / SSRF guard).
"""

import pytest

from backend.services.media import storage
from backend.services.media.storage import (
    StorageError,
    StubStorage,
    get_storage,
    signed_url_for,
)


# ── StubStorage (no network) ──────────────────────────────────────────────────


def test_stub_put_bytes_reports_size_and_stub_signed_url():
    s = StubStorage()
    obj = s.put_bytes(b"hello", "media/u/j/a.mp3", "audio/mpeg")
    assert obj.key == "media/u/j/a.mp3" and obj.size_bytes == 5 and obj.mime == "audio/mpeg"
    assert s.signed_url("media/u/j/a.mp3").startswith("https://stub.local/media/")


def test_stub_put_from_url_does_not_fetch():
    obj = StubStorage().put_from_url("https://provider/x.mp4", "media/u/j/a.mp4", mime="video/mp4")
    assert obj.key == "media/u/j/a.mp4" and obj.size_bytes is None


# ── get_storage() resolution ──────────────────────────────────────────────────


def test_get_storage_dry_run_is_stub(monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    assert isinstance(get_storage(), StubStorage)


def test_get_storage_explicit_stub_backend(monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("MEDIA_STORAGE_BACKEND", "stub")
    assert isinstance(get_storage(), StubStorage)
    monkeypatch.setenv("MEDIA_STORAGE_BACKEND", "none")
    assert isinstance(get_storage(), StubStorage)


def test_get_storage_unknown_backend_raises(monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("MEDIA_STORAGE_BACKEND", "wasabi")
    with pytest.raises(StorageError, match="Unknown MEDIA_STORAGE_BACKEND"):
        get_storage()


def test_supabase_backend_unconfigured_fails_closed(monkeypatch):
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("MEDIA_STORAGE_BACKEND", "supabase")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(StorageError, match="not configured"):
        get_storage()


# ── signed_url_for trust boundary (r3 security fix) ───────────────────────────


@pytest.mark.parametrize("bad", ["http://evil.example/x", "https://provider.cdn/asset.mp4"])
def test_signed_url_for_rejects_absolute_urls(bad):
    """An absolute value in place of a storage key is a data-integrity/SSRF risk —
    refuse it loudly rather than serving it verbatim."""
    with pytest.raises(StorageError, match="non-storage asset URL"):
        signed_url_for(bad)


def test_signed_url_for_signs_a_storage_key(monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")  # → StubStorage, no network
    url = signed_url_for("media/u/j/a.mp4")
    assert url == "https://stub.local/media/media/u/j/a.mp4"


def test_signed_url_for_uses_resolved_backend(monkeypatch):
    """The key is passed through to whatever backend get_storage() resolves."""
    captured = {}

    class _Spy(StubStorage):
        def signed_url(self, key, *, expires_s=3600):
            captured["key"] = key
            captured["expires_s"] = expires_s
            return "https://signed/ok"

    monkeypatch.setattr(storage, "get_storage", lambda: _Spy())
    assert signed_url_for("media/u/j/a.mp4", expires_s=120) == "https://signed/ok"
    assert captured == {"key": "media/u/j/a.mp4", "expires_s": 120}
