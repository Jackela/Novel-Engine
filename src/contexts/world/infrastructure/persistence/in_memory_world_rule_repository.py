#!/usr/bin/env python3
"""In-Memory World Rule Repository Implementation.

This module provides an in-memory implementation of IWorldRuleRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

from typing import Dict, List, Optional, Set

from src.contexts.world.domain.entities.world_rule import WorldRule
from src.contexts.world.domain.repositories.world_rule_repository import (
    IWorldRuleRepository,
)


class InMemoryWorldRuleRepository(IWorldRuleRepository):
    """In-memory implementation of IWorldRuleRepository.

    Stores world rules in a dictionary indexed by ID, with additional
    indexes for efficient category-based lookups.

    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access,
        use locking or switch to a thread-safe implementation.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._rules: Dict[str, WorldRule] = {}
        # Index: category (lowercase) -> set of rule_ids
        self._category_index: Dict[str, Set[str]] = {}

    def _index_rule(self, rule: WorldRule) -> None:
        """Add rule to category index.

        Args:
            rule: The rule to index.
        """
        if rule.category:
            category_lower = rule.category.lower()
            if category_lower not in self._category_index:
                self._category_index[category_lower] = set()
            self._category_index[category_lower].add(rule.id)

    def _unindex_rule(self, rule: WorldRule) -> None:
        """Remove rule from category index.

        Args:
            rule: The rule to unindex.
        """
        if rule.category:
            category_lower = rule.category.lower()
            if category_lower in self._category_index:
                self._category_index[category_lower].discard(rule.id)
                if not self._category_index[category_lower]:
                    del self._category_index[category_lower]

    async def save(self, rule: WorldRule) -> WorldRule:
        """Save a WorldRule to storage.

        Args:
            rule: The WorldRule to save.

        Returns:
            The saved WorldRule.
        """
        existing = self._rules.get(rule.id)
        if existing:
            # Update: unindex old, index new
            self._unindex_rule(existing)

        self._rules[rule.id] = rule
        self._index_rule(rule)
        return rule

    async def get_by_id(self, rule_id: str) -> Optional[WorldRule]:
        """Retrieve a WorldRule by ID.

        Args:
            rule_id: Unique identifier.

        Returns:
            WorldRule if found, None otherwise.
        """
        return self._rules.get(rule_id)

    async def delete(self, rule_id: str) -> bool:
        """Delete a WorldRule.

        Args:
            rule_id: Unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        rule = self._rules.get(rule_id)
        if rule:
            self._unindex_rule(rule)
            del self._rules[rule_id]
            return True
        return False

    async def exists(self, rule_id: str) -> bool:
        """Check if a WorldRule exists.

        Args:
            rule_id: Unique identifier.

        Returns:
            True if exists.
        """
        return rule_id in self._rules

    async def find_by_category(
        self,
        category: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorldRule]:
        """Find rules by category.

        Args:
            category: Category to filter by (case-insensitive).
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of matching WorldRule instances.
        """
        category_lower = category.lower().strip()
        rule_ids = self._category_index.get(category_lower, set())
        rules = [
            self._rules[rule_id]
            for rule_id in rule_ids
            if rule_id in self._rules
        ]
        # Sort by severity descending, then by name
        rules.sort(key=lambda r: (-r.severity, r.name.lower()))
        return rules[offset : offset + limit]

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
            limit: Maximum results.

        Returns:
            List of WorldRule instances within the range.
        """
        rules = [
            rule
            for rule in self._rules.values()
            if min_severity <= rule.severity <= max_severity
        ]
        # Sort by severity descending
        rules.sort(key=lambda r: -r.severity)
        return rules[:limit]

    async def find_absolute_rules(
        self,
        limit: int = 100,
    ) -> List[WorldRule]:
        """Find all absolute rules (severity >= 90).

        Args:
            limit: Maximum results.

        Returns:
            List of absolute WorldRule instances.
        """
        return await self.find_by_severity_range(
            min_severity=90, max_severity=100, limit=limit
        )

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[WorldRule]:
        """Search rules by name with optional category filtering.

        Args:
            query: Search query string (matches name, case-insensitive).
            category: Optional category to filter results.
            limit: Maximum results.

        Returns:
            List of matching WorldRule instances.
        """
        query_lower = query.lower().strip()
        category_lower = category.lower().strip() if category else None
        results: List[WorldRule] = []

        for rule in self._rules.values():
            # Name match (case-insensitive partial match)
            if query_lower and query_lower not in rule.name.lower():
                continue

            # Category filter
            if category_lower is not None:
                if not rule.category or rule.category.lower() != category_lower:
                    continue

            results.append(rule)
            if len(results) >= limit:
                break

        # Sort by name for consistent alphabetical results
        results.sort(key=lambda r: r.name.lower())
        return results

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorldRule]:
        """Get all rules with pagination.

        Args:
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of WorldRule instances.
        """
        all_rules = list(self._rules.values())
        # Sort by updated_at descending
        all_rules.sort(key=lambda r: r.updated_at, reverse=True)
        return all_rules[offset : offset + limit]

    async def count_all(self) -> int:
        """Get total count of world rules."""
        return len(self._rules)

    async def get_all_categories(self) -> List[str]:
        """Get all unique categories across all rules.

        Returns:
            Sorted list of unique categories.
        """
        return sorted(self._category_index.keys())

    # Utility methods for testing

    def clear(self) -> None:
        """Clear all data from the repository."""
        self._rules.clear()
        self._category_index.clear()
