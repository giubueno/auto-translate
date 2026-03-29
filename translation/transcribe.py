import argparse
import os
import subprocess
from pathlib import Path
import json
import whisper

def extract_audio_from_video(video_path, output_audio_path=None):
    """
    Extract audio from MP4 video file using ffmpeg
    :param video_path: Path to the MP4 video file
    :param output_audio_path: Path for the output audio file (optional)
    :return: Path to the extracted audio file
    """
    if output_audio_path is None:
        video_name = Path(video_path).stem
        output_audio_path = f"{video_name}_audio.wav"
    
    try:
        # Use ffmpeg to extract audio from video
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite output file
            output_audio_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Audio extracted from {video_path} to {output_audio_path}")
        return output_audio_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        raise
    except FileNotFoundError:
        print("ffmpeg not found. Please install ffmpeg to process video files.")
        raise

def transcribe_audio_local(audio_path, model_name="base"):
    """
    Transcribe audio using local Whisper model
    :param audio_path: Path to the audio file
    :param model_name: Whisper model size (tiny, base, small, medium, large)
    :return: Transcription result with timestamps
    """
    print(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)
    
    print(f"Transcribing audio file: {audio_path}")
    result = model.transcribe(audio_path, word_timestamps=True)
    
    return result

def extract_segment_audio(audio_path, start_time, end_time, output_path):
    """
    Extract a segment of audio using ffmpeg.
    :param audio_path: Path to the source audio file
    :param start_time: Start time in seconds
    :param end_time: End time in seconds
    :param output_path: Path to save the extracted segment
    :return: Path to the extracted segment
    """
    duration = end_time - start_time
    cmd = [
        'ffmpeg', '-i', audio_path,
        '-ss', str(start_time),
        '-t', str(duration),
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        '-y',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def compute_segment_prosody(segment):
    """
    Compute prosody metadata for a transcription segment.
    :param segment: Whisper transcription segment with word timestamps
    :return: Dict with speech_rate_wps, duration_s, word_count, avg_pause_s
    """
    start = float(segment['start'])
    end = float(segment['end'])
    duration = end - start
    text = segment['text'].strip()
    word_count = len(text.split())

    speech_rate = round(word_count / duration, 2) if duration > 0 else 0.0

    # Compute average pause between words from word-level timestamps
    avg_pause = 0.0
    words = segment.get('words', [])
    if len(words) > 1:
        pauses = []
        for i in range(1, len(words)):
            gap = float(words[i]['start']) - float(words[i - 1]['end'])
            if gap > 0:
                pauses.append(gap)
        avg_pause = round(sum(pauses) / len(pauses), 3) if pauses else 0.0

    return {
        'duration_s': round(duration, 2),
        'word_count': word_count,
        'speech_rate_wps': speech_rate,
        'avg_pause_s': avg_pause,
    }


def extract_segment_prompts(audio_path, result, output_dir):
    """
    Extract per-segment audio clips and compute prosody metadata.
    These clips serve as voice prompts for Chatterbox so it can
    reproduce the original intonation per segment.
    :param audio_path: Path to the full audio file
    :param result: Whisper transcription result
    :param output_dir: Directory to save segment audio clips
    :return: List of enriched segment dicts with audio_prompt and prosody
    """
    prompts_dir = os.path.join(output_dir, "prompts")
    os.makedirs(prompts_dir, exist_ok=True)

    enriched_segments = []

    for i, segment in enumerate(result.get('segments', [])):
        text = segment['text'].strip()
        if not text:
            continue

        start = float(segment['start'])
        end = float(segment['end'])
        minutes = int(start // 60)
        seconds = int(start % 60)

        # Extract audio clip for this segment
        prompt_filename = f"prompt_{i:04d}_{minutes:02d}{seconds:02d}.wav"
        prompt_path = os.path.join(prompts_dir, prompt_filename)
        extract_segment_audio(audio_path, start, end, prompt_path)

        # Compute prosody metadata
        prosody = compute_segment_prosody(segment)

        enriched_segments.append({
            'index': i,
            'start': start,
            'end': end,
            'minutes': minutes,
            'seconds': seconds,
            'text': text,
            'audio_prompt': prompt_path,
            'prosody': prosody,
        })

    return enriched_segments


def save_transcription_result(result, output_file):
    """
    Save transcription result to JSON file
    :param result: Transcription result from Whisper
    :param output_file: Output file path
    """
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Transcription saved to: {output_file}")

def save_transcription_txt(result, output_file, enriched_segments=None):
    """
    Save transcription as a .txt file with (MM:SS) timestamps and prosody info.
    Format is compatible with tts_from_docx.py pipeline.
    :param result: Whisper transcription result
    :param output_file: Output .txt file path
    :param enriched_segments: Optional enriched segments with prosody data
    """
    # Build a lookup from enriched segments if available
    prosody_map = {}
    if enriched_segments:
        for seg in enriched_segments:
            prosody_map[seg['index']] = seg

    with open(output_file, 'w', encoding='utf-8') as f:
        if 'segments' in result:
            for i, segment in enumerate(result['segments']):
                text = segment['text'].strip()
                if not text:
                    continue
                timestamp = format_time(segment['start'])

                f.write(f"Speaker ({timestamp}):\n")
                f.write(f"{text}\n")

                if i in prosody_map:
                    p = prosody_map[i]['prosody']
                    f.write(f"  [rate: {p['speech_rate_wps']} wps | "
                            f"duration: {p['duration_s']}s | "
                            f"words: {p['word_count']} | "
                            f"avg_pause: {p['avg_pause_s']}s]\n")

                f.write("\n")

    print(f"Transcription text saved to: {output_file}")

def print_formatted_transcription(result):
    """
    Print the transcription in a readable format with timestamps
    :param result: Transcription result from Whisper
    """
    print("\n" + "="*60)
    print("TRANSCRIPTION WITH TIMESTAMPS")
    print("="*60)
    
    if 'segments' in result:
        for segment in result['segments']:
            start_time = format_time(segment['start'])
            end_time = format_time(segment['end'])
            text = segment['text'].strip()
            
            print(f"\n[{start_time} - {end_time}] {text}")
            
            # Print word-level timestamps if available
            if 'words' in segment and segment['words']:
                print("  Words:")
                for word_info in segment['words']:
                    word_start = format_time(word_info['start'])
                    word_end = format_time(word_info['end'])
                    word = word_info['word']
                    print(f"    [{word_start}-{word_end}] {word}")
    else:
        print("No transcription segments found")

def format_time(seconds):
    """
    Format seconds into MM:SS format
    :param seconds: Time in seconds
    :return: Formatted time string
    """
    if seconds is None:
        return "00:00"
    
    try:
        seconds = float(seconds)
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return "00:00"

def main(file_path, model_name="base", output_dir="outputs"):
    """
    Main function to transcribe audio/video file with per-segment voice prompts.
    :param file_path: Path to audio or video file
    :param model_name: Whisper model to use
    :param output_dir: Directory to save output files
    """
    os.makedirs(output_dir, exist_ok=True)

    # Check if the file is a video file
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
    file_ext = Path(file_path).suffix.lower()
    file_stem = Path(file_path).stem

    if file_ext in video_extensions:
        print(f"Processing video file: {file_path}")
        audio_path = extract_audio_from_video(file_path)
        file_to_transcribe = audio_path
    else:
        print(f"Processing audio file: {file_path}")
        file_to_transcribe = file_path
        audio_path = file_path

    # Transcribe the audio
    result = transcribe_audio_local(file_to_transcribe, model_name)

    # Extract per-segment audio prompts and prosody metadata
    print("\nExtracting per-segment audio prompts and prosody data...")
    enriched_segments = extract_segment_prompts(audio_path, result, output_dir)
    print(f"Extracted {len(enriched_segments)} segment prompts to {output_dir}/prompts/")

    # Save results
    json_file = os.path.join(output_dir, f"{file_stem}_transcription.json")
    txt_file = os.path.join(output_dir, f"{file_stem}_transcription.txt")
    segments_file = os.path.join(output_dir, f"{file_stem}_segments.json")

    save_transcription_result(result, json_file)
    save_transcription_txt(result, txt_file, enriched_segments)

    # Save enriched segments with audio prompts and prosody
    with open(segments_file, 'w', encoding='utf-8') as f:
        json.dump(enriched_segments, f, ensure_ascii=False, indent=2)
    print(f"Enriched segments saved to: {segments_file}")

    # Print formatted transcription
    print_formatted_transcription(result)

    # Clean up extracted audio file if it was created from video
    if file_ext in video_extensions and os.path.exists(audio_path):
        os.remove(audio_path)
        print(f"Cleaned up temporary audio file: {audio_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio/video file to text with timestamps using local Whisper")
    parser.add_argument("-f", "--file", help="Audio or video file path", required=True)
    parser.add_argument("-m", "--model", help="Whisper model size (tiny, base, small, medium, large)", default="base")
    parser.add_argument("-o", "--output", help="Output directory (default: outputs)", default="outputs")
    args = parser.parse_args()

    main(args.file, args.model, args.output)
