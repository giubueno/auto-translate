import unittest
import translators
from gtts import gTTS
import time

class TestTranslators(unittest.TestCase):
    def create_sample_audio(self, text):
        speech = gTTS(text=text, lang="en")
        file_path = f"/tmp/sample_audio_{time.time()}.mp3"
        speech.save(file_path)
        return file_path

    def test_transcribe(self):
        expected = "Surely goodness and mercy shall follow me."
        file_path = self.create_sample_audio(expected)
        translator = translators.AudioTranslator(file_path)
        transcription = translator.transcribe()
        actual = transcription.original_text()
        self.assertEqual(actual.strip(), expected)

if __name__ == "__main__":
    unittest.main()
