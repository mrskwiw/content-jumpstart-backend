"""
Local ffmpeg wrapper for Phase 12 P12.3 (cinematic assembly).

The one non-API stage of the media subsystem: `concat` stitches generated clips
into one video, `mux` marries a video track to an audio track. Runs the server's
ffmpeg binary (`FFMPEG_PATH`, default `ffmpeg`) over temp files and returns the
output bytes, which the orchestrator persists to storage like any other stage.

The Docker image MUST include ffmpeg (see project/Dockerfile). In `MEDIA_DRY_RUN`
this is never reached — the assemble stage routes to the StubProvider instead.
"""

from __future__ import annotations

import logging
import os
import subprocess  # noqa: S404  # nosec B404 - fixed arg list, never a shell string
import tempfile
from typing import List, Optional

logger = logging.getLogger(__name__)

_TIMEOUT_S = 600  # long renders/stitches can take minutes


class FfmpegError(Exception):
    """An ffmpeg invocation failed or produced no output."""


def ffmpeg_bin() -> str:
    return os.getenv("FFMPEG_PATH", "ffmpeg").strip() or "ffmpeg"


def _run(cmd: List[str]) -> None:
    try:
        proc = subprocess.run(  # noqa: S603  # nosec B603 - fixed binary + arg list, shell=False
            cmd,
            capture_output=True,
            timeout=_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise FfmpegError(f"ffmpeg failed to run: {e}") from e
    if proc.returncode != 0:
        raise FfmpegError(f"ffmpeg exited {proc.returncode}: {proc.stderr[:400]!r}")


def run(op: str, input_paths: List[str], *, audio_path: Optional[str] = None) -> bytes:
    """Run an assembly `op` over local input files, returning the output mp4 bytes.

    - ``concat``: concatenate ``input_paths`` (clips) into one video (re-encoded so
      clips with differing params join cleanly).
    - ``mux``: mux ``input_paths[0]`` (video) with ``audio_path`` (audio), trimming
      to the shorter stream.
    """
    if not input_paths:
        raise FfmpegError("no input files to assemble")
    bin_ = ffmpeg_bin()
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "out.mp4")
        if op == "concat":
            list_path = os.path.join(tmp, "inputs.txt")
            with open(list_path, "w", encoding="utf-8") as fh:
                for p in input_paths:
                    # ffmpeg concat demuxer: each line `file '<path>'`.
                    fh.write(f"file '{p}'\n")
            _run(
                [
                    bin_,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_path,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    out_path,
                ]
            )
        elif op == "mux":
            if not audio_path:
                raise FfmpegError("mux requires an audio_path")
            _run(
                [
                    bin_,
                    "-y",
                    "-i",
                    input_paths[0],
                    "-i",
                    audio_path,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-shortest",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    out_path,
                ]
            )
        else:
            raise FfmpegError(f"unknown ffmpeg op '{op}'")
        try:
            with open(out_path, "rb") as fh:
                data = fh.read()
        except OSError as e:
            raise FfmpegError(f"ffmpeg produced no output: {e}") from e
    if not data:
        raise FfmpegError("ffmpeg produced an empty file")
    return data
