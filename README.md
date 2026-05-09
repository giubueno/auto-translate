# Saddleback

Local-first CLI to dub English meeting MP4s into German and Spanish audio. Runs entirely on macOS Apple Silicon — Whisper transcription, LM Studio (gemma-4-e4b) translation, Qwen3-TTS voice-cloned synthesis, ffmpeg mux. No cloud, no recurring cost, no telemetry.

See `docs/prd.md` for the full Product Requirements Document including capability contract (43 FRs), non-functional requirements, and phased scope (MVP → Growth → Vision).

## Requirements

- macOS 14.x+ on Apple Silicon (M1/M2/M3/M4)
- Python 3.14
- ffmpeg (`brew install ffmpeg`)
- LM Studio running on the local LAN with `google/gemma-4-e4b` loaded (default endpoint: `http://192.168.0.42:1234/v1` — configurable)

## Install

```bash
python3.14 -m venv venv
./venv/bin/pip install -e .
```

## Usage

```bash
saddleback doctor                     # preflight: ffmpeg, LM Studio, models, runs dir
saddleback dub meeting.mp4            # full pipeline: extract → transcribe → translate → tts → time-fit → mux
saddleback dub meeting.mp4 --lang de  # German only
saddleback regen 42 --shorter         # regenerate segment 42 with shorter translation
saddleback play 42 --lang de          # spot-check a single segment
saddleback status                     # stage-completion of most recent run
saddleback clean                      # remove intermediate artifacts, keep dubbed MP4s
```

## Test mode

Deterministic, network-free, no model loads:

```bash
saddleback dub meeting.mp4 --test-mode
```

Uses stub translations and stub TTS clips. Useful in CI and for pipeline-shape verification.

## Project status

**Phase 1 (MVP)** — see `docs/prd.md` for full scope.
