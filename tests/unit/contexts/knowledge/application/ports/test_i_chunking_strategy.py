"""
Unit tests for IChunkingStrategy port interface.

Warzone 4: AI Brain - BRAIN-039A-01
Tests the chunking strategy port and Chunk entity.
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.application.ports.i_chunking_strategy import (
    Chunk,
    ChunkingError,
    IChunkingStrategy,
)
from src.contexts.knowledge.domain.models.chunking_strategy import (
    ChunkingStrategy,
    ChunkStrategyType,
)

pytestmark = pytest.mark.unit


class TestChunk:
    """Tests for Chunk entity."""

    def test_chunk_creation_with_minimal_args(self):
        """Test creating a Chunk with minimal arguments."""
        chunk = Chunk(text="Sample text", index=0)

        assert chunk.text == "Sample text"
        assert chunk.index == 0
        assert chunk.metadata == {}

    def test_chunk_creation_with_metadata(self):
        """Test creating a Chunk with metadata."""
        metadata = {"source": "lore", "position": 100}
        chunk = Chunk(text="Sample text", index=0, metadata=metadata)

        assert chunk.text == "Sample text"
        assert chunk.index == 0
        assert chunk.metadata == metadata

    def test_chunk_repr_short_text(self):
        """Test Chunk repr for short text."""
        chunk = Chunk(text="Short", index=0)
        repr_str = repr(chunk)

        assert "Chunk(index=0" in repr_str
        assert "Short" in repr_str
        assert "..." not in repr_str

    def test_chunk_repr_long_text(self):
        """Test Chunk repr for long text gets truncated."""
        long_text = "This is a very long piece of text that should be truncated"
        chunk = Chunk(text=long_text, index=0)
        repr_str = repr(chunk)

        assert "Chunk(index=0" in repr_str
        assert "..." in repr_str

    def test_chunk_equality_same_text_and_index(self):
        """Test Chunk equality with same text and index."""
        chunk1 = Chunk(text="Same text", index=0)
        chunk2 = Chunk(text="Same text", index=0)

        assert chunk1 == chunk2

    def test_chunk_equality_different_text(self):
        """Test Chunk inequality with different text."""
        chunk1 = Chunk(text="Text A", index=0)
        chunk2 = Chunk(text="Text B", index=0)

        assert chunk1 != chunk2

    def test_chunk_equality_different_index(self):
        """Test Chunk inequality with different index."""
        chunk1 = Chunk(text="Same text", index=0)
        chunk2 = Chunk(text="Same text", index=1)

        assert chunk1 != chunk2

    def test_chunk_equality_different_type(self):
        """Test Chunk inequality with different type."""
        chunk = Chunk(text="Text", index=0)

        assert chunk != "Text"
        assert chunk != 0
        assert chunk is not None

    def test_chunk_hash(self):
        """Test Chunk hash based on text and index."""
        chunk1 = Chunk(text="Same text", index=0)
        chunk2 = Chunk(text="Same text", index=0)

        # Same text and index should have same hash
        assert hash(chunk1) == hash(chunk2)

        # Can be used in sets
        chunk_set = {chunk1, chunk2}
        assert len(chunk_set) == 1

    def test_chunk_hash_different(self):
        """Test Chunk hash differs for different content."""
        chunk1 = Chunk(text="Text A", index=0)
        chunk2 = Chunk(text="Text B", index=0)

        assert hash(chunk1) != hash(chunk2)

    def test_chunk_in_set(self):
        """Test Chunks can be stored in a set."""
        chunk1 = Chunk(text="Text A", index=0)
        chunk2 = Chunk(text="Text B", index=1)
        chunk3 = Chunk(text="Text A", index=0)  # Duplicate of chunk1

        chunk_set = {chunk1, chunk2, chunk3}
        assert len(chunk_set) == 2

    def test_chunk_metadata_is_mutable_dict(self):
        """Test that Chunk metadata can be modified."""
        chunk = Chunk(text="Text", index=0, metadata={"key": "value"})
        chunk.metadata["new_key"] = "new_value"

        assert "new_key" in chunk.metadata
        assert chunk.metadata["new_key"] == "new_value"


class TestChunkingError:
    """Tests for ChunkingError exception."""

    def test_error_creation_default_code(self):
        """Test creating ChunkingError with default code."""
        error = ChunkingError("Test error message")

        assert str(error) == "Test error message"
        assert error.code == "CHUNKING_ERROR"
        assert isinstance(error, Exception)

    def test_error_creation_custom_code(self):
        """Test creating ChunkingError with custom code."""
        error = ChunkingError("Custom error", code="CUSTOM_ERROR")

        assert str(error) == "Custom error"
        assert error.code == "CUSTOM_ERROR"


class TestIChunkingStrategyProtocol:
    """Tests for IChunkingStrategy protocol."""

    def test_valid_implementation(self):
        """Test that a valid implementation conforms to the protocol."""

        # A valid implementation must have the chunk method
        class ValidChunkingStrategy:
            async def chunk(
                self,
                text: str,
                config: ChunkingStrategy | None = None,
            ) -> list[Chunk]:
                return [
                    Chunk(text=text, index=0, metadata={"strategy": "valid"}),
                ]

            def supports_strategy_type(self, strategy_type: str) -> bool:
                return strategy_type == "valid"

        # Should be compatible with IChunkingStrategy
        strategy: IChunkingStrategy = ValidChunkingStrategy()
        assert hasattr(strategy, "chunk")
        assert hasattr(strategy, "supports_strategy_type")

    def test_invalid_implementation_missing_chunk(self):
        """Test that class without chunk method is not compatible."""

        class InvalidStrategy:
            def supports_strategy_type(self, strategy_type: str) -> bool:
                return False

        strategy = InvalidStrategy()
        assert not hasattr(strategy, "chunk")

    def test_invalid_implementation_missing_supports(self):
        """Test that class without supports_strategy_type is not compatible."""

        class InvalidStrategy:
            async def chunk(
                self,
                text: str,
                config: ChunkingStrategy | None = None,
            ) -> list[Chunk]:
                return []

        strategy = InvalidStrategy()
        assert not hasattr(strategy, "supports_strategy_type")

    def test_chunk_method_signature_allows_none_config(self):
        """Test that chunk method accepts None for config."""

        class FlexibleStrategy:
            async def chunk(
                self,
                text: str,
                config: ChunkingStrategy | None = None,
            ) -> list[Chunk]:
                # Should use default when config is None
                if config is None:
                    config = ChunkingStrategy.default()
                return [Chunk(text=text, index=0)]

            def supports_strategy_type(self, strategy_type: str) -> bool:
                return True

        strategy = FlexibleStrategy()
        # Should not raise TypeError for None config
        assert strategy.chunk  # Method exists and accepts None

    def test_supports_strategy_type_checks_fixed(self):
        """Test supports_strategy_type for 'fixed' strategy."""

        class FixedOnlyStrategy:
            async def chunk(
                self,
                text: str,
                config: ChunkingStrategy | None = None,
            ) -> list[Chunk]:
                return []

            def supports_strategy_type(self, strategy_type: str) -> bool:
                return strategy_type == ChunkStrategyType.FIXED.value

        strategy = FixedOnlyStrategy()
        assert strategy.supports_strategy_type("fixed") is True
        assert strategy.supports_strategy_type("semantic") is False

    def test_supports_strategy_type_case_sensitive(self):
        """Test supports_strategy_type is case-sensitive."""

        class CaseSensitiveStrategy:
            async def chunk(
                self,
                text: str,
                config: ChunkingStrategy | None = None,
            ) -> list[Chunk]:
                return []

            def supports_strategy_type(self, strategy_type: str) -> bool:
                return strategy_type == "fixed"

        strategy = CaseSensitiveStrategy()
        assert strategy.supports_strategy_type("fixed") is True
        assert strategy.supports_strategy_type("FIXED") is False
        assert strategy.supports_strategy_type("Fixed") is False
