"""Stage 1: extract source audio + reference voice clip from the source MP4.

FR1, FR3, FR5.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from saddleback.config import Config


class ExtractError(Exception):
    pass


def probe_audio_stream(source: Path) -> tuple[float, int]:
    """Return (duration_seconds, audio_stream_count). Raises ExtractError on probe failure."""
    if shutil.which("ffprobe") is None:
        raise ExtractError("ffprobe not found in PATH; install ffmpeg")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ExtractError(f"ffprobe failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    duration = float(data.get("format", {}).get("duration", 0.0))
    return duration, len(audio)


def extract_audio(source: Path, out_wav: Path, sample_rate: int = 24000) -> Path:
    """Extract audio as 24 kHz mono WAV. Returns the output path."""
    if shutil.which("ffmpeg") is None:
        raise ExtractError("ffmpeg not found in PATH; install ffmpeg")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(out_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ExtractError(f"ffmpeg extract failed: {result.stderr.strip()}")
    return out_wav


def pick_ref_clip(
    audio_wav: Path,
    out_ref: Path,
    min_seconds: float,
    max_seconds: float,
) -> Path:
    """Extract a reference voice clip.

    MVP heuristic: take a window from min(60s, 0.1*duration) into the audio of length
    clamp(max_seconds, ref_max). This avoids the very first second (often has intro
    music or silence) and grabs a continuous block of presenter speech.
    """
    if shutil.which("ffmpeg") is None:
        raise ExtractError("ffmpeg not found in PATH; install ffmpeg")

    duration, _ = probe_audio_stream(audio_wav)
    ref_len = max(min_seconds, min(max_seconds, max_seconds))
    if duration <= ref_len:
        start = 0.0
        ref_len = max(min_seconds, duration * 0.5)
    else:
        # 10% in, but cap at 60s offset for short videos
        start = min(60.0, duration * 0.1)
        if start + ref_len > duration:
            start = max(0.0, duration - ref_len)

    out_ref.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(audio_wav),
        "-t",
        f"{ref_len:.3f}",
        "-c:a",
        "pcm_s16le",
        str(out_ref),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ExtractError(f"ffmpeg ref-clip extract failed: {result.stderr.strip()}")
    return out_ref


def run(source: Path, run_dir: Path, cfg: Config) -> dict[str, Path]:
    """Run the full extract stage. Returns artifact paths."""
    duration, audio_streams = probe_audio_stream(source)
    if audio_streams == 0:
        raise ExtractError(f"source {source} has no audio stream")
    if duration < 1.0:
        raise ExtractError(f"source {source} duration {duration:.2f}s is too short to dub")

    audio_wav = run_dir / "audio.wav"
    ref_wav = run_dir / "ref.wav"

    extract_audio(source, audio_wav, sample_rate=cfg.tts.sample_rate_out)
    pick_ref_clip(
        audio_wav,
        ref_wav,
        min_seconds=cfg.tts.ref_min_seconds,
        max_seconds=cfg.tts.ref_max_seconds,
    )
    return {"audio": audio_wav, "ref": ref_wav}
