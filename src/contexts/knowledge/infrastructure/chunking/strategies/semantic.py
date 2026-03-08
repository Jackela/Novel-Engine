"""
Semantic Similarity Chunking Strategy

Implements semantic-aware chunking using embeddings to group
semantically related sentences into chunks.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import structlog

from ....application.ports.i_chunking_strategy import Chunk, ChunkingError
from ....domain.models.chunking_strategy import ChunkingStrategy, ChunkStrategyType
from ..base import _SENTENCE_END, _WORD_PATTERN, BaseChunkingStrategy
from .fixed_size import FixedSizeStrategy as FixedSizeStrategy

if TYPE_CHECKING:
    from ....application.ports.i_embedding_service import IEmbeddingService

logger = structlog.get_logger()


class SemanticSimilarityStrategy(BaseChunkingStrategy):
    """
    Semantic-aware chunking strategy adapter.

    Groups semantically related sentences into chunks using embeddings.
    Maintains narrative coherence by grouping sentences that discuss
    similar topics or themes.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)
        - similarity_threshold: Minimum cosine similarity to group sentences (default: 0.75)
        - max_sentences_per_chunk: Maximum sentences in a semantic group (default: 10)

    Why semantic chunking:
        - Groups related content regardless of sentence boundaries
        - Preserves thematic coherence better than fixed-size approaches
        - Ideal for narrative text with shifting topics
        - Better retrieval quality for RAG applications

    Algorithm:
        1. Split text into sentences
        2. Generate embeddings for each sentence
        3. Group sentences by semantic similarity using cosine similarity
        4. Create chunks from semantically coherent groups
        5. Apply overlap between chunks for context continuity

    Example:
        >>> strategy = SemanticSimilarityStrategy(embedding_service=service)
        >>> chunks = await strategy.chunk(
        ...     "The warrior entered. The castle was dark. Meanwhile, the princess waited.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.SEMANTIC)
        ... )
        >>> len(chunks)
        2
    """

    # Default semantic chunking parameters
    DEFAULT_SIMILARITY_THRESHOLD = 0.75
    DEFAULT_MAX_SENTENCES_PER_CHUNK = 10
    DEFAULT_MIN_SENTENCES_PER_CHUNK = 2

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        default_config: ChunkingStrategy | None = None,
    ) -> None:
        """
        Initialize the semantic chunking strategy.

        Args:
            embedding_service: Service for generating text embeddings
            default_config: Default configuration to use when none is provided
        """
        self._embedding_service = embedding_service
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=500,
            overlap=50,
        )

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into semantically coherent chunks.

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

        if strategy_config.strategy != ChunkStrategyType.SEMANTIC:
            logger.warning(
                "semantic_chunking_strategy_mismatch",
                expected=ChunkStrategyType.SEMANTIC,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="semantic",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("semantic_chunking_start")

        try:
            # Step 1: Split text into sentences
            sentences = self._split_into_sentences(text)
            if not sentences:
                log.info("semantic_chunking_no_sentences", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            # Step 2: Generate embeddings for all sentences
            sentence_texts = [s[2] for s in sentences]
            embeddings = await self._embedding_service.embed_batch(sentence_texts)

            # Step 3: Group sentences by semantic similarity
            semantic_groups = self._group_by_similarity(
                sentences,
                embeddings,
                strategy_config,
            )

            # Step 4: Create chunks from semantic groups
            chunks = await self._create_chunks_from_groups(
                text,
                semantic_groups,
                strategy_config,
            )

            if not chunks:
                # Fallback if something went wrong
                log.info("semantic_chunking_no_chunks", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            log.info(
                "semantic_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error(
                "semantic_chunking_error", error=str(e), error_type=type(e).__name__
            )
            raise ChunkingError(
                f"Semantic chunking failed: {e}", code="SEMANTIC_CHUNKING_ERROR"
            ) from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'semantic' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.SEMANTIC.value

    def _split_into_sentences(self, text: str) -> list[tuple[int, int, str]]:
        """
        Split text into sentences with position tracking.

        Args:
            text: Source text

        Returns:
            List of (start_pos, end_pos, sentence_text) tuples
        """
        sentences: list[tuple[int, int, str]] = []
        last_end = 0

        for match in _SENTENCE_END.finditer(text):
            end_pos = match.end()
            sentence_text = text[last_end:end_pos].strip()
            if sentence_text:
                sentences.append((last_end, end_pos, sentence_text))
            last_end = end_pos

        # Add remaining text as last sentence
        if last_end < len(text.strip()):
            remaining = text[last_end:].strip()
            if remaining:
                sentences.append((last_end, len(text), remaining))

        return sentences

    def _group_by_similarity(
        self,
        sentences: list[tuple[int, int, str]],
        embeddings: list[list[float]],
        config: ChunkingStrategy,
    ) -> list[list[tuple[int, int, str]]]:
        """
        Group sentences by semantic similarity.

        Uses cosine similarity to determine sentence relatedness.
        Sentences are grouped when similarity exceeds threshold.

        Args:
            sentences: List of (start, end, text) tuples
            embeddings: List of embedding vectors for each sentence
            config: Chunking configuration

        Returns:
            List of sentence groups, where each group is a list of sentences
        """
        if not sentences:
            return []

        groups: list[list[tuple[int, int, str]]] = []
        current_group: list[tuple[int, int, str]] = [sentences[0]]

        # Use default similarity threshold (could be made configurable)
        similarity_threshold = self.DEFAULT_SIMILARITY_THRESHOLD
        max_sentences = self.DEFAULT_MAX_SENTENCES_PER_CHUNK

        for i in range(1, len(sentences)):
            sentence = sentences[i]
            current_embedding = embeddings[i]

            # Calculate similarity with last sentence in current group
            last_idx = sentences.index(current_group[-1])
            last_embedding = embeddings[last_idx]

            similarity = self._cosine_similarity(current_embedding, last_embedding)

            # Check word count of current group
            group_text = " ".join(s[2] for s in current_group)
            group_words = len(_WORD_PATTERN.findall(group_text))

            # Decide whether to start a new group
            should_start_new = (
                similarity < similarity_threshold
                or len(current_group) >= max_sentences
                or group_words >= config.chunk_size
            )

            if should_start_new and current_group:
                # Save current group and start new one
                groups.append(current_group)
                current_group = [sentence]
            else:
                # Add to current group
                current_group.append(sentence)

        # Add final group
        if current_group:
            groups.append(current_group)

        return groups

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _create_chunks_from_groups(
        self,
        original_text: str,
        semantic_groups: list[list[tuple[int, int, str]]],
        config: ChunkingStrategy,
    ) -> list[Chunk]:
        """
        Create Chunk entities from semantic groups with overlap.

        Args:
            original_text: Full source text
            semantic_groups: Groups of related sentences
            config: Chunking configuration

        Returns:
            List of Chunk entities
        """
        chunks: list[Chunk] = []
        chunk_index = 0

        for group in semantic_groups:
            # Get group text bounds
            start_pos = group[0][0]
            end_pos = group[-1][1]

            # Apply overlap by including sentences from previous group
            overlap_limit = config.overlap or 0
            if chunk_index > 0 and overlap_limit > 0:
                overlap_words = overlap_limit
                # Find sentences to include for overlap
                overlap_sentences = self._get_overlap_sentences(
                    semantic_groups[chunk_index - 1],
                    overlap_words,
                )
                if overlap_sentences:
                    start_pos = overlap_sentences[0][0]

            chunk_text = original_text[start_pos:end_pos].strip()
            word_count = len(_WORD_PATTERN.findall(chunk_text))

            if word_count < config.min_chunk_size:
                # Merge with next group if too small
                if chunk_index + 1 < len(semantic_groups):
                    next_group = semantic_groups[chunk_index + 1]
                    end_pos = next_group[-1][1]
                    chunk_text = original_text[start_pos:end_pos].strip()
                    word_count = len(_WORD_PATTERN.findall(chunk_text))

            # Skip if still too small (unless it's the only chunk)
            if word_count < config.min_chunk_size and len(chunks) > 0:
                continue

            metadata: dict[str, Any] = {
                "strategy": "semantic",
                "word_count": word_count,
                "start_char": start_pos,
                "end_char": end_pos,
                "chunk_size": config.chunk_size,
                "overlap": config.overlap,
                "sentence_count": len(group),
            }

            chunks.append(
                Chunk(
                    text=chunk_text,
                    index=chunk_index,
                    metadata=metadata,
                )
            )

            chunk_index += 1

        return chunks

    def _get_overlap_sentences(
        self,
        prev_group: list[tuple[int, int, str]],
        overlap_words: int,
    ) -> list[tuple[int, int, str]]:
        """
        Get sentences from previous group for overlap.

        Args:
            prev_group: Previous sentence group
            overlap_words: Desired overlap word count

        Returns:
            List of sentences to include for overlap
        """
        if not prev_group:
            return []

        # Take sentences from the end of previous group
        overlap_sentences: list[tuple[int, int, str]] = []
        word_count = 0

        for sentence in reversed(prev_group):
            sent_words = len(_WORD_PATTERN.findall(sentence[2]))
            if word_count + sent_words <= overlap_words:
                overlap_sentences.insert(0, sentence)
                word_count += sent_words
            else:
                break

        return overlap_sentences

    async def _fallback_fixed(self, text: str, config: ChunkingStrategy) -> list[Chunk]:
        """Fallback to fixed chunking if semantic chunking fails."""
        fixed_strategy = FixedSizeStrategy(default_config=config)
        fixed_config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )
        chunks = await fixed_strategy.chunk(text, fixed_config)
        for chunk in chunks:
            chunk.metadata["strategy"] = "semantic_fixed_fallback"
        return chunks
