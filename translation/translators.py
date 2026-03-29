import whisper
from pathlib import Path
import os
from pydub import AudioSegment
from utils.translation import translate_text
from utils.chatterbox_tts import ChatterboxVoiceCloner

class Segment:
    def __init__(self, text, segment):
        self.original = segment
        self.text = text

    def original_text(self):
        return self.original["text"]
    
    def start(self):
        return self.original["start"]

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
    def __init__(self, audio_file_path, language="de", destination_folder="outputs", audio_prompt_path=None):
        self.audio_file_path = audio_file_path
        self.language = language
        self.destination_folder = destination_folder
        self.transcription = None
        self.audio_prompt_path = audio_prompt_path or audio_file_path  # Use source audio for voice cloning if not specified
        self._cloner = None

    @property
    def cloner(self):
        """Lazy load the Chatterbox voice cloner."""
        if self._cloner is None:
            self._cloner = ChatterboxVoiceCloner()
        return self._cloner

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
        print(" Load the Whisper model")
        # Load the Whisper model
        model = whisper.load_model("medium.en")

        print("Transcribe the audio file")
        # Transcribe the audio file
        result = model.transcribe(self.audio_file_path, language="en", word_timestamps=True)
        print("Create the transcription object")
        self.transcription = Transcription(result)
        return self.transcription

    def translate(self):
        """
        Translate text from source language to target language.

        :return: Translated text
        """
        for _, segment in enumerate(self.transcription.segments):
            text = segment["text"]
            source_language = self.transcription.source_language()
            target_language = self.language
            translated_text = translate_text(text, source_language, target_language)
            self.transcription.add_translated_segment(translated_text, segment)
        return self.transcription.translated_text

    def text_to_speech(self):
        file_list = []
        file_names = []

        # make sure all the folders exist
        os.makedirs(f"{self.destination_folder}/{self.language}", exist_ok=True)

        segments = self.transcription.translated_segments

        output_folder_path = f"{self.destination_folder}/{self.language}"

        # Generate speech for each segment using Chatterbox
        for segment in segments:
            chunk = segment.text

            file_name = f"{segment.start()}.mp3"
            speech_file_path = f"{output_folder_path}/{file_name}"

            self.cloner.generate_speech(
                chunk,
                self.audio_prompt_path,
                speech_file_path,
                self.language
            )
            file_list.append(speech_file_path)
            file_names.append(file_name)

        if os.path.exists(f"{output_folder_path}/filelist.txt"):
            os.remove(f"{output_folder_path}/filelist.txt")

        # Create a temporary file to hold the list of files
        with open(f"{output_folder_path}/filelist.txt", "w") as file:
            for filename in file_names:
                file.write(f"file '{filename}'\n")

        return file_list

    def join_files(output_file, file_list):
        # Create an empty AudioSegment
        combined = AudioSegment.silent(duration=0)

        # Sort the file list based on start time
        file_list.sort(key=lambda x: x['start'])

        # Calculate the end time of the last added audio
        last_end_time = 0

        for file_info in file_list:
            # Load the audio file
            audio = AudioSegment.from_mp3(file_info['file'])

            # Calculate padding duration
            pad_duration = file_info['start'] - last_end_time

            if pad_duration > 0:
                # Add silence if there's a gap
                combined += AudioSegment.silent(duration=pad_duration)
            elif pad_duration < 0:
                # Trim the combined audio if there's an overlap
                combined = combined[:file_info['start']]

            # Add the audio to the combined track
            combined += audio

            # Update the last end time
            last_end_time = file_info['start'] + len(audio)

        # Export the final combined audio
        combined.export(output_file, format="mp3")

    def run(self):
        print("Transcribing audio...")
        self.transcribe()
        print("Translating text...")
        self.translate()
        print("Converting text to speech...")
        self.text_to_speech()