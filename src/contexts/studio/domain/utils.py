"""Shared domain utilities for Novel Studio."""

from __future__ import annotations

import hashlib
import hmac
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
    """Deserialize JSON.

    Returns an empty dict for empty input. Raises ``ValueError`` for malformed
    JSON so callers must decide how to handle corrupt stored data.
    """
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON: {exc}") from exc


def new_id() -> str:
    """Generate a new opaque UUID string."""
    return str(uuid4())


def _token_hash(token: str, secret_key: str) -> str:
    """Derive a session lookup digest with the deployment secret.

    Session tokens are bearer credentials.  Keying their database digest with
    the deployment secret prevents an attacker with a database-only copy from
    validating guesses offline, and rotating the secret invalidates all
    existing sessions by design.
    """
    return hmac.new(
        secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _word_count(markdown: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", markdown, flags=re.UNICODE))
