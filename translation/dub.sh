#!/bin/bash
#
# Dubbing Script
#
# Generates cloned-voice audio from translated transcription segments using
# Chatterbox TTS. Uses per-segment audio prompts to preserve original intonation.
#
# Usage: ./dub.sh <target_language> [device]
#   target_language: Required. Language code (e.g. de, es, fr)
#   device:          Optional. Chatterbox device: cuda, mps, cpu (default: auto)
#
# Expects translate.sh to have been run first, producing outputs/{lang}/*_segments.json
#

source venv/bin/activate > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate the virtual environment."
    echo "Set up the venv per VOICE_CLONING.md instructions."
    exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: ./dub.sh <target_language> [device]"
    echo "  Example: ./dub.sh de"
    echo "  Example: ./dub.sh es cpu"
    exit 1
fi

TARGET_LANGUAGE=$1
DEVICE=${2:-}

# Find the translated segments JSON
SEGMENTS_FILE=$(find "./outputs/${TARGET_LANGUAGE}" -maxdepth 1 -name "*_segments.json" -type f | head -n 1)

if [ -z "$SEGMENTS_FILE" ]; then
    echo "Error: No *_segments.json found in outputs/${TARGET_LANGUAGE}/"
    echo "Run ./translate.sh ${TARGET_LANGUAGE} first to generate translations."
    exit 1
fi

echo "Found translated segments: $SEGMENTS_FILE"
echo "Target language: $TARGET_LANGUAGE"

DEVICE_FLAG=""
if [ -n "$DEVICE" ]; then
    DEVICE_FLAG="-d $DEVICE"
fi

python3 dub.py -f "$SEGMENTS_FILE" -l "$TARGET_LANGUAGE" $DEVICE_FLAG
if [ $? -ne 0 ]; then
    echo "Error: Dubbing failed"
    exit 1
fi

echo "=== Dubbing complete ==="
