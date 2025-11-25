"""
Unit Tests for AccessControlService Domain Service

TDD Approach: Tests for domain service coordinating access control.

Constitution Compliance:
- Article III (TDD): Tests for domain service behavior
- Article I (DDD): Pure domain service testing
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

try:
    from contexts.knowledge.domain.models.access_control_rule import AccessControlRule
    from contexts.knowledge.domain.models.access_level import AccessLevel
    from contexts.knowledge.domain.models.agent_identity import AgentIdentity
    from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
    from contexts.knowledge.domain.models.knowledge_type import KnowledgeType
    from contexts.knowledge.domain.services.access_control_service import (
        AccessControlService,
    )
except ImportError:
    AccessControlService = None
    KnowledgeEntry = None
    KnowledgeType = None
    AccessControlRule = None
    AccessLevel = None
    AgentIdentity = None


pytestmark = pytest.mark.knowledge


class TestAccessControlServiceFilterAccessibleEntries:
    """Test suite for AccessControlService.filter_accessible_entries method."""

    @pytest.fixture
    def service(self):
        """Create AccessControlService instance."""
        if AccessControlService is None:
            pytest.skip("AccessControlService not yet implemented")
        return AccessControlService()

    @pytest.fixture
    def sample_entries(self):
        """Create sample entries with different access levels."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented")

        public_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Public knowledge",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-001",
        )

        engineer_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Engineer knowledge",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-002",
        )

        medical_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Medical knowledge",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("medical",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-003",
        )

        char_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Character-specific memory",
            knowledge_type=KnowledgeType.MEMORY,
            owning_character_id="char-alpha",
            access_control=AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=("char-alpha",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-004",
        )

        return [public_entry, engineer_entry, medical_entry, char_entry]

    @pytest.mark.unit
    @pytest.mark.fast
    def test_filter_returns_all_public_entries(self, service, sample_entries):
        """Test that public entries are accessible to all agents."""
        # Arrange
        agent = AgentIdentity(character_id="char-beta", roles=())

        # Act
        accessible = service.filter_accessible_entries(sample_entries, agent)

        # Assert - should get only public entry
        assert len(accessible) == 1
        assert accessible[0].access_control.access_level == AccessLevel.PUBLIC

    @pytest.mark.unit
    def test_filter_returns_public_and_role_based_entries(
        self, service, sample_entries
    ):
        """Test that agent with roles gets public + matching role entries."""
        # Arrange
        agent = AgentIdentity(character_id="char-beta", roles=("engineer",))

        # Act
        accessible = service.filter_accessible_entries(sample_entries, agent)

        # Assert - should get public + engineer entries
        assert len(accessible) == 2
        entry_ids = [e.id for e in accessible]
        assert sample_entries[0].id in entry_ids  # Public
        assert sample_entries[1].id in entry_ids  # Engineer

    @pytest.mark.unit
    def test_filter_with_multiple_roles_gets_all_matching(
        self, service, sample_entries
    ):
        """Test that agent with multiple roles gets all matching entries."""
        # Arrange
        agent = AgentIdentity(character_id="char-beta", roles=("engineer", "medical"))

        # Act
        accessible = service.filter_accessible_entries(sample_entries, agent)

        # Assert - should get public + engineer + medical
        assert len(accessible) == 3
        entry_ids = [e.id for e in accessible]
        assert sample_entries[0].id in entry_ids  # Public
        assert sample_entries[1].id in entry_ids  # Engineer
        assert sample_entries[2].id in entry_ids  # Medical

    @pytest.mark.unit
    def test_filter_with_character_id_gets_character_specific(
        self, service, sample_entries
    ):
        """Test that agent's character_id grants access to character-specific entries."""
        # Arrange
        agent = AgentIdentity(character_id="char-alpha", roles=())

        # Act
        accessible = service.filter_accessible_entries(sample_entries, agent)

        # Assert - should get public + character-specific
        assert len(accessible) == 2
        entry_ids = [e.id for e in accessible]
        assert sample_entries[0].id in entry_ids  # Public
        assert sample_entries[3].id in entry_ids  # Character-specific

    @pytest.mark.unit
    def test_filter_empty_list_returns_empty(self, service):
        """Test that filtering empty list returns empty list."""
        if AgentIdentity is None:
            pytest.skip("AgentIdentity not yet implemented")

        # Arrange
        agent = AgentIdentity(character_id="char-beta", roles=("engineer",))

        # Act
        accessible = service.filter_accessible_entries([], agent)

        # Assert
        assert len(accessible) == 0


class TestAccessControlServiceCanAccessEntry:
    """Test suite for AccessControlService.can_access_entry method."""

    @pytest.fixture
    def service(self):
        """Create AccessControlService instance."""
        if AccessControlService is None:
            pytest.skip("AccessControlService not yet implemented")
        return AccessControlService()

    @pytest.mark.unit
    def test_can_access_public_entry(self, service):
        """Test that any agent can access public entry."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Required models not yet implemented")

        # Arrange
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Public",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-001",
        )
        agent = AgentIdentity(character_id="char-001", roles=())

        # Act
        has_access = service.can_access_entry(entry, agent)

        # Assert
        assert has_access is True

    @pytest.mark.unit
    def test_can_access_role_based_with_matching_role(self, service):
        """Test that agent with matching role can access role-based entry."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Required models not yet implemented")

        # Arrange
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Engineer only",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-002",
        )
        agent = AgentIdentity(character_id="char-001", roles=("engineer",))

        # Act
        has_access = service.can_access_entry(entry, agent)

        # Assert
        assert has_access is True

    @pytest.mark.unit
    def test_cannot_access_role_based_without_matching_role(self, service):
        """Test that agent without matching role cannot access role-based entry."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Required models not yet implemented")

        # Arrange
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Engineer only",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-002",
        )
        agent = AgentIdentity(character_id="char-001", roles=("medical",))

        # Act
        has_access = service.can_access_entry(entry, agent)

        # Assert
        assert has_access is False
