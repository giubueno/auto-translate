from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path


def make_run_id(source: Path) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{source.stem}-{stamp}"


def find_run_dir(runs_root: Path, run_id: str | None) -> Path | None:
    if run_id is not None:
        candidate = runs_root / run_id
        return candidate if candidate.exists() else None
    if not runs_root.exists():
        return None
    candidates = sorted([p for p in runs_root.iterdir() if p.is_dir()], reverse=True)
    return candidates[0] if candidates else None


def existing_run_dir_for_source(runs_root: Path, source: Path) -> Path | None:
    """Find the most recent run dir whose run-id starts with the source stem."""
    if not runs_root.exists():
        return None
    prefix = f"{source.stem}-"
    matching = sorted(
        (p for p in runs_root.iterdir() if p.is_dir() and p.name.startswith(prefix)),
        reverse=True,
    )
    return matching[0] if matching else None


def file_hash(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()
