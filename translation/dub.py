"""
Dub: generate cloned-voice audio from translated transcription segments.

Reads translated segments JSON (from translate.py) and uses Chatterbox TTS
with per-segment audio prompts to reproduce the original speaker's voice
in the target language, preserving intonation per segment.

Usage:
  python dub.py -f outputs/de/20260308_segments.json -l de
  python dub.py -f outputs/es/20260308_segments.json -l es --device cpu
"""

import argparse
import json
import os
from pathlib import Path

from utils.chatterbox_tts import ChatterboxVoiceCloner, voice_over_chatterbox, VoiceOverResult
from audio_builder import AudioBuilder


def dub_segments(segments, language, output_dir, device=None, workers=4):
    """
    Generate cloned-voice audio for each translated segment using Chatterbox.
    Uses per-segment audio prompts for intonation-accurate voice cloning.

    :param segments: List of translated segment dicts with 'translated_text' and 'audio_prompt'
    :param language: Target language code
    :param output_dir: Output directory for audio files
    :param device: Chatterbox device (cuda, mps, cpu, or None for auto)
    :param workers: Number of parallel workers for audio generation
    :return: List of VoiceOverResult objects
    """
    os.makedirs(output_dir, exist_ok=True)

    files_path = os.path.join(output_dir, "files.txt")
    # Clear the files manifest
    open(files_path, 'w').close()

    # Initialize Chatterbox once (GPU-bound, sequential)
    print(f"Initializing Chatterbox voice cloner...")
    cloner = ChatterboxVoiceCloner(device=device)

    voice_over_results = []
    total = len(segments)

    for i, seg in enumerate(segments):
        text = seg.get('translated_text', seg.get('text', ''))
        if not text.strip():
            continue

        minutes = seg.get('minutes', 0)
        seconds = seg.get('seconds', 0)
        audio_prompt = seg.get('audio_prompt')

        if not audio_prompt or not os.path.exists(audio_prompt):
            print(f"  WARNING: No audio prompt for segment {i}, skipping")
            continue

        prosody = seg.get('prosody', {})
        rate_info = f" | rate: {prosody.get('speech_rate_wps', '?')} wps" if prosody else ""
        print(f"\n[{i + 1}/{total}] ({minutes:02d}:{seconds:02d}){rate_info}")
        print(f"  Text: {text[:60]}{'...' if len(text) > 60 else ''}")
        print(f"  Prompt: {Path(audio_prompt).name}")

        result = voice_over_chatterbox(
            minutes=minutes,
            seconds=seconds,
            text=text,
            audio_prompt_path=audio_prompt,
            language=language,
            files_path=files_path,
            cloner=cloner
        )
        voice_over_results.append(result)

    return voice_over_results


def main(segments_file, language, device=None, output_dir=None, workers=4):
    """
    Main dubbing function.
    :param segments_file: Path to translated segments JSON
    :param language: Target language code
    :param device: Chatterbox device
    :param output_dir: Output directory (default: outputs/{language})
    :param workers: Number of parallel workers
    """
    with open(segments_file, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    # Verify segments have translated text
    has_translation = any('translated_text' in seg for seg in segments)
    if not has_translation:
        print("ERROR: Segments file has no 'translated_text' field.")
        print("Run translate.py first to translate the segments.")
        return

    print("=" * 60)
    print("DUBBING PIPELINE (Chatterbox Voice Cloning)")
    print("=" * 60)
    print(f"Segments file: {segments_file}")
    print(f"Target language: {language}")
    print(f"Segments to dub: {len(segments)}")
    print("=" * 60)

    if output_dir is None:
        output_dir = os.path.join("outputs", language)

    # Generate cloned-voice audio for each segment
    voice_over_results = dub_segments(segments, language, output_dir, device, workers)

    if not voice_over_results:
        print("ERROR: No audio segments were generated.")
        return

    # Build final synchronized audio
    print(f"\nBuilding synchronized audio from {len(voice_over_results)} segments...")
    audio_builder = AudioBuilder(language=language)
    audio_builder.build(voice_over_results)

    output_file = os.path.join(output_dir, f"{language}_synced.mp3")
    print(f"\n{'=' * 60}")
    print("DUBBING COMPLETE")
    print(f"{'=' * 60}")
    print(f"Output: {output_file}")
    print(f"Segments: {output_dir}/*.mp3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dub translated segments using Chatterbox voice cloning"
    )
    parser.add_argument("-f", "--file", required=True,
                        help="Path to translated segments JSON (from translate.py)")
    parser.add_argument("-l", "--language", required=True,
                        help="Target language code (e.g. de, es, fr)")
    parser.add_argument("-d", "--device", default=None,
                        help="Chatterbox device: cuda, mps, cpu (default: auto)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output directory (default: outputs/{language})")
    parser.add_argument("-w", "--workers", type=int, default=4,
                        help="Number of parallel workers (default: 4)")
    args = parser.parse_args()

    main(args.file, args.language, args.device, args.output, args.workers)