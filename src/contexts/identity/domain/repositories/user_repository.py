"""User Repository Interface

Repository port for User aggregate persistence.
This module defines both the abstract class for implementations
and maintains backward compatibility with the old structure.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.contexts.identity.domain.aggregates.user import User
from src.contexts.identity.domain.ports.user_repository_port import (
    UserRepositoryPort,
)


class UserRepository(UserRepositoryPort, ABC):
    """Abstract implementation of UserRepositoryPort.

    This abstract class implements the UserRepositoryPort protocol
    and serves as the base for concrete repository implementations.

    AI注意:
    - This is a port in hexagonal architecture
    - Implementations in infrastructure layer
    - All methods are async
    """

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by their ID."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address."""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by their username."""
        pass

    @abstractmethod
    async def save(self, user: User) -> None:
        """Save a user (create or update)."""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete a user. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists."""
        pass

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool:
        """Check if a user with the given username exists."""
        pass

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        """List all users with pagination.

        Default implementation returns empty list.
        Concrete implementations should override this.
        """
        return []


class AuthenticationService(ABC):
    """Service for authentication operations.

    Handles password hashing and verification.

    Note: This is kept for backward compatibility.
    New code should use AuthenticationPort from domain.ports.
    """

    @abstractmethod
    async def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password."""
        pass

    @abstractmethod
    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a hash."""
        pass

    @abstractmethod
    async def generate_token(self, user_id: str, token_type: str = "access") -> str:
        """Generate an authentication token."""
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> Optional[str]:
        """Verify a token and return the user_id if valid."""
        pass
