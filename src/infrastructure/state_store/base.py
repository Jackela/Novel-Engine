"""Base State Store Interface.

Abstract base class for all state store implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from src.infrastructure.state_store.config import StateKey


class StateStore(ABC):
    """Abstract base class for state store implementations.

    Provides a unified interface for different storage backends
    (Redis, PostgreSQL, S3).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection to the storage backend."""
        pass

    @abstractmethod
    async def get(self, key: StateKey) -> Optional[Any]:
        """Retrieve value by key.

        Args:
            key: The state key to look up

        Returns:
            The stored value or None if not found
        """
        pass

    @abstractmethod
    async def set(self, key: StateKey, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value by key.

        Args:
            key: The state key
            value: The value to store
            ttl: Optional time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: StateKey) -> bool:
        """Delete value by key.

        Args:
            key: The state key to delete

        Returns:
            True if deleted, False if not found or error
        """
        pass

    @abstractmethod
    async def exists(self, key: StateKey) -> bool:
        """Check if key exists.

        Args:
            key: The state key to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def list_keys(self, pattern: str) -> List[StateKey]:
        """List keys matching pattern.

        Args:
            pattern: Pattern to match keys against

        Returns:
            List of matching state keys
        """
        pass

    @abstractmethod
    async def increment(self, key: StateKey, amount: int = 1) -> Optional[int]:
        """Increment counter value.

        Args:
            key: The counter key
            amount: Amount to increment by

        Returns:
            New value or None if error
        """
        pass

    @abstractmethod
    async def expire(self, key: StateKey, ttl: int) -> bool:
        """Set TTL for existing key.

        Args:
            key: The state key
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check store health.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to the storage backend."""
        pass
