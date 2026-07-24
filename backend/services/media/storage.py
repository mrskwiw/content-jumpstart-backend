"""
Durable media asset storage (Phase 12 — P12.2).

Provider CDN URLs expire, so a finished asset must be re-hosted somewhere durable.
This is a thin `MediaStorage` interface with one concrete backend today —
**Supabase Storage** (S3-backed object store, chosen 2026-07-22) — plus a
no-network `StubStorage` for dry-run/tests. The interface exists so Cloudflare R2
(zero-egress; the at-scale cost win — see BUGS analysis) can drop in later as a
config swap with no orchestrator changes.

Objects are keyed `media/<user_id>/<job_id>/<asset_id>.<ext>`. `MediaAsset.url`
stores the **key** (durable); callers mint a short-lived signed URL on demand via
`signed_url()` (never a permanent public link).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from backend.services.distribution.net_guard import safe_stream_get
from backend.services.media.providers import dry_run_enabled

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = (5, 300)  # (connect, read) — reads stream large media


@dataclass
class StoredObject:
    key: str
    size_bytes: Optional[int] = None
    mime: Optional[str] = None


class StorageError(Exception):
    """A storage backend operation failed."""


class MediaStorage:
    """Persist finished media and mint short-lived read URLs."""

    def put_bytes(self, data: bytes, key: str, mime: str) -> StoredObject:  # pragma: no cover
        raise NotImplementedError

    def put_from_url(
        self, source_url: str, key: str, *, mime: Optional[str] = None
    ) -> StoredObject:  # pragma: no cover
        raise NotImplementedError

    def signed_url(self, key: str, *, expires_s: int = 3600) -> str:  # pragma: no cover
        raise NotImplementedError


class StubStorage(MediaStorage):
    """No-network backend for dry-run/tests. Echoes deterministic stub URLs."""

    def put_bytes(self, data: bytes, key: str, mime: str) -> StoredObject:
        return StoredObject(key=key, size_bytes=len(data or b""), mime=mime)

    def put_from_url(
        self, source_url: str, key: str, *, mime: Optional[str] = None
    ) -> StoredObject:
        # Dry-run never re-hosts a real asset; the stub URL is already "ours".
        return StoredObject(key=key, size_bytes=None, mime=mime)

    def signed_url(self, key: str, *, expires_s: int = 3600) -> str:
        return f"https://stub.local/media/{key}"


class SupabaseStorage(MediaStorage):
    """Supabase Storage backend via the Storage REST API (no extra SDK dependency).

    Requires `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (service-role) and a bucket
    (`MEDIA_STORAGE_BUCKET`, default `media`). Uploads with the service role; reads
    go through time-limited signed URLs so the bucket stays private.
    """

    def __init__(self):
        self.base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        self.bucket = os.getenv("MEDIA_STORAGE_BUCKET", "media").strip()
        if not self.base or not self.key:
            raise StorageError("SUPABASE_URL / SUPABASE_SERVICE_KEY not configured")

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.key}"}

    def put_bytes(self, data: bytes, key: str, mime: str) -> StoredObject:
        import requests

        resp = requests.post(
            f"{self.base}/storage/v1/object/{self.bucket}/{key}",
            headers={**self._auth(), "Content-Type": mime, "x-upsert": "true"},
            data=data,
            timeout=_HTTP_TIMEOUT,
        )
        if resp.status_code >= 400:
            raise StorageError(f"Supabase upload {resp.status_code}: {resp.text[:300]}")
        return StoredObject(key=key, size_bytes=len(data or b""), mime=mime)

    def put_from_url(
        self, source_url: str, key: str, *, mime: Optional[str] = None
    ) -> StoredObject:
        # `source_url` is provider-issued but still fetched server-side, so it goes
        # through the SSRF guard (rejects internal/loopback targets, re-validates
        # every redirect hop) exactly like the Phase-10 media fetch.
        with safe_stream_get(source_url, timeout=_HTTP_TIMEOUT) as src:
            src.raise_for_status()
            content_type = mime or src.headers.get("Content-Type", "application/octet-stream")
            data = src.content
        return self.put_bytes(data, key, content_type)

    def signed_url(self, key: str, *, expires_s: int = 3600) -> str:
        import requests

        resp = requests.post(
            f"{self.base}/storage/v1/object/sign/{self.bucket}/{key}",
            headers={**self._auth(), "Content-Type": "application/json"},
            json={"expiresIn": expires_s},
            timeout=(5, 30),
        )
        if resp.status_code >= 400:
            raise StorageError(f"Supabase sign {resp.status_code}: {resp.text[:300]}")
        signed = (resp.json() or {}).get("signedURL") or (resp.json() or {}).get("signedUrl") or ""
        return f"{self.base}/storage/v1{signed}" if signed.startswith("/") else signed


def signed_url_for(url_or_key: str, *, expires_s: int = 3600) -> str:
    """Mint a signed URL for a durable storage key, or pass an already-absolute URL
    through unchanged. Most assets persist a storage key, but some (dry-run
    `assemble()`, legacy rows) persist a full `http(s)://` URL — signing that as a
    key would produce a malformed link."""
    if url_or_key.startswith(("http://", "https://")):
        return url_or_key
    return get_storage().signed_url(url_or_key, expires_s=expires_s)


def get_storage() -> MediaStorage:
    """Resolve the storage backend: StubStorage in dry-run (or when unconfigured),
    else the configured durable backend (Supabase today; R2 is a future swap)."""
    if dry_run_enabled():
        return StubStorage()
    backend = os.getenv("MEDIA_STORAGE_BACKEND", "supabase").strip().lower()
    if backend == "supabase":
        return SupabaseStorage()
    if backend in ("stub", "none"):
        return StubStorage()
    raise StorageError(f"Unknown MEDIA_STORAGE_BACKEND '{backend}'")
