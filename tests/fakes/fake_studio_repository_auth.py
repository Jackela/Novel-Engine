from __future__ import annotations

from datetime import datetime

from src.contexts.studio.application.ports.studio_repository import (
    OwnerDto,
    SessionDto,
)
from src.contexts.studio.domain.utils import new_id, utcnow


class FakeStudioRepositoryAuthMixin:
    _owners: dict[str, OwnerDto]
    _sessions: dict[str, SessionDto]

    def _delete_session_cascade(self, session_id: str) -> None:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True

    def owner_exists(self) -> bool:
        return bool(self._owners)

    def get_owner_by_username(self, username: str) -> OwnerDto | None:
        for owner in self._owners.values():
            if owner.username == username:
                return owner
        return None

    def get_first_owner(self) -> OwnerDto | None:
        if not self._owners:
            return None
        return min(self._owners.values(), key=lambda owner: owner.created_at)

    def create_owner(self, username: str, password_hash: str) -> OwnerDto:
        owner = OwnerDto(
            id=new_id(),
            username=username,
            password_hash=password_hash,
            created_at=utcnow(),
        )
        self._owners[owner.id] = owner
        return owner

    def create_session(
        self,
        *,
        kind: str,
        owner_id: str | None,
        token_hash: str,
        csrf_token: str,
        expires_at: datetime | None,
        created_at: datetime,
        last_seen_at: datetime,
    ) -> SessionDto:
        session = SessionDto(
            id=new_id(),
            kind=kind,
            owner_id=owner_id,
            token_hash=token_hash,
            csrf_token=csrf_token,
            created_at=created_at,
            expires_at=expires_at,
            last_seen_at=last_seen_at,
        )
        self._sessions[session.id] = session
        return session

    def get_session_by_token_hash(self, token_hash: str) -> SessionDto | None:
        for session in self._sessions.values():
            if session.token_hash == token_hash:
                return session
        return None

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def delete_expired_guest_sessions(self, now: datetime) -> int:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.kind == "guest"
            and session.expires_at is not None
            and session.expires_at <= now
        ]
        for session_id in expired:
            self._delete_session_cascade(session_id)
        return len(expired)

    def update_session_last_seen(
        self,
        session_id: str,
        last_seen_at: datetime,
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        self._sessions[session_id] = SessionDto(
            id=session.id,
            kind=session.kind,
            owner_id=session.owner_id,
            token_hash=session.token_hash,
            csrf_token=session.csrf_token,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_seen_at=last_seen_at,
        )
