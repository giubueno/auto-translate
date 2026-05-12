---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
releaseMode: phased
inputDocuments: []
workflowType: 'prd'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 0
classification:
  projectType: cli_tool
  projectSubtype: rich-cli
  domain: general
  complexity: medium-high
  projectContext: greenfield
  userBase: single-user-personal-tool
visionInsights:
  vision: "Local Mac CLI that dubs English meeting recordings into German and Spanish audio, so native-speaker colleagues can follow along with low cognitive load."
  successCriterion: "Low cognitive load: audience listens, does not translate-while-watching."
  whatMakesItSpecial:
    - "Fully local (privacy, zero recurring cost)"
    - "Pragmatic quality bar: understandable beats broadcast-perfect"
    - "Voice-cloned from source presenter (continuity, not perfection)"
    - "Single-user personal tool, no platform ceremony"
  coreInsight: "Local TTS (Qwen3-TTS via mlx_audio) and local LLM translation (LM Studio + gemma-4-e4b) just crossed the 'good-enough' threshold. Cloud no longer required."
  whyNow: "Local TTS hit good-enough quality (Qwen3-TTS spike validated DE+ES voice clone)."
mvpReference:
  sourceDuration: "~30 min MP4"
  sourceLang: en
  targetLangs: [de, es]
  speakers: 1
  speakerType: solo-presenter (meetings)
discoveryNotes:
  - "Drop TUI; use rich-CLI (rich.progress + rich.live + click/typer)"
  - "UX-Spec post-PRD = light pass (no full UX workflow)"
  - "Single speaker confirmed; no diarization in MVP"
  - "Conditional ingest path: auto-detect .srt sidecar to skip Whisper"
  - "Per-segment regen via CLI flag, not interactive surface"
externalDependencies:
  translator:
    provider: "LM Studio (OpenAI-compatible API)"
    endpoint: "configurable via SADDLEBACK_TRANSLATOR_ENDPOINT; defaults to http://localhost:1234/v1"
    model: "google/gemma-4-e4b"
    smokeTest: "PASS (DE+ES idiomatic output)"
  tts:
    library: "mlx_audio"
    model: "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
    spikeResult: "PASS (DE+ES voice-cloned, RTF 1.4-2.2x M-series, 7GB peak)"
  transcribe:
    library: "faster-whisper"
    model: "large-v3-turbo"
  mux: "ffmpeg"
proposedNfrs:
  - "Deterministic test mode (mocked LM Studio + cached TTS)"
  - "Long-audio segment drift <= +/-200ms over >5min source"
  - "Translation length budget ratio <= 1.3x, regen on overflow"
  - "(SOFTENED) Voice consistency across segments — relaxed since 'understandable' is the bar"
  - "Memory ceiling: single-job, 7GB peak, 16GB Mac safe"
  - "Resumable per-stage (artifact-driven)"
  - "Version pinning: requirements.txt + git SHAs per release"
---

# Product Requirements Document - Saddleback Video Dub CLI

**Author:** Giulliano
**Date:** 2026-05-09

## Executive Summary

Saddleback Video Dub is a local-first command-line tool for macOS Apple Silicon that converts an English meeting recording (MP4) into German and Spanish audio dubs the original presenter's colleagues can follow with low cognitive load. Designed as a single-user personal utility, it removes the manual loop of hiring interpreters, generating subtitles, or routing recordings through cloud translation services.

The tool addresses a concrete pain: solo-presenter meeting recordings — pitch decks, demos, internal updates — that need to circulate to non-English-speaking team members without forcing them to translate-while-watching. Output targets `~30 min` MP4 sources, produces `_de.mp4` and `_es.mp4` artifacts, and runs end-to-end on the operator's own Mac without sending audio, transcript, or text to any third-party service.

### What Makes This Special

- **Fully local pipeline.** Transcription (faster-whisper), translation (LM Studio + `google/gemma-4-e4b` over OpenAI-compatible API), and TTS (Qwen3-TTS via `mlx_audio`) run on-device. Privacy by construction; zero recurring cost.
- **Voice-cloned continuity, not perfection.** A 3–8 second reference clip from the source speaker is reused for every segment in both target languages. Audience hears one consistent voice rather than a generic synthetic narrator. Voice fidelity is a convenience, not a quality gate — *understandable* is the bar.
- **"Good-enough" is the unlock.** Local TTS quality on Apple Silicon (Qwen3-TTS 8-bit MLX) and local LLM translation quality (gemma-4-e4b) crossed the usability threshold during the spike phase. Cloud is no longer required for this workflow, which is what makes the tool viable now.
- **Pragmatic CLI surface.** A `rich`-styled command-line interface (not a TUI) with stage-by-stage progress and resumable artifacts. Per-segment regeneration is exposed via flags rather than an interactive UI.

## Project Classification

- **Project Type:** `cli_tool` (rich-CLI variant; not a TUI)
- **Domain:** general (no regulated-industry constraints)
- **Complexity:** medium-high — five external runtime dependencies (ffmpeg, faster-whisper, LM Studio HTTP, mlx_audio + Qwen3-TTS model, rich rendering), each with its own failure surface; multi-stage pipeline with strict per-segment timing constraints; resumability and deterministic test mode required
- **Project Context:** greenfield
- **User Base:** single-user personal tool (operator = primary author and sole consumer of the CLI itself; secondary audience consumes the dubbed video output)

## Success Criteria

### User Success

- **Operator (Giulliano):** Can drop a 30-min English meeting MP4 into a directory, run a single command, and have `<source>_de.mp4` and `<source>_es.mp4` ready to share within 60 minutes on an M-series Mac without manual intervention.
- **Audience (DE/ES colleagues):** Can play the dubbed MP4 once, end-to-end, and accurately recall the meeting's main points without re-watching, without consulting an interpreter, and without translating-while-listening. *Low cognitive load* is the primary qualitative target.
- **Recovery:** When the operator catches a bad segment in preview, they can regenerate that segment alone (translation, TTS, or both) via a CLI flag in under 90 seconds, without re-running upstream stages.

### Business Success

> *Single-user personal tool — "business success" reframed as operational adoption.*

- **Adoption by operator:** ≥ 1 dub job per week sustained for 8 consecutive weeks after MVP completion (proves it's actually usable, not just shipped).
- **Adoption by audience:** ≥ 2 internal teammates report they prefer the dubbed version over the original EN recording for the same meeting (sample of 3 dubbed videos).
- **Cost containment:** Zero recurring spend (no cloud TTS/translation invoice). One-time hardware constraint: must run on operator's existing Mac (no upgrade required).

### Technical Success

- **End-to-end success rate:** ≥ 95% of 30-min source MP4s complete the full pipeline without manual intervention (failures isolated and reported, not silent).
- **Translation quality gate:** ≥ 90% of segments accepted on first pass (no manual regen) for typical meeting content (no proprietary jargon).
- **Voice intelligibility:** Whisper round-trip transcription of dubbed audio matches source semantic intent (judged by sentence-level similarity ≥ 0.85, e.g., via embedding cosine sim) for ≥ 95% of segments.
- **Memory ceiling:** Peak RSS ≤ 8 GB during TTS. Runs on 16 GB Mac with other apps open.
- **Determinism:** Test mode with mocked LM Studio + cached TTS produces byte-identical output across runs (locked seeds, recorded responses).

### Measurable Outcomes

| Outcome | Threshold | How measured |
|---|---|---|
| End-to-end runtime | ≤ 60 min for 30-min source | Wall-clock timing per stage |
| Pipeline success rate | ≥ 95% | Successful job count / total job count over 20 jobs |
| First-pass segment acceptance | ≥ 90% | Segments not flagged for regen on review |
| Round-trip semantic similarity | ≥ 0.85 | Embedding cosine on Whisper transcript vs source |
| Peak memory | ≤ 8 GB RSS | macOS Activity Monitor / `psutil` snapshot |
| Per-segment regen time | ≤ 90 s | Wall-clock from flag invocation to artifact written |
| Recurring cost | $0 | Invoice review |

## User Journeys

### Persona 1 — Giulliano (Operator)

**Backstory:** Tech operator at small German-Spanish-English team. Records weekly demo and pitch sessions in English. Some teammates struggle with English meetings, miss context, ask for replays. Manual subtitling burns hours; cloud TTS feels invasive (recordings contain internal product details). Has an M-series Mac that already runs faster-whisper and LM Studio for other tasks.

**Goal:** Ship a 30-minute meeting recording to DE and ES audiences within an hour, without leaving his Mac.

**Obstacle:** No tool exists that ties local Whisper + local LLM translation + local Apple-Silicon TTS into one repeatable pipeline. Stitching scripts by hand each week is tedious and error-prone.

#### Journey 1A — Happy Path: "From Drop to Dub"

**Opening Scene.** Friday afternoon. Giulliano just finished recording `weekly-demo-2026-05-08.mp4` — a 28-minute solo product walkthrough in English. He drops it into `~/dub/incoming/`.

**Rising Action.**
1. Runs `saddleback dub weekly-demo-2026-05-08.mp4`.
2. CLI confirms: source detected, no `.srt` sidecar, both DE and ES targets, 28:14 duration. Asks `[y/N]`. Confirms.
3. Stage 1 — *Extract audio.* Bar fills in seconds. Source ref clip auto-extracted from longest contiguous speech window.
4. Stage 2 — *Transcribe.* faster-whisper large-v3-turbo chews through audio. Per-segment count rises live. ~2 min.
5. Stage 3 — *Translate.* LM Studio at the configured endpoint reachable, `gemma-4-e4b` loaded. Per-segment progress for DE, then ES. ~5 min combined.
6. Stage 4 — *TTS.* Qwen3-TTS via `mlx_audio` synthesizes DE then ES, segment by segment. Per-segment RTF shown live. ~30 min combined.
7. Stage 5 — *Time-fit + Build.* Each segment stretched/compressed to source timing window. Crossfade across gaps. Audible warning lights up if any segment exceeded length budget (none did).
8. Stage 6 — *Mux.* `weekly-demo-2026-05-08_de.mp4` and `_es.mp4` written next to the source.

**Climax.** Final `rich`-styled summary table shows: total runtime 41 min, 187 segments, 0 regen warnings, both targets ≥ 0.87 round-trip semantic similarity. Two output paths printed.

**Resolution.** Giulliano plays the first 30 seconds of `_de.mp4` to spot-check, sounds right, posts both files to the team Slack. Total wall-clock: 45 minutes including the spot-check.

#### Journey 1B — Edge Case: "Bad Segment Recovery"

**Opening Scene.** Same workflow as 1A, but at the post-run summary Giulliano notices segment 042 in `_de.mp4` flagged with a `length_overflow` warning — DE translation was too long, time-fit clipped it.

**Rising Action.**
1. Plays segment 042 alone via `saddleback play 042 --lang de`. Confirms it cuts off mid-word.
2. Runs `saddleback regen 042 --lang de --shorter`. CLI re-prompts the translator with a shorter-form instruction, re-synthesizes the TTS, time-fits.
3. ~30 seconds later, regen artifact lands. CLI auto-rebuilds the synced audio (only the affected window), re-muxes only the DE output.

**Climax.** Plays segment 042 again, fits cleanly within the source window, no clip-off.

**Resolution.** Total recovery time: under 90 seconds. Giulliano re-shares the corrected `_de.mp4`. He never had to touch the ES output, never re-ran Whisper, never re-loaded a 7 GB TTS model from scratch (resumable artifacts made the rebuild cheap).

**Failure modes covered:**
- LM Studio unreachable on launch → CLI fails fast with the endpoint URL and the `curl /v1/models` command to test.
- TTS model OOM mid-job → CLI catches the OS signal, writes a partial-stage marker, exits non-zero. Re-run picks up where it left off.
- Source has no usable speech (silent video) → fails at extract-ref-clip stage with an actionable error.

---

### Persona 2 — Anja (DE-Speaking Teammate, Audience)

**Backstory:** Engineering manager based in Munich. Native German, professional but tiring English. Joins recordings of meetings she missed; usually opens transcripts in a second window and reads while listening. Loses 30% of the nuance. Stops watching ~halfway through.

**Goal:** Catch up on the weekly demo without parking 60 minutes of focused effort to translate-while-watching.

**Obstacle:** Subtitles distract from the demo on screen; manual transcript translation is async and slow.

#### Journey 2 — Audience Playback

**Opening Scene.** Monday morning. Anja sees `weekly-demo-2026-05-08_de.mp4` posted in #team-recordings. She queues it during her commute.

**Rising Action.**
1. Plays the file in her usual video app. Same visuals as the EN source.
2. Audio is German. Voice is Giulliano's — same cadence, same intonation as if he were speaking to her live.
3. She listens passively. Catches every product-detail moment. Doesn't open the transcript window.
4. At minute 12, a slightly stilted segment plays — a translation that sounds 90% natural. She continues anyway, meaning still clear.

**Climax.** End of the recording. She closes the app and writes a one-line follow-up question in Slack — about a feature mentioned at minute 22. She would not have caught that detail in the EN version.

**Resolution.** She reports to Giulliano: "Vielen Dank, das war sehr hilfreich." First time she's followed a full-length demo without context loss.

---

### Persona 3 — Operator First-Run (Setup Journey)

**Opening Scene.** Fresh Mac. Giulliano clones the repo for the first time on a new machine.

**Rising Action.**
1. `make setup` (or equivalent) creates Python 3.14 venv, installs pinned `requirements.txt`.
2. First `saddleback dub` invocation runs a self-check: ffmpeg present, LM Studio reachable, Qwen3-TTS model downloadable. Reports any failure with exact remediation steps (e.g., `brew install ffmpeg`, `start LM Studio and load gemma-4-e4b`).
3. First TTS run downloads the ~2 GB Qwen3-TTS 8-bit model from HuggingFace. CLI shows the progress.

**Climax.** Self-check passes. Pipeline runs end-to-end on a tiny 30-second test clip shipped in the repo (`tests/fixtures/sample.mp4`). Output plays correctly.

**Resolution.** Setup complete in ≤ 20 minutes including the model download. Same `saddleback dub` command works for real jobs from then on.

---

### Journey Requirements Summary

| Journey | Capabilities required |
|---|---|
| 1A — Happy Path | Single-command CLI; pipeline orchestrator; per-stage progress UI (`rich`); audio extract; auto-detect `.srt`; Whisper transcribe; LM Studio translate (DE+ES); Qwen3-TTS synth; voice ref clip auto-extraction; segment time-fit; audio build with crossfade; ffmpeg mux; round-trip semantic similarity scorer; summary report |
| 1B — Bad Segment Recovery | Per-segment artifact addressing (`segment N`); regen subcommand; "shorter" re-prompt mode for translator; partial audio rebuild; partial mux; resumability (skip stages with valid artifacts) |
| 2 — Audience Playback | (No CLI surface for audience) — relies on dub *quality*: voice consistency, low cognitive load, intelligibility ≥ threshold from Success Criteria |
| 3 — First-Run Setup | Self-check / preflight subcommand (`saddleback doctor`); pinned dependency manifest; model auto-download; bundled tiny test fixture; actionable error messages with remediation hints |

Capabilities NOT directly revealed (out of MVP):
- Admin/multi-user surface (single-user tool)
- API consumer surface (no programmatic API in MVP — CLI only)
- Support/troubleshooting external surface (`doctor` subcommand handles operator-side troubleshooting)

## Domain-Specific Requirements

> Domain is `general` (no regulatory regime applies). This section captures the few constraints that come from the *operating context* — privacy expectations of recorded meetings, third-party model licensing, and the local LAN integration — rather than from any regulator.

### Compliance & Regulatory

- **Not applicable.** No HIPAA, GDPR-special-category, FDA, PCI-DSS, SOC2, or sector-specific regulation governs this tool. Source meeting recordings remain on the operator's machine and on the local LAN where LM Studio runs; no third-party processor is engaged.
- **GDPR — general posture only:** Audio of identifiable speakers (operator and any incidental voices in source) is "personal data" by definition. Mitigated entirely by *no data leaves the local network*. Recordings remain under the operator's control; no retention beyond what the operator chooses to keep on disk.

### Technical Constraints

- **Privacy by construction.** No external HTTP egress is permitted by design for any pipeline stage in MVP. The translator endpoint is on `localhost` or the operator's LAN (configured per-operator via env var or local config; never committed). Whisper, mlx_audio, and ffmpeg are all on-device. Any future cloud option must be a deliberate, opt-in addition.
- **Integration boundary — LM Studio.** The translator dependency is reached over an OpenAI-compatible HTTP API on the local network. The tool MUST NOT hard-code the host or model — both are configurable. Reachability check (`GET /v1/models`) MUST run before any translation work begins, with a clear failure message including the configured URL.
- **Model licensing — operator's responsibility.** Qwen3-TTS (Apache-2.0 weights via `mlx-community`), `gemma-4-e4b` (Gemma terms), `faster-whisper` / OpenAI Whisper (MIT). All permissive for personal use. The PRD does not redistribute models; operator pulls them from HuggingFace / LM Studio directly. License terms are noted in the README, not enforced in code.
- **Local file-system trust boundary.** All artifacts (audio, transcripts, translations, TTS clips, intermediate state) live under a single job directory (`runs/<timestamp>/`). The tool reads/writes only within this tree plus the source MP4's directory. No system-wide writes.

### Integration Requirements

- **LM Studio (local LAN):** OpenAI-compatible chat completions endpoint. Configurable host + port + model name. Must support text-in / text-out (no tool use, no streaming required for MVP).
- **HuggingFace Hub (one-time / cache):** Model weight download for Qwen3-TTS and `faster-whisper`. Cached under `~/.cache/huggingface/`. Subsequent runs are offline-capable once cached.
- **ffmpeg (local binary):** Required for audio extract and final mux. Discovered via `PATH`. Version pin tested against ffmpeg 6.x and 8.x (per spike).

### Risk Mitigations

| Risk | Mitigation |
|---|---|
| Recording leaks via accidental cloud call | Hard policy: no cloud SDKs in dependency list; integration tests assert no outbound DNS to non-LAN IPs |
| Translator host changes IP / goes offline | Configurable endpoint + preflight reachability check + actionable error |
| Model weights pulled from compromised source | Pin model revision SHAs in config (HuggingFace `revision=` parameter), not just `main` |
| Audio of identifiable third parties on call | Out of MVP scope — single solo-presenter meetings only. Multi-party recordings are explicitly NOT supported in MVP and the CLI MAY refuse to dub if diarization detects multiple speakers (Growth phase) |

## CLI Tool Specific Requirements

### Project-Type Overview

Saddleback is a scriptable CLI built with `typer` (or `click`) and `rich`. It is invoked from the operator's terminal, returns structured exit codes, and writes all artifacts to a deterministic per-job directory tree. Output is human-readable by default and machine-readable on demand. The tool is designed to be runnable from cron, shell scripts, or Makefiles — not just by a human at a prompt.

### Technical Architecture Considerations

- **Process model:** Single foreground process. Long-running stages (TTS, Whisper) execute in subprocesses spawned by the orchestrator so a SIGINT cleanly cancels the stage and writes a partial-progress marker.
- **State model:** All state on disk under `runs/<source-stem>-<YYYYMMDD-HHMMSS>/`. No in-memory job registry. Re-running the same command on the same input resumes the existing run if a directory exists, or creates a new one.
- **No daemon, no service:** MVP has no background daemon, no scheduled task runner, no IPC server. Each invocation is self-contained.

### Command Structure

Top-level command: `saddleback`

| Subcommand | Purpose |
|---|---|
| `saddleback dub <input.mp4> [--lang de\|es\|both] [--config PATH]` | Run full end-to-end pipeline. Default `--lang both`. |
| `saddleback regen <segment-id> [--lang de\|es] [--shorter]` | Re-run translation+TTS for one segment in current/most-recent job. Auto-rebuilds affected output. |
| `saddleback play <segment-id> [--lang de\|es]` | Play a single segment via `afplay` (macOS) for spot-checking. |
| `saddleback doctor` | Self-check: ffmpeg, LM Studio reachability, model presence, Python deps, write-perm to job dir. |
| `saddleback status [<run-id>]` | Print stage-completion status of a job (which artifacts exist, which stages remain). |
| `saddleback clean [<run-id>] [--keep-outputs]` | Remove intermediate artifacts (transcripts, TTS clips); optionally keep final MP4s. |

Global flags (apply to any subcommand):

- `--config PATH` — explicit config file
- `--quiet` / `--verbose` — log level
- `--json` — machine-parseable status events to stdout
- `--no-progress` — disable rich progress bars (for CI / piping)
- `--dry-run` — print plan, no work
- `--version`, `--help`

### Output Formats

| Output | Format | Location |
|---|---|---|
| Dubbed videos | MP4 (H.264 video copy + AAC audio re-encode) | Next to source: `<source>_de.mp4`, `<source>_es.mp4` |
| Source audio extract | WAV 24 kHz mono | `runs/<id>/audio.wav` |
| Voice reference clip | WAV 24 kHz mono | `runs/<id>/ref.wav` |
| Transcript with timestamps | JSON (segment list with `start`, `end`, `text`) | `runs/<id>/segments.json` |
| Translations | JSON (per-language map of segment-id → translated text) | `runs/<id>/translations/{de,es}.json` |
| TTS clips | WAV 24 kHz mono per segment | `runs/<id>/tts/{de,es}/seg_NNNN.wav` |
| Synced track | WAV 24 kHz mono full duration | `runs/<id>/synced/{de,es}.wav` |
| Run manifest | JSON (config snapshot, stage completion, timings, hashes) | `runs/<id>/manifest.json` |
| Quality report | JSON + rich table on console | `runs/<id>/report.json` |
| Console (default) | `rich`-styled progress bars + summary table | stdout |
| Console (`--json`) | NDJSON stream, one event per line | stdout |
| Logs | Plain text | `runs/<id>/log.txt` (and stderr at `--verbose`) |

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success — both targets produced |
| 1 | Generic failure (unspecified error in pipeline) |
| 2 | Misuse / bad CLI args |
| 3 | Preflight failed (missing ffmpeg / LM Studio / model) |
| 4 | Source unusable (corrupt MP4, no audio track, silent) |
| 5 | Stage-level failure (transcribe / translate / tts / mux) — manifest records which stage |
| 130 | SIGINT (operator cancelled) — partial progress preserved |

### Config Schema

Configuration is 100% environment-variable driven. There is no TOML or YAML config file. Local overrides live in a gitignored `.env` file at the project root; every supported variable is documented in `.env.sample` with its default value.

Precedence (lowest → highest):

1. Built-in defaults (in `src/saddleback/config.py`)
2. Variables already in `os.environ` (shell exports, CI env, etc.)
3. Variables loaded from `.env` (only applied to keys not already in the environment — shell wins over file)

Variable names follow the flattened pattern `SADDLEBACK_<SECTION>_<KEY>` — e.g. `SADDLEBACK_TRANSLATOR_ENDPOINT`, `SADDLEBACK_TTS_MODEL`, `SADDLEBACK_RUNTIME_TEST_MODE`. List-valued knobs (`SADDLEBACK_TARGETS_LANGUAGES`, `SADDLEBACK_OUTPUT_FORMATS`) accept comma-separated values.

The `--config PATH` CLI flag points at an alternate `.env`-format file when the default `./.env` is not desired.

### Scripting Support

- All long-running operations stream NDJSON status events on `--json` mode. Schema: `{"ts": "...", "stage": "transcribe", "event": "segment_done", "segment_id": 42, "elapsed_ms": 1230}`.
- Exit codes are stable and documented (see Output Formats above) for use in shell scripts.
- All file paths in output are absolute when `--json` is used (so callers do not need to track CWD).
- Designed to be safe under cron: locks job directory with `fcntl` flock so two invocations on the same source serialize cleanly.
- Honors `NO_COLOR` env var (per https://no-color.org).
- `--quiet` produces zero stdout on success, only stderr on failure.

### Implementation Considerations

- **CLI framework:** `typer` (preferred for type-hint-driven schema + auto-help) or `click`. Decision deferred to architecture step.
- **Console renderer:** `rich` for progress bars (`Progress`, `Live`), tables (summary report), and styled error messages.
- **Subprocess orchestration:** `asyncio.create_subprocess_exec` for stage spawning when concurrency is enabled (e.g., translate stage). Direct in-process call when sequential (TTS).
- **Artifact addressing:** Stage skip logic is content-hash based — each stage records input hash + output hash in `manifest.json`. Re-run with same inputs hits the cache; changed config invalidates downstream stages selectively.
- **Logging:** stdlib `logging` configured with rich handler. File handler always writes `log.txt`; stderr handler levels follow `--verbose` / `--quiet`.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** *Problem-solving MVP.* Goal is to validate that fully-local DE+ES dub of a 30-min meeting MP4 is fast enough, intelligible enough, and operationally simple enough that the operator (Giulliano) actually uses it weekly. Every MVP capability ties back to one of three things: (1) ingest a meeting, (2) produce both target dubs, (3) recover from one bad segment without a full rerun. Anything that doesn't move one of those needles is post-MVP.

**Resource Requirements:** Single developer (Giulliano), part-time. No team, no PM, no QA staff. Hardware: existing M-series Mac (16 GB RAM minimum), existing LM Studio host on local LAN, existing ffmpeg install. No new licenses, no new hardware purchases.

**Validation gate for "MVP done":**

- 5 consecutive successful end-to-end runs on real 20–30 min meeting recordings
- ≥ 1 segment regen demonstrated and produces clean output
- Audience playback feedback collected from at least 1 DE-speaking and 1 ES-speaking colleague
- Doctor subcommand catches all preflight failures simulated in test fixtures

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

- Journey 1A — Happy Path "From Drop to Dub" (end-to-end pipeline)
- Journey 1B — Bad Segment Recovery (regen subcommand)
- Journey 2 — Audience Playback (output-quality gates only; no CLI surface)
- Journey 3 — First-Run Setup (`saddleback doctor`)

**Must-Have Capabilities:**

- `saddleback dub <input.mp4>` runs full pipeline end-to-end with both DE and ES targets
- ffmpeg-based audio extract + final mux
- faster-whisper transcription (large-v3-turbo default, large-v3 selectable, segment-level timestamps)
- LM Studio translation (gemma-4-e4b @ configurable endpoint, system-prompt-anchored, JSON-validated)
- Auto voice-reference-clip extraction from longest contiguous source-speech window
- Qwen3-TTS synthesis via mlx_audio (`mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit`)
- Per-segment time-fitting via `pyrubberband` (or `ffmpeg atempo`) to source segment duration
- Synced-audio assembly with crossfade across gaps
- Resumable per-stage execution with content-hash artifact addressing
- `saddleback regen <id> [--lang] [--shorter]` with partial rebuild + partial re-mux
- `saddleback doctor` preflight check
- Auto-detect `<source>.srt` sidecar to skip Whisper
- Env-var-only configuration (no TOML/YAML), with `.env` file loader; CLI flag overrides for the most common knobs
- `rich`-styled progress UI + `--json` NDJSON event stream alternative
- Stable exit codes (0/1/2/3/4/5/130)
- Deterministic test mode (mocked LM Studio responses, cached TTS outputs)

### Post-MVP Features

**Phase 2 (Growth):**

- Selectable single target language (`--lang de` or `--lang es` only) and any single additional language Qwen3-TTS supports per spike-validated CSV (e.g., FR, IT, PT, JA)
- Glossary / protected-terms file for proper nouns and internal acronyms (per Lena/Linguist round)
- `saddleback play <segment-id>` interactive segment audition
- `saddleback status` and `saddleback clean` lifecycle commands
- `saddleback batch <input-dir>` for queueing multiple sources
- Quality dashboard: per-run report aggregator with trend tracking
- Subtitle output (`.srt`) alongside dubbed audio
- Lightweight web UI / local server for non-CLI consumers in the team

**Phase 3 (Vision / Expansion):**

- Multi-speaker diarization (`pyannote`) with per-speaker voice cloning
- Lip-sync re-render (Wav2Lip or equivalent)
- Real-time / streaming dub for live meetings
- Multi-language batch on a single run (parallel TTS workers, gated on multi-GPU/ANE budget)
- Translation memory and per-speaker glossary that learns over time
- Voice-design presets ("more energetic", "calmer") via Qwen3-TTS VoiceDesign variant
- macOS desktop wrapper (Electron or SwiftUI thin wrapper around CLI)

### Risk Mitigation Strategy

| Risk | Phase | Mitigation |
|---|---|---|
| **Technical: Qwen3-TTS multilingual quality regresses on production-length input** | MVP | Spike validated DE+ES on short clips (PASS). Add an MVP gate: a 10-min real meeting clip end-to-end test before claiming MVP done. Fallback: XTTS-v2 if Qwen3 misbehaves on long-form. |
| **Technical: Translation length explosion (DE > 1.3× EN)** | MVP | Translator system prompt instructs target-length budget. Translation length-budget validator + auto re-prompt with `--shorter`. Manual `regen --shorter` as escape valve. |
| **Technical: 7 GB peak TTS memory ceiling** | MVP | Hard policy: serialize TTS jobs (no concurrent TTS workers in MVP). Documented as `runtime.parallel_tts = false` default. Phase 2 may revisit. |
| **Technical: LM Studio host changes IP / restarts** | MVP | Configurable endpoint, preflight reachability check, actionable error message including the current configured URL. |
| **Operational: Operator returns months later, env broken** | MVP | Pinned `requirements.txt` with explicit version specifiers; pinned model revisions in `.env`; `saddleback doctor` reports exact remediation steps. |
| **Quality: Bad segment ships unnoticed** | MVP | Round-trip Whisper transcription of dubbed audio with cosine-similarity threshold; segments below threshold flagged in summary report for operator review. |
| **Market: Audience finds dub unhelpful** | MVP | Validation gate requires ≥ 1 DE and ≥ 1 ES audience checkpoint before declaring MVP done. If feedback fails, scope returns to translator/TTS quality (not new features). |
| **Resource: Developer underestimates work** | MVP | MVP is intentionally narrow (DE+ES only, single-speaker only, no diarization, no UI beyond CLI). Cut Phase-2 features without remorse if MVP slips. |
| **Resource: Mac too constrained for Phase-3 features** | Vision | Defer Wav2Lip / multi-GPU TTS until hardware case is proven. None of these block MVP. |

## Functional Requirements

> **Capability Contract.** This is the binding inventory. Capabilities not listed here will not exist in MVP unless added explicitly. Each FR specifies WHAT, not HOW.

### Source Ingest & Preflight

- **FR1:** The operator can submit a single MP4 file as the source for a dub job by passing its path as a CLI argument.
- **FR2:** The system can detect whether a `.srt` sidecar file exists alongside the source and use it as the segment source instead of running transcription.
- **FR3:** The system can verify the source MP4 has a usable audio stream and a non-zero duration before starting any pipeline work, and refuses jobs with corrupt or silent sources.
- **FR4:** The operator can run a self-check command that reports the availability of every external dependency (ffmpeg, LM Studio endpoint, Qwen3-TTS model presence, write permissions to the configured runs directory) with actionable remediation steps for each failure.
- **FR5:** The system can extract a voice reference clip (3–8 seconds of contiguous speech) from the source audio without operator input.

### Transcription

- **FR6:** The system can transcribe the source audio into a sequence of timestamped speech segments using a local speech-to-text engine.
- **FR7:** The system can produce, for each transcribed segment, the original-language text and the precise start/end times within the source audio.
- **FR8:** The system can persist the full segment list as a structured artifact that downstream stages consume without re-running transcription.
- **FR9:** The system can skip transcription entirely when an authoritative segment list (e.g., from a `.srt` sidecar) is already available.

### Translation

- **FR10:** The system can translate each source segment into German and Spanish using a configurable LM-Studio-compatible HTTP endpoint and model.
- **FR11:** The system can verify the translator endpoint is reachable before submitting any translation work, and refuses to proceed if it is not.
- **FR12:** The system can constrain its translation prompt so that the target text fits within a length budget proportional to the source segment's duration.
- **FR13:** The system can detect when a translation exceeds the per-segment length budget and mark the segment for either automatic shortening or operator review.
- **FR14:** The system can request a shorter alternative translation for a flagged segment by re-prompting the translator with a "shorter" instruction.
- **FR15:** The system can persist all translations as structured artifacts addressable by segment id and target language.
- **FR16:** The system can resume a partially completed translation pass without re-translating segments that already have a valid persisted output.

### Voice Synthesis (TTS)

- **FR17:** The system can synthesize each translated segment into spoken audio in the target language using the source-speaker's voice as a reference, via a local on-device TTS engine.
- **FR18:** The system can reuse a single voice reference clip for every segment within a job and across both target languages.
- **FR19:** The system can persist each synthesized segment as an addressable audio artifact tagged with its segment id and target language.
- **FR20:** The system can resume a partially completed synthesis pass without re-synthesizing segments that already have a valid audio artifact.
- **FR21:** The system can serialize TTS work so that no more than one synthesis call is in flight at a time, regardless of overall job concurrency.

### Audio Synchronization & Build

- **FR22:** The system can stretch or compress each synthesized segment to match the duration of its corresponding source segment.
- **FR23:** The system can flag any segment whose synthesized audio cannot be fit to source duration within an acceptable distortion threshold.
- **FR24:** The system can assemble all synthesized segments for a target language into a single continuous audio track aligned to the source timeline, with crossfades across silent gaps.
- **FR25:** The system can persist the assembled per-language audio track as an artifact for later muxing.

### Output Production (Mux)

- **FR26:** The system can produce, for each target language, a final MP4 that contains the source video stream and the synthesized audio track.
- **FR27:** The system can write each final MP4 to a deterministic location adjacent to the source file using a predictable suffix per language (e.g., `_de.mp4`, `_es.mp4`).
- **FR28:** The system can rebuild only the affected target's final MP4 when a single segment is regenerated, without re-muxing unaffected targets.

### Job Lifecycle & Recovery

- **FR29:** The system can persist all intermediate artifacts of a job under a single deterministic per-job directory.
- **FR30:** The system can resume a previously interrupted job by detecting which stages have valid artifacts and skipping those stages on the next invocation.
- **FR31:** The operator can request regeneration of a single segment by id, optionally limited to one target language.
- **FR32:** The operator can request a shortened-translation regeneration of a single segment when the original translation exceeded the length budget.
- **FR33:** The system can rebuild only the parts of the synced track and final outputs affected by a regenerated segment.
- **FR34:** The system can capture and persist a per-job manifest containing the configuration snapshot, stage timings, artifact hashes, and quality-report summary.
- **FR35:** The system can detect operator cancellation (SIGINT) and persist a partial-progress marker before exiting.

### Quality Reporting

- **FR36:** The system can produce a per-job quality report summarizing total runtime, segment count, regen warnings, and a measure of round-trip semantic similarity between the source segments and a back-transcription of the synthesized audio.
- **FR37:** The system can flag, in the quality report, any segments whose round-trip similarity falls below a configured threshold.

### CLI / Operator Interface

- **FR38:** The operator can invoke the dub pipeline via a single command and confirm or cancel the run before any work begins.
- **FR39:** The operator can choose target languages for a run via a CLI flag, with both DE and ES selected by default.
- **FR40:** The operator can request human-readable progress output (rich-styled bars and tables) by default, or machine-parseable progress events via a `--json` flag.
- **FR41:** The operator can override any configurable parameter via a layered config system (built-in defaults, user config file, project config file, environment variables, CLI flags).
- **FR42:** The system can return stable, documented exit codes that distinguish between misuse, preflight failure, source unusable, stage failure, generic failure, and operator cancellation.
- **FR43:** The system can run with deterministic test mode enabled (mocked translator responses, cached TTS outputs, locked seeds) so that test executions produce reproducible byte-identical artifacts.

## Non-Functional Requirements

> Quality attributes the system MUST meet. Each NFR is testable and measurable. Categories not relevant to a single-user, single-machine CLI tool (scalability, accessibility, multi-tenant security) are intentionally omitted.

### Performance

- **NFR-P1: End-to-end runtime.** A 30-minute single-speaker EN MP4 produces both `_de.mp4` and `_es.mp4` in ≤ 60 minutes wall-clock on a baseline M-series Mac (M1 or newer, ≥ 16 GB RAM) with the configured LM Studio host reachable on the local LAN.
- **NFR-P2: Per-segment regen.** Regenerating a single segment via `saddleback regen <id> [--lang]` completes (translation + TTS + partial rebuild + partial mux of the affected target only) in ≤ 90 seconds wall-clock.
- **NFR-P3: Preflight responsiveness.** `saddleback doctor` completes all preflight checks in ≤ 5 seconds when all dependencies are healthy.
- **NFR-P4: Translator concurrency.** The translator stage runs at a configurable parallelism (default 4 concurrent requests) without exceeding the LM Studio host's published rate limits or causing it to drop connections.
- **NFR-P5: TTS throughput.** TTS achieves a real-time factor (RTF) ≥ 1.0× on the baseline Mac (i.e., 1 minute of dubbed audio in ≤ 1 minute of wall-clock); spike measured 1.4–2.2×.

### Reliability

- **NFR-R1: End-to-end success rate.** ≥ 95% of submitted 30-minute MP4 jobs complete the full pipeline without manual intervention, measured over a rolling sample of 20 jobs.
- **NFR-R2: Resumability.** After any non-fatal interruption (SIGINT, transient LM Studio failure, OOM, machine sleep), re-running the same `dub` command on the same source resumes from the last completed stage and does not redo work whose artifacts are valid.
- **NFR-R3: Stage isolation.** A failure in any single stage produces a stage-tagged exit code and never silently masks the failure as success. The manifest records which stage failed.
- **NFR-R4: Cancellation safety.** SIGINT during any stage produces an exit within 5 seconds, persists a partial-progress marker, and leaves the job directory in a state from which the next invocation can resume.
- **NFR-R5: Quality detection.** Round-trip semantic similarity is computed and reported for ≥ 95% of synthesized segments. Segments below the configured threshold are flagged in the quality report.

### Privacy & Security

- **NFR-S1: No external egress.** No pipeline stage performs HTTP, DNS, or any other network call to a destination outside the local LAN, except (a) one-time HuggingFace model-weight downloads to the local cache and (b) calls to the operator-configured LM Studio endpoint. Outbound calls to any other host are a defect.
- **NFR-S2: No telemetry.** The tool collects no analytics, error reports, or usage metrics. No third-party analytics SDK is permitted in the dependency list.
- **NFR-S3: File-system trust boundary.** All artifacts are written under the configured `runs_dir` and the source MP4's parent directory. The tool never writes to system-wide locations or to paths outside these two roots.
- **NFR-S4: Configurable endpoint.** The LM Studio host, port, and model name are runtime-configurable. None is hard-coded in source.
- **NFR-S5: Pinned model revisions.** Qwen3-TTS and faster-whisper model revisions are pinned by HuggingFace `revision=` SHA (or equivalent) in configuration, not floated to `main`.

### Maintainability

- **NFR-M1: Version pinning.** All Python dependencies are pinned in a `requirements.txt` (or `pyproject.toml` lockfile) with explicit version specifiers (no unbounded ranges). Each MVP release tags its commit and bundles the lockfile.
- **NFR-M2: Diagnosability.** `saddleback doctor` reports actionable remediation steps for every failure it can detect (missing binary, unreachable endpoint, missing model, write-permission denial, unsupported Python version).
- **NFR-M3: Logs.** Every job writes a complete plain-text log to `runs/<id>/log.txt` capturing per-stage start/end timestamps, every CLI flag and config value resolved, and every external call's success/failure.
- **NFR-M4: Manifest integrity.** Every artifact in a job directory is referenced in the per-job manifest with its content hash. Stale or orphaned files in a run directory are detectable by comparing the directory listing against the manifest.

### Portability

- **NFR-PO1: Platform support.** The tool is supported on macOS 14.x and later running on Apple Silicon (M1, M2, M3, M4 families). Other platforms (Intel macOS, Linux, Windows) are explicitly out of MVP scope.
- **NFR-PO2: Python version.** The tool runs on Python 3.14.x. Earlier or later major versions are not guaranteed for MVP. The version requirement is enforced at startup with a clear error.
- **NFR-PO3: External-binary discovery.** ffmpeg is discovered via `PATH`. The tool does not bundle ffmpeg and does not require a specific install location, but it logs the resolved path in the manifest.

### Testability

- **NFR-T1: Deterministic test mode.** A `--test-mode` (or env var equivalent) replaces the LM Studio HTTP client with recorded responses and the TTS engine with a cached-output stub. In test mode, the same input MP4 produces byte-identical artifacts across runs (modulo timestamps in the manifest).
- **NFR-T2: No-network tests.** The default test suite runs to completion without any outbound network call. Tests asserting "no LM Studio call was made" pass when the deterministic test mode is engaged.
- **NFR-T3: Bundled fixture.** The repository ships with a tiny (≤ 30 second, ≤ 5 MB) source MP4 fixture that exercises every pipeline stage end-to-end inside CI in under 10 minutes on a CI Mac runner.
- **NFR-T4: Reproducible TTS.** Where TTS engine sampling is non-deterministic by default, sampling seeds are pinned in test mode so cached comparisons remain valid.

### Resource Constraints

- **NFR-RC1: Memory ceiling.** Peak resident set size during any pipeline stage MUST NOT exceed 8 GB. Verified on the baseline 16 GB Mac with at least one other application open (e.g., browser).
- **NFR-RC2: Disk usage.** A typical 30-minute job produces ≤ 2 GB of intermediate artifacts (audio, segments, TTS clips, synced tracks) before final mux. The `clean` subcommand can remove intermediate artifacts and retain only the final MP4 outputs.
- **NFR-RC3: TTS serialization.** TTS calls are serialized in MVP — at most one synthesis call in flight at a time — to prevent concurrent peak-memory accumulation. This is enforced at the runtime layer, not relied on as a convention.
- **NFR-RC4: No new hardware.** The tool runs on the operator's existing Mac. No GPU upgrade, no external accelerator, and no additional purchased software license is required for MVP operation.
