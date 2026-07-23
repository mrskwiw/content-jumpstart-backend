"""
Unit tests for the local ffmpeg wrapper (Phase 12 P12.3).

subprocess is mocked — no real ffmpeg binary needed. Covers concat/mux command
shape, output read-back, and every error path (unknown op, missing audio, no
inputs, non-zero exit).
"""

import pytest

from backend.services.media import ffmpeg


def _writer(payload: bytes):
    """A fake subprocess.run that writes `payload` to the ffmpeg output path (last arg)."""

    def run(cmd, **kw):
        with open(cmd[-1], "wb") as fh:
            fh.write(payload)

        class _Proc:
            returncode = 0
            stderr = b""

        return _Proc()

    return run


def test_concat_builds_command_and_returns_bytes(monkeypatch):
    captured = {}

    def run(cmd, **kw):
        captured["cmd"] = cmd
        with open(cmd[-1], "wb") as fh:
            fh.write(b"VID")

        class _Proc:
            returncode = 0
            stderr = b""

        return _Proc()

    monkeypatch.setattr(ffmpeg.subprocess, "run", run)
    data = ffmpeg.run("concat", ["/tmp/a.mp4", "/tmp/b.mp4"])
    assert data == b"VID"
    assert "concat" in captured["cmd"] and "-safe" in captured["cmd"]


def test_mux_success(monkeypatch):
    monkeypatch.setattr(ffmpeg.subprocess, "run", _writer(b"MUXED"))
    assert ffmpeg.run("mux", ["/tmp/v.mp4"], audio_path="/tmp/a.mp3") == b"MUXED"


def test_mux_requires_audio(monkeypatch):
    monkeypatch.setattr(ffmpeg.subprocess, "run", _writer(b"x"))
    with pytest.raises(ffmpeg.FfmpegError):
        ffmpeg.run("mux", ["/tmp/v.mp4"])


def test_unknown_op(monkeypatch):
    monkeypatch.setattr(ffmpeg.subprocess, "run", _writer(b"x"))
    with pytest.raises(ffmpeg.FfmpegError):
        ffmpeg.run("rotate", ["/tmp/a.mp4"])


def test_no_inputs():
    with pytest.raises(ffmpeg.FfmpegError):
        ffmpeg.run("concat", [])


def test_nonzero_exit_raises(monkeypatch):
    def run(cmd, **kw):
        class _Proc:
            returncode = 1
            stderr = b"boom"

        return _Proc()

    monkeypatch.setattr(ffmpeg.subprocess, "run", run)
    with pytest.raises(ffmpeg.FfmpegError):
        ffmpeg.run("concat", ["/tmp/a.mp4"])


def test_binary_env(monkeypatch):
    monkeypatch.delenv("FFMPEG_PATH", raising=False)
    assert ffmpeg.ffmpeg_bin() == "ffmpeg"
    monkeypatch.setenv("FFMPEG_PATH", "/usr/local/bin/ffmpeg")
    assert ffmpeg.ffmpeg_bin() == "/usr/local/bin/ffmpeg"
