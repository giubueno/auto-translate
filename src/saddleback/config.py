from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TranslatorConfig(BaseModel):
    endpoint: str = "http://192.168.0.42:1234/v1"
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


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


_ENV_PREFIX = "SADDLEBACK_"


def _from_env() -> dict[str, Any]:
    """Read SADDLEBACK_<SECTION>_<KEY>=value into nested dict."""
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
    """Layered: defaults → ~/.config/saddleback/config.toml → ./saddleback.toml → env → explicit_path."""
    cwd = cwd or Path.cwd()
    user_config = Path.home() / ".config" / "saddleback" / "config.toml"
    project_config = cwd / "saddleback.toml"

    merged: dict[str, Any] = {}
    for layer in (user_config, project_config):
        merged = _deep_merge(merged, _load_toml(layer))
    merged = _deep_merge(merged, _from_env())
    if explicit_path is not None:
        merged = _deep_merge(merged, _load_toml(explicit_path))

    return Config.model_validate(merged)
