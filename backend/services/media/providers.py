"""
Media provider abstraction for Phase 12 (P12.1 backbone).

Mirrors `distribution/publishers.py`: each provider turns a job `spec` into a
`MediaResult`. Media renders are **long-running and async**, so the contract is
`start()` (submit) → `poll()` (status) / `parse_webhook()` (push), not a single
synchronous `publish()`.

P12.1 ships only the `StubProvider` (deterministic, no network, zero cost). Every
real provider name resolves to a fail-closed `NotImplementedProvider` until its
integration lands (P12.2+). Set `MEDIA_DRY_RUN=true` (or use provider `"stub"`)
to route everything to the stub — safe for tests and demos.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class MediaKind(str, Enum):
    """The unit of work a single provider call performs."""

    AUDIO_CLEAN = "audio_clean"  # ElevenLabs Voice Isolator
    TTS = "tts"  # ElevenLabs TTS / voiceover
    DUB = "dub"  # ElevenLabs Dubbing (translate + preserve voice)
    LIPSYNC = "lipsync"  # Sync.so
    AVATAR_VIDEO = "avatar_video"  # HeyGen talking-head
    GEN_CLIP = "gen_clip"  # Kling / Veo b-roll clip
    ASSEMBLE = "assemble"  # ffmpeg concat / mux (local)


@dataclass
class MediaResult:
    """Outcome of a provider `start`/`poll`/`parse_webhook` call."""

    ok: bool
    external_id: Optional[str] = None  # provider job id (async handle)
    asset_url: Optional[str] = None  # set when the render is ready
    done: bool = False  # True when the job is complete
    cost_cents: int = 0  # actual spend reported by the provider (0 in dry-run)
    duration_s: Optional[int] = None  # produced media duration, when known
    mime: Optional[str] = None
    error: Optional[str] = None


def dry_run_enabled() -> bool:
    """Route every provider call to the StubProvider (no network, no spend)."""
    return os.getenv("MEDIA_DRY_RUN", "false").strip().lower() in ("1", "true", "yes")


class BaseMediaProvider:
    """A single async media operation for one `MediaKind`."""

    name: str = "base"

    def __init__(self, kind: MediaKind, credential=None, **kw):
        self.kind = kind
        self.credential = credential

    def start(self, spec: dict) -> MediaResult:  # pragma: no cover - abstract
        """Submit the job; return an `external_id` (async) or a ready asset."""
        raise NotImplementedError

    def poll(self, external_id: str) -> MediaResult:  # pragma: no cover - abstract
        """Check an in-flight job's status."""
        raise NotImplementedError

    def parse_webhook(self, payload: dict, headers: dict) -> MediaResult:  # pragma: no cover
        """Translate a provider callback into a `MediaResult` (P12.2+)."""
        raise NotImplementedError


class StubProvider(BaseMediaProvider):
    """Deterministic, no-network provider for dry-run/demo/tests.

    Models the async lifecycle so the orchestrator's submit → poll → chain path
    is exercised end-to-end: `start()` returns a `processing` handle, and the
    next `poll()` returns `done` with a stable stub asset URL. Cost is always 0.
    """

    name = "stub"

    def start(self, spec: dict) -> MediaResult:
        digest = hashlib.sha256(
            f"{self.kind.value}:{spec.get('prompt') or spec.get('script') or ''}".encode("utf-8")
        ).hexdigest()[:16]
        return MediaResult(ok=True, external_id=f"stub_{self.kind.value}_{digest}", done=False)

    def poll(self, external_id: str) -> MediaResult:
        # The stub completes on the first poll — deterministic and instant.
        digest = external_id.rsplit("_", 1)[-1]
        return MediaResult(
            ok=True,
            external_id=external_id,
            asset_url=f"https://stub.local/media/{digest}.mp4",
            done=True,
            cost_cents=0,
            duration_s=int(_default_seconds(self.kind)),
            mime="video/mp4" if _is_video(self.kind) else "audio/mpeg",
        )

    def parse_webhook(self, payload: dict, headers: dict) -> MediaResult:
        ext = str(payload.get("external_id") or payload.get("id") or "")
        return self.poll(ext) if ext else MediaResult(ok=False, error="stub webhook missing id")


class NotImplementedProvider(BaseMediaProvider):
    """Fail-closed provider for real integrations not built yet (P12.2+)."""

    def __init__(self, kind: MediaKind, requested_name: str, credential=None, **kw):
        super().__init__(kind, credential=credential)
        self.name = requested_name

    def _fail(self) -> MediaResult:
        return MediaResult(
            ok=False,
            done=False,
            error=(
                f"Media provider '{self.name}' for '{self.kind.value}' is not implemented yet — "
                f"it requires the P12.2+ integration + API credentials. "
                f"Set MEDIA_DRY_RUN=true to exercise the pipeline with the stub."
            ),
        )

    def start(self, spec: dict) -> MediaResult:
        return self._fail()

    def poll(self, external_id: str) -> MediaResult:
        return self._fail()

    def parse_webhook(self, payload: dict, headers: dict) -> MediaResult:
        return self._fail()


# Real providers are wired here as they're built (P12.2+). A name absent from
# this map (outside dry-run) falls through to NotImplementedProvider.
_REAL_PROVIDERS: dict[str, type[BaseMediaProvider]] = {}


def get_provider(kind: MediaKind, name: str, credential=None) -> BaseMediaProvider:
    """Resolve the provider for a job.

    Order: explicit dry-run / `"stub"` name → StubProvider; a name with a real
    implementation → that provider; otherwise a fail-closed NotImplementedProvider.
    """
    if name == "stub" or dry_run_enabled():
        return StubProvider(kind, credential=credential)
    impl = _REAL_PROVIDERS.get(name)
    if impl:
        return impl(kind, credential=credential)
    return NotImplementedProvider(kind, name, credential=credential)


# ── Shared helpers (also used by cost estimation) ─────────────────────────────

_DEFAULT_SECONDS: dict[MediaKind, float] = {
    MediaKind.AUDIO_CLEAN: 60.0,
    MediaKind.TTS: 30.0,
    MediaKind.DUB: 30.0,
    MediaKind.LIPSYNC: 30.0,
    MediaKind.AVATAR_VIDEO: 60.0,
    MediaKind.GEN_CLIP: 8.0,
    MediaKind.ASSEMBLE: 0.0,
}

_VIDEO_KINDS = {MediaKind.AVATAR_VIDEO, MediaKind.GEN_CLIP, MediaKind.LIPSYNC, MediaKind.ASSEMBLE}


def _default_seconds(kind: MediaKind) -> float:
    return _DEFAULT_SECONDS.get(kind, 30.0)


def _is_video(kind: MediaKind) -> bool:
    return kind in _VIDEO_KINDS
