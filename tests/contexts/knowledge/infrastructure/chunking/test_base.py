"""Tests for Chunking Base module.

Tests cover:
- CoherenceScore creation and validation
- CoherenceScore level categories
- BaseChunkingStrategy interface existence
- Pattern getter functions
"""

from __future__ import annotations

import re

import pytest

from src.contexts.knowledge.infrastructure.chunking.base import (
    DEFAULT_COHERENCE_THRESHOLD,
    MAX_COHERENCE_THRESHOLD,
    MIN_COHERENCE_THRESHOLD,
    BaseChunkingStrategy,
    CoherenceScore,
    get_paragraph_delim_pattern,
    get_sentence_end_pattern,
    get_word_pattern,
)

pytestmark = pytest.mark.unit


class TestCoherenceScoreCreation:
    """Test CoherenceScore dataclass creation."""

    def test_coherence_score_creation(self) -> None:
        """Test creating a CoherenceScore with valid values."""
        score = CoherenceScore(
            score=0.85,
            internal_coherence=0.82,
            boundary_quality=0.90,
            size_score=1.0,
            warnings=(),
            is_acceptable=True,
        )

        assert score.score == 0.85
        assert score.internal_coherence == 0.82
        assert score.boundary_quality == 0.90
        assert score.size_score == 1.0
        assert score.warnings == ()
        assert score.is_acceptable is True

    def test_coherence_score_defaults(self) -> None:
        """Test CoherenceScore with default values."""
        score = CoherenceScore(
            score=0.75, internal_coherence=0.70, boundary_quality=0.80, size_score=0.85
        )

        assert score.warnings == ()
        assert score.is_acceptable is True

    def test_coherence_score_clamps_values_above_max(self) -> None:
        """Test that values above MAX_COHERENCE_THRESHOLD are clamped."""
        score = CoherenceScore(
            score=1.5, internal_coherence=2.0, boundary_quality=1.2, size_score=999.0
        )

        assert score.score == MAX_COHERENCE_THRESHOLD
        assert score.internal_coherence == MAX_COHERENCE_THRESHOLD
        assert score.boundary_quality == MAX_COHERENCE_THRESHOLD
        assert score.size_score == MAX_COHERENCE_THRESHOLD

    def test_coherence_score_clamps_values_below_min(self) -> None:
        """Test that values below MIN_COHERENCE_THRESHOLD are clamped."""
        score = CoherenceScore(
            score=-0.5,
            internal_coherence=-1.0,
            boundary_quality=-0.1,
            size_score=-999.0,
        )

        assert score.score == MIN_COHERENCE_THRESHOLD
        assert score.internal_coherence == MIN_COHERENCE_THRESHOLD
        assert score.boundary_quality == MIN_COHERENCE_THRESHOLD
        assert score.size_score == MIN_COHERENCE_THRESHOLD


class TestCoherenceScoreGetLevel:
    """Test CoherenceScore get_level method."""

    def test_get_level_excellent(self) -> None:
        """Test get_level returns 'excellent' for scores >= 0.8."""
        score = CoherenceScore(
            score=0.85, internal_coherence=0.8, boundary_quality=0.8, size_score=0.8
        )

        assert score.get_level() == "excellent"

    def test_get_level_good(self) -> None:
        """Test get_level returns 'good' for scores >= 0.6 and < 0.8."""
        score = CoherenceScore(
            score=0.75, internal_coherence=0.8, boundary_quality=0.8, size_score=0.8
        )

        assert score.get_level() == "good"

        score = CoherenceScore(
            score=0.6, internal_coherence=0.8, boundary_quality=0.8, size_score=0.8
        )
        assert score.get_level() == "good"

    def test_get_level_fair(self) -> None:
        """Test get_level returns 'fair' for scores >= 0.4 and < 0.6."""
        score = CoherenceScore(
            score=0.55, internal_coherence=0.8, boundary_quality=0.8, size_score=0.8
        )

        assert score.get_level() == "fair"

        score = CoherenceScore(
            score=0.4, internal_coherence=0.8, boundary_quality=0.8, size_score=0.8
        )
        assert score.get_level() == "fair"

    def test_get_level_poor(self) -> None:
        """Test get_level returns 'poor' for scores < 0.4."""
        score = CoherenceScore(
            score=0.35, internal_coherence=0.8, boundary_quality=0.8, size_score=0.8
        )

        assert score.get_level() == "poor"

        score = CoherenceScore(
            score=0.0, internal_coherence=0.8, boundary_quality=0.8, size_score=0.8
        )
        assert score.get_level() == "poor"


class TestBaseChunkingStrategyInterface:
    """Test BaseChunkingStrategy abstract interface."""

    def test_base_chunking_strategy_is_abstract(self) -> None:
        """Test that BaseChunkingStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseChunkingStrategy()

    def test_base_chunking_strategy_has_chunk_method(self) -> None:
        """Test that BaseChunkingStrategy defines chunk method."""
        assert hasattr(BaseChunkingStrategy, "chunk")

    def test_base_chunking_strategy_has_supports_strategy_type(self) -> None:
        """Test that BaseChunkingStrategy defines supports_strategy_type method."""
        assert hasattr(BaseChunkingStrategy, "supports_strategy_type")


class TestPatternGetters:
    """Test pattern getter functions."""

    def test_get_word_pattern_returns_compiled_pattern(self) -> None:
        """Test get_word_pattern returns a compiled regex pattern."""
        pattern = get_word_pattern()

        assert isinstance(pattern, re.Pattern)

    def test_get_word_pattern_matches_words(self) -> None:
        """Test word pattern matches words."""
        pattern = get_word_pattern()

        text = "Hello world test"
        matches = pattern.findall(text)

        assert len(matches) == 3
        assert matches == ["Hello", "world", "test"]

    def test_get_sentence_end_pattern_returns_compiled_pattern(self) -> None:
        """Test get_sentence_end_pattern returns a compiled regex pattern."""
        pattern = get_sentence_end_pattern()

        assert isinstance(pattern, re.Pattern)

    def test_get_sentence_end_pattern_matches_sentence_endings(self) -> None:
        """Test sentence end pattern matches sentence endings."""
        pattern = get_sentence_end_pattern()

        text = "First sentence. Second sentence! Third question? Still third?"
        matches = pattern.findall(text)

        # Pattern includes the whitespace after punctuation
        assert len(matches) >= 2  # At least 2 matches expected

    def test_get_paragraph_delim_pattern_returns_compiled_pattern(self) -> None:
        """Test get_paragraph_delim_pattern returns a compiled regex pattern."""
        pattern = get_paragraph_delim_pattern()

        assert isinstance(pattern, re.Pattern)

    def test_get_paragraph_delim_pattern_matches_paragraph_breaks(self) -> None:
        """Test paragraph delimiter pattern matches paragraph breaks."""
        pattern = get_paragraph_delim_pattern()

        text = "Para 1\n\nPara 2\n\n\nPara 3"
        matches = pattern.findall(text)

        assert len(matches) == 2


class TestConstants:
    """Test module constants."""

    def test_min_coherence_threshold(self) -> None:
        """Test MIN_COHERENCE_THRESHOLD constant."""
        assert MIN_COHERENCE_THRESHOLD == 0.0

    def test_max_coherence_threshold(self) -> None:
        """Test MAX_COHERENCE_THRESHOLD constant."""
        assert MAX_COHERENCE_THRESHOLD == 1.0

    def test_default_coherence_threshold(self) -> None:
        """Test DEFAULT_COHERENCE_THRESHOLD constant."""
        assert DEFAULT_COHERENCE_THRESHOLD == 0.6
