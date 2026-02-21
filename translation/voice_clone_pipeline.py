#!/usr/bin/env python3
"""
Voice Clone Pipeline

Pipeline for cloning a voice from a video and generating translated speech using Chatterbox.

Steps:
1. Extract audio from video
2. Transcribe with Whisper
3. Translate segments to target language
4. Generate speech with cloned voice using Chatterbox
5. Build synchronized audio output
"""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv

from transcribe import extract_audio_from_video, transcribe_audio_local
from utils.translation import translate_text
from utils.chatterbox_tts import ChatterboxVoiceCloner, voice_over_chatterbox, VoiceOverResult
from audio_builder import AudioBuilder

load_dotenv()


def run_pipeline(video_path, target_language="de", source_language="en",
                 output_dir="outputs", whisper_model="base", device=None,
                 sequential=False, gap_ms=1000, parallel_workers=4):
    """
    Run the voice clone translation pipeline.

    :param video_path: Path to the source video file
    :param target_language: Target language code (default: de for German)
    :param source_language: Source language code (default: en for English)
    :param output_dir: Output directory for generated files
    :param whisper_model: Whisper model size to use
    :param device: Device for Chatterbox (cuda, mps, cpu, or auto)
    :param sequential: If True, concatenate audio sequentially with gaps (no video sync)
    :param gap_ms: Gap in milliseconds between chunks in sequential mode
    :param parallel_workers: Number of parallel workers for translation
    """
    print("=" * 60)
    print("VOICE CLONE TRANSLATION PIPELINE (Chatterbox)")
    print("=" * 60)
    print(f"Video: {video_path}")
    print(f"Source Language: {source_language}")
    print(f"Target Language: {target_language}")
    print(f"Output Directory: {output_dir}")
    print(f"Mode: {'Sequential (with gaps)' if sequential else 'Time-synchronized'}")
    if sequential:
        print(f"Gap between chunks: {gap_ms}ms")
    print(f"Parallel workers: {parallel_workers}")
    print("=" * 60)

    # Verify input file exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Create output directory
    language_output_dir = Path(output_dir) / target_language
    language_output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize files manifest
    files_path = language_output_dir / "files.txt"
    if files_path.exists():
        os.remove(files_path)

    # Step 1: Extract audio from video
    print("\n[Step 1] Extracting audio from video...")
    video_name = Path(video_path).stem
    audio_path = f"{video_name}_audio.wav"
    extract_audio_from_video(video_path, audio_path)

    # Step 2: Initialize Chatterbox voice cloner
    print("\n[Step 2] Initializing Chatterbox voice cloner...")
    cloner = ChatterboxVoiceCloner(device=device)

    try:
        # Step 3: Transcribe audio with Whisper
        print(f"\n[Step 3] Transcribing audio with Whisper ({whisper_model} model)...")
        transcription_result = transcribe_audio_local(audio_path, whisper_model)

        if 'segments' not in transcription_result or not transcription_result['segments']:
            raise ValueError("No transcription segments found")

        segments = transcription_result['segments']
        print(f"Found {len(segments)} segments to process")

        # Step 4: Translate all segments in parallel for speed
        print(f"\n[Step 4] Translating segments in parallel ({parallel_workers} workers)...")

        # Prepare segments with their metadata
        segments_to_process = []
        for i, segment in enumerate(segments):
            original_text = segment['text'].strip()
            if not original_text:
                continue
            start_time = segment['start']
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            segments_to_process.append({
                'index': i,
                'original_text': original_text,
                'minutes': minutes,
                'seconds': seconds
            })

        # Parallel translation
        def translate_segment(seg):
            translated = translate_text(seg['original_text'], source_language, target_language)
            return {**seg, 'translated_text': translated}

        translated_segments = []
        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            futures = {executor.submit(translate_segment, seg): seg for seg in segments_to_process}
            for future in as_completed(futures):
                result = future.result()
                translated_segments.append(result)
                print(f"  Translated segment {result['index'] + 1}/{len(segments)}: "
                      f"{result['translated_text'][:40]}{'...' if len(result['translated_text']) > 40 else ''}")

        # Sort by original order
        translated_segments.sort(key=lambda x: x['index'])

        # Step 5: Generate speech for each segment in parallel
        print(f"\n[Step 5] Generating speech with cloned voice ({parallel_workers} workers)...")
        voice_over_results = []

        def generate_speech_segment(seg):
            print(f"\nSegment {seg['index'] + 1}/{len(segments)} [{seg['minutes']:02d}:{seg['seconds']:02d}]")
            print(f"  Text: {seg['translated_text'][:50]}{'...' if len(seg['translated_text']) > 50 else ''}")
            return voice_over_chatterbox(
                minutes=seg['minutes'],
                seconds=seg['seconds'],
                text=seg['translated_text'],
                audio_prompt_path=audio_path,
                language=target_language,
                files_path=str(files_path),
                cloner=cloner
            )

        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            futures = {executor.submit(generate_speech_segment, seg): seg for seg in translated_segments}
            for future in as_completed(futures):
                voice_over_results.append(future.result())

        # Step 6: Build audio output
        mode_desc = "sequential" if sequential else "synchronized"
        print(f"\n[Step 6] Building {mode_desc} audio...")
        audio_builder = AudioBuilder(
            language=target_language,
            sequential=sequential,
            gap_ms=gap_ms
        )
        audio_builder.build(voice_over_results)

        output_file = language_output_dir / f"{target_language}_synced.mp3"
        print(f"\n{'=' * 60}")
        print("PIPELINE COMPLETE")
        print(f"{'=' * 60}")
        print(f"Output file: {output_file}")
        print(f"Individual segments: {language_output_dir}/*.mp3")

    finally:
        # Clean up extracted audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"Cleaned up temporary audio file: {audio_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Voice Clone Translation Pipeline - Clone voice and translate to another language using Chatterbox"
    )
    parser.add_argument(
        "-v", "--video",
        required=True,
        help="Path to the source video file"
    )
    parser.add_argument(
        "-l", "--language",
        default="de",
        help="Target language code (default: de for German)"
    )
    parser.add_argument(
        "-s", "--source",
        default="en",
        help="Source language code (default: en for English)"
    )
    parser.add_argument(
        "-o", "--output",
        default="outputs",
        help="Output directory (default: outputs)"
    )
    parser.add_argument(
        "-m", "--model",
        default="base",
        help="Whisper model size: tiny, base, small, medium, large (default: base)"
    )
    parser.add_argument(
        "-d", "--device",
        default=None,
        help="Device for Chatterbox: cuda, mps, cpu (default: auto-detect)"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Concatenate audio sequentially with gaps instead of time-synced overlay"
    )
    parser.add_argument(
        "-g", "--gap",
        type=int,
        default=1000,
        help="Gap in milliseconds between chunks in sequential mode (default: 1000)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for translation (default: 4)"
    )

    args = parser.parse_args()

    run_pipeline(
        video_path=args.video,
        target_language=args.language,
        source_language=args.source,
        output_dir=args.output,
        whisper_model=args.model,
        device=args.device,
        sequential=args.sequential,
        gap_ms=args.gap,
        parallel_workers=args.workers
    )


if __name__ == "__main__":
    main()
