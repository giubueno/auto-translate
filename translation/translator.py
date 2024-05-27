import argparse
import re
import time
from pathlib import Path
import boto3
from openai import OpenAI
import os

def speak(minutes, seconds, text, language="es", voice="echo", files_path="outputs/es/output.mp3"):
    client = OpenAI()

    output_path = Path(f"outputs/{language}")
    # Create the output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Text to be converted to speech
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice=voice,
        input=text
    ) as response:
        # Format minutes and seconds as two-digit numbers
        minutes_str = str(minutes).zfill(2)
        seconds_str = str(seconds).zfill(2)
        speech_file_path = Path(__file__).parent / f"{output_path}/{minutes_str}{seconds_str}.mp3"
        response.stream_to_file(speech_file_path)

    # Append the file path to the files.txt
    with open(files_path, 'a') as file:
        file.write(f"file '{speech_file_path}'\n")

def translate_text(text, source_language='en', target_language='es'):
    translate = boto3.client(service_name='translate', region_name='us-east-1', use_ssl=True)
    result = translate.translate_text(Text=text, SourceLanguageCode=source_language, TargetLanguageCode=target_language)
    return result.get('TranslatedText')

def execute(language, original_file_path):
    # create an empty mp3 file
    files_path = f"outputs/{language}/files.txt"
    open(files_path, 'w').close()
    
    with open(original_file_path, 'r', encoding='utf-8') as file:
        minutes = 0
        seconds = 0
        # read line by line
        for line in file:
            if line.strip() == "":
                continue
            # parse something similar to (00:01): using regex
            match = re.match(r"\((\d{2}):(\d{2})\):", line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                continue

            # translate the text
            translated_text = translate_text(line, source_language='en', target_language=language)
            # wait 5 seconds
            time.sleep(2)
            
            speak(minutes, seconds, translated_text, language, "echo", files_path)
        
        # concatenate all the mp3 files
        os.system(f"ffmpeg -f concat -safe 0 -i {files_path} -c copy outputs/{language}/output.mp3")

parser = argparse.ArgumentParser(description="Translate the texts in inputs/en to the target language and save the files into outputs/{languae}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
args = parser.parse_args()
execute(args.language, args.file)