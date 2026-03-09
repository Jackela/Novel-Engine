#!/usr/bin/env python3
"""
Unit tests for Knowledge Access Control Models

Comprehensive test suite for access control models including:
- AccessLevel enum
- AccessControlRule
- AgentIdentity
"""

import sys
from unittest.mock import MagicMock, Mock

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

from src.contexts.knowledge.domain.models.access_control_rule import (
    AccessControlRule,
)
from src.contexts.knowledge.domain.models.access_level import AccessLevel
from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity


class TestAccessLevel:
    """Test suite for AccessLevel enum."""

    def test_access_level_values(self):
        """Test that enum has correct values."""
        assert AccessLevel.PUBLIC.value == "public"
        assert AccessLevel.ROLE_BASED.value == "role_based"
        assert AccessLevel.CHARACTER_SPECIFIC.value == "character_specific"

    def test_access_level_string_comparison(self):
        """Test that enum can be compared to strings."""
        assert AccessLevel.PUBLIC == "public"
        assert AccessLevel.ROLE_BASED == "role_based"


class TestAgentIdentity:
    """Test suite for AgentIdentity value object."""

    def test_agent_identity_creation_success(self):
        """Test successful AgentIdentity creation."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("narrator", "gm"),
        )

        assert agent.character_id == "char_123"
        assert "narrator" in agent.roles
        assert "gm" in agent.roles

    def test_agent_identity_creation_default_roles(self):
        """Test creation with default empty roles."""
        agent = AgentIdentity(character_id="char_123")

        assert agent.character_id == "char_123"
        assert agent.roles == ()

    def test_agent_identity_empty_character_raises_error(self):
        """Test that empty character_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            AgentIdentity(character_id="")
        assert "character_id is required" in str(exc_info.value)

    def test_agent_identity_roles_normalized_to_lowercase(self):
        """Test that roles are normalized to lowercase."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("NARRATOR", "GM"),
        )

        assert "narrator" in agent.roles
        assert "gm" in agent.roles

    def test_agent_identity_roles_whitespace_stripped(self):
        """Test that role whitespace is stripped."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("  narrator  ", "  gm  "),
        )

        assert "narrator" in agent.roles
        assert "gm" in agent.roles

    def test_agent_identity_empty_roles_filtered(self):
        """Test that empty roles are filtered out."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("narrator", "", "gm"),
        )

        assert "" not in agent.roles
        assert "narrator" in agent.roles
        assert "gm" in agent.roles

    def test_has_role_success(self):
        """Test has_role returns True for existing role."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("narrator", "gm"),
        )

        assert agent.has_role("narrator") is True
        assert agent.has_role("NARRATOR") is True  # Case insensitive

    def test_has_role_not_found(self):
        """Test has_role returns False for non-existent role."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("narrator",),
        )

        assert agent.has_role("gm") is False

    def test_has_role_empty_string(self):
        """Test has_role returns False for empty string."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("narrator",),
        )

        assert agent.has_role("") is False

    def test_roles_as_list(self):
        """Test that roles can be passed as list."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=["narrator", "gm"],  # List instead of tuple
        )

        assert "narrator" in agent.roles
        assert "gm" in agent.roles

    def test_roles_duplicates_removed(self):
        """Test that duplicate roles are removed."""
        agent = AgentIdentity(
            character_id="char_123",
            roles=("narrator", "narrator", "gm"),
        )

        assert agent.roles.count("narrator") == 1


class TestAccessControlRule:
    """Test suite for AccessControlRule."""

    def test_access_control_public_creation(self):
        """Test creation of public access rule."""
        rule = AccessControlRule(
            access_level=AccessLevel.PUBLIC,
        )

        assert rule.access_level == AccessLevel.PUBLIC

    def test_access_control_role_based_creation(self):
        """Test creation of role-based access rule."""
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("narrator", "gm"),
        )

        assert rule.access_level == AccessLevel.ROLE_BASED
        assert "narrator" in rule.allowed_roles
        assert "gm" in rule.allowed_roles

    def test_access_control_role_based_empty_raises_error(self):
        """Test that role-based without roles raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=(),
            )
        assert "requires at least one allowed role" in str(exc_info.value)

    def test_access_control_character_specific_creation(self):
        """Test creation of character-specific access rule."""
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("char_123",),
        )

        assert rule.access_level == AccessLevel.CHARACTER_SPECIFIC
        assert "char_123" in rule.allowed_character_ids

    def test_access_control_character_specific_empty_raises_error(self):
        """Test that character-specific without IDs raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=(),
            )
        assert "requires at least one allowed character ID" in str(exc_info.value)

    def test_permits_public_access(self):
        """Test that public access permits any agent."""
        rule = AccessControlRule(
            access_level=AccessLevel.PUBLIC,
        )

        agent = Mock(spec=AgentIdentity)

        assert rule.permits(agent) is True

    def test_permits_role_based_allowed(self):
        """Test role-based access with allowed role."""
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("narrator", "gm"),
        )

        agent = AgentIdentity(
            character_id="char_123",
            roles=("narrator",),
        )

        assert rule.permits(agent) is True

    def test_permits_role_based_denied(self):
        """Test role-based access with disallowed role."""
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("narrator", "gm"),
        )

        agent = AgentIdentity(
            character_id="char_123",
            roles=("player",),
        )

        assert rule.permits(agent) is False

    def test_permits_character_specific_allowed(self):
        """Test character-specific access with matching character."""
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("char_123",),
        )

        agent = AgentIdentity(character_id="char_123")

        assert rule.permits(agent) is True

    def test_permits_character_specific_denied(self):
        """Test character-specific access with different character."""
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("char_123",),
        )

        agent = AgentIdentity(character_id="char_456")

        assert rule.permits(agent) is False

    def test_allowed_roles_normalized(self):
        """Test that allowed_roles are normalized."""
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("NARRATOR", "  GM  "),
        )

        assert "narrator" in rule.allowed_roles
        assert "gm" in rule.allowed_roles

    def test_allowed_character_ids_normalized(self):
        """Test that allowed_character_ids are normalized."""
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("  char_123  ",),
        )

        assert "char_123" in rule.allowed_character_ids

    def test_allowed_character_ids_empty_filtered(self):
        """Test that empty character IDs are filtered, leaving only valid IDs."""
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("", "char_123"),
        )
        # Empty string should be filtered, leaving only valid ID
        assert rule.allowed_character_ids == ("char_123",)
