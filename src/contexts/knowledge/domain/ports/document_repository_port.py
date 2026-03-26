"""Document repository port interface."""

from typing import Protocol
from uuid import UUID

from src.contexts.knowledge.domain.entities.document import Document


class DocumentRepositoryPort(Protocol):
    """Repository port for Document entity."""

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Get document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document if found, None otherwise
        """
        ...

    async def get_by_knowledge_base(self, kb_id: UUID) -> list[Document]:
        """Get all documents in a knowledge base.

        Args:
            kb_id: Knowledge base UUID

        Returns:
            List of documents
        """
        ...

    async def save(self, document: Document) -> None:
        """Save document.

        Args:
            document: Document to save
        """
        ...

    async def delete(self, document_id: UUID) -> bool:
        """Delete document.

        Args:
            document_id: Document UUID to delete

        Returns:
            True if deleted, False if not found
        """
        ...
