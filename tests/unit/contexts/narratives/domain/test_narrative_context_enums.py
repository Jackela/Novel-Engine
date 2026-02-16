#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Enum Value Objects

Test suite covering ContextScope and ContextType enum validation
and behavior in the Narrative Context domain layer.
"""

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
)

pytestmark = pytest.mark.unit


class TestContextScopeEnum:
    """Test suite for ContextScope enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_scope_levels_exist(self):
        """Test that all expected scope levels are defined."""
        expected_scopes = {"GLOBAL", "ARC", "CHAPTER", "SCENE", "MOMENT"}
        actual_scopes = {item.name for item in ContextScope}
        assert actual_scopes == expected_scopes

    @pytest.mark.unit
    @pytest.mark.fast
    def test_scope_string_values(self):
        """Test that scope enum values have correct string representations."""
        assert ContextScope.GLOBAL.value == "global"
        assert ContextScope.ARC.value == "arc"
        assert ContextScope.CHAPTER.value == "chapter"
        assert ContextScope.SCENE.value == "scene"
        assert ContextScope.MOMENT.value == "moment"

    @pytest.mark.unit
    def test_scope_logical_ordering(self):
        """Test that scope levels represent logical hierarchy."""
        scope_hierarchy = {
            ContextScope.GLOBAL: 5,
            ContextScope.ARC: 4,
            ContextScope.CHAPTER: 3,
            ContextScope.SCENE: 2,
            ContextScope.MOMENT: 1,
        }

        assert scope_hierarchy[ContextScope.GLOBAL] > scope_hierarchy[ContextScope.ARC]
        assert scope_hierarchy[ContextScope.ARC] > scope_hierarchy[ContextScope.CHAPTER]
        assert (
            scope_hierarchy[ContextScope.CHAPTER] > scope_hierarchy[ContextScope.SCENE]
        )
        assert (
            scope_hierarchy[ContextScope.SCENE] > scope_hierarchy[ContextScope.MOMENT]
        )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_scope_uniqueness(self):
        """Test that all scope values are unique."""
        values = [item.value for item in ContextScope]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_scope_membership(self):
        """Test scope membership operations."""
        assert ContextScope.GLOBAL in ContextScope
        assert "global" == ContextScope.GLOBAL.value
        assert ContextScope.GLOBAL == ContextScope("global")


class TestContextTypeEnum:
    """Test suite for ContextType enum."""

    @pytest.mark.unit
    def test_all_context_types_exist(self):
        """Test that all expected context types are defined."""
        expected_types = {
            "SETTING",
            "CULTURAL",
            "HISTORICAL",
            "SOCIAL",
            "POLITICAL",
            "ECONOMIC",
            "TECHNOLOGICAL",
            "MAGICAL",
            "EMOTIONAL",
            "THEMATIC",
            "INTERPERSONAL",
            "ENVIRONMENTAL",
        }
        actual_types = {item.name for item in ContextType}
        assert actual_types == expected_types

    @pytest.mark.unit
    def test_context_type_string_values(self):
        """Test that context type enum values have correct string representations."""
        assert ContextType.SETTING.value == "setting"
        assert ContextType.CULTURAL.value == "cultural"
        assert ContextType.HISTORICAL.value == "historical"
        assert ContextType.SOCIAL.value == "social"
        assert ContextType.POLITICAL.value == "political"
        assert ContextType.ECONOMIC.value == "economic"
        assert ContextType.TECHNOLOGICAL.value == "technological"
        assert ContextType.MAGICAL.value == "magical"
        assert ContextType.EMOTIONAL.value == "emotional"
        assert ContextType.THEMATIC.value == "thematic"
        assert ContextType.INTERPERSONAL.value == "interpersonal"
        assert ContextType.ENVIRONMENTAL.value == "environmental"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_context_type_uniqueness(self):
        """Test that all context type values are unique."""
        values = [item.value for item in ContextType]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_context_type_membership(self):
        """Test context type membership operations."""
        assert ContextType.SETTING in ContextType
        assert "setting" == ContextType.SETTING.value
        assert ContextType.SETTING == ContextType("setting")
