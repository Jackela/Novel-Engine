"""
Document Entity

Represents a searchable document within a knowledge base.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.shared.domain.base.entity import Entity

# Type alias for Document ID
DocumentId = UUID


@dataclass(kw_only=True, eq=False)
class Document(Entity[DocumentId]):
    """
    Document entity for knowledge storage.

    AI注意:
    - Documents belong to a specific knowledge base
    - Content can be chunked for better retrieval
    - Tracks indexing status for vector search
    - Supports multiple content types
    """

    knowledge_base_id: str
    title: str
    content: str
    content_type: str = field(default="text")
    source: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    is_indexed: bool = field(default=False)
    indexed_at: Optional[datetime] = None
    chunk_count: int = field(default=0)
    word_count: int = field(default=0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate document invariants.

        Required by Entity base class. Called during __post_init__.
        """
        if not self.knowledge_base_id:
            raise ValueError("Document must belong to a knowledge base")

        if not self.title or len(self.title.strip()) == 0:
            raise ValueError("Document title cannot be empty")

        if len(self.title) > 300:
            raise ValueError("Document title cannot exceed 300 characters")

        if not self.content:
            raise ValueError("Document content cannot be empty")

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        super().__post_init__()

        # Calculate word count
        self.word_count = len(self.content.split())

    @property
    def content_hash(self) -> str:
        """Generate simple content hash for change detection."""
        import hashlib

        return hashlib.md5(self.content.encode()).hexdigest()[:16]

    def update_content(self, new_content: str) -> None:
        """
        Update document content and reset indexing status.

        Args:
            new_content: New document content
        """
        self.content = new_content
        self.word_count = len(new_content.split())
        self.is_indexed = False
        self.indexed_at = None
        self.embedding = None
        self.chunks = []
        self.chunk_count = 0
        self.updated_at = datetime.utcnow()

    def update_title(self, new_title: str) -> None:
        """Update document title."""
        if not new_title or len(new_title.strip()) == 0:
            raise ValueError("Title cannot be empty")

        if len(new_title) > 300:
            raise ValueError("Title cannot exceed 300 characters")

        self.title = new_title
        self.updated_at = datetime.utcnow()

    def add_tag(self, tag: str) -> None:
        """Add a tag to the document."""
        tag = tag.strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the document."""
        tag = tag.strip().lower()
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow()

    def set_indexed(self, embedding: Optional[List[float]] = None) -> None:
        """
        Mark document as indexed with optional embedding.

        Args:
            embedding: Optional vector embedding for the document
        """
        self.is_indexed = True
        self.indexed_at = datetime.utcnow()
        if embedding:
            self.embedding = embedding

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Add content chunks for better retrieval.

        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
        """
        self.chunks = chunks
        self.chunk_count = len(chunks)
        self.updated_at = datetime.utcnow()

    def get_chunk_content(self, chunk_index: int) -> Optional[str]:
        """Get content of a specific chunk."""
        if 0 <= chunk_index < len(self.chunks):
            return self.chunks[chunk_index].get("content")
        return None

    def update_metadata(self, key: str, value: Any) -> None:
        """Update document metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "id": str(self.id),
            "knowledge_base_id": self.knowledge_base_id,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "source": self.source,
            "tags": self.tags,
            "word_count": self.word_count,
            "chunk_count": self.chunk_count,
            "is_indexed": self.is_indexed,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_search_result(self) -> Dict[str, Any]:
        """Convert to search result format (excludes full content)."""
        return {
            "id": str(self.id),
            "title": self.title,
            "content_preview": self.content[:200] + "..."
            if len(self.content) > 200
            else self.content,
            "content_type": self.content_type,
            "source": self.source,
            "tags": self.tags,
            "word_count": self.word_count,
            "metadata": self.metadata,
        }
