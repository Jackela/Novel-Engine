"""
Sentence Boundary Chunking Strategy

Implements sentence-aware chunking with configurable overlap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from ....application.ports.i_chunking_strategy import Chunk, ChunkingError
from ....domain.models.chunking_strategy import ChunkingStrategy, ChunkStrategyType
from ..base import _SENTENCE_END, _WORD_PATTERN, BaseChunkingStrategy
from .fixed_size import FixedSizeStrategy as FixedSizeStrategy

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


class SentenceBoundaryStrategy(BaseChunkingStrategy):
    """
    Sentence-aware chunking strategy adapter.

    Splits text into chunks at sentence boundaries with configurable overlap.
    Preserves sentence integrity for better semantic coherence.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)

    Why sentence-aware:
        - Preserves natural language boundaries
        - Better semantic coherence than fixed-size
        - Avoids mid-sentence breaks
        - Ideal for narrative text and dialogue

    Example:
        >>> strategy = SentenceBoundaryStrategy()
        >>> chunks = await strategy.chunk(
        ...     "This is sentence one. This is sentence two.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.SENTENCE)
        ... )
        >>> len(chunks)
        1
    """

    def __init__(self, default_config: ChunkingStrategy | None = None) -> None:
        """
        Initialize the sentence chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
        """
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=500,
            overlap=50,
        )

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into sentence-aware chunks with overlap.

        Args:
            text: Source text to chunk
            config: Optional chunking configuration (uses defaults if None)

        Returns:
            List of Chunk entities with text, index, and metadata

        Raises:
            ChunkingError: If chunking fails
            ValueError: If text is empty or configuration is invalid
        """
        strategy_config = config or self._default_config

        if not text or not text.strip():
            raise ValueError("Cannot chunk empty text")

        if strategy_config.strategy != ChunkStrategyType.SENTENCE:
            logger.warning(
                "sentence_chunking_strategy_mismatch",
                expected=ChunkStrategyType.SENTENCE,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="sentence",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("sentence_chunking_start")

        try:
            # Find all sentence boundaries
            sentences: list[tuple[int, int]] = []
            last_end = 0

            for match in _SENTENCE_END.finditer(text):
                end_pos = match.end()
                sentences.append((last_end, end_pos))
                last_end = end_pos

            # Add remaining text as last sentence if any
            if last_end < len(text.strip()):
                sentences.append((last_end, len(text)))

            # If no sentence breaks found, fall back to fixed chunking
            if not sentences:
                log.info("sentence_chunking_no_breaks", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            chunks: list[Any] = []
            current_sentences: list[tuple[int, int]] = []
            current_word_count = 0
            chunk_index = 0

            for start, end in sentences:
                sentence_text = text[start:end].strip()
                if not sentence_text:
                    continue

                sentence_words = len(_WORD_PATTERN.findall(sentence_text))

                # Check if adding this sentence would exceed chunk size
                if current_word_count + sentence_words > strategy_config.chunk_size:
                    if current_sentences:
                        # Create chunk from accumulated sentences
                        chunk_start = current_sentences[0][0]
                        chunk_end = current_sentences[-1][1]
                        chunk_content = text[chunk_start:chunk_end].strip()

                        chunks.append(
                            self._create_chunk(
                                chunk_content,
                                chunk_index,
                                chunk_start,
                                chunk_end,
                                current_word_count,
                                strategy_config,
                            )
                        )
                        chunk_index += 1

                    # Keep overlap sentences for next chunk
                    overlap_to_keep: list[tuple[int, int]] = []
                    overlap_count = 0
                    # Walk backwards from the end of current sentences
                    for s_start, s_end in reversed(current_sentences):
                        s_words = len(_WORD_PATTERN.findall(text[s_start:s_end]))
                        if overlap_count + s_words <= strategy_config.overlap:
                            overlap_to_keep.insert(0, (s_start, s_end))
                            overlap_count += s_words
                        else:
                            break

                    current_sentences = overlap_to_keep
                    current_word_count = overlap_count

                current_sentences.append((start, end))
                current_word_count += sentence_words

            # Add final chunk if any sentences remain
            if current_sentences:
                chunk_start = current_sentences[0][0]
                chunk_end = current_sentences[-1][1]
                chunk_content = text[chunk_start:chunk_end].strip()

                chunks.append(
                    self._create_chunk(
                        chunk_content,
                        chunk_index,
                        chunk_start,
                        chunk_end,
                        current_word_count,
                        strategy_config,
                    )
                )

            if not chunks:
                # Fallback if something went wrong
                return await self._fallback_fixed(text, strategy_config)

            log.info(
                "sentence_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error(
                "sentence_chunking_error", error=str(e), error_type=type(e).__name__
            )
            raise ChunkingError(
                f"Sentence chunking failed: {e}", code="SENTENCE_CHUNKING_ERROR"
            ) from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'sentence' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.SENTENCE.value

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        word_count: int,
        config: ChunkingStrategy,
    ) -> Chunk:
        """Create a Chunk entity with metadata."""
        metadata: dict[str, Any] = {
            "strategy": "sentence",
            "word_count": word_count,
            "start_char": start_pos,
            "end_char": end_pos,
            "chunk_size": config.chunk_size,
            "overlap": config.overlap,
        }
        return Chunk(text=content, index=index, metadata=metadata)

    async def _fallback_fixed(self, text: str, config: ChunkingStrategy) -> list[Chunk]:
        """Fallback to fixed chunking if no sentence breaks found."""
        fixed_strategy = FixedSizeStrategy(default_config=config)
        # Convert to SENTENCE type config for fixed strategy
        fixed_config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )
        chunks = await fixed_strategy.chunk(text, fixed_config)
        # Update metadata to reflect sentence strategy was attempted
        for chunk in chunks:
            chunk.metadata["strategy"] = "sentence_fixed_fallback"
        return chunks
