from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from saddleback.config import Config
from saddleback.stages import extract


def _ffmpeg_or_skip():
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not available")


def test_probe_audio_stream(fixture_mp4: Path):
    _ffmpeg_or_skip()
    duration, count = extract.probe_audio_stream(fixture_mp4)
    assert count == 1
    assert duration > 1.0


def test_extract_full(fixture_mp4: Path, tmp_path: Path):
    _ffmpeg_or_skip()
    cfg = Config()
    artifacts = extract.run(fixture_mp4, tmp_path, cfg)
    assert artifacts["audio"].exists()
    assert artifacts["ref"].exists()
    assert artifacts["audio"].stat().st_size > 0
    assert artifacts["ref"].stat().st_size > 0


def test_extract_rejects_silent_or_too_short_source(tmp_path: Path):
    _ffmpeg_or_skip()
    bad = tmp_path / "silent.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:d=0.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(bad),
        ],
        check=True,
    )
    cfg = Config()
    with pytest.raises(extract.ExtractError):
        extract.run(bad, tmp_path, cfg)
