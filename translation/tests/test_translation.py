import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.translation import (
    translate_text,
    detect_backend,
    get_lmstudio_client,
    get_openai_client,
    get_active_backend,
    DEFAULT_LMSTUDIO_BASE_URL,
    DEFAULT_LMSTUDIO_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_GEMINI_MODEL,
)


class TestDetectBackend(unittest.TestCase):
    """Tests for backend auto-detection."""

    def setUp(self):
        """Clear relevant environment variables before each test."""
        self.env_patcher = patch.dict(os.environ, {}, clear=True)
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_default_is_lmstudio(self):
        """Default backend should be lmstudio when no env vars set."""
        result = detect_backend()
        self.assertEqual(result, "lmstudio")

    def test_explicit_backend_lmstudio(self):
        """Explicit TRANSLATION_BACKEND=lmstudio should be respected."""
        with patch.dict(os.environ, {'TRANSLATION_BACKEND': 'lmstudio'}):
            result = detect_backend()
            self.assertEqual(result, "lmstudio")

    def test_explicit_backend_openai(self):
        """Explicit TRANSLATION_BACKEND=openai should be respected."""
        with patch.dict(os.environ, {'TRANSLATION_BACKEND': 'openai'}):
            result = detect_backend()
            self.assertEqual(result, "openai")

    def test_explicit_backend_gemini(self):
        """Explicit TRANSLATION_BACKEND=gemini should be respected."""
        with patch.dict(os.environ, {'TRANSLATION_BACKEND': 'gemini'}):
            result = detect_backend()
            self.assertEqual(result, "gemini")

    def test_explicit_backend_case_insensitive(self):
        """TRANSLATION_BACKEND should be case insensitive."""
        with patch.dict(os.environ, {'TRANSLATION_BACKEND': 'OPENAI'}):
            result = detect_backend()
            self.assertEqual(result, "openai")

    def test_openai_key_selects_openai(self):
        """OPENAI_API_KEY present should select openai backend."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test'}):
            result = detect_backend()
            self.assertEqual(result, "openai")

    def test_gemini_key_selects_gemini(self):
        """GOOGLE_GEMINI_API_KEY present should select gemini backend."""
        with patch.dict(os.environ, {'GOOGLE_GEMINI_API_KEY': 'test-key'}):
            result = detect_backend()
            self.assertEqual(result, "gemini")

    def test_openai_priority_over_gemini(self):
        """OpenAI should have priority over Gemini when both keys present."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'sk-test',
            'GOOGLE_GEMINI_API_KEY': 'test-key'
        }):
            result = detect_backend()
            self.assertEqual(result, "openai")

    def test_explicit_backend_overrides_auto_detection(self):
        """Explicit backend should override auto-detection."""
        with patch.dict(os.environ, {
            'TRANSLATION_BACKEND': 'lmstudio',
            'OPENAI_API_KEY': 'sk-test'
        }):
            result = detect_backend()
            self.assertEqual(result, "lmstudio")


class TestTranslateText(unittest.TestCase):
    """Tests for the translate_text function."""

    def test_empty_string_returns_empty(self):
        """Empty string should return empty without calling API."""
        result = translate_text("")
        self.assertEqual(result, "")

    def test_whitespace_only_returns_empty(self):
        """Whitespace-only string should return empty without calling API."""
        result = translate_text("   ")
        self.assertEqual(result, "")

    def test_newline_only_returns_empty(self):
        """Newline-only string should return empty without calling API."""
        result = translate_text("\n\n")
        self.assertEqual(result, "")


class TestLMStudioBackend(unittest.TestCase):
    """Tests for LM Studio translation backend."""

    def setUp(self):
        """Reset global client state before each test."""
        import utils.translation as translation_module
        translation_module._lmstudio_client = None

    @patch('utils.translation.get_lmstudio_client')
    @patch('utils.translation.detect_backend', return_value='lmstudio')
    def test_translate_with_lmstudio(self, mock_detect, mock_get_client):
        """translate_text should use LM Studio when backend is lmstudio."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hallo Welt"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = translate_text("Hello World", "en", "de")

        self.assertEqual(result, "Hallo Welt")
        mock_client.chat.completions.create.assert_called_once()

    @patch('utils.translation.OpenAI')
    def test_lmstudio_client_uses_default_url(self, mock_openai):
        """LM Studio client should use default base URL."""
        get_lmstudio_client()
        mock_openai.assert_called_once_with(
            base_url=DEFAULT_LMSTUDIO_BASE_URL,
            api_key="lm-studio"
        )

    @patch('utils.translation.OpenAI')
    def test_lmstudio_client_uses_env_url(self, mock_openai):
        """LM Studio client should use LMSTUDIO_BASE_URL env var."""
        with patch.dict(os.environ, {'LMSTUDIO_BASE_URL': 'http://custom:5000/v1'}):
            import utils.translation as translation_module
            translation_module._lmstudio_client = None  # Reset
            get_lmstudio_client()
            mock_openai.assert_called_once_with(
                base_url='http://custom:5000/v1',
                api_key="lm-studio"
            )


class TestOpenAIBackend(unittest.TestCase):
    """Tests for OpenAI translation backend."""

    def setUp(self):
        """Reset global client state before each test."""
        import utils.translation as translation_module
        translation_module._openai_client = None

    @patch('utils.translation.get_openai_client')
    @patch('utils.translation.detect_backend', return_value='openai')
    def test_translate_with_openai(self, mock_detect, mock_get_client):
        """translate_text should use OpenAI when backend is openai."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Bonjour le monde"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = translate_text("Hello World", "en", "fr")

        self.assertEqual(result, "Bonjour le monde")

    @patch('utils.translation.OpenAI')
    def test_openai_client_requires_api_key(self, mock_openai):
        """OpenAI client should raise error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                get_openai_client()
            self.assertIn("OPENAI_API_KEY", str(context.exception))

    @patch('utils.translation.OpenAI')
    def test_openai_client_uses_api_key(self, mock_openai):
        """OpenAI client should use OPENAI_API_KEY env var."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-key'}):
            get_openai_client()
            mock_openai.assert_called_once_with(api_key='sk-test-key')


class TestGeminiBackend(unittest.TestCase):
    """Tests for Google Gemini translation backend."""

    def setUp(self):
        """Reset global client state before each test."""
        import utils.translation as translation_module
        translation_module._gemini_model = None

    @patch('utils.translation.get_gemini_model')
    @patch('utils.translation.detect_backend', return_value='gemini')
    def test_translate_with_gemini(self, mock_detect, mock_get_model):
        """translate_text should use Gemini when backend is gemini."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Ciao mondo"
        mock_model.generate_content.return_value = mock_response
        mock_get_model.return_value = mock_model

        result = translate_text("Hello World", "en", "it")

        self.assertEqual(result, "Ciao mondo")


class TestBackendParameter(unittest.TestCase):
    """Tests for explicit backend parameter."""

    @patch('utils.translation._translate_with_lmstudio')
    def test_explicit_backend_lmstudio(self, mock_translate):
        """Explicit backend='lmstudio' should use LM Studio."""
        mock_translate.return_value = "Test"
        translate_text("Hello", "en", "de", backend="lmstudio")
        mock_translate.assert_called_once()

    @patch('utils.translation._translate_with_openai')
    def test_explicit_backend_openai(self, mock_translate):
        """Explicit backend='openai' should use OpenAI."""
        mock_translate.return_value = "Test"
        translate_text("Hello", "en", "de", backend="openai")
        mock_translate.assert_called_once()

    @patch('utils.translation._translate_with_gemini')
    def test_explicit_backend_gemini(self, mock_translate):
        """Explicit backend='gemini' should use Gemini."""
        mock_translate.return_value = "Test"
        translate_text("Hello", "en", "de", backend="gemini")
        mock_translate.assert_called_once()

    @patch('utils.translation._translate_with_lmstudio')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test'})
    def test_explicit_backend_overrides_env(self, mock_translate):
        """Explicit backend parameter should override env var detection."""
        mock_translate.return_value = "Test"
        # Even with OPENAI_API_KEY set, explicit backend should win
        translate_text("Hello", "en", "de", backend="lmstudio")
        mock_translate.assert_called_once()


class TestGetActiveBackend(unittest.TestCase):
    """Tests for get_active_backend function."""

    def test_returns_detected_backend(self):
        """get_active_backend should return the detected backend."""
        with patch('utils.translation.detect_backend', return_value='openai'):
            from utils.translation import get_active_backend
            result = get_active_backend()
            self.assertEqual(result, "openai")


class TestDefaultValues(unittest.TestCase):
    """Tests for default configuration values."""

    def test_default_lmstudio_base_url(self):
        """Default LM Studio base URL should be localhost:1234."""
        self.assertEqual(DEFAULT_LMSTUDIO_BASE_URL, "http://localhost:1234/v1")

    def test_default_lmstudio_model(self):
        """Default LM Studio model should be qwen/qwen3-vl-8b:2."""
        self.assertEqual(DEFAULT_LMSTUDIO_MODEL, "qwen/qwen3-vl-8b:2")

    def test_default_openai_model(self):
        """Default OpenAI model should be gpt-4o-mini."""
        self.assertEqual(DEFAULT_OPENAI_MODEL, "gpt-4o-mini")

    def test_default_gemini_model(self):
        """Default Gemini model should be gemini-2.0-flash."""
        self.assertEqual(DEFAULT_GEMINI_MODEL, "gemini-2.0-flash")


class TestLegacyCompatibility(unittest.TestCase):
    """Tests for backwards compatibility."""

    def test_legacy_get_client_alias(self):
        """get_client should be an alias for get_lmstudio_client."""
        from utils.translation import get_client, get_lmstudio_client
        self.assertIs(get_client, get_lmstudio_client)

    def test_legacy_default_base_url(self):
        """DEFAULT_BASE_URL should be an alias for DEFAULT_LMSTUDIO_BASE_URL."""
        from utils.translation import DEFAULT_BASE_URL, DEFAULT_LMSTUDIO_BASE_URL
        self.assertEqual(DEFAULT_BASE_URL, DEFAULT_LMSTUDIO_BASE_URL)

    def test_legacy_default_model(self):
        """DEFAULT_MODEL should be an alias for DEFAULT_LMSTUDIO_MODEL."""
        from utils.translation import DEFAULT_MODEL, DEFAULT_LMSTUDIO_MODEL
        self.assertEqual(DEFAULT_MODEL, DEFAULT_LMSTUDIO_MODEL)


class TestIntegration(unittest.TestCase):
    """Integration tests (require actual services running)."""

    @unittest.skipUnless(
        os.environ.get('RUN_INTEGRATION_TESTS') == '1',
        "Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable."
    )
    def test_real_translation(self):
        """Test actual translation with detected backend."""
        backend = detect_backend()
        print(f"\nUsing backend: {backend}")
        result = translate_text("Hello, how are you?", "en", "es")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        print(f"Translation result: {result}")


if __name__ == "__main__":
    unittest.main()
