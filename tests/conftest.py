from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def fixture_mp4() -> Path:
    p = REPO_ROOT / "tests" / "fixtures" / "sample.mp4"
    assert p.exists(), f"fixture missing: {p}"
    return p


@pytest.fixture()
def runs_root(tmp_path: Path) -> Path:
    d = tmp_path / "runs"
    d.mkdir()
    return d
