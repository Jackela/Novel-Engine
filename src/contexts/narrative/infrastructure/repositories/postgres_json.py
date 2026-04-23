"""Helpers for JSON payload handling in PostgreSQL repositories."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


def dump_json(value: Any) -> str:
    """Serialize a Python value to a JSON string."""
    return json.dumps(value, ensure_ascii=True)


def load_json_object(value: Any) -> dict[str, Any]:
    """Normalize a database JSON value into a Python mapping."""
    if value is None:
        return {}

    if isinstance(value, str):
        if not value.strip():
            return {}
        value = json.loads(value)

    if isinstance(value, Mapping):
        return dict(value)

    return dict(value) if isinstance(value, Sequence) else {}


def load_json_array(value: Any) -> list[Any]:
    """Normalize a database JSON value into a Python list."""
    if value is None:
        return []

    if isinstance(value, str):
        if not value.strip():
            return []
        value = json.loads(value)

    if isinstance(value, list):
        return list(value)

    if isinstance(value, tuple):
        return list(value)

    return list(value) if isinstance(value, Sequence) else []
