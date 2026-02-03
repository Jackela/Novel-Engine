"""
Unit Tests for SourceType Enumeration

Tests the source type enumeration for RAG knowledge entries.

Warzone 4: AI Brain - BRAIN-003
Tests source type validation and conversion.

Constitution Compliance:
- Article III (TDD): Tests written to validate enumeration behavior
- Article I (DDD): Tests domain model behavior
"""

import pytest

from src.contexts.knowledge.domain.models.source_type import SourceType


class TestSourceType:
    """Unit tests for SourceType enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_source_types_defined(self):
        """Test that all expected source types are defined."""
        assert SourceType.CHARACTER.value == "CHARACTER"
        assert SourceType.LORE.value == "LORE"
        assert SourceType.SCENE.value == "SCENE"
        assert SourceType.PLOTLINE.value == "PLOTLINE"
        assert SourceType.ITEM.value == "ITEM"
        assert SourceType.LOCATION.value == "LOCATION"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_source_type_is_string_enum(self):
        """Test that SourceType is a string enum."""
        assert isinstance(SourceType.CHARACTER, str)
        assert SourceType.CHARACTER == "CHARACTER"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_string_valid_value(self):
        """Test from_string with valid values."""
        assert SourceType.from_string("CHARACTER") == SourceType.CHARACTER
        assert SourceType.from_string("character") == SourceType.CHARACTER
        assert SourceType.from_string("  character  ") == SourceType.CHARACTER

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_string_invalid_value_raises_error(self):
        """Test from_string with invalid value raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            SourceType.from_string("INVALID")

        assert "Unknown SourceType" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_string_empty_raises_error(self):
        """Test from_string with empty string raises ValueError."""
        with pytest.raises(ValueError):
            SourceType.from_string("")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_source_types_from_string(self):
        """Test from_string works for all source types."""
        test_cases = [
            ("CHARACTER", SourceType.CHARACTER),
            ("LORE", SourceType.LORE),
            ("SCENE", SourceType.SCENE),
            ("PLOTLINE", SourceType.PLOTLINE),
            ("ITEM", SourceType.ITEM),
            ("LOCATION", SourceType.LOCATION),
        ]

        for value, expected in test_cases:
            assert SourceType.from_string(value) == expected
            assert SourceType.from_string(value.lower()) == expected
