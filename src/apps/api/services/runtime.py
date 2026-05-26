"""Canonical in-memory runtime state for guest sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_workspace_id(workspace_id: str | None) -> str | None:
    if workspace_id is None:
        return None
    normalized = workspace_id.strip()
    return normalized or None


@dataclass(slots=True)
class GuestSession:
    """Canonical guest workspace session."""

    workspace_id: str
    session_id: str
    is_new_session: bool
    created_at: str


class CanonicalRuntimeService:
    """Manage guest sessions for local-first workspace access."""

    def __init__(self) -> None:
        self._sessions: dict[str, GuestSession] = {}

    def reset(self) -> None:
        """Reset in-memory state for tests or application reconfiguration."""
        self._sessions.clear()

    async def shutdown(self) -> None:
        """Clear transient state during API shutdown."""
        self.reset()

    async def create_or_resume_guest_session(
        self,
        workspace_id: str | None = None,
    ) -> GuestSession:
        """Create or resume a canonical guest workspace session."""
        normalized_workspace_id = _normalize_workspace_id(workspace_id)
        if normalized_workspace_id is None:
            normalized_workspace_id = f"guest-{uuid4().hex[:12]}"

        session = self._sessions.get(normalized_workspace_id)
        if session is None:
            session = GuestSession(
                workspace_id=normalized_workspace_id,
                session_id=f"session-{uuid4().hex[:12]}",
                is_new_session=True,
                created_at=_timestamp(),
            )
            self._sessions[normalized_workspace_id] = session
            return session

        session.is_new_session = False
        return session


runtime_store = CanonicalRuntimeService()

__all__ = ["CanonicalRuntimeService", "GuestSession", "runtime_store"]
