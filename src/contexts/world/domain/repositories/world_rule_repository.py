#!/usr/bin/env python3
"""World Rule Repository Interface.

This module defines the abstract repository interface for WorldRule entities.
Following DDD principles, the domain layer defines the contract while the
infrastructure layer provides concrete implementations.

Why a separate WorldRule repository: World rules are frequently queried by
category and severity. A dedicated repository enables efficient filtering
and supports rule-based constraint checking during narrative generation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.world_rule import WorldRule


class IWorldRuleRepository(ABC):
    """Abstract repository interface for WorldRule entities.

    This interface defines the contract for persisting and querying
    WorldRule entities. The design optimizes for rule lookup by category
    and severity to support narrative constraint checking.

    Thread Safety:
        Implementations should be thread-safe for concurrent access.
    """

    # Basic CRUD Operations

    @abstractmethod
    async def save(self, rule: WorldRule) -> WorldRule:
        """Save a WorldRule to persistent storage.

        Handles both create and update operations based on whether
        the rule already exists.

        Args:
            rule: The WorldRule to save.

        Returns:
            The saved WorldRule (may include generated IDs).

        Raises:
            RepositoryException: If save operation fails.
        """

    @abstractmethod
    async def get_by_id(self, rule_id: str) -> Optional[WorldRule]:
        """Retrieve a WorldRule by its unique identifier.

        Args:
            rule_id: Unique identifier for the rule.

        Returns:
            WorldRule if found, None otherwise.
        """

    @abstractmethod
    async def delete(self, rule_id: str) -> bool:
        """Delete a WorldRule from persistent storage.

        Args:
            rule_id: Unique identifier for the rule.

        Returns:
            True if deletion was successful, False if not found.
        """

    @abstractmethod
    async def exists(self, rule_id: str) -> bool:
        """Check if a WorldRule exists in storage.

        Args:
            rule_id: Unique identifier for the rule.

        Returns:
            True if rule exists, False otherwise.
        """

    # Category-based Queries

    @abstractmethod
    async def find_by_category(
        self,
        category: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorldRule]:
        """Find rules by category (e.g., "magic", "physics", "social").

        Args:
            category: Category to filter by (case-insensitive).
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of WorldRule instances matching the category.
        """

    # Severity-based Queries

    @abstractmethod
    async def find_by_severity_range(
        self,
        min_severity: int = 0,
        max_severity: int = 100,
        limit: int = 100,
    ) -> List[WorldRule]:
        """Find rules within a severity range.

        Args:
            min_severity: Minimum severity (inclusive).
            max_severity: Maximum severity (inclusive).
            limit: Maximum number of results.

        Returns:
            List of WorldRule instances within the severity range.
        """

    @abstractmethod
    async def find_absolute_rules(
        self,
        limit: int = 100,
    ) -> List[WorldRule]:
        """Find all absolute rules (severity >= 90).

        Args:
            limit: Maximum number of results.

        Returns:
            List of absolute WorldRule instances.
        """

    # Search Queries

    @abstractmethod
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[WorldRule]:
        """Search rules by name and optionally filter by category.

        Args:
            query: Search query string (matches name, case-insensitive).
            category: Optional category to filter results.
            limit: Maximum number of results.

        Returns:
            List of matching WorldRule instances.
        """

    # Utility Methods

    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorldRule]:
        """Get all rules with pagination.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of WorldRule instances.
        """

    @abstractmethod
    async def count_all(self) -> int:
        """Get total count of world rules.

        Returns:
            Total number of rules in storage.
        """

    @abstractmethod
    async def get_all_categories(self) -> List[str]:
        """Get all unique categories across all rules.

        Useful for building category filters.

        Returns:
            Sorted list of unique categories.
        """


class WorldRuleRepositoryException(Exception):
    """Base exception for world rule repository operations."""


class WorldRuleNotFoundException(WorldRuleRepositoryException):
    """Raised when a requested world rule is not found."""

    def __init__(self, rule_id: str):
        super().__init__(f"World rule not found: {rule_id}")
        self.rule_id = rule_id


class DuplicateWorldRuleException(WorldRuleRepositoryException):
    """Raised when attempting to create a duplicate world rule."""

    def __init__(self, rule_id: str, name: str):
        super().__init__(f"World rule already exists: {rule_id} ({name})")
        self.rule_id = rule_id
        self.name = name
