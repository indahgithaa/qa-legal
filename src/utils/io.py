"""Small, dependency-free JSONL helpers."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield JSON objects from a UTF-8 JSONL file.

    Blank lines are ignored. Invalid JSON errors include their source line.
    """
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path} at line {line_number}: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"Expected a JSON object in {path} at line {line_number}")
            yield value


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    """Atomically write records as UTF-8 JSONL and return their count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    count = 0
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
            for record in records:
                file.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
                count += 1
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return count

