"""PostgreSQL implementation of UserRepository.

This module provides a concrete implementation of the UserRepository
using PostgreSQL as the underlying storage mechanism.
"""

from __future__ import annotations

import json
from uuid import UUID

import asyncpg

from src.contexts.identity.domain.aggregates.user import User
from src.contexts.identity.domain.repositories.user_repository import UserRepository


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository.

    This class implements the UserRepository abstract class using
    PostgreSQL as the underlying storage mechanism.

    Attributes:
        _pool: asyncpg connection pool for database access.
    """

    def __init__(self, pool: asyncpg.Pool):
        """Initialize PostgreSQL user repository.

        Args:
            pool: asyncpg connection pool.
        """
        self._pool = pool

    def _row_to_user(self, row: asyncpg.Record) -> User:
        """Convert a database row to a User aggregate.

        Args:
            row: Database record.

        Returns:
            User aggregate.
        """
        # Parse JSON fields
        roles = json.loads(row["roles"]) if row["roles"] else []
        profile = json.loads(row["profile"]) if row["profile"] else {}

        # Parse timestamps
        last_login = row["last_login"]
        locked_until = row["locked_until"]

        return User(
            id=UUID(row["id"]),
            email=row["email"],
            username=row["username"],
            hashed_password=row["hashed_password"],
            status=row["status"],
            roles=roles,
            profile=profile,
            email_verified=row["email_verified"],
            last_login=last_login,
            failed_login_attempts=row["failed_login_attempts"],
            locked_until=locked_until,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get a user by their ID.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The User aggregate if found, None otherwise.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM users WHERE id = $1
                """,
                str(user_id),
            )
            if row:
                return self._row_to_user(row)
            return None

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by their email address.

        Args:
            email: The user's email address.

        Returns:
            The User aggregate if found, None otherwise.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM users WHERE email = $1
                """,
                email,
            )
            if row:
                return self._row_to_user(row)
            return None

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by their username.

        Args:
            username: The user's username.

        Returns:
            The User aggregate if found, None otherwise.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM users WHERE username = $1
                """,
                username,
            )
            if row:
                return self._row_to_user(row)
            return None

    async def save(self, user: User) -> None:
        """Save a user (create or update).

        Args:
            user: The User aggregate to save.
        """
        async with self._pool.acquire() as conn:
            # Convert complex types to JSON
            roles_json = json.dumps(user.roles)
            profile_json = json.dumps(user.profile)

            await conn.execute(
                """
                INSERT INTO users (
                    id, email, username, hashed_password, status,
                    roles, profile, email_verified, last_login,
                    failed_login_attempts, locked_until, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    username = EXCLUDED.username,
                    hashed_password = EXCLUDED.hashed_password,
                    status = EXCLUDED.status,
                    roles = EXCLUDED.roles,
                    profile = EXCLUDED.profile,
                    email_verified = EXCLUDED.email_verified,
                    last_login = EXCLUDED.last_login,
                    failed_login_attempts = EXCLUDED.failed_login_attempts,
                    locked_until = EXCLUDED.locked_until,
                    updated_at = EXCLUDED.updated_at
                """,
                str(user.id),
                user.email,
                user.username,
                user.hashed_password,
                user.status,
                roles_json,
                profile_json,
                user.email_verified,
                user.last_login,
                user.failed_login_attempts,
                user.locked_until,
                user.created_at,
                user.updated_at,
            )

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            True if user was deleted, False if not found.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM users WHERE id = $1
                """,
                str(user_id),
            )
            # Check if any row was deleted
            return "DELETE 1" in result

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists.

        Args:
            email: The email address to check.

        Returns:
            True if a user with this email exists, False otherwise.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM users WHERE email = $1
                """,
                email,
            )
            return row is not None

    async def exists_by_username(self, username: str) -> bool:
        """Check if a user with the given username exists.

        Args:
            username: The username to check.

        Returns:
            True if a user with this username exists, False otherwise.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM users WHERE username = $1
                """,
                username,
            )
            return row is not None

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """List all users with pagination.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of User aggregates.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
            return [self._row_to_user(row) for row in rows]
