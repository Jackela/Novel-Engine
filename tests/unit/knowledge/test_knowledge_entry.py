"""
Unit Tests for KnowledgeEntry Domain Model

TDD Approach: Tests written FIRST, must FAIL before implementation.

Constitution Compliance:
- Article III (TDD): Red-Green-Refactor cycle
- Article I (DDD): Pure domain model testing with no infrastructure
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

# NOTE: These imports will fail until domain models are implemented
# This is expected for TDD - tests must fail first
try:
    from src.contexts.knowledge.domain.events.knowledge_entry_updated import (
        KnowledgeEntryUpdated,
    )
    from src.contexts.knowledge.domain.models.access_control_rule import AccessControlRule
    from src.contexts.knowledge.domain.models.access_level import AccessLevel
    from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
    from src.contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
    from src.contexts.knowledge.domain.models.knowledge_type import KnowledgeType
except ImportError:
    # Expected to fail - models not yet implemented
    KnowledgeEntry = None
    KnowledgeType = None
    AccessControlRule = None
    AccessLevel = None
    AgentIdentity = None
    KnowledgeEntryUpdated = None


pytestmark = pytest.mark.knowledge


class TestKnowledgeEntryUpdateContent:
    """Test suite for KnowledgeEntry.update_content method."""

    @pytest.fixture
    def sample_knowledge_entry(self):
        """Create a sample knowledge entry for testing."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        entry_id = str(uuid4())
        created_at = datetime.now(timezone.utc)

        return KnowledgeEntry(
            id=entry_id,
            content="Original character profile content",
            knowledge_type=KnowledgeType.PROFILE,
            owning_character_id="char-001",
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=created_at,
            updated_at=created_at,
            created_by="user-001",
        )

    @pytest.mark.unit
    def test_update_content_success(self, sample_knowledge_entry):
        """Test successful content update returns domain event."""
        # Arrange
        new_content = "Updated character profile content"
        updated_by = "user-002"
        original_updated_at = sample_knowledge_entry.updated_at

        # Act
        event = sample_knowledge_entry.update_content(new_content, updated_by)

        # Assert
        assert sample_knowledge_entry.content == new_content
        assert sample_knowledge_entry.updated_at > original_updated_at
        assert isinstance(event, KnowledgeEntryUpdated)
        assert event.entry_id == sample_knowledge_entry.id
        assert event.updated_by == updated_by
        assert event.timestamp == sample_knowledge_entry.updated_at

    @pytest.mark.unit
    def test_update_content_empty_string_raises_error(self, sample_knowledge_entry):
        """Test that empty content raises ValueError."""
        # Arrange
        empty_content = ""
        updated_by = "user-002"

        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            sample_knowledge_entry.update_content(empty_content, updated_by)

    @pytest.mark.unit
    def test_update_content_whitespace_only_raises_error(self, sample_knowledge_entry):
        """Test that whitespace-only content raises ValueError."""
        # Arrange
        whitespace_content = "   \n\t   "
        updated_by = "user-002"

        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            sample_knowledge_entry.update_content(whitespace_content, updated_by)

    @pytest.mark.unit
    def test_update_content_preserves_immutable_fields(self, sample_knowledge_entry):
        """Test that update_content does not modify immutable fields."""
        # Arrange
        new_content = "Updated content"
        updated_by = "user-002"
        original_id = sample_knowledge_entry.id
        original_created_at = sample_knowledge_entry.created_at
        original_created_by = sample_knowledge_entry.created_by
        original_knowledge_type = sample_knowledge_entry.knowledge_type

        # Act
        sample_knowledge_entry.update_content(new_content, updated_by)

        # Assert - immutable fields unchanged
        assert sample_knowledge_entry.id == original_id
        assert sample_knowledge_entry.created_at == original_created_at
        assert sample_knowledge_entry.created_by == original_created_by
        assert sample_knowledge_entry.knowledge_type == original_knowledge_type

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_content_timestamp_is_utc(self, sample_knowledge_entry):
        """Test that updated_at timestamp uses UTC timezone."""
        # Arrange
        new_content = "Updated content"
        updated_by = "user-002"

        # Act
        event = sample_knowledge_entry.update_content(new_content, updated_by)

        # Assert
        assert sample_knowledge_entry.updated_at.tzinfo == timezone.utc
        assert event.timestamp.tzinfo == timezone.utc

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_content_multiple_times(self, sample_knowledge_entry):
        """Test multiple consecutive content updates."""
        # Arrange
        updated_by = "user-002"

        # Act - First update
        event1 = sample_knowledge_entry.update_content("First update", updated_by)
        timestamp1 = sample_knowledge_entry.updated_at

        # Act - Second update
        import time

        time.sleep(0.001)
        event2 = sample_knowledge_entry.update_content("Second update", updated_by)
        timestamp2 = sample_knowledge_entry.updated_at

        # Assert
        assert sample_knowledge_entry.content == "Second update"
        assert timestamp2 > timestamp1
        assert event1.event_id != event2.event_id  # Different events


class TestKnowledgeEntryContentValidation:
    """Test suite for KnowledgeEntry content validation."""

    @pytest.fixture
    def sample_entry_data(self):
        """Sample data for creating knowledge entries."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        return {
            "id": str(uuid4()),
            "content": "Valid content",
            "knowledge_type": KnowledgeType.PROFILE,
            "owning_character_id": "char-001",
            "access_control": AccessControlRule(access_level=AccessLevel.PUBLIC),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by": "user-001",
        }

    @pytest.mark.unit
    def test_create_entry_with_empty_content_raises_error(self, sample_entry_data):
        """Test that creating entry with empty content raises ValueError."""
        # Arrange
        sample_entry_data["content"] = ""

        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            KnowledgeEntry(**sample_entry_data)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_entry_with_valid_content_succeeds(self, sample_entry_data):
        """Test successful creation with valid content."""
        # Act
        entry = KnowledgeEntry(**sample_entry_data)

        # Assert
        assert entry.content == sample_entry_data["content"]
        assert entry.id == sample_entry_data["id"]

    @pytest.mark.unit
    @pytest.mark.unit
    def test_knowledge_type_is_immutable(self, sample_entry_data):
        """Test that knowledge_type cannot be changed after creation."""
        # Arrange
        entry = KnowledgeEntry(**sample_entry_data)

        # Act & Assert
        # Dataclass frozen=True should prevent modification
        with pytest.raises(AttributeError):
            entry.knowledge_type = KnowledgeType.OBJECTIVE

    @pytest.mark.unit
    def test_created_at_is_immutable(self, sample_entry_data):
        """Test that created_at cannot be changed after creation."""
        # Arrange
        entry = KnowledgeEntry(**sample_entry_data)
        new_timestamp = datetime.now(timezone.utc) + timedelta(days=1)

        # Act & Assert
        with pytest.raises(AttributeError):
            entry.created_at = new_timestamp

    @pytest.mark.unit
    def test_id_is_immutable(self, sample_entry_data):
        """Test that entry ID cannot be changed after creation."""
        # Arrange
        entry = KnowledgeEntry(**sample_entry_data)
        new_id = str(uuid4())

        # Act & Assert
        with pytest.raises(AttributeError):
            entry.id = new_id


class TestKnowledgeEntryIsAccessibleBy:
    """Test suite for KnowledgeEntry.is_accessible_by method (T054 - US2)."""

    @pytest.fixture
    def public_entry(self):
        """Create a public access knowledge entry."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        return KnowledgeEntry(
            id=str(uuid4()),
            content="Public knowledge content",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-001",
        )

    @pytest.fixture
    def role_based_entry(self):
        """Create a role-based access knowledge entry."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        return KnowledgeEntry(
            id=str(uuid4()),
            content="Role-based knowledge content",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer", "medical"),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-001",
        )

    @pytest.fixture
    def character_specific_entry(self):
        """Create a character-specific access knowledge entry."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        return KnowledgeEntry(
            id=str(uuid4()),
            content="Character-specific knowledge content",
            knowledge_type=KnowledgeType.PROFILE,
            owning_character_id="char-001",
            access_control=AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=("char-001", "char-002"),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-001",
        )

    @pytest.mark.unit
    def test_public_entry_accessible_by_all_agents(self, public_entry):
        """Test that PUBLIC entry is accessible by all agents."""
        # Arrange
        agent1 = AgentIdentity(character_id="char-001", roles=())
        agent2 = AgentIdentity(character_id="char-002", roles=("engineer",))
        agent3 = AgentIdentity(character_id="char-003", roles=("medical", "crew"))

        # Act & Assert
        assert public_entry.is_accessible_by(agent1) is True
        assert public_entry.is_accessible_by(agent2) is True
        assert public_entry.is_accessible_by(agent3) is True

    @pytest.mark.unit
    def test_role_based_entry_accessible_by_agents_with_matching_role(
        self, role_based_entry
    ):
        """Test that ROLE_BASED entry is accessible by agents with matching role."""
        # Arrange
        agent_with_engineer = AgentIdentity(
            character_id="char-001", roles=("engineer",)
        )
        agent_with_medical = AgentIdentity(character_id="char-002", roles=("medical",))
        agent_with_both = AgentIdentity(
            character_id="char-003", roles=("engineer", "medical")
        )

        # Act & Assert
        assert role_based_entry.is_accessible_by(agent_with_engineer) is True
        assert role_based_entry.is_accessible_by(agent_with_medical) is True
        assert role_based_entry.is_accessible_by(agent_with_both) is True

    @pytest.mark.unit
    def test_role_based_entry_not_accessible_by_agents_without_matching_role(
        self, role_based_entry
    ):
        """Test that ROLE_BASED entry is not accessible by agents without matching role."""
        # Arrange
        agent_no_roles = AgentIdentity(character_id="char-001", roles=())
        agent_wrong_role = AgentIdentity(character_id="char-002", roles=("crew",))
        agent_other_roles = AgentIdentity(
            character_id="char-003", roles=("security", "pilot")
        )

        # Act & Assert
        assert role_based_entry.is_accessible_by(agent_no_roles) is False
        assert role_based_entry.is_accessible_by(agent_wrong_role) is False
        assert role_based_entry.is_accessible_by(agent_other_roles) is False

    @pytest.mark.unit
    def test_character_specific_entry_accessible_by_allowed_characters(
        self, character_specific_entry
    ):
        """Test that CHARACTER_SPECIFIC entry is accessible by allowed characters."""
        # Arrange
        agent_char_001 = AgentIdentity(character_id="char-001", roles=())
        agent_char_002 = AgentIdentity(character_id="char-002", roles=("engineer",))

        # Act & Assert
        assert character_specific_entry.is_accessible_by(agent_char_001) is True
        assert character_specific_entry.is_accessible_by(agent_char_002) is True

    @pytest.mark.unit
    def test_character_specific_entry_not_accessible_by_other_characters(
        self, character_specific_entry
    ):
        """Test that CHARACTER_SPECIFIC entry is not accessible by other characters."""
        # Arrange
        agent_char_003 = AgentIdentity(character_id="char-003", roles=())
        agent_char_004 = AgentIdentity(character_id="char-004", roles=("engineer",))

        # Act & Assert
        assert character_specific_entry.is_accessible_by(agent_char_003) is False
        assert character_specific_entry.is_accessible_by(agent_char_004) is False

    @pytest.mark.unit
    def test_is_accessible_by_delegates_to_access_control_rule(self):
        """Test that is_accessible_by delegates to AccessControlRule.permits."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        # Arrange
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Test content",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("scientist",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-001",
        )
        agent_with_role = AgentIdentity(character_id="char-001", roles=("scientist",))
        agent_without_role = AgentIdentity(character_id="char-002", roles=("engineer",))

        # Act & Assert - should delegate to AccessControlRule.permits
        assert entry.is_accessible_by(agent_with_role) is True
        assert entry.is_accessible_by(agent_without_role) is False
