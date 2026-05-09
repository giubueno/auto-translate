"""Stage 6: mux source video + per-lang synced audio into final MP4s.

FR26, FR27, FR28.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from saddleback.config import Config


class MuxError(Exception):
    pass


def output_path_for(source: Path, lang: str) -> Path:
    """Deterministic location next to source. (FR27)"""
    return source.with_name(f"{source.stem}_{lang}{source.suffix}")


def mux_one(
    source: Path,
    synced_audio: Path,
    out_path: Path,
    cfg: Config,
) -> Path:
    """Mux source video stream + given audio track into out_path."""
    if shutil.which("ffmpeg") is None:
        raise MuxError("ffmpeg not found in PATH")
    if not source.exists():
        raise MuxError(f"source {source} not found")
    if not synced_audio.exists():
        raise MuxError(f"synced audio {synced_audio} not found")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-i",
        str(synced_audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy" if cfg.output.copy_video else "libx264",
        "-c:a",
        cfg.output.audio_codec,
        "-b:a",
        f"{cfg.output.audio_bitrate_k}k",
        "-shortest",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise MuxError(f"ffmpeg mux failed: {result.stderr.strip()}")
    return out_path


def run(
    source: Path,
    tracks_by_lang: dict[str, Path],
    cfg: Config,
) -> dict[str, Path]:
    """Mux all targets. Returns {lang: final_mp4_path}."""
    out: dict[str, Path] = {}
    for lang, track in tracks_by_lang.items():
        final = output_path_for(source, lang)
        mux_one(source, track, final, cfg)
        out[lang] = final
    return out


def remux_one(
    source: Path,
    synced_audio: Path,
    lang: str,
    cfg: Config,
) -> Path:
    """Re-mux a single language only. (FR28)"""
    out_path = output_path_for(source, lang)
    return mux_one(source, synced_audio, out_path, cfg)
