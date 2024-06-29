import whisper
import boto3
from pathlib import Path
import os
from openai import OpenAI
import time

class Segment:
    def __init__(self, text, segment):
        self.original = segment
        self.text = text

    def original_text(self):
        return self.original["text"]

class Transcription:
    def __init__(self, transcription):
        self.transcription = transcription
        self.segments = transcription["segments"]
        self.translated_text = None
        self.translated_segments = []

    def original_text(self):
        return self.transcription["text"]
    
    def source_language(self):
        return self.transcription["language"]
    
    def add_translated_segment(self, text, segment):
        if self.translated_text is None:
            self.translated_text = text
        else:
            self.translated_text += " " + text
        self.translated_segments.append(Segment(text, segment))

class AudioTranslator:
    def __init__(self, audio_file_path, language="de", destination_folder="outputs"):
        self.audio_file_path = audio_file_path
        self.language = language
        self.destination_folder = destination_folder
        self.transcription = None

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
        model = whisper.load_model("medium")

        # Transcribe the audio file
        result = model.transcribe(self.audio_file_path, word_timestamps=True)
        self.transcription = Transcription(result)
        return self.transcription

    def translate(self):
        """
        Translate text from source language to target language using AWS Translate.

        :param text: Text to translate
        :param source_language: Source language code (e.g., 'en' for English)
        :param target_language: Target language code (e.g., 'es' for Spanish)
        :return: Translated text
        """
        translate = boto3.client(service_name='translate', region_name='us-east-1', use_ssl=True)
        for _, segment in enumerate(self.transcription.segments):
            text = segment["text"]
            source_language = self.transcription.source_language()
            target_language = self.language
            result = translate.translate_text(Text=text, SourceLanguageCode=source_language, TargetLanguageCode=target_language)
            translated_text = result.get('TranslatedText')
            self.transcription.add_translated_segment(translated_text, segment)
        return self.transcription.translated_text

    def text_to_speech(self):
        client = OpenAI()
        file_list = []

        # make sure all the folders exist
        os.makedirs(f"{self.destination_folder}/{self.language}", exist_ok=True)

        segments = self.transcription.translated_segments

        # Print the chunks
        for segment in segments:
            chunk = segment.text

            # Text to be converted to speech
            with client.audio.speech.with_streaming_response.create(
                model="tts-1-hd",
                voice="echo",
                input=chunk
            ) as response:
                timestamp = int(time.time())
                speech_file_path = Path(__file__).parent / f"outputs/{self.language}/openai_{timestamp}.mp3"
                response.stream_to_file(speech_file_path)
                file_list.append(speech_file_path)
        return file_list

    def run(self):
        self.transcribe()
        self.translate()
        self.text_to_speech()