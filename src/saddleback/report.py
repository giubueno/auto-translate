"""Quality report — round-trip transcribe synced audio and compare to source.

FR36, FR37.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from saddleback.config import Config
from saddleback.types import Segment


def _tokens(text: str) -> set[str]:
    """Cheap, deterministic token set: lowercase alphabetic tokens."""
    out: set[str] = set()
    cur: list[str] = []
    for ch in text.lower():
        if ch.isalpha():
            cur.append(ch)
        else:
            if cur:
                out.add("".join(cur))
                cur = []
    if cur:
        out.add("".join(cur))
    return out


def _jaccard(a: str, b: str) -> float:
    """Cheap Jaccard similarity over tokens — used as a proxy for semantic match.

    NOTE: a real implementation would use multilingual sentence embeddings (e.g.,
    paraphrase-multilingual-MiniLM-L12-v2). This proxy keeps MVP free of an extra
    embedding-model dependency. Score is artificially low for cross-language pairs —
    treat as a relative signal across segments, not an absolute quality metric.
    """
    sa, sb = _tokens(a), _tokens(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _back_transcribe(track_path: Path, lang: str, cfg: Config) -> list[tuple[float, float, str]]:
    """Transcribe synced track per language. Returns list of (start, end, text)."""
    if cfg.runtime.test_mode:
        return []
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return []

    model = WhisperModel(
        cfg.transcribe.model,
        device=cfg.transcribe.device,
        compute_type=cfg.transcribe.compute_type,
    )
    segments_iter, _info = model.transcribe(str(track_path), beam_size=1, language=lang)
    return [(float(s.start), float(s.end), s.text.strip()) for s in segments_iter]


def _segment_overlap(seg: Segment, txt_segments: list[tuple[float, float, str]]) -> str:
    """Concatenate all back-transcribed text whose time window overlaps the source segment."""
    parts: list[str] = []
    for start, end, text in txt_segments:
        if end < seg.start or start > seg.end:
            continue
        parts.append(text)
    return " ".join(parts).strip()


def build_report(
    run_dir: Path,
    segments: list[Segment],
    outputs: dict[str, Path],
    flagged_by_lang: dict[str, list[int]],
    cfg: Config,
) -> dict[str, Any]:
    """Run round-trip transcribe per lang; compute per-segment similarity proxy."""
    per_lang: dict[str, dict[str, Any]] = {}
    for lang, mp4_path in outputs.items():
        track_path = run_dir / "synced" / f"{lang}.wav"
        if not track_path.exists():
            per_lang[lang] = {"output": str(mp4_path), "back_transcribed": False}
            continue

        txt_segments = _back_transcribe(track_path, lang, cfg)
        per_segment: list[dict[str, Any]] = []
        below_threshold: list[int] = []
        for seg in segments:
            back_text = _segment_overlap(seg, txt_segments)
            score = _jaccard(seg.text, back_text)
            if score < cfg.runtime.similarity_threshold:
                below_threshold.append(seg.id)
            per_segment.append(
                {
                    "id": seg.id,
                    "start": seg.start,
                    "end": seg.end,
                    "source_text": seg.text,
                    "back_text": back_text,
                    "similarity_proxy": round(score, 3),
                }
            )

        per_lang[lang] = {
            "output": str(mp4_path),
            "back_transcribed": True,
            "flagged_segments": flagged_by_lang.get(lang, []),
            "below_similarity_threshold": below_threshold,
            "similarity_threshold": cfg.runtime.similarity_threshold,
            "segments": per_segment,
            "note": (
                "similarity_proxy is a token-Jaccard score across languages — a relative "
                "indicator across segments, not an absolute quality metric. Replace with "
                "embedding-based cross-lingual similarity in a later phase."
            ),
        }

    return {
        "run_id": run_dir.name,
        "segment_count": len(segments),
        "languages": per_lang,
    }
