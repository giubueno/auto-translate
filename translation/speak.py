from pathlib import Path
import os
from openai import OpenAI
import argparse

def speak(input_file_path, language="es", voice="echo"):
    '''Convert text to speech using OpenAI's API'''
    client = OpenAI()

    output_path = Path(f"outputs/{language}")
    # Create the output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

        i = 0
        for line in lines:
            text = line.strip()
            if text == "":
                continue
            i += 1

            # Text to be converted to speech
            with client.audio.speech.with_streaming_response.create(
                model="tts-1-hd",
                voice=voice,
                input=text
            ) as response:
                speech_file_path = Path(__file__).parent / f"{output_path}/{os.path.basename(file.name)}_{i}.mp3"
                response.stream_to_file(speech_file_path)

def execute(language="es", voice="echo"):
    '''Convert all text files in the input directory to speech using OpenAI's API'''
    input_files = Path(__file__).parent / f"inputs/texts/{language}"
    for input_file in input_files.iterdir():
        speak(input_file, language, voice)

# Parse the command line arguments
parser = argparse.ArgumentParser(description="Convert text to speech using OpenAI's API")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Text file path", required=False)
parser.add_argument("-v", "--voice", help="Voice", required=False, default="echo")
args = parser.parse_args()

if args.file is None:
    execute(args.language, args.voice)
else:
    speak(args.file, args.language, args.voice)

# python speak.py -l es -v onyx