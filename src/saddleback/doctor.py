from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from rich.console import Console
from rich.table import Table

from saddleback.config import Config, load_config
from saddleback.exit_codes import ExitCode

PYTHON_REQUIRED = (3, 14)


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    remediation: str = ""


def _check_python() -> CheckResult:
    actual = sys.version_info[:2]
    if actual == PYTHON_REQUIRED:
        return CheckResult("python", True, f"{sys.version.split()[0]}")
    return CheckResult(
        "python",
        False,
        f"running {sys.version.split()[0]}, need {'.'.join(map(str, PYTHON_REQUIRED))}.x",
        f"install Python {'.'.join(map(str, PYTHON_REQUIRED))}.x and recreate venv: "
        f"python3.14 -m venv venv && ./venv/bin/pip install -e .",
    )


def _check_ffmpeg() -> CheckResult:
    path = shutil.which("ffmpeg")
    if path is None:
        return CheckResult(
            "ffmpeg",
            False,
            "not found in PATH",
            "install via Homebrew: brew install ffmpeg",
        )
    return CheckResult("ffmpeg", True, path)


def _check_lm_studio(cfg: Config) -> CheckResult:
    endpoint = cfg.translator.endpoint.rstrip("/")
    url = f"{endpoint}/models"
    try:
        req = Request(url, headers={"Authorization": f"Bearer {cfg.translator.api_key}"})
        with urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                return CheckResult(
                    "lm_studio",
                    False,
                    f"GET {url} → {resp.status}",
                    f"verify LM Studio is running and reachable at {endpoint}",
                )
            body = resp.read().decode("utf-8", errors="replace")
            if cfg.translator.model in body:
                return CheckResult("lm_studio", True, f"{endpoint} ✓ model {cfg.translator.model} available")
            return CheckResult(
                "lm_studio",
                False,
                f"endpoint reachable but model {cfg.translator.model!r} not loaded",
                f"in LM Studio, load model {cfg.translator.model!r} or set "
                f"SADDLEBACK_TRANSLATOR_MODEL=<available-model>",
            )
    except URLError as exc:
        return CheckResult(
            "lm_studio",
            False,
            f"GET {url} failed: {exc.reason}",
            f"verify LM Studio is running and reachable at {endpoint}; "
            f"test with: curl {endpoint}/models",
        )
    except Exception as exc:
        return CheckResult(
            "lm_studio",
            False,
            f"unexpected error: {exc}",
            f"verify LM Studio is running and reachable at {endpoint}",
        )


def _check_tts_model(cfg: Config) -> CheckResult:
    cache_root = Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"
    model_dir = cache_root / f"models--{cfg.tts.model.replace('/', '--')}"
    if model_dir.exists():
        return CheckResult("tts_model", True, f"cached at {model_dir}")
    return CheckResult(
        "tts_model",
        False,
        f"not cached at {model_dir}",
        f"first run of `saddleback dub` will download {cfg.tts.model} (~2 GB). "
        f"or pre-download: huggingface-cli download {cfg.tts.model}",
    )


def _check_runs_dir(cfg: Config) -> CheckResult:
    runs_dir = cfg.runtime.runs_dir
    try:
        runs_dir.mkdir(parents=True, exist_ok=True)
        probe = runs_dir / ".saddleback-doctor-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return CheckResult("runs_dir", True, str(runs_dir.resolve()))
    except OSError as exc:
        return CheckResult(
            "runs_dir",
            False,
            f"cannot write to {runs_dir}: {exc}",
            f"choose a writable runs_dir via config or set SADDLEBACK_RUNTIME_RUNS_DIR",
        )


def run_doctor(opts: dict[str, Any]) -> ExitCode:
    cfg = load_config(explicit_path=opts.get("config_path"))
    console = Console(no_color="NO_COLOR" in os.environ)

    checks = [
        _check_python(),
        _check_ffmpeg(),
        _check_runs_dir(cfg),
        _check_lm_studio(cfg),
        _check_tts_model(cfg),
    ]

    if opts.get("json"):
        import json

        for c in checks:
            print(
                json.dumps(
                    {
                        "check": c.name,
                        "ok": c.ok,
                        "detail": c.detail,
                        "remediation": c.remediation,
                    }
                )
            )
    else:
        table = Table(title="saddleback doctor", show_lines=False)
        table.add_column("check")
        table.add_column("status")
        table.add_column("detail")
        for c in checks:
            status = "[green]OK[/]" if c.ok else "[red]FAIL[/]"
            table.add_row(c.name, status, c.detail)
        console.print(table)
        for c in checks:
            if not c.ok and c.remediation:
                console.print(f"[yellow]{c.name}[/]: {c.remediation}")

    return ExitCode.OK if all(c.ok for c in checks) else ExitCode.PREFLIGHT_FAILED
