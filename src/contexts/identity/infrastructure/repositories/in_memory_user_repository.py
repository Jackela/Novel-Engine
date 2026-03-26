"""In-memory implementation of the user repository port."""

from __future__ import annotations

from uuid import UUID

import bcrypt

from src.contexts.identity.domain.aggregates.user import User
from src.contexts.identity.domain.repositories.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    """Simple in-memory user repository with a seeded demo account."""

    def __init__(self, seed_demo_user: bool = True) -> None:
        self._users_by_id: dict[UUID, User] = {}
        self._users_by_email: dict[str, UUID] = {}
        self._users_by_username: dict[str, UUID] = {}

        if seed_demo_user:
            self._seed_demo_user()

    def _seed_demo_user(self) -> None:
        """Create a deterministic demo user for local development and tests."""
        hashed_password = bcrypt.hashpw(
            b"demo-password",
            bcrypt.gensalt(rounds=12),
        ).decode("utf-8")
        user = User(
            email="operator@novel.engine",
            username="operator",
            hashed_password=hashed_password,
            roles=["author"],
            profile={"display_name": "Operator"},
            email_verified=True,
        )
        self._store(user)

    def _remove_indexes(self, user_id: UUID) -> None:
        existing = self._users_by_id.get(user_id)
        if existing is None:
            return

        self._users_by_email.pop(existing.email, None)
        self._users_by_username.pop(existing.username, None)

    def _store(self, user: User) -> None:
        self._remove_indexes(user.id)
        self._users_by_id[user.id] = user
        self._users_by_email[user.email] = user.id
        self._users_by_username[user.username] = user.id

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        user_id = self._users_by_email.get(email)
        return self._users_by_id.get(user_id) if user_id else None

    async def get_by_username(self, username: str) -> User | None:
        user_id = self._users_by_username.get(username)
        return self._users_by_id.get(user_id) if user_id else None

    async def save(self, user: User) -> None:
        self._store(user)

    async def delete(self, user_id: UUID) -> bool:
        user = self._users_by_id.pop(user_id, None)
        if user is None:
            return False

        self._users_by_email.pop(user.email, None)
        self._users_by_username.pop(user.username, None)
        return True

    async def exists_by_email(self, email: str) -> bool:
        return email in self._users_by_email

    async def exists_by_username(self, username: str) -> bool:
        return username in self._users_by_username

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        users = sorted(self._users_by_id.values(), key=lambda user: user.created_at)
        return users[offset : offset + limit]
