from __future__ import annotations

from src.contexts.studio.infrastructure.repository.common import (
    Owner,
    OwnerDto,
    SessionDto,
    SessionRecord,
    StudioDatabase,
    _owner_dto,
    _session_dto,
    datetime,
    func,
    new_id,
    select,
    utcnow,
)

__all__ = ["AuthRepositoryMixin"]


class AuthRepositoryMixin:
    database: StudioDatabase

    def owner_exists(self) -> bool:
        with self.database.session() as session:
            return (session.scalar(select(func.count()).select_from(Owner)) or 0) > 0

    def get_owner_by_username(self, username: str) -> OwnerDto | None:
        with self.database.session() as session:
            owner = session.scalar(select(Owner).where(Owner.username == username))
            return _owner_dto(owner) if owner is not None else None

    def get_first_owner(self) -> OwnerDto | None:
        with self.database.session() as session:
            owner = session.scalar(select(Owner).order_by(Owner.created_at))
            return _owner_dto(owner) if owner is not None else None

    def create_owner(self, username: str, password_hash: str) -> OwnerDto:
        with self.database.session() as session:
            owner = Owner(
                id=new_id(),
                username=username,
                password_hash=password_hash,
                created_at=utcnow(),
            )
            session.add(owner)
            session.flush()
            return _owner_dto(owner)

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
        with self.database.session() as session:
            record = SessionRecord(
                id=new_id(),
                kind=kind,
                owner_id=owner_id,
                token_hash=token_hash,
                csrf_token=csrf_token,
                created_at=created_at,
                expires_at=expires_at,
                last_seen_at=last_seen_at,
            )
            session.add(record)
            session.flush()
            return _session_dto(record)

    def get_session_by_token_hash(self, token_hash: str) -> SessionDto | None:
        with self.database.session() as session:
            record = session.scalar(
                select(SessionRecord).where(SessionRecord.token_hash == token_hash)
            )
            return _session_dto(record) if record is not None else None

    def delete_session(self, session_id: str) -> None:
        with self.database.session() as session:
            record = session.get(SessionRecord, session_id)
            if record is not None:
                session.delete(record)

    def delete_expired_guest_sessions(self, now: datetime) -> int:
        with self.database.session() as session:
            expired = session.scalars(
                select(SessionRecord).where(
                    SessionRecord.kind == "guest",
                    SessionRecord.expires_at.is_not(None),
                    SessionRecord.expires_at <= now,
                )
            ).all()
            for record in expired:
                session.delete(record)
            return len(expired)

    def update_session_last_seen(self, session_id: str, last_seen_at: datetime) -> None:
        with self.database.session() as session:
            record = session.get(SessionRecord, session_id)
            if record is not None:
                record.last_seen_at = last_seen_at
