import os
from moviepy.editor import VideoFileClip
import google.generativeai as genai
from pydub import AudioSegment
import tempfile

class VideoTranslator:
    def __init__(self, api_key):
        """
        Initialize the VideoTranslator with Gemini API key.
        
        Args:
            api_key (str): Google Gemini API key
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
    def extract_audio(self, video_path, output_path=None):
        """
        Extract audio from video file.
        
        Args:
            video_path (str): Path to the input video file
            output_path (str, optional): Path to save the audio file. If None, creates a temporary file.
            
        Returns:
            str: Path to the extracted audio file
        """
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.mp3')
            
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_path)
        video.close()
        
        return output_path
    
    def translate_audio(self, audio_path, target_language):
        """
        Translate audio content using Gemini.
        
        Args:
            audio_path (str): Path to the audio file
            target_language (str): Target language for translation
            
        Returns:
            str: Translated text
        """
        # Load audio file
        audio = AudioSegment.from_file(audio_path)
        
        # Convert audio to text (this is a placeholder - you'll need to implement
        # actual speech-to-text functionality using a service like Google Speech-to-Text)
        # For now, we'll assume we have the text
        text = "Sample text from audio"  # Replace with actual speech-to-text
        
        # Prepare the prompt for translation
        prompt = f"Translate the following text to {target_language}: {text}"
        
        # Get translation from Gemini
        response = self.model.generate_content(prompt)
        translated_text = response.text
        
        return translated_text
    
    def process_video(self, video_path, target_language, output_audio_path=None):
        """
        Process video file: extract audio and translate.
        
        Args:
            video_path (str): Path to the input video file
            target_language (str): Target language for translation
            output_audio_path (str, optional): Path to save the extracted audio
            
        Returns:
            tuple: (path to extracted audio, translated text)
        """
        # Extract audio from video
        audio_path = self.extract_audio(video_path, output_audio_path)
        
        # Translate the audio content
        translated_text = self.translate_audio(audio_path, target_language)
        
        return audio_path, translated_text

# Example usage
if __name__ == "__main__":
    # Replace with your actual Gemini API key
    API_KEY = "your_gemini_api_key"
    
    translator = VideoTranslator(API_KEY)
    video_path = "input.mp4"
    target_language = "Spanish"
    
    audio_path, translated_text = translator.process_video(video_path, target_language)
    print(f"Audio extracted to: {audio_path}")
    print(f"Translated text: {translated_text}") 