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

    AUDIO_CLEAN = "audio_clean"  # A1  ElevenLabs Voice Isolator
    AUDIO_MASTER = "audio_master"  # A2/D2  Auphonic loudness master
    TTS = "tts"  # B1  ElevenLabs TTS / voiceover
    DUB = "dub"  # B3  ElevenLabs Dubbing (translate + preserve voice)
    LIPSYNC = "lipsync"  # C1  Sync.so
    AVATAR_VIDEO = "avatar_video"  # HeyGen talking-head
    GEN_CLIP = "gen_clip"  # Kling / Veo b-roll clip
    GEN_IMAGE = "gen_image"  # IMAGE-GEN: Flux / DALL·E / Ideogram still image
    ASSEMBLE = "assemble"  # ffmpeg concat / mux (local)


@dataclass
class MediaResult:
    """Outcome of a provider `start`/`poll`/`parse_webhook` call."""

    ok: bool
    external_id: Optional[str] = None  # provider job id (async handle)
    asset_url: Optional[str] = None  # provider-hosted (expiring) URL to re-host
    content: Optional[bytes] = None  # raw bytes for synchronous providers (TTS)
    content_mime: Optional[str] = None  # mime of `content`
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
        if _is_image(self.kind):
            # A still image has no duration; return an image asset + mime.
            return MediaResult(
                ok=True,
                external_id=external_id,
                asset_url=f"https://stub.local/media/{digest}.png",
                done=True,
                cost_cents=0,
                duration_s=None,
                mime="image/png",
            )
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


_HTTP_TIMEOUT = 60


class _MissingCredential(Exception):
    """Raised when a real provider's API key isn't configured on the instance."""


def _require_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise _MissingCredential(f"{name} is not set")
    return val


class ElevenLabsTTSProvider(BaseMediaProvider):
    """ElevenLabs text-to-speech (P12.2). Synchronous: `start()` returns the audio
    bytes directly (no external job), so the stage completes immediately and the
    orchestrator persists the bytes to storage."""

    name = "elevenlabs_tts"
    BASE = "https://api.elevenlabs.io/v1"

    def start(self, spec: dict) -> MediaResult:
        import requests

        try:
            api_key = _require_env("ELEVENLABS_API_KEY")
            voice_id = spec.get("voice_id") or os.getenv("ELEVENLABS_VOICE_ID", "").strip()
            if not voice_id:
                return MediaResult(
                    ok=False, error="No ElevenLabs voice_id (spec or ELEVENLABS_VOICE_ID)"
                )
            text = spec.get("script") or spec.get("text") or ""
            if not text:
                return MediaResult(ok=False, error="TTS requires 'script'/'text' in the spec")
            resp = requests.post(
                f"{self.BASE}/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "accept": "audio/mpeg"},
                json={
                    "text": text,
                    "model_id": spec.get("model_id", "eleven_multilingual_v2"),
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"ElevenLabs {resp.status_code}: {resp.text[:300]}"
                )
            return MediaResult(
                ok=True,
                done=True,
                content=resp.content,
                content_mime="audio/mpeg",
                mime="audio/mpeg",
            )
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001 - surface any failure as a result
            logger.warning("ElevenLabs TTS failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:  # pragma: no cover - synchronous
        return MediaResult(ok=True, done=True, external_id=external_id)


class HeyGenProvider(BaseMediaProvider):
    """HeyGen avatar (talking-head) video (P12.2). Asynchronous: `start()` submits
    a render and returns a `video_id`; `poll()`/`parse_webhook()` report completion
    with a (short-lived) hosted URL that the orchestrator re-hosts to storage."""

    name = "heygen"
    BASE = "https://api.heygen.com"

    def start(self, spec: dict) -> MediaResult:
        import requests

        try:
            api_key = _require_env("HEYGEN_API_KEY")
            avatar_id = spec.get("avatar_id") or os.getenv("HEYGEN_AVATAR_ID", "").strip()
            if not avatar_id:
                return MediaResult(ok=False, error="No HeyGen avatar_id (spec or HEYGEN_AVATAR_ID)")
            # Prefer the upstream stage's audio (talking-head from real TTS); fall
            # back to HeyGen's native voice from the script text.
            parent_audio = spec.get("_parent_asset_url")
            if parent_audio:
                voice = {"type": "audio", "audio_url": parent_audio}
            else:
                voice_id = spec.get("voice_id") or os.getenv("HEYGEN_VOICE_ID", "").strip()
                voice = {"type": "text", "input_text": spec.get("script", ""), "voice_id": voice_id}
            resp = requests.post(
                f"{self.BASE}/v2/video/generate",
                headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
                json={
                    "video_inputs": [
                        {"character": {"type": "avatar", "avatar_id": avatar_id}, "voice": voice}
                    ],
                    "dimension": {"width": 1280, "height": 720},
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(ok=False, error=f"HeyGen {resp.status_code}: {resp.text[:300]}")
            video_id = ((resp.json() or {}).get("data") or {}).get("video_id", "")
            if not video_id:
                return MediaResult(ok=False, error="HeyGen returned no video_id")
            return MediaResult(ok=True, external_id=video_id, done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("HeyGen submit failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:
        import requests

        try:
            api_key = _require_env("HEYGEN_API_KEY")
            resp = requests.get(
                f"{self.BASE}/v1/video_status.get",
                headers={"X-Api-Key": api_key},
                params={"video_id": external_id},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"HeyGen status {resp.status_code}: {resp.text[:200]}"
                )
            data = (resp.json() or {}).get("data") or {}
            return self._from_status(external_id, data)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("HeyGen poll failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def parse_webhook(self, payload: dict, headers: dict) -> MediaResult:
        # HeyGen callback: {"event_type": "avatar_video.success", "event_data": {...}}
        event = str(payload.get("event_type") or "")
        data = payload.get("event_data") or payload
        external_id = str(data.get("video_id") or payload.get("external_id") or "")
        if event.endswith(".fail") or data.get("status") == "failed":
            return MediaResult(
                ok=False, external_id=external_id, error=str(data.get("msg") or "HeyGen failed")
            )
        return self._from_status(external_id, data)

    @staticmethod
    def _from_status(external_id: str, data: dict) -> MediaResult:
        status = str(data.get("status") or "")
        if status in ("completed", "success") or data.get("video_url"):
            return MediaResult(
                ok=True,
                done=True,
                external_id=external_id,
                asset_url=data.get("video_url") or data.get("url"),
                duration_s=int(data["duration"]) if data.get("duration") else None,
                mime="video/mp4",
            )
        if status in ("failed", "error"):
            return MediaResult(
                ok=False, external_id=external_id, error=str(data.get("error") or "HeyGen failed")
            )
        return MediaResult(ok=True, external_id=external_id, done=False)  # still processing


class KlingProvider(BaseMediaProvider):
    """Kling generative b-roll clip (P12.3). Async: submit a text→video task, poll
    for the finished clip URL (which the orchestrator re-hosts to storage)."""

    name = "kling"
    BASE = "https://api.klingai.com/v1"

    def start(self, spec: dict) -> MediaResult:
        import requests

        try:
            api_key = _require_env("KLING_API_KEY")
            prompt = spec.get("prompt") or spec.get("script") or ""
            if not prompt:
                return MediaResult(ok=False, error="Kling requires a 'prompt' in the spec")
            resp = requests.post(
                f"{self.BASE}/videos/text2video",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "duration": str(int(spec.get("seconds", 5))),
                    "model_name": spec.get("model", "kling-v1"),
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(ok=False, error=f"Kling {resp.status_code}: {resp.text[:300]}")
            task_id = ((resp.json() or {}).get("data") or {}).get("task_id", "")
            if not task_id:
                return MediaResult(ok=False, error="Kling returned no task_id")
            return MediaResult(ok=True, external_id=task_id, done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Kling submit failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:
        import requests

        try:
            api_key = _require_env("KLING_API_KEY")
            resp = requests.get(
                f"{self.BASE}/videos/text2video/{external_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"Kling status {resp.status_code}: {resp.text[:200]}"
                )
            data = (resp.json() or {}).get("data") or {}
            status = str(data.get("task_status") or "")
            if status == "succeed":
                videos = (data.get("task_result") or {}).get("videos") or []
                url = videos[0].get("url") if videos else None
                if not url:
                    return MediaResult(
                        ok=False, external_id=external_id, error="Kling succeeded with no video url"
                    )
                return MediaResult(
                    ok=True, done=True, external_id=external_id, asset_url=url, mime="video/mp4"
                )
            if status == "failed":
                return MediaResult(
                    ok=False,
                    external_id=external_id,
                    error=str(data.get("task_status_msg") or "Kling failed"),
                )
            return MediaResult(
                ok=True, external_id=external_id, done=False
            )  # submitted / processing
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Kling poll failed: %s", e)
            return MediaResult(ok=False, error=str(e))


class VeoProvider(BaseMediaProvider):
    """Google Veo premium b-roll via Vertex AI (P12.3). Gated behind quality=premium
    AND Vertex credentials; fail-closed otherwise (access is region/tier-limited)."""

    name = "veo"

    def start(self, spec: dict) -> MediaResult:
        try:
            _require_env("GOOGLE_VERTEX_PROJECT")
            _require_env("GOOGLE_VERTEX_ACCESS_TOKEN")
        except _MissingCredential as e:
            return MediaResult(
                ok=False, error=f"Veo not configured ({e}); use Kling or set quality!=premium"
            )
        # Real Vertex AI predict/operation wiring lands when account access is
        # confirmed (spec §9 open question). Until then, fail closed rather than
        # pretend — never silently fall back to a different (billed) provider.
        return MediaResult(
            ok=False,
            error="Veo (Vertex AI) submission not implemented yet — access unconfirmed. Use Kling (default).",
        )

    def poll(
        self, external_id: str
    ) -> MediaResult:  # pragma: no cover - unreachable until start works
        return MediaResult(ok=False, error="Veo not implemented")


class SyncProvider(BaseMediaProvider):
    """Sync.so lip-sync (P12.3, optional). Async: submit video+audio, poll for the
    lip-synced result. Only used when the pipeline requests lip-sync."""

    name = "sync"
    BASE = "https://api.sync.so/v2"

    def start(self, spec: dict) -> MediaResult:
        import requests

        try:
            api_key = _require_env("SYNC_API_KEY")
            video_url = spec.get("_video_url")
            audio_url = spec.get("_audio_url")
            if not video_url or not audio_url:
                return MediaResult(
                    ok=False, error="Sync.so requires both a video and an audio input"
                )
            resp = requests.post(
                f"{self.BASE}/generate",
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "model": spec.get("model", "lipsync-1.9.0-beta"),
                    "input": [
                        {"type": "video", "url": video_url},
                        {"type": "audio", "url": audio_url},
                    ],
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(ok=False, error=f"Sync.so {resp.status_code}: {resp.text[:300]}")
            job_id = (resp.json() or {}).get("id", "")
            if not job_id:
                return MediaResult(ok=False, error="Sync.so returned no job id")
            return MediaResult(ok=True, external_id=job_id, done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Sync.so submit failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:
        import requests

        try:
            api_key = _require_env("SYNC_API_KEY")
            resp = requests.get(
                f"{self.BASE}/generate/{external_id}",
                headers={"x-api-key": api_key},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"Sync.so status {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json() or {}
            status = str(data.get("status") or "")
            if status == "COMPLETED":
                return MediaResult(
                    ok=True,
                    done=True,
                    external_id=external_id,
                    asset_url=data.get("outputUrl"),
                    mime="video/mp4",
                )
            if status in ("FAILED", "ERROR", "REJECTED"):
                return MediaResult(
                    ok=False,
                    external_id=external_id,
                    error=str(data.get("error") or "Sync.so failed"),
                )
            return MediaResult(ok=True, external_id=external_id, done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Sync.so poll failed: %s", e)
            return MediaResult(ok=False, error=str(e))


class FfmpegProvider(BaseMediaProvider):
    """Local ffmpeg assembly (P12.3). Synchronous: downloads the input assets the
    orchestrator injected as fresh signed URLs, runs concat/mux, and returns the
    output bytes for the orchestrator to persist. No external API."""

    name = "ffmpeg"

    def start(self, spec: dict) -> MediaResult:
        import tempfile

        from backend.services.distribution.net_guard import safe_stream_get
        from backend.services.media import ffmpeg

        op = spec.get("_ffmpeg_op", "concat")
        if op == "mux":
            input_urls = [spec["_video_url"]] if spec.get("_video_url") else []
            audio_url = spec.get("_audio_url")
        else:
            input_urls = list(spec.get("_input_urls") or [])
            audio_url = None
        if not input_urls:
            return MediaResult(ok=False, error=f"ffmpeg {op}: no input assets injected")

        tmpdir = tempfile.mkdtemp(prefix="media_ffmpeg_")
        try:
            in_paths = [
                self._download(safe_stream_get, u, os.path.join(tmpdir, f"in_{i}.mp4"))
                for i, u in enumerate(input_urls)
            ]
            audio_path = (
                self._download(safe_stream_get, audio_url, os.path.join(tmpdir, "audio.bin"))
                if audio_url
                else None
            )
            data = ffmpeg.run(op, in_paths, audio_path=audio_path)
            return MediaResult(
                ok=True, done=True, content=data, content_mime="video/mp4", mime="video/mp4"
            )
        except ffmpeg.FfmpegError as e:
            return MediaResult(ok=False, error=f"ffmpeg {op} failed: {e}")
        except Exception as e:  # noqa: BLE001
            logger.warning("ffmpeg assemble failed: %s", e)
            return MediaResult(ok=False, error=str(e))
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    @staticmethod
    def _download(getter, url: str, dest: str) -> str:
        with getter(url, timeout=(5, 300)) as src:
            src.raise_for_status()
            with open(dest, "wb") as fh:
                fh.write(src.content)
        return dest

    def poll(self, external_id: str) -> MediaResult:  # pragma: no cover - synchronous
        return MediaResult(ok=True, done=True, external_id=external_id)


def _source_url(spec: dict) -> Optional[str]:
    """The source a standalone op operates on. ONLY the orchestrator-injected signed
    URL (`_source_url`) — never a caller-supplied `source_url`, so a raw external URL
    can never reach a vendor fetcher (SSRF). The orchestrator resolves an owned
    source_asset_id to this."""
    return spec.get("_source_url")


class ElevenLabsIsolatorProvider(BaseMediaProvider):
    """A1 — ElevenLabs Voice Isolator (P12.4). Synchronous: downloads the source,
    uploads it, and returns the cleaned audio bytes."""

    name = "elevenlabs_isolator"
    BASE = "https://api.elevenlabs.io/v1"

    def start(self, spec: dict) -> MediaResult:
        import requests

        from backend.services.distribution.net_guard import safe_stream_get

        try:
            api_key = _require_env("ELEVENLABS_API_KEY")
            src = _source_url(spec)
            if not src:
                return MediaResult(
                    ok=False, error="audio isolation needs a source (source_asset_id or source_url)"
                )
            with safe_stream_get(src, timeout=(5, 300)) as r:
                r.raise_for_status()
                audio = r.content
            resp = requests.post(
                f"{self.BASE}/audio-isolation",
                headers={"xi-api-key": api_key},
                files={"audio": ("input", audio)},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"ElevenLabs isolate {resp.status_code}: {resp.text[:300]}"
                )
            return MediaResult(
                ok=True,
                done=True,
                content=resp.content,
                content_mime="audio/mpeg",
                mime="audio/mpeg",
            )
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("ElevenLabs isolate failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:  # pragma: no cover - synchronous
        return MediaResult(ok=True, done=True, external_id=external_id)


class AuphonicProvider(BaseMediaProvider):
    """A2/D2 — Auphonic loudness master (P12.4). Async REST job: create + start a
    production over the source URL, poll until Done, then re-host the output."""

    name = "auphonic"
    BASE = "https://auphonic.com/api"

    def start(self, spec: dict) -> MediaResult:
        import requests

        try:
            api_key = _require_env("AUPHONIC_API_KEY")
            src = _source_url(spec)
            if not src:
                return MediaResult(
                    ok=False, error="mastering needs a source (source_asset_id or source_url)"
                )
            resp = requests.post(
                f"{self.BASE}/simple/productions.json",
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "input_file": src,
                    "title": spec.get("title", "master"),
                    "loudness_target": spec.get("lufs", os.getenv("AUDIO_LUFS_DEFAULT", "-14")),
                    "action": "start",
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"Auphonic {resp.status_code}: {resp.text[:300]}"
                )
            uuid = ((resp.json() or {}).get("data") or {}).get("uuid", "")
            if not uuid:
                return MediaResult(ok=False, error="Auphonic returned no production uuid")
            return MediaResult(ok=True, external_id=uuid, done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Auphonic submit failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:
        import requests

        try:
            api_key = _require_env("AUPHONIC_API_KEY")
            resp = requests.get(
                f"{self.BASE}/production/{external_id}.json",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"Auphonic status {resp.status_code}: {resp.text[:200]}"
                )
            data = (resp.json() or {}).get("data") or {}
            status_string = str(data.get("status_string") or "")
            if status_string == "Done":
                files = data.get("output_files") or []
                url = files[0].get("download_url") if files else None
                if not url:
                    return MediaResult(
                        ok=False, external_id=external_id, error="Auphonic done with no output file"
                    )
                return MediaResult(
                    ok=True, done=True, external_id=external_id, asset_url=url, mime="audio/mpeg"
                )
            if status_string in ("Error", "Incomplete", "Fail", "Warning"):
                return MediaResult(
                    ok=False, external_id=external_id, error=f"Auphonic {status_string}"
                )
            return MediaResult(ok=True, external_id=external_id, done=False)  # processing
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Auphonic poll failed: %s", e)
            return MediaResult(ok=False, error=str(e))


class ElevenLabsDubProvider(BaseMediaProvider):
    """B3 — ElevenLabs Dubbing (P12.4). Async: submit source + target language, poll,
    then fetch the dubbed audio bytes. The target language is encoded into the
    external id so `poll()` (which only gets the id) can fetch the right track."""

    name = "elevenlabs_dub"
    BASE = "https://api.elevenlabs.io/v1"

    def start(self, spec: dict) -> MediaResult:
        import requests

        try:
            api_key = _require_env("ELEVENLABS_API_KEY")
            src = _source_url(spec)
            target_lang = spec.get("target_lang") or spec.get("target_language")
            if not src:
                return MediaResult(
                    ok=False, error="dubbing needs a source (source_asset_id or source_url)"
                )
            if not target_lang:
                return MediaResult(ok=False, error="dubbing requires 'target_lang' in the spec")
            resp = requests.post(
                f"{self.BASE}/dubbing",
                headers={"xi-api-key": api_key},
                data={"source_url": src, "target_lang": target_lang, "mode": "automatic"},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"ElevenLabs dub {resp.status_code}: {resp.text[:300]}"
                )
            dubbing_id = (resp.json() or {}).get("dubbing_id", "")
            if not dubbing_id:
                return MediaResult(ok=False, error="ElevenLabs dub returned no dubbing_id")
            return MediaResult(ok=True, external_id=f"{dubbing_id}|{target_lang}", done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("ElevenLabs dub failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:
        import requests

        try:
            api_key = _require_env("ELEVENLABS_API_KEY")
            dubbing_id, _, lang = external_id.partition("|")
            status_resp = requests.get(
                f"{self.BASE}/dubbing/{dubbing_id}",
                headers={"xi-api-key": api_key},
                timeout=_HTTP_TIMEOUT,
            )
            if status_resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"ElevenLabs dub status {status_resp.status_code}"
                )
            status = str((status_resp.json() or {}).get("status") or "")
            if status == "dubbed":
                audio = requests.get(
                    f"{self.BASE}/dubbing/{dubbing_id}/audio/{lang}",
                    headers={"xi-api-key": api_key},
                    timeout=_HTTP_TIMEOUT,
                )
                if audio.status_code >= 400:
                    return MediaResult(ok=False, error=f"ElevenLabs dub audio {audio.status_code}")
                return MediaResult(
                    ok=True,
                    done=True,
                    external_id=external_id,
                    content=audio.content,
                    content_mime="audio/mpeg",
                    mime="audio/mpeg",
                )
            if status == "failed":
                return MediaResult(
                    ok=False, external_id=external_id, error="ElevenLabs dubbing failed"
                )
            return MediaResult(ok=True, external_id=external_id, done=False)  # dubbing in progress
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("ElevenLabs dub poll failed: %s", e)
            return MediaResult(ok=False, error=str(e))


# Real providers are wired here as they're built. A name absent from this map
# (outside dry-run) falls through to NotImplementedProvider (fail-closed).
class FluxProvider(BaseMediaProvider):
    """Black Forest Labs FLUX image generation (IMAGE-GEN). Async: submit a text→image
    request, poll for the finished image URL (which the orchestrator re-hosts to
    storage). Requires `BFL_API_KEY`; fail-closed otherwise."""

    name = "flux"
    BASE = "https://api.bfl.ml/v1"

    def start(self, spec: dict) -> MediaResult:
        import requests

        try:
            api_key = _require_env("BFL_API_KEY")
            prompt = spec.get("prompt") or spec.get("script") or ""
            if not prompt:
                return MediaResult(ok=False, error="Flux requires a 'prompt' in the spec")
            model = spec.get("model", "flux-pro-1.1")
            resp = requests.post(
                f"{self.BASE}/{model}",
                headers={"x-key": api_key, "Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "width": int(spec.get("width", 1024)),
                    "height": int(spec.get("height", 1024)),
                },
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(ok=False, error=f"Flux {resp.status_code}: {resp.text[:300]}")
            job_id = (resp.json() or {}).get("id", "")
            if not job_id:
                return MediaResult(ok=False, error="Flux returned no job id")
            return MediaResult(ok=True, external_id=job_id, done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Flux submit failed: %s", e)
            return MediaResult(ok=False, error=str(e))

    def poll(self, external_id: str) -> MediaResult:
        import requests

        try:
            api_key = _require_env("BFL_API_KEY")
            resp = requests.get(
                f"{self.BASE}/get_result",
                headers={"x-key": api_key},
                params={"id": external_id},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code >= 400:
                return MediaResult(
                    ok=False, error=f"Flux status {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json() or {}
            status = str(data.get("status") or "")
            if status == "Ready":
                url = (data.get("result") or {}).get("sample")
                if not url:
                    return MediaResult(
                        ok=False, external_id=external_id, error="Flux ready with no image url"
                    )
                return MediaResult(
                    ok=True, done=True, external_id=external_id, asset_url=url, mime="image/png"
                )
            # Terminal failure states (content moderation, error, expired handle).
            if status in ("Error", "Content Moderated", "Request Moderated", "Task not found"):
                return MediaResult(ok=False, external_id=external_id, error=f"Flux {status}")
            # Pending / Processing / anything else → still in flight.
            return MediaResult(ok=True, external_id=external_id, done=False)
        except _MissingCredential as e:
            return MediaResult(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.warning("Flux poll failed: %s", e)
            return MediaResult(ok=False, error=str(e))


_REAL_PROVIDERS: dict[str, type[BaseMediaProvider]] = {
    "elevenlabs_tts": ElevenLabsTTSProvider,
    "flux": FluxProvider,
    "elevenlabs_isolator": ElevenLabsIsolatorProvider,
    "elevenlabs_dub": ElevenLabsDubProvider,
    "auphonic": AuphonicProvider,
    "heygen": HeyGenProvider,
    "kling": KlingProvider,
    "veo": VeoProvider,
    "sync": SyncProvider,
    "ffmpeg": FfmpegProvider,
}


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
    MediaKind.AUDIO_MASTER: 60.0,
    MediaKind.TTS: 30.0,
    MediaKind.DUB: 30.0,
    MediaKind.LIPSYNC: 30.0,
    MediaKind.AVATAR_VIDEO: 60.0,
    MediaKind.GEN_CLIP: 8.0,
    # A still image is a single unit, not a duration; 1.0 makes the per-second cost
    # model resolve to a flat per-image price (rate × 1s).
    MediaKind.GEN_IMAGE: 1.0,
    MediaKind.ASSEMBLE: 0.0,
}

_IMAGE_KINDS = {MediaKind.GEN_IMAGE}


def _is_image(kind: MediaKind) -> bool:
    return kind in _IMAGE_KINDS


_VIDEO_KINDS = {MediaKind.AVATAR_VIDEO, MediaKind.GEN_CLIP, MediaKind.LIPSYNC, MediaKind.ASSEMBLE}


def _default_seconds(kind: MediaKind) -> float:
    return _DEFAULT_SECONDS.get(kind, 30.0)


def _is_video(kind: MediaKind) -> bool:
    return kind in _VIDEO_KINDS
