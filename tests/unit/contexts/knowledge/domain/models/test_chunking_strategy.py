"""
Unit Tests for ChunkingStrategy Value Object

Tests the chunking strategy configuration for RAG.

Warzone 4: AI Brain - BRAIN-003
Tests chunking strategy validation and presets.

Constitution Compliance:
- Article III (TDD): Tests written to validate value object behavior
- Article I (DDD): Tests value object invariants
"""

import pytest

from src.contexts.knowledge.domain.models.chunking_strategy import (
    ChunkStrategyType,
    ChunkingStrategy,
    ChunkingStrategies,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_OVERLAP,
    MAX_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
)


class TestChunkingStrategy:
    """Unit tests for ChunkingStrategy value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_strategy_creates_valid_config(self):
        """Test that default factory creates valid strategy."""
        strategy = ChunkingStrategy.default()

        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == DEFAULT_CHUNK_SIZE
        assert strategy.overlap == DEFAULT_OVERLAP

    @pytest.mark.unit
    @pytest.mark.fast
    def test_strategy_is_immutable(self):
        """Test that ChunkingStrategy is frozen (immutable)."""
        strategy = ChunkingStrategy.default()

        # Attempting to modify should raise
        with pytest.raises(Exception):  # FrozenInstanceError
            strategy.chunk_size = 1000

    @pytest.mark.unit
    @pytest.mark.fast
    def test_effective_chunk_size_calculates_correctly(self):
        """Test that effective_chunk_size returns chunk_size - overlap."""
        strategy = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=500,
            overlap=50,
        )

        assert strategy.effective_chunk_size() == 450

    @pytest.mark.unit
    @pytest.mark.fast
    def test_for_character_returns_smaller_chunks(self):
        """Test that character preset returns smaller semantic chunks."""
        strategy = ChunkingStrategy.for_character()

        assert strategy.strategy == ChunkStrategyType.SEMANTIC
        assert strategy.chunk_size == 200
        assert strategy.overlap == 20

    @pytest.mark.unit
    @pytest.mark.fast
    def test_for_scene_returns_paragraph_chunks(self):
        """Test that scene preset returns paragraph-aware chunks."""
        strategy = ChunkingStrategy.for_scene()

        assert strategy.strategy == ChunkStrategyType.PARAGRAPH
        assert strategy.chunk_size == 300
        assert strategy.overlap == 30

    @pytest.mark.unit
    @pytest.mark.fast
    def test_for_lore_returns_fixed_chunks(self):
        """Test that lore preset returns fixed chunks."""
        strategy = ChunkingStrategy.for_lore()

        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == 400
        assert strategy.overlap == 40


class TestChunkingStrategyValidation:
    """Unit tests for ChunkingStrategy validation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_chunk_size_below_minimum_raises_error(self):
        """Test that chunk_size below MIN_CHUNK_SIZE raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ChunkingStrategy(
                strategy=ChunkStrategyType.FIXED,
                chunk_size=MIN_CHUNK_SIZE - 1,
                overlap=10,
            )

        assert "chunk_size must be at least" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_chunk_size_above_maximum_raises_error(self):
        """Test that chunk_size above MAX_CHUNK_SIZE raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ChunkingStrategy(
                strategy=ChunkStrategyType.FIXED,
                chunk_size=MAX_CHUNK_SIZE + 1,
                overlap=10,
            )

        assert "chunk_size must be at most" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_negative_overlap_raises_error(self):
        """Test that negative overlap raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ChunkingStrategy(
                strategy=ChunkStrategyType.FIXED,
                chunk_size=500,
                overlap=-1,
            )

        assert "overlap must be non-negative" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_overlap_greater_than_chunk_size_raises_error(self):
        """Test that overlap >= chunk_size raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ChunkingStrategy(
                strategy=ChunkStrategyType.FIXED,
                chunk_size=500,
                overlap=500,
            )

        assert "overlap must be less than chunk_size" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_min_chunk_size_below_one_raises_error(self):
        """Test that min_chunk_size < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ChunkingStrategy(
                strategy=ChunkStrategyType.FIXED,
                chunk_size=500,
                overlap=50,
                min_chunk_size=0,
            )

        assert "min_chunk_size must be at least 1" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_min_chunk_size_greater_than_chunk_size_raises_error(self):
        """Test that min_chunk_size >= chunk_size raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ChunkingStrategy(
                strategy=ChunkStrategyType.FIXED,
                chunk_size=500,
                overlap=50,
                min_chunk_size=500,
            )

        assert "min_chunk_size must be less than chunk_size" in str(exc_info.value)


class TestChunkingStrategies:
    """Unit tests for ChunkingStrategies factory class."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_strategy(self):
        """Test ChunkingStrategies.default() returns correct strategy."""
        strategy = ChunkingStrategies.default()

        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == 500
        assert strategy.overlap == 50

    @pytest.mark.unit
    @pytest.mark.fast
    def test_character_strategy(self):
        """Test ChunkingStrategies.character() returns correct strategy."""
        strategy = ChunkingStrategies.character()

        assert strategy.strategy == ChunkStrategyType.SEMANTIC
        assert strategy.chunk_size == 200
        assert strategy.overlap == 20

    @pytest.mark.unit
    @pytest.mark.fast
    def test_scene_strategy(self):
        """Test ChunkingStrategies.scene() returns correct strategy."""
        strategy = ChunkingStrategies.scene()

        assert strategy.strategy == ChunkStrategyType.PARAGRAPH
        assert strategy.chunk_size == 300
        assert strategy.overlap == 30

    @pytest.mark.unit
    @pytest.mark.fast
    def test_lore_strategy(self):
        """Test ChunkingStrategies.lore() returns correct strategy."""
        strategy = ChunkingStrategies.lore()

        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == 400
        assert strategy.overlap == 40

    @pytest.mark.unit
    @pytest.mark.fast
    def test_small_strategy(self):
        """Test ChunkingStrategies.small() returns small chunks."""
        strategy = ChunkingStrategies.small()

        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == 100
        assert strategy.overlap == 10

    @pytest.mark.unit
    @pytest.mark.fast
    def test_large_strategy(self):
        """Test ChunkingStrategies.large() returns large chunks."""
        strategy = ChunkingStrategies.large()

        assert strategy.strategy == ChunkStrategyType.FIXED
        assert strategy.chunk_size == 1000
        assert strategy.overlap == 100


class TestChunkStrategyType:
    """Unit tests for ChunkStrategyType enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_strategy_types_defined(self):
        """Test that all expected strategy types are defined."""
        assert ChunkStrategyType.FIXED.value == "fixed"
        assert ChunkStrategyType.SEMANTIC.value == "semantic"
        assert ChunkStrategyType.SENTENCE.value == "sentence"
        assert ChunkStrategyType.PARAGRAPH.value == "paragraph"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_strategy_type_is_string_enum(self):
        """Test that ChunkStrategyType is a string enum."""
        assert isinstance(ChunkStrategyType.FIXED, str)
        assert ChunkStrategyType.FIXED == "fixed"
