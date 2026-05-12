"""Stage 4: synthesize translated segments via Qwen3-TTS (mlx_audio).

FR17, FR18, FR19, FR20, FR21.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

import numpy as np

from saddleback.config import Config
from saddleback.types import Segment, Translation


class TtsError(Exception):
    pass


_LANG_TO_QWEN = {"de": "german", "es": "spanish"}


# Persistent model holder. Loaded once per process; serialized via lock (FR21).
class _ModelHolder:
    def __init__(self) -> None:
        self.model = None
        self.lock = threading.Lock()
        self.cfg_signature: tuple | None = None


_holder = _ModelHolder()


def _load_model(cfg: Config):
    try:
        from mlx_audio.tts.utils import load_model
    except ImportError as exc:
        raise TtsError("mlx_audio not installed; pip install mlx-audio") from exc

    sig = (cfg.tts.model,)
    with _holder.lock:
        if _holder.model is None or _holder.cfg_signature != sig:
            _holder.model = load_model(cfg.tts.model)
            _holder.cfg_signature = sig
    return _holder.model


def _save_wav(samples: np.ndarray, sample_rate: int, out_path: Path) -> None:
    import soundfile as sf

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if samples.ndim > 1:
        samples = samples.reshape(-1)
    if samples.dtype != np.float32 and samples.dtype != np.int16:
        samples = samples.astype(np.float32)
    sf.write(str(out_path), samples, sample_rate, subtype="PCM_16")


def _synthesize_one(
    text: str,
    lang: str,
    ref_wav: Path,
    out_path: Path,
    cfg: Config,
) -> None:
    """Serialized: holds the global TTS lock for the entire synth call."""
    import mlx.core as mx

    model = _load_model(cfg)
    lang_code = _LANG_TO_QWEN.get(lang, "auto")

    audio_chunks: list[np.ndarray] = []
    sample_rate = getattr(model, "sample_rate", cfg.tts.sample_rate_out)

    with _holder.lock:
        for result in model.generate(
            text=text,
            ref_audio=str(ref_wav),
            lang_code=lang_code,
            temperature=cfg.tts.temperature,
            speed=cfg.tts.speed,
        ):
            audio = result.audio if hasattr(result, "audio") else result
            if hasattr(audio, "tolist"):
                arr = np.array(audio.tolist(), dtype=np.float32)
            elif isinstance(audio, mx.array):
                arr = np.array(audio.tolist(), dtype=np.float32)
            else:
                arr = np.asarray(audio, dtype=np.float32)
            audio_chunks.append(arr)

    if not audio_chunks:
        raise TtsError(f"TTS produced no audio for '{text[:60]}...' (lang={lang})")
    full = np.concatenate(audio_chunks)
    _save_wav(full, sample_rate, out_path)


def run(
    segments: list[Segment],
    translations_by_lang: dict[str, list[Translation]],
    ref_wav: Path,
    run_dir: Path,
    cfg: Config,
) -> dict[str, dict[int, Path]]:
    """Synthesize each segment for each target language. Resumable. Serialized. (FR20, FR21)"""
    if cfg.runtime.test_mode:
        return _run_test_mode(segments, translations_by_lang, ref_wav, run_dir, cfg)

    out: dict[str, dict[int, Path]] = {}
    seg_by_id = {s.id: s for s in segments}

    for lang, translations in translations_by_lang.items():
        lang_dir = run_dir / "tts" / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        per_seg: dict[int, Path] = {}
        for t in translations:
            seg = seg_by_id[t.segment_id]
            wav_path = lang_dir / f"seg_{seg.id:04d}.wav"
            if wav_path.exists() and wav_path.stat().st_size > 0:
                per_seg[seg.id] = wav_path
                continue
            _synthesize_one(t.text, lang, ref_wav, wav_path, cfg)
            per_seg[seg.id] = wav_path
        out[lang] = per_seg
    return out


def regen_one(
    segment: Segment,
    translation: Translation,
    lang: str,
    ref_wav: Path,
    run_dir: Path,
    cfg: Config,
) -> Path:
    """Regenerate a single TTS clip and overwrite its file. (FR31, FR33)"""
    lang_dir = run_dir / "tts" / lang
    wav_path = lang_dir / f"seg_{segment.id:04d}.wav"
    if cfg.runtime.test_mode:
        _stub_wav(wav_path, segment.duration, cfg.tts.sample_rate_out)
        return wav_path
    _synthesize_one(translation.text, lang, ref_wav, wav_path, cfg)
    return wav_path


# ---- test mode ----


def _stub_wav(path: Path, duration: float, sample_rate: int) -> None:
    """Write a deterministic short tone — placeholder used in test_mode."""
    n = max(int(sample_rate * max(0.1, duration)), 1)
    t = np.linspace(0.0, max(0.1, duration), n, endpoint=False, dtype=np.float32)
    samples = (0.05 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)
    _save_wav(samples, sample_rate, path)


def _run_test_mode(
    segments: list[Segment],
    translations_by_lang: dict[str, list[Translation]],
    ref_wav: Path,
    run_dir: Path,
    cfg: Config,
) -> dict[str, dict[int, Path]]:
    out: dict[str, dict[int, Path]] = {}
    seg_by_id = {s.id: s for s in segments}
    for lang, translations in translations_by_lang.items():
        lang_dir = run_dir / "tts" / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        per_seg: dict[int, Path] = {}
        for t in translations:
            seg = seg_by_id[t.segment_id]
            wav_path = lang_dir / f"seg_{seg.id:04d}.wav"
            if not wav_path.exists() or wav_path.stat().st_size == 0:
                _stub_wav(wav_path, seg.duration, cfg.tts.sample_rate_out)
            per_seg[seg.id] = wav_path
        out[lang] = per_seg
    _ = ref_wav  # ref_wav presence verified by caller; unused in test_mode
    return out
