"""Audio-only export — write `<source>_<lang>.<ext>` alongside the dubbed MP4.

Sources the synced WAV track produced by `stages/build.py` (already
sample-aligned to source duration) and either copies it (`wav`) or transcodes
via ffmpeg (`m4a`, `mp3`).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from saddleback.config import Config


class AudioExportError(Exception):
    pass


_CODEC_BY_FORMAT = {
    "m4a": ("aac", "ipod"),  # codec, container
    "mp3": ("libmp3lame", "mp3"),
}


def output_path_for(source: Path, lang: str, fmt: str) -> Path:
    return source.with_name(f"{source.stem}_{lang}.{fmt}")


def export_one(synced_wav: Path, source: Path, lang: str, fmt: str, cfg: Config) -> Path:
    """Produce one audio-only artifact next to `source`. Returns the output path."""
    if fmt not in {"wav", "m4a", "mp3"}:
        raise AudioExportError(f"unsupported audio_export format {fmt!r}")
    if not synced_wav.exists():
        raise AudioExportError(f"synced track {synced_wav} not found")

    out = output_path_for(source, lang, fmt)
    out.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "wav":
        shutil.copy2(synced_wav, out)
        return out

    if shutil.which("ffmpeg") is None:
        raise AudioExportError("ffmpeg not found in PATH")

    codec, container = _CODEC_BY_FORMAT[fmt]
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(synced_wav),
        "-vn",
        "-c:a",
        codec,
        "-b:a",
        f"{cfg.output.audio_bitrate_k}k",
        "-f",
        container,
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudioExportError(
            f"ffmpeg audio export to {fmt} failed: {result.stderr.strip()}"
        )
    return out


def run(
    source: Path,
    synced_tracks_by_lang: dict[str, Path],
    fmt: str,
    cfg: Config,
) -> dict[str, Path]:
    """Export audio-only files for every target language. Returns {lang: path}."""
    out: dict[str, Path] = {}
    for lang, synced_wav in synced_tracks_by_lang.items():
        out[lang] = export_one(synced_wav, source, lang, fmt, cfg)
    return out
