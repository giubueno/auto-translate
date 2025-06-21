#! /bin/bash

source venv/bin/activate

pip install -r requirements.txt

# Use export for environment variables in bash
export DATE_FILE="20250622-1"
export DOC_LANGUAGE=de

LANGUAGES=("pt-br" "de" "es")

# for each language in LANGUAGES, run the script
for language in "${LANGUAGES[@]}"; do
    echo "Running for $language"

    python3 tts_from_docx.py -f ./inputs/$DATE_FILE.docx -l $language -s $DOC_LANGUAGE

    # rename the file
    mv ./outputs/$language/$language_synced.mp3 ./outputs/$language/$language$DATE_FILE.mp3
done

# upload the file to my google drive
