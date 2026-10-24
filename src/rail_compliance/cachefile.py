"""Cache entries: the value plus how long the original call took.

Entries written before latency was recorded are the bare value; they load with 0 seconds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MARK = "_cache"


def read(path: Path) -> tuple[Any, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and MARK in data:
        return data["value"], float(data["seconds"])
    return data, 0.0


def write(path: Path, value: Any, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {MARK: 1, "seconds": round(seconds, 4), "value": value}
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")
