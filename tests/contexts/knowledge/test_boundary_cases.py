"""
Boundary Cases Tests for Knowledge Context

Tests edge cases, boundary conditions, and limit cases for knowledge context modules.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.contexts.knowledge.domain.models.access_control_rule import AccessControlRule
from src.contexts.knowledge.domain.models.access_level import AccessLevel
from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
from src.contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
from src.contexts.knowledge.domain.models.knowledge_type import KnowledgeType
from src.contexts.knowledge.domain.models.source_type import SourceType
from src.contexts.knowledge.domain.models.token_usage import TokenUsage, TokenUsageStats

pytestmark = pytest.mark.unit



class TestKnowledgeEntryBoundaryCases:
    """Boundary tests for KnowledgeEntry domain model."""

    def test_create_with_empty_content_raises(self):
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            KnowledgeEntry(
                id=str(uuid4()),
                content="",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by="test_user",
            )

    def test_create_with_whitespace_only_content_raises(self):
        """Test that whitespace-only content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            KnowledgeEntry(
                id=str(uuid4()),
                content="   \n\t  ",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by="test_user",
            )

    def test_create_with_very_long_content(self):
        """Test that very long content is handled properly."""
        long_content = "A" * 100000  # 100k characters
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content=long_content,
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test_user",
        )
        assert len(entry.content) == 100000

    def test_create_with_empty_id_raises(self):
        """Test that empty id raises ValueError."""
        with pytest.raises(ValueError, match="id is required"):
            KnowledgeEntry(
                id="",
                content="Valid content",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by="test_user",
            )

    def test_create_with_empty_created_by_raises(self):
        """Test that empty created_by raises ValueError."""
        with pytest.raises(ValueError, match="created_by is required"):
            KnowledgeEntry(
                id=str(uuid4()),
                content="Valid content",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by="",
            )

    def test_create_with_updated_before_created_raises(self):
        """Test that updated_at before created_at raises ValueError."""
        created = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError, match="updated_at cannot be earlier"):
            KnowledgeEntry(
                id=str(uuid4()),
                content="Valid content",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
                created_at=created,
                updated_at=updated,
                created_by="test_user",
            )

    def test_content_gets_stripped(self):
        """Test that content gets whitespace stripped."""
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="  Content with spaces  ",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test_user",
        )
        assert entry.content == "Content with spaces"


class TestTokenUsageBoundaryCases:
    """Boundary tests for TokenUsage domain model."""

    def test_create_with_negative_input_tokens_raises(self):
        """Test that negative input tokens raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4",
                input_tokens=-1,
                output_tokens=10,
            )

    def test_create_with_negative_output_tokens_raises(self):
        """Test that negative output tokens raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4",
                input_tokens=10,
                output_tokens=-1,
            )

    def test_create_with_negative_latency_raises(self):
        """Test that negative latency raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            TokenUsage.create(
                provider="openai",
                model_name="gpt-4",
                input_tokens=10,
                output_tokens=10,
                latency_ms=-100,
            )

    def test_create_with_zero_tokens(self):
        """Test that zero tokens is allowed."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4",
            input_tokens=0,
            output_tokens=0,
        )
        assert usage.total_tokens == 0
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_create_with_very_large_token_count(self):
        """Test handling of very large token counts."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4",
            input_tokens=10_000_000,
            output_tokens=10_000_000,
        )
        assert usage.total_tokens == 20_000_000


class TestTokenUsageStatsBoundaryCases:
    """Boundary tests for TokenUsageStats."""

    def test_from_usages_with_empty_list(self):
        """Test stats creation from empty usage list."""
        stats = TokenUsageStats.from_usages([])
        assert stats.total_requests == 0
        assert stats.total_tokens == 0

    def test_from_usages_with_single_item(self):
        """Test stats from single usage."""
        usage = TokenUsage.create(
            provider="openai",
            model_name="gpt-4",
            input_tokens=100,
            output_tokens=50,
        )
        stats = TokenUsageStats.from_usages([usage])
        assert stats.total_requests == 1
        assert stats.total_tokens == 150
        assert stats.total_input_tokens == 100
        assert stats.total_output_tokens == 50

    def test_validation_negative_requests_raises(self):
        """Test that negative total_requests in stats raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            TokenUsageStats(
                provider="all",
                model_name="all",
                workspace_id=None,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                total_requests=-1,
            )

    def test_validation_mismatched_counts_raises(self):
        """Test that mismatched counts raise ValueError."""
        with pytest.raises(ValueError, match="must equal"):
            TokenUsageStats(
                provider="all",
                model_name="all",
                workspace_id=None,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                total_requests=10,
                successful_requests=5,
                failed_requests=3,  # Should be 5
            )

    def test_validation_mismatched_tokens_raises(self):
        """Test that mismatched token counts raise ValueError."""
        with pytest.raises(ValueError, match="must equal"):
            TokenUsageStats(
                provider="all",
                model_name="all",
                workspace_id=None,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                total_tokens=100,
                total_input_tokens=50,
                total_output_tokens=30,  # Should be 50
            )


class TestAgentIdentityBoundaryCases:
    """Boundary tests for AgentIdentity."""

    def test_create_with_minimal_values(self):
        """Test creating agent with minimal required values."""
        agent = AgentIdentity(
            character_id="char_001",
        )
        assert agent.character_id == "char_001"

    def test_create_with_roles(self):
        """Test creating agent with roles."""
        agent = AgentIdentity(
            character_id="char_001",
            roles=("admin", "reader"),
        )
        assert agent.has_role("admin") is True
        assert agent.has_role("ADMIN") is True  # Case insensitive

    def test_create_with_special_characters_in_id(self):
        """Test creating agent with special characters."""
        agent = AgentIdentity(
            character_id="char_日本語_001",
        )
        assert "日本語" in agent.character_id


class TestAccessControlBoundaryCases:
    """Boundary tests for AccessControlRule."""

    def test_public_access_permits_anyone(self):
        """Test that public access permits any agent."""
        rule = AccessControlRule(access_level=AccessLevel.PUBLIC)
        agent = AgentIdentity(character_id="any_agent")
        assert rule.permits(agent) is True

    def test_role_based_access_denies_without_role(self):
        """Test that role-based access denies without matching role."""
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("admin",),
        )
        agent = AgentIdentity(character_id="user", roles=("reader",))
        assert rule.permits(agent) is False

    def test_role_based_access_permits_with_role(self):
        """Test that role-based access permits with matching role."""
        rule = AccessControlRule(
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=("admin",),
        )
        agent = AgentIdentity(character_id="admin_user", roles=("admin",))
        assert rule.permits(agent) is True

    def test_character_specific_access_denies_unauthorized(self):
        """Test that character-specific access denies unauthorized."""
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("char_001",),
        )
        agent = AgentIdentity(character_id="unauthorized")
        assert rule.permits(agent) is False

    def test_character_specific_access_permits_authorized(self):
        """Test that character-specific access permits authorized."""
        rule = AccessControlRule(
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=("char_001",),
        )
        agent = AgentIdentity(character_id="char_001")
        assert rule.permits(agent) is True

    def test_role_based_requires_roles(self):
        """Test that role-based access requires at least one role."""
        with pytest.raises(ValueError, match="requires at least one"):
            AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=(),
            )

    def test_character_specific_requires_ids(self):
        """Test that character-specific access requires at least one character ID."""
        with pytest.raises(ValueError, match="requires at least one"):
            AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=(),
            )


class TestKnowledgeTypeBoundaryCases:
    """Boundary tests for KnowledgeType enum."""

    def test_all_enum_values_exist(self):
        """Test that all expected enum values exist."""
        expected = [
            KnowledgeType.PROFILE,
            KnowledgeType.OBJECTIVE,
            KnowledgeType.MEMORY,
            KnowledgeType.LORE,
            KnowledgeType.RULES,
        ]
        for enum_val in expected:
            assert isinstance(enum_val, KnowledgeType)

    def test_enum_values_are_unique(self):
        """Test that all enum values are unique."""
        values = [e.value for e in KnowledgeType]
        assert len(values) == len(set(values))


class TestSourceTypeBoundaryCases:
    """Boundary tests for SourceType."""

    def test_all_source_types_exist(self):
        """Test that all expected source types exist."""
        expected = [
            SourceType.CHARACTER,
            SourceType.LORE,
            SourceType.SCENE,
            SourceType.PLOTLINE,
            SourceType.ITEM,
            SourceType.LOCATION,
        ]
        for source_type in expected:
            assert isinstance(source_type, SourceType)

    def test_from_string_valid(self):
        """Test from_string with valid values."""
        assert SourceType.from_string("CHARACTER") == SourceType.CHARACTER
        assert SourceType.from_string("character") == SourceType.CHARACTER
        assert SourceType.from_string("lore") == SourceType.LORE

    def test_from_string_invalid(self):
        """Test from_string with invalid value."""
        with pytest.raises(ValueError, match="Unknown SourceType"):
            SourceType.from_string("invalid")
