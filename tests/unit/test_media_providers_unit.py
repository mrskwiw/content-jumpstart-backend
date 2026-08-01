"""
Unit tests for Phase 12 P12.2 real providers — error/edge branches.

Direct provider calls with mocked `requests` (no DB, no app). Covers the failure
paths the happy-path integration tests don't: missing creds/inputs, HTTP errors,
network exceptions, HeyGen still-processing / failed states, and webhook fail events.
"""

from backend.services.media.providers import (
    AuphonicProvider,
    ElevenLabsDubProvider,
    ElevenLabsIsolatorProvider,
    ElevenLabsTTSProvider,
    FfmpegProvider,
    HeyGenProvider,
    FluxProvider,
    KlingProvider,
    MediaKind,
    NotImplementedProvider,
    SyncProvider,
    VeoProvider,
    get_provider,
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
    p = NotImplementedProvider(MediaKind.GEN_CLIP, "unknown_provider")
    assert not p.poll("x").ok
    assert not p.parse_webhook({}, {}).ok


# ── Kling (P12.3, async b-roll) ───────────────────────────────────────────────


def test_kling_missing_credential(monkeypatch):
    monkeypatch.delenv("KLING_API_KEY", raising=False)
    assert not KlingProvider(MediaKind.GEN_CLIP).start({"prompt": "x"}).ok
    assert not KlingProvider(MediaKind.GEN_CLIP).poll("t").ok


def test_kling_start_no_prompt(monkeypatch):
    monkeypatch.setenv("KLING_API_KEY", "k")  # pragma: allowlist secret
    r = KlingProvider(MediaKind.GEN_CLIP).start({})
    assert not r.ok and "prompt" in r.error


def test_kling_start_http_error_and_no_task(monkeypatch):
    monkeypatch.setenv("KLING_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=500, text="boom"))
    assert not KlingProvider(MediaKind.GEN_CLIP).start({"prompt": "x"}).ok
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={"data": {}}))
    r = KlingProvider(MediaKind.GEN_CLIP).start({"prompt": "x"})
    assert not r.ok and "task_id" in r.error


def test_kling_start_success(monkeypatch):
    monkeypatch.setenv("KLING_API_KEY", "k")  # pragma: allowlist secret
    _patch(
        monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={"data": {"task_id": "t1"}})
    )
    r = KlingProvider(MediaKind.GEN_CLIP).start({"prompt": "sunset"})
    assert r.ok and r.external_id == "t1" and not r.done


def test_kling_poll_states(monkeypatch):
    monkeypatch.setenv("KLING_API_KEY", "k")  # pragma: allowlist secret
    p = KlingProvider(MediaKind.GEN_CLIP)
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(status=200, json_body={"data": {"task_status": "submitted"}}),
    )
    assert p.poll("t").ok and not p.poll("t").done
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            status=200, json_body={"data": {"task_status": "failed", "task_status_msg": "nope"}}
        ),
    )
    assert not p.poll("t").ok
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            status=200,
            json_body={"data": {"task_status": "succeed", "task_result": {"videos": []}}},
        ),
    )
    assert not p.poll("t").ok  # succeeded but no video url
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            status=200,
            json_body={
                "data": {
                    "task_status": "succeed",
                    "task_result": {"videos": [{"url": "https://c/x.mp4"}]},
                }
            },
        ),
    )
    done = p.poll("t")
    assert done.ok and done.done and done.asset_url.endswith(".mp4")
    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=500, text="err"))
    assert not p.poll("t").ok


# ── Sync.so (P12.3, optional lip-sync) ────────────────────────────────────────


def test_sync_missing_credential_and_inputs(monkeypatch):
    monkeypatch.delenv("SYNC_API_KEY", raising=False)
    assert not SyncProvider(MediaKind.LIPSYNC).start({"_video_url": "v", "_audio_url": "a"}).ok
    monkeypatch.setenv("SYNC_API_KEY", "s")  # pragma: allowlist secret
    r = SyncProvider(MediaKind.LIPSYNC).start({"_video_url": "v"})  # no audio
    assert not r.ok and "audio" in r.error.lower()


def test_sync_start_and_poll(monkeypatch):
    monkeypatch.setenv("SYNC_API_KEY", "s")  # pragma: allowlist secret
    p = SyncProvider(MediaKind.LIPSYNC)
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={"id": "j1"}))
    started = p.start({"_video_url": "v", "_audio_url": "a"})
    assert started.ok and started.external_id == "j1"
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=400, text="bad"))
    assert not p.start({"_video_url": "v", "_audio_url": "a"}).ok
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            status=200, json_body={"status": "COMPLETED", "outputUrl": "https://c/x.mp4"}
        ),
    )
    assert p.poll("j1").done
    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=200, json_body={"status": "FAILED"}))
    assert not p.poll("j1").ok
    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=200, json_body={"status": "PROCESSING"}))
    assert p.poll("j1").ok and not p.poll("j1").done


# ── Veo (premium, gated) ──────────────────────────────────────────────────────


def test_veo_configured_but_unimplemented(monkeypatch):
    monkeypatch.setenv("GOOGLE_VERTEX_PROJECT", "p")
    monkeypatch.setenv("GOOGLE_VERTEX_ACCESS_TOKEN", "t")  # pragma: allowlist secret
    r = VeoProvider(MediaKind.GEN_CLIP).start({"prompt": "x"})
    assert not r.ok and "not implemented" in r.error.lower()


# ── Ffmpeg (local assembly) ───────────────────────────────────────────────────


def test_ffmpeg_provider_no_inputs():
    r = FfmpegProvider(MediaKind.ASSEMBLE).start({"_ffmpeg_op": "concat"})
    assert not r.ok and "no input" in r.error.lower()


def test_ffmpeg_provider_concat_success(monkeypatch, tmp_path):
    class _Stream:
        content = b"CLIP"
        headers = {"Content-Type": "video/mp4"}

        def raise_for_status(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "backend.services.distribution.net_guard.safe_stream_get", lambda url, **kw: _Stream()
    )
    monkeypatch.setattr(
        "backend.services.media.ffmpeg.run", lambda op, paths, audio_path=None: b"STITCHED"
    )
    r = FfmpegProvider(MediaKind.ASSEMBLE).start(
        {"_ffmpeg_op": "concat", "_input_urls": ["u1", "u2"]}
    )
    assert r.ok and r.done and r.content == b"STITCHED"


def test_ffmpeg_provider_surfaces_ffmpeg_error(monkeypatch):
    from backend.services.media import ffmpeg as ffmpeg_mod

    class _Stream:
        content = b"CLIP"
        headers = {"Content-Type": "video/mp4"}

        def raise_for_status(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def boom(op, paths, audio_path=None):
        raise ffmpeg_mod.FfmpegError("bad codec")

    monkeypatch.setattr(
        "backend.services.distribution.net_guard.safe_stream_get", lambda url, **kw: _Stream()
    )
    monkeypatch.setattr("backend.services.media.ffmpeg.run", boom)
    r = FfmpegProvider(MediaKind.ASSEMBLE).start({"_ffmpeg_op": "concat", "_input_urls": ["u1"]})
    assert not r.ok and "ffmpeg" in r.error.lower()


# ── P12.4 audio ops (isolator / auphonic / dub) ───────────────────────────────


def _audio_stream(monkeypatch, content=b"AUDIO"):
    class _S:
        def __init__(self):
            self.content = content
            self.headers = {"Content-Type": "audio/mpeg"}

        def raise_for_status(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "backend.services.distribution.net_guard.safe_stream_get", lambda url, **kw: _S()
    )


def test_isolator_missing_credential_and_source(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert not ElevenLabsIsolatorProvider(MediaKind.AUDIO_CLEAN).start({"_source_url": "u"}).ok
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    r = ElevenLabsIsolatorProvider(MediaKind.AUDIO_CLEAN).start({})
    assert not r.ok and "source" in r.error.lower()


def test_isolator_http_error(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    _audio_stream(monkeypatch)
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=422, text="bad"))
    r = ElevenLabsIsolatorProvider(MediaKind.AUDIO_CLEAN).start({"_source_url": "u"})
    assert not r.ok and "422" in r.error


def test_auphonic_missing_credential_and_source(monkeypatch):
    monkeypatch.delenv("AUPHONIC_API_KEY", raising=False)
    assert not AuphonicProvider(MediaKind.AUDIO_MASTER).start({"_source_url": "u"}).ok
    assert not AuphonicProvider(MediaKind.AUDIO_MASTER).poll("x").ok
    monkeypatch.setenv("AUPHONIC_API_KEY", "k")  # pragma: allowlist secret
    r = AuphonicProvider(MediaKind.AUDIO_MASTER).start({})
    assert not r.ok and "source" in r.error.lower()


def test_auphonic_start_error_and_no_uuid(monkeypatch):
    monkeypatch.setenv("AUPHONIC_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=500, text="down"))
    assert not AuphonicProvider(MediaKind.AUDIO_MASTER).start({"_source_url": "u"}).ok
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={"data": {}}))
    r = AuphonicProvider(MediaKind.AUDIO_MASTER).start({"_source_url": "u"})
    assert not r.ok and "uuid" in r.error


def test_auphonic_poll_states(monkeypatch):
    monkeypatch.setenv("AUPHONIC_API_KEY", "k")  # pragma: allowlist secret
    p = AuphonicProvider(MediaKind.AUDIO_MASTER)
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            status=200, json_body={"data": {"status_string": "Audio Processing"}}
        ),
    )
    assert p.poll("x").ok and not p.poll("x").done
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(status=200, json_body={"data": {"status_string": "Error"}}),
    )
    assert not p.poll("x").ok
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            status=200, json_body={"data": {"status_string": "Done", "output_files": []}}
        ),
    )
    assert not p.poll("x").ok  # done but no file
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            status=200,
            json_body={
                "data": {
                    "status_string": "Done",
                    "output_files": [{"download_url": "https://a/o.mp3"}],
                }
            },
        ),
    )
    done = p.poll("x")
    assert done.ok and done.done and done.asset_url.endswith(".mp3")
    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=500, text="e"))
    assert not p.poll("x").ok


def test_dub_missing_cred_source_lang(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert (
        not ElevenLabsDubProvider(MediaKind.DUB).start({"_source_url": "u", "target_lang": "es"}).ok
    )
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    assert not ElevenLabsDubProvider(MediaKind.DUB).start({"target_lang": "es"}).ok  # no source
    r = ElevenLabsDubProvider(MediaKind.DUB).start({"_source_url": "u"})  # no lang
    assert not r.ok and "target_lang" in r.error


def test_dub_start_error_and_no_id(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=400, text="bad"))
    assert (
        not ElevenLabsDubProvider(MediaKind.DUB).start({"_source_url": "u", "target_lang": "es"}).ok
    )
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={}))
    r = ElevenLabsDubProvider(MediaKind.DUB).start({"_source_url": "u", "target_lang": "es"})
    assert not r.ok and "dubbing_id" in r.error


def test_dub_start_success_encodes_lang(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={"dubbing_id": "d1"}))
    r = ElevenLabsDubProvider(MediaKind.DUB).start({"_source_url": "u", "target_lang": "es"})
    assert r.ok and r.external_id == "d1|es"


def test_dub_poll_states(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    p = ElevenLabsDubProvider(MediaKind.DUB)

    def get_dubbed(url, **kw):
        if "/audio/" in url:
            return _Resp(status=200, content=b"DUBBED")
        return _Resp(status=200, json_body={"status": "dubbed"})

    _patch(monkeypatch, get=get_dubbed)
    done = p.poll("d1|es")
    assert done.ok and done.done and done.content == b"DUBBED"

    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=200, json_body={"status": "dubbing"}))
    assert p.poll("d1|es").ok and not p.poll("d1|es").done

    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=200, json_body={"status": "failed"}))
    assert not p.poll("d1|es").ok


# ── get_provider resolution / fail-closed ─────────────────────────────────────


def test_get_provider_unknown_name_fails_closed(monkeypatch):
    """Outside dry-run, an unwired provider name yields a fail-closed stub."""
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    p = get_provider(MediaKind.GEN_CLIP, "totally_unknown")
    assert isinstance(p, NotImplementedProvider)
    assert not p.start({}).ok  # NotImplementedProvider.start


def test_get_provider_dry_run_and_stub_name_use_stub(monkeypatch):
    monkeypatch.setenv("MEDIA_DRY_RUN", "true")
    assert get_provider(MediaKind.TTS, "elevenlabs_tts").name == "stub"
    monkeypatch.delenv("MEDIA_DRY_RUN", raising=False)
    assert get_provider(MediaKind.TTS, "stub").name == "stub"


# ── Network-exception (generic) branches for the real providers ───────────────
#
# Each real provider wraps its HTTP call in `except Exception` so a transport
# failure surfaces as a failed MediaResult (the orchestrator then retries). The
# missing-cred / non-2xx branches are covered above; these hit the catch-all.


def _raise(*a, **kw):
    raise RuntimeError("connection reset")


def test_heygen_start_missing_credential(monkeypatch):
    monkeypatch.delenv("HEYGEN_API_KEY", raising=False)
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).start({"script": "hi"})
    assert not r.ok and "HEYGEN_API_KEY" in r.error


def test_heygen_start_network_exception(monkeypatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "k")  # pragma: allowlist secret
    monkeypatch.setenv("HEYGEN_AVATAR_ID", "a")
    _patch(monkeypatch, post=_raise)
    r = HeyGenProvider(MediaKind.AVATAR_VIDEO).start({"voice_id": "v", "script": "hi"})
    assert not r.ok and "connection reset" in r.error


def test_kling_start_and_poll_network_exception(monkeypatch):
    monkeypatch.setenv("KLING_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=_raise, get=_raise)
    assert not KlingProvider(MediaKind.GEN_CLIP).start({"prompt": "x"}).ok
    assert not KlingProvider(MediaKind.GEN_CLIP).poll("t").ok


def test_sync_start_no_job_id_and_network(monkeypatch):
    monkeypatch.setenv("SYNC_API_KEY", "s")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=200, json_body={}))
    r = SyncProvider(MediaKind.LIPSYNC).start({"_video_url": "v", "_audio_url": "a"})
    assert not r.ok and "job id" in r.error.lower()
    _patch(monkeypatch, post=_raise)
    assert not SyncProvider(MediaKind.LIPSYNC).start({"_video_url": "v", "_audio_url": "a"}).ok


def test_sync_poll_http_error_missing_cred_and_network(monkeypatch):
    monkeypatch.setenv("SYNC_API_KEY", "s")  # pragma: allowlist secret
    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=503, text="down"))
    assert not SyncProvider(MediaKind.LIPSYNC).poll("j1").ok  # http-error branch
    _patch(monkeypatch, get=_raise)
    assert not SyncProvider(MediaKind.LIPSYNC).poll("j1").ok  # network branch
    monkeypatch.delenv("SYNC_API_KEY", raising=False)
    assert not SyncProvider(MediaKind.LIPSYNC).poll("j1").ok  # missing-cred branch


def test_ffmpeg_provider_generic_exception(monkeypatch):
    """A non-FfmpegError (e.g. a download blowing up) is caught and surfaced."""
    monkeypatch.setattr("backend.services.distribution.net_guard.safe_stream_get", _raise)
    r = FfmpegProvider(MediaKind.ASSEMBLE).start({"_ffmpeg_op": "concat", "_input_urls": ["u1"]})
    assert not r.ok and "connection reset" in r.error


def test_isolator_network_exception(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    _audio_stream(monkeypatch)
    _patch(monkeypatch, post=_raise)
    r = ElevenLabsIsolatorProvider(MediaKind.AUDIO_CLEAN).start({"_source_url": "u"})
    assert not r.ok and "connection reset" in r.error


def test_auphonic_start_and_poll_network_exception(monkeypatch):
    monkeypatch.setenv("AUPHONIC_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=_raise, get=_raise)
    assert not AuphonicProvider(MediaKind.AUDIO_MASTER).start({"_source_url": "u"}).ok
    assert not AuphonicProvider(MediaKind.AUDIO_MASTER).poll("x").ok


def test_dub_start_network_exception(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=_raise)
    r = ElevenLabsDubProvider(MediaKind.DUB).start({"_source_url": "u", "target_lang": "es"})
    assert not r.ok and "connection reset" in r.error


def test_dub_poll_status_http_error(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, get=lambda url, **kw: _Resp(status=500, text="err"))
    r = ElevenLabsDubProvider(MediaKind.DUB).poll("d1|es")
    assert not r.ok and "500" in r.error


def test_dub_poll_audio_http_error(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret

    def get(url, **kw):
        if "/audio/" in url:
            return _Resp(status=502, text="bad gateway")
        return _Resp(status=200, json_body={"status": "dubbed"})

    _patch(monkeypatch, get=get)
    r = ElevenLabsDubProvider(MediaKind.DUB).poll("d1|es")
    assert not r.ok and "502" in r.error


def test_dub_poll_missing_cred_and_network(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert not ElevenLabsDubProvider(MediaKind.DUB).poll("d1|es").ok  # missing-cred
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, get=_raise)
    assert not ElevenLabsDubProvider(MediaKind.DUB).poll("d1|es").ok  # network


# ── Flux (IMAGE-GEN) ──────────────────────────────────────────────────────────


def test_flux_missing_credential(monkeypatch):
    monkeypatch.delenv("BFL_API_KEY", raising=False)
    r = FluxProvider(MediaKind.GEN_IMAGE).start({"prompt": "a cat"})
    assert not r.ok and "BFL_API_KEY" in r.error


def test_flux_missing_prompt(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    r = FluxProvider(MediaKind.GEN_IMAGE).start({})
    assert not r.ok and "prompt" in r.error.lower()


def test_flux_start_success_returns_job_id(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(json_body={"id": "job-123"}))
    r = FluxProvider(MediaKind.GEN_IMAGE).start({"prompt": "a cat"})
    assert r.ok and r.external_id == "job-123" and not r.done


def test_flux_start_http_error(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(status=402, text="pay up"))
    r = FluxProvider(MediaKind.GEN_IMAGE).start({"prompt": "a cat"})
    assert not r.ok and "402" in r.error


def test_flux_start_no_job_id(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, post=lambda url, **kw: _Resp(json_body={}))
    r = FluxProvider(MediaKind.GEN_IMAGE).start({"prompt": "a cat"})
    assert not r.ok and "no job id" in r.error.lower()


def test_flux_poll_ready_returns_image(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    _patch(
        monkeypatch,
        get=lambda url, **kw: _Resp(
            json_body={"status": "Ready", "result": {"sample": "https://cdn/x.png"}}
        ),
    )
    r = FluxProvider(MediaKind.GEN_IMAGE).poll("job-123")
    assert r.ok and r.done and r.asset_url == "https://cdn/x.png" and r.mime == "image/png"


def test_flux_poll_pending_not_done(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, get=lambda url, **kw: _Resp(json_body={"status": "Pending"}))
    r = FluxProvider(MediaKind.GEN_IMAGE).poll("job-123")
    assert r.ok and not r.done


def test_flux_poll_moderated_fails(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, get=lambda url, **kw: _Resp(json_body={"status": "Content Moderated"}))
    r = FluxProvider(MediaKind.GEN_IMAGE).poll("job-123")
    assert not r.ok and "Moderated" in r.error


def test_flux_poll_ready_without_url_fails(monkeypatch):
    monkeypatch.setenv("BFL_API_KEY", "k")  # pragma: allowlist secret
    _patch(monkeypatch, get=lambda url, **kw: _Resp(json_body={"status": "Ready", "result": {}}))
    r = FluxProvider(MediaKind.GEN_IMAGE).poll("job-123")
    assert not r.ok and "no image url" in r.error.lower()
