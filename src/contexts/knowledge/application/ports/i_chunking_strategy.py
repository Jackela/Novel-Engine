"""
Chunking Strategy Port Interface

Defines the contract for text chunking strategies in the RAG pipeline.

Constitution Compliance:
- Article II (Hexagonal): Application layer port interface
- Article V (SOLID): Interface segregation - chunking operations only

Warzone 4: AI Brain - BRAIN-039A-01
Defines the pluggable chunking strategy interface for RAG content processing.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.contexts.knowledge.domain.models.chunking_strategy import (
    ChunkingStrategy,
)


class ChunkingError(Exception):
    """Exception raised for chunking strategy errors."""

    def __init__(self, message: str, code: str = "CHUNKING_ERROR"):
        """
        Initialize chunking error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code for categorization
        """
        self.code = code
        super().__init__(message)


class Chunk:
    """
    Domain entity representing a chunk of text with metadata.

    Why not a value object:
        Chunks have identity (their index) and may carry rich metadata
        that makes them meaningful as entities in the RAG pipeline.

    Attributes:
        text: The chunked text content
        index: Zero-based index of this chunk in the sequence
        metadata: Optional metadata dictionary (source, position, etc.)
    """

    def __init__(
        self,
        text: str,
        index: int,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize a Chunk.

        Args:
            text: The chunked text content
            index: Zero-based index in the chunk sequence
            metadata: Optional metadata for this chunk
        """
        self.text = text
        self.index = index
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        """String representation for debugging."""
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Chunk(index={self.index}, text={repr(preview)})"

    def __eq__(self, other: object) -> bool:
        """Equality check based on text and index."""
        if not isinstance(other, Chunk):
            return False
        return self.text == other.text and self.index == other.index

    def __hash__(self) -> int:
        """Hash based on text and index."""
        return hash((self.text, self.index))


class IChunkingStrategy(ABC):
    """
    Port interface for text chunking strategies.

    Implementations provide different approaches to splitting text into
    chunks for vector storage and RAG retrieval, such as:
    - Fixed-size chunking with overlap
    - Sentence-aware chunking
    - Paragraph-aware chunking
    - Semantic chunking using embeddings

    Constitution Compliance:
        - Article II (Hexagonal): Port interface for chunking implementations
        - Article V (SOLID): Single responsibility - text chunking
    """

    @abstractmethod
    async def chunk(
        self,
        text: str,
        config: Optional[ChunkingStrategy] = None,
    ) -> list[Chunk]:
        """
        Split text into chunks according to this strategy.

        Args:
            text: Source text to chunk
            config: Optional chunking configuration (uses defaults if None)

        Returns:
            List of Chunk entities with text, index, and metadata

        Raises:
            ChunkingError: If chunking fails
            ValueError: If text is empty or configuration is invalid

        Example:
            >>> strategy = IChunkingStrategy()
            >>> chunks = await strategy.chunk(
            ...     "Long text content...",
            ...     ChunkingStrategy.strategy=ChunkStrategyType.FIXED
            ... )
            >>> len(chunks)
            5
            >>> chunks[0].text
            'Long text content...'
            >>> chunks[0].index
            0
        """
        ...

    @abstractmethod
    def supports_strategy_type(self, strategy_type: str) -> bool:
        """
        Check if this implementation supports a given strategy type.

        Args:
            strategy_type: The strategy type identifier (e.g., "fixed", "semantic")

        Returns:
            True if this implementation handles the strategy type
        """
        ...


__all__ = [
    "ChunkingError",
    "Chunk",
    "IChunkingStrategy",
]
