"""
Doublage: replace only the voice in an .mp4 video with dubbed audio.

Uses Demucs to separate the original audio into vocals and background,
discards the original vocals, mixes the dubbed voice with the original
background (music, ambience, effects), and produces a new .mp4.

Usage:
  python doublage.py -v inputs/20260308.mp4 -l de
  python doublage.py -v inputs/20260308.mp4 -a outputs/de/de_synced.mp3
  python doublage.py -v inputs/20260308.mp4 -l de --full  # replace all audio
"""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def extract_audio_wav(video_path, output_wav):
    """
    Extract audio from video as WAV for Demucs processing.
    """
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
        '-y', output_wav
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  Extracted audio: {output_wav}")
    return output_wav


def separate_vocals(audio_wav, output_dir):
    """
    Use Demucs to separate audio into vocals and no_vocals (background) stems.

    :param audio_wav: Path to the source WAV audio
    :param output_dir: Directory for Demucs output
    :return: (vocals_path, no_vocals_path)
    """
    print("  Running Demucs vocal separation (htdemucs)...")
    cmd = [
        'python3', '-m', 'demucs',
        '--two-stems', 'vocals',
        '-o', output_dir,
        audio_wav
    ]
    subprocess.run(cmd, check=True)

    # Demucs outputs to {output_dir}/htdemucs/{stem_name}/
    audio_stem = Path(audio_wav).stem
    demucs_dir = os.path.join(output_dir, 'htdemucs', audio_stem)

    vocals_path = os.path.join(demucs_dir, 'vocals.wav')
    no_vocals_path = os.path.join(demucs_dir, 'no_vocals.wav')

    if not os.path.exists(no_vocals_path):
        raise FileNotFoundError(f"Demucs output not found: {no_vocals_path}")

    print(f"  Vocals: {vocals_path}")
    print(f"  Background: {no_vocals_path}")
    return vocals_path, no_vocals_path


def mix_audio(background_path, dubbed_voice_path, output_path):
    """
    Mix the original background audio with the dubbed voice using ffmpeg.

    :param background_path: Path to the background (no vocals) WAV
    :param dubbed_voice_path: Path to the dubbed voice audio
    :param output_path: Path for the mixed output audio
    :return: Path to the mixed audio
    """
    print("  Mixing background + dubbed voice...")
    cmd = [
        'ffmpeg',
        '-i', background_path,
        '-i', dubbed_voice_path,
        '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest:normalize=0',
        '-ac', '2',
        '-y', output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  Mixed audio: {output_path}")
    return output_path


def mux_video_audio(video_path, audio_path, output_path):
    """
    Combine original video stream with new audio into final .mp4.
    Video is copied without re-encoding.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        '-y',
        output_path
    ]

    subprocess.run(cmd, check=True)
    print(f"  Final video: {output_path}")
    return output_path


def main(video_path, language=None, audio_path=None, output_path=None, full_replace=False):
    """
    Main doublage function.

    :param video_path: Path to the original .mp4
    :param language: Target language code
    :param audio_path: Explicit path to dubbed audio
    :param output_path: Explicit output path
    :param full_replace: If True, replace all audio (no vocal separation)
    """
    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found: {video_path}")
        return

    video_stem = Path(video_path).stem

    # Resolve dubbed audio path
    if audio_path is None:
        if language is None:
            print("ERROR: Provide either --language or --audio")
            return
        audio_path = os.path.join("outputs", language, f"{language}_synced.mp3")

    if not os.path.exists(audio_path):
        print(f"ERROR: Dubbed audio not found: {audio_path}")
        print("Run ./dub.sh first to generate the dubbed audio.")
        return

    # Resolve output path
    if output_path is None:
        if language:
            output_path = os.path.join("outputs", language, f"{video_stem}_{language}.mp4")
        else:
            output_path = os.path.join("outputs", f"{video_stem}_dubbed.mp4")

    print("=" * 60)
    if full_replace:
        print("DOUBLAGE (Full Audio Replacement)")
    else:
        print("DOUBLAGE (Voice-Only Replacement via Demucs)")
    print("=" * 60)
    print(f"  Video: {video_path}")
    print(f"  Dubbed audio: {audio_path}")
    print(f"  Output: {output_path}")
    print("=" * 60)

    if full_replace:
        # Simple mode: replace entire audio track
        mux_video_audio(video_path, audio_path, output_path)
    else:
        # Voice-only mode: separate vocals, mix background + dubbed voice
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Step 1: Extract audio from video
            print("\n[Step 1] Extracting audio from video...")
            original_wav = os.path.join(tmp_dir, "original.wav")
            extract_audio_wav(video_path, original_wav)

            # Step 2: Separate vocals from background using Demucs
            print("\n[Step 2] Separating vocals from background...")
            vocals_path, background_path = separate_vocals(original_wav, tmp_dir)

            # Step 3: Mix background + dubbed voice
            print("\n[Step 3] Mixing background with dubbed voice...")
            mixed_audio = os.path.join(tmp_dir, "mixed.wav")
            mix_audio(background_path, audio_path, mixed_audio)

            # Step 4: Mux mixed audio with original video
            print("\n[Step 4] Creating final video...")
            mux_video_audio(video_path, mixed_audio, output_path)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print("DOUBLAGE COMPLETE")
    print(f"{'=' * 60}")
    print(f"Output: {output_path} ({file_size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Doublage: replace voice in video with dubbed audio, preserving background"
    )
    parser.add_argument("-v", "--video", required=True,
                        help="Path to the original .mp4 video")
    parser.add_argument("-l", "--language", default=None,
                        help="Target language code (auto-finds outputs/{lang}/{lang}_synced.mp3)")
    parser.add_argument("-a", "--audio", default=None,
                        help="Explicit path to dubbed audio file (overrides --language)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output .mp4 path (default: outputs/{lang}/{stem}_{lang}.mp4)")
    parser.add_argument("--full", action="store_true",
                        help="Replace entire audio track instead of voice-only")
    args = parser.parse_args()

    main(args.video, args.language, args.audio, args.output, args.full)
