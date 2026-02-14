"""
IPromptRepository Port Interface

Hexagonal architecture port defining the contract for prompt template persistence.

Warzone 4: AI Brain - BRAIN-014A

Constitution Compliance:
- Article II (Hexagonal): Domain/Application layer defines port, Infrastructure provides adapter
- Article I (DDD): Pure interface with no infrastructure coupling
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.models.prompt_template import PromptTemplate


class PromptRepositoryError(Exception):
    """Base exception for prompt repository errors."""


class PromptNotFoundError(PromptRepositoryError):
    """Raised when a prompt template is not found."""

    def __init__(self, prompt_id: str) -> None:
        self.prompt_id = prompt_id
        super().__init__(f"Prompt template with id '{prompt_id}' not found")


class PromptValidationError(PromptRepositoryError):
    """Raised when prompt template validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Prompt validation failed: {message}")


class IPromptRepository(ABC):
    """
    Repository port for prompt template persistence.

    This interface defines the contract that infrastructure adapters must implement
    for persisting and retrieving PromptTemplate entities.

    Per Article II (Hexagonal Architecture):
    - Domain/Application layer defines this port
    - Infrastructure layer provides adapter implementation (SQLite, PostgreSQL, etc.)
    - Application use cases depend ONLY on this abstraction, never on concrete adapters

    Methods:
        save: Persist a prompt template (create or update)
        get_by_id: Retrieve a prompt template by its unique ID
        get_by_name: Retrieve a prompt template by name
        list_all: List all prompt templates with optional filtering
        delete: Remove a prompt template (soft delete)
        get_version_history: Get all versions of a prompt template
        get_by_tag: List prompts by tag

    Constitution Compliance:
    - Article II (Hexagonal): Port interface in application layer
    - Article V (SOLID): ISP - Interface Segregation Principle (focused contract)
    - Article V (SOLID): DIP - Depend on abstractions, not concretions
    """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def get_version_history(self, template_id: str) -> list[PromptTemplate]:
        """
        Get all versions of a prompt template.

        This includes the template itself and all versions with parent_version_id
        pointing to it (direct descendants).

        Args:
            template_id: ID of the prompt template

        Returns:
            List of PromptTemplate entities ordered by version (ascending)

        Raises:
            PromptRepositoryError: If retrieval operation fails
        """

    @abstractmethod
    async def get_by_tag(self, tag: str, limit: int = 50) -> list[PromptTemplate]:
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

    @abstractmethod
    async def count(self) -> int:
        """
        Count total number of prompt templates.

        Returns:
            Total count of non-deleted prompt templates

        Raises:
            PromptRepositoryError: If count operation fails
        """

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[PromptTemplate]:
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


__all__ = [
    "IPromptRepository",
    "PromptRepositoryError",
    "PromptNotFoundError",
    "PromptValidationError",
]
