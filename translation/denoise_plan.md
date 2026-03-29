# Denoise Feature Plan

## Overview

Add audio post-processing to clean the "tail noise" artifact (low-level hiss/breathing) that Chatterbox TTS appends to every generated WAV clip.

## Pipeline

Three-stage ffmpeg audio filter chain applied to each generated WAV:

1. **RNNoise denoising:** `arnndn=m={model_path}=0.8`
2. **Conservative silence trim:** `silenceremove=start_periods=0:stop_periods=-1:stop_duration=0.2:stop_threshold=-35dB`
3. **Smooth fade-out:** `afade=t=out:st={calculated}:d=0.03` (dynamic start time based on trimmed duration)

## Scope

### Build

- `utils/denoise.py` — single function `clean_audio(input_path: str, output_path: str) -> bool`
  - Runs ffmpeg subprocess with the three-filter chain
  - Validates input file exists, output succeeds
  - Logs duration savings (input vs output length)
  - Handles missing ffmpeg or missing `arnndn` filter gracefully (skip denoise, fall back to silence-trim + fade only)
  - Checks RNNoise model availability before attempting denoise
- Modify `utils/chatterbox_tts.py` — `ChatterboxVoiceCloner.generate_speech()`
  - Call `clean_audio()` on WAV **before** the existing MP3 conversion step (line ~148)
  - Merge into the existing post-processing flow, not a separate pass

### Skip (from original prompt)

- Pydantic models for paths — overkill for internal utility
- Class wrapper with batch processing — YAGNI, `generate_speech` handles one file at a time
- FastAPI endpoint — not in this project's scope
- Node.js subprocess wrapper — irrelevant to this codebase

## Key Design Decisions

### Fade-out timing

The original prompt hardcodes `st=0.08` for fade-out start. This only works for very short clips. Instead, probe trimmed duration with `ffprobe` and calculate fade-out start as `duration - 0.03s` so the fade applies to the actual end of the clip regardless of length.

### RNNoise model provisioning

The `arnndn` filter requires a RNNoise model file at runtime. The function must:

1. Accept a configurable model path (env var or parameter)
2. Check the model file exists before constructing the ffmpeg command
3. If missing, log a warning and run only silence-trim + fade (graceful degradation)

### ffmpeg compatibility

Not all ffmpeg builds include the `arnndn` filter. The function should detect this (e.g., catch subprocess error) and fall back to the two remaining filters.

## Integration Point

```
generate_speech()
  ├── Model inference → WAV saved
  ├── clean_audio(wav_path, wav_path)    ← NEW
  └── ffmpeg WAV → MP3 conversion        ← EXISTING
```

## Tests

| Test | Type | What it verifies |
|------|------|-----------------|
| `test_clean_audio_command` | Unit (mocked subprocess) | Correct ffmpeg command construction |
| `test_clean_audio_missing_ffmpeg` | Unit (mocked subprocess) | Graceful failure when ffmpeg not found |
| `test_clean_audio_missing_model` | Unit | Falls back to silence-trim + fade when RNNoise model missing |
| `test_clean_audio_integration` | Integration (real ffmpeg) | Runs on a small WAV fixture; output exists, is shorter or equal, is valid audio |
| `test_clean_audio_short_clip` | Edge case | Clips < 500ms handled without error |
| `test_clean_audio_already_clean` | Edge case | Already-clean files pass through without corruption |
| `test_generate_speech_calls_denoise` | Integration | `generate_speech()` calls `clean_audio()` before MP3 conversion |

## Dependencies

- `ffmpeg` with `arnndn` filter support (optional — degrades gracefully)
- RNNoise model file (path configurable via `RNNOISE_MODEL_PATH` env var)
- No new Python packages required (uses `subprocess`)
