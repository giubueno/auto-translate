"""Configuration: env-var-driven, with optional .env file loading.

Policy: every configurable knob is a SADDLEBACK_<SECTION>_<KEY> environment
variable. There is no TOML or YAML config file. Local development overrides
live in a .env file at the project root (gitignored). The .env.sample file
documents every supported variable with its default value.

Layering (lowest → highest precedence):
  1. Built-in defaults (this module)
  2. Variables already in os.environ
  3. Variables loaded from .env files (only sets keys not already in env)

Note that step 3 NEVER overrides step 2 — a value already exported in the
shell wins over the .env file. This matches the conventional dotenv contract
and lets CI / overrides work without editing the file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TranslatorConfig(BaseModel):
    # Default targets a local LM Studio instance. Operators on a non-loopback
    # host MUST override via SADDLEBACK_TRANSLATOR_ENDPOINT.
    endpoint: str = "http://localhost:1234/v1"
    model: str = "google/gemma-4-e4b"
    api_key: str = "lm-studio"
    temperature: float = 0.2
    max_concurrency: int = 4
    timeout_seconds: float = 60.0


class TranscribeConfig(BaseModel):
    # large-v3-turbo: ~3x faster than large-v3 on CPU int8 with comparable accuracy.
    # Switch to "large-v3" if quality regressions on long-form material show up.
    model: str = "large-v3-turbo"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    beam_size: int = 5


class TtsConfig(BaseModel):
    model: str = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
    sample_rate_out: int = 24000
    ref_min_seconds: float = 3.0
    ref_max_seconds: float = 8.0
    temperature: float = 0.7


class OutputConfig(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["mp4"])
    copy_video: bool = True
    audio_codec: str = "aac"
    audio_bitrate_k: int = 192
    # If set to "wav", "m4a", or "mp3", export an audio-only file next to the
    # source MP4 in addition to the dubbed video (e.g. meeting_de.wav).
    audio_export: str | None = None

    @field_validator("formats", mode="before")
    @classmethod
    def _coerce_formats(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("audio_export", mode="before")
    @classmethod
    def _coerce_audio_export(cls, v: Any) -> Any:
        if v is None or v == "" or v is False:
            return None
        if isinstance(v, str):
            v = v.strip().lower()
            if v in {"", "none", "false", "off", "no"}:
                return None
        return v

    @field_validator("audio_export")
    @classmethod
    def _validate_audio_export(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in {"wav", "m4a", "mp3"}:
            raise ValueError(
                f"unsupported audio_export format {v!r}; expected wav, m4a, or mp3"
            )
        return v


class RuntimeConfig(BaseModel):
    runs_dir: Path = Path("./runs")
    keep_intermediate: bool = True
    parallel_translate: bool = True
    parallel_tts: bool = False
    test_mode: bool = False
    length_budget_ratio: float = 1.3
    similarity_threshold: float = 0.85

    @field_validator("runs_dir", mode="before")
    @classmethod
    def _coerce_runs_dir(cls, v: Any) -> Path:
        return Path(v).expanduser() if not isinstance(v, Path) else v


class TargetsConfig(BaseModel):
    languages: list[str] = Field(default_factory=lambda: ["de", "es"])

    @field_validator("languages", mode="before")
    @classmethod
    def _coerce_languages(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("languages")
    @classmethod
    def _validate_languages(cls, v: list[str]) -> list[str]:
        allowed = {"de", "es"}
        for lang in v:
            if lang not in allowed:
                raise ValueError(f"unsupported language {lang!r}; MVP supports de + es only")
        return v


class Config(BaseModel):
    translator: TranslatorConfig = Field(default_factory=TranslatorConfig)
    transcribe: TranscribeConfig = Field(default_factory=TranscribeConfig)
    tts: TtsConfig = Field(default_factory=TtsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    targets: TargetsConfig = Field(default_factory=TargetsConfig)


_ENV_PREFIX = "SADDLEBACK_"


def _parse_dotenv(text: str) -> dict[str, str]:
    """Parse a .env file's contents into a dict of KEY=VALUE pairs.

    Supports: blank lines, full-line `# ...` comments, KEY=VALUE pairs with
    optional surrounding single or double quotes, and a leading `export `
    keyword (`export FOO=bar`). Does NOT support multiline values, variable
    interpolation, or inline comments (the value runs to end-of-line).
    """
    pairs: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if key:
            pairs[key] = value
    return pairs


def load_dotenv_into_env(path: Path, override: bool = False) -> int:
    """Load `.env`-style file into os.environ. Existing env vars win unless override=True.

    Returns the number of keys set. Missing files are silently ignored.
    """
    if not path.exists():
        return 0
    pairs = _parse_dotenv(path.read_text(encoding="utf-8"))
    n = 0
    for key, value in pairs.items():
        if override or key not in os.environ:
            os.environ[key] = value
            n += 1
    return n


def _from_env() -> dict[str, Any]:
    """Read SADDLEBACK_<SECTION>_<KEY>=value into a nested dict."""
    sections: dict[str, dict[str, Any]] = {}
    for key, value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        rest = key[len(_ENV_PREFIX) :].lower()
        if "_" not in rest:
            continue
        section, _, name = rest.partition("_")
        sections.setdefault(section, {})[name] = _coerce_env(value)
    return sections


def _coerce_env(s: str) -> Any:
    low = s.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def load_config(
    explicit_path: Path | None = None,
    cwd: Path | None = None,
) -> Config:
    """Build Config from defaults + environment + optional .env file.

    Lookup order for the .env file (first match wins):
      1. explicit_path argument (typically from --config CLI flag)
      2. <cwd>/.env
    """
    cwd = cwd or Path.cwd()
    if explicit_path is not None:
        load_dotenv_into_env(explicit_path)
    else:
        load_dotenv_into_env(cwd / ".env")
    return Config.model_validate(_from_env())
