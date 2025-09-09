import random
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

def save_transcription_result(result, output_file):
    """
    Save transcription result to JSON file
    :param result: Transcription result from Whisper
    :param output_file: Output file path
    """
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Transcription saved to: {output_file}")

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

def main(file_path, model_name="base"):
    """
    Main function to transcribe audio/video file
    :param file_path: Path to audio or video file
    :param model_name: Whisper model to use
    """
    # Check if the file is a video file
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext in video_extensions:
        print(f"Processing video file: {file_path}")
        # Extract audio from video
        audio_path = extract_audio_from_video(file_path)
        file_to_transcribe = audio_path
    else:
        print(f"Processing audio file: {file_path}")
        file_to_transcribe = file_path
    
    # Transcribe the audio
    result = transcribe_audio_local(file_to_transcribe, model_name)
    
    # Save results
    output_file = f"{Path(file_path).stem}_transcription.json"
    save_transcription_result(result, output_file)
    
    # Print formatted transcription
    print_formatted_transcription(result)
    
    # Clean up extracted audio file if it was created
    if file_ext in video_extensions and os.path.exists(audio_path):
        os.remove(audio_path)
        print(f"Cleaned up temporary audio file: {audio_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio/video file to text with timestamps using local Whisper")
    parser.add_argument("-f", "--file", help="Audio or video file path", required=True)
    parser.add_argument("-m", "--model", help="Whisper model size (tiny, base, small, medium, large)", default="base")
    args = parser.parse_args()

    main(args.file, args.model)
