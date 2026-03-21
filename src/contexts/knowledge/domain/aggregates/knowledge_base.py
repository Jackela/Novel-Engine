"""
Knowledge Base Aggregate Root

Manages document collections and vector search capabilities.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Protocol
from datetime import datetime
from uuid import UUID, uuid4

from src.shared.domain.base.aggregate import AggregateRoot
from src.contexts.knowledge.domain.entities.document import Document


# Type alias for Document ID
DocumentId = UUID


class VectorStore(Protocol):
    """Protocol for vector storage implementations."""

    async def store_embedding(
        self,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store document embedding in vector store."""
        ...

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents by embedding."""
        ...

    async def delete_document(self, document_id: str) -> None:
        """Delete document from vector store."""
        ...


@dataclass(kw_only=True, eq=False)
class KnowledgeBase(AggregateRoot):
    """
    Knowledge base aggregate for RAG operations.

    AI注意:
    - Manages document collection lifecycle
    - Supports semantic search via vector embeddings
    - Can be project-specific or global
    - Maintains document indexing status
    """

    name: str
    owner_id: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    documents: List[Document] = field(default_factory=list)
    embedding_model: str = field(default="text-embedding-3-small")
    is_public: bool = field(default=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate knowledge base invariants."""
        super().__post_init__()

        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Knowledge base name cannot be empty")

        if len(self.name) > 200:
            raise ValueError("Knowledge base name cannot exceed 200 characters")

        if not self.owner_id:
            raise ValueError("Knowledge base must have an owner")

    @property
    def document_count(self) -> int:
        """Return total number of documents."""
        return len(self.documents)

    @property
    def indexed_count(self) -> int:
        """Return number of indexed documents."""
        return sum(1 for doc in self.documents if doc.is_indexed)

    def add_document(
        self,
        title: str,
        content: str,
        content_type: str = "text",
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Document:
        """
        Add a new document to the knowledge base.

        Args:
            title: Document title
            content: Document content
            content_type: Type of content (text, markdown, code, etc.)
            source: Optional source reference
            tags: Optional list of tags

        Returns:
            The newly created document

        Raises:
            ValueError: If document count exceeds limit
        """
        if len(self.documents) >= 1000:
            raise ValueError("Knowledge base cannot exceed 1000 documents")

        document = Document(
            knowledge_base_id=str(self.id),
            title=title,
            content=content,
            content_type=content_type,
            source=source,
            tags=tags or [],
        )

        self.documents.append(document)
        self.updated_at = datetime.utcnow()

        return document

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID."""
        for doc in self.documents:
            if str(doc.id) == document_id:
                return doc
        return None

    def remove_document(self, document_id: str) -> bool:
        """
        Remove a document from the knowledge base.

        Args:
            document_id: ID of document to remove

        Returns:
            True if document was found and removed
        """
        initial_count = len(self.documents)
        self.documents = [doc for doc in self.documents if str(doc.id) != document_id]

        if len(self.documents) < initial_count:
            self.updated_at = datetime.utcnow()
            return True

        return False

    def search_by_tags(self, tags: List[str]) -> List[Document]:
        """
        Find documents matching any of the provided tags.

        Args:
            tags: List of tags to search for

        Returns:
            List of matching documents
        """
        tag_set = set(tags)
        return [doc for doc in self.documents if tag_set.intersection(set(doc.tags))]

    def update_metadata(self, key: str, value: Any) -> None:
        """Update knowledge base metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert knowledge base to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "owner_id": self.owner_id,
            "description": self.description,
            "project_id": self.project_id,
            "document_count": self.document_count,
            "indexed_count": self.indexed_count,
            "embedding_model": self.embedding_model,
            "is_public": self.is_public,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
