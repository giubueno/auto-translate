# Saddleback

Local-first CLI to dub English meeting MP4s into German and Spanish audio. Runs entirely on macOS Apple Silicon — Whisper transcription, LM Studio (gemma-4-e4b) translation, Qwen3-TTS voice-cloned synthesis, ffmpeg mux. No cloud, no recurring cost, no telemetry.

See [`docs/prd.md`](docs/prd.md) for the full PRD: capability contract (43 FRs), non-functional requirements, phased scope (MVP → Growth → Vision), and architecture decisions.

---

## Table of contents

- [Prerequisites](#prerequisites)
- [Install](#install)
- [Quickstart](#quickstart)
- [Commands](#commands)
- [Configuration](#configuration)
- [Outputs](#outputs)
- [Resume, regenerate, recover](#resume-regenerate-recover)
- [Test mode](#test-mode)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Project status](#project-status)

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **macOS 14+ on Apple Silicon** | M1, M2, M3, or M4. Intel macOS, Linux, and Windows are explicitly out of MVP scope. |
| **Python 3.14** | The CLI enforces this at startup. Use Homebrew (`brew install python@3.14`) or [pyenv](https://github.com/pyenv/pyenv). |
| **ffmpeg** | `brew install ffmpeg`. Tested with ffmpeg 6.x and 8.x. |
| **LM Studio** | Running on the local LAN, OpenAI-compatible API enabled, with the configured translation model loaded. Default endpoint: `http://192.168.0.42:1234/v1`. Default model: `google/gemma-4-e4b`. Both are configurable. |
| **~5 GB free disk** | Qwen3-TTS model (~2 GB), faster-whisper model (~1 GB), per-job intermediates (~1–2 GB for a 30-min source). |
| **16 GB RAM minimum** | Peak resident set during TTS is ~7 GB. The pipeline is single-job; do not run two concurrently. |

---

## Install

```bash
git clone git@github.com:giubueno/auto-translate.git saddleback
cd saddleback

python3.14 -m venv venv
./venv/bin/pip install -e .

# Sanity check: every preflight should be green.
./venv/bin/saddleback doctor
```

`saddleback doctor` checks: Python version, ffmpeg in `PATH`, runs directory writable, LM Studio reachable + correct model loaded, Qwen3-TTS model present in the HuggingFace cache. If any check fails, the CLI prints the exact remediation step.

The first dub run will lazily download the Qwen3-TTS 8-bit model (~2 GB) and the faster-whisper model on first use. Subsequent runs are offline-capable for those stages.

---

## Quickstart

```bash
# Activate the venv once per shell session, OR call ./venv/bin/saddleback directly.
source ./venv/bin/activate

# 1. Preflight — make sure everything is reachable.
saddleback doctor

# 2. Drop a 30-min English meeting MP4 into a directory of your choice.
#    Example assumes ~/Downloads/meeting.mp4 exists.
saddleback dub ~/Downloads/meeting.mp4

# 3. Wait. (~30–45 min for a 30-min source on an M-series Mac.)
#    The CLI prints stage-by-stage progress with rich progress bars.

# 4. Outputs land next to the source:
#    ~/Downloads/meeting_de.mp4
#    ~/Downloads/meeting_es.mp4
```

`saddleback dub` is the primary command. Everything else is for inspection, recovery, or scripting.

---

## Commands

```text
saddleback dub <input.mp4> [--lang de|es|both]
    Run the full pipeline end-to-end. Writes <input>_de.mp4 and/or <input>_es.mp4
    next to the source. Default --lang is 'both'.

saddleback regen <segment-id> [--lang de|es] [--shorter] [--run-id <id>]
    Regenerate one segment of an existing run. Re-translates, re-synthesizes,
    rebuilds only the affected synced track, and re-muxes only the affected
    target MP4. --shorter re-prompts the translator with a 'shorter' instruction
    (use when the segment overflowed the source duration window).

saddleback play <segment-id> [--lang de|es] [--run-id <id>]
    Play a single fitted segment via afplay (macOS) for spot-checking.

saddleback doctor
    Preflight check: Python, ffmpeg, runs dir, LM Studio, TTS model.

saddleback status [<run-id>]
    Print stage-completion status of a job. Defaults to the most recent run.

saddleback clean [<run-id>] [--remove-outputs|--keep-outputs]
    Delete intermediate artifacts (audio.wav, segments.json, translations/,
    tts/, fitted/, synced/). --keep-outputs (default) preserves the final
    dubbed MP4s next to the source.
```

### Global flags (apply to any subcommand)

```text
--config PATH      Explicit config file (TOML).
-q, --quiet        Suppress non-error stdout. Errors still go to stderr.
-v, --verbose      Verbose logging to stderr.
--json             Emit NDJSON status events to stdout (machine-readable).
--no-progress      Disable rich progress bars (set automatically when NO_COLOR is set).
--dry-run          Print the plan, do no work.
--test-mode        Deterministic test mode (see below).
--version          Print version and exit.
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success — both target MP4s produced |
| 1 | Generic / unexpected failure |
| 2 | Misuse / bad CLI arguments |
| 3 | Preflight failed (missing ffmpeg / LM Studio / model) |
| 4 | Source unusable (corrupt MP4, no audio track, silent) |
| 5 | Stage-level failure — manifest records which stage |
| 130 | SIGINT — partial progress preserved, re-run to resume |

---

## Configuration

Configuration is layered. Later layers override earlier ones; arrays of tables merge by key, scalars override.

1. Built-in defaults (in `src/saddleback/config.py`)
2. `~/.config/saddleback/config.toml` (per-user)
3. `./saddleback.toml` (per-project, in CWD)
4. Environment variables (`SADDLEBACK_<SECTION>_<KEY>`)
5. CLI flags (highest priority)

### Example `saddleback.toml`

```toml
[translator]
endpoint        = "http://192.168.0.42:1234/v1"
model           = "google/gemma-4-e4b"
api_key         = "lm-studio"
temperature     = 0.2
max_concurrency = 4

[transcribe]
model        = "large-v3-turbo"   # ~3x faster than large-v3; same default for MVP
device       = "cpu"
compute_type = "int8"
language     = "en"
beam_size    = 5

[tts]
model           = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
sample_rate_out = 24000
ref_min_seconds = 3.0
ref_max_seconds = 8.0
temperature     = 0.7

[output]
formats         = ["mp4"]
copy_video      = true
audio_codec     = "aac"
audio_bitrate_k = 192

[runtime]
runs_dir              = "./runs"
keep_intermediate     = true
parallel_translate    = true
parallel_tts          = false   # serialize TTS to respect 7 GB peak memory ceiling
length_budget_ratio   = 1.3
similarity_threshold  = 0.85

[targets]
languages = ["de", "es"]
```

### Environment overrides

```bash
export SADDLEBACK_TRANSLATOR_ENDPOINT="http://10.0.0.5:1234/v1"
export SADDLEBACK_TRANSLATOR_MODEL="google/gemma-4-31b"
export SADDLEBACK_TRANSCRIBE_MODEL="large-v3"   # pin if turbo regresses
export SADDLEBACK_RUNTIME_RUNS_DIR="/Volumes/scratch/saddleback-runs"
export SADDLEBACK_RUNTIME_TEST_MODE="true"
```

`NO_COLOR=1` disables rich color output (per [no-color.org](https://no-color.org)).

---

## Outputs

Per job, all artifacts live under a single deterministic directory:

```text
runs/<source-stem>-<YYYYMMDD-HHMMSS>/
├── manifest.json                # config snapshot, stage timings, artifact hashes
├── log.txt                      # full plain-text log
├── audio.wav                    # 24 kHz mono extract of source audio
├── ref.wav                      # 3–8 sec voice reference clip
├── segments.json                # [{id, start, end, text}, ...]
├── translations/
│   ├── de.json                  # [{segment_id, lang, text, overflow, attempts}, ...]
│   └── es.json
├── tts/
│   ├── de/seg_NNNN.wav          # raw synthesized clip per segment
│   └── es/seg_NNNN.wav
├── fitted/
│   ├── de/seg_NNNN.wav          # time-fit clip (stretched/compressed to source duration)
│   └── es/seg_NNNN.wav
├── synced/
│   ├── de.wav                   # full-duration assembled track
│   └── es.wav
└── report.json                  # quality report (segment count, flagged segments, similarity)
```

Final dubbed videos land next to the source:

```text
<source>_de.mp4
<source>_es.mp4
```

The video stream is copied (no re-encode); audio is re-encoded to AAC.

---

## Resume, regenerate, recover

### Resume an interrupted job

`saddleback dub <same-source.mp4>` again. The orchestrator detects the existing `runs/<source-stem>-*` directory, inspects which stages have valid artifacts, and skips them. SIGINT, OOM, machine sleep, and transient LM Studio failures all leave the run dir in a state from which the next invocation resumes.

### Regenerate one bad segment

```bash
# Find the offending segment id from the post-run summary or from runs/<id>/report.json.
saddleback regen 42 --lang de --shorter
```

This re-translates segment 42 with a "shorter" prompt instruction, re-synthesizes its TTS clip, refits it to the source duration, rebuilds only the German synced track, and re-muxes only `<source>_de.mp4`. The Spanish output is left untouched. Total time: under 90 seconds for a typical segment.

### Inspect a run

```bash
saddleback status                         # most recent run
saddleback status meeting-20260509-223617 # specific run
```

### Reclaim disk

```bash
saddleback clean                          # remove intermediates, keep dubbed MP4s
saddleback clean --remove-outputs         # remove final MP4s too
```

---

## Test mode

Deterministic, network-free, no model loads. Replaces the LM Studio HTTP client with stub translations (`[de] <source>` / `[es] <source>`) and the TTS engine with a 220 Hz sine-wave stub clipped to source segment duration.

```bash
saddleback dub fixture.mp4 --test-mode
# or:
SADDLEBACK_RUNTIME_TEST_MODE=true saddleback dub fixture.mp4
```

The same input produces byte-identical artifacts across runs (modulo timestamps in the manifest). Suitable for CI, pipeline-shape verification, and demos without burning real model time.

---

## Development

### Run tests

```bash
./venv/bin/pip install -e ".[dev]"
./venv/bin/pytest
```

The test suite (13 tests) covers config layering, the extract stage against a bundled fixture, `.srt` sidecar parsing, the deterministic translate stub, and a full E2E run with a `socket.connect`-blocking guard that proves the pipeline never touches the network in test mode.

### Project layout

```text
saddleback/
├── README.md
├── LICENSE
├── pyproject.toml
├── docs/
│   └── prd.md                  # full PRD (43 FRs, NFRs, scope)
├── src/saddleback/
│   ├── cli.py                  # typer entrypoint (dub, regen, play, doctor, status, clean)
│   ├── config.py               # layered TOML + env + flag config (pydantic)
│   ├── doctor.py               # preflight checks
│   ├── orchestrator.py         # stage runner, manifest, resume, regen orchestration
│   ├── report.py               # round-trip quality report
│   ├── jobdir.py               # run-id, run-dir lookup, file hashing
│   ├── exit_codes.py           # IntEnum for stable exit codes
│   ├── types.py                # Segment, Translation, Manifest, StageStatus pydantic models
│   └── stages/
│       ├── extract.py          # ffmpeg extract + auto ref-clip
│       ├── transcribe.py       # faster-whisper + .srt sidecar fallback
│       ├── translate.py        # async LM Studio + length budget + shorter retry + test-mode stub
│       ├── tts.py              # mlx_audio Qwen3-TTS, serialized, persistent model + test-mode stub
│       ├── build.py            # ffmpeg atempo time-fit + crossfade assembly
│       └── mux.py              # per-language ffmpeg mux
└── tests/
    ├── conftest.py
    ├── fixtures/sample.mp4     # ~4 sec synthetic clip for E2E test
    └── test_*.py
```

### Adding a stage

Each pipeline stage is a self-contained module under `src/saddleback/stages/`. Stages must:

1. Read inputs from artifact paths under `run_dir`.
2. Write outputs as content-addressable artifacts under `run_dir`.
3. Honor `cfg.runtime.test_mode` and provide a stub path that does not touch the network or load heavy models.
4. Surface a stage-specific exception type that the orchestrator maps to exit code 5.

The orchestrator (`orchestrator.py`) records stage status in `manifest.json` and skips stages whose artifacts are present and valid.

---

## Troubleshooting

### `saddleback doctor` fails on `lm_studio`

LM Studio is not reachable, or the configured model is not loaded.

1. Open LM Studio on the host.
2. Load `google/gemma-4-e4b` (or the model named in your config).
3. Start the local server (Settings → Developer → Local Server → Start).
4. Test reachability: `curl http://192.168.0.42:1234/v1/models`.
5. If the host has changed, set `SADDLEBACK_TRANSLATOR_ENDPOINT` or update `saddleback.toml`.

### `saddleback doctor` fails on `tts_model`

The Qwen3-TTS 8-bit model is not in the HuggingFace cache. The first `saddleback dub` invocation will download it (~2 GB). To pre-download:

```bash
huggingface-cli download mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit
```

### `saddleback dub` is unbearably slow at the transcribe stage

By default the project uses `large-v3-turbo`, which is roughly 3× faster than `large-v3` at comparable accuracy on long-form English. If you have pinned `large-v3` in your config and a 30-min source is taking ~30 min just to transcribe, switch back to turbo:

```bash
SADDLEBACK_TRANSCRIBE_MODEL=large-v3-turbo saddleback dub <input.mp4>
```

### A segment in the dubbed output sounds clipped or mangled

The translation overflowed the source segment duration window, and time-fit had to compress beyond the safe distortion threshold. Check the run summary or `report.json` for `flagged_segments`. Then:

```bash
saddleback regen <segment-id> --lang de --shorter
```

### Out of memory during TTS

Peak RSS is ~7 GB. The CLI serializes TTS calls to keep peak bounded. Close other large-memory apps (browsers, IDEs) before a real run. The 0.86B Qwen3-TTS variant uses less RAM at slightly lower quality if needed:

```toml
[tts]
model = "mlx-community/Qwen3-TTS-12Hz-0.86B-Base-8bit"
```

### A run was killed mid-stage

Re-run the same `saddleback dub <same-source.mp4>` command. Resumability is per-stage and per-segment; valid artifacts are reused.

---

## Project status

**Phase 1 (MVP)** — feature-complete per `docs/prd.md`. Live validation in progress: a real 38-min meeting end-to-end pass is the next gate.

Roadmap (see PRD § Project Scoping):

- **Phase 2 (Growth):** selectable target language for any one of Qwen3-TTS's supported languages, glossary / protected-terms file, batch ingest, quality dashboard, optional `.srt` output, lightweight web UI.
- **Phase 3 (Vision):** multi-speaker diarization with per-speaker voice cloning, lip-sync re-render, real-time streaming dub, voice-design presets.

## License

MIT — see [`LICENSE`](LICENSE).
