#!/usr/bin/env python3
"""
Character Repository Interface

This module defines the repository interface for Character aggregates.
Following DDD principles, the interface is defined in the domain layer
while the implementation resides in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..aggregates.character import Character
from ..value_objects.character_id import CharacterID
from ..value_objects.character_profile import CharacterClass, CharacterRace


class ICharacterRepository(ABC):
    """
    Repository interface for Character aggregate operations.

    This interface defines the contract for persisting and retrieving
    Character aggregates. The actual implementation will be provided
    by the infrastructure layer using the chosen persistence technology.

    Following the Repository pattern, this provides a collection-like
    interface for Character aggregates while hiding persistence details.
    """

    # ==================== Basic CRUD Operations ====================

    @abstractmethod
    async def get_by_id(self, character_id: CharacterID) -> Optional[Character]:
        """
        Retrieve a character by their unique identifier.

        Args:
            character_id: The unique identifier of the character

        Returns:
            Character aggregate if found, None otherwise

        Raises:
            RepositoryException: If retrieval fails due to infrastructure issues
        """

    @abstractmethod
    async def save(self, character: Character) -> None:
        """
        Save a character aggregate to the repository.

        This method handles both new character creation and updates to
        existing characters. The repository implementation should use
        the character's version for optimistic concurrency control.

        Args:
            character: The character aggregate to save

        Raises:
            ConcurrencyException: If the character version conflicts
            RepositoryException: If save operation fails
        """

    @abstractmethod
    async def delete(self, character_id: CharacterID) -> bool:
        """
        Delete a character from the repository.

        Args:
            character_id: The unique identifier of the character to delete

        Returns:
            True if character was deleted, False if not found

        Raises:
            RepositoryException: If deletion fails due to infrastructure issues
        """

    @abstractmethod
    async def exists(self, character_id: CharacterID) -> bool:
        """
        Check if a character exists in the repository.

        Args:
            character_id: The unique identifier to check

        Returns:
            True if character exists, False otherwise

        Raises:
            RepositoryException: If check fails due to infrastructure issues
        """

    # ==================== Query Operations ====================

    @abstractmethod
    async def find_by_name(self, name: str) -> List[Character]:
        """
        Find characters by name (supports partial matching).

        Args:
            name: The character name to search for

        Returns:
            List of matching characters (may be empty)

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def find_by_class(self, character_class: CharacterClass) -> List[Character]:
        """
        Find all characters of a specific class.

        Args:
            character_class: The character class to filter by

        Returns:
            List of matching characters (may be empty)

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def find_by_race(self, race: CharacterRace) -> List[Character]:
        """
        Find all characters of a specific race.

        Args:
            race: The character race to filter by

        Returns:
            List of matching characters (may be empty)

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def find_by_level_range(
        self, min_level: int, max_level: int
    ) -> List[Character]:
        """
        Find characters within a level range.

        Args:
            min_level: Minimum character level (inclusive)
            max_level: Maximum character level (inclusive)

        Returns:
            List of matching characters (may be empty)

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def find_alive_characters(self) -> List[Character]:
        """
        Find all characters that are currently alive.

        Returns:
            List of alive characters (may be empty)

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def find_by_created_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Character]:
        """
        Find characters created within a date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of matching characters (may be empty)

        Raises:
            RepositoryException: If search fails
        """

    # ==================== Advanced Query Operations ====================

    @abstractmethod
    async def find_by_criteria(
        self, criteria: Dict[str, Any], limit: Optional[int] = None, offset: int = 0
    ) -> List[Character]:
        """
        Find characters matching multiple criteria.

        Args:
            criteria: Dictionary of search criteria (field: value pairs)
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of matching characters (may be empty)

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def count_by_criteria(self, criteria: Dict[str, Any]) -> int:
        """
        Count characters matching specific criteria.

        Args:
            criteria: Dictionary of search criteria (field: value pairs)

        Returns:
            Number of matching characters

        Raises:
            RepositoryException: If count fails
        """

    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistical information about characters in the repository.

        Returns:
            Dictionary containing statistics like:
            - total_characters: Total number of characters
            - characters_by_class: Count by character class
            - characters_by_race: Count by character race
            - average_level: Average character level
            - level_distribution: Distribution of characters by level range
            - alive_characters: Number of alive characters

        Raises:
            RepositoryException: If statistics calculation fails
        """

    # ==================== Bulk Operations ====================

    @abstractmethod
    async def save_multiple(self, characters: List[Character]) -> None:
        """
        Save multiple characters in a single transaction.

        Args:
            characters: List of character aggregates to save

        Raises:
            ConcurrencyException: If any character version conflicts
            RepositoryException: If save operation fails
        """

    @abstractmethod
    async def delete_multiple(self, character_ids: List[CharacterID]) -> int:
        """
        Delete multiple characters in a single transaction.

        Args:
            character_ids: List of character identifiers to delete

        Returns:
            Number of characters actually deleted

        Raises:
            RepositoryException: If deletion fails
        """

    # ==================== Version Control Operations ====================

    @abstractmethod
    async def get_version(self, character_id: CharacterID) -> Optional[int]:
        """
        Get the current version of a character without loading the full aggregate.

        Args:
            character_id: The character identifier

        Returns:
            Current version number, or None if character doesn't exist

        Raises:
            RepositoryException: If version retrieval fails
        """

    @abstractmethod
    async def get_character_history(
        self, character_id: CharacterID, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the change history for a character (if supported by implementation).

        Args:
            character_id: The character identifier
            limit: Maximum number of history entries to return

        Returns:
            List of history entries with version, timestamp, and changes

        Raises:
            RepositoryException: If history retrieval fails
            NotSupportedException: If history tracking is not supported
        """

    # ==================== Metadata/Smart Tag Operations ====================

    @abstractmethod
    async def find_by_smart_tag(
        self,
        category: str,
        tag: str,
        limit: int = 100,
    ) -> List[Character]:
        """
        Find characters with a specific smart tag in metadata.

        Args:
            category: The smart tag category (e.g., "genre", "mood").
            tag: The tag value to search for (case-insensitive).
            limit: Maximum number of results.

        Returns:
            List of Character instances with the smart tag.

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def find_by_smart_tags(
        self,
        tags: Dict[str, List[str]],
        match_all: bool = False,
        limit: int = 100,
    ) -> List[Character]:
        """
        Find characters matching multiple smart tags.

        Args:
            tags: Dictionary mapping categories to tag lists.
            match_all: If True, character must have ALL tags. If False, ANY tag.
            limit: Maximum number of results.

        Returns:
            List of matching Character instances.

        Raises:
            RepositoryException: If search fails
        """

    @abstractmethod
    async def find_by_metadata(
        self,
        metadata_key: str,
        metadata_value: Any = None,
        limit: int = 100,
    ) -> List[Character]:
        """
        Find characters with a specific metadata key or key-value pair.

        Args:
            metadata_key: The metadata key to search for.
            metadata_value: Optional value to match. If None, matches any value.
            limit: Maximum number of results.

        Returns:
            List of Character instances with the metadata key.

        Raises:
            RepositoryException: If search fails
        """


class RepositoryException(Exception):
    """Base exception for repository operations."""


class ConcurrencyException(RepositoryException):
    """Exception raised when optimistic concurrency control fails."""

    def __init__(self, message: str, expected_version: int, actual_version: int):
        super().__init__(message)
        self.expected_version = expected_version
        self.actual_version = actual_version


class NotSupportedException(RepositoryException):
    """Exception raised when an operation is not supported by the implementation."""
