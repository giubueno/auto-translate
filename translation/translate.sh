#!/bin/bash
#
# Translation Script
#
# Translates enriched transcription segments into a target language using
# LM Studio (local) or Gemini API.
#
# Usage: ./translate.sh <target_language> [source_language] [workers]
#   target_language: Required. Language code (e.g. de, es, fr)
#   source_language: Optional. Source language code (default: en)
#   workers:         Optional. Number of parallel workers (default: 4)
#
# Expects transcribe.sh to have been run first, producing outputs/*_segments.json
#

source venv_voice/bin/activate > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate the virtual environment. Run transcribe.sh first."
    exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: ./translate.sh <target_language> [source_language] [workers]"
    echo "  Example: ./translate.sh de en 4"
    exit 1
fi

TARGET_LANGUAGE=$1
SOURCE_LANGUAGE=${2:-en}
WORKERS=${3:-4}

# Find the segments JSON from transcribe.sh output
SEGMENTS_FILE=$(find ./outputs -maxdepth 1 -name "*_segments.json" -type f | head -n 1)

if [ -z "$SEGMENTS_FILE" ]; then
    echo "Error: No *_segments.json file found in outputs/"
    echo "Run ./transcribe.sh first to generate the transcription."
    exit 1
fi

echo "Found segments file: $SEGMENTS_FILE"
echo "Translating: $SOURCE_LANGUAGE -> $TARGET_LANGUAGE"

python3 translate.py -f "$SEGMENTS_FILE" -l "$TARGET_LANGUAGE" -s "$SOURCE_LANGUAGE" -w "$WORKERS"
if [ $? -ne 0 ]; then
    echo "Error: Translation failed"
    exit 1
fi

echo "=== Translation complete ==="
