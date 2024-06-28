import whisper
import json

class AudioTranslator:
    def __init__(self, audio_file_path, languages=["es", "de"], destination_folder="outputs"):
        self.audio_file_path = audio_file_path
        self.languages = languages
        self.destination_folder = destination_folder

    def transcribe(self):
        ''' 
        Transcribe an audio file using the base model and return the transcription with timestamps.
        Returns the transcription in JSON format.
        {
            "text": "Hello, this is a test.",
            "segments": [
                {
                    "id": 0,
                    "seek": 0,
                    "start": 0.0,
                    "end": 2.5,
                    "text": "Hello, this is a test.",
                    "tokens": [50364, 2159, 11, 341, 307, 257, 1332, 13],
                    "temperature": 0.0,
                    "avg_logprob": -0.450,
                    "compression_ratio": 1.2,
                    "no_speech_prob": 0.1,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5},
                        {"word": "this", "start": 0.5, "end": 0.8},
                        {"word": "is", "start": 0.8, "end": 1.0},
                        {"word": "a", "start": 1.0, "end": 1.1},
                        {"word": "test", "start": 1.1, "end": 1.5}
                    ]
                }
            ],
            "language": "en"
        }
        '''    
        # Load the Whisper model
        model = whisper.load_model("base")

        # Transcribe the audio file
        return model.transcribe(self.audio_file_path, word_timestamps=True)


    def translate(self):
        for language in self.languages:
            print(f"Translating {self.audio_file_path} to {language}...")

    def text_to_speech(self):
        for language in self.languages:
            print(f"Converting text to speech in {language}...")

    def run(self):
        self.transcribe()
        self.translate()
        self.text_to_speech()