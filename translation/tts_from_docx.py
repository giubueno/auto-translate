from concurrent.futures import ThreadPoolExecutor, as_completed

from docx import Document
import re
from utils.tts import voice_over, VoiceOverResult
from utils.translation import translate_text
import os
import argparse
from audio_builder import AudioBuilder

def execute(doc_path, language="de", source_language="de", workers=4):
    os.makedirs(f"outputs/{language}", exist_ok=True)

    files_path = f"outputs/{language}/files.txt"
    doc = Document(doc_path)

    print("language: ", language)

    # Create an empty list of files
    open(files_path, 'w').close()

    voice_over_results: list[VoiceOverResult] = []

    audio_builder = AudioBuilder(language=language)

    # First pass: collect all segments with timestamps and translated text
    segments = []
    minutes = 0
    seconds = 0

    for paragraph in doc.paragraphs:
        speech_text = paragraph.text
        if speech_text == "":
            continue

        match = re.match(r".*\((\d{2}):(\d{2})\):?", speech_text)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            minutes_str = str(minutes).zfill(2)
            seconds_str = str(seconds).zfill(2)
            path = f"{minutes_str}:{seconds_str}"
            print("time: ", path)
            continue

        if language != source_language:
            content = translate_text(speech_text, source_language=source_language, target_language=language)
        else:
            content = speech_text

        segments.append({'minutes': minutes, 'seconds': seconds, 'content': content})

    # Generate audio in parallel
    print(f"Generating audio for {len(segments)} segments with {workers} workers...")

    def generate_audio(seg):
        print("content: ", seg['content'])
        return voice_over(seg['minutes'], seg['seconds'], seg['content'], language=language, files_path=files_path)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(generate_audio, seg): seg for seg in segments}
        for future in as_completed(futures):
            try:
                voice_over_results.append(future.result())
            except Exception as e:
                print(e)

    # build the audio
    audio_builder.build(voice_over_results)

parser = argparse.ArgumentParser(description="Translate the texts in the docx file informed to the target language and save the files into outputs/{languae}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
parser.add_argument("-s", "--source_language", help="Source language of the text", required=False, default="de")
parser.add_argument("-w", "--workers", type=int, default=4, help="Number of parallel workers for audio generation (default: 4)")
args = parser.parse_args()
execute(args.file, args.language, args.source_language, args.workers)
