from utils.tts import VoiceOverResult
from pydub import AudioSegment

class AudioBuilder:
    def __init__(self, language="de", sequential=False, gap_ms=1000):
        """
        Initialize AudioBuilder.

        :param language: Target language code
        :param sequential: If True, concatenate audio sequentially with gaps.
                          If False, overlay at original timestamps (video sync)
        :param gap_ms: Gap in milliseconds between chunks (only used in sequential mode)
        """
        self.language = language
        self.files_path = f"outputs/{language}/files.txt"
        self.sequential = sequential
        self.gap_ms = gap_ms

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

        if self.sequential:
            self._build_sequential(voice_over_results)
        else:
            self._build_synced(voice_over_results)

    def _build_sequential(self, voice_over_results: list[VoiceOverResult]):
        """Build audio by concatenating chunks sequentially with gaps."""
        print(f"Building sequential audio with {self.gap_ms}ms gaps between chunks...")

        # Sort by timestamp to maintain order
        sorted_results = sorted(
            voice_over_results,
            key=lambda x: x.minutes * 60 + x.seconds
        )

        # Create silence segment for gaps
        gap = AudioSegment.silent(duration=self.gap_ms)

        # Start with empty audio
        audio_result = AudioSegment.empty()

        for i, voice_over_result in enumerate(sorted_results):
            audio_file = AudioSegment.from_mp3(voice_over_result.files_path)
            duration = len(audio_file)

            print(f"Appending {voice_over_result.files_path} (duration: {duration}ms)")

            # Append audio chunk
            audio_result += audio_file

            # Add gap after each chunk except the last one
            if i < len(sorted_results) - 1:
                audio_result += gap

        output_path = f"outputs/{self.language}/{self.language}_sequential.mp3"
        print(f"Saving {output_path}")
        audio_result.export(output_path, format="mp3")
        print(f"Total duration: {len(audio_result)}ms")

    def _build_synced(self, voice_over_results: list[VoiceOverResult]):
        """Build audio by overlaying chunks at original timestamps (video sync)."""
        print("Building time-synchronized audio...")

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

        # Sort by start time to process in order
        audio_segments.sort(key=lambda x: x[1])

        # Truncate overlapping segments
        for i in range(len(audio_segments) - 1):
            audio_file, start_time, duration = audio_segments[i]
            next_start = audio_segments[i + 1][1]
            end_time = start_time + duration

            if end_time > next_start:
                overlap_ms = end_time - next_start
                max_duration = next_start - start_time - 50  # 50ms buffer
                if max_duration > 0:
                    truncated = audio_file[:max_duration].fade_out(30)
                    audio_segments[i] = (truncated, start_time, max_duration)
                    print(f"WARNING: Segment at {start_time}ms overlaps next segment by {overlap_ms}ms — truncated to {max_duration}ms")
                else:
                    # Segments start at same time or nearly — skip this segment
                    audio_segments[i] = (AudioSegment.empty(), start_time, 0)
                    print(f"WARNING: Segment at {start_time}ms fully overlaps next segment — skipped")

        # Recalculate max_end_time after truncation
        max_end_time = 0
        for audio_file, start_time, duration in audio_segments:
            max_end_time = max(max_end_time, start_time + duration)

        # Create a base audio segment with silence for the total duration
        audio_result = AudioSegment.silent(duration=max_end_time)

        # Overlay each audio segment at its specified position
        for audio_file, start_time, duration in audio_segments:
            if duration > 0:
                audio_result = audio_result.overlay(audio_file, position=start_time)

        print(f"Saving {self.language}_synced.mp3")
        audio_result.export(f"outputs/{self.language}/{self.language}_synced.mp3", format="mp3")