"""Stage 5: time-fit each TTS clip to source segment duration; assemble synced track.

FR22, FR23, FR24, FR25.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from saddleback.config import Config
from saddleback.types import Segment


class BuildError(Exception):
    pass


# Fit thresholds — distortion bounds.
MIN_RATIO = 0.7   # don't slow down beyond 0.7x (would over-stretch)
MAX_RATIO = 1.5   # don't speed up beyond 1.5x (would under-fit)


def _atempo_chain(ratio: float) -> list[str]:
    """ffmpeg's atempo only accepts [0.5, 100.0]; chain filters for extreme ratios."""
    if ratio <= 0:
        raise BuildError(f"invalid atempo ratio {ratio}")
    chain: list[str] = []
    while ratio > 2.0:
        chain.append("atempo=2.0")
        ratio /= 2.0
    while ratio < 0.5:
        chain.append("atempo=0.5")
        ratio /= 0.5
    chain.append(f"atempo={ratio:.6f}")
    return chain


def _wav_duration(path: Path) -> float:
    info = sf.info(str(path))
    return info.frames / float(info.samplerate)


def _time_fit_clip(in_wav: Path, target_seconds: float, out_wav: Path) -> tuple[bool, float]:
    """Stretch/compress in_wav to target_seconds using ffmpeg atempo. Returns (overflow_flagged, achieved_seconds)."""
    if shutil.which("ffmpeg") is None:
        raise BuildError("ffmpeg not found in PATH")

    src_dur = _wav_duration(in_wav)
    if src_dur <= 0:
        raise BuildError(f"clip {in_wav} has zero duration")
    if target_seconds <= 0:
        raise BuildError(f"target duration must be positive; got {target_seconds}")

    raw_ratio = src_dur / target_seconds
    flagged = raw_ratio < MIN_RATIO or raw_ratio > MAX_RATIO
    ratio = max(MIN_RATIO, min(MAX_RATIO, raw_ratio))

    chain = ",".join(_atempo_chain(ratio))
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(in_wav),
        "-filter:a",
        chain,
        "-c:a",
        "pcm_s16le",
        str(out_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise BuildError(f"ffmpeg atempo failed: {result.stderr.strip()}")
    return flagged, _wav_duration(out_wav)


def _assemble_track(
    fitted_clips: list[tuple[Segment, Path]],
    total_duration: float,
    sample_rate: int,
    out_wav: Path,
    crossfade_ms: int = 30,
) -> None:
    """Lay each fitted clip at its source `start` position. Crossfade across silent gaps."""
    total_samples = int(round(total_duration * sample_rate))
    track = np.zeros(total_samples, dtype=np.float32)

    fade_samples = max(1, int(round(sample_rate * crossfade_ms / 1000.0)))
    fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)

    for seg, clip in fitted_clips:
        data, sr = sf.read(str(clip), dtype="float32", always_2d=False)
        if sr != sample_rate:
            raise BuildError(
                f"clip {clip} sample rate {sr} != track sample rate {sample_rate}; "
                f"all clips must be resampled before assembly"
            )
        if data.ndim > 1:
            data = data.mean(axis=1)

        start_idx = int(round(seg.start * sample_rate))
        end_idx = start_idx + len(data)
        if end_idx > total_samples:
            data = data[: total_samples - start_idx]
            end_idx = total_samples
        if start_idx >= total_samples:
            continue

        # Apply fades to the clip itself.
        clip_local = data.copy()
        if len(clip_local) >= 2 * fade_samples:
            clip_local[:fade_samples] *= fade_in
            clip_local[-fade_samples:] *= fade_out

        # Mix into track (handles overlapping windows safely).
        track[start_idx:end_idx] += clip_local

    # Soft clip protection.
    np.clip(track, -1.0, 1.0, out=track)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), track, sample_rate, subtype="PCM_16")


def run(
    segments: list[Segment],
    tts_paths_by_lang: dict[str, dict[int, Path]],
    audio_wav: Path,
    run_dir: Path,
    cfg: Config,
) -> tuple[dict[str, Path], dict[str, list[int]]]:
    """Time-fit + assemble per-lang synced tracks. Returns ({lang: track_path}, {lang: [flagged_seg_ids]})."""
    sample_rate = cfg.tts.sample_rate_out
    total_duration = _wav_duration(audio_wav)

    seg_by_id = {s.id: s for s in segments}
    out_paths: dict[str, Path] = {}
    flagged: dict[str, list[int]] = {}

    for lang, per_seg in tts_paths_by_lang.items():
        fitted_dir = run_dir / "fitted" / lang
        fitted_dir.mkdir(parents=True, exist_ok=True)
        fitted_clips: list[tuple[Segment, Path]] = []
        flagged_ids: list[int] = []

        for seg_id, tts_clip in per_seg.items():
            seg = seg_by_id[seg_id]
            fitted_path = fitted_dir / f"seg_{seg_id:04d}.wav"
            if not fitted_path.exists() or fitted_path.stat().st_size == 0:
                is_flagged, _achieved = _time_fit_clip(tts_clip, seg.duration, fitted_path)
                if is_flagged:
                    flagged_ids.append(seg_id)
            else:
                # Recompute flag status from existing files.
                src_dur = _wav_duration(tts_clip)
                ratio = src_dur / seg.duration if seg.duration > 0 else 1.0
                if ratio < MIN_RATIO or ratio > MAX_RATIO:
                    flagged_ids.append(seg_id)
            fitted_clips.append((seg, fitted_path))

        track_path = run_dir / "synced" / f"{lang}.wav"
        _assemble_track(
            fitted_clips=fitted_clips,
            total_duration=total_duration,
            sample_rate=sample_rate,
            out_wav=track_path,
        )
        out_paths[lang] = track_path
        flagged[lang] = sorted(flagged_ids)

    return out_paths, flagged


def rebuild_one(
    segments: list[Segment],
    tts_paths_by_lang: dict[str, dict[int, Path]],
    audio_wav: Path,
    run_dir: Path,
    cfg: Config,
    lang: str,
    segment_id: int,
) -> tuple[Path, list[int]]:
    """Refit just the one segment, then re-assemble the affected language's full synced track."""
    sample_rate = cfg.tts.sample_rate_out
    total_duration = _wav_duration(audio_wav)
    seg_by_id = {s.id: s for s in segments}

    per_seg = tts_paths_by_lang[lang]
    fitted_dir = run_dir / "fitted" / lang
    fitted_dir.mkdir(parents=True, exist_ok=True)

    seg = seg_by_id[segment_id]
    tts_clip = per_seg[segment_id]
    fitted_path = fitted_dir / f"seg_{segment_id:04d}.wav"
    is_flagged, _ = _time_fit_clip(tts_clip, seg.duration, fitted_path)

    flagged_ids: list[int] = []
    fitted_clips: list[tuple[Segment, Path]] = []
    for sid, clip in per_seg.items():
        seg_i = seg_by_id[sid]
        fp = fitted_dir / f"seg_{sid:04d}.wav"
        if sid == segment_id and is_flagged:
            flagged_ids.append(sid)
        elif fp.exists():
            src_dur = _wav_duration(clip)
            ratio = src_dur / seg_i.duration if seg_i.duration > 0 else 1.0
            if ratio < MIN_RATIO or ratio > MAX_RATIO:
                flagged_ids.append(sid)
        fitted_clips.append((seg_i, fp))

    track_path = run_dir / "synced" / f"{lang}.wav"
    _assemble_track(
        fitted_clips=fitted_clips,
        total_duration=total_duration,
        sample_rate=sample_rate,
        out_wav=track_path,
    )
    return track_path, sorted(flagged_ids)
