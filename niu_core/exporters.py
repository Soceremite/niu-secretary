"""Export helpers for JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path


def write_json(path: str | Path, payload: dict | list, *, indent: int = 2) -> dict:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent) + "\n",
        encoding="utf-8",
    )
    return {"path": str(target), "bytes": target.stat().st_size}


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
