#! /bin/bash

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

DATE_FILE=$1

if [ -z "$DATE_FILE" ]; then
    echo "Usage: $0 <date_file>"
    echo "Example: $0 20250803"
    echo "The date file is the date of the file to process in the format YYYYMMDD"
    exit 1
fi

DOC_LANGUAGE=$2
if [ -z "$DOC_LANGUAGE" ]; then
    DOC_LANGUAGE="de"
fi

LANGUAGES=("pt-br" "de" "es")

for language in "${LANGUAGES[@]}"; do
    # create a folder for the date
    mkdir -p ./outputs/${language}
done

if [ -z "$DATE_FILE" ]; then
    echo "Usage: $0 <date_file>"
    echo "Example: $0 20250803"
    echo "The date file is the date of the file to process in the format YYYYMMDD"
    echo "The doc language is the language of the document to process"
    echo "The doc language is optional and defaults to de"
    echo "the input file should be ./inputs/<DATE_FILE>.docx"
    exit 1
fi

# for each language in LANGUAGES, run the script
for language in "${LANGUAGES[@]}"; do
    echo "Running for $language"

    python3 tts_from_docx.py -f ./inputs/$DATE_FILE.docx -l $language -s $DOC_LANGUAGE
    if [ $? -ne 0 ]; then
        echo "Error: Failed to run the script"
        exit 1
    fi

    # rename the file
    mv ./outputs/${language}/${language}_synced.mp3 ./outputs/${language}/${language}_${DATE_FILE}.mp3
done
