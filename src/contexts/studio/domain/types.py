"""Shared Novel Studio domain types."""

from __future__ import annotations

from typing import Literal

DocumentKind = Literal["chapter", "outline", "character", "world", "note"]
SessionKind = Literal["owner", "guest"]
JobStatus = Literal["queued", "running", "completed", "failed", "interrupted"]
JobKind = Literal["ai", "review", "export", "import"]
ExportFormat = Literal["markdown", "docx", "epub"]

DOCUMENT_KINDS: tuple[DocumentKind, ...] = (
    "chapter",
    "outline",
    "character",
    "world",
    "note",
)
