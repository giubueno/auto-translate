from utils.tts import VoiceOverResult
from pydub import AudioSegment

class AudioBuilder:
    def __init__(self, language="de"):
        self.language = language
        self.files_path = f"outputs/{language}/files.txt"

    def merge_files_respecting_time(self):
        # read the files.txt file
        with open(self.files_path, 'r') as file:
            lines = file.readlines()
        
        # sort the lines by the time
        lines.sort(key=lambda x: x.split('file ')[1].split('.mp3')[0])
        
        # merge the files
        with open(self.files_path, 'w') as file:
            file.writelines(lines)

        # create a new audio segment
        audio_result = AudioSegment.empty()

    def build(self, voice_over_results: list[VoiceOverResult]):
        self.merge_files_respecting_time()
        
        # Calculate the total duration needed
        max_end_time = 0
        audio_segments = []
        
        for voice_over_result in voice_over_results:
            # open the audio file
            audio_file = AudioSegment.from_mp3(voice_over_result.files_path)
            # calculate the duration of the audio file
            duration = len(audio_file)
            # calculate the start time of the audio file
            start_time = voice_over_result.minutes * 60 * 1000 + voice_over_result.seconds * 1000
            # calculate the end time of the audio file
            end_time = start_time + duration
            
            audio_segments.append((audio_file, start_time, duration))
            max_end_time = max(max_end_time, end_time)
            
            print(f"Prepared {voice_over_result.files_path} at {start_time}ms with duration {duration}ms")
        
        # Create a base audio segment with silence for the total duration
        audio_result = AudioSegment.silent(duration=max_end_time)
        
        # Overlay each audio segment at its specified position
        for audio_file, start_time, duration in audio_segments:
            audio_result = audio_result.overlay(audio_file, position=start_time)
        
        print(f"Saving {self.language}_synced.mp3")
        audio_result.export(f"outputs/{self.language}/{self.language}_synced.mp3", format="mp3")