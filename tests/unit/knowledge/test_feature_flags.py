"""
Unit Tests for Knowledge Feature Flags

Tests feature flag behavior for knowledge system rollout and migration.

Constitution Compliance:
- Article III (TDD): Tests written to validate feature flag behavior
- FR-018: Tests for rollback capability
"""

import os

import pytest

from contexts.knowledge.infrastructure.config.feature_flags import KnowledgeFeatureFlags


class TestKnowledgeFeatureFlags:
    """Unit tests for KnowledgeFeatureFlags."""

    def setup_method(self):
        """Clear feature flag before each test."""
        KnowledgeFeatureFlags.clear_flag()

    def teardown_method(self):
        """Clear feature flag after each test."""
        KnowledgeFeatureFlags.clear_flag()

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_use_knowledge_base_returns_false_when_not_set(self):
        """Test that use_knowledge_base returns False when env var not set."""
        # Ensure env var is not set
        KnowledgeFeatureFlags.clear_flag()

        # Should default to False (Markdown files)
        assert KnowledgeFeatureFlags.use_knowledge_base() is False

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_use_knowledge_base_returns_true_for_truthy_values(self):
        """Test that use_knowledge_base returns True for truthy string values."""
        truthy_values = ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON"]

        for value in truthy_values:
            os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = value
            assert (
                KnowledgeFeatureFlags.use_knowledge_base() is True
            ), f"Expected True for value '{value}'"
            KnowledgeFeatureFlags.clear_flag()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_use_knowledge_base_returns_false_for_falsy_values(self):
        """Test that use_knowledge_base returns False for falsy string values."""
        falsy_values = ["false", "FALSE", "False", "0", "no", "NO", "off", "OFF"]

        for value in falsy_values:
            os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = value
            assert (
                KnowledgeFeatureFlags.use_knowledge_base() is False
            ), f"Expected False for value '{value}'"
            KnowledgeFeatureFlags.clear_flag()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_use_knowledge_base_returns_false_for_empty_string(self):
        """Test that use_knowledge_base returns False for empty string."""
        os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = ""
        assert KnowledgeFeatureFlags.use_knowledge_base() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_use_knowledge_base_returns_false_for_whitespace(self):
        """Test that use_knowledge_base returns False for whitespace-only value."""
        os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = "   "
        assert KnowledgeFeatureFlags.use_knowledge_base() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_use_knowledge_base_returns_false_for_invalid_values(self):
        """Test that use_knowledge_base returns False for invalid values."""
        invalid_values = ["maybe", "unknown", "2", "enabled", "disabled"]

        for value in invalid_values:
            os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = value
            assert (
                KnowledgeFeatureFlags.use_knowledge_base() is False
            ), f"Expected False for invalid value '{value}'"
            KnowledgeFeatureFlags.clear_flag()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_knowledge_source_returns_knowledge_base_when_enabled(self):
        """Test that get_knowledge_source returns 'knowledge_base' when enabled."""
        os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = "true"
        assert KnowledgeFeatureFlags.get_knowledge_source() == "knowledge_base"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_knowledge_source_returns_markdown_when_disabled(self):
        """Test that get_knowledge_source returns 'markdown' when disabled."""
        os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = "false"
        assert KnowledgeFeatureFlags.get_knowledge_source() == "markdown"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_knowledge_source_returns_markdown_when_not_set(self):
        """Test that get_knowledge_source returns 'markdown' by default."""
        KnowledgeFeatureFlags.clear_flag()
        assert KnowledgeFeatureFlags.get_knowledge_source() == "markdown"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_use_knowledge_base_enables_flag(self):
        """Test that set_use_knowledge_base(True) enables the flag."""
        KnowledgeFeatureFlags.set_use_knowledge_base(True)
        assert KnowledgeFeatureFlags.use_knowledge_base() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_use_knowledge_base_disables_flag(self):
        """Test that set_use_knowledge_base(False) disables the flag."""
        # First enable it
        KnowledgeFeatureFlags.set_use_knowledge_base(True)
        assert KnowledgeFeatureFlags.use_knowledge_base() is True

        # Then disable it
        KnowledgeFeatureFlags.set_use_knowledge_base(False)
        assert KnowledgeFeatureFlags.use_knowledge_base() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_clear_flag_removes_environment_variable(self):
        """Test that clear_flag removes the environment variable."""
        # Set the flag
        os.environ[KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV] = "true"
        assert KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV in os.environ

        # Clear it
        KnowledgeFeatureFlags.clear_flag()
        assert KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV not in os.environ

    @pytest.mark.unit
    @pytest.mark.fast
    def test_clear_flag_is_idempotent(self):
        """Test that clear_flag can be called multiple times safely."""
        KnowledgeFeatureFlags.clear_flag()
        KnowledgeFeatureFlags.clear_flag()  # Should not raise
        assert KnowledgeFeatureFlags.use_knowledge_base() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_feature_flag_environment_variable_name_is_correct(self):
        """Test that the environment variable name follows convention."""
        assert (
            KnowledgeFeatureFlags.USE_KNOWLEDGE_BASE_ENV
            == "NOVEL_ENGINE_USE_KNOWLEDGE_BASE"
        )

    @pytest.mark.unit
    def test_migration_scenario_enable_then_disable(self):
        """
        Test migration scenario: enable knowledge base, then rollback.

        Validates FR-018: Rollback capability
        """
        # Initial state: Markdown files
        assert KnowledgeFeatureFlags.use_knowledge_base() is False
        assert KnowledgeFeatureFlags.get_knowledge_source() == "markdown"

        # Enable knowledge base for migration
        KnowledgeFeatureFlags.set_use_knowledge_base(True)
        assert KnowledgeFeatureFlags.use_knowledge_base() is True
        assert KnowledgeFeatureFlags.get_knowledge_source() == "knowledge_base"

        # Rollback to Markdown files (FR-018)
        KnowledgeFeatureFlags.set_use_knowledge_base(False)
        assert KnowledgeFeatureFlags.use_knowledge_base() is False
        assert KnowledgeFeatureFlags.get_knowledge_source() == "markdown"
