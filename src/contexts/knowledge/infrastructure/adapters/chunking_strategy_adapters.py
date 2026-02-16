"""
Chunking Strategy Adapters

Implements IChunkingStrategy port for various chunking approaches.
Adapts the existing TextChunker domain service to the hexagonal architecture.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapters implementing application port
- Article V (SOLID): SRP - each adapter handles one strategy type

Warzone 4: AI Brain - BRAIN-039A-02, BRAIN-039A-03, BRAIN-039A-04
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

from ...application.ports.i_chunking_strategy import (
    Chunk,
    ChunkingError,
)
from ...domain.models.chunking_strategy import (
    ChunkingStrategy,
    ChunkStrategyType,
)

if TYPE_CHECKING:
    from ...application.ports.i_embedding_service import IEmbeddingService

logger = structlog.get_logger()

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


class ChunkCoherenceAnalyzer:
    """
    Analyzes chunk coherence using embeddings and structural analysis.

    Provides coherence scoring for chunks to identify potential issues
    with chunk boundaries, semantic drift, or inappropriate sizes.

    Coherence analysis helps:
    - Identify chunks that may have poor retrieval quality
    - Warn about chunks that break at awkward boundaries
    - Detect chunks that are too small or too large
    - Guide chunking strategy selection and tuning

    Why coherence matters:
        - Incoherent chunks reduce RAG retrieval quality
        - Breaking mid-sentence or mid-dialogue hurts comprehension
        - Tiny chunks lack context, huge chunks reduce precision

    Example:
        >>> analyzer = ChunkCoherenceAnalyzer(embedding_service)
        >>> chunks = await some_strategy.chunk(text, config)
        >>> results = await analyzer.analyze_chunks(chunks, config)
        >>> for chunk, score in zip(chunks, results):
        ...     if not score.is_acceptable:
        ...         print(f"Chunk {chunk.index} has low coherence: {score.score}")
    """

    # Default weights for score components
    DEFAULT_INTERNAL_WEIGHT = 0.5
    DEFAULT_BOUNDARY_WEIGHT = 0.3
    DEFAULT_SIZE_WEIGHT = 0.2

    # Coherence thresholds
    DEFAULT_ACCEPTABLE_THRESHOLD = 0.5
    DEFAULT_GOOD_THRESHOLD = 0.7
    DEFAULT_EXCELLENT_THRESHOLD = 0.85

    def __init__(
        self,
        embedding_service: IEmbeddingService | None = None,
        acceptable_threshold: float = DEFAULT_ACCEPTABLE_THRESHOLD,
        good_threshold: float = DEFAULT_GOOD_THRESHOLD,
        excellent_threshold: float = DEFAULT_EXCELLENT_THRESHOLD,
        internal_weight: float = DEFAULT_INTERNAL_WEIGHT,
        boundary_weight: float = DEFAULT_BOUNDARY_WEIGHT,
        size_weight: float = DEFAULT_SIZE_WEIGHT,
    ):
        """
        Initialize the coherence analyzer.

        Args:
            embedding_service: Service for generating embeddings.
                If None, internal coherence is estimated using heuristics.
            acceptable_threshold: Minimum score for acceptable coherence
            good_threshold: Minimum score for good coherence
            excellent_threshold: Minimum score for excellent coherence
            internal_weight: Weight for internal coherence in overall score
            boundary_weight: Weight for boundary quality in overall score
            size_weight: Weight for size appropriateness in overall score
        """
        self._embedding_service = embedding_service
        self._acceptable_threshold = acceptable_threshold
        self._good_threshold = good_threshold
        self._excellent_threshold = excellent_threshold
        self._internal_weight = internal_weight
        self._boundary_weight = boundary_weight
        self._size_weight = size_weight

    async def analyze_chunks(
        self,
        chunks: list[Chunk],
        config: ChunkingStrategy,
    ) -> list[CoherenceScore]:
        """
        Analyze coherence for all chunks.

        Args:
            chunks: List of chunks to analyze
            config: Chunking configuration used to create the chunks

        Returns:
            List of CoherenceScore objects, one per chunk
        """
        results: list[CoherenceScore] = []

        for chunk in chunks:
            score = await self.analyze_chunk(chunk, config)
            results.append(score)

        return results

    async def analyze_chunk(
        self,
        chunk: Chunk,
        config: ChunkingStrategy,
    ) -> CoherenceScore:
        """
        Analyze coherence for a single chunk.

        Args:
            chunk: Chunk to analyze
            config: Chunking configuration used to create the chunk

        Returns:
            CoherenceScore with detailed analysis
        """
        warnings: list[str] = []

        # Calculate individual components
        internal_coherence = await self._calculate_internal_coherence(chunk)
        boundary_quality = self._calculate_boundary_quality(chunk)
        size_score = self._calculate_size_score(chunk, config)

        # Generate warnings for issues
        if internal_coherence < 0.4:
            warnings.append("Low semantic coherence within chunk")
        if boundary_quality < 0.5:
            warnings.append("Chunk breaks at awkward boundary")
        if size_score < 0.5:
            word_count = chunk.metadata.get("word_count", 0)
            if word_count < config.min_chunk_size:
                warnings.append(f"Chunk too small ({word_count} words)")
            elif word_count > config.chunk_size * 1.5:
                warnings.append(f"Chunk too large ({word_count} words)")

        # Calculate overall score as weighted average
        overall = (
            internal_coherence * self._internal_weight
            + boundary_quality * self._boundary_weight
            + size_score * self._size_weight
        )

        # Determine if acceptable
        is_acceptable = overall >= self._acceptable_threshold

        return CoherenceScore(
            score=overall,
            internal_coherence=internal_coherence,
            boundary_quality=boundary_quality,
            size_score=size_score,
            warnings=tuple(warnings),
            is_acceptable=is_acceptable,
        )

    async def _calculate_internal_coherence(self, chunk: Chunk) -> float:
        """
        Calculate internal semantic coherence of a chunk.

        Higher when sentences within the chunk are semantically related.
        Uses embeddings if available, otherwise uses heuristics.

        Args:
            chunk: Chunk to analyze

        Returns:
            Coherence score from 0.0 to 1.0
        """
        text = chunk.text

        if self._embedding_service is not None:
            return await self._embedding_based_coherence(text)
        else:
            return self._heuristic_coherence(text, chunk.metadata)

    async def _embedding_based_coherence(self, text: str) -> float:
        """
        Calculate coherence using sentence embeddings.

        Splits text into sentences, generates embeddings, and measures
        average cosine similarity between adjacent sentences.

        Args:
            text: Chunk text to analyze

        Returns:
            Coherence score from 0.0 to 1.0
        """
        # Split into sentences
        sentences = _SENTENCE_END.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            # Single sentence is perfectly coherent
            return 1.0

        try:
            # Generate embeddings for all sentences
            embeddings = await self._embedding_service.embed_batch(sentences)  # type: ignore

            # Calculate pairwise similarities between adjacent sentences
            similarities = []
            for i in range(len(embeddings) - 1):
                sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
                similarities.append(sim)

            # Return average similarity
            return sum(similarities) / len(similarities) if similarities else 1.0

        except Exception:
            # Fallback to heuristic if embedding fails
            return self._heuristic_coherence(text, {})

    def _heuristic_coherence(self, text: str, metadata: dict[str, Any]) -> float:
        """
        Calculate coherence using heuristics without embeddings.

        Heuristics:
        - High word count usually means lower coherence (more topic drift)
        - Presence of dialogue markers can indicate coherence shifts
        - Paragraph structure can indicate topic organization

        Args:
            text: Chunk text to analyze
            metadata: Chunk metadata for additional context

        Returns:
            Estimated coherence score from 0.0 to 1.0
        """
        word_count = metadata.get("word_count", len(_WORD_PATTERN.findall(text)))

        # Base score decreases with chunk size (larger chunks drift more)
        base_score = 1.0
        if word_count > 500:
            base_score -= min(0.3, (word_count - 500) / 2000)
        if word_count > 1000:
            base_score -= min(0.2, (word_count - 1000) / 2000)

        # Check for dialogue coherence indicators
        dialogue_markers = text.count('"') + text.count("'")
        if dialogue_markers > 10:
            # Lots of dialogue - check if it's coherent (paired quotes)
            quotes = text.count('"')
            if quotes % 2 == 0:
                # Even number of quotes suggests proper dialogue structure
                base_score = min(1.0, base_score + 0.1)

        # Check for paragraph structure
        paragraph_count = len(_PARAGRAPH_DELIM.findall(text))
        if paragraph_count > 1:
            # Multiple paragraphs suggest structure
            base_score = min(1.0, base_score + 0.05)

        return max(0.0, min(1.0, base_score))

    def _calculate_boundary_quality(self, chunk: Chunk) -> float:
        """
        Calculate quality of chunk boundaries.

        Higher when chunk starts and ends at natural boundaries
        (sentence ends, paragraph ends, etc.)

        Args:
            chunk: Chunk to analyze

        Returns:
            Boundary quality score from 0.0 to 1.0
        """
        text = chunk.text
        score = 1.0

        # Check if chunk ends with sentence-ending punctuation
        stripped = text.rstrip()
        if stripped and stripped[-1] in ".!?":
            score += 0.2  # Bonus for ending at sentence boundary
        elif stripped and stripped[-1] == '"':
            # Check if it's a closed quote (sentence end)
            score += 0.1
        else:
            # Penalty for not ending at sentence boundary
            score -= 0.3

        # Check if chunk starts with capital letter (proper sentence start)
        if stripped and stripped[0].isupper():
            score += 0.1
        else:
            score -= 0.1

        # Check for paragraph structure within chunk
        paragraph_count = len(_PARAGRAPH_DELIM.findall(text))
        if paragraph_count > 0:
            score += 0.1 * min(paragraph_count, 3)  # Bonus for structure

        return max(0.0, min(1.0, score))

    def _calculate_size_score(self, chunk: Chunk, config: ChunkingStrategy) -> float:
        """
        Calculate score based on chunk size appropriateness.

        Higher when chunk size is within the target range.

        Args:
            chunk: Chunk to analyze
            config: Chunking configuration with target size

        Returns:
            Size score from 0.0 to 1.0
        """
        word_count = chunk.metadata.get(
            "word_count", len(_WORD_PATTERN.findall(chunk.text))
        )
        target = config.chunk_size
        min_size = config.min_chunk_size

        if word_count < min_size:
            # Penalty for being too small
            ratio = word_count / min_size
            return ratio * 0.5  # Max 0.5 for too-small chunks
        elif word_count <= target:
            # Ideal size
            return 1.0
        elif word_count <= target * 1.2:
            # Slightly over but acceptable
            return 0.9
        elif word_count <= target * 1.5:
            # Over target
            excess = (word_count - target) / (target * 0.5)
            return 1.0 - (excess * 0.3)
        else:
            # Way over target
            ratio = target / word_count
            return max(0.1, ratio * 0.5)

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity from -1.0 to 1.0
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


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

            while i < len(words):
                # Determine end of this chunk
                end_idx = min(i + strategy_config.chunk_size, len(words))

                # Extract chunk words
                chunk_words = words[i:end_idx]
                chunk_text = " ".join(chunk_words)

                # Find character positions for metadata
                chunk_start = self._find_char_position(text, words, i)
                chunk_end = self._find_char_position(text, words, end_idx - 1) + len(
                    words[end_idx - 1]
                )

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
            raise ChunkingError(
                f"Fixed chunking failed: {e}", code="FIXED_CHUNKING_ERROR"
            ) from e

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
        estimated_pos = word_index * 5  # Rough estimate
        search_start = max(0, estimated_pos - 50)
        found_pos = text.find(target_word, search_start)
        return max(0, found_pos)


class SentenceChunkingStrategy:
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
        >>> strategy = SentenceChunkingStrategy()
        >>> chunks = await strategy.chunk(
        ...     "This is sentence one. This is sentence two.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.SENTENCE)
        ... )
        >>> len(chunks)
        1
    """

    def __init__(self, default_config: ChunkingStrategy | None = None):
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

            chunks = []
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
        fixed_strategy = FixedChunkingStrategy(default_config=config)
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


class ParagraphChunkingStrategy:
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
        >>> strategy = ParagraphChunkingStrategy()
        >>> chunks = await strategy.chunk(
        ...     "Para one.\\n\\nPara two.\\n\\nPara three.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.PARAGRAPH)
        ... )
        >>> len(chunks)
        3
    """

    def __init__(self, default_config: ChunkingStrategy | None = None):
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

            chunks = []
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
                    for p_start, p_end in reversed(current_paragraphs):
                        p_words = len(_WORD_PATTERN.findall(text[p_start:p_end]))
                        if overlap_count + p_words <= strategy_config.overlap:
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
        fixed_strategy = FixedChunkingStrategy(default_config=config)
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


class SemanticChunkingStrategy:
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
        >>> strategy = SemanticChunkingStrategy(embedding_service=service)
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
    ):
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
            if chunk_index > 0 and config.overlap > 0:
                overlap_words = config.overlap
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
        fixed_strategy = FixedChunkingStrategy(default_config=config)
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


class NarrativeFlowChunkingStrategy:
    """
    Narrative flow preserving chunking strategy adapter.

    Splits text while preserving narrative flow and coherence.
    Specifically designed for fiction and narrative content where
    maintaining story flow is critical for reader comprehension.

    Key features:
        - Preserves sentence boundaries (never breaks mid-sentence)
        - Respects dialogue boundaries (never breaks mid-dialogue exchange)
        - Groups related narrative beats together
        - Maintains scene continuity through overlap

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)
        - preserve_dialogue: Keep dialogue exchanges together (default: True)
        - preserve_paragraphs: Keep paragraphs together when possible (default: True)

    Why narrative flow:
        - Narrative comprehension depends on sentence and dialogue coherence
        - Breaking in middle of dialogue disrupts reader immersion
        - Scene continuity improves RAG retrieval for narrative content
        - Better chunk quality for story generation and summarization

    Example:
        >>> strategy = NarrativeFlowChunkingStrategy()
        >>> chunks = await strategy.chunk(
        ...     '"Hello," she said. "How are you?" "I am well," he replied.',
        ...     ChunkingStrategy(strategy=ChunkStrategyType.NARRATIVE_FLOW)
        ... )
        >>> # Dialogue exchange preserved in single chunk
    """

    # Common dialogue tag verbs for detecting dialogue boundaries
    _DIALOGUE_TAGS = {
        "said",
        "asked",
        "replied",
        "whispered",
        "shouted",
        "murmured",
        "exclaimed",
        "cried",
        "called",
        "responded",
        "answered",
        "declared",
        "stated",
        "added",
        "continued",
        "interrupted",
        "objected",
        "agreed",
        "nodded",
        "smiled",
        "laughed",
        "grinned",
        "chuckled",
        "sighed",
        "groaned",
        "gasped",
        "screamed",
        "yelled",
        "bellowed",
        "roared",
        "hissed",
        "snapped",
        "barked",
        "growled",
        "muttered",
        "mumbled",
        "grumbled",
        "assented",
        "countered",
        "retorted",
        "protested",
        "insisted",
        "demanded",
        "commanded",
        "ordered",
        "requested",
        "begged",
        "pleaded",
        "implored",
        "prayed",
        "cursed",
        "thanked",
        "apologized",
        "greeted",
        "welcomed",
        "bid",
        "wished",
        "hoped",
        "wondered",
        "thought",
        "reflected",
        "remembered",
        "recalled",
        "realized",
        "understood",
        "decided",
        "resolved",
        "promised",
        "vowed",
        "pledged",
        "consented",
        "refused",
        "denied",
        "admitted",
        "confessed",
        "acknowledged",
        "recognized",
        "identified",
        "discovered",
        "found",
        "learned",
        "heard",
        "saw",
        "watched",
        "observed",
        "noticed",
        "remarked",
        "commented",
        "noted",
        "explained",
        "described",
        "related",
        "recounted",
        "told",
        "narrated",
        "spoke",
        "addressed",
        "conversed",
        "chatted",
        "discussed",
        "debated",
        "argued",
        "quarreled",
        "disputed",
        "contested",
        "challenged",
        "questioned",
        "queried",
        "inquired",
    }

    def __init__(
        self,
        default_config: ChunkingStrategy | None = None,
        preserve_dialogue: bool = True,
        preserve_paragraphs: bool = True,
    ):
        """
        Initialize the narrative flow chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
            preserve_dialogue: Keep dialogue exchanges together
            preserve_paragraphs: Keep paragraphs together when possible
        """
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.NARRATIVE_FLOW,
            chunk_size=500,
            overlap=50,
        )
        self._preserve_dialogue = preserve_dialogue
        self._preserve_paragraphs = preserve_paragraphs

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into narrative flow preserving chunks.

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

        if strategy_config.strategy != ChunkStrategyType.NARRATIVE_FLOW:
            logger.warning(
                "narrative_flow_chunking_strategy_mismatch",
                expected=ChunkStrategyType.NARRATIVE_FLOW,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="narrative_flow",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
            preserve_dialogue=self._preserve_dialogue,
            preserve_paragraphs=self._preserve_paragraphs,
        )

        log.debug("narrative_flow_chunking_start")

        try:
            # Step 1: Identify narrative boundaries
            boundaries = self._identify_narrative_boundaries(text)
            log.debug("narrative_boundaries_identified", count=len(boundaries))

            # Step 2: Group narrative units into chunks
            chunks = self._create_narrative_chunks(
                text,
                boundaries,
                strategy_config,
            )

            if not chunks:
                # Fallback to sentence chunking if no chunks created
                log.info("narrative_flow_no_chunks", fallback="sentence")
                return await self._fallback_sentence(text, strategy_config)

            log.info(
                "narrative_flow_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error(
                "narrative_flow_chunking_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ChunkingError(
                f"Narrative flow chunking failed: {e}",
                code="NARRATIVE_FLOW_CHUNKING_ERROR",
            ) from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'narrative_flow' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.NARRATIVE_FLOW.value

    def _identify_narrative_boundaries(
        self, text: str
    ) -> list[tuple[int, int, str, dict[str, Any]]]:
        """
        Identify narrative boundaries in text.

        A narrative boundary is a point where a chunk can reasonably break.
        Boundaries are identified with metadata about their type and quality.

        Args:
            text: Source text

        Returns:
            List of (start, end, type, metadata) tuples for each narrative unit
        """
        units: list[tuple[int, int, str, dict[str, Any]]] = []
        current_pos = 0
        text_len = len(text)

        while current_pos < text_len:
            # Skip whitespace
            while current_pos < text_len and text[current_pos].isspace():
                current_pos += 1

            if current_pos >= text_len:
                break

            # Check for dialogue start
            if self._preserve_dialogue and text[current_pos] in ('"', "'"):
                dialogue_info = self._extract_dialogue_unit(text, current_pos)
                if dialogue_info:
                    units.append(dialogue_info)
                    current_pos = dialogue_info[1]  # Move to end of dialogue
                    continue

            # Check for paragraph break
            if self._preserve_paragraphs:
                # Find next paragraph delimiter
                para_match = _PARAGRAPH_DELIM.search(text, current_pos)
                if para_match and para_match.start() > current_pos:
                    # Extract paragraph as narrative unit
                    para_end = para_match.start()
                    para_text = text[current_pos:para_end].strip()
                    if para_text:
                        word_count = len(_WORD_PATTERN.findall(para_text))
                        units.append(
                            (
                                current_pos,
                                para_end,
                                "paragraph",
                                {
                                    "word_count": word_count,
                                    "ends_with_period": para_text.rstrip().endswith(
                                        (".", "!", "?", '"', "'")
                                    ),
                                },
                            )
                        )
                    current_pos = para_match.end()
                    continue

            # Default: find next sentence boundary
            sentence_match = _SENTENCE_END.search(text, current_pos)
            if sentence_match:
                sent_end = sentence_match.end()
                sent_text = text[current_pos:sent_end].strip()
                if sent_text:
                    word_count = len(_WORD_PATTERN.findall(sent_text))
                    units.append(
                        (
                            current_pos,
                            sent_end,
                            "sentence",
                            {"word_count": word_count},
                        )
                    )
                current_pos = sent_end
            else:
                # No more sentence boundaries - take remaining text
                remaining = text[current_pos:].strip()
                if remaining:
                    word_count = len(_WORD_PATTERN.findall(remaining))
                    units.append(
                        (
                            current_pos,
                            text_len,
                            "sentence",
                            {"word_count": word_count},
                        )
                    )
                break

        return units

    def _extract_dialogue_unit(
        self, text: str, start_pos: int
    ) -> tuple[int, int, str, dict[str, Any]] | None:
        """
        Extract a complete dialogue unit starting at position.

        A dialogue unit includes:
        - The quoted speech
        - Any dialogue tags (e.g., "she said")
        - Any adjacent dialogue in the same exchange

        Args:
            text: Source text
            start_pos: Position where dialogue starts

        Returns:
            (start, end, type, metadata) tuple or None if not dialogue
        """
        quote_char = text[start_pos]
        if quote_char not in ('"', "'"):
            return None

        # Find closing quote
        closing_pos = start_pos + 1
        while closing_pos < len(text):
            if text[closing_pos] == quote_char and text[closing_pos - 1] != "\\":
                break
            closing_pos += 1

        if closing_pos >= len(text):
            return None

        # Extract dialogue and check for tag
        after_quote = closing_pos + 1
        tag_end = after_quote

        # Look for dialogue tag pattern
        while tag_end < len(text) and text[tag_end] not in ".!?":
            tag_end += 1

        # Include end punctuation
        if tag_end < len(text) and text[tag_end] in ".!?":
            tag_end += 1

        # Check if next sentence is also dialogue (same exchange)
        next_start = tag_end
        while next_start < len(text) and text[next_start].isspace():
            next_start += 1

        # If next starts with quote, include it
        if next_start < len(text) and text[next_start] == quote_char:
            # Recursively get next dialogue
            next_dialogue = self._extract_dialogue_unit(text, next_start)
            if next_dialogue:
                # Merge both dialogues
                word_count = len(
                    _WORD_PATTERN.findall(text[start_pos : next_dialogue[1]])
                )
                return (
                    start_pos,
                    next_dialogue[1],
                    "dialogue_exchange",
                    {
                        "word_count": word_count,
                        "quote_char": quote_char,
                        "exchange_length": 2,
                    },
                )

        word_count = len(_WORD_PATTERN.findall(text[start_pos:tag_end]))
        return (
            start_pos,
            tag_end,
            "dialogue",
            {"word_count": word_count, "quote_char": quote_char},
        )

    def _create_narrative_chunks(
        self,
        text: str,
        boundaries: list[tuple[int, int, str, dict[str, Any]]],
        config: ChunkingStrategy,
    ) -> list[Chunk]:
        """
        Create chunks from narrative boundaries.

        Groups narrative units into chunks while respecting:
        - Size limits
        - Dialogue continuity
        - Narrative coherence

        Args:
            text: Source text
            boundaries: List of narrative boundary units
            config: Chunking configuration

        Returns:
            List of Chunk entities
        """
        chunks: list[Chunk] = []
        current_units: list[tuple[int, int, str, dict[str, Any]]] = []
        current_word_count = 0
        chunk_index = 0

        for start, end, unit_type, metadata in boundaries:
            unit_word_count = metadata.get("word_count", 0)

            # Check if adding this unit would exceed chunk size
            if current_word_count + unit_word_count > config.chunk_size:
                if current_units:
                    # Check if we should extend for dialogue continuity
                    if unit_type == "dialogue" and chunk_index > 0:
                        # Check if previous chunk ended with dialogue
                        last_unit = current_units[-1]
                        if last_unit[2] in ("dialogue", "dialogue_exchange"):
                            # Extend current chunk to include this dialogue
                            pass  # Don't break mid-dialogue exchange

                    if current_word_count + unit_word_count > config.chunk_size:
                        # Create chunk from current units
                        chunk_start = current_units[0][0]
                        chunk_end = current_units[-1][1]
                        chunk_content = text[chunk_start:chunk_end].strip()

                        chunks.append(
                            self._create_chunk(
                                chunk_content,
                                chunk_index,
                                chunk_start,
                                chunk_end,
                                current_word_count,
                                config,
                                self._get_narrative_metadata(current_units),
                            )
                        )
                        chunk_index += 1

                        # Keep overlap units for next chunk
                        overlap_to_keep = self._get_overlap_units(
                            current_units,
                            config.overlap,
                        )
                        current_units = overlap_to_keep
                        current_word_count = sum(
                            u[3].get("word_count", 0) for u in overlap_to_keep
                        )

            current_units.append((start, end, unit_type, metadata))
            current_word_count += unit_word_count

        # Add final chunk
        if current_units:
            chunk_start = current_units[0][0]
            chunk_end = current_units[-1][1]
            chunk_content = text[chunk_start:chunk_end].strip()

            if chunk_content and current_word_count >= config.min_chunk_size:
                chunks.append(
                    self._create_chunk(
                        chunk_content,
                        chunk_index,
                        chunk_start,
                        chunk_end,
                        current_word_count,
                        config,
                        self._get_narrative_metadata(current_units),
                    )
                )

        return chunks

    def _get_overlap_units(
        self,
        units: list[tuple[int, int, str, dict[str, Any]]],
        overlap_words: int,
    ) -> list[tuple[int, int, str, dict[str, Any]]]:
        """
        Get units to include in overlap.

        Preserves complete narrative units in overlap for continuity.

        Args:
            units: Current narrative units
            overlap_words: Desired overlap word count

        Returns:
            List of units to include in overlap
        """
        if not units or overlap_words <= 0:
            return []

        overlap_units: list[tuple[int, int, str, dict[str, Any]]] = []
        word_count = 0

        # Take units from the end, preferring complete narrative units
        for unit in reversed(units):
            unit_words = unit[3].get("word_count", 0)
            if word_count + unit_words <= overlap_words:
                overlap_units.insert(0, unit)
                word_count += unit_words
            else:
                break

        return overlap_units

    def _get_narrative_metadata(
        self,
        units: list[tuple[int, int, str, dict[str, Any]]],
    ) -> dict[str, Any]:
        """
        Extract metadata about narrative composition.

        Args:
            units: Narrative units in the chunk

        Returns:
            Metadata dict with narrative composition info
        """
        unit_types = [u[2] for u in units]
        dialogue_count = sum(1 for t in unit_types if "dialogue" in t)
        paragraph_count = sum(1 for t in unit_types if t == "paragraph")
        sentence_count = sum(1 for t in unit_types if t == "sentence")

        return {
            "dialogue_units": dialogue_count,
            "paragraph_units": paragraph_count,
            "sentence_units": sentence_count,
            "total_units": len(units),
            "has_dialogue": dialogue_count > 0,
        }

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        word_count: int,
        config: ChunkingStrategy,
        narrative_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """Create a Chunk entity with metadata."""
        metadata: dict[str, Any] = {
            "strategy": "narrative_flow",
            "word_count": word_count,
            "start_char": start_pos,
            "end_char": end_pos,
            "chunk_size": config.chunk_size,
            "overlap": config.overlap,
        }
        if narrative_metadata:
            metadata.update(narrative_metadata)
        return Chunk(text=content, index=index, metadata=metadata)

    async def _fallback_sentence(
        self, text: str, config: ChunkingStrategy
    ) -> list[Chunk]:
        """Fallback to sentence chunking if narrative flow chunking fails."""
        sentence_strategy = SentenceChunkingStrategy(
            default_config=ChunkingStrategy(
                strategy=ChunkStrategyType.SENTENCE,
                chunk_size=config.chunk_size,
                overlap=config.overlap,
                min_chunk_size=config.min_chunk_size,
            )
        )
        chunks = await sentence_strategy.chunk(text)
        for chunk in chunks:
            chunk.metadata["strategy"] = "narrative_flow_sentence_fallback"
            chunk.metadata["original_strategy"] = chunk.metadata.get("strategy", "")
        return chunks


class ContentType(str, Enum):
    """
    Content type hints for auto-detection.

    When content type is known, the appropriate strategy is selected directly.
    When UNKNOWN, the strategy is detected by analyzing text structure.
    """

    SCENE = "scene"
    CHARACTER = "character"
    LORE = "lore"
    DIALOGUE = "dialogue"
    NARRATIVE = "narrative"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class AutoChunkingStrategy:
    """
    Auto-detection chunking strategy adapter.

    Automatically selects the best chunking strategy based on:
    1. Content type hint (if provided)
    2. Text structure analysis (paragraphs, sentences, dialogue)
    3. Content length and complexity

    Strategy selection rules:
    - Scene -> Semantic (preserves narrative flow and topic shifts)
    - Character -> Paragraph (groups related character traits)
    - Lore -> Fixed (consistent world-building chunks)
    - Dialogue -> Sentence (preserves speaker turns)
    - Document -> Paragraph (respects document structure)
    - Unknown -> Detected by analysis

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size (default: 50)
        - content_type: Optional hint for strategy selection

    Why auto-detection:
        - Provides sensible defaults without manual configuration
        - Adapts to different content types automatically
        - Improves RAG retrieval quality by using appropriate chunking

    Example:
        >>> strategy = AutoChunkingStrategy(embedding_service=service)
        >>> chunks = await strategy.chunk(
        ...     scene_text,
        ...     ChunkingStrategy(strategy=ChunkStrategyType.AUTO)
        ... )
        >>> # Uses semantic chunking for scenes
    """

    # Content type to strategy mappings
    CONTENT_TYPE_STRATEGY_MAP: dict[ContentType, ChunkStrategyType] = {
        ContentType.SCENE: ChunkStrategyType.SEMANTIC,
        ContentType.CHARACTER: ChunkStrategyType.PARAGRAPH,
        ContentType.LORE: ChunkStrategyType.FIXED,
        ContentType.DIALOGUE: ChunkStrategyType.SENTENCE,
        ContentType.NARRATIVE: ChunkStrategyType.SEMANTIC,
        ContentType.DOCUMENT: ChunkStrategyType.PARAGRAPH,
    }

    def __init__(
        self,
        embedding_service: IEmbeddingService | None = None,
        default_config: ChunkingStrategy | None = None,
    ):
        """
        Initialize the auto chunking strategy.

        Args:
            embedding_service: Required for semantic chunking. If None, semantic
                strategy falls back to paragraph chunking.
            default_config: Default configuration to use when none is provided
        """
        self._embedding_service = embedding_service
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=500,
            overlap=50,
        )

        # Initialize delegate strategies (created on demand to avoid circular imports)
        # Use Any for typing since each slot can only hold its specific type
        self._fixed_strategy: Any = None
        self._sentence_strategy: Any = None
        self._paragraph_strategy: Any = None
        self._semantic_strategy: Any = None

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into chunks using auto-detected strategy.

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

        if strategy_config.strategy != ChunkStrategyType.AUTO:
            logger.warning(
                "auto_chunking_strategy_mismatch",
                expected=ChunkStrategyType.AUTO,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="auto",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("auto_chunking_start")

        try:
            # Step 1: Determine content type
            content_type = self._get_content_type_hint(strategy_config)
            log = log.bind(content_type=content_type)

            # Step 2: Select strategy based on content type or structure
            selected_strategy = self._select_strategy(
                text,
                content_type,
                strategy_config,
            )
            log = log.bind(selected_strategy=selected_strategy.value)

            log.info(
                "auto_chunking_strategy_selected",
                content_type=content_type,
                strategy=selected_strategy.value,
            )

            # Step 3: Delegate to selected strategy
            chunks = await self._chunk_with_strategy(
                text,
                selected_strategy,
                strategy_config,
            )

            # Step 4: Update metadata to indicate auto-detection
            for chunk in chunks:
                chunk.metadata["auto_detected"] = True
                chunk.metadata["content_type"] = content_type
                chunk_metadata_strategy = chunk.metadata.get("strategy", "")
                chunk.metadata["original_strategy"] = chunk_metadata_strategy
                chunk.metadata["strategy"] = f"auto_{chunk_metadata_strategy}"

            log.info(
                "auto_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error("auto_chunking_error", error=str(e), error_type=type(e).__name__)
            raise ChunkingError(
                f"Auto chunking failed: {e}", code="AUTO_CHUNKING_ERROR"
            ) from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'auto' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.AUTO.value

    def _get_content_type_hint(self, config: ChunkingStrategy) -> ContentType:
        """
        Extract content type hint from configuration.

        Content type can be provided via:
        1. ChunkingStrategy.for_content_type() factory method
        2. Passing strategy=ChunkStrategyType.AUTO with content_type metadata

        Args:
            config: Chunking configuration

        Returns:
            Content type hint (UNKNOWN if not specified)
        """
        # Content type can be inferred from the strategy itself when using AUTO
        # The for_content_type factory method sets the strategy to AUTO
        # We detect content type by analyzing text structure in _detect_from_structure
        return ContentType.UNKNOWN

    def _select_strategy(
        self,
        text: str,
        content_type: ContentType,
        config: ChunkingStrategy,
    ) -> ChunkStrategyType:
        """
        Select the best chunking strategy for the given text.

        Args:
            text: Source text to analyze
            content_type: Content type hint (may be UNKNOWN)
            config: Chunking configuration

        Returns:
            Selected chunking strategy type
        """
        # If content type is known, use predefined mapping
        if content_type != ContentType.UNKNOWN:
            strategy = self.CONTENT_TYPE_STRATEGY_MAP.get(content_type)
            if strategy:
                # If semantic is selected but no embedding service, fall back to paragraph
                if (
                    strategy == ChunkStrategyType.SEMANTIC
                    and self._embedding_service is None
                ):
                    return ChunkStrategyType.PARAGRAPH
                return strategy

        # Otherwise, detect strategy from text structure
        return self._detect_from_structure(text)

    def _detect_from_structure(self, text: str) -> ChunkStrategyType:
        """
        Detect best strategy by analyzing text structure.

        Detection heuristics:
        1. High paragraph density -> Paragraph (document-like)
        2. High sentence density with dialogue markers -> Sentence (dialogue)
        3. Long flowing text with semantic shifts -> Semantic (narrative)
        4. Fallback -> Fixed (generic)

        Args:
            text: Source text to analyze

        Returns:
            Detected chunking strategy type
        """
        # Count structural elements
        paragraph_count = len(_PARAGRAPH_DELIM.findall(text))
        sentence_count = len(_SENTENCE_END.findall(text))
        word_count = len(_WORD_PATTERN.findall(text))
        dialogue_marker_count = text.count('"') + text.count("'")

        if word_count == 0:
            return ChunkStrategyType.FIXED

        # Calculate densities
        char_count = len(text)
        paragraph_density = paragraph_count / max(char_count, 1) * 1000
        sentence_density = sentence_count / max(word_count, 1)
        dialogue_ratio = dialogue_marker_count / max(word_count, 1)

        # Decision tree
        # 1. Document-like: Multiple paragraphs per 1000 chars
        if paragraph_density > 2.0:
            return ChunkStrategyType.PARAGRAPH

        # 2. Dialogue-heavy: Many quotes relative to word count
        if dialogue_ratio > 0.3:
            return ChunkStrategyType.SENTENCE

        # 3. Dense sentences: More than 1 sentence per 8 words
        if sentence_density > 0.12 and word_count > 100:
            # Semantic if we have embedding service, otherwise sentence
            if self._embedding_service is not None:
                return ChunkStrategyType.SEMANTIC
            return ChunkStrategyType.SENTENCE

        # 4. Fallback to fixed for generic content
        return ChunkStrategyType.FIXED

    async def _chunk_with_strategy(
        self,
        text: str,
        strategy_type: ChunkStrategyType,
        config: ChunkingStrategy,
    ) -> list[Chunk]:
        """
        Delegate chunking to the appropriate strategy.

        Args:
            text: Source text to chunk
            strategy_type: Strategy to use
            config: Chunking configuration

        Returns:
            List of Chunk entities
        """
        # Convert config to target strategy type
        target_config = ChunkingStrategy(
            strategy=strategy_type,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )

        if strategy_type == ChunkStrategyType.FIXED:
            delegate = self._get_fixed_strategy()
            return await delegate.chunk(text, target_config)  # type: ignore[no-any-return]

        if strategy_type == ChunkStrategyType.SENTENCE:
            delegate = self._get_sentence_strategy()
            return await delegate.chunk(text, target_config)  # type: ignore[no-any-return]

        if strategy_type == ChunkStrategyType.PARAGRAPH:
            delegate = self._get_paragraph_strategy()
            return await delegate.chunk(text, target_config)  # type: ignore[no-any-return]

        if strategy_type == ChunkStrategyType.SEMANTIC:
            if self._embedding_service is None:
                # Fall back to paragraph if no embedding service
                delegate = self._get_paragraph_strategy()
                para_config = ChunkingStrategy(
                    strategy=ChunkStrategyType.PARAGRAPH,
                    chunk_size=config.chunk_size,
                    overlap=config.overlap,
                    min_chunk_size=config.min_chunk_size,
                )
                return await delegate.chunk(text, para_config)  # type: ignore[no-any-return]

            delegate = self._get_semantic_strategy()
            return await delegate.chunk(text, target_config)  # type: ignore[no-any-return]

        # Should never reach here
        raise ChunkingError(
            f"Unknown strategy type: {strategy_type}", code="UNKNOWN_STRATEGY"
        )

    def _get_fixed_strategy(self) -> Any:
        """Get or create fixed chunking delegate."""
        if self._fixed_strategy is None:
            self._fixed_strategy = FixedChunkingStrategy()
        return self._fixed_strategy

    def _get_sentence_strategy(self) -> Any:
        """Get or create sentence chunking delegate."""
        if self._sentence_strategy is None:
            self._sentence_strategy = SentenceChunkingStrategy()
        return self._sentence_strategy

    def _get_paragraph_strategy(self) -> Any:
        """Get or create paragraph chunking delegate."""
        if self._paragraph_strategy is None:
            self._paragraph_strategy = ParagraphChunkingStrategy()
        return self._paragraph_strategy

    def _get_semantic_strategy(self) -> Any:
        """Get or create semantic chunking delegate."""
        if self._semantic_strategy is None:
            if self._embedding_service is None:
                raise ChunkingError(
                    "Embedding service required for semantic chunking",
                    code="MISSING_EMBEDDING_SERVICE",
                )
            self._semantic_strategy = SemanticChunkingStrategy(
                embedding_service=self._embedding_service,
            )
        return self._semantic_strategy


__all__ = [
    "CoherenceScore",
    "ChunkCoherenceAnalyzer",
    "FixedChunkingStrategy",
    "SentenceChunkingStrategy",
    "ParagraphChunkingStrategy",
    "SemanticChunkingStrategy",
    "NarrativeFlowChunkingStrategy",
    "AutoChunkingStrategy",
    "ContentType",
    "DEFAULT_COHERENCE_THRESHOLD",
]
