from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Segment(BaseModel):
    id: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class Translation(BaseModel):
    segment_id: int
    lang: str
    text: str
    overflow: bool = False
    attempts: int = 1


class StageStatus(BaseModel):
    name: str
    started_at: str | None = None
    finished_at: str | None = None
    ok: bool | None = None
    detail: str = ""
    artifact_paths: list[str] = Field(default_factory=list)


class Manifest(BaseModel):
    version: int = 1
    run_id: str
    source_path: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    targets: list[str]
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    stages: dict[str, StageStatus] = Field(default_factory=dict)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, obj: Any) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(obj, "model_dump"):
        data = obj.model_dump()
    else:
        data = obj
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def read_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
