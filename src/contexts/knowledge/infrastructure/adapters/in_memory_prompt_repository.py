"""
In-Memory Prompt Repository Adapter

Warzone 4: AI Brain - BRAIN-014B
In-memory implementation of IPromptRepository for testing and development.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implements application port
- Article I (DDD): No business logic, only persistence
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional

from ...application.ports.i_prompt_repository import (
    IPromptRepository,
    PromptRepositoryError,
    PromptValidationError,
)
from ...domain.models.prompt_template import PromptTemplate


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class InMemoryPromptRepository(IPromptRepository):
    """
    In-memory implementation of prompt template repository.

    Why OrderedDict:
        Maintains insertion order for predictable test results.
        Provides O(1) lookups by ID.

    Why thread-safe:
        Uses asyncio.Lock for concurrent access protection.

    Attributes:
        _templates: Storage for prompt templates (ID -> PromptTemplate)
        _lock: Async lock for thread-safe operations
        _deleted_ids: Set of soft-deleted template IDs
    """

    def __init__(self) -> None:
        """Initialize the in-memory repository."""
        self._templates: OrderedDict[str, PromptTemplate] = OrderedDict()
        self._name_index: dict[str, str] = {}  # name -> id (latest version)
        self._lock = asyncio.Lock()
        self._deleted_ids: set[str] = set()

    async def save(self, template: PromptTemplate) -> str:
        """
        Persist a prompt template (insert new or update existing).

        Args:
            template: PromptTemplate entity to persist

        Returns:
            The ID of the saved template

        Raises:
            PromptValidationError: If template validation fails
            PromptRepositoryError: If persistence operation fails
        """
        async with self._lock:
            try:
                # Validate template before saving
                issues = template.validate_syntax()
                if issues:
                    raise PromptValidationError(
                        f"Template validation failed: {', '.join(issues)}"
                    )

                # Check if updating existing
                if template.id in self._templates:
                    existing = self._templates[template.id]
                    # Update timestamp
                    object.__setattr__(template, "updated_at", _utcnow())

                # Store template
                self._templates[template.id] = template

                # Update name index (for get_by_name)
                existing_id = self._name_index.get(template.name)
                if existing_id is None:
                    self._name_index[template.name] = template.id
                else:
                    existing = self._templates.get(existing_id)
                    if existing is None or template.version >= existing.version:
                        self._name_index[template.name] = template.id

                return template.id

            except PromptValidationError:
                raise
            except Exception as e:
                raise PromptRepositoryError(f"Failed to save template: {e}") from e

    async def get_by_id(self, template_id: str) -> Optional[PromptTemplate]:
        """
        Retrieve a prompt template by its unique identifier.

        Args:
            template_id: Unique identifier of the prompt template

        Returns:
            PromptTemplate if found, None otherwise

        Raises:
            PromptRepositoryError: If retrieval operation fails
        """
        async with self._lock:
            try:
                if template_id in self._deleted_ids:
                    return None
                return self._templates.get(template_id)
            except Exception as e:
                raise PromptRepositoryError(f"Failed to get template by id: {e}") from e

    async def get_by_name(
        self, name: str, version: Optional[int] = None
    ) -> Optional[PromptTemplate]:
        """
        Retrieve a prompt template by name.

        Args:
            name: Name of the prompt template
            version: Optional version number (latest if None)

        Returns:
            PromptTemplate if found, None otherwise

        Raises:
            PromptRepositoryError: If retrieval operation fails
        """
        async with self._lock:
            try:
                # Find all templates with this name
                matching = [
                    t
                    for t in self._templates.values()
                    if t.name == name and t.id not in self._deleted_ids
                ]

                if not matching:
                    return None

                # If version specified, find exact match
                if version is not None:
                    for template in matching:
                        if template.version == version:
                            return template
                    return None

                # Return latest version
                matching.sort(key=lambda t: t.version, reverse=True)
                return matching[0]

            except Exception as e:
                raise PromptRepositoryError(f"Failed to get template by name: {e}") from e

    async def list_all(
        self,
        tags: Optional[list[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptTemplate]:
        """
        List all prompt templates with optional filtering.

        Args:
            tags: Optional filter by tags (prompts must have ALL tags)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of PromptTemplate entities

        Raises:
            PromptRepositoryError: If listing operation fails
        """
        async with self._lock:
            try:
                results = [
                    t
                    for t in self._templates.values()
                    if t.id not in self._deleted_ids
                ]

                # Filter by tags if specified
                if tags:
                    results = [
                        t
                        for t in results
                        if all(tag in t.tags for tag in tags)
                    ]

                # Apply pagination
                start = offset
                end = start + limit
                return results[start:end]

            except Exception as e:
                raise PromptRepositoryError(f"Failed to list templates: {e}") from e

    async def delete(self, template_id: str) -> bool:
        """
        Soft delete a prompt template by its unique identifier.

        Args:
            template_id: Unique identifier of the template to delete

        Returns:
            True if deleted, False if not found

        Raises:
            PromptRepositoryError: If deletion fails
        """
        async with self._lock:
            try:
                if template_id in self._templates and template_id not in self._deleted_ids:
                    self._deleted_ids.add(template_id)
                    # Remove from name index
                    template = self._templates[template_id]
                    if self._name_index.get(template.name) == template_id:
                        # Find if there are other versions
                        others = [
                            t
                            for t in self._templates.values()
                            if t.name == template.name and t.id != template_id
                        ]
                        if others:
                            latest = max(others, key=lambda t: t.version)
                            self._name_index[template.name] = latest.id
                        else:
                            self._name_index.pop(template.name, None)
                    return True
                return False

            except Exception as e:
                raise PromptRepositoryError(f"Failed to delete template: {e}") from e

    async def get_version_history(
        self, template_id: str
    ) -> list[PromptTemplate]:
        """
        Get all versions of a prompt template.

        Args:
            template_id: ID of the prompt template

        Returns:
            List of PromptTemplate entities ordered by version (ascending)

        Raises:
            PromptRepositoryError: If retrieval operation fails
        """
        async with self._lock:
            try:
                if template_id not in self._templates:
                    return []

                template = self._templates[template_id]

                # Find all versions with same name
                versions = [
                    t
                    for t in self._templates.values()
                    if t.name == template.name and t.id not in self._deleted_ids
                ]

                # Sort by version
                versions.sort(key=lambda t: t.version)
                return versions

            except Exception as e:
                raise PromptRepositoryError(f"Failed to get version history: {e}") from e

    async def get_by_tag(
        self, tag: str, limit: int = 50
    ) -> list[PromptTemplate]:
        """
        List prompt templates by tag.

        Args:
            tag: Tag to filter by
            limit: Maximum number of results

        Returns:
            List of PromptTemplate entities with the specified tag

        Raises:
            PromptRepositoryError: If retrieval operation fails
        """
        async with self._lock:
            try:
                results = [
                    t
                    for t in self._templates.values()
                    if tag in t.tags and t.id not in self._deleted_ids
                ]
                return results[:limit]

            except Exception as e:
                raise PromptRepositoryError(f"Failed to get templates by tag: {e}") from e

    async def count(self) -> int:
        """
        Count total number of prompt templates.

        Returns:
            Total count of non-deleted prompt templates

        Raises:
            PromptRepositoryError: If count operation fails
        """
        async with self._lock:
            try:
                return sum(
                    1 for t in self._templates.values() if t.id not in self._deleted_ids
                )
            except Exception as e:
                raise PromptRepositoryError(f"Failed to count templates: {e}") from e

    async def search(
        self, query: str, limit: int = 20
    ) -> list[PromptTemplate]:
        """
        Search prompt templates by name or description.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching PromptTemplate entities

        Raises:
            PromptRepositoryError: If search operation fails
        """
        async with self._lock:
            try:
                query_lower = query.lower()
                results = [
                    t
                    for t in self._templates.values()
                    if t.id not in self._deleted_ids
                    and (
                        query_lower in t.name.lower()
                        or query_lower in t.description.lower()
                    )
                ]
                return results[:limit]

            except Exception as e:
                raise PromptRepositoryError(f"Failed to search templates: {e}") from e


__all__ = ["InMemoryPromptRepository"]
