"""
Chunk Coherence Analyzer Module

Provides coherence analysis for chunks to identify potential issues
with chunk boundaries, semantic drift, or inappropriate sizes.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import structlog

from .base import (
    MAX_COHERENCE_THRESHOLD,
    MIN_COHERENCE_THRESHOLD,
    _PARAGRAPH_DELIM,
    _SENTENCE_END,
    _WORD_PATTERN,
    CoherenceScore,
)

if TYPE_CHECKING:
    from ...application.ports.i_chunking_strategy import Chunk
    from ...domain.models.chunking_strategy import ChunkingStrategy

logger = structlog.get_logger()


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
        embedding_service: Any | None = None,
        acceptable_threshold: float = DEFAULT_ACCEPTABLE_THRESHOLD,
        good_threshold: float = DEFAULT_GOOD_THRESHOLD,
        excellent_threshold: float = DEFAULT_EXCELLENT_THRESHOLD,
        internal_weight: float = DEFAULT_INTERNAL_WEIGHT,
        boundary_weight: float = DEFAULT_BOUNDARY_WEIGHT,
        size_weight: float = DEFAULT_SIZE_WEIGHT,
    ) -> None:
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
        chunks: list[Any],
        config: Any,
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
        chunk: Any,
        config: Any,
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
            min_chunk_size = getattr(config, "min_chunk_size", 50)
            chunk_size = getattr(config, "chunk_size", 500)
            if word_count < min_chunk_size:
                warnings.append(f"Chunk too small ({word_count} words)")
            elif word_count > chunk_size * 1.5:
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

    async def _calculate_internal_coherence(self, chunk: Any) -> float:
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
            if self._embedding_service is None:
                return self._heuristic_coherence(text, {})
            embeddings = await self._embedding_service.embed_batch(sentences)

            # Calculate pairwise similarities between adjacent sentences
            similarities: list[Any] = []
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

    def _calculate_boundary_quality(self, chunk: Any) -> float:
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

    def _calculate_size_score(self, chunk: Any, config: Any) -> float:
        """
        Calculate score based on chunk size appropriateness.

        Higher when chunk size is within the target range.

        Args:
            chunk: Chunk to analyze
            config: Chunking configuration with target size

        Returns:
            Size score from 0.0 to 1.0
        """
        word_count_raw = chunk.metadata.get(
            "word_count", len(_WORD_PATTERN.findall(chunk.text))
        )
        word_count = int(word_count_raw) if word_count_raw is not None else 0
        target = int(getattr(config, "chunk_size", 500) or 500)
        min_size = int(getattr(config, "min_chunk_size", 50) or 50)

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
