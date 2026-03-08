"""
Paragraph Boundary Chunking Strategy

Implements paragraph-aware chunking with configurable overlap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from ....application.ports.i_chunking_strategy import Chunk, ChunkingError
from ....domain.models.chunking_strategy import ChunkingStrategy, ChunkStrategyType
from ..base import _PARAGRAPH_DELIM, _WORD_PATTERN, BaseChunkingStrategy
from .fixed_size import FixedSizeStrategy as FixedSizeStrategy

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


class ParagraphBoundaryStrategy(BaseChunkingStrategy):
    """
    Paragraph-aware chunking strategy adapter.

    Splits text into chunks at paragraph boundaries with configurable overlap.
    Preserves paragraph integrity for document structure.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)

    Why paragraph-aware:
        - Preserves document structure
        - Groups related sentences together
        - Better for structured documents
        - Maintains thematic coherence

    Example:
        >>> strategy = ParagraphBoundaryStrategy()
        >>> chunks = await strategy.chunk(
        ...     "Para one.\\n\\nPara two.\\n\\nPara three.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.PARAGRAPH)
        ... )
        >>> len(chunks)
        3
    """

    def __init__(self, default_config: ChunkingStrategy | None = None) -> None:
        """
        Initialize the paragraph chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
        """
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=500,
            overlap=50,
        )

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into paragraph-aware chunks with overlap.

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

        if strategy_config.strategy != ChunkStrategyType.PARAGRAPH:
            logger.warning(
                "paragraph_chunking_strategy_mismatch",
                expected=ChunkStrategyType.PARAGRAPH,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="paragraph",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("paragraph_chunking_start")

        try:
            # Split by paragraph delimiters
            paragraphs: list[tuple[int, int]] = []
            last_end = 0

            for match in _PARAGRAPH_DELIM.finditer(text):
                end_pos = match.end() - len(match.group())  # Exclude delimiter
                paragraphs.append((last_end, end_pos))
                last_end = match.end()

            # Add remaining text
            if last_end < len(text.strip()):
                paragraphs.append((last_end, len(text)))

            # If no paragraph breaks found, fall back to fixed chunking
            if not paragraphs:
                log.info("paragraph_chunking_no_breaks", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            chunks: list[Any] = []
            current_paragraphs: list[tuple[int, int]] = []
            current_word_count = 0
            chunk_index = 0

            for start, end in paragraphs:
                para_text = text[start:end].strip()
                if not para_text:
                    continue

                para_words = len(_WORD_PATTERN.findall(para_text))

                if current_word_count + para_words > strategy_config.chunk_size:
                    if current_paragraphs:
                        # Create chunk
                        chunk_start = current_paragraphs[0][0]
                        chunk_end = current_paragraphs[-1][1]
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

                    # Keep overlap paragraphs
                    overlap_to_keep: list[tuple[int, int]] = []
                    overlap_count = 0
                    overlap_limit = strategy_config.overlap or 0
                    for p_start, p_end in reversed(current_paragraphs):
                        p_words = len(_WORD_PATTERN.findall(text[p_start:p_end]))
                        if overlap_count + p_words <= overlap_limit:
                            overlap_to_keep.insert(0, (p_start, p_end))
                            overlap_count += p_words
                        else:
                            break

                    current_paragraphs = overlap_to_keep
                    current_word_count = overlap_count

                current_paragraphs.append((start, end))
                current_word_count += para_words

            # Add final chunk
            if current_paragraphs:
                chunk_start = current_paragraphs[0][0]
                chunk_end = current_paragraphs[-1][1]
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
                "paragraph_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error(
                "paragraph_chunking_error", error=str(e), error_type=type(e).__name__
            )
            raise ChunkingError(
                f"Paragraph chunking failed: {e}", code="PARAGRAPH_CHUNKING_ERROR"
            ) from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'paragraph' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.PARAGRAPH.value

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
            "strategy": "paragraph",
            "word_count": word_count,
            "start_char": start_pos,
            "end_char": end_pos,
            "chunk_size": config.chunk_size,
            "overlap": config.overlap,
        }
        return Chunk(text=content, index=index, metadata=metadata)

    async def _fallback_fixed(self, text: str, config: ChunkingStrategy) -> list[Chunk]:
        """Fallback to fixed chunking if no paragraph breaks found."""
        fixed_strategy = FixedSizeStrategy(default_config=config)
        # Convert to PARAGRAPH type config for fixed strategy
        fixed_config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )
        chunks = await fixed_strategy.chunk(text, fixed_config)
        # Update metadata to reflect paragraph strategy was attempted
        for chunk in chunks:
            chunk.metadata["strategy"] = "paragraph_fixed_fallback"
        return chunks
