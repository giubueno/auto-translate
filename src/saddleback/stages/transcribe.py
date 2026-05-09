"""Stage 2: transcribe source audio into timestamped segments.

FR6, FR7, FR8, FR9.
"""

from __future__ import annotations

import re
from pathlib import Path

from saddleback.config import Config
from saddleback.types import Segment, write_json


class TranscribeError(Exception):
    pass


def parse_srt(srt_path: Path) -> list[Segment]:
    """Parse a .srt sidecar into Segments. Used to skip Whisper (FR9)."""
    text = srt_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text.strip())
    segments: list[Segment] = []
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        # Skip the index line if present.
        try:
            int(lines[0].strip())
            ts_line = lines[1]
            text_lines = lines[2:]
        except ValueError:
            ts_line = lines[0]
            text_lines = lines[1:]
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", ts_line)
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(x) for x in m.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
        seg_text = " ".join(text_lines).strip()
        if not seg_text:
            continue
        segments.append(
            Segment(id=len(segments), start=start, end=end, text=seg_text)
        )
    return segments


def find_srt_sidecar(source: Path) -> Path | None:
    """Look for <source>.srt next to the source MP4."""
    candidate = source.with_suffix(".srt")
    return candidate if candidate.exists() else None


def transcribe_with_whisper(audio_wav: Path, cfg: Config) -> list[Segment]:
    """Run faster-whisper transcription. Returns segment list."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscribeError(
            "faster-whisper not installed; pip install faster-whisper"
        ) from exc

    model = WhisperModel(
        cfg.transcribe.model,
        device=cfg.transcribe.device,
        compute_type=cfg.transcribe.compute_type,
    )
    segments_iter, _info = model.transcribe(
        str(audio_wav),
        beam_size=cfg.transcribe.beam_size,
        language=cfg.transcribe.language or None,
    )
    out: list[Segment] = []
    for s in segments_iter:
        out.append(Segment(id=len(out), start=float(s.start), end=float(s.end), text=s.text.strip()))
    return out


def run(source: Path, audio_wav: Path, run_dir: Path, cfg: Config) -> list[Segment]:
    """Run the transcribe stage. Skips Whisper if .srt sidecar present."""
    out_path = run_dir / "segments.json"
    if out_path.exists():
        raw = __import__("json").loads(out_path.read_text())
        return [Segment.model_validate(s) for s in raw]

    sidecar = find_srt_sidecar(source)
    if sidecar is not None:
        segments = parse_srt(sidecar)
        if not segments:
            raise TranscribeError(f".srt sidecar {sidecar} parsed to zero segments")
    else:
        segments = transcribe_with_whisper(audio_wav, cfg)
        if not segments:
            raise TranscribeError("Whisper produced zero segments from source audio")

    write_json(out_path, [s.model_dump() for s in segments])
    return segments
