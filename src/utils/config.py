"""YAML configuration loading with simple file inheritance."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path) -> dict[str, Any]:
    """Load YAML and recursively merge an optional ``extends`` parent file."""
    resolved_path = path.resolve()
    with resolved_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration root must be a mapping: {resolved_path}")

    parent_name = loaded.pop("extends", None)
    if parent_name is None:
        return loaded
    parent_path = (resolved_path.parent / str(parent_name)).resolve()
    if parent_path == resolved_path:
        raise ValueError(f"Configuration cannot extend itself: {resolved_path}")
    return _deep_merge(load_config(parent_path), loaded)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged

