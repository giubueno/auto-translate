# Translation

Code used to translate audios using Whisper to transcribe text, LM Studio or Gemini to translate the text, and Chatterbox for text-to-speech with voice cloning.

## Running

You can run this code using Python 3.

### Dependencies

If you don't have one already, create a virtual environment using:

```sh
python3 -m venv venv
```

Activate the Virtual Environment: Before installing dependencies, activate the virtual environment. On macOS and Linux, run:

```sh
python3 -m venv venv
source venv/bin/activate
```

On Windows, run:

```sh
.\venv\Scripts\activate
```

To install all dependencies listed in requirements.txt, use the following command:

```sh
pip install -r requirements.txt
```

***Attention***
We are using Open Whisper (Open source), which depends on NumPy < 2.x. You need to make sure that you have a 1.x version.

For example:

```sh
pip install numpy==1.26.4
```

### Required Credentials and Environment Variables

This project uses several external services that require API keys and credentials. Create a `.env` file in the root directory with the following variables:

```sh
# LM Studio Configuration (for local translation)
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen/qwen3-vl-8b:2

# Google Gemini API Key (for translation)
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here

# Google Cloud Credentials (optional, for Google Cloud services)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
```

#### How to obtain credentials:

1. **LM Studio (for local translation):**
   - Download and install [LM Studio](https://lmstudio.ai/)
   - Download a model (default: `qwen/qwen3-vl-8b:2`)
   - Start the local server (default port: 1234)
   - The API is OpenAI-compatible and runs at `http://localhost:1234/v1`
   - No API key required for local usage

2. **Google Gemini API Key (for translation):**
   - Sign up at [Google AI Studio](https://aistudio.google.com/)
   - Navigate to API Keys section
   - Create a new API key

3. **Google Cloud Credentials (optional):**
   - Set up a Google Cloud project
   - Enable the required APIs (Text-to-Speech, Translate)
   - Create a service account and download the JSON credentials file

### Testing

You can run the test by executing:

```sh
python -m unittest discover -s tests
```

## Audio translation

### Building an MP3 file

0125 = 85000

```sh
python build.py -f outputs/de/german.mp3 -i outputs/de/0125.mp3 -o outputs/de/german.mp3 -t 85000
```

### Translate

```sh
python translate.py -l de -f inputs/texts/en/0125.txt
```

## Pipelines Comparison

This project offers two distinct audio translation pipelines:

| | `voice.sh` | `voice_clone.sh` |
|---|---|---|
| **Input** | `.docx` document | Video file (`.mp4`) |
| **TTS Engine** | Cloud API (OpenAI) | Local model (Chatterbox) |
| **Voice Output** | Standard/generic voice | Cloned from original speaker |
| **Python Entry** | `tts_from_docx.py` | `voice_clone_pipeline.py` |
| **Default Languages** | `de`, `es` | 23+ supported |
| **Parallelism** | Sequential per language | Configurable workers (`-w`) |
| **Audio Modes** | Time-synced | Time-synced or sequential |
| **Device Support** | N/A (cloud) | `cuda`, `mps`, `cpu` |

**When to use `voice.sh`:** You have a written document (`.docx`) and need it translated and spoken in a standard voice. Best for quick document-to-speech conversion.

**When to use `voice_clone.sh`:** You have a video of someone speaking and want the translation to sound like the original speaker. Best for dubbing, podcasts, or preserving speaker authenticity.

## Running voice.sh

The `voice.sh` script automatically detects a `.docx` file in the `inputs/` folder and generates translated audio files for one or more target languages.

### Prerequisites

Before running `voice.sh`, ensure you have:

1. **All required credentials** (see section above)
2. **A `.docx` file** placed in the `inputs/` directory
3. **A Python virtual environment** at `venv/` (the script activates it automatically)

### Usage

```sh
# Make the script executable (first time only)
chmod +x voice.sh

./voice.sh [doc_language] [target_language ...]
```

| Argument | Description | Default |
|---|---|---|
| `doc_language` | Language of the source document | `de` |
| `target_language` | One or more target languages to generate | `de es` |

### Examples

```sh
# Default: source is German, generates German and Spanish audio
./voice.sh

# Source is English, generate German and Spanish
./voice.sh en de es

# Source is English, generate only French
./voice.sh en fr

# Source is German, generate Portuguese, Spanish, and Italian
./voice.sh de pt-br es it
```

### What voice.sh does

1. **Activates** the virtual environment and installs dependencies
2. **Auto-detects** the first `.docx` file in `inputs/`
3. **For each target language:**
   - Runs `tts_from_docx.py` to translate and convert text to speech
   - Saves the output as `outputs/{lang}/{lang}_{filename}.mp3`

### Input file format

The DOCX file should contain:
- **Timestamps** in format `(MM:SS):` at the beginning of paragraphs
- **Text content** to be translated and converted to speech
- **Proper paragraph structure** for processing

Example:
```
(00:01): Welcome to our presentation.
(00:05): Today we will discuss important topics.
```

### Output structure

The script generates:
```
outputs/
├── pt-br/
│   ├── pt-br_20250727.mp3
│   └── files.txt
├── de/
│   ├── de_20250727.mp3
│   └── files.txt
└── es/
    ├── es_20250727.mp3
    └── files.txt
```

### Troubleshooting

1. **Permission denied:** Run `chmod +x voice.sh`
2. **Missing credentials:** Ensure all environment variables are set
3. **File not found:** Check that the DOCX file exists in `inputs/` directory
4. **API rate limits:** The script includes delays to avoid rate limiting
5. **Virtual environment issues:** Ensure `venv/bin/activate` exists and is accessible

## Voice Cloning Pipeline

The voice cloning pipeline uses **Chatterbox TTS** to clone a speaker's voice from a video and generate translated speech in multiple languages.

### Features

- **Voice Cloning:** Extracts and clones the speaker's voice from source video
- **Local Processing:** Uses Whisper for transcription (no cloud API needed)
- **Multi-language Support:** Supports 23+ languages including ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, tr, zh
- **Parallel Translation:** Speeds up processing with concurrent translation workers
- **Two Output Modes:**
  - **Time-synchronized:** Preserves original video timing (for dubbing)
  - **Sequential:** Concatenates audio with configurable gaps (for podcasts/audiobooks)

### Prerequisites

Install Chatterbox TTS and its dependencies:

```sh
pip install chatterbox-tts
```

Ensure FFmpeg is installed for audio processing:

```sh
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### Usage

#### Shell Script

```sh
# Make executable (first time only)
chmod +x voice_clone.sh

# Basic usage - time-synchronized output (for video dubbing)
./voice_clone.sh /path/to/video.mp4 -l de -s en

# Sequential mode with 1-second gaps (for podcasts/audiobooks)
./voice_clone.sh /path/to/video.mp4 -l de --sequential -g 1000

# Maximum speed with 8 parallel translation workers
./voice_clone.sh /path/to/video.mp4 -l fr --sequential -w 8

# Specify device (cuda, mps, or cpu)
./voice_clone.sh /path/to/video.mp4 -l es -d cuda
```

#### Python Script

```sh
# Time-synchronized (default)
python3 voice_clone_pipeline.py -v video.mp4 -l de -s en

# Sequential with 1-second gaps
python3 voice_clone_pipeline.py -v video.mp4 -l de --sequential -g 1000

# Full options
python3 voice_clone_pipeline.py -v video.mp4 -l de -s en --sequential -g 1000 -w 4 -d cuda
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-v, --video` | Path to source video file (required) | - |
| `-l, --language` | Target language code | `de` |
| `-s, --source` | Source language code | `en` |
| `-o, --output` | Output directory | `outputs` |
| `-m, --model` | Whisper model size (tiny, base, small, medium, large) | `base` |
| `-d, --device` | Device for Chatterbox (cuda, mps, cpu) | auto-detect |
| `--sequential` | Concatenate audio with gaps instead of time-synced overlay | disabled |
| `-g, --gap` | Gap in milliseconds between chunks in sequential mode | `1000` |
| `-w, --workers` | Number of parallel workers for translation | `4` |

### Output Modes

#### Time-Synchronized Mode (Default)

Best for **video dubbing**. Audio segments are placed at their original timestamps, maintaining sync with the source video.

```
outputs/{lang}/{lang}_synced.mp3
```

#### Sequential Mode

Best for **podcasts, audiobooks, or standalone audio**. Audio segments are concatenated with configurable silence gaps between them.

```
outputs/{lang}/{lang}_sequential.mp3
```

### Output Structure

```
outputs/
└── de/
    ├── 0000.mp3          # Individual segment at 00:00
    ├── 0015.mp3          # Individual segment at 00:15
    ├── 0032.mp3          # Individual segment at 00:32
    ├── files.txt         # Manifest of generated files
    ├── de_synced.mp3     # Time-synchronized output
    └── de_sequential.mp3 # Sequential output (if --sequential used)
```

### Pipeline Steps

1. **Extract Audio:** Extracts audio track from source video
2. **Initialize Voice Cloner:** Loads Chatterbox TTS model
3. **Transcribe:** Uses Whisper to transcribe audio into segments
4. **Translate (Parallel):** Translates all segments concurrently for speed
5. **Generate Speech:** Creates voice-cloned speech for each segment
6. **Build Output:** Merges segments into final audio file

### Performance Tips

- **GPU Acceleration:** Use `-d cuda` on NVIDIA GPUs for faster TTS generation
- **Parallel Workers:** Increase `-w` value on multi-core systems (default: 4)
- **Whisper Model:** Use `tiny` or `base` for faster transcription, `large` for accuracy
- **Skip Regeneration:** Existing segment files are skipped automatically

### Troubleshooting

1. **CUDA out of memory:** Use `-d cpu` or a smaller Whisper model
2. **MPS issues on Mac:** The pipeline defaults to CPU for MPS compatibility
3. **Slow processing:** Increase parallel workers with `-w 8` or higher
4. **Missing audio:** Ensure FFmpeg is installed and in PATH