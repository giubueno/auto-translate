# Saddleback

A multilingual audio/video translation platform that combines local transcription, flexible translation backends, and voice cloning for creating dubbed content in multiple languages.

## Features

- **Local Transcription**: Uses OpenAI's Whisper for accurate speech-to-text (configurable model sizes: tiny, base, small, medium, large)
- **Multi-Backend Translation**: Supports OpenAI GPT and Google Gemini for translation
- **Voice Cloning**: Uses Chatterbox TTS for natural, speaker-specific audio generation
- **Two Output Modes**:
  - **Time-Synchronized**: Maintains original video timing for video dubbing
  - **Sequential**: Concatenates audio with configurable gaps for podcasts/audiobooks
- **23+ Languages Supported**: ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, tr, zh
- **DOCX Processing**: Process documents with timestamps for batch translation

## Pipeline

1. Extract audio from video (using FFmpeg)
2. Transcribe audio using Whisper (locally)
3. Translate transcription using OpenAI or Google Gemini
4. Generate speech using Chatterbox TTS (voice cloning) or OpenAI TTS

## Installation

### Prerequisites

- Python 3.11+
- FFmpeg
- GPU support recommended (CUDA or Apple Silicon MPS)

### Setup

```bash
cd translation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file with your API keys:

```
OPENAI_API_KEY=your_openai_key          # For OpenAI translation and TTS
GOOGLE_GEMINI_API_KEY=your_gemini_key   # For Gemini translation (optional)
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

### Text-to-Speech

```bash
python speak.py -f text.txt -l de -v alloy
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
│   ├── translate.py              # CLI for translating audio
│   ├── speak.py                  # CLI for text-to-speech
│   └── voice_clone.sh            # Bash wrapper for voice cloning
└── README.md
```

## License

MIT License
