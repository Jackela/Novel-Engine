"""
Chunking Strategy Base Module

Defines the abstract base class and shared constants for chunking strategies.
This module provides the foundation for the strategy pattern implementation.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...application.ports.i_chunking_strategy import Chunk
    from ...domain.models.chunking_strategy import ChunkingStrategy

# Default coherence threshold for warnings
DEFAULT_COHERENCE_THRESHOLD = 0.6
MIN_COHERENCE_THRESHOLD = 0.0
MAX_COHERENCE_THRESHOLD = 1.0

# Word pattern for counting
_WORD_PATTERN = re.compile(r"\S+")

# Sentence end pattern: . ! ? followed by whitespace
_SENTENCE_END = re.compile(r"[.!?]+\s+", re.MULTILINE)

# Paragraph delimiter: two or more newlines
_PARAGRAPH_DELIM = re.compile(r"\n\n+", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class CoherenceScore:
    """
    Coherence score for a chunk.

    Measures how semantically coherent a chunk is based on:
    - Internal coherence: similarity between sentences within the chunk
    - Boundary quality: whether the chunk starts/ends at natural boundaries
    - Size appropriateness: whether the chunk is too small or too large

    Attributes:
        score: Overall coherence score from 0.0 to 1.0
        internal_coherence: Average similarity between adjacent sentences
        boundary_quality: Score for how well chunk boundaries preserve structure
        size_score: Score based on whether chunk size is appropriate
        warnings: Tuple of warning messages for potential issues
        is_acceptable: Whether the chunk meets minimum coherence standards

    Example:
        >>> score = CoherenceScore(
        ...     score=0.85,
        ...     internal_coherence=0.82,
        ...     boundary_quality=0.90,
        ...     size_score=1.0,
        ...     warnings=(),
        ...     is_acceptable=True
        ... )
    """

    score: float
    internal_coherence: float
    boundary_quality: float
    size_score: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    is_acceptable: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize the coherence score."""
        # Clamp scores to valid range
        score = max(MIN_COHERENCE_THRESHOLD, min(MAX_COHERENCE_THRESHOLD, self.score))
        internal = max(
            MIN_COHERENCE_THRESHOLD,
            min(MAX_COHERENCE_THRESHOLD, self.internal_coherence),
        )
        boundary = max(
            MIN_COHERENCE_THRESHOLD, min(MAX_COHERENCE_THRESHOLD, self.boundary_quality)
        )
        size = max(
            MIN_COHERENCE_THRESHOLD, min(MAX_COHERENCE_THRESHOLD, self.size_score)
        )

        object.__setattr__(self, "score", score)
        object.__setattr__(self, "internal_coherence", internal)
        object.__setattr__(self, "boundary_quality", boundary)
        object.__setattr__(self, "size_score", size)

    def get_level(self) -> str:
        """
        Get the coherence level category.

        Returns:
            "excellent" (>=0.8), "good" (>=0.6), "fair" (>=0.4), "poor" (<0.4)
        """
        if self.score >= 0.8:
            return "excellent"
        if self.score >= 0.6:
            return "good"
        if self.score >= 0.4:
            return "fair"
        return "poor"


class BaseChunkingStrategy(ABC):
    """
    Abstract base class for chunking strategies.

    All chunking strategies must implement this interface to ensure
    consistent behavior across different chunking approaches.

    Example:
        >>> class MyStrategy(BaseChunkingStrategy):
        ...     async def chunk(self, text, config):
        ...         # Implementation
        ...         pass
        ...
        ...     def supports_strategy_type(self, strategy_type):
        ...         return strategy_type == "my_strategy"
    """

    @abstractmethod
    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into chunks according to the strategy.

        Args:
            text: Source text to chunk
            config: Optional chunking configuration

        Returns:
            List of Chunk entities with text, index, and metadata

        Raises:
            ChunkingError: If chunking fails
            ValueError: If text is empty or configuration is invalid
        """
        ...

    @abstractmethod
    def supports_strategy_type(self, strategy_type: str) -> bool:
        """
        Check if this implementation supports a given strategy type.

        Args:
            strategy_type: The strategy type identifier

        Returns:
            True if this strategy supports the given type
        """
        ...


def get_word_pattern() -> re.Pattern:
    """Get the compiled word pattern regex."""
    return _WORD_PATTERN


def get_sentence_end_pattern() -> re.Pattern:
    """Get the compiled sentence end pattern regex."""
    return _SENTENCE_END


def get_paragraph_delim_pattern() -> re.Pattern:
    """Get the compiled paragraph delimiter pattern regex."""
    return _PARAGRAPH_DELIM
