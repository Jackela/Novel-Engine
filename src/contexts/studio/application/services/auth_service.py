from __future__ import annotations

from src.contexts.studio.application.service_common import (
    _DUMMY_HASH,
    GUEST_TTL,
    Any,
    InvalidOperation,
    Principal,
    StudioRepository,
    _as_utc,
    _token_hash,
    bcrypt,
    datetime,
    secrets,
    utcnow,
)

__all__ = ["AuthService"]


class AuthService:
    """Owner configuration and session lifecycle."""

    def __init__(self, repository: StudioRepository, session_secret: str) -> None:
        self._repository = repository
        self._session_secret = session_secret

    def owner_exists(self) -> bool:
        return self._repository.owner_exists()

    def owner_principal(self, username: str | None = None) -> Principal:
        """Return an operational principal for local CLI maintenance."""
        if username is not None:
            owner = self._repository.get_owner_by_username(username.strip())
        else:
            owner = self._repository.get_first_owner()
        if owner is None:
            raise InvalidOperation("Configure the local owner before importing data.")
        return Principal(
            session_id=f"cli:{owner.id}",
            kind="owner",
            owner_id=owner.id,
            expires_at=None,
        )

    def setup_owner(self, username: str, password: str) -> dict[str, Any]:
        username = username.strip()
        password_bytes = password.encode("utf-8")
        if not username or len(password) < 10 or len(password_bytes) > 72:
            raise InvalidOperation(
                "Username is required and password must be 10-72 UTF-8 bytes."
            )
        if self._repository.owner_exists():
            raise InvalidOperation("The local owner has already been configured.")
        owner = self._repository.create_owner(
            username=username,
            password_hash=bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode(
                "ascii"
            ),
        )
        return {"id": owner.id, "username": owner.username}

    def create_owner_session(
        self,
        username: str,
        password: str,
    ) -> tuple[str, str, Principal]:
        password_bytes = password.encode("utf-8")
        owner = self._repository.get_owner_by_username(username.strip())
        # Always run bcrypt against a real or dummy hash so the timing of the
        # response does not reveal whether the username exists.
        password_hash = (
            owner.password_hash.encode("ascii") if owner is not None else _DUMMY_HASH
        )
        password_valid = bcrypt.checkpw(password_bytes, password_hash)
        if owner is None or len(password_bytes) > 72 or not password_valid:
            raise InvalidOperation("Invalid username or password.")
        return self._create_session(kind="owner", owner_id=owner.id)

    def create_guest_session(self) -> tuple[str, str, Principal]:
        return self._create_session(
            kind="guest",
            owner_id=None,
            expires_at=utcnow() + GUEST_TTL,
        )

    def _create_session(
        self,
        *,
        kind: str,
        owner_id: str | None,
        expires_at: datetime | None = None,
    ) -> tuple[str, str, Principal]:
        token = secrets.token_urlsafe(36)
        csrf_token = secrets.token_urlsafe(32)
        now = utcnow()
        record = self._repository.create_session(
            kind=kind,
            owner_id=owner_id,
            token_hash=_token_hash(token, self._session_secret),
            csrf_token=csrf_token,
            expires_at=expires_at,
            created_at=now,
            last_seen_at=now,
        )
        return token, csrf_token, Principal(record.id, kind, owner_id, expires_at)

    def csrf_token_for_session(self, token_hash: str) -> str | None:
        """Return the CSRF token associated with a session token hash."""
        record = self._repository.get_session_by_token_hash(token_hash)
        return record.csrf_token if record is not None else None

    def principal_from_token(self, token: str | None) -> Principal | None:
        if not token:
            return None
        record = self._repository.get_session_by_token_hash(
            _token_hash(token, self._session_secret)
        )
        if record is None:
            return None
        now = utcnow()
        expires_at = record.expires_at
        if expires_at is not None and _as_utc(expires_at) <= now:
            self._repository.delete_session(record.id)
            return None
        self._repository.update_session_last_seen(record.id, now)
        return Principal(record.id, record.kind, record.owner_id, expires_at)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        record = self._repository.get_session_by_token_hash(
            _token_hash(token, self._session_secret)
        )
        if record is not None:
            self._repository.delete_session(record.id)

    def cleanup_expired_guests(self) -> int:
        return self._repository.delete_expired_guest_sessions(utcnow())
