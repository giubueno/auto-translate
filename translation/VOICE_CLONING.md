# Voice Cloning Translation Pipeline

Clone a voice from a video and generate translated speech using Chatterbox (local, open-source TTS).

## Prerequisites

- Python 3.11 (required by Chatterbox)
- FFmpeg installed (`brew install ffmpeg` on macOS)
- Sufficient RAM (8GB+ recommended)
- OpenAI API key (for translation)

## Setup

1. Create a Python 3.11 virtual environment:

```bash
cd /Users/giubueno/projects/saddleback/translation
~/.pyenv/versions/3.11.10/bin/python -m venv venv
```

2. Activate the virtual environment and install dependencies:

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install openai git+https://github.com/openai/whisper.git
```

3. Set your OpenAI API key in `.env`:

```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Using the Shell Script

```bash
./voice_clone.sh <video_path> [target_language] [source_language] [device]
```

**Arguments:**
- `video_path` - Path to the source video file (required)
- `target_language` - Target language code (default: `de` for German)
- `source_language` - Source language code (default: `en` for English)
- `device` - Device for Chatterbox: `cuda`, `mps`, `cpu` (default: auto-detect)

**Examples:**

```bash
# Translate English video to German
./voice_clone.sh /path/to/video.mp4

# Translate to French
./voice_clone.sh /path/to/video.mp4 fr en

# Force CPU processing
./voice_clone.sh /path/to/video.mp4 de en cpu
```

### Using Python Directly

```bash
source venv/bin/activate
python3 voice_clone_pipeline.py -v <video_path> -l <target_lang> -s <source_lang> -o outputs
```

**Options:**
- `-v, --video` - Path to the source video file (required)
- `-l, --language` - Target language code (default: `de`)
- `-s, --source` - Source language code (default: `en`)
- `-o, --output` - Output directory (default: `outputs`)
- `-m, --model` - Whisper model size: `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
- `-d, --device` - Device for Chatterbox: `cuda`, `mps`, `cpu` (default: auto-detect)

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

## Output Structure

```
outputs/<language>/
├── 0000.mp3          # Segment at 00:00
├── 0015.mp3          # Segment at 00:15
├── 0123.mp3          # Segment at 01:23
├── ...               # More segments
├── files.txt         # Manifest of all segments
└── <lang>_synced.mp3 # Final synchronized audio
```

## Pipeline Steps

1. **Extract Audio** - Extracts audio from video using FFmpeg
2. **Initialize Chatterbox** - Loads the multilingual TTS model
3. **Transcribe** - Uses Whisper to transcribe audio with timestamps
4. **Translate & Generate** - For each segment:
   - Translates text using OpenAI GPT-3.5
   - Generates speech with cloned voice using Chatterbox
5. **Build Audio** - Synchronizes all segments into final output

## Performance Notes

- **CPU processing is slow**: Each segment takes ~15-30 seconds on CPU
- **Long videos take hours**: A 30-minute video with 900 segments can take 4-7 hours on CPU
- **GPU recommended**: Use CUDA if available for faster processing
- **Memory usage**: Chatterbox models require significant RAM (8GB+)

## Troubleshooting

### Model loading fails on non-CUDA device

The pipeline includes a patch for loading Chatterbox models on CPU/MPS. If you encounter issues, ensure you're using the latest `utils/chatterbox_tts.py`.

### Out of memory

Try using a smaller Whisper model (`-m tiny`) or processing shorter videos.

### FFmpeg not found

Install FFmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## Files

| File | Description |
|------|-------------|
| `voice_clone_pipeline.py` | Main orchestration script |
| `voice_clone.sh` | Shell wrapper for easy execution |
| `utils/chatterbox_tts.py` | Chatterbox voice cloning utility |
| `utils/translation.py` | OpenAI translation utility |
| `transcribe.py` | Whisper transcription utility |
| `audio_builder.py` | Audio synchronization utility |
