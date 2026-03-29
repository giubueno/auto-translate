#! /bin/bash
#
# Voice Translation Script
# 
# This script automatically detects .docx files in the inputs folder and processes them
# for text-to-speech translation into multiple languages.
#
# Usage: ./voice.sh [doc_language] [target_language ...]
#   doc_language: Optional language of the source document (defaults to "de")
#   target_language: Optional. If given, only these target languages (e.g. "de" or "en" "de")
#
# The script will:
# 1. Automatically find the .docx file in the inputs folder
# 2. Process it for the target language(s) (default: de, es)
# 3. Generate audio files in the outputs folder
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

# Automatically detect the .docx file in the inputs folder
DOCX_FILE=$(find ./inputs -name "*.docx" -type f | head -n 1)

if [ -z "$DOCX_FILE" ]; then
    echo "Error: No .docx file found in the inputs folder"
    echo "Please place a .docx file in the inputs folder"
    exit 1
fi

# Extract the filename without path and extension
DATE_FILE=$(basename "$DOCX_FILE" .docx)
echo "Found input file: $DOCX_FILE"
echo "Using date file: $DATE_FILE"

DOC_LANGUAGE=$1
if [ -z "$DOC_LANGUAGE" ]; then
    DOC_LANGUAGE="de"
fi

if [ -n "$2" ]; then
    shift
    LANGUAGES=("$@")
else
    LANGUAGES=("de" "es")
fi

for language in "${LANGUAGES[@]}"; do
    # create a folder for the date
    mkdir -p ./outputs/${language}
done


# Input file already verified to exist above

# Step 1: Translate all languages in parallel (CPU/API-bound)
echo "=== Step 1: Translating all languages in parallel ==="
PIDS=()
for language in "${LANGUAGES[@]}"; do
    echo "Starting translation for $language"
    python3 tts_from_docx.py -f "$DOCX_FILE" -l "$language" -s "$DOC_LANGUAGE" --step translate &
    PIDS+=($!)
done

FAILED=0
for pid in "${PIDS[@]}"; do
    wait "$pid" || FAILED=1
done

if [ $FAILED -ne 0 ]; then
    echo "Error: One or more translations failed"
    exit 1
fi
echo "=== All translations complete ==="

# Step 2: Synthesize sequentially (GPU-bound, one at a time)
echo "=== Step 2: Synthesizing audio sequentially ==="
for language in "${LANGUAGES[@]}"; do
    echo "Synthesizing audio for $language"
    python3 tts_from_docx.py -f "$DOCX_FILE" -l "$language" -s "$DOC_LANGUAGE" --step synthesize
    if [ $? -ne 0 ]; then
        echo "Error: Synthesis failed for $language"
        exit 1
    fi

    mv "./outputs/${language}/${language}_synced.mp3" "./outputs/${language}/${language}_${DATE_FILE}.mp3"
done
echo "=== All synthesis complete ==="
