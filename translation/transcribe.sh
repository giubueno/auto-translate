#!/bin/bash
#
# Transcription Script
#
# This script automatically detects .mp4 files in the inputs folder and generates
# a transcription.txt in the outputs folder using local Whisper.
#
# Usage: ./transcribe.sh [model]
#   model: Optional Whisper model size (tiny, base, small, medium, large). Defaults to "base".
#

python3 -m venv venv_voice

source venv_voice/bin/activate > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate the virtual environment"
    exit 1
fi

pip install -r requirements_voice.txt > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Failed to install the requirements"
    exit 1
fi

# Automatically detect the .mp4 file in the inputs folder
MP4_FILE=$(find ./inputs -name "*.mp4" -type f | head -n 1)

if [ -z "$MP4_FILE" ]; then
    echo "Error: No .mp4 file found in the inputs folder"
    echo "Please place a .mp4 file in the inputs folder"
    exit 1
fi

echo "Found input file: $MP4_FILE"

MODEL=${1:-base}
echo "Using Whisper model: $MODEL"

python3 transcribe.py -f "$MP4_FILE" -m "$MODEL" -o ./outputs
if [ $? -ne 0 ]; then
    echo "Error: Transcription failed"
    exit 1
fi

echo "=== Transcription complete ==="
