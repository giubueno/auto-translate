import moviepy.editor as mp
from pydub import AudioSegment
import numpy as np
from scipy.io import wavfile
import tempfile
import os

def replace_voice(video_path, audio_path, output_path):
    # Load the video
    video = mp.VideoFileClip(video_path)
    
    # Extract the original audio from the video
    original_audio = video.audio
    
    # Save the original audio to a temporary WAV file
    temp_original = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    original_audio.write_audiofile(temp_original.name, codec='pcm_s16le')
    temp_original.close()
    
    # Load the original audio and new voice audio
    original, original_sr = librosa.load(temp_original.name, sr=None)
    new_voice, new_voice_sr = librosa.load(audio_path, sr=None)
    
    # Ensure both audios have the same sample rate
    if original_sr != new_voice_sr:
        new_voice = librosa.resample(new_voice, new_voice_sr, original_sr)
    
    # Separate voice and background from original audio
    S_original = librosa.stft(original)
    S_background = np.copy(S_original)
    S_background = librosa.decompose.nn_filter(S_background,
                                               aggregate=np.median,
                                               metric='cosine',
                                               width=int(librosa.time_to_frames(2, sr=original_sr)))
    S_voice = S_original - S_background
    
    # Reconstruct background audio
    background = librosa.istft(S_background)
    
    # Adjust the length of the new voice to match the original
    if len(new_voice) > len(original):
        new_voice = new_voice[:len(original)]
    else:
        new_voice = np.pad(new_voice, (0, len(original) - len(new_voice)))
    
    # Combine new voice with background
    combined = new_voice + background
    
    # Normalize audio
    combined = librosa.util.normalize(combined)
    
    # Save the combined audio to a temporary file
    temp_combined = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    wavfile.write(temp_combined.name, original_sr, (combined * 32767).astype(np.int16))
    temp_combined.close()
    
    # Load the combined audio as an AudioFileClip
    new_audio = mp.AudioFileClip(temp_combined.name)
    
    # Set the new audio to the video
    final_video = video.set_audio(new_audio)
    
    # Write the final video
    final_video.write_videofile(output_path, audio_codec='aac')
    
    # Clean up temporary files
    os.unlink(temp_original.name)
    os.unlink(temp_combined.name)

# Example usage
# replace_voice('input_video.mp4', 'new_voice.mp3', 'output_video.mp4')