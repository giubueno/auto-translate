from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from saddleback.config import Config
from saddleback.stages import audio_export


def _make_synced_wav(path: Path, seconds: float = 1.0, sample_rate: int = 24000) -> None:
    samples = np.zeros(int(sample_rate * seconds), dtype=np.float32)
    sf.write(str(path), samples, sample_rate, subtype="PCM_16")


def _ffmpeg_or_skip():
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")


def test_wav_export_is_a_copy(tmp_path: Path):
    cfg = Config()
    synced = tmp_path / "synced_de.wav"
    _make_synced_wav(synced)
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"fake-mp4-bytes")

    out = audio_export.export_one(synced, source, "de", "wav", cfg)
    assert out == tmp_path / "meeting_de.wav"
    assert out.read_bytes() == synced.read_bytes()


def test_m4a_export_uses_ffmpeg(tmp_path: Path):
    _ffmpeg_or_skip()
    cfg = Config()
    synced = tmp_path / "synced_de.wav"
    _make_synced_wav(synced, seconds=0.5)
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"fake-mp4-bytes")

    out = audio_export.export_one(synced, source, "de", "m4a", cfg)
    assert out == tmp_path / "meeting_de.m4a"
    assert out.exists()
    assert out.stat().st_size > 0


def test_unsupported_format_rejected(tmp_path: Path):
    cfg = Config()
    synced = tmp_path / "synced_de.wav"
    _make_synced_wav(synced)
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"fake")
    with pytest.raises(audio_export.AudioExportError):
        audio_export.export_one(synced, source, "de", "flac", cfg)


def test_run_exports_all_langs(tmp_path: Path):
    cfg = Config()
    de_synced = tmp_path / "de.wav"
    es_synced = tmp_path / "es.wav"
    _make_synced_wav(de_synced)
    _make_synced_wav(es_synced)
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"fake")

    out = audio_export.run(
        source=source,
        synced_tracks_by_lang={"de": de_synced, "es": es_synced},
        fmt="wav",
        cfg=cfg,
    )
    assert set(out) == {"de", "es"}
    assert out["de"].name == "meeting_de.wav"
    assert out["es"].name == "meeting_es.wav"
    assert out["de"].exists() and out["es"].exists()


def test_config_audio_export_validator():
    from pydantic import ValidationError

    from saddleback.config import OutputConfig

    assert OutputConfig().audio_export is None
    assert OutputConfig(audio_export="wav").audio_export == "wav"
    assert OutputConfig(audio_export="").audio_export is None
    assert OutputConfig(audio_export="false").audio_export is None
    with pytest.raises(ValidationError):
        OutputConfig(audio_export="flac")
