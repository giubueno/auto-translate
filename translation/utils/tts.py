from pathlib import Path
from openai import OpenAI

def speak(minutes, seconds, text, language="es", voice="echo", files_path="outputs/es/output.mp3"):
    client = OpenAI()

    output_path = Path(f"outputs/{language}")
    # Create the output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Text to be converted to speech
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice=voice,
        input=text       
    ) as response:
        # Format minutes and seconds as two-digit numbers
        minutes_str = str(minutes).zfill(2)
        seconds_str = str(seconds).zfill(2)
        speech_file_path = Path(__file__).parent.parent / f"{output_path}/{minutes_str}{seconds_str}.mp3"
        response.stream_to_file(speech_file_path)

    # Append the file path to the files.txt
    with open(files_path, 'a') as file:
        file.write(f"file '{speech_file_path}'\n")
