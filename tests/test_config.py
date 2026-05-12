from __future__ import annotations

import os
from pathlib import Path

from saddleback.config import Config, load_config


def test_defaults_match_prd():
    cfg = Config()
    assert cfg.translator.endpoint == "http://192.168.0.77:1234/v1"
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


def test_project_config_overrides_user_config(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SADDLEBACK_TRANSLATOR_ENDPOINT", raising=False)
    project_toml = tmp_path / "saddleback.toml"
    project_toml.write_text(
        '[translator]\nmodel = "google/gemma-4-31b"\n',
        encoding="utf-8",
    )
    cfg = load_config(cwd=tmp_path)
    assert cfg.translator.model == "google/gemma-4-31b"


def test_unsupported_language_rejected():
    import pytest

    from pydantic import ValidationError
    from saddleback.config import TargetsConfig

    with pytest.raises(ValidationError):
        TargetsConfig(languages=["fr"])
