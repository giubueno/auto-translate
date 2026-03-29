# Video Voice Translation Pipeline

Translate the voice in a video to another language while preserving background audio, music, and the original speaker's voice characteristics.

## Prerequisites

- Python 3.11 (required by Chatterbox)
- FFmpeg (`brew install ffmpeg`)
- 8GB+ RAM (48GB recommended for large videos)
- Google Gemini API key or LM Studio running locally (for translation)

## Setup

```bash
cd /Users/giubueno/projects/saddleback/translation

# Create Python 3.11 virtual environment
~/.pyenv/versions/3.11.10/bin/python -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install git+https://github.com/openai/whisper.git
```

Set your API key in `.env`:

```
GOOGLE_GEMINI_API_KEY=your_key_here
```

Or use LM Studio locally (no API key needed, just have it running on `localhost:1234`).

## Pipeline Overview

The pipeline has 4 steps, each with its own script:

```
Input (.mp4) --> Transcribe --> Translate --> Dub --> Doublage --> Output (.mp4)
```

| Step | Script | What it does |
|------|--------|-------------|
| 1 | `transcribe.sh` | Extracts speech from video using Whisper, creates per-segment audio prompts and prosody metadata |
| 2 | `translate.sh` | Translates transcription to target language using LM Studio or Gemini |
| 3 | `dub.sh` | Generates speech in the target language using Chatterbox voice cloning with per-segment audio prompts |
| 4 | `doublage.sh` | Separates background audio using Demucs, mixes with dubbed voice, produces final video |

## Quick Start

1. Place your `.mp4` file in the `inputs/` folder.

2. Run each step in order:

```bash
# Step 1: Transcribe the video
./transcribe.sh

# Step 2: Translate to your target language (e.g. Spanish)
./translate.sh es

# Step 3: Generate dubbed audio with cloned voice
./dub.sh es

# Step 4: Create the final dubbed video
./doublage.sh es
```

3. Find your output at `outputs/es/<filename>_es.mp4`.

## Step-by-Step Details

### Step 1: Transcribe

```bash
./transcribe.sh [model]
```

- **model** (optional): Whisper model size. Options: `tiny`, `base` (default), `small`, `medium`, `large`. Larger models are more accurate but slower.
- Automatically finds the `.mp4` file in `inputs/`.
- Extracts per-segment audio clips as voice prompts (used by Chatterbox to preserve intonation).
- Computes prosody metadata (speech rate, pauses) for quality control.

**Output:**
```
outputs/
  <name>_transcription.json    # Raw Whisper output
  <name>_transcription.txt     # Human-readable with timestamps and prosody
  <name>_segments.json         # Enriched segments (used by next steps)
  prompts/                     # Per-segment audio clips
    prompt_0000_0000.wav
    prompt_0001_0023.wav
    ...
```

### Step 2: Translate

```bash
./translate.sh <target_language> [source_language] [workers]
```

- **target_language** (required): Language code (e.g. `de`, `es`, `fr`, `pt`).
- **source_language** (optional, default: `en`): Source language code.
- **workers** (optional, default: `4`): Number of parallel translation workers.
- Translates all segments in parallel for speed.
- Preserves audio prompts and prosody metadata alongside translations.

**Output:**
```
outputs/<lang>/
  <name>_segments.json         # Translated segments with all metadata
  <name>_transcription.txt     # Human-readable translated text
```

### Step 3: Dub

```bash
./dub.sh <target_language> [device]
```

- **target_language** (required): Language code matching the translate step.
- **device** (optional): `mps` (default on Apple Silicon), `cuda`, or `cpu`.
- Uses Chatterbox TTS with per-segment audio prompts to clone the original speaker's voice.
- Each segment uses its own audio clip as the voice reference, preserving the intonation and emotion of that specific moment.
- Processes segments sequentially (single GPU).

**Output:**
```
outputs/<lang>/
  0000.mp3                     # Individual segment audio files
  0123.mp3
  ...
  files.txt                    # Segment manifest
  <lang>_synced.mp3            # Final synchronized audio
```

### Step 4: Doublage

```bash
./doublage.sh <target_language> [--full]
```

- **target_language** (required): Language code matching the dub step.
- **--full** (optional): Replace the entire audio track instead of voice-only.
- By default, uses Demucs to separate the original vocals from the background (music, ambience, effects), then mixes the dubbed voice with the original background.
- Video stream is copied without re-encoding (fast, lossless).

**Output:**
```
outputs/<lang>/
  <name>_<lang>.mp4            # Final dubbed video
```

## Translating to Multiple Languages

Each step after transcribe can be run for different languages. Transcription only needs to happen once:

```bash
# Transcribe once
./transcribe.sh

# Translate to multiple languages (can run in parallel since they're CPU-bound)
./translate.sh de &
./translate.sh es &
./translate.sh fr &
wait

# Dub each language (sequential, GPU-bound)
./dub.sh de
./dub.sh es
./dub.sh fr

# Create final videos
./doublage.sh de
./doublage.sh es
./doublage.sh fr
```

## Supported Languages

Chatterbox multilingual model supports 23 languages:

| Code | Language   | Code | Language   |
|------|------------|------|------------|
| ar   | Arabic     | ms   | Malay      |
| da   | Danish     | nl   | Dutch      |
| de   | German     | no   | Norwegian  |
| el   | Greek      | pl   | Polish     |
| en   | English    | pt   | Portuguese |
| es   | Spanish    | ru   | Russian    |
| fi   | Finnish    | sv   | Swedish    |
| fr   | French     | sw   | Swahili    |
| he   | Hebrew     | tr   | Turkish    |
| hi   | Hindi      | zh   | Chinese    |
| it   | Italian    |      |            |
| ja   | Japanese   |      |            |
| ko   | Korean     |      |            |

## Troubleshooting

### Demucs is slow

Demucs vocal separation takes roughly 25% of the video duration on Apple Silicon. For a 36-minute video, expect ~10 minutes.

### Out of memory during dub

Try using CPU mode: `./dub.sh de cpu`. Slower but uses less memory.

### Translation quality is poor

- Use a larger LM Studio model for better results.
- Switch to Gemini by setting `GOOGLE_GEMINI_API_KEY` in `.env`.

### Whisper transcription misses words

Use a larger Whisper model: `./transcribe.sh medium` or `./transcribe.sh large`.

### FFmpeg not found

```bash
brew install ffmpeg
```
