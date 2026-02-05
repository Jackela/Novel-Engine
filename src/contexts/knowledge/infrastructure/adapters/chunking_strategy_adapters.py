"""
Chunking Strategy Adapters

Implements IChunkingStrategy port for various chunking approaches.
Adapts the existing TextChunker domain service to the hexagonal architecture.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapters implementing application port
- Article V (SOLID): SRP - each adapter handles one strategy type

Warzone 4: AI Brain - BRAIN-039A-02
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError, IChunkingStrategy
from ...domain.models.chunking_strategy import (
    ChunkStrategyType,
    ChunkingStrategy,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

# Word pattern for counting
_WORD_PATTERN = re.compile(r"\S+")


class FixedChunkingStrategy:
    """
    Fixed-size chunking strategy adapter.

    Splits text into chunks of a fixed word count with configurable overlap.
    This is the simplest and most predictable chunking approach.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)

    Why fixed-size:
        - Predictable chunk sizes for vector storage
        - Simple to understand and debug
        - Works well for most content types
        - Consistent token counts for LLM context windows

    Example:
        >>> strategy = FixedChunkingStrategy()
        >>> chunks = await strategy.chunk(
        ...     "This is a long text..." * 100,
        ...     ChunkingStrategy.strategy=ChunkStrategyType.FIXED,
        ...     chunk_size=200,
        ...     overlap=20
        ... )
        >>> len(chunks)
        3
        >>> chunks[0].index
        0
        >>> chunks[1].index
        1
        >>> # Chunks overlap by 20 words
    """

    def __init__(self, default_config: ChunkingStrategy | None = None):
        """
        Initialize the fixed chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
        """
        self._default_config = default_config or ChunkingStrategy.default()

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into fixed-size chunks with overlap.

        Args:
            text: Source text to chunk
            config: Optional chunking configuration (uses defaults if None)

        Returns:
            List of Chunk entities with text, index, and metadata

        Raises:
            ChunkingError: If chunking fails
            ValueError: If text is empty or configuration is invalid

        Example:
            >>> strategy = FixedChunkingStrategy()
            >>> chunks = await strategy.chunk("long text...")
            >>> chunks[0].text
            'long text...'
            >>> chunks[0].metadata["word_count"]
            500
        """
        # Use provided config or default
        strategy_config = config or self._default_config

        # Validate input
        if not text or not text.strip():
            raise ValueError("Cannot chunk empty text")

        # Ensure we're using the FIXED strategy type
        if strategy_config.strategy != ChunkStrategyType.FIXED:
            logger.warning(
                "fixed_chunking_strategy_mismatch",
                expected=ChunkStrategyType.FIXED,
                actual=strategy_config.strategy,
            )
            # Continue anyway - the config might have been set elsewhere

        log = logger.bind(
            strategy="fixed",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("fixed_chunking_start")

        try:
            # Extract words from text
            words = _WORD_PATTERN.findall(text)

            if not words:
                return []

            chunks = []
            chunk_index = 0
            i = 0
            start_char_pos = 0
            total_char_pos = 0

            while i < len(words):
                # Determine end of this chunk
                end_idx = min(i + strategy_config.chunk_size, len(words))

                # Extract chunk words
                chunk_words = words[i:end_idx]
                chunk_text = " ".join(chunk_words)

                # Find character positions for metadata
                chunk_start = self._find_char_position(text, words, i)
                chunk_end = self._find_char_position(text, words, end_idx - 1) + len(words[end_idx - 1])

                # Create metadata
                metadata: dict[str, Any] = {
                    "strategy": "fixed",
                    "word_count": len(chunk_words),
                    "start_char": chunk_start,
                    "end_char": chunk_end,
                    "chunk_size": strategy_config.chunk_size,
                    "overlap": strategy_config.overlap,
                }

                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=chunk_index,
                        metadata=metadata,
                    )
                )

                chunk_index += 1
                # Move forward by effective chunk size (chunk_size - overlap)
                i += strategy_config.effective_chunk_size()

            log.info(
                "fixed_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error("fixed_chunking_error", error=str(e), error_type=type(e).__name__)
            raise ChunkingError(f"Fixed chunking failed: {e}", code="FIXED_CHUNKING_ERROR") from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """
        Check if this implementation supports a given strategy type.

        Args:
            strategy_type: The strategy type identifier

        Returns:
            True if strategy_type is "fixed" (case-insensitive)
        """
        return strategy_type.lower() == ChunkStrategyType.FIXED.value

    def _find_char_position(self, text: str, words: list[str], word_index: int) -> int:
        """
        Find the character position of a word in the original text.

        Args:
            text: Original text
            words: List of words extracted from text
            word_index: Index of word to find

        Returns:
            Character position where the word starts
        """
        if word_index >= len(words):
            return len(text)
        if word_index < 0:
            return 0

        target_word = words[word_index]
        words_found = 0

        for match in _WORD_PATTERN.finditer(text):
            if words_found == word_index:
                if match.group() == target_word:
                    return match.start()
            words_found += 1

        # Fallback: search from estimated position
        estimated_pos = (word_index * 5)  # Rough estimate
        search_start = max(0, estimated_pos - 50)
        found_pos = text.find(target_word, search_start)
        return max(0, found_pos)


__all__ = [
    "FixedChunkingStrategy",
]
