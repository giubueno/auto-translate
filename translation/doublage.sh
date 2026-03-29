#!/bin/bash
#
# Doublage Script
#
# Replaces only the voice in an .mp4 video with dubbed audio, preserving
# background sounds (music, ambience, effects) using Demucs vocal separation.
#
# Usage: ./doublage.sh <target_language> [--full]
#   target_language: Required. Language code (e.g. de, es, fr)
#   --full:          Optional. Replace entire audio instead of voice-only
#
# Expects:
#   - An .mp4 file in the inputs/ folder
#   - Dubbed audio at outputs/{lang}/{lang}_synced.mp3 (from dub.sh)
#

source venv/bin/activate > /dev/null 2>&1
if [ $? -ne 0 ]; then
    source venv_voice/bin/activate > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Error: Failed to activate the virtual environment."
        exit 1
    fi
fi

if [ -z "$1" ]; then
    echo "Usage: ./doublage.sh <target_language> [--full]"
    echo "  Example: ./doublage.sh de            # voice-only replacement (preserves background)"
    echo "  Example: ./doublage.sh de --full      # replace entire audio track"
    exit 1
fi

TARGET_LANGUAGE=$1
FULL_FLAG=""
if [ "$2" == "--full" ]; then
    FULL_FLAG="--full"
fi

# Find the .mp4 file in inputs
MP4_FILE=$(find ./inputs -name "*.mp4" -type f | head -n 1)

if [ -z "$MP4_FILE" ]; then
    echo "Error: No .mp4 file found in the inputs folder"
    exit 1
fi

# Check dubbed audio exists
DUBBED_AUDIO="./outputs/${TARGET_LANGUAGE}/${TARGET_LANGUAGE}_synced.mp3"
if [ ! -f "$DUBBED_AUDIO" ]; then
    echo "Error: Dubbed audio not found at $DUBBED_AUDIO"
    echo "Run ./dub.sh ${TARGET_LANGUAGE} first."
    exit 1
fi

echo "Found video: $MP4_FILE"
echo "Found dubbed audio: $DUBBED_AUDIO"
if [ -n "$FULL_FLAG" ]; then
    echo "Mode: Full audio replacement"
else
    echo "Mode: Voice-only replacement (Demucs)"
fi

python3 doublage.py -v "$MP4_FILE" -l "$TARGET_LANGUAGE" $FULL_FLAG
if [ $? -ne 0 ]; then
    echo "Error: Doublage failed"
    exit 1
fi

echo "=== Doublage complete ==="
