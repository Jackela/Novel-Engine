"""
Tests for Chunking Strategy Adapters

Tests for the IChunkingStrategy port implementations.

Warzone 4: AI Brain - BRAIN-039A-02
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
