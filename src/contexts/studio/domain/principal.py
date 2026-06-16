"""Caller identity primitive for Novel Studio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Principal:
    """Identity of the caller for authorization and scoping."""

    session_id: str
    kind: str
    owner_id: str | None
    expires_at: datetime | None
