from concurrent.futures import ThreadPoolExecutor, as_completed

from docx import Document
import json
import re
from utils.tts import voice_over, VoiceOverResult
from utils.translation import translate_text
import os
import argparse
from audio_builder import AudioBuilder


def _segments_path(language):
    return f"outputs/{language}/segments.json"


def translate_step(doc_path, language="de", source_language="de"):
    """Parse docx and translate all segments. Save to segments.json."""
    os.makedirs(f"outputs/{language}", exist_ok=True)

    doc = Document(doc_path)
    print(f"[translate] language: {language}")

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
            print(f"[translate] time: {str(minutes).zfill(2)}:{str(seconds).zfill(2)}")
            continue

        if language != source_language:
            content = translate_text(speech_text, source_language=source_language, target_language=language)
        else:
            content = speech_text

        segments.append({'minutes': minutes, 'seconds': seconds, 'content': content})

    out_path = _segments_path(language)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"[translate] Saved {len(segments)} segments to {out_path}")


def synthesize_step(language="de", workers=4):
    """Load segments.json and generate audio with TTS."""
    seg_path = _segments_path(language)
    with open(seg_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    files_path = f"outputs/{language}/files.txt"
    open(files_path, 'w').close()

    print(f"[synthesize] Generating audio for {len(segments)} segments with {workers} workers...")

    voice_over_results: list[VoiceOverResult] = []
    audio_builder = AudioBuilder(language=language)

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

    audio_builder.build(voice_over_results)
    print(f"[synthesize] Audio build complete for {language}")


def execute(doc_path, language="de", source_language="de", workers=4):
    """Full pipeline: translate then synthesize."""
    translate_step(doc_path, language, source_language)
    synthesize_step(language, workers)


parser = argparse.ArgumentParser(description="Translate the texts in the docx file informed to the target language and save the files into outputs/{language}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
parser.add_argument("-s", "--source_language", help="Source language of the text", required=False, default="de")
parser.add_argument("-w", "--workers", type=int, default=4, help="Number of parallel workers for audio generation (default: 4)")
parser.add_argument("--step", choices=["translate", "synthesize"], default=None, help="Run only a specific step (default: both)")
args = parser.parse_args()

if args.step == "translate":
    translate_step(args.file, args.language, args.source_language)
elif args.step == "synthesize":
    synthesize_step(args.language, args.workers)
else:
    execute(args.file, args.language, args.source_language, args.workers)
