import unittest
from unittest.mock import patch
import translators
from gtts import gTTS
import time
from difflib import SequenceMatcher

class TestTranslators(unittest.TestCase):
    def strings_are_similar(self, str1, str2, threshold):
        # Calculate the similarity ratio using SequenceMatcher
        similarity_ratio = SequenceMatcher(None, str1, str2).ratio()
        # Compare the similarity ratio with the threshold
        if similarity_ratio >= threshold:
            return True
        else:
            self.assertEqual(str1, str2)

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

    @patch("translators.translate_text", return_value="Sicherlich werden mir Güte und Barmherzigkeit folgen.")
    def test_translate(self, mock_translate):
        original = "Surely goodness and mercy shall follow me."
        expected = "Sicherlich werden mir Güte und Barmherzigkeit folgen."
        file_path = self.create_sample_audio(original)
        translator = translators.AudioTranslator(file_path)
        translator.transcribe()
        actual = translator.translate()
        self.assertTrue(self.strings_are_similar(actual, expected, 0.95))
        mock_translate.assert_called_once()

    @patch("translators.translate_text", return_value="Sicherlich werden mir Güte und Barmherzigkeit folgen.")
    @patch("translators.ChatterboxVoiceCloner")
    def test_text_to_speech(self, mock_cloner_cls, mock_translate):
        expected = "Surely goodness and mercy shall follow me."
        file_path = self.create_sample_audio(expected)
        translator = translators.AudioTranslator(file_path)
        translator.transcribe()
        translator.translate()
        file_list = translator.text_to_speech()
        self.assertEqual(len(file_list), 1)

if __name__ == "__main__":
    unittest.main()
