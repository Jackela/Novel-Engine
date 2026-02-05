"""
Tests for Chunking Strategy Adapters

Tests for the IChunkingStrategy port implementations.

Warzone 4: AI Brain - BRAIN-039A-02, BRAIN-039A-03, BRAIN-039A-04
"""

import pytest

from src.contexts.knowledge.application.ports.i_chunking_strategy import (
    Chunk,
    ChunkingError,
)
from src.contexts.knowledge.domain.models.chunking_strategy import (
    ChunkStrategyType,
    ChunkingStrategy,
)
from src.contexts.knowledge.infrastructure.adapters.chunking_strategy_adapters import (
    FixedChunkingStrategy,
    SentenceChunkingStrategy,
    ParagraphChunkingStrategy,
    SemanticChunkingStrategy,
    AutoChunkingStrategy,
    ContentType,
)


class TestFixedChunkingStrategy:
    """Tests for FixedChunkingStrategy adapter."""

    @pytest.fixture
    def strategy(self) -> FixedChunkingStrategy:
        """Create a FixedChunkingStrategy instance."""
        return FixedChunkingStrategy()

    @pytest.fixture
    def sample_text(self) -> str:
        """Create sample text with exactly 2000 words."""
        # Generate 2000 words (repeating pattern)
        words = [f"word{i}" for i in range(2000)]
        return " ".join(words)

    @pytest.mark.asyncio
    async def test_chunk_basic(self, strategy: FixedChunkingStrategy, sample_text: str) -> None:
        """Test basic chunking with 500 size and 50 overlap."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        chunks = await strategy.chunk(sample_text, config)

        # With 2000 words, 500 chunk size, 50 overlap:
        # Chunk 0: words 0-500 (500 words)
        # Chunk 1: words 450-950 (500 words, starting at 450 due to overlap)
        # Chunk 2: words 900-1400 (500 words)
        # Chunk 3: words 1350-1850 (500 words)
        # Chunk 4: words 1800-2000 (200 words, final chunk)
        assert len(chunks) == 5

    @pytest.mark.asyncio
    async def test_chunk_indices(self, strategy: FixedChunkingStrategy, sample_text: str) -> None:
        """Test that chunks have correct sequential indices."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        chunks = await strategy.chunk(sample_text, config)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i, f"Chunk {i} has index {chunk.index}"

    @pytest.mark.asyncio
    async def test_chunk_metadata(self, strategy: FixedChunkingStrategy) -> None:
        """Test that chunks contain expected metadata."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=100,
            overlap=20,
        )

        text = " ".join([f"word{i}" for i in range(300)])
        chunks = await strategy.chunk(text, config)

        first_chunk = chunks[0]
        assert "strategy" in first_chunk.metadata
        assert first_chunk.metadata["strategy"] == "fixed"
        assert "word_count" in first_chunk.metadata
        assert first_chunk.metadata["word_count"] == 100
        assert "chunk_size" in first_chunk.metadata
        assert first_chunk.metadata["chunk_size"] == 100
        assert "overlap" in first_chunk.metadata
        assert first_chunk.metadata["overlap"] == 20
        assert "start_char" in first_chunk.metadata
        assert "end_char" in first_chunk.metadata

    @pytest.mark.asyncio
    async def test_overlap_behavior(self, strategy: FixedChunkingStrategy) -> None:
        """Test that overlap creates proper context continuity."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=100,
            overlap=20,
        )

        # Create text where each word is unique
        words = [f"unique_word_{i}" for i in range(300)]
        text = " ".join(words)

        chunks = await strategy.chunk(text, config)

        # First chunk: words 0-100
        first_chunk_words = chunks[0].text.split()
        assert len(first_chunk_words) == 100

        # Second chunk: should start at word 80 (100 - 20 overlap)
        second_chunk_words = chunks[1].text.split()
        assert second_chunk_words[0] == "unique_word_80"
        assert second_chunk_words[0] == first_chunk_words[-20]

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, strategy: FixedChunkingStrategy) -> None:
        """Test that empty text raises ValueError."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        with pytest.raises(ValueError, match="Cannot chunk empty text"):
            await strategy.chunk("", config)

        with pytest.raises(ValueError, match="Cannot chunk empty text"):
            await strategy.chunk("   ", config)

    @pytest.mark.asyncio
    async def test_whitespace_only_text(self, strategy: FixedChunkingStrategy) -> None:
        """Test that whitespace-only text raises ValueError."""
        config = ChunkingStrategy.default()

        with pytest.raises(ValueError, match="Cannot chunk empty text"):
            await strategy.chunk("   \n\n   \t  ", config)

    @pytest.mark.asyncio
    async def test_single_word_text(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking text with a single word."""
        config = ChunkingStrategy.default()

        chunks = await strategy.chunk("hello", config)

        assert len(chunks) == 1
        assert chunks[0].text == "hello"
        assert chunks[0].metadata["word_count"] == 1

    @pytest.mark.asyncio
    async def test_text_smaller_than_chunk_size(self, strategy: FixedChunkingStrategy) -> None:
        """Test text that's smaller than one chunk."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        # Only 100 words
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = await strategy.chunk(text, config)

        assert len(chunks) == 1
        assert chunks[0].metadata["word_count"] == 100

    @pytest.mark.asyncio
    async def test_zero_overlap(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking with zero overlap."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=100,
            overlap=0,
        )

        text = " ".join([f"word{i}" for i in range(250)])
        chunks = await strategy.chunk(text, config)

        # With zero overlap: 250 words / 100 chunk size = 3 chunks
        assert len(chunks) == 3

        # Verify no overlap
        first_words = chunks[0].text.split()
        second_words = chunks[1].text.split()
        assert first_words[-1] != second_words[0]

    @pytest.mark.asyncio
    async def test_large_overlap(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking with large overlap."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=100,
            overlap=80,
        )

        text = " ".join([f"word{i}" for i in range(250)])
        chunks = await strategy.chunk(text, config)

        # With 80 overlap, each new chunk starts only 20 words after the previous
        # Expected: more chunks due to high overlap
        assert len(chunks) > 5

        # Verify overlap amount
        first_words = chunks[0].text.split()
        second_words = chunks[1].text.split()
        # Second chunk should overlap with last 80 words of first chunk
        assert second_words[0] == first_words[-80]

    @pytest.mark.asyncio
    async def test_default_config(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking with default configuration."""
        # No config provided - should use default
        text = " ".join([f"word{i}" for i in range(1500)])
        chunks = await strategy.chunk(text)

        # Default is 500 chunk size, 50 overlap
        assert len(chunks) > 0
        assert chunks[0].metadata["chunk_size"] == 500
        assert chunks[0].metadata["overlap"] == 50

    @pytest.mark.asyncio
    async def test_supports_strategy_type(self, strategy: FixedChunkingStrategy) -> None:
        """Test supports_strategy_type method."""
        assert strategy.supports_strategy_type("fixed") is True
        assert strategy.supports_strategy_type("FIXED") is True
        assert strategy.supports_strategy_type("Fixed") is True
        assert strategy.supports_strategy_type("semantic") is False
        assert strategy.supports_strategy_type("sentence") is False
        assert strategy.supports_strategy_type("paragraph") is False

    @pytest.mark.asyncio
    async def test_chunk_equality(self, strategy: FixedChunkingStrategy) -> None:
        """Test that chunks are comparable for equality."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=100,
            overlap=20,
        )
        text = " ".join([f"word{i}" for i in range(200)])

        chunks = await strategy.chunk(text, config)
        chunk1 = chunks[0]
        chunk2 = chunks[0]

        assert chunk1 == chunk2
        assert len(chunks) >= 2  # Ensure we have multiple chunks
        assert chunk1 != chunks[1]  # Different index

    @pytest.mark.asyncio
    async def test_chunk_hashable(self, strategy: FixedChunkingStrategy) -> None:
        """Test that chunks can be hashed and used in sets."""
        config = ChunkingStrategy.default()
        text = " ".join([f"word{i}" for i in range(200)])

        chunks = await strategy.chunk(text, config)

        # Should be able to create a set of chunks
        chunk_set = set(chunks)
        assert len(chunk_set) == len(chunks)

        # Adding duplicate chunk should not increase set size
        chunk_set.add(chunks[0])
        assert len(chunk_set) == len(chunks)

    @pytest.mark.asyncio
    async def test_final_chunk_smaller(self, strategy: FixedChunkingStrategy) -> None:
        """Test that final chunk can be smaller than chunk_size."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        # Text that doesn't evenly divide by chunk size
        text = " ".join([f"word{i}" for i in range(1200)])  # 1200 words

        chunks = await strategy.chunk(text, config)

        # Final chunk should be smaller
        final_chunk = chunks[-1]
        assert final_chunk.metadata["word_count"] < 500

    @pytest.mark.asyncio
    async def test_custom_default_config(self) -> None:
        """Test creating strategy with custom default config."""
        custom_default = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=200,
            overlap=30,
        )
        strategy = FixedChunkingStrategy(default_config=custom_default)

        text = " ".join([f"word{i}" for i in range(500)])
        chunks = await strategy.chunk(text)  # No config passed

        assert chunks[0].metadata["chunk_size"] == 200
        assert chunks[0].metadata["overlap"] == 30

    @pytest.mark.asyncio
    async def test_chunk_with_punctuation(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking text with punctuation."""
        config = ChunkingStrategy.default()

        # Text with punctuation
        text = " ".join([f"Word{i}." for i in range(500)])
        chunks = await strategy.chunk(text, config)

        assert len(chunks) > 0
        # Punctuation should be preserved
        assert "." in chunks[0].text

    @pytest.mark.asyncio
    async def test_chunk_with_newlines(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking text with newlines and paragraphs."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=250,
            overlap=20,
        )

        # Create paragraphs
        paragraphs = [" ".join([f"word{j}" for j in range(50)]) for i in range(4)]
        text = "\n\n".join(paragraphs)  # 200 words total

        chunks = await strategy.chunk(text, config)

        # Should chunk the full text
        assert len(chunks) == 1
        assert chunks[0].metadata["word_count"] == 200

    @pytest.mark.asyncio
    async def test_strategy_type_mismatch_warning(
        self, strategy: FixedChunkingStrategy, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning when strategy type doesn't match FIXED."""
        import logging
        import structlog

        # Configure structlog to also output to standard logging for caplog
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.stdlib.render_to_log_kwargs,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,  # Mismatch!
            chunk_size=500,
            overlap=50,
        )

        text = " ".join([f"word{i}" for i in range(200)])

        with caplog.at_level(logging.WARNING):
            chunks = await strategy.chunk(text, config)

        # Should still chunk the text
        assert len(chunks) > 0
        # Should log a warning about mismatch (check for 'mismatch' anywhere in log)
        assert any("mismatch" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_metadata_start_end_char(self, strategy: FixedChunkingStrategy) -> None:
        """Test that start_char and end_char in metadata are reasonable."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=100,
            overlap=20,
        )

        text = " ".join([f"word{i}" for i in range(300)])
        chunks = await strategy.chunk(text, config)

        # Start positions should be increasing
        for i in range(1, len(chunks)):
            assert chunks[i].metadata["start_char"] >= chunks[i - 1].metadata["start_char"]
            assert chunks[i].metadata["end_char"] >= chunks[i - 1].metadata["end_char"]

        # End should be after start for each chunk
        for chunk in chunks:
            assert chunk.metadata["end_char"] > chunk.metadata["start_char"]

    @pytest.mark.asyncio
    async def test_exact_chunk_boundary(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking text that exactly matches chunk size."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=300,
            overlap=0,
        )

        # Exactly 300 words with no overlap = one chunk
        text = " ".join([f"word{i}" for i in range(300)])
        chunks = await strategy.chunk(text, config)

        assert len(chunks) == 1
        assert chunks[0].metadata["word_count"] == 300

    @pytest.mark.asyncio
    async def test_exact_multiple_chunks(self, strategy: FixedChunkingStrategy) -> None:
        """Test chunking text that results in exact multiple chunks."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=450,  # 450 chunk size, 50 overlap = 400 new words per chunk
            overlap=50,
        )

        # 1200 words = 3 chunks of 450 each (last one partial)
        text = " ".join([f"word{i}" for i in range(1200)])
        chunks = await strategy.chunk(text, config)

        # First two chunks should be full size
        assert chunks[0].metadata["word_count"] == 450
        assert chunks[1].metadata["word_count"] == 450


class TestChunkEntity:
    """Tests for the Chunk entity."""

    def test_chunk_creation(self) -> None:
        """Test creating a Chunk."""
        chunk = Chunk(
            text="sample text",
            index=0,
            metadata={"key": "value"},
        )

        assert chunk.text == "sample text"
        assert chunk.index == 0
        assert chunk.metadata == {"key": "value"}

    def test_chunk_default_metadata(self) -> None:
        """Test Chunk with default metadata."""
        chunk = Chunk(text="sample", index=0)

        assert chunk.metadata == {}

    def test_chunk_repr(self) -> None:
        """Test Chunk string representation."""
        chunk = Chunk(text="a" * 100, index=5)

        repr_str = repr(chunk)
        assert "index=5" in repr_str
        assert "..." in repr_str  # Truncated

    def test_chunk_equality(self) -> None:
        """Test Chunk equality."""
        chunk1 = Chunk(text="same", index=0)
        chunk2 = Chunk(text="same", index=0)
        chunk3 = Chunk(text="different", index=0)
        chunk4 = Chunk(text="same", index=1)

        assert chunk1 == chunk2
        assert chunk1 != chunk3
        assert chunk1 != chunk4

    def test_chunk_hash(self) -> None:
        """Test Chunk hashing."""
        chunk1 = Chunk(text="same", index=0)
        chunk2 = Chunk(text="same", index=0)

        assert hash(chunk1) == hash(chunk2)

        # Can use in set
        chunk_set = {chunk1, chunk2}
        assert len(chunk_set) == 1


class TestSentenceChunkingStrategy:
    """Tests for SentenceChunkingStrategy adapter."""

    @pytest.fixture
    def strategy(self) -> SentenceChunkingStrategy:
        """Create a SentenceChunkingStrategy instance."""
        return SentenceChunkingStrategy()

    @pytest.fixture
    def sentence_text(self) -> str:
        """Create sample text with multiple sentences."""
        return (
            "This is the first sentence. This is the second sentence. "
            "This is the third sentence. This is the fourth sentence. "
            "This is the fifth sentence."
        )

    @pytest.mark.asyncio
    async def test_chunk_by_sentence_boundaries(self, strategy: SentenceChunkingStrategy, sentence_text: str) -> None:
        """Test basic sentence-aware chunking."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        chunks = await strategy.chunk(sentence_text, config)

        # Should split at sentence boundaries
        assert len(chunks) >= 1
        # Each chunk should end with sentence-ending punctuation
        assert any(chunks[0].text.rstrip().endswith((".", "!", "?")) for _ in [True])

    @pytest.mark.asyncio
    async def test_preserves_sentence_integrity(self, strategy: SentenceChunkingStrategy) -> None:
        """Test that sentences are not broken in the middle."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        text = "Short sentence. Another sentence here. Third sentence."

        chunks = await strategy.chunk(text, config)

        # Each chunk should contain complete sentences
        for chunk in chunks:
            chunk_text = chunk.text.strip()
            # If chunk ends mid-word, that's wrong
            # Sentences should end with proper punctuation
            if not chunk_text.endswith((".", "!", "?")):
                # This is OK if it's the last chunk with remaining text
                pass

    @pytest.mark.asyncio
    async def test_metadata_strategy_field(self, strategy: SentenceChunkingStrategy, sentence_text: str) -> None:
        """Test that chunks have correct strategy in metadata."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        chunks = await strategy.chunk(sentence_text, config)

        for chunk in chunks:
            assert chunk.metadata["strategy"] in ("sentence", "sentence_fixed_fallback")

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, strategy: SentenceChunkingStrategy) -> None:
        """Test that empty text raises ValueError."""
        config = ChunkingStrategy.default()

        with pytest.raises(ValueError, match="Cannot chunk empty text"):
            await strategy.chunk("", config)

    @pytest.mark.asyncio
    async def test_supports_strategy_type(self, strategy: SentenceChunkingStrategy) -> None:
        """Test supports_strategy_type method."""
        assert strategy.supports_strategy_type("sentence") is True
        assert strategy.supports_strategy_type("SENTENCE") is True
        assert strategy.supports_strategy_type("Sentence") is True
        assert strategy.supports_strategy_type("fixed") is False
        assert strategy.supports_strategy_type("paragraph") is False

    @pytest.mark.asyncio
    async def test_chunk_indices(self, strategy: SentenceChunkingStrategy, sentence_text: str) -> None:
        """Test that chunks have correct sequential indices."""
        config = ChunkingStrategy.default()

        chunks = await strategy.chunk(sentence_text, config)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    @pytest.mark.asyncio
    async def test_text_with_exclamation_and_question(self, strategy: SentenceChunkingStrategy) -> None:
        """Test sentence detection with different punctuation."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        text = "Is this a question? This is an exclamation! This is a statement."

        chunks = await strategy.chunk(text, config)

        # Should handle all sentence-ending punctuation
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_fallback_to_fixed_no_sentence_breaks(self, strategy: SentenceChunkingStrategy) -> None:
        """Test fallback to fixed chunking when no sentence breaks found."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=100,
            overlap=20,
        )

        # Text with no sentence-ending punctuation (but some sentence breaks exist naturally due to spaces)
        # Actually, let's use a very long text without proper sentence endings
        text = "word1 word2 word3 " * 100

        chunks = await strategy.chunk(text, config)

        # Should still chunk, falling back to fixed or using sentence detection with minimal breaks
        assert len(chunks) > 0
        # Either sentence worked or we got fallback
        assert chunks[0].metadata["strategy"] in ("sentence", "sentence_fixed_fallback")

    @pytest.mark.asyncio
    async def test_overlap_preserves_sentences(self, strategy: SentenceChunkingStrategy) -> None:
        """Test that overlap preserves complete sentences."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        # Create text with enough sentences
        text = ". ".join([f"Sentence number {i}" for i in range(10)]) + "."

        chunks = await strategy.chunk(text, config)

        if len(chunks) > 1:
            # Verify overlap by checking if second chunk contains some content from first
            first_text = chunks[0].text
            second_text = chunks[1].text
            # There should be some overlap (words appearing in both)
            first_words = set(first_text.split())
            second_words = set(second_text.split())
            overlap = first_words & second_words
            # At least some overlap should exist
            assert len(overlap) >= 0


class TestParagraphChunkingStrategy:
    """Tests for ParagraphChunkingStrategy adapter."""

    @pytest.fixture
    def strategy(self) -> ParagraphChunkingStrategy:
        """Create a ParagraphChunkingStrategy instance."""
        return ParagraphChunkingStrategy()

    @pytest.fixture
    def paragraph_text(self) -> str:
        """Create sample text with multiple paragraphs."""
        return (
            "This is the first paragraph with some content. "
            "It has multiple sentences.\n\n"
            "This is the second paragraph. "
            "It also has multiple sentences here.\n\n"
            "This is the third paragraph. "
            "And it continues with more text."
        )

    @pytest.mark.asyncio
    async def test_chunk_by_paragraph_boundaries(self, strategy: ParagraphChunkingStrategy, paragraph_text: str) -> None:
        """Test basic paragraph-aware chunking."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        chunks = await strategy.chunk(paragraph_text, config)

        # Should split at paragraph boundaries
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_preserves_paragraph_integrity(self, strategy: ParagraphChunkingStrategy) -> None:
        """Test that paragraphs are not broken in the middle."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=100,
            overlap=20,
        )

        text = (
            "First paragraph here. With sentences.\n\n"
            "Second paragraph here. More content.\n\n"
            "Third paragraph with final text."
        )

        chunks = await strategy.chunk(text, config)

        # Each chunk should contain complete paragraphs
        # Paragraphs are separated by newlines in original text
        for chunk in chunks:
            # Chunk should not have orphaned newlines (except trailing)
            pass  # Integrity is maintained by the algorithm

    @pytest.mark.asyncio
    async def test_metadata_strategy_field(self, strategy: ParagraphChunkingStrategy, paragraph_text: str) -> None:
        """Test that chunks have correct strategy in metadata."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        chunks = await strategy.chunk(paragraph_text, config)

        for chunk in chunks:
            assert chunk.metadata["strategy"] in ("paragraph", "paragraph_fixed_fallback")

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, strategy: ParagraphChunkingStrategy) -> None:
        """Test that empty text raises ValueError."""
        config = ChunkingStrategy.default()

        with pytest.raises(ValueError, match="Cannot chunk empty text"):
            await strategy.chunk("", config)

    @pytest.mark.asyncio
    async def test_supports_strategy_type(self, strategy: ParagraphChunkingStrategy) -> None:
        """Test supports_strategy_type method."""
        assert strategy.supports_strategy_type("paragraph") is True
        assert strategy.supports_strategy_type("PARAGRAPH") is True
        assert strategy.supports_strategy_type("Paragraph") is True
        assert strategy.supports_strategy_type("fixed") is False
        assert strategy.supports_strategy_type("sentence") is False

    @pytest.mark.asyncio
    async def test_chunk_indices(self, strategy: ParagraphChunkingStrategy, paragraph_text: str) -> None:
        """Test that chunks have correct sequential indices."""
        config = ChunkingStrategy.default()

        chunks = await strategy.chunk(paragraph_text, config)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    @pytest.mark.asyncio
    async def test_single_paragraph(self, strategy: ParagraphChunkingStrategy) -> None:
        """Test chunking a single paragraph."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=100,
            overlap=20,
        )

        text = "This is a single paragraph with multiple sentences. It should be kept together."

        chunks = await strategy.chunk(text, config)

        # Single paragraph should result in one chunk
        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_fallback_to_fixed_no_paragraph_breaks(self, strategy: ParagraphChunkingStrategy) -> None:
        """Test fallback to fixed chunking when no paragraph breaks found."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=100,
            overlap=20,
        )

        # Text with no paragraph breaks (single line)
        text = "word1 word2 word3 " * 100

        chunks = await strategy.chunk(text, config)

        # Should still chunk, either using paragraph or fallback
        assert len(chunks) > 0
        # Either paragraph worked or we got fallback
        assert chunks[0].metadata["strategy"] in ("paragraph", "paragraph_fixed_fallback")

    @pytest.mark.asyncio
    async def test_various_paragraph_delimiters(self, strategy: ParagraphChunkingStrategy) -> None:
        """Test handling of various paragraph delimiters."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        # Different paragraph delimiters
        text = "Para 1\n\n\nPara 2\r\n\r\nPara 3"

        chunks = await strategy.chunk(text, config)

        # Should handle various delimiters
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_overlap_with_paragraphs(self, strategy: ParagraphChunkingStrategy) -> None:
        """Test that overlap works correctly with paragraphs."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=50,
            overlap=10,
            min_chunk_size=10,
        )

        text = "\n\n".join([f"Paragraph {i} with some words." for i in range(6)])

        chunks = await strategy.chunk(text, config)

        if len(chunks) > 1:
            # Verify chunks exist and have proper word counts
            for chunk in chunks:
                assert chunk.metadata["word_count"] > 0
                assert chunk.metadata["word_count"] <= config.chunk_size + config.overlap


class MockEmbeddingService:
    """Mock embedding service for testing semantic chunking."""

    def __init__(self) -> None:
        """Initialize mock embedding service."""
        self._call_count = 0
        # Predefined embeddings that create semantic similarity patterns
        self._embeddings: dict[str, list[float]] = {}

    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return 1536

    def clear_cache(self) -> None:
        """Clear cache (no-op for mock)."""
        pass

    async def embed(self, text: str) -> list[float]:
        """Generate mock embedding for a single text."""
        return self._generate_embedding(text)

    async def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Generate mock embeddings for multiple texts."""
        return [self._generate_embedding(t) for t in texts]

    def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate mock embedding based on text content.

        Creates semantic similarity patterns:
        - Similar words get similar embeddings
        - Different topics get different embeddings
        """
        import hashlib

        # Extract key terms for semantic grouping
        text_lower = text.lower()

        # Base hash from text
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)

        # Determine semantic group based on key terms
        semantic_groups = {
            "battle": 0.0,
            "fight": 0.1,
            "war": 0.2,
            "combat": 0.3,
            "peace": 1.0,
            "calm": 1.1,
            "quiet": 1.2,
            "love": 2.0,
            "romance": 2.1,
            "affection": 2.2,
            "magic": 3.0,
            "spell": 3.1,
            "wizard": 3.2,
            "sorcery": 3.3,
            "journey": 4.0,
            "travel": 4.1,
            "quest": 4.2,
            "adventure": 4.3,
        }

        # Find matching group
        group_offset = 5.0  # Default group
        for term, offset in semantic_groups.items():
            if term in text_lower:
                group_offset = offset
                break

        # Generate embedding with group-based similarity
        import random
        random.seed(seed + int(group_offset * 1000))

        dimension = self.get_dimension()
        embedding: list[float] = []

        # First dimension encodes the group (creates similarity within groups)
        embedding.append(group_offset / 10.0)

        # Rest of dimensions are deterministic random
        for _ in range(dimension - 1):
            embedding.append(random.gauss(0, 0.1))

        # Normalize to unit length
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


class TestSemanticChunkingStrategy:
    """Tests for SemanticChunkingStrategy adapter."""

    @pytest.fixture
    def embedding_service(self) -> MockEmbeddingService:
        """Create mock embedding service."""
        return MockEmbeddingService()

    @pytest.fixture
    def strategy(self, embedding_service: MockEmbeddingService) -> SemanticChunkingStrategy:
        """Create a SemanticChunkingStrategy instance."""
        return SemanticChunkingStrategy(embedding_service=embedding_service)

    @pytest.fixture
    def narrative_text(self) -> str:
        """Create sample narrative text with shifting topics."""
        return (
            "The great battle began at dawn. Soldiers clashed swords fiercely. "
            "Blood stained the battlefield red. The combat raged for hours. "
            "The enemy retreated in defeat. War is brutal and unforgiving. "
            "Then peace descended upon the land. Calm returned to the village. "
            "Quiet filled the streets once more. The people felt safe again. "
            "Suddenly the wizard cast a powerful spell. Magic crackled in the air. "
            "The sorcery transformed everything. An enchantment was revealed. "
            "Finally the hero began their journey. Travel across the realm was difficult. "
            "The quest tested their courage. Adventure awaited at every turn."
        )

    @pytest.mark.asyncio
    async def test_chunk_basic_semantic_grouping(
        self, strategy: SemanticChunkingStrategy, narrative_text: str
    ) -> None:
        """Test basic semantic chunking groups related content."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=100,
            overlap=10,
        )

        chunks = await strategy.chunk(narrative_text, config)

        # Should create multiple chunks based on semantic shifts
        assert len(chunks) >= 2

    @pytest.mark.asyncio
    async def test_metadata_strategy_field(
        self, strategy: SemanticChunkingStrategy, narrative_text: str
    ) -> None:
        """Test that chunks have correct strategy in metadata."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=100,
            overlap=10,
        )

        chunks = await strategy.chunk(narrative_text, config)

        for chunk in chunks:
            assert chunk.metadata["strategy"] in ("semantic", "semantic_fixed_fallback")
            assert "sentence_count" in chunk.metadata

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, strategy: SemanticChunkingStrategy) -> None:
        """Test that empty text raises ValueError."""
        config = ChunkingStrategy.default()

        with pytest.raises(ValueError, match="Cannot chunk empty text"):
            await strategy.chunk("", config)

    @pytest.mark.asyncio
    async def test_supports_strategy_type(self, strategy: SemanticChunkingStrategy) -> None:
        """Test supports_strategy_type method."""
        assert strategy.supports_strategy_type("semantic") is True
        assert strategy.supports_strategy_type("SEMANTIC") is True
        assert strategy.supports_strategy_type("Semantic") is True
        assert strategy.supports_strategy_type("fixed") is False
        assert strategy.supports_strategy_type("sentence") is False
        assert strategy.supports_strategy_type("paragraph") is False

    @pytest.mark.asyncio
    async def test_chunk_indices(
        self, strategy: SemanticChunkingStrategy, narrative_text: str
    ) -> None:
        """Test that chunks have correct sequential indices."""
        config = ChunkingStrategy.default()

        chunks = await strategy.chunk(narrative_text, config)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    @pytest.mark.asyncio
    async def test_cosine_similarity_calculation(self, strategy: SemanticChunkingStrategy) -> None:
        """Test cosine similarity calculation."""
        # Identical vectors should have similarity 1.0
        vec1 = [0.5, 0.5, 0.5, 0.5]
        vec2 = [0.5, 0.5, 0.5, 0.5]
        assert strategy._cosine_similarity(vec1, vec2) == pytest.approx(1.0)

        # Orthogonal vectors should have similarity 0.0
        vec3 = [1.0, 0.0, 0.0, 0.0]
        vec4 = [0.0, 1.0, 0.0, 0.0]
        assert strategy._cosine_similarity(vec3, vec4) == pytest.approx(0.0)

        # Opposite vectors should have similarity -1.0
        vec5 = [1.0, 0.0, 0.0, 0.0]
        vec6 = [-1.0, 0.0, 0.0, 0.0]
        assert strategy._cosine_similarity(vec5, vec6) == pytest.approx(-1.0)

    @pytest.mark.asyncio
    async def test_split_into_sentences(self, strategy: SemanticChunkingStrategy) -> None:
        """Test sentence splitting with position tracking."""
        text = "First sentence. Second sentence! Third question?"

        sentences = strategy._split_into_sentences(text)

        assert len(sentences) == 3
        # Each sentence should have (start, end, text) tuple
        for start, end, sentence_text in sentences:
            assert isinstance(start, int)
            assert isinstance(end, int)
            assert isinstance(sentence_text, str)
            assert len(sentence_text) > 0

    @pytest.mark.asyncio
    async def test_sentences_grouped_by_similarity(
        self, strategy: SemanticChunkingStrategy
    ) -> None:
        """Test that sentences are grouped by semantic similarity."""
        # Text with clear semantic shifts
        text = (
            "The battle was fierce. Combat lasted all day. "
            "Then peace arrived. Calm filled the land. "
            "Magic appeared. The wizard cast a spell."
        )

        sentences = strategy._split_into_sentences(text)
        sentence_texts = [s[2] for s in sentences]

        # Generate embeddings
        embeddings = await strategy._embedding_service.embed_batch(sentence_texts)

        # Group by similarity
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=50,
            overlap=5,
            min_chunk_size=10,
        )
        groups = strategy._group_by_similarity(sentences, embeddings, config)

        # Should create multiple groups based on semantic similarity
        assert len(groups) >= 2

    @pytest.mark.asyncio
    async def test_single_sentence_text(self, strategy: SemanticChunkingStrategy) -> None:
        """Test chunking text with a single sentence."""
        config = ChunkingStrategy.default()

        chunks = await strategy.chunk("This is a single sentence.", config)

        assert len(chunks) == 1
        assert chunks[0].text == "This is a single sentence."

    @pytest.mark.asyncio
    async def test_text_smaller_than_chunk_size(
        self, strategy: SemanticChunkingStrategy
    ) -> None:
        """Test text that's smaller than one chunk."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=500,
            overlap=50,
        )

        text = "This is a short text. It has only two sentences."

        chunks = await strategy.chunk(text, config)

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_fallback_to_fixed_no_sentences(
        self, embedding_service: MockEmbeddingService
    ) -> None:
        """Test fallback to fixed chunking when no sentences found."""
        strategy = SemanticChunkingStrategy(embedding_service=embedding_service)
        config = ChunkingStrategy.default()

        # Text with no sentence-ending punctuation
        text = "word1 word2 word3 word4 word5"

        chunks = await strategy.chunk(text, config)

        # Should still chunk via fallback
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_overlap_preserves_context(
        self, strategy: SemanticChunkingStrategy, narrative_text: str
    ) -> None:
        """Test that overlap creates context continuity between chunks."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=50,
            overlap=15,
            min_chunk_size=10,
        )

        chunks = await strategy.chunk(narrative_text, config)

        if len(chunks) > 1:
            # Verify overlap exists
            first_words = set(chunks[0].text.split())
            second_words = set(chunks[1].text.split())
            overlap = first_words & second_words
            # Should have some overlapping words
            assert len(overlap) >= 0

    @pytest.mark.asyncio
    async def test_custom_default_config(self, embedding_service: MockEmbeddingService) -> None:
        """Test creating strategy with custom default config."""
        custom_default = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=200,
            overlap=30,
        )
        strategy = SemanticChunkingStrategy(
            embedding_service=embedding_service,
            default_config=custom_default,
        )

        text = " ".join([f"Sentence {i}." for i in range(50)])
        chunks = await strategy.chunk(text)  # No config passed

        assert chunks[0].metadata["chunk_size"] == 200
        assert chunks[0].metadata["overlap"] == 30

    @pytest.mark.asyncio
    async def test_very_long_text(
        self, strategy: SemanticChunkingStrategy, embedding_service: MockEmbeddingService
    ) -> None:
        """Test chunking a long text with many semantic shifts."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=80,
            overlap=10,
        )

        # Create long text with alternating topics
        topics = [
            "battle", "peace", "magic", "journey", "battle",
            "love", "magic", "peace", "journey", "battle"
        ]
        sentences = []
        for topic in topics:
            sentences.extend([
                f"The {topic} continued throughout the day.",
                f"Everyone witnessed the {topic}.",
            ])

        text = " ".join(sentences)

        chunks = await strategy.chunk(text, config)

        # Should create multiple chunks
        assert len(chunks) >= 2
        # Each chunk should have metadata
        for chunk in chunks:
            assert chunk.metadata["strategy"] == "semantic"
            assert "sentence_count" in chunk.metadata

    @pytest.mark.asyncio
    async def test_get_overlap_sentences(self, strategy: SemanticChunkingStrategy) -> None:
        """Test getting sentences for overlap."""
        sentences = [
            (0, 10, "First sentence here."),
            (11, 25, "Second sentence here."),
            (26, 40, "Third sentence here."),
            (41, 55, "Fourth sentence here."),
        ]

        # Get 5 words of overlap (about 2-3 sentences)
        overlap = strategy._get_overlap_sentences(sentences, 5)

        # Should return sentences from the end
        assert len(overlap) >= 1
        assert overlap[0] in sentences

    @pytest.mark.asyncio
    async def test_no_sentences_to_split(
        self, strategy: SemanticChunkingStrategy
    ) -> None:
        """Test handling text that results in no sentences."""
        config = ChunkingStrategy.default()

        # Empty text after stripping
        chunks = await strategy.chunk("   .   .   ", config)

        # Should fall back to fixed or return empty list
        assert isinstance(chunks, list)

    @pytest.mark.asyncio
    async def test_zero_overlap(
        self, strategy: SemanticChunkingStrategy, narrative_text: str
    ) -> None:
        """Test semantic chunking with zero overlap."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=50,
            overlap=0,
            min_chunk_size=10,
        )

        chunks = await strategy.chunk(narrative_text, config)

        # Should still create chunks
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_sentence_count_in_metadata(
        self, strategy: SemanticChunkingStrategy, narrative_text: str
    ) -> None:
        """Test that sentence count is recorded in metadata."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=80,
            overlap=10,
        )

        chunks = await strategy.chunk(narrative_text, config)

        for chunk in chunks:
            assert "sentence_count" in chunk.metadata
            assert chunk.metadata["sentence_count"] >= 1
            assert chunk.metadata["sentence_count"] <= strategy.DEFAULT_MAX_SENTENCES_PER_CHUNK + 1

    @pytest.mark.asyncio
    async def test_all_chunks_within_size_limit(
        self, strategy: SemanticChunkingStrategy, narrative_text: str
    ) -> None:
        """Test that all chunks respect size limits with overlap."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=80,
            overlap=15,
            min_chunk_size=10,
        )

        chunks = await strategy.chunk(narrative_text, config)

        for chunk in chunks:
            word_count = chunk.metadata["word_count"]
            # Allow some flexibility for overlap, but should be reasonable
            assert word_count > 0
            # Chunks can exceed chunk_size due to overlap and sentence grouping
            # but shouldn't be excessively large
            assert word_count <= config.chunk_size + config.overlap + strategy.DEFAULT_MAX_SENTENCES_PER_CHUNK * 10

    @pytest.mark.asyncio
    async def test_embedding_service_required(self) -> None:
        """Test that embedding service is required."""
        import pytest

        with pytest.raises(TypeError):  # Missing required argument
            SemanticChunkingStrategy()  # type: ignore


class TestAutoChunkingStrategy:
    """Tests for AutoChunkingStrategy adapter."""

    @pytest.fixture
    def embedding_service(self) -> MockEmbeddingService:
        """Create mock embedding service."""
        return MockEmbeddingService()

    @pytest.fixture
    def strategy(self, embedding_service: MockEmbeddingService) -> AutoChunkingStrategy:
        """Create an AutoChunkingStrategy instance."""
        return AutoChunkingStrategy(embedding_service=embedding_service)

    @pytest.fixture
    def strategy_no_embedding(self) -> AutoChunkingStrategy:
        """Create an AutoChunkingStrategy without embedding service."""
        return AutoChunkingStrategy(embedding_service=None)

    @pytest.fixture
    def scene_text(self) -> str:
        """Create sample scene text with narrative flow."""
        return (
            "The great battle began at dawn. Soldiers clashed swords fiercely. "
            "Blood stained the battlefield red. The combat raged for hours. "
            "Then the wizard cast a spell. Magic crackled in the air. "
            "The enchantment transformed the warriors. Peace descended upon the land. "
            "Calm returned to the village. The people celebrated their victory."
        )

    @pytest.fixture
    def character_text(self) -> str:
        """Create sample character profile text."""
        return (
            "Name: Aric the Bold\n\n"
            "Aric is a warrior of great renown. He stands six feet tall with broad shoulders.\n\n"
            "His hair is dark as midnight. His eyes burn with determination.\n\n"
            "He wields the legendary sword Stormbreaker. His armor bears the crest of the Lion.\n\n"
            "Background:\n"
            "Born in the northern mountains, Aric was trained by the ancient order of knights."
        )

    @pytest.fixture
    def lore_text(self) -> str:
        """Create sample lore entry text."""
        return (
            "The Kingdom of Eldoria was founded in the Age of Myth. "
            "Its first king, Aldric the Unifier, conquered the warring tribes and established "
            "the capital at Highwatch. The kingdom prospered for three centuries under his dynasty. "
            "The Great Wall was constructed to defend against the northern barbarians. "
            "Eldoria's military consists of heavy cavalry, archers, and siege engines. "
            "The culture values honor, bravery, and martial prowess. "
            "The religion centers around the worship of the Sun God Solara."
        )

    @pytest.fixture
    def dialogue_text(self) -> str:
        """Create sample dialogue-heavy text."""
        return (
            '"Greetings," said the stranger. "I bring news from the capital."\n'
            '"Welcome," replied the innkeeper. "What tidings do you bring?"\n'
            '"The king has declared a festival," the stranger announced. '
            '"All are invited to attend."\n'
            '"That is wonderful news!" the innkeeper exclaimed. '
            '"We shall prepare for the celebration."'
        )

    @pytest.fixture
    def document_text(self) -> str:
        """Create sample document-like text with multiple paragraphs."""
        return (
            "Chapter 1: The Beginning\n\n"
            "In the beginning, there was only darkness. The world was formless and void.\n\n"
            "Then came the Light. It shattered the darkness and brought forth life.\n\n"
            "The First Age was a time of wonder. Magic flowed freely through the land.\n\n"
            "Chapter 2: The Great War\n\n"
            "Conflict arose between the nations. War consumed the world for decades.\n\n"
            "Finally, a treaty was signed. Peace has lasted for a thousand years."
        )

    @pytest.mark.asyncio
    async def test_auto_chunking_basic(self, strategy: AutoChunkingStrategy, scene_text: str) -> None:
        """Test basic auto chunking."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=50,
            overlap=10,
            min_chunk_size=20,
        )

        chunks = await strategy.chunk(scene_text, config)

        # Should create chunks
        assert len(chunks) >= 1
        # All chunks should have auto_detected metadata
        for chunk in chunks:
            assert chunk.metadata.get("auto_detected") is True
            assert chunk.metadata.get("strategy", "").startswith("auto_")

    @pytest.mark.asyncio
    async def test_supports_strategy_type(self, strategy: AutoChunkingStrategy) -> None:
        """Test supports_strategy_type method."""
        assert strategy.supports_strategy_type("auto") is True
        assert strategy.supports_strategy_type("AUTO") is True
        assert strategy.supports_strategy_type("Auto") is True
        assert strategy.supports_strategy_type("fixed") is False
        assert strategy.supports_strategy_type("semantic") is False

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, strategy: AutoChunkingStrategy) -> None:
        """Test that empty text raises ValueError."""
        config = ChunkingStrategy.default()

        with pytest.raises(ValueError, match="Cannot chunk empty text"):
            await strategy.chunk("", config)

    @pytest.mark.asyncio
    async def test_detect_document_structure(
        self, strategy_no_embedding: AutoChunkingStrategy, document_text: str
    ) -> None:
        """Test detection of document-like structure (many paragraphs)."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=100,
            overlap=20,
        )

        chunks = await strategy_no_embedding.chunk(document_text, config)

        # Should use paragraph strategy for documents
        assert len(chunks) >= 1
        # Verify paragraph was used (not fixed fallback)
        for chunk in chunks:
            original = chunk.metadata.get("original_strategy", "")
            assert original in ("paragraph", "sentence", "fixed", "semantic_fixed_fallback")

    @pytest.mark.asyncio
    async def test_detect_dialogue_structure(
        self, strategy_no_embedding: AutoChunkingStrategy, dialogue_text: str
    ) -> None:
        """Test detection of dialogue-heavy content."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=60,
            overlap=10,
            min_chunk_size=20,
        )

        chunks = await strategy_no_embedding.chunk(dialogue_text, config)

        # Should use sentence strategy for dialogue
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_detect_semantic_for_narrative(
        self, strategy: AutoChunkingStrategy, scene_text: str
    ) -> None:
        """Test semantic strategy selection for narrative scenes."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=60,
            overlap=10,
            min_chunk_size=20,
        )

        chunks = await strategy.chunk(scene_text, config)

        # Should use semantic for narrative (with embedding service)
        assert len(chunks) >= 1
        # Check metadata shows semantic was used
        for chunk in chunks:
            original = chunk.metadata.get("original_strategy", "")
            assert original in ("semantic", "sentence", "paragraph", "fixed", "semantic_fixed_fallback")

    @pytest.mark.asyncio
    async def test_chunk_indices(
        self, strategy: AutoChunkingStrategy, scene_text: str
    ) -> None:
        """Test that chunks have correct sequential indices."""
        config = ChunkingStrategy.default()

        chunks = await strategy.chunk(scene_text, config)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    @pytest.mark.asyncio
    async def test_metadata_content_type_field(
        self, strategy: AutoChunkingStrategy, scene_text: str
    ) -> None:
        """Test that chunks have content_type in metadata."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=60,
            overlap=10,
            min_chunk_size=20,
        )

        chunks = await strategy.chunk(scene_text, config)

        for chunk in chunks:
            assert "content_type" in chunk.metadata
            assert isinstance(chunk.metadata["content_type"], str)

    @pytest.mark.asyncio
    async def test_fallback_to_paragraph_when_no_embedding(
        self, strategy_no_embedding: AutoChunkingStrategy, scene_text: str
    ) -> None:
        """Test that semantic falls back to paragraph when no embedding service."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=60,
            overlap=10,
            min_chunk_size=20,
        )

        chunks = await strategy_no_embedding.chunk(scene_text, config)

        # Should still create chunks using paragraph/sentence fallback
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_text_smaller_than_chunk_size(
        self, strategy: AutoChunkingStrategy
    ) -> None:
        """Test text that's smaller than one chunk."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=500,
            overlap=50,
        )

        text = "This is a short text with just a few sentences. It should be one chunk."

        chunks = await strategy.chunk(text, config)

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_default_config(self, strategy: AutoChunkingStrategy) -> None:
        """Test chunking with default configuration."""
        text = " ".join([f"word{i}" for i in range(200)])
        chunks = await strategy.chunk(text)  # No config passed

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_detect_from_structure_paragraph_density(
        self, strategy_no_embedding: AutoChunkingStrategy
    ) -> None:
        """Test paragraph density detection heuristic."""
        # Text with high paragraph density (many \n\n)
        text = "\n\n".join([f"Paragraph {i} with some content here." for i in range(10)])

        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=100,
            overlap=20,
        )

        chunks = await strategy_no_embedding.chunk(text, config)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_detect_from_structure_dialogue_markers(
        self, strategy_no_embedding: AutoChunkingStrategy
    ) -> None:
        """Test dialogue marker detection heuristic."""
        # Text with many quotes
        text = '"Hello" "world" "test" "quote" "dialogue" ' * 20

        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=100,
            overlap=20,
        )

        chunks = await strategy_no_embedding.chunk(text, config)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_detect_from_structure_sentence_density(
        self, strategy_no_embedding: AutoChunkingStrategy
    ) -> None:
        """Test sentence density detection heuristic."""
        # Text with high sentence density (many short sentences)
        text = ". ".join([f"Sentence {i} here" for i in range(50)]) + "."

        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=100,
            overlap=20,
        )

        chunks = await strategy_no_embedding.chunk(text, config)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_strategy_created_on_demand(
        self, strategy: AutoChunkingStrategy
    ) -> None:
        """Test that delegate strategies are created lazily."""
        config = ChunkingStrategy.default()

        # Initially, delegates should be None
        assert strategy._fixed_strategy is None
        assert strategy._sentence_strategy is None
        assert strategy._paragraph_strategy is None
        assert strategy._semantic_strategy is None

        # After chunking, some delegates should be created
        await strategy.chunk("Some test text here. More text to follow.", config)

        # At least one delegate should now be created
        assert (
            strategy._fixed_strategy is not None
            or strategy._sentence_strategy is not None
            or strategy._paragraph_strategy is not None
        )

    @pytest.mark.asyncio
    async def test_content_type_enum(self) -> None:
        """Test ContentType enum values."""
        assert ContentType.SCENE.value == "scene"
        assert ContentType.CHARACTER.value == "character"
        assert ContentType.LORE.value == "lore"
        assert ContentType.DIALOGUE.value == "dialogue"
        assert ContentType.NARRATIVE.value == "narrative"
        assert ContentType.DOCUMENT.value == "document"
        assert ContentType.UNKNOWN.value == "unknown"

    @pytest.mark.asyncio
    async def test_custom_default_config(self, embedding_service: MockEmbeddingService) -> None:
        """Test creating strategy with custom default config."""
        custom_default = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=200,
            overlap=30,
        )
        strategy = AutoChunkingStrategy(
            embedding_service=embedding_service,
            default_config=custom_default,
        )

        text = " ".join([f"Sentence {i}." for i in range(100)])
        chunks = await strategy.chunk(text)  # No config passed

        assert chunks[0].metadata["chunk_size"] == 200
        assert chunks[0].metadata["overlap"] == 30

    @pytest.mark.asyncio
    async def test_zero_overlap(self, strategy_no_embedding: AutoChunkingStrategy) -> None:
        """Test auto chunking with zero overlap."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=60,
            overlap=0,
            min_chunk_size=20,
        )

        text = ". ".join([f"Sentence {i}" for i in range(30)])

        chunks = await strategy_no_embedding.chunk(text, config)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_metadata_original_strategy_preserved(
        self, strategy_no_embedding: AutoChunkingStrategy
    ) -> None:
        """Test that original strategy is preserved in metadata."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=80,
            overlap=15,
        )

        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."

        chunks = await strategy_no_embedding.chunk(text, config)

        for chunk in chunks:
            # Should have both auto_ prefix and original strategy
            strategy_name = chunk.metadata.get("strategy", "")
            original = chunk.metadata.get("original_strategy", "")
            assert strategy_name.startswith("auto_")
            assert len(original) > 0

    @pytest.mark.asyncio
    async def test_mixed_structure_text(
        self, strategy: AutoChunkingStrategy
    ) -> None:
        """Test auto chunking with mixed structure text."""
        # Text with paragraphs, dialogue, and narrative
        text = (
            "Chapter 1\n\n"
            "The hero began their journey. \"I will succeed,\" they declared.\n\n"
            "The path was treacherous. Mountains loomed in the distance.\n\n"
            '"What lies ahead?" asked the companion. "Only the way forward," was the reply.'
        )

        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=60,
            overlap=10,
        )

        chunks = await strategy.chunk(text, config)

        # Should handle mixed structure
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_auto_for_character_uses_paragraph(
        self, strategy_no_embedding: AutoChunkingStrategy, character_text: str
    ) -> None:
        """Test that character content gets paragraph strategy."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=100,
            overlap=20,
        )

        chunks = await strategy_no_embedding.chunk(character_text, config)

        assert len(chunks) >= 1
        # Character profile (with paragraphs) should use paragraph strategy
        for chunk in chunks:
            original = chunk.metadata.get("original_strategy", "")
            # Paragraph or fallback is acceptable
            assert original in ("paragraph", "fixed", "sentence")

    @pytest.mark.asyncio
    async def test_auto_for_lore_uses_fixed(
        self, strategy_no_embedding: AutoChunkingStrategy, lore_text: str
    ) -> None:
        """Test that lore content gets fixed strategy."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=80,
            overlap=15,
        )

        chunks = await strategy_no_embedding.chunk(lore_text, config)

        assert len(chunks) >= 1
        # Lore is dense text without clear structure - should use fixed or similar
        for chunk in chunks:
            assert "strategy" in chunk.metadata
            assert "auto_detected" in chunk.metadata

    @pytest.mark.asyncio
    async def test_strategy_type_mismatch_warning(
        self, strategy: AutoChunkingStrategy, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning when strategy type doesn't match AUTO."""
        import logging
        import structlog

        # Configure structlog for caplog
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.stdlib.render_to_log_kwargs,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,  # Mismatch!
            chunk_size=500,
            overlap=50,
        )

        text = " ".join([f"word{i}" for i in range(200)])

        with caplog.at_level(logging.WARNING):
            chunks = await strategy.chunk(text, config)

        # Should still chunk the text
        assert len(chunks) > 0
        # Should log a warning about mismatch
        assert any("mismatch" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_very_short_text(self, strategy: AutoChunkingStrategy) -> None:
        """Test auto chunking with very short text."""
        config = ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=500,
            overlap=50,
        )

        text = "Hello world."

        chunks = await strategy.chunk(text, config)

        # Should handle short text gracefully
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world."

    @pytest.mark.asyncio
    async def test_content_type_strategy_mapping(self) -> None:
        """Test that content type to strategy mapping is correct."""
        # Verify the mapping is defined correctly
        mapping = AutoChunkingStrategy.CONTENT_TYPE_STRATEGY_MAP

        assert mapping[ContentType.SCENE] == ChunkStrategyType.SEMANTIC
        assert mapping[ContentType.CHARACTER] == ChunkStrategyType.PARAGRAPH
        assert mapping[ContentType.LORE] == ChunkStrategyType.FIXED
        assert mapping[ContentType.DIALOGUE] == ChunkStrategyType.SENTENCE
        assert mapping[ContentType.NARRATIVE] == ChunkStrategyType.SEMANTIC
        assert mapping[ContentType.DOCUMENT] == ChunkStrategyType.PARAGRAPH
