#! /bin/bash

# activate the virtual environment
source venv/bin/activate > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate the virtual environment"
    exit 1
fi

# install the requirements
pip install -r requirements.txt > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Failed to install the requirements"
    exit 1
fi

LANGUAGES=(
    "de"
    "es"
    "pt-br"
)

# receive the time to crop as an argument
DATE_FILE=$1
TIME_TO_CROP=$2

if [ -z "$DATE_FILE" ] || [ -z "$TIME_TO_CROP" ]; then
    echo "Usage: $0 <date_file> <time_to_crop>"
    echo "Example: $0 20250803 00:01:24"
    echo "The time to crop is the time to start the crop in the format HH:MM:SS"
    echo "The date file is the date of the file to crop in the format YYYYMMDD"
    exit 1
fi

for language in "${LANGUAGES[@]}"; do
    # remove the cropped file if it exists
    rm outputs/${language}/${language}_${DATE_FILE}_cropped.mp3
    # crop the first 27:24 of the file and save it as outputs/${language}/${language}_${DATE_FILE}_cropped.mp3
    ffmpeg -i outputs/${language}/${language}_${DATE_FILE}.mp3 -ss ${TIME_TO_CROP} -c copy outputs/${language}/${language}_${DATE_FILE}_cropped.mp3
done

