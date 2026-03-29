"""
Translate transcription segments or plain text into a target language.

Supports two modes:
  - Segments mode: reads enriched segments JSON from transcribe.py,
    translates in parallel, preserves audio prompts and prosody data.
  - Text mode (legacy): reads a plain text file and translates line by line.

Usage:
  # Segments mode (from transcribe.py output)
  python translate.py -f outputs/20260308_segments.json -l de

  # Text mode (legacy)
  python translate.py -f inputs/texts/en/script.txt -l de --text
"""

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from utils.translation import translate_text, get_active_backend

load_dotenv()


def translate_segments(segments, source_language, target_language, workers=4):
    """
    Translate a list of enriched segments in parallel.
    :param segments: List of segment dicts with 'text' field
    :param source_language: Source language code
    :param target_language: Target language code
    :param workers: Number of parallel workers
    :return: List of segments with 'translated_text' added
    """
    backend = get_active_backend()
    print(f"Using translation backend: {backend}")
    print(f"Translating {len(segments)} segments ({source_language} -> {target_language}) with {workers} workers...")

    def do_translate(seg):
        translated = translate_text(
            seg['text'],
            source_language=source_language,
            target_language=target_language
        )
        return {**seg, 'translated_text': translated}

    translated = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(do_translate, seg): seg for seg in segments}
        for future in as_completed(futures):
            result = future.result()
            idx = result.get('index', '?')
            preview = result['translated_text'][:50]
            print(f"  [{idx}] {preview}{'...' if len(result['translated_text']) > 50 else ''}")
            translated.append(result)

    translated.sort(key=lambda x: x.get('index', 0))
    return translated


def save_translated_txt(segments, output_file):
    """
    Save translated segments as a human-readable .txt with timestamps and prosody.
    :param segments: List of translated segment dicts
    :param output_file: Output .txt path
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for seg in segments:
            minutes = seg.get('minutes', 0)
            seconds = seg.get('seconds', 0)
            f.write(f"Speaker ({minutes:02d}:{seconds:02d}):\n")
            f.write(f"{seg['translated_text']}\n")

            prosody = seg.get('prosody', {})
            if prosody:
                f.write(f"  [rate: {prosody.get('speech_rate_wps', '?')} wps | "
                        f"duration: {prosody.get('duration_s', '?')}s | "
                        f"words: {prosody.get('word_count', '?')} | "
                        f"avg_pause: {prosody.get('avg_pause_s', '?')}s]\n")

            f.write("\n")

    print(f"Translated text saved to: {output_file}")


def execute_segments(file_path, target_language, source_language="en", output_dir=None, workers=4):
    """
    Translate enriched segments JSON from transcribe.py.
    :param file_path: Path to the segments JSON file
    :param target_language: Target language code
    :param source_language: Source language code
    :param output_dir: Output directory (default: outputs/{target_language})
    :param workers: Number of parallel workers
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    print(f"Loaded {len(segments)} segments from {file_path}")

    if output_dir is None:
        output_dir = os.path.join("outputs", target_language)
    os.makedirs(output_dir, exist_ok=True)

    # Translate
    translated = translate_segments(segments, source_language, target_language, workers)

    # Derive file stem from input filename
    file_stem = Path(file_path).stem.replace('_segments', '')

    # Save translated segments JSON (preserves audio_prompt, prosody, adds translated_text)
    json_out = os.path.join(output_dir, f"{file_stem}_segments.json")
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump(translated, f, ensure_ascii=False, indent=2)
    print(f"Translated segments saved to: {json_out}")

    # Save human-readable txt
    txt_out = os.path.join(output_dir, f"{file_stem}_transcription.txt")
    save_translated_txt(translated, txt_out)

    print(f"\n=== Translation complete: {len(translated)} segments -> {target_language} ===")


def execute_text(file_path, target_language, source_language="en"):
    """
    Legacy text mode: translate a plain text file line by line.
    :param file_path: Path to the text file
    :param target_language: Target language code
    :param source_language: Source language code
    """
    output_path = Path(f"inputs/texts/{target_language}")
    output_path.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    filename = os.path.basename(file_path)

    with open(output_path / filename, 'w', encoding='utf-8') as f:
        for line in lines:
            translated = translate_text(line, source_language=source_language, target_language=target_language)
            f.write(translated)

    print(f"Translated text saved to: {output_path / filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Translate transcription segments or plain text to a target language"
    )
    parser.add_argument("-f", "--file", required=True, help="Path to segments JSON or text file")
    parser.add_argument("-l", "--language", required=True, help="Target language code (e.g. de, es, fr)")
    parser.add_argument("-s", "--source", default="en", help="Source language code (default: en)")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: outputs/{language})")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Number of parallel workers (default: 4)")
    parser.add_argument("--text", action="store_true", help="Use legacy text mode (line-by-line translation)")
    args = parser.parse_args()

    if args.text:
        execute_text(args.file, args.language, args.source)
    else:
        execute_segments(args.file, args.language, args.source, args.output, args.workers)