"""Knowledge repository port interface."""

from typing import Protocol
from uuid import UUID

from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase


class KnowledgeRepositoryPort(Protocol):
    """Repository port for KnowledgeBase aggregate."""

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        """Get knowledge base by ID.

        Args:
            knowledge_base_id: Knowledge base UUID

        Returns:
            KnowledgeBase if found, None otherwise
        """
        ...

    async def get_by_name(self, name: str) -> KnowledgeBase | None:
        """Get knowledge base by name.

        Args:
            name: Knowledge base name

        Returns:
            KnowledgeBase if found, None otherwise
        """
        ...

    async def save(self, knowledge_base: KnowledgeBase) -> None:
        """Save knowledge base.

        Args:
            knowledge_base: Knowledge base to save
        """
        ...

    async def delete(self, knowledge_base_id: UUID) -> bool:
        """Delete knowledge base.

        Args:
            knowledge_base_id: Knowledge base UUID to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeBase]:
        """List all knowledge bases.

        Args:
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of knowledge bases
        """
        ...
