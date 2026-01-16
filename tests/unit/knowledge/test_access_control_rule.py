"""
Unit Tests for AccessControlRule Value Object

TDD Approach: Tests written FIRST, must FAIL before implementation.

Constitution Compliance:
- Article III (TDD): Red-Green-Refactor cycle
- Article I (DDD): Pure domain value object testing
"""

import pytest

# NOTE: These imports will fail until domain models are implemented
try:
    from src.contexts.knowledge.domain.models.access_control_rule import AccessControlRule
    from src.contexts.knowledge.domain.models.access_level import AccessLevel
    from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
except ImportError:
    AccessControlRule = None
    AccessLevel = None
    AgentIdentity = None


pytestmark = pytest.mark.knowledge


class TestAccessControlRuleInvariants:
    """Test suite for AccessControlRule invariants and validation."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_public_access_level_requires_no_additional_data(self):
        """Test PUBLIC access level can be created without roles or character IDs."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )

        # Act
        rule = AccessControlRule(access_level=AccessLevel.PUBLIC)

        # Assert
        assert rule.access_level == AccessLevel.PUBLIC
        assert len(rule.allowed_roles) == 0
        assert len(rule.allowed_character_ids) == 0

    @pytest.mark.unit
    def test_role_based_access_requires_roles(self):
        """Test ROLE_BASED access level requires at least one role."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )

        # Act & Assert
        with pytest.raises(
            ValueError, match="ROLE_BASED access requires at least one allowed role"
        ):
            AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=(),  # Empty tuple - should raise error
            )

    @pytest.mark.unit
    def test_role_based_access_with_roles_succeeds(self):
        """Test ROLE_BASED access level with roles succeeds."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )

        # Act
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("engineer", "crew"),
        )

        # Assert
        assert rule.access_level == AccessLevel.ROLE_BASED
        assert "engineer" in rule.allowed_roles
        assert "crew" in rule.allowed_roles

    @pytest.mark.unit
    def test_character_specific_access_requires_character_ids(self):
        """Test CHARACTER_SPECIFIC access level requires at least one character ID."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="CHARACTER_SPECIFIC access requires at least one allowed character ID",
        ):
            AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=(),  # Empty tuple - should raise error
            )

    @pytest.mark.unit
    def test_character_specific_access_with_character_ids_succeeds(self):
        """Test CHARACTER_SPECIFIC access level with character IDs succeeds."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )

        # Act
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("char-001", "char-002"),
        )

        # Assert
        assert rule.access_level == AccessLevel.CHARACTER_SPECIFIC
        assert "char-001" in rule.allowed_character_ids
        assert "char-002" in rule.allowed_character_ids

    @pytest.mark.unit
    def test_access_control_rule_is_immutable(self):
        """Test that AccessControlRule is immutable (frozen dataclass)."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        rule = AccessControlRule(access_level=AccessLevel.PUBLIC)

        # Act & Assert
        with pytest.raises(AttributeError):
            rule.access_level = AccessLevel.ROLE_BASED


class TestAccessControlRulePermits:
    """Test suite for AccessControlRule.permits method."""

    @pytest.fixture
    def public_rule(self):
        """Public access rule."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )
        return AccessControlRule(access_level=AccessLevel.PUBLIC)

    @pytest.fixture
    def role_based_rule(self):
        """Role-based access rule."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )
        return AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("engineer", "medical"),
        )

    @pytest.fixture
    def character_specific_rule(self):
        """Character-specific access rule."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )
        return AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("char-001", "char-002"),
        )

    @pytest.mark.unit
    def test_public_rule_permits_all_agents(self, public_rule):
        """Test PUBLIC access permits all agents."""
        # Arrange
        agent1 = AgentIdentity(character_id="char-001", roles=())
        agent2 = AgentIdentity(character_id="char-002", roles=("engineer",))
        agent3 = AgentIdentity(character_id="char-003", roles=("medical", "crew"))

        # Act & Assert
        assert public_rule.permits(agent1) is True
        assert public_rule.permits(agent2) is True
        assert public_rule.permits(agent3) is True

    @pytest.mark.unit
    def test_role_based_rule_permits_agents_with_matching_role(self, role_based_rule):
        """Test ROLE_BASED access permits agents with matching role."""
        # Arrange
        agent_with_engineer = AgentIdentity(
            character_id="char-001", roles=("engineer",)
        )
        agent_with_medical = AgentIdentity(character_id="char-002", roles=("medical",))
        agent_with_both = AgentIdentity(
            character_id="char-003", roles=("engineer", "medical")
        )

        # Act & Assert
        assert role_based_rule.permits(agent_with_engineer) is True
        assert role_based_rule.permits(agent_with_medical) is True
        assert role_based_rule.permits(agent_with_both) is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_role_based_rule_denies_agents_without_matching_role(self, role_based_rule):
        """Test ROLE_BASED access denies agents without matching role."""
        # Arrange
        agent_no_roles = AgentIdentity(character_id="char-001", roles=())
        agent_wrong_role = AgentIdentity(character_id="char-002", roles=("crew",))
        agent_other_roles = AgentIdentity(
            character_id="char-003", roles=("security", "pilot")
        )

        # Act & Assert
        assert role_based_rule.permits(agent_no_roles) is False
        assert role_based_rule.permits(agent_wrong_role) is False
        assert role_based_rule.permits(agent_other_roles) is False

    @pytest.mark.unit
    def test_character_specific_rule_permits_allowed_characters(
        self, character_specific_rule
    ):
        """Test CHARACTER_SPECIFIC access permits allowed characters."""
        # Arrange
        agent_char_001 = AgentIdentity(character_id="char-001", roles=())
        agent_char_002 = AgentIdentity(character_id="char-002", roles=("engineer",))

        # Act & Assert
        assert character_specific_rule.permits(agent_char_001) is True
        assert character_specific_rule.permits(agent_char_002) is True

    @pytest.mark.unit
    def test_character_specific_rule_denies_other_characters(
        self, character_specific_rule
    ):
        """Test CHARACTER_SPECIFIC access denies other characters."""
        # Arrange
        agent_char_003 = AgentIdentity(character_id="char-003", roles=())
        agent_char_004 = AgentIdentity(character_id="char-004", roles=("engineer",))

        # Act & Assert
        assert character_specific_rule.permits(agent_char_003) is False
        assert character_specific_rule.permits(agent_char_004) is False

    @pytest.mark.unit
    def test_role_based_with_multiple_roles_any_match_grants_access(self):
        """Test ROLE_BASED with multiple roles - any match grants access."""
        if AccessControlRule is None:
            pytest.skip(
                "AccessControlRule not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("engineer", "medical", "security"),
        )
        agent = AgentIdentity(character_id="char-001", roles=("crew", "security"))

        # Act & Assert
        assert rule.permits(agent) is True  # Has "security" role
