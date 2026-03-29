# Saddleback

A multilingual audio/video translation platform that combines local transcription, flexible translation backends, and voice cloning for creating dubbed content in multiple languages.

## Features

- **Local Transcription**: Uses Whisper for accurate speech-to-text (configurable model sizes: tiny, base, small, medium, large)
- **Multi-Backend Translation**: Supports Google Gemini and LM Studio (local) for translation
- **Voice Cloning**: Uses Chatterbox TTS for natural, speaker-specific audio generation
- **Two Output Modes**:
  - **Time-Synchronized**: Maintains original video timing for video dubbing
  - **Sequential**: Concatenates audio with configurable gaps for podcasts/audiobooks
- **23+ Languages Supported**: ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, tr, zh
- **DOCX Processing**: Process documents with timestamps for batch translation

## Pipeline

1. Extract audio from video (using FFmpeg)
2. Transcribe audio using Whisper (locally)
3. Translate transcription using Google Gemini or LM Studio (local)
4. Generate speech using Chatterbox TTS (voice cloning)

## Installation

### Prerequisites

- Python 3.11+
- FFmpeg
- GPU support recommended (CUDA or Apple Silicon MPS)

### Setup

```bash
cd translation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file with your API keys:

```
GOOGLE_GEMINI_API_KEY=your_gemini_key   # For Gemini translation
# Or use LM Studio locally (no API key required)
LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

## Usage

### Voice Cloning (Simple)

```bash
cd translation
./voice_clone.sh /path/to/video.mp4 -l de -s en
```

### Voice Cloning (Advanced)

```bash
./voice_clone.sh video.mp4 -l fr --sequential -g 1000 -w 8 -d cuda

./voice_clone.sh video.mp4 -l fr --sequential -g 1000 -w 8 -d mps
```

Options:
- `-l, --language`: Target language (default: de)
- `-s, --source-language`: Source language (default: en)
- `--sequential`: Use sequential mode instead of time-synchronized
- `-g, --gap`: Gap between segments in ms for sequential mode (default: 500)
- `-w, --workers`: Number of parallel translation workers (default: 4)
- `-d, --device`: Device for processing (cuda, mps, cpu)

### Command-Line Translation

```bash
python translate.py -l de -f audio.mp3
```

### DOCX Processing

Process DOCX files with timestamp format `(MM:SS): text`:

```bash
./voice.sh [doc_language]
```

## Project Structure

```
saddleback/
├── translation/
│   ├── voice_clone_pipeline.py   # Main orchestration pipeline
│   ├── transcribe.py             # Audio extraction & transcription
│   ├── audio_builder.py          # Audio output building
│   ├── utils/
│   │   ├── translation.py        # Multi-backend translation
│   │   └── chatterbox_tts.py     # Voice cloning engine
│   ├── translator.py             # CLI for translation with Chatterbox TTS
│   └── voice_clone.sh            # Bash wrapper for voice cloning
└── README.md
```

## License

MIT License
