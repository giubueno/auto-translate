from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from saddleback.config import Config, TargetsConfig, load_config


def test_defaults_match_prd():
    cfg = Config()
    assert cfg.translator.endpoint == "http://localhost:1234/v1"
    assert cfg.translator.model == "google/gemma-4-e4b"
    assert cfg.tts.model == "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
    assert cfg.targets.languages == ["de", "es"]
    assert cfg.runtime.parallel_tts is False  # NFR-RC3


def test_env_overrides(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SADDLEBACK_TRANSLATOR_ENDPOINT", "http://example.local:9999/v1")
    monkeypatch.setenv("SADDLEBACK_RUNTIME_TEST_MODE", "true")
    cfg = load_config(cwd=tmp_path)
    assert cfg.translator.endpoint == "http://example.local:9999/v1"
    assert cfg.runtime.test_mode is True


def test_dotenv_loaded_from_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SADDLEBACK_TRANSLATOR_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "SADDLEBACK_TRANSLATOR_MODEL=google/gemma-4-31b\n",
        encoding="utf-8",
    )
    cfg = load_config(cwd=tmp_path)
    assert cfg.translator.model == "google/gemma-4-31b"


def test_shell_env_wins_over_dotenv(tmp_path: Path, monkeypatch):
    """A value already exported in the shell takes precedence over .env."""
    monkeypatch.setenv("SADDLEBACK_TRANSLATOR_MODEL", "shell-wins")
    (tmp_path / ".env").write_text(
        "SADDLEBACK_TRANSLATOR_MODEL=dotenv-loses\n",
        encoding="utf-8",
    )
    cfg = load_config(cwd=tmp_path)
    assert cfg.translator.model == "shell-wins"


def test_explicit_dotenv_path(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SADDLEBACK_TRANSLATOR_MODEL", raising=False)
    explicit = tmp_path / "custom.env"
    explicit.write_text(
        '# comment line\nexport SADDLEBACK_TRANSLATOR_MODEL="quoted-model-name"\n',
        encoding="utf-8",
    )
    cfg = load_config(explicit_path=explicit, cwd=tmp_path)
    assert cfg.translator.model == "quoted-model-name"


def test_targets_languages_csv_string(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("SADDLEBACK_TARGETS_LANGUAGES", "de, es")
    cfg = load_config(cwd=tmp_path)
    assert cfg.targets.languages == ["de", "es"]


def test_unsupported_language_rejected():
    with pytest.raises(ValidationError):
        TargetsConfig(languages=["fr"])
