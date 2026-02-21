import argparse
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
from utils.translation import translate_text
from utils.chatterbox_tts import ChatterboxVoiceCloner, voice_over_chatterbox

def execute(language, original_file_path, audio_prompt_path, workers=4):
    # create output directory
    os.makedirs(f"outputs/{language}", exist_ok=True)

    # create an empty files list
    files_path = f"outputs/{language}/files.txt"
    open(files_path, 'w').close()

    # Initialize Chatterbox voice cloner once for reuse
    cloner = ChatterboxVoiceCloner()

    # First pass: collect all segments with timestamps and translated text
    segments = []
    with open(original_file_path, 'r', encoding='utf-8') as file:
        minutes = 0
        seconds = 0
        for line in file:
            if line.strip() == "":
                continue
            match = re.match(r"\((\d{2}):(\d{2})\):", line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                continue

            translated_text = translate_text(line, source_language='en', target_language=language)
            segments.append({'minutes': minutes, 'seconds': seconds, 'text': translated_text})

    # Generate audio in parallel
    print(f"Generating audio for {len(segments)} segments with {workers} workers...")
    results = []

    def generate_audio(seg):
        return voice_over_chatterbox(seg['minutes'], seg['seconds'], seg['text'], audio_prompt_path, language, files_path, cloner)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(generate_audio, seg): seg for seg in segments}
        for future in as_completed(futures):
            results.append(future.result())

    # Sort results by timestamp and rewrite files.txt in correct order
    results.sort(key=lambda r: r.minutes * 60 + r.seconds)
    with open(files_path, 'w') as f:
        for r in results:
            f.write(f"file '{r.files_path}'\n")

    # concatenate all the mp3 files
    os.system(f"ffmpeg -f concat -safe 0 -i {files_path} -c copy outputs/{language}/output.mp3")

parser = argparse.ArgumentParser(description="Translate texts and generate speech using Chatterbox TTS with voice cloning")
parser.add_argument("-l", "--language", help="Target language", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
parser.add_argument("-a", "--audio", help="Audio prompt file for voice cloning", required=True)
parser.add_argument("-w", "--workers", type=int, default=4, help="Number of parallel workers for audio generation (default: 4)")
args = parser.parse_args()
execute(args.language, args.file, args.audio, args.workers)
