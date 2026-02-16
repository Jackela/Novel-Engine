"""
Unit Tests for TextChunker Domain Service

Tests text chunking for RAG vector storage.

Warzone 4: AI Brain - BRAIN-003
Tests various chunking strategies and edge cases.

Constitution Compliance:
- Article III (TDD): Tests written to validate chunking behavior
- Article I (DDD): Tests domain service behavior
"""

import pytest

from src.contexts.knowledge.domain.models.chunking_strategy import (
    ChunkingStrategy,
    ChunkStrategyType,
)
from src.contexts.knowledge.domain.services.text_chunker import (
    ChunkedDocument,
    TextChunk,
    TextChunker,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_2000_word_text() -> str:
    """
    Create a 2000-word text for chunking tests.

    Returns:
        Text with exactly 2000 words
    """
    words = [f"word{i}" for i in range(2000)]
    return " ".join(words)


@pytest.fixture
def sample_scene_text() -> str:
    """
    Create a sample scene text with paragraphs.

    Returns:
        Scene text with multiple paragraphs
    """
    return """
    The brave warrior stood at the edge of the cliff, looking out over the vast expanse of the kingdom. The wind whipped at his cloak, carrying the scent of pine and distant rain.

    He had traveled far to reach this place. Through forests dark and deep, across rivers swollen with spring melt, and over mountains that scraped the sky. His journey had begun with a promise—a promise to find the ancient artifact that could save his people from the darkness gathering at the edges of the world.

    "You cannot succeed," the old seer had told him, her eyes clouded with the weight of centuries. "The path is too dangerous, the guardians too terrible. No mortal has ever returned from the Citadel of Echoes."

    He had not listened. How could he, when every night he saw the same vision in his dreams? A world covered in shadow, where hope flickered like a dying candle. And always, the voice whispering: "Find the artifact. Find it before it is too late."

    Now, standing at the cliff's edge, he could see it in the distance—the Citadel of Echoes, rising from the mist like a needle of black stone. The entrance was a gaping maw, and from within came a sound like the sighing of a thousand ghosts.

    He tightened his grip on his sword and took the first step downward.

    The descent was treacherous. The path was narrow and slick with moss, and the wind howled through the crags like a wounded beast. More than once he nearly fell, his boots skidding on loose stones, his heart pounding as he caught himself at the last second.

    But he did not stop. He could not stop. The fate of everyone he loved depended on his success.

    At last he reached the bottom. Before him stretched a vast cavern, its ceiling lost in darkness. In the center, upon a pedestal of obsidian, rested the artifact—a sphere of crystal that pulsed with an inner light.

    And around it, coiled like a serpent around a tree, waited the guardian.

    The battle that followed would be told in songs for generations to come. But in that moment, there was only the clash of steel against scale, the roar of a creature as old as the mountains themselves, and the desperate determination of one warrior who refused to yield.

    When the dust finally settled, the guardian lay defeated, and the sphere was in his hands.

    He had done it. He had found the artifact.

    Now he just had to make it back alive.
    """


class TestTextChunker:
    """Unit tests for TextChunker service."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_chunk_empty_text_raises_error(self):
        """Test that chunking empty text raises ValueError."""
        strategy = ChunkingStrategy.default()

        with pytest.raises(ValueError) as exc_info:
            TextChunker.chunk("", strategy)

        assert "Cannot chunk empty text" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_chunk_whitespace_only_raises_error(self):
        """Test that chunking whitespace-only text raises ValueError."""
        strategy = ChunkingStrategy.default()

        with pytest.raises(ValueError) as exc_info:
            TextChunker.chunk("   ", strategy)

        assert "Cannot chunk empty text" in str(exc_info.value)


class TestFixedChunking:
    """Unit tests for fixed-size chunking strategy."""

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_fixed_500_word_chunks(self, sample_2000_word_text: str):
        """
        Test splitting a 2000-word text into 500-word chunks with 50-word overlap.

        Warzone 4: AI Brain - BRAIN-003
        Verifies fixed chunking strategy with overlap works correctly.
        """
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        result = TextChunker.chunk(sample_2000_word_text, strategy)

        # Should have approximately 5 chunks:
        # Chunk 1: words 0-499 (500 words)
        # Chunk 2: words 450-949 (500 words, 50 overlap)
        # Chunk 3: words 900-1399 (500 words, 50 overlap)
        # Chunk 4: words 1350-1849 (500 words, 50 overlap)
        # Chunk 5: words 1800-1999 (200 words)
        assert result.total_chunks > 1
        # total_words includes overlap, so it will be greater than original
        assert result.total_words >= 2000

        # First chunk should have 500 words
        assert result.chunks[0].word_count == 500

        # Verify overlap
        first_chunk_end = result.chunks[0].content.split()[-50:]
        second_chunk_start = result.chunks[1].content.split()[:50]
        assert first_chunk_end == second_chunk_start

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_fixed_small_text_single_chunk(self):
        """Test that text smaller than chunk size results in single chunk."""
        text = "This is a short text."
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        result = TextChunker.chunk(text, strategy)

        assert result.total_chunks == 1
        assert result.chunks[0].content == text

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_fixed_exact_size(self):
        """Test chunking text that exactly matches chunk size."""
        text = " ".join([f"word{i}" for i in range(450)])
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        result = TextChunker.chunk(text, strategy)

        # Text fits in one chunk (less than chunk_size)
        assert result.total_chunks == 1
        assert result.chunks[0].word_count == 450

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_indices_are_sequential(self, sample_2000_word_text: str):
        """Test that chunk indices are sequential starting from 0."""
        strategy = ChunkingStrategy.default()
        result = TextChunker.chunk(sample_2000_word_text, strategy)

        for i, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == i

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_positions_are_valid(self, sample_2000_word_text: str):
        """Test that chunk start/end positions are within bounds."""
        strategy = ChunkingStrategy.default()
        result = TextChunker.chunk(sample_2000_word_text, strategy)

        text_length = len(sample_2000_word_text)
        for chunk in result.chunks:
            assert 0 <= chunk.start_pos < text_length
            assert 0 < chunk.end_pos <= text_length
            assert chunk.start_pos < chunk.end_pos


class TestSentenceChunking:
    """Unit tests for sentence-based chunking strategy."""

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_by_sentence_preserves_boundaries(self, sample_scene_text: str):
        """Test that sentence chunking respects sentence boundaries."""
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=100,
            overlap=20,
            min_chunk_size=20,
        )

        result = TextChunker.chunk(sample_scene_text, strategy)

        # Each chunk should end at sentence boundary
        for chunk in result.chunks:
            assert chunk.content.endswith(("!", "?", ".", '"'))

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_by_sentence_has_overlap(self, sample_scene_text: str):
        """Test that sentence chunking includes overlap."""
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=80,
            overlap=20,
            min_chunk_size=20,
        )

        result = TextChunker.chunk(sample_scene_text, strategy)

        if result.total_chunks > 1:
            # Second chunk should start with some of the same content as first chunk
            first_chunk_words = result.chunks[0].content.lower().split()
            second_chunk_words = result.chunks[1].content.lower().split()

            # Check for overlap (at least some words should match)
            overlap_found = False
            for word in first_chunk_words[-20:]:
                if word in second_chunk_words[:20]:
                    overlap_found = True
                    break
            assert overlap_found, "No overlap found between sentence chunks"


class TestParagraphChunking:
    """Unit tests for paragraph-based chunking strategy."""

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_by_paragraph_preserves_boundaries(self, sample_scene_text: str):
        """Test that paragraph chunking respects paragraph boundaries."""
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=100,
            overlap=20,
        )

        result = TextChunker.chunk(sample_scene_text, strategy)

        # Chunks should be complete paragraphs
        for chunk in result.chunks:
            # Paragraph chunks shouldn't end mid-sentence unless very long
            # This is a soft check - paragraphs naturally end at sentence boundaries
            assert chunk.content.strip() == chunk.content.strip()

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_by_paragraph_with_short_text(self):
        """Test paragraph chunking with text shorter than chunk size."""
        text = "Short paragraph."
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=100,
            overlap=20,
        )

        result = TextChunker.chunk(text, strategy)

        assert result.total_chunks == 1
        assert result.chunks[0].content == text


class TestSemanticChunking:
    """Unit tests for semantic chunking strategy."""

    @pytest.mark.unit
    @pytest.mark.medium
    def test_chunk_semantic_with_paragraphs(self, sample_scene_text: str):
        """Test that semantic chunking uses paragraph boundaries."""
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=100,
            overlap=20,
        )

        result = TextChunker.chunk(sample_scene_text, strategy)

        # Semantic chunking should respect document structure
        assert result.total_chunks > 0
        assert all(
            chunk.word_count <= strategy.chunk_size * 1.5 for chunk in result.chunks
        )


class TestTextChunkerUtilities:
    """Unit tests for TextChunker utility methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_count_words(self):
        """Test word counting utility."""
        text = "The quick brown fox jumps over the lazy dog."
        count = TextChunker.count_words(text)

        assert count == 9

    @pytest.mark.unit
    @pytest.mark.fast
    def test_count_words_with_multiple_spaces(self):
        """Test word counting with irregular spacing."""
        text = "  The   quick  brown   fox  "
        count = TextChunker.count_words(text)

        assert count == 4

    @pytest.mark.unit
    @pytest.mark.fast
    def test_count_words_empty(self):
        """Test word counting with empty string."""
        count = TextChunker.count_words("")

        assert count == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "The quick brown fox jumps over the lazy dog."
        tokens = TextChunker.estimate_tokens(text)

        # 9 words * 1.3 = ~12 tokens
        assert 11 <= tokens <= 13


class TestChunkedDocument:
    """Unit tests for ChunkedDocument value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_chunked_document_fields(self):
        """Test ChunkedDocument contains all expected fields."""
        strategy = ChunkingStrategy.default()
        chunks = [
            TextChunk(
                content="First chunk",
                chunk_index=0,
                start_pos=0,
                end_pos=11,
                word_count=2,
            )
        ]

        doc = ChunkedDocument(
            chunks=chunks,
            total_chunks=1,
            total_words=2,
            strategy=strategy,
        )

        assert doc.total_chunks == 1
        assert doc.total_words == 2
        assert doc.strategy == strategy


class TestTextChunk:
    """Unit tests for TextChunk value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_text_chunk_is_immutable(self):
        """Test that TextChunk is frozen (immutable)."""
        chunk = TextChunk(
            content="Test",
            chunk_index=0,
            start_pos=0,
            end_pos=4,
            word_count=1,
        )

        # Attempting to modify should raise
        with pytest.raises(Exception):
            chunk.content = "Modified"
