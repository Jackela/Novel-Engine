"""Refresh-session storage used by browser cookie authentication.

The in-process store is intentionally small and deterministic for development
and tests. Production deployments should back the same contract with the
``refresh_sessions`` table added by the baseline migration.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@dataclass
class RefreshSession:
    """Server-side metadata for a browser refresh token."""

    session_id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    user_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    revoked_at: datetime | None = None
    rotated_at: datetime | None = None
    rotated_to: str | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > _now()


@dataclass(frozen=True)
class RefreshSessionIssue:
    """Issued refresh token plus its persisted session record."""

    raw_token: str
    session: RefreshSession


class InMemoryRefreshSessionStore:
    """Revocable refresh-token store with one-time rotation semantics."""

    def __init__(self) -> None:
        self._sessions: dict[str, RefreshSession] = {}
        self._tokens_by_hash: dict[str, str] = {}

    def create(
        self,
        *,
        user_id: str,
        expires_in_days: int,
        user_snapshot: dict[str, Any] | None = None,
    ) -> RefreshSessionIssue:
        session_id = str(uuid4())
        raw_token = f"{session_id}.{secrets.token_urlsafe(48)}"
        session = RefreshSession(
            session_id=session_id,
            user_id=user_id,
            token_hash=_hash_token(raw_token),
            expires_at=_now() + timedelta(days=expires_in_days),
            user_snapshot=user_snapshot or {},
        )
        self._sessions[session_id] = session
        self._tokens_by_hash[session.token_hash] = session_id
        return RefreshSessionIssue(raw_token=raw_token, session=session)

    def verify(self, raw_token: str) -> RefreshSession | None:
        session_id = self._tokens_by_hash.get(_hash_token(raw_token))
        if session_id is None:
            return None
        session = self._sessions.get(session_id)
        if session is None or not session.is_active:
            return None
        return session

    def rotate(
        self,
        *,
        raw_token: str,
        expires_in_days: int,
    ) -> RefreshSessionIssue | None:
        session = self.verify(raw_token)
        if session is None:
            return None

        new_issue = self.create(
            user_id=session.user_id,
            expires_in_days=expires_in_days,
            user_snapshot=dict(session.user_snapshot),
        )
        rotated_at = _now()
        session.revoked_at = rotated_at
        session.rotated_at = rotated_at
        session.rotated_to = new_issue.session.session_id
        session.updated_at = rotated_at
        self._tokens_by_hash.pop(session.token_hash, None)
        return new_issue

    def revoke(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        session_id = self._tokens_by_hash.get(_hash_token(raw_token))
        if session_id is None:
            return
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.revoked_at = _now()
        session.updated_at = session.revoked_at
        self._tokens_by_hash.pop(session.token_hash, None)

    def reset(self) -> None:
        self._sessions.clear()
        self._tokens_by_hash.clear()


_refresh_session_store = InMemoryRefreshSessionStore()


def get_refresh_session_store() -> InMemoryRefreshSessionStore:
    """Return the process-wide refresh session store."""
    return _refresh_session_store


def reset_refresh_session_store() -> None:
    """Clear refresh session state between tests."""
    _refresh_session_store.reset()


__all__ = [
    "InMemoryRefreshSessionStore",
    "RefreshSession",
    "RefreshSessionIssue",
    "get_refresh_session_store",
    "reset_refresh_session_store",
]
