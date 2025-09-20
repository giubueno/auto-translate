#! /bin/bash
#
# Voice Translation Script
# 
# This script automatically detects .docx files in the inputs folder and processes them
# for text-to-speech translation into multiple languages.
#
# Usage: ./voice.sh [doc_language]
#   doc_language: Optional language of the source document (defaults to "de")
#
# The script will:
# 1. Automatically find the .docx file in the inputs folder
# 2. Process it for languages: pt-br, de, es
# 3. Generate audio files in the outputs folder
#

source venv/bin/activate > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate the virtual environment"
    exit 1
fi

pip install -r requirements.txt > /dev/null 2>&1
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

LANGUAGES=("pt-br" "de" "es")

for language in "${LANGUAGES[@]}"; do
    # create a folder for the date
    mkdir -p ./outputs/${language}
done


# Input file already verified to exist above

# for each language in LANGUAGES, run the script
for language in "${LANGUAGES[@]}"; do
    echo "Running for $language"

    python3 tts_from_docx.py -f "$DOCX_FILE" -l $language -s $DOC_LANGUAGE
    if [ $? -ne 0 ]; then
        echo "Error: Failed to run the script"
        exit 1
    fi

    # rename the file
    mv ./outputs/${language}/${language}_synced.mp3 ./outputs/${language}/${language}_${DATE_FILE}.mp3
done
