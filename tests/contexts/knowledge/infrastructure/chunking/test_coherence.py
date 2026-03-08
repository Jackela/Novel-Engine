"""Tests for Chunk Coherence Analyzer module.

Tests cover:
- Similarity scoring
- Boundary detection
- Size score calculation
- Coherence analysis with and without embedding service
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.knowledge.infrastructure.chunking.coherence import (
    ChunkCoherenceAnalyzer,
    CoherenceScore,
)
from src.contexts.knowledge.infrastructure.chunking.base import (
    MIN_COHERENCE_THRESHOLD,
    MAX_COHERENCE_THRESHOLD,
)
pytestmark = pytest.mark.unit



class MockChunk:
    """Mock chunk for testing."""
    
    def __init__(self, text: str, index: int = 0, metadata: dict[str, Any] | None = None) -> None:
        self.text = text
        self.index = index
        self.metadata = metadata or {}


class MockConfig:
    """Mock config for testing."""
    
    def __init__(self, chunk_size: int = 500, min_chunk_size: int = 50) -> None:
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size


class TestChunkCoherenceAnalyzerInit:
    """Test ChunkCoherenceAnalyzer initialization."""

    def test_analyzer_creation_with_defaults(self) -> None:
        """Test creating analyzer with default values."""
        analyzer = ChunkCoherenceAnalyzer()
        
        assert analyzer._embedding_service is None
        assert analyzer._acceptable_threshold == ChunkCoherenceAnalyzer.DEFAULT_ACCEPTABLE_THRESHOLD
        assert analyzer._internal_weight == ChunkCoherenceAnalyzer.DEFAULT_INTERNAL_WEIGHT

    def test_analyzer_creation_with_custom_values(self) -> None:
        """Test creating analyzer with custom values."""
        mock_service = MagicMock()
        analyzer = ChunkCoherenceAnalyzer(
            embedding_service=mock_service,
            acceptable_threshold=0.4,
            good_threshold=0.6,
            excellent_threshold=0.8,
            internal_weight=0.6,
            boundary_weight=0.25,
            size_weight=0.15
        )
        
        assert analyzer._embedding_service == mock_service
        assert analyzer._acceptable_threshold == 0.4
        assert analyzer._good_threshold == 0.6
        assert analyzer._excellent_threshold == 0.8
        assert analyzer._internal_weight == 0.6
        assert analyzer._boundary_weight == 0.25
        assert analyzer._size_weight == 0.15


class TestCalculateBoundaryQuality:
    """Test _calculate_boundary_quality method."""

    def test_ends_with_punctuation_high_score(self) -> None:
        """Test high score when chunk ends with sentence punctuation."""
        analyzer = ChunkCoherenceAnalyzer()
        chunk = MockChunk("This is a complete sentence.")
        
        score = analyzer._calculate_boundary_quality(chunk)
        
        assert score > 0.5  # Should have bonus for proper ending

    def test_ends_with_quote_score(self) -> None:
        """Test score when chunk ends with quote."""
        analyzer = ChunkCoherenceAnalyzer()
        chunk = MockChunk('She said "hello".')
        
        score = analyzer._calculate_boundary_quality(chunk)
        
        assert score > 0.5

    def test_no_punctuation_penalty(self) -> None:
        """Test penalty when chunk doesn't end with punctuation."""
        analyzer = ChunkCoherenceAnalyzer()
        chunk = MockChunk("This is incomplete")
        
        score = analyzer._calculate_boundary_quality(chunk)
        
        assert score < 1.0  # Should have penalty

    def test_starts_with_capital_bonus(self) -> None:
        """Test bonus when chunk starts with capital letter."""
        analyzer = ChunkCoherenceAnalyzer()
        chunk1 = MockChunk("Capital start with proper ending.")
        chunk2 = MockChunk("lowercase start with proper ending.")
        
        score1 = analyzer._calculate_boundary_quality(chunk1)
        score2 = analyzer._calculate_boundary_quality(chunk2)
        
        # Both should end properly, but capital start should score higher or equal
        assert score1 >= score2

    def test_paragraph_structure_bonus(self) -> None:
        """Test bonus for paragraph structure within chunk."""
        analyzer = ChunkCoherenceAnalyzer()
        chunk = MockChunk("Para 1.\n\nPara 2.\n\nPara 3.")
        
        score = analyzer._calculate_boundary_quality(chunk)
        
        assert score > 0.5  # Should have bonus for structure


class TestCalculateSizeScore:
    """Test _calculate_size_score method."""

    def test_ideal_size_score(self) -> None:
        """Test perfect score for ideal chunk size."""
        analyzer = ChunkCoherenceAnalyzer()
        config = MockConfig(chunk_size=100, min_chunk_size=10)
        chunk = MockChunk("word " * 50, metadata={"word_count": 50})  # Half of chunk_size
        
        score = analyzer._calculate_size_score(chunk, config)
        
        assert score == 1.0

    def test_too_small_penalty(self) -> None:
        """Test penalty for chunks below min size."""
        analyzer = ChunkCoherenceAnalyzer()
        config = MockConfig(chunk_size=100, min_chunk_size=50)
        chunk = MockChunk("word " * 10, metadata={"word_count": 10})  # Below min_chunk_size
        
        score = analyzer._calculate_size_score(chunk, config)
        
        assert score < 0.5  # Should be penalized

    def test_slightly_over_score(self) -> None:
        """Test score for chunks slightly over target."""
        analyzer = ChunkCoherenceAnalyzer()
        config = MockConfig(chunk_size=100, min_chunk_size=10)
        chunk = MockChunk("word " * 110, metadata={"word_count": 110})  # 10% over
        
        score = analyzer._calculate_size_score(chunk, config)
        
        assert 0.8 < score <= 0.9  # Slightly reduced

    def test_way_over_score(self) -> None:
        """Test score for chunks way over target."""
        analyzer = ChunkCoherenceAnalyzer()
        config = MockConfig(chunk_size=100, min_chunk_size=10)
        chunk = MockChunk("word " * 200, metadata={"word_count": 200})  # 2x over
        
        score = analyzer._calculate_size_score(chunk, config)
        
        assert score < 0.5  # Significantly reduced

    def test_size_score_from_text_when_no_metadata(self) -> None:
        """Test size score calculated from text when no word_count metadata."""
        analyzer = ChunkCoherenceAnalyzer()
        config = MockConfig(chunk_size=100, min_chunk_size=10)
        chunk = MockChunk("one two three four five")
        
        score = analyzer._calculate_size_score(chunk, config)
        
        # Should calculate word count from text
        assert score > 0  # Should have a valid score


class TestHeuristicCoherence:
    """Test _heuristic_coherence method."""

    def test_small_text_high_score(self) -> None:
        """Test high score for small text."""
        analyzer = ChunkCoherenceAnalyzer()
        text = "Short text."
        
        score = analyzer._heuristic_coherence(text, {})
        
        assert score > 0.7

    def test_large_text_penalty(self) -> None:
        """Test penalty for large text."""
        analyzer = ChunkCoherenceAnalyzer()
        text = "word " * 600  # More than 500 words
        
        score = analyzer._heuristic_coherence(text, {})
        
        # Should have some penalty for large text (score < 1.0)
        assert score < 1.0

    def test_dialogue_coherence_bonus(self) -> None:
        """Test bonus for well-structured dialogue."""
        analyzer = ChunkCoherenceAnalyzer()
        text = '"Hello," she said. "How are you?" he replied. "I am well," she answered.'
        
        score = analyzer._heuristic_coherence(text, {})
        
        # Even number of quotes should get bonus
        assert score > 0

    def test_paragraph_structure_bonus(self) -> None:
        """Test bonus for paragraph structure."""
        analyzer = ChunkCoherenceAnalyzer()
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        
        score = analyzer._heuristic_coherence(text, {})
        
        # Multiple paragraphs should get bonus
        assert score > 0.8


class TestCosineSimilarity:
    """Test _cosine_similarity method."""

    def test_identical_vectors(self) -> None:
        """Test cosine similarity of identical vectors is 1.0."""
        analyzer = ChunkCoherenceAnalyzer()
        vec = [1.0, 2.0, 3.0]
        
        similarity = analyzer._cosine_similarity(vec, vec)
        
        assert similarity == 1.0

    def test_orthogonal_vectors(self) -> None:
        """Test cosine similarity of orthogonal vectors is 0.0."""
        analyzer = ChunkCoherenceAnalyzer()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        
        similarity = analyzer._cosine_similarity(vec1, vec2)
        
        assert similarity == 0.0

    def test_opposite_vectors(self) -> None:
        """Test cosine similarity of opposite vectors is -1.0."""
        analyzer = ChunkCoherenceAnalyzer()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        
        similarity = analyzer._cosine_similarity(vec1, vec2)
        
        assert similarity == -1.0

    def test_different_length_vectors(self) -> None:
        """Test cosine similarity with different length vectors returns 0.0."""
        analyzer = ChunkCoherenceAnalyzer()
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]
        
        similarity = analyzer._cosine_similarity(vec1, vec2)
        
        assert similarity == 0.0

    def test_zero_vector(self) -> None:
        """Test cosine similarity with zero vector returns 0.0."""
        analyzer = ChunkCoherenceAnalyzer()
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [0.0, 0.0, 0.0]
        
        similarity = analyzer._cosine_similarity(vec1, vec2)
        
        assert similarity == 0.0


@pytest.mark.asyncio
class TestAnalyzeChunk:
    """Test analyze_chunk method."""

    async def test_analyze_chunk_returns_coherence_score(self) -> None:
        """Test that analyze_chunk returns a CoherenceScore."""
        analyzer = ChunkCoherenceAnalyzer()
        chunk = MockChunk("This is a complete sentence with proper structure.")
        config = MockConfig()
        
        score = await analyzer.analyze_chunk(chunk, config)
        
        assert isinstance(score, CoherenceScore)
        assert 0 <= score.score <= 1

    async def test_analyze_chunk_generates_warnings(self) -> None:
        """Test that analyze_chunk generates warnings for poor quality."""
        analyzer = ChunkCoherenceAnalyzer()
        # Very short chunk (below min size)
        chunk = MockChunk("Hi.", metadata={"word_count": 1})
        config = MockConfig(min_chunk_size=50)
        
        score = await analyzer.analyze_chunk(chunk, config)
        
        assert len(score.warnings) > 0

    async def test_analyze_chunk_boundary_quality_warning(self) -> None:
        """Test warning for poor boundary quality or small chunk size."""
        analyzer = ChunkCoherenceAnalyzer()
        # Very small chunk that triggers warnings
        chunk = MockChunk(
            "tiny", 
            metadata={"word_count": 1}
        )
        config = MockConfig(chunk_size=200, min_chunk_size=10)
        
        score = await analyzer.analyze_chunk(chunk, config)
        
        # Should have some warning (boundary, coherence, or size)
        has_boundary_warning = any("boundary" in w.lower() for w in score.warnings)
        has_coherence_warning = any("coherence" in w.lower() for w in score.warnings)
        has_size_warning = any("small" in w.lower() for w in score.warnings)
        assert has_boundary_warning or has_coherence_warning or has_size_warning or not score.is_acceptable


@pytest.mark.asyncio
class TestAnalyzeChunks:
    """Test analyze_chunks method."""

    async def test_analyze_multiple_chunks(self) -> None:
        """Test analyzing multiple chunks returns list of scores."""
        analyzer = ChunkCoherenceAnalyzer()
        chunks = [
            MockChunk("First chunk."),
            MockChunk("Second chunk."),
            MockChunk("Third chunk."),
        ]
        config = MockConfig()
        
        scores = await analyzer.analyze_chunks(chunks, config)
        
        assert len(scores) == 3
        assert all(isinstance(s, CoherenceScore) for s in scores)

    async def test_analyze_empty_chunks(self) -> None:
        """Test analyzing empty chunks returns empty list."""
        analyzer = ChunkCoherenceAnalyzer()
        chunks: list[MockChunk] = []
        config = MockConfig()
        
        scores = await analyzer.analyze_chunks(chunks, config)
        
        assert scores == []


@pytest.mark.asyncio
class TestEmbeddingBasedCoherence:
    """Test _embedding_based_coherence method."""

    async def test_single_sentence_perfect_coherence(self) -> None:
        """Test single sentence has perfect coherence."""
        mock_service = AsyncMock()
        analyzer = ChunkCoherenceAnalyzer(embedding_service=mock_service)
        
        # Single sentence should have coherence of 1.0
        coherence = await analyzer._embedding_based_coherence("Single sentence.")
        
        assert coherence == 1.0
        # Should not call embedding service for single sentence
        mock_service.embed_batch.assert_not_called()

    async def test_embedding_based_with_similar_sentences(self) -> None:
        """Test embedding-based coherence calculation."""
        mock_service = AsyncMock()
        # Return similar embeddings
        mock_service.embed_batch.return_value = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.8, 0.2, 0.0],
        ]
        analyzer = ChunkCoherenceAnalyzer(embedding_service=mock_service)
        
        coherence = await analyzer._embedding_based_coherence(
            "First sentence. Second sentence. Third sentence."
        )
        
        assert 0 < coherence <= 1.0
        mock_service.embed_batch.assert_called_once()

    async def test_embedding_failure_fallback(self) -> None:
        """Test fallback to heuristic when embedding fails."""
        mock_service = AsyncMock()
        mock_service.embed_batch.side_effect = Exception("Embedding failed")
        analyzer = ChunkCoherenceAnalyzer(embedding_service=mock_service)
        
        # Should not raise, should fallback to heuristic
        coherence = await analyzer._embedding_based_coherence(
            "First sentence. Second sentence."
        )
        
        assert 0 <= coherence <= 1.0


class TestInternalCoherence:
    """Test _calculate_internal_coherence method."""

    @pytest.mark.asyncio
    async def test_uses_embedding_service_when_available(self) -> None:
        """Test that embedding service is used when available."""
        mock_service = AsyncMock()
        mock_service.embed_batch.return_value = [
            [1.0, 0.0],
            [1.0, 0.0],
        ]
        analyzer = ChunkCoherenceAnalyzer(embedding_service=mock_service)
        chunk = MockChunk("Sentence one. Sentence two.")
        
        coherence = await analyzer._calculate_internal_coherence(chunk)
        
        mock_service.embed_batch.assert_called_once()
        assert coherence == 1.0  # Identical embeddings

    @pytest.mark.asyncio
    async def test_uses_heuristic_when_no_embedding_service(self) -> None:
        """Test that heuristic is used when no embedding service."""
        analyzer = ChunkCoherenceAnalyzer()  # No embedding service
        chunk = MockChunk("Sentence one. Sentence two.")
        
        coherence = await analyzer._calculate_internal_coherence(chunk)
        
        assert 0 <= coherence <= 1.0


class TestAnalyzerConstants:
    """Test analyzer constants."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        assert ChunkCoherenceAnalyzer.DEFAULT_ACCEPTABLE_THRESHOLD == 0.5
        assert ChunkCoherenceAnalyzer.DEFAULT_GOOD_THRESHOLD == 0.7
        assert ChunkCoherenceAnalyzer.DEFAULT_EXCELLENT_THRESHOLD == 0.85

    def test_default_weights(self) -> None:
        """Test default weight values."""
        assert ChunkCoherenceAnalyzer.DEFAULT_INTERNAL_WEIGHT == 0.5
        assert ChunkCoherenceAnalyzer.DEFAULT_BOUNDARY_WEIGHT == 0.3
        assert ChunkCoherenceAnalyzer.DEFAULT_SIZE_WEIGHT == 0.2
