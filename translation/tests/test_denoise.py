import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import json
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.denoise import clean_audio, _build_filter_chain, _get_duration


class TestBuildFilterChain(unittest.TestCase):
    """Tests for filter chain construction."""

    def test_with_rnnoise_model(self):
        """Filter chain should include arnndn when model file exists."""
        with patch('os.path.isfile', return_value=True):
            chain = _build_filter_chain("/path/to/model.rnnn", 5.0)
        self.assertIn("arnndn=m=/path/to/model.rnnn", chain)
        self.assertIn("silenceremove", chain)
        self.assertIn("afade", chain)

    def test_without_rnnoise_model(self):
        """Filter chain should skip arnndn when model path is None."""
        chain = _build_filter_chain(None, 5.0)
        self.assertNotIn("arnndn", chain)
        self.assertIn("silenceremove", chain)
        self.assertIn("afade", chain)

    def test_fade_start_calculation(self):
        """Fade start should be duration minus 0.03s."""
        chain = _build_filter_chain(None, 2.0)
        self.assertIn("st=1.9700", chain)

    def test_fade_start_short_clip(self):
        """Fade start should be 0 for very short clips."""
        chain = _build_filter_chain(None, 0.01)
        self.assertIn("st=0.0000", chain)


class TestCleanAudioCommand(unittest.TestCase):
    """Tests for correct ffmpeg command construction."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    @patch('utils.denoise.os.path.isfile', return_value=True)
    def test_ffmpeg_called_with_correct_args(self, mock_isfile, mock_run, mock_close, mock_mkstemp, mock_replace):
        """ffmpeg should be called with the constructed filter chain."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        # ffprobe returns duration
        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '3.5'}})

        mock_run.return_value = probe_result

        clean_audio('/input.wav', '/output.wav', rnnoise_model_path='/model.rnnn')

        # Find the ffmpeg calls (not ffprobe)
        ffmpeg_calls = [c for c in mock_run.call_args_list if c[0][0][0] == 'ffmpeg']
        self.assertTrue(len(ffmpeg_calls) >= 1)

        first_ffmpeg_args = ffmpeg_calls[0][0][0]
        self.assertEqual(first_ffmpeg_args[0], 'ffmpeg')
        self.assertEqual(first_ffmpeg_args[1], '-i')
        self.assertEqual(first_ffmpeg_args[2], '/input.wav')
        self.assertIn('-af', first_ffmpeg_args)

        af_index = first_ffmpeg_args.index('-af')
        filter_str = first_ffmpeg_args[af_index + 1]
        self.assertIn('arnndn', filter_str)
        self.assertIn('silenceremove', filter_str)


class TestCleanAudioNoRNNoise(unittest.TestCase):
    """Tests for fallback when RNNoise model is missing."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    def test_fallback_without_model(self, mock_run, mock_close, mock_mkstemp, mock_replace):
        """Should use silence trim + fade only when no model path given."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '2.0'}})
        mock_run.return_value = probe_result

        clean_audio('/input.wav', '/output.wav', rnnoise_model_path=None)

        ffmpeg_calls = [c for c in mock_run.call_args_list if c[0][0][0] == 'ffmpeg']
        self.assertTrue(len(ffmpeg_calls) >= 1)

        af_index = ffmpeg_calls[0][0][0].index('-af')
        filter_str = ffmpeg_calls[0][0][0][af_index + 1]
        self.assertNotIn('arnndn', filter_str)
        self.assertIn('silenceremove', filter_str)
        self.assertIn('afade', filter_str)

    @patch('utils.denoise._cleanup_temp')
    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    @patch('utils.denoise.os.path.isfile', return_value=True)
    def test_arnndn_failure_retries_without(self, mock_isfile, mock_run, mock_close, mock_mkstemp, mock_replace, mock_cleanup):
        """When arnndn fails, should retry with silence trim + fade only."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '2.0'}})

        def side_effect(cmd, **kwargs):
            if cmd[0] == 'ffprobe':
                return probe_result
            if cmd[0] == 'ffmpeg':
                af_idx = cmd.index('-af')
                if 'arnndn' in cmd[af_idx + 1]:
                    raise subprocess.CalledProcessError(1, cmd)
                return MagicMock()
            return probe_result

        mock_run.side_effect = side_effect

        result = clean_audio('/input.wav', '/output.wav', rnnoise_model_path='/model.rnnn')

        self.assertTrue(result)
        ffmpeg_calls = [c for c in mock_run.call_args_list if c[0][0][0] == 'ffmpeg']
        # At least 2 ffmpeg calls: first (arnndn, fails), second (fallback).
        # A third fade-out pass may also run.
        self.assertGreaterEqual(len(ffmpeg_calls), 2)

        # First call should have arnndn (and fail)
        af_index_0 = ffmpeg_calls[0][0][0].index('-af')
        self.assertIn('arnndn', ffmpeg_calls[0][0][0][af_index_0 + 1])

        # Second call (fallback) should not have arnndn
        af_index_1 = ffmpeg_calls[1][0][0].index('-af')
        self.assertNotIn('arnndn', ffmpeg_calls[1][0][0][af_index_1 + 1])


class TestCleanAudioMissingFfmpeg(unittest.TestCase):
    """Tests for graceful failure when ffmpeg is not installed."""

    @patch('utils.denoise.subprocess.run', side_effect=FileNotFoundError)
    def test_returns_false_when_ffmpeg_missing(self, mock_run):
        """Should return False and not crash when ffmpeg is not found."""
        result = clean_audio('/input.wav', '/output.wav')
        self.assertFalse(result)


class TestCleanAudioShortClip(unittest.TestCase):
    """Tests for handling short audio clips."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    def test_short_clip_no_crash(self, mock_run, mock_close, mock_mkstemp, mock_replace):
        """Clips shorter than 0.5s should be processed without error."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '0.3'}})
        mock_run.return_value = probe_result

        result = clean_audio('/input.wav', '/output.wav')
        self.assertTrue(result)


class TestCleanAudioAlreadyClean(unittest.TestCase):
    """Tests for already-clean input files."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    def test_already_clean_succeeds(self, mock_run, mock_close, mock_mkstemp, mock_replace):
        """Already-clean files should pass through without corruption."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '5.0'}})
        mock_run.return_value = probe_result

        result = clean_audio('/input.wav', '/output.wav')
        self.assertTrue(result)


class TestCleanAudioEnvVar(unittest.TestCase):
    """Tests for RNNOISE_MODEL_PATH env var fallback."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    @patch('utils.denoise.os.path.isfile', return_value=True)
    @patch.dict(os.environ, {'RNNOISE_MODEL_PATH': '/env/model.rnnn'})
    def test_uses_env_var(self, mock_isfile, mock_run, mock_close, mock_mkstemp, mock_replace):
        """Should use RNNOISE_MODEL_PATH env var when no explicit path given."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '2.0'}})
        mock_run.return_value = probe_result

        clean_audio('/input.wav', '/output.wav')

        ffmpeg_calls = [c for c in mock_run.call_args_list if c[0][0][0] == 'ffmpeg']
        self.assertTrue(len(ffmpeg_calls) >= 1)

        af_index = ffmpeg_calls[0][0][0].index('-af')
        filter_str = ffmpeg_calls[0][0][0][af_index + 1]
        self.assertIn('arnndn=m=/env/model.rnnn', filter_str)


class TestGenerateSpeechCallsDenoise(unittest.TestCase):
    """Tests that generate_speech() integrates with clean_audio."""

    @patch('utils.denoise.clean_audio')
    @patch('subprocess.run')
    @patch('utils.chatterbox_tts.ta')
    def test_generate_speech_calls_clean_audio(self, mock_ta, mock_subprocess, mock_clean):
        """generate_speech() should call clean_audio on WAV before MP3 conversion."""
        import tempfile
        from utils.chatterbox_tts import ChatterboxVoiceCloner

        cloner = ChatterboxVoiceCloner.__new__(ChatterboxVoiceCloner)
        cloner.device = 'cpu'
        cloner._lock = __import__('threading').Lock()

        mock_model = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_model.sr = 24000
        cloner._model = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.mp3")
            # Create dummy WAV so unlink() succeeds after MP3 conversion
            wav_path = os.path.join(tmpdir, "test.wav")
            open(wav_path, 'w').close()
            cloner.generate_speech("Hello", "/prompt.wav", output_path, language="en")

        mock_clean.assert_called_once()
        call_args = mock_clean.call_args[0]
        self.assertTrue(call_args[0].endswith('.wav'))
        self.assertTrue(call_args[1].endswith('.wav'))


if __name__ == "__main__":
    unittest.main()
