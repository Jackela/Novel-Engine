"""
SourceKnowledgeEntry Entity

RAG-focused knowledge entry with vector storage support.

Warzone 4: AI Brain - BRAIN-003
Entity representing a chunk of content ready for vector storage and retrieval.

Constitution Compliance:
- Article I (DDD): Entity with identity and behavior
- Article I (DDD): Self-validating with invariants
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from .knowledge_metadata import ConfidentialityLevel, KnowledgeMetadata
from .source_type import SourceType


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """
    Metadata attached to source knowledge entries.

    Why frozen:
        Immutable metadata prevents accidental modification during
        pipeline processing.

    Attributes:
        word_count: Number of words in the content
        chunk_index: Zero-based index if this is part of a sequence
        total_chunks: Total number of chunks in the sequence
        tags: Optional tags for filtering
        extra: Additional metadata key-value pairs (preserved for backward compatibility)
        knowledge: Structured system-level metadata (world_version, confidentiality, etc.)
    """

    word_count: int
    chunk_index: int = 0
    total_chunks: int = 1
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    knowledge: KnowledgeMetadata = field(default_factory=lambda: KnowledgeMetadata.create_default())


@dataclass
class SourceKnowledgeEntry:
    """
    Entity representing a knowledge entry for RAG (Retrieval-Augmented Generation).

    Why not frozen:
        Entity needs to update embedding_id after embedding generation.

    Why dataclass:
        Simple value-based entity with clear structure.

    Attributes:
        id: Unique identifier for this entry (UUID)
        content: The text content of this knowledge entry
        source_type: Type of source (CHARACTER, LORE, SCENE, etc.)
        source_id: ID of the source entity
        embedding_id: ID of the embedding in vector store (set after embedding)
        metadata: Additional metadata about the content
        created_at: Timestamp when entry was created
        updated_at: Timestamp when entry was last updated

    Invariants:
        - id must be a non-empty string
        - content must be non-empty
        - source_type must be a valid SourceType
        - source_id must be non-empty
    """

    id: str
    content: str
    source_type: SourceType
    source_id: str
    metadata: SourceMetadata
    embedding_id: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        if not self.id or not self.id.strip():
            raise ValueError("SourceKnowledgeEntry.id is required")

        if not self.content or not self.content.strip():
            raise ValueError("SourceKnowledgeEntry.content cannot be empty")

        if not isinstance(self.source_type, SourceType):
            raise ValueError(
                f"source_type must be a SourceType, got {type(self.source_type)}"
            )

        if not self.source_id or not self.source_id.strip():
            raise ValueError("SourceKnowledgeEntry.source_id is required")

        # Normalize timestamps to UTC
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=timezone.utc))
        else:
            object.__setattr__(self, "created_at", self.created_at.astimezone(timezone.utc))

        if self.updated_at.tzinfo is None:
            object.__setattr__(self, "updated_at", self.updated_at.replace(tzinfo=timezone.utc))
        else:
            object.__setattr__(self, "updated_at", self.updated_at.astimezone(timezone.utc))

        # Strip content
        object.__setattr__(self, "content", self.content.strip())

    def set_embedding_id(self, embedding_id: str) -> None:
        """
        Set the embedding ID after generating the vector.

        Args:
            embedding_id: ID of the embedding in vector store

        Raises:
            ValueError: If embedding_id is empty
        """
        if not embedding_id or not embedding_id.strip():
            raise ValueError("embedding_id cannot be empty")

        object.__setattr__(self, "embedding_id", embedding_id)
        object.__setattr__(self, "updated_at", _utcnow())

    def update_content(self, new_content: str) -> None:
        """
        Update the content of this entry.

        Why:
            Content updates should invalidate the embedding.
            The embedding_id is cleared to force re-embedding.

        Args:
            new_content: New content for this entry

        Raises:
            ValueError: If new_content is empty
        """
        if not new_content or not new_content.strip():
            raise ValueError("content cannot be empty")

        object.__setattr__(self, "content", new_content.strip())
        object.__setattr__(self, "embedding_id", None)  # Invalidate embedding
        object.__setattr__(self, "updated_at", _utcnow())

    def has_embedding(self) -> bool:
        """
        Check if this entry has been embedded.

        Returns:
            True if embedding_id is set
        """
        return self.embedding_id is not None

    def get_vector_document_id(self) -> str:
        """
        Get the ID to use for vector storage.

        Returns:
            ID to use for VectorDocument (uses embedding_id if set, else own id)

        Why:
            Allows separating entity ID from vector storage ID for flexibility.
        """
        return self.embedding_id if self.embedding_id else self.id

    def to_vector_metadata(self) -> dict[str, Any]:
        """
        Convert to metadata dict for VectorDocument.

        Returns:
            Dictionary with all metadata fields for vector storage

        Why:
            Encapsulates the mapping between entity and vector metadata.
        """
        base_metadata = {
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "chunk_index": self.metadata.chunk_index,
            "total_chunks": self.metadata.total_chunks,
            "word_count": self.metadata.word_count,
            "tags": self.metadata.tags.copy(),
            "created_at": self.created_at.isoformat(),
            # Include structured knowledge metadata
            "world_version": self.metadata.knowledge.world_version,
            "confidentiality_level": self.metadata.knowledge.confidentiality_level.value,
            "source_version": self.metadata.knowledge.source_version,
        }

        # Add last_accessed if present
        if self.metadata.knowledge.last_accessed:
            base_metadata["last_accessed"] = self.metadata.knowledge.last_accessed.isoformat()

        # Merge with extra fields (extra takes precedence for backward compatibility)
        return {**base_metadata, **self.metadata.extra}

    @classmethod
    def create(
        cls,
        content: str,
        source_type: SourceType | str,
        source_id: str,
        word_count: int,
        chunk_index: int = 0,
        total_chunks: int = 1,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
        knowledge_metadata: KnowledgeMetadata | None = None,
        world_version: str | None = None,
        confidentiality_level: ConfidentialityLevel | str | None = None,
        id: str | None = None,
    ) -> SourceKnowledgeEntry:
        """
        Factory method to create a new SourceKnowledgeEntry.

        Args:
            content: Text content
            source_type: Type of source (SourceType or string)
            source_id: ID of the source entity
            word_count: Number of words in content
            chunk_index: Index in chunk sequence (default 0)
            total_chunks: Total chunks in sequence (default 1)
            tags: Optional tags for filtering
            extra_metadata: Additional metadata key-value pairs
            knowledge_metadata: Structured knowledge metadata (takes precedence over world_version/confidentiality_level)
            world_version: World version for knowledge metadata (if knowledge_metadata not provided)
            confidentiality_level: Confidentiality level for knowledge metadata (if knowledge_metadata not provided)
            id: Optional explicit ID (auto-generated if not provided)

        Returns:
            New SourceKnowledgeEntry instance
        """
        # Normalize source_type
        if isinstance(source_type, str):
            source_type = SourceType.from_string(source_type)

        # Build or use provided KnowledgeMetadata
        if knowledge_metadata is None:
            if isinstance(confidentiality_level, str):
                try:
                    confidentiality_level = ConfidentialityLevel(confidentiality_level)
                except ValueError:
                    confidentiality_level = ConfidentialityLevel.PUBLIC
            knowledge_metadata = KnowledgeMetadata.create_default(
                world_version=world_version or "1.0.0",
                confidentiality_level=confidentiality_level or ConfidentialityLevel.PUBLIC,
            )

        metadata = SourceMetadata(
            word_count=word_count,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            tags=tags or [],
            extra=extra_metadata or {},
            knowledge=knowledge_metadata,
        )

        return cls(
            id=id or str(uuid4()),
            content=content,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
        )


__all__ = [
    "SourceKnowledgeEntry",
    "SourceMetadata",
]
