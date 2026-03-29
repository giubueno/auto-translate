"""Simple TTS using gTTS for tts_from_docx pipeline."""
from pathlib import Path

from gtts import gTTS


class VoiceOverResult:
    """Result of a single voice-over segment (matches chatterbox_tts API)."""
    def __init__(self, minutes, seconds, text, language="de", audio_prompt_path=None, files_path="outputs/de/output.mp3"):
        self.minutes = minutes
        self.seconds = seconds
        self.text = text
        self.language = language
        self.audio_prompt_path = audio_prompt_path
        self.files_path = files_path


def voice_over(minutes, seconds, content, language="de", files_path="outputs/de/files.txt") -> VoiceOverResult:
    """
    Generate speech from text using gTTS and append to the files manifest.

    :param minutes: Timestamp minutes
    :param seconds: Timestamp seconds
    :param content: Text to convert to speech
    :param language: Target language code (e.g. de, es, en)
    :param files_path: Path to the files manifest
    :return: VoiceOverResult with path to the generated mp3
    """
    output_path = Path(f"outputs/{language}")
    output_path.mkdir(parents=True, exist_ok=True)
    minutes_str = str(minutes).zfill(2)
    seconds_str = str(seconds).zfill(2)
    speech_file_path = Path(f"outputs/{language}/{minutes_str}{seconds_str}.mp3")
    if not speech_file_path.exists():
        tts = gTTS(text=content, lang=language)
        tts.save(str(speech_file_path))
    with open(files_path, "a") as f:
        f.write(f"file '{speech_file_path}'\n")
    return VoiceOverResult(minutes, seconds, content, language, None, str(speech_file_path))
