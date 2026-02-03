"""
ChunkingStrategy Value Object

Defines how text should be chunked for vector storage and RAG retrieval.

Warzone 4: AI Brain - BRAIN-003
Encapsulates chunking configuration for semantic search optimization.

Constitution Compliance:
- Article I (DDD): Value object is immutable and self-validating
- Article V (SOLID): SRP - Single responsibility for chunking configuration
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, Optional


class ChunkStrategyType(str, Enum):
    """
    Type of chunking strategy to use.

    FIXED: Split by fixed word count with overlap
    SEMANTIC: Split by semantic boundaries (sentences, paragraphs)
    SENTENCE: Split by sentences with overlap
    PARAGRAPH: Split by paragraphs with overlap
    """

    FIXED = "fixed"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"


# Default chunking configurations
DEFAULT_CHUNK_SIZE: Final[int] = 500
DEFAULT_OVERLAP: Final[int] = 50
MIN_CHUNK_SIZE: Final[int] = 50
MAX_CHUNK_SIZE: Final[int] = 2000


@dataclass(frozen=True, slots=True)
class ChunkingStrategy:
    """
    Value object defining how text should be chunked for vector storage.

    Why frozen:
        Immutable configuration ensures chunking behavior is consistent
        throughout the ingestion pipeline.

    Attributes:
        strategy: Type of chunking strategy (FIXED, SEMANTIC, SENTENCE, PARAGRAPH)
        chunk_size: Maximum words per chunk
        overlap: Number of overlapping words between chunks
        min_chunk_size: Minimum chunk size to avoid tiny fragments

    Example:
        >>> strategy = ChunkingStrategy(
        ...     strategy=ChunkStrategyType.FIXED,
        ...     chunk_size=500,
        ...     overlap=50
        ... )
        >>> chunks = TextChunker.chunk(text, strategy)
    """

    strategy: ChunkStrategyType
    chunk_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_OVERLAP
    min_chunk_size: int = MIN_CHUNK_SIZE

    def __post_init__(self) -> None:
        """Validate chunking parameters."""
        chunk_size = int(self.chunk_size)
        overlap = int(self.overlap)
        min_chunk_size = int(self.min_chunk_size)

        if chunk_size < MIN_CHUNK_SIZE:
            raise ValueError(
                f"chunk_size must be at least {MIN_CHUNK_SIZE}, got {chunk_size}"
            )
        if chunk_size > MAX_CHUNK_SIZE:
            raise ValueError(
                f"chunk_size must be at most {MAX_CHUNK_SIZE}, got {chunk_size}"
            )
        if overlap < 0:
            raise ValueError(f"overlap must be non-negative, got {overlap}")
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap must be less than chunk_size, got {overlap} >= {chunk_size}"
            )
        if min_chunk_size < 1:
            raise ValueError(f"min_chunk_size must be at least 1, got {min_chunk_size}")
        if min_chunk_size >= chunk_size:
            raise ValueError(
                f"min_chunk_size must be less than chunk_size, "
                f"got {min_chunk_size} >= {chunk_size}"
            )

        # Ensure integer values
        object.__setattr__(self, "chunk_size", chunk_size)
        object.__setattr__(self, "overlap", overlap)
        object.__setattr__(self, "min_chunk_size", min_chunk_size)

    @classmethod
    def default(cls) -> ChunkingStrategy:
        """
        Create default chunking strategy.

        Returns:
            ChunkingStrategy with fixed 500-word chunks and 50-word overlap
        """
        return cls(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=DEFAULT_CHUNK_SIZE,
            overlap=DEFAULT_OVERLAP,
        )

    @classmethod
    def for_character(cls) -> ChunkingStrategy:
        """
        Create chunking strategy optimized for character profiles.

        Returns:
            ChunkingStrategy with smaller chunks for profile data
        """
        return cls(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=200,
            overlap=20,
        )

    @classmethod
    def for_scene(cls) -> ChunkingStrategy:
        """
        Create chunking strategy optimized for scenes.

        Returns:
            ChunkingStrategy with paragraph-aware chunking
        """
        return cls(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=300,
            overlap=30,
        )

    @classmethod
    def for_lore(cls) -> ChunkingStrategy:
        """
        Create chunking strategy optimized for lore entries.

        Returns:
            ChunkingStrategy with fixed chunks for world-building content
        """
        return cls(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=400,
            overlap=40,
        )

    def effective_chunk_size(self) -> int:
        """
        Get the effective chunk size accounting for overlap.

        Returns:
            Number of new words per chunk (chunk_size - overlap)
        """
        return self.chunk_size - self.overlap


# Common strategies for convenience
class ChunkingStrategies:
    """
    Pre-configured chunking strategies for common use cases.

    Why class with class methods:
        Provides discoverable, named strategies that can be referenced
        throughout the codebase without duplicating configuration.
    """

    @staticmethod
    def default() -> ChunkingStrategy:
        """Default strategy: 500-word fixed chunks with 50-word overlap."""
        return ChunkingStrategy.default()

    @staticmethod
    def character() -> ChunkingStrategy:
        """Character profiles: 200-word semantic chunks."""
        return ChunkingStrategy.for_character()

    @staticmethod
    def scene() -> ChunkingStrategy:
        """Scenes: 300-word paragraph chunks."""
        return ChunkingStrategy.for_scene()

    @staticmethod
    def lore() -> ChunkingStrategy:
        """Lore: 400-word fixed chunks."""
        return ChunkingStrategy.for_lore()

    @staticmethod
    def small() -> ChunkingStrategy:
        """Small chunks: 100 words with 10-word overlap."""
        return ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED, chunk_size=100, overlap=10
        )

    @staticmethod
    def large() -> ChunkingStrategy:
        """Large chunks: 1000 words with 100-word overlap."""
        return ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED, chunk_size=1000, overlap=100
        )


__all__ = [
    "ChunkStrategyType",
    "ChunkingStrategy",
    "ChunkingStrategies",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_OVERLAP",
    "MIN_CHUNK_SIZE",
    "MAX_CHUNK_SIZE",
]
