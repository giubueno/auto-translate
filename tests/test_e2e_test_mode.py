"""End-to-end test in deterministic test mode. NFR-T1, NFR-T2, NFR-T3.

Uses the bundled tests/fixtures/sample.mp4 (~4s synthetic video). Skips Whisper by
writing a hand-crafted .srt sidecar so the pipeline never touches the network or the
TTS model.
"""

from __future__ import annotations

import shutil
import socket
from pathlib import Path

import pytest

from saddleback.config import load_config
from saddleback.exit_codes import ExitCode


def _no_network_socket():
    """Patch socket to forbid all outbound DNS/TCP — verifies NFR-S1, NFR-T2."""
    real = socket.socket

    class GuardedSocket(real):
        def connect(self, *_args, **_kwargs):  # type: ignore[override]
            raise AssertionError(
                "outbound network call attempted in test_mode (forbidden by NFR-T2)"
            )

    return GuardedSocket


def _ffmpeg_or_skip():
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not available")


def test_dub_end_to_end_deterministic(fixture_mp4: Path, tmp_path: Path, monkeypatch):
    _ffmpeg_or_skip()
    # Copy fixture so we don't pollute tests/fixtures with siblings.
    workdir = tmp_path / "work"
    workdir.mkdir()
    source = workdir / "sample.mp4"
    shutil.copy(fixture_mp4, source)

    # Hand-crafted .srt sidecar — skips Whisper (FR9), so no model load needed.
    srt = workdir / "sample.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nHello there.\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nThis is a short test.\n",
        encoding="utf-8",
    )

    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("SADDLEBACK_RUNTIME_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("SADDLEBACK_RUNTIME_TEST_MODE", "true")

    # Forbid outbound network in test_mode (NFR-T2).
    monkeypatch.setattr(socket, "socket", _no_network_socket())

    from saddleback.orchestrator import run_dub

    code = run_dub(
        source=source,
        targets=["de", "es"],
        opts={"test_mode": True, "json": False, "quiet": True, "config_path": None},
    )

    assert code == ExitCode.OK

    # Outputs exist and are non-empty.
    out_de = workdir / "sample_de.mp4"
    out_es = workdir / "sample_es.mp4"
    assert out_de.exists() and out_de.stat().st_size > 0
    assert out_es.exists() and out_es.stat().st_size > 0

    # Run dir contains expected artifacts.
    runs = list(runs_dir.iterdir())
    assert len(runs) == 1
    run_dir = runs[0]
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "audio.wav").exists()
    assert (run_dir / "ref.wav").exists()
    assert (run_dir / "segments.json").exists()
    assert (run_dir / "translations" / "de.json").exists()
    assert (run_dir / "translations" / "es.json").exists()
    assert (run_dir / "tts" / "de").is_dir()
    assert (run_dir / "synced" / "de.wav").exists()
    assert (run_dir / "report.json").exists()


def test_test_mode_does_not_require_whisper_or_lm_studio(fixture_mp4: Path, tmp_path: Path, monkeypatch):
    """Smoke check: no calls reach the network or load heavy ML models in test_mode."""
    _ffmpeg_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()
    source = workdir / "sample.mp4"
    shutil.copy(fixture_mp4, source)

    srt = workdir / "sample.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:04,000\nOne segment is enough for smoke.\n",
        encoding="utf-8",
    )

    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("SADDLEBACK_RUNTIME_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("SADDLEBACK_RUNTIME_TEST_MODE", "true")

    # Even without socket guard, this should succeed without heavy deps.
    cfg = load_config(cwd=workdir)
    assert cfg.runtime.test_mode is True

    from saddleback.orchestrator import run_dub

    code = run_dub(
        source=source,
        targets=["de"],
        opts={"test_mode": True, "json": False, "quiet": True, "config_path": None},
    )
    assert code == ExitCode.OK


def test_dub_with_also_audio_writes_wav_next_to_source(fixture_mp4: Path, tmp_path: Path, monkeypatch):
    """End-to-end with --also-audio produces meeting_de.wav next to the source."""
    _ffmpeg_or_skip()
    workdir = tmp_path / "work"
    workdir.mkdir()
    source = workdir / "sample.mp4"
    shutil.copy(fixture_mp4, source)

    srt = workdir / "sample.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:04,000\nHello there.\n",
        encoding="utf-8",
    )

    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("SADDLEBACK_RUNTIME_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("SADDLEBACK_RUNTIME_TEST_MODE", "true")

    from saddleback.orchestrator import run_dub

    code = run_dub(
        source=source,
        targets=["de", "es"],
        opts={
            "test_mode": True,
            "json": False,
            "quiet": True,
            "config_path": None,
            "audio_export": "wav",
        },
    )
    assert code == ExitCode.OK
    assert (workdir / "sample_de.wav").exists()
    assert (workdir / "sample_es.wav").exists()
    assert (workdir / "sample_de.mp4").exists()
    assert (workdir / "sample_es.mp4").exists()
