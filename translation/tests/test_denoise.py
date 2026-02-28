import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import json
import subprocess
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.denoise import (
    clean_chatterbox_audio,
    clean_audio,
    AudioCleaner,
    AudioInputPath,
    AudioOutputPath,
    DenoiseResult,
    _build_filter_chain,
    _get_duration,
    _is_wav,
    _convert_to_wav,
)


class TestPydanticModels(unittest.TestCase):
    """Tests for pydantic path validation models."""

    def test_audio_input_path_valid(self):
        """AudioInputPath should accept existing files."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            tmp_path = f.name
        try:
            model = AudioInputPath(path=tmp_path)
            self.assertEqual(model.path, tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_audio_input_path_missing_file(self):
        """AudioInputPath should reject non-existent files."""
        with self.assertRaises(Exception):
            AudioInputPath(path="/nonexistent/file.wav")

    def test_audio_output_path_valid(self):
        """AudioOutputPath should accept paths with existing parent dirs."""
        model = AudioOutputPath(path="/tmp/output.wav")
        self.assertEqual(model.path, "/tmp/output.wav")

    def test_audio_output_path_missing_parent(self):
        """AudioOutputPath should reject paths with non-existent parent dirs."""
        with self.assertRaises(Exception):
            AudioOutputPath(path="/nonexistent/dir/output.wav")

    def test_denoise_result_model(self):
        """DenoiseResult should store all fields correctly."""
        result = DenoiseResult(
            success=True,
            input_path="/input.wav",
            output_path="/output.wav",
            input_duration=5.0,
            output_duration=4.2,
            duration_saved=0.8
        )
        self.assertTrue(result.success)
        self.assertEqual(result.duration_saved, 0.8)
        self.assertIsNone(result.error)

    def test_denoise_result_with_error(self):
        """DenoiseResult should store error messages."""
        result = DenoiseResult(
            success=False,
            input_path="/input.wav",
            output_path="/output.wav",
            error="ffmpeg not found"
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "ffmpeg not found")


class TestIsWav(unittest.TestCase):
    """Tests for WAV file detection."""

    def test_wav_extension(self):
        self.assertTrue(_is_wav("file.wav"))

    def test_wav_uppercase(self):
        self.assertTrue(_is_wav("file.WAV"))

    def test_mp3_extension(self):
        self.assertFalse(_is_wav("file.mp3"))

    def test_flac_extension(self):
        self.assertFalse(_is_wav("file.flac"))

    def test_no_extension(self):
        self.assertFalse(_is_wav("file"))


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


class TestConvertToWav(unittest.TestCase):
    """Tests for non-WAV to WAV conversion."""

    @patch('utils.denoise.subprocess.run')
    def test_successful_conversion(self, mock_run):
        """Should return temp WAV path on successful conversion."""
        mock_run.return_value = MagicMock()
        result = _convert_to_wav("/input.mp3")
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('.wav'))
        # Clean up temp file
        if result and os.path.exists(result):
            os.unlink(result)

    @patch('utils.denoise.subprocess.run', side_effect=FileNotFoundError)
    def test_ffmpeg_not_found(self, mock_run):
        """Should return None when ffmpeg is not installed."""
        result = _convert_to_wav("/input.mp3")
        self.assertIsNone(result)

    @patch('utils.denoise.subprocess.run',
           side_effect=subprocess.CalledProcessError(1, 'ffmpeg'))
    def test_conversion_failure(self, mock_run):
        """Should return None when ffmpeg conversion fails."""
        result = _convert_to_wav("/input.mp3")
        self.assertIsNone(result)


class TestCleanChatterboxAudioName(unittest.TestCase):
    """Tests for function naming and backward compatibility."""

    def test_clean_audio_is_alias(self):
        """clean_audio should be an alias for clean_chatterbox_audio."""
        self.assertIs(clean_audio, clean_chatterbox_audio)

    def test_function_has_type_hints(self):
        """clean_chatterbox_audio should have type annotations."""
        annotations = clean_chatterbox_audio.__annotations__
        self.assertIn('input_path', annotations)
        self.assertIn('output_path', annotations)
        self.assertIn('return', annotations)


class TestCleanChatterboxAudioCommand(unittest.TestCase):
    """Tests for correct ffmpeg command construction."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    @patch('utils.denoise.os.path.isfile', return_value=True)
    def test_ffmpeg_called_with_correct_args(self, mock_isfile, mock_run,
                                              mock_close, mock_mkstemp, mock_replace):
        """ffmpeg should be called with the constructed filter chain."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '3.5'}})
        mock_run.return_value = probe_result

        clean_chatterbox_audio('/input.wav', '/output.wav',
                               rnnoise_model_path='/model.rnnn')

        ffmpeg_calls = [c for c in mock_run.call_args_list
                        if c[0][0][0] == 'ffmpeg']
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


class TestCleanChatterboxAudioNonWav(unittest.TestCase):
    """Tests for non-WAV input handling."""

    @patch('utils.denoise._process_audio', return_value=True)
    @patch('utils.denoise._convert_to_wav')
    def test_mp3_input_converts_to_wav(self, mock_convert, mock_process):
        """MP3 inputs should be converted to WAV before processing."""
        mock_convert.return_value = '/tmp/converted.wav'

        result = clean_chatterbox_audio('/input.mp3', '/output.wav')

        mock_convert.assert_called_once_with('/input.mp3')
        mock_process.assert_called_once_with('/tmp/converted.wav', '/output.wav', None)
        self.assertTrue(result)

    @patch('utils.denoise._convert_to_wav', return_value=None)
    def test_conversion_failure_returns_false(self, mock_convert):
        """Should return False if non-WAV conversion fails."""
        result = clean_chatterbox_audio('/input.flac', '/output.wav')
        self.assertFalse(result)

    @patch('utils.denoise._process_audio', return_value=True)
    def test_wav_input_skips_conversion(self, mock_process):
        """WAV inputs should skip the conversion step."""
        with patch('utils.denoise._convert_to_wav') as mock_convert:
            clean_chatterbox_audio('/input.wav', '/output.wav')
            mock_convert.assert_not_called()


class TestCleanChatterboxAudioNoRNNoise(unittest.TestCase):
    """Tests for fallback when RNNoise model is missing."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    def test_fallback_without_model(self, mock_run, mock_close,
                                     mock_mkstemp, mock_replace):
        """Should use silence trim + fade only when no model path given."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '2.0'}})
        mock_run.return_value = probe_result

        clean_chatterbox_audio('/input.wav', '/output.wav',
                               rnnoise_model_path=None)

        ffmpeg_calls = [c for c in mock_run.call_args_list
                        if c[0][0][0] == 'ffmpeg']
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
    def test_arnndn_failure_retries_without(self, mock_isfile, mock_run,
                                             mock_close, mock_mkstemp,
                                             mock_replace, mock_cleanup):
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

        result = clean_chatterbox_audio('/input.wav', '/output.wav',
                                        rnnoise_model_path='/model.rnnn')

        self.assertTrue(result)
        ffmpeg_calls = [c for c in mock_run.call_args_list
                        if c[0][0][0] == 'ffmpeg']
        self.assertGreaterEqual(len(ffmpeg_calls), 2)

        af_index_0 = ffmpeg_calls[0][0][0].index('-af')
        self.assertIn('arnndn', ffmpeg_calls[0][0][0][af_index_0 + 1])

        af_index_1 = ffmpeg_calls[1][0][0].index('-af')
        self.assertNotIn('arnndn', ffmpeg_calls[1][0][0][af_index_1 + 1])


class TestCleanChatterboxAudioMissingFfmpeg(unittest.TestCase):
    """Tests for graceful failure when ffmpeg is not installed."""

    @patch('utils.denoise.subprocess.run', side_effect=FileNotFoundError)
    def test_returns_false_when_ffmpeg_missing(self, mock_run):
        """Should return False and not crash when ffmpeg is not found."""
        result = clean_chatterbox_audio('/input.wav', '/output.wav')
        self.assertFalse(result)


class TestCleanChatterboxAudioShortClip(unittest.TestCase):
    """Tests for handling short audio clips (<500ms)."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    def test_short_clip_no_crash(self, mock_run, mock_close,
                                  mock_mkstemp, mock_replace):
        """Clips shorter than 0.5s should be processed without error."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '0.3'}})
        mock_run.return_value = probe_result

        result = clean_chatterbox_audio('/input.wav', '/output.wav')
        self.assertTrue(result)

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    def test_very_short_clip(self, mock_run, mock_close,
                              mock_mkstemp, mock_replace):
        """Clips under 30ms should still process (fade start = 0)."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '0.02'}})
        mock_run.return_value = probe_result

        result = clean_chatterbox_audio('/input.wav', '/output.wav')
        self.assertTrue(result)


class TestCleanChatterboxAudioAlreadyClean(unittest.TestCase):
    """Tests for already-clean input files."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    def test_already_clean_succeeds(self, mock_run, mock_close,
                                     mock_mkstemp, mock_replace):
        """Already-clean files should pass through without corruption."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '5.0'}})
        mock_run.return_value = probe_result

        result = clean_chatterbox_audio('/input.wav', '/output.wav')
        self.assertTrue(result)


class TestCleanChatterboxAudioEnvVar(unittest.TestCase):
    """Tests for RNNOISE_MODEL_PATH env var fallback."""

    @patch('utils.denoise.os.replace')
    @patch('utils.denoise.tempfile.mkstemp')
    @patch('utils.denoise.os.close')
    @patch('utils.denoise.subprocess.run')
    @patch('utils.denoise.os.path.isfile', return_value=True)
    @patch.dict(os.environ, {'RNNOISE_MODEL_PATH': '/env/model.rnnn'})
    def test_uses_env_var(self, mock_isfile, mock_run, mock_close,
                           mock_mkstemp, mock_replace):
        """Should use RNNOISE_MODEL_PATH env var when no explicit path given."""
        mock_mkstemp.return_value = (5, '/tmp/test.wav')

        probe_result = MagicMock()
        probe_result.stdout = json.dumps({'format': {'duration': '2.0'}})
        mock_run.return_value = probe_result

        clean_chatterbox_audio('/input.wav', '/output.wav')

        ffmpeg_calls = [c for c in mock_run.call_args_list
                        if c[0][0][0] == 'ffmpeg']
        self.assertTrue(len(ffmpeg_calls) >= 1)

        af_index = ffmpeg_calls[0][0][0].index('-af')
        filter_str = ffmpeg_calls[0][0][0][af_index + 1]
        self.assertIn('arnndn=m=/env/model.rnnn', filter_str)


class TestAudioCleaner(unittest.TestCase):
    """Tests for AudioCleaner class wrapper."""

    def test_init_with_model_path(self):
        """AudioCleaner should store model path."""
        cleaner = AudioCleaner(rnnoise_model_path="/path/to/model.rnnn")
        self.assertEqual(cleaner.rnnoise_model_path, "/path/to/model.rnnn")

    @patch.dict(os.environ, {'RNNOISE_MODEL_PATH': '/env/model.rnnn'})
    def test_init_from_env_var(self):
        """AudioCleaner should fall back to env var."""
        cleaner = AudioCleaner()
        self.assertEqual(cleaner.rnnoise_model_path, "/env/model.rnnn")

    @patch('utils.denoise.clean_chatterbox_audio', return_value=True)
    @patch('utils.denoise._get_duration')
    def test_clean_returns_denoise_result(self, mock_duration, mock_clean):
        """clean() should return a DenoiseResult."""
        mock_duration.return_value = 4.2

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            tmp_path = f.name
        try:
            result = AudioCleaner().clean(tmp_path, "/tmp/output.wav")
            self.assertIsInstance(result, DenoiseResult)
            self.assertTrue(result.success)
            self.assertEqual(result.input_path, tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_clean_invalid_input(self):
        """clean() with invalid input should return failed DenoiseResult."""
        cleaner = AudioCleaner()
        result = cleaner.clean("/nonexistent/file.wav", "/tmp/output.wav")
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    @patch('utils.denoise.clean_chatterbox_audio', return_value=True)
    @patch('utils.denoise._get_duration', return_value=4.0)
    @patch('utils.denoise.glob_module.glob')
    def test_clean_multiple(self, mock_glob, mock_duration, mock_clean):
        """clean_multiple() should process all matched files."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f2:
            tmp1, tmp2 = f1.name, f2.name

        try:
            mock_glob.return_value = [tmp1, tmp2]
            cleaner = AudioCleaner()
            results = cleaner.clean_multiple("*.wav")

            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.success for r in results))
        finally:
            os.unlink(tmp1)
            os.unlink(tmp2)

    @patch('utils.denoise.glob_module.glob', return_value=[])
    def test_clean_multiple_no_matches(self, mock_glob):
        """clean_multiple() with no matches should return empty list."""
        cleaner = AudioCleaner()
        results = cleaner.clean_multiple("nonexistent/*.wav")
        self.assertEqual(results, [])


class TestGenerateSpeechCallsDenoise(unittest.TestCase):
    """Tests that generate_speech() integrates with clean_audio."""

    @patch('utils.denoise.clean_audio')
    @patch('subprocess.run')
    @patch('utils.chatterbox_tts.ta')
    def test_generate_speech_calls_clean_audio(self, mock_ta, mock_subprocess,
                                                mock_clean):
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
            wav_path = os.path.join(tmpdir, "test.wav")
            open(wav_path, 'w').close()
            cloner.generate_speech("Hello", "/prompt.wav", output_path,
                                   language="en")

        mock_clean.assert_called_once()
        call_args = mock_clean.call_args[0]
        self.assertTrue(call_args[0].endswith('.wav'))
        self.assertTrue(call_args[1].endswith('.wav'))


if __name__ == "__main__":
    unittest.main()
