import os
from openai import OpenAI

# =============================================================================
# Translation Backend Configuration
# =============================================================================
# Supported backends: "lmstudio", "openai", "gemini"
# Auto-detection priority: TRANSLATION_BACKEND env var > OpenAI > Gemini > LM Studio

# LM Studio defaults
DEFAULT_LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
DEFAULT_LMSTUDIO_MODEL = "qwen/qwen3-vl-8b:2"

# OpenAI defaults
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

# Gemini defaults
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

# Global clients (lazy initialized)
_lmstudio_client = None
_openai_client = None
_gemini_model = None


def detect_backend():
    """
    Detect which translation backend to use based on environment variables.

    Priority:
    1. TRANSLATION_BACKEND env var (explicit choice)
    2. OPENAI_API_KEY present -> openai
    3. GOOGLE_GEMINI_API_KEY present -> gemini
    4. Default -> lmstudio (local, no API key needed)

    :return: Backend name ("lmstudio", "openai", or "gemini")
    """
    # Check for explicit backend choice
    explicit_backend = os.getenv("TRANSLATION_BACKEND", "").lower()
    if explicit_backend in ("lmstudio", "openai", "gemini"):
        return explicit_backend

    # Auto-detect based on available API keys
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GOOGLE_GEMINI_API_KEY"):
        return "gemini"

    # Default to LM Studio (local, no API key required)
    return "lmstudio"


def get_lmstudio_client(base_url=None):
    """
    Get or create an OpenAI client configured for LM Studio.

    :param base_url: LM Studio API base URL
    :return: OpenAI client instance
    """
    global _lmstudio_client

    base_url = base_url or os.getenv("LMSTUDIO_BASE_URL", DEFAULT_LMSTUDIO_BASE_URL)

    if _lmstudio_client is None:
        _lmstudio_client = OpenAI(
            base_url=base_url,
            api_key="lm-studio"  # LM Studio doesn't require a real API key
        )

    return _lmstudio_client


def get_openai_client():
    """
    Get or create an OpenAI client.

    :return: OpenAI client instance
    """
    global _openai_client

    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _openai_client = OpenAI(api_key=api_key)

    return _openai_client


def get_gemini_model():
    """
    Get or create a Gemini model instance.

    :return: Gemini GenerativeModel instance
    """
    global _gemini_model

    if _gemini_model is None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        _gemini_model = genai.GenerativeModel(model_name)

    return _gemini_model


def _translate_with_lmstudio(text, source_language, target_language, model=None, base_url=None):
    """Translate using LM Studio local API."""
    client = get_lmstudio_client(base_url)
    model = model or os.getenv("LMSTUDIO_MODEL", DEFAULT_LMSTUDIO_MODEL)

    prompt = f"Translate the following text from {source_language} to {target_language}. Only return the translated text, nothing else: {text}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional translator. Translate the given text accurately while preserving the original meaning and tone. Only output the translation, no explanations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


def _translate_with_openai(text, source_language, target_language, model=None):
    """Translate using OpenAI API."""
    client = get_openai_client()
    model = model or os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

    prompt = f"Translate the following text from {source_language} to {target_language}. Only return the translated text, nothing else: {text}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional translator. Translate the given text accurately while preserving the original meaning and tone. Only output the translation, no explanations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


def _translate_with_gemini(text, source_language, target_language):
    """Translate using Google Gemini API."""
    model = get_gemini_model()

    prompt = f"""You are a professional translator. Translate the following text from {source_language} to {target_language}.
Only return the translated text, nothing else. No explanations, no quotes, just the translation.

Text to translate: {text}"""

    response = model.generate_content(prompt)
    return response.text.strip()


def translate_text(text, source_language='en', target_language='es', model=None, base_url=None, backend=None):
    """
    Translate text from source language to target language.

    Automatically selects the translation backend based on available environment variables,
    or uses the explicitly specified backend.

    Backend selection priority:
    1. backend parameter (if provided)
    2. TRANSLATION_BACKEND env var
    3. OPENAI_API_KEY present -> OpenAI
    4. GOOGLE_GEMINI_API_KEY present -> Gemini
    5. Default -> LM Studio (local)

    :param text: Text to translate
    :param source_language: Source language code (e.g., 'en' for English)
    :param target_language: Target language code (e.g., 'es' for Spanish)
    :param model: Model to use (backend-specific, uses defaults if not provided)
    :param base_url: LM Studio API base URL (only used for lmstudio backend)
    :param backend: Force specific backend ("lmstudio", "openai", or "gemini")
    :return: Translated text
    """
    if text == "" or text.strip() == "":
        return ""

    # Determine which backend to use
    selected_backend = backend or detect_backend()

    if selected_backend == "openai":
        return _translate_with_openai(text, source_language, target_language, model)
    elif selected_backend == "gemini":
        return _translate_with_gemini(text, source_language, target_language)
    else:  # lmstudio (default)
        return _translate_with_lmstudio(text, source_language, target_language, model, base_url)


def get_active_backend():
    """
    Get the name of the currently active translation backend.

    :return: Backend name ("lmstudio", "openai", or "gemini")
    """
    return detect_backend()


# Legacy aliases for backwards compatibility
get_client = get_lmstudio_client
DEFAULT_BASE_URL = DEFAULT_LMSTUDIO_BASE_URL
DEFAULT_MODEL = DEFAULT_LMSTUDIO_MODEL
