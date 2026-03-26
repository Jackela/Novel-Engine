"""User repository port (interface).

This module defines the abstract interface for user repository operations,
following the Ports and Adapters pattern (Hexagonal Architecture).

The domain layer depends on this port, while infrastructure provides
concrete implementations (e.g., PostgresUserRepository).
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.contexts.identity.domain.aggregates.user import User


class UserRepositoryPort(Protocol):
    """Port interface for user repository operations.

    This protocol defines the contract for user persistence operations.
    It abstracts away the underlying storage mechanism from the domain layer.

    Implementations:
        - PostgresUserRepository: Uses PostgreSQL for user storage
        - InMemoryUserRepository: In-memory implementation for testing
    """

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get a user by their ID.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The User aggregate if found, None otherwise.
        """
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by their email address.

        Args:
            email: The user's email address.

        Returns:
            The User aggregate if found, None otherwise.
        """
        ...

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by their username.

        Args:
            username: The user's username.

        Returns:
            The User aggregate if found, None otherwise.
        """
        ...

    async def save(self, user: User) -> None:
        """Save a user (create or update).

        Args:
            user: The User aggregate to save.

        Raises:
            UserRepositoryError: If save operation fails.
        """
        ...

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            True if user was deleted, False if not found.

        Raises:
            UserRepositoryError: If delete operation fails.
        """
        ...

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists.

        Args:
            email: The email address to check.

        Returns:
            True if a user with this email exists, False otherwise.
        """
        ...

    async def exists_by_username(self, username: str) -> bool:
        """Check if a user with the given username exists.

        Args:
            username: The username to check.

        Returns:
            True if a user with this username exists, False otherwise.
        """
        ...

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
        ...
