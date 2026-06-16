"""Shared domain utilities for Novel Studio."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


def dump_json(value: object) -> str:
    """Compact JSON serialization used for stored columns."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load_json(value: str | None) -> Any:
    """Deserialize JSON, returning an empty dict on empty/malformed input."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        logger.warning("json_decode_failed value=%s error=%s", value, str(exc))
        return {}


def new_id() -> str:
    """Generate a new opaque UUID string."""
    return str(uuid4())


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _word_count(markdown: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", markdown, flags=re.UNICODE))
