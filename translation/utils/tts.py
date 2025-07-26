from pathlib import Path
from openai import OpenAI

class VoiceOverResult:
    def __init__(self, minutes, seconds, text, language="es", voice="echo", files_path="outputs/es/output.mp3"):
        self.minutes = minutes
        self.seconds = seconds
        self.text = text
        self.language = language
        self.voice = voice
        self.files_path = files_path


def voice_over(minutes, seconds, text, language="es", voice="echo", files_path="outputs/es/output.mp3") -> VoiceOverResult:
    client = OpenAI()

    output_path = Path(f"outputs/{language}")
    # Create the output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Format minutes and seconds as two-digit numbers
    minutes_str = str(minutes).zfill(2)
    seconds_str = str(seconds).zfill(2)
    speech_file_path = Path(__file__).parent.parent / f"{output_path}/{minutes_str}{seconds_str}.mp3"
    if speech_file_path.exists():
        print(f"File {speech_file_path} already exists")
    else:
        # Text to be converted to speech
        with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=voice,
            input=text,
            speed=1.1
        ) as response:
            response.stream_to_file(speech_file_path)
        
    # Append the file path to the files.txt
    with open(files_path, 'a') as file:
        file.write(f"file '{speech_file_path}'\n")

    result = VoiceOverResult(minutes, seconds, text, language, voice, speech_file_path)

    return result