"""Transactional application services for Novel Studio.

The application layer now depends only on the ``StudioRepository`` port and
small injected callables. All SQLAlchemy/model details are encapsulated by the
infrastructure implementation.
"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar, cast

import bcrypt
import yaml

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
    TextGenerationProviderName,
)
from src.contexts.studio.application.ports import (
    DocumentDto,
    ExportDto,
    JobDto,
    ProjectDto,
    ReviewDto,
    RevisionDto,
    SnapshotDto,
    StudioRepository,
    TextGenerationProviderFactory,
)
from src.contexts.studio.application.service_payloads import (
    _document_payload,
    _export_payload,
    _job_payload,
    _project_payload,
    _review_payload,
    _revision_payload,
    _safe_load_json,
    _snapshot_payload,
    iso,
)
from src.contexts.studio.domain.exceptions import (
    InvalidOperation,
    NotFound,
    RevisionConflict,
)
from src.contexts.studio.domain.principal import Principal
from src.contexts.studio.domain.types import DOCUMENT_KINDS, DocumentKind, ExportFormat
from src.contexts.studio.domain.utils import (
    _token_hash,
    _word_count,
    dump_json,
    load_json,
    new_id,
    utcnow,
)

GUEST_TTL = timedelta(hours=24)
SESSION_COOKIE = "novel_studio_session"
CSRF_COOKIE = "novel_studio_csrf"

# Constant dummy bcrypt hash used to keep login timing constant regardless of
# whether the supplied username exists. A fresh salt is generated at import
# time so no hardcoded password literal lives in source control.
_DUMMY_HASH = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt())

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _plain_text(markdown: str) -> str:
    text_value = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text_value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text_value)
    text_value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text_value)
    text_value = re.sub(r"^[#>*+-]+\s*", "", text_value, flags=re.MULTILINE)
    text_value = re.sub(r"[*_`~]", "", text_value)
    return text_value.strip()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_FTS_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_MAX_SEARCH_TOKENS = 8


def _build_fts5_match_query(query: str) -> str | None:
    """Build a safe SQLite FTS5 MATCH expression from user text.

    User input is reduced to tokenizer-like word tokens, then each token is
    quoted before joining with AND semantics. FTS5 operators, column filters,
    NEAR groups, wildcards, and punctuation never cross this boundary.
    """
    tokens = _FTS_TOKEN_RE.findall(query.casefold())
    if not tokens:
        return None
    unique_tokens = list(dict.fromkeys(tokens))[:_MAX_SEARCH_TOKENS]
    return " ".join(f'"{token}"' for token in unique_tokens)


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Known mechanical phrases emitted by providers such as DashScope. These are
# stripped or rewritten before the proposal is returned or persisted so the
# manuscript stays in-world.
_FORBIDDEN_TEMPLATE_PHRASES = (
    "revision anchor",
    "the chapter closes",
    "the next scene",
    "first draft",
    "rewritten chapter",
    "focus character",
    "focus_motivation",
    "relationship_status",
    "outline_hook",
)

_FORBIDDEN_TEMPLATE_PATTERN = "|".join(
    re.escape(phrase) for phrase in _FORBIDDEN_TEMPLATE_PHRASES
)
_MECHANICAL_PREAMBLE_RE = re.compile(
    rf"^\s*(?:here(?:'s| is)|below is|sure[,!:]?|certainly[,!:]?|"
    rf"as requested[,!:]?|draft(?:ed)? chapter)\b.*"
    rf"(?:{_FORBIDDEN_TEMPLATE_PATTERN}).*$",
    re.IGNORECASE,
)
_FORBIDDEN_TEMPLATE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"revision anchor:\s*", re.IGNORECASE), ""),
    (re.compile(r"\bthe chapter closes\b", re.IGNORECASE), "The scene settles"),
    (re.compile(r"\bthe next scene\b", re.IGNORECASE), "What follows"),
    (re.compile(r"\bfirst draft\b", re.IGNORECASE), "opening passage"),
    (re.compile(r"\brewritten chapter\b", re.IGNORECASE), "reworked passage"),
    (re.compile(r"\bfocus character\b", re.IGNORECASE), "central figure"),
    (re.compile(r"\bfocus_motivation\b", re.IGNORECASE), "central motivation"),
    (re.compile(r"\brelationship_status\b", re.IGNORECASE), "relationship state"),
    (re.compile(r"\boutline_hook\b", re.IGNORECASE), "story hook"),
)


_PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.IGNORECASE
    ),
    re.compile(
        r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.IGNORECASE
    ),
    re.compile(r"new\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|the)", re.IGNORECASE),
    re.compile(r"override\s+(?:the\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"(?:act\s+as|pretend\s+to\s+be)\s+(?:a|an|the)", re.IGNORECASE),
)


def _sanitize_instruction(instruction: str) -> str:
    """Neutralize common prompt-injection patterns and wrap the instruction.

    The wrapped format makes it harder for user content to be interpreted as
    system-level instructions, while preserving the author's writing direction.
    """
    cleaned = instruction.strip()
    for pattern in _PROMPT_INJECTION_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned


def _format_user_instruction(instruction: str) -> str:
    """Format an author instruction so it is structurally isolated in the prompt."""
    sanitized = _sanitize_instruction(instruction)
    return f"[BEGIN AUTHOR INSTRUCTION]\n{sanitized}\n[END AUTHOR INSTRUCTION]"


def _sanitize_chapter_markdown(markdown: str) -> str:
    """Remove provider preambles and mechanical labels before manuscript storage."""
    cleaned_lines: list[str] = []
    for line in str(markdown).strip().splitlines():
        if _MECHANICAL_PREAMBLE_RE.search(line):
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    for pattern, replacement in _FORBIDDEN_TEMPLATE_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _owner_scopes(principal: Principal) -> tuple[str | None, str | None]:
    """Return (owner_id, guest_session_id) used to scope repository queries."""
    if principal.kind == "owner" and principal.owner_id:
        return principal.owner_id, None
    return None, principal.session_id


# ---------------------------------------------------------------------------
# Domain services
# ---------------------------------------------------------------------------

__all__ = [
    "Any",
    "Iterable",
    "Path",
    "T",
    "cast",
    "hashlib",
    "secrets",
    "bcrypt",
    "yaml",
    "datetime",
    "TextGenerationProviderError",
    "TextGenerationProviderName",
    "DocumentDto",
    "ExportDto",
    "JobDto",
    "ProjectDto",
    "ReviewDto",
    "RevisionDto",
    "SnapshotDto",
    "StudioRepository",
    "TextGenerationProviderFactory",
    "InvalidOperation",
    "NotFound",
    "RevisionConflict",
    "DOCUMENT_KINDS",
    "DocumentKind",
    "ExportFormat",
    "_token_hash",
    "_word_count",
    "dump_json",
    "load_json",
    "new_id",
    "utcnow",
    "GUEST_TTL",
    "SESSION_COOKIE",
    "CSRF_COOKIE",
    "_DUMMY_HASH",
    "logger",
    "iso",
    "_plain_text",
    "_as_utc",
    "_escape_html",
    "_build_fts5_match_query",
    "_stream_sha256",
    "_safe_load_json",
    "_sanitize_chapter_markdown",
    "_sanitize_instruction",
    "_format_user_instruction",
    "Principal",
    "_owner_scopes",
    "_project_payload",
    "_document_payload",
    "_revision_payload",
    "_snapshot_payload",
    "_review_payload",
    "_job_payload",
    "_export_payload",
]
