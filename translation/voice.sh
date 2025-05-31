#! /bin/bash

source myenv/bin/activate

# Use export for environment variables in bash
export DATE_FILE="20250525"
export DOC_LANGUAGE=de
export SPEAKER_LANGUAGE="pt-br"

python3 tts_from_docx.py -f ./inputs/$DATE_FILE.docx -l $SPEAKER_LANGUAGE -s $DOC_LANGUAGE

# rename the file
mv ./outputs/$SPEAKER_LANGUAGE/output.mp3 ./outputs/$SPEAKER_LANGUAGE/$SPEAKER_LANGUAGE$DATE_FILE.mp3

# upload the file to my google drive
