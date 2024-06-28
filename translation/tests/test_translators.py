import unittest
import translators
from gtts import gTTS
import time
from difflib import SequenceMatcher

class TestTranslators(unittest.TestCase):
    def strings_are_similar(self, str1, str2, threshold):
        # Calculate the similarity ratio using SequenceMatcher
        similarity_ratio = SequenceMatcher(None, str1, str2).ratio()
        # Compare the similarity ratio with the threshold
        return similarity_ratio >= threshold

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
        self.assertTrue(self.strings_are_similar(actual, expected, 0.95))

if __name__ == "__main__":
    unittest.main()
