"""
Integration Tests for PostgreSQLKnowledgeRepository

TDD Approach: Tests written FIRST, must FAIL before implementation.
These tests require a real PostgreSQL database connection.

Constitution Compliance:
- Article III (TDD): Red-Green-Refactor cycle
- Article IV (SSOT): PostgreSQL as single source of truth
- Article II (Hexagonal): Infrastructure adapter testing
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

# NOTE: These imports will fail until infrastructure is implemented
try:
    from contexts.knowledge.domain.models.access_control_rule import AccessControlRule
    from contexts.knowledge.domain.models.access_level import AccessLevel
    from contexts.knowledge.domain.models.agent_identity import AgentIdentity
    from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
    from contexts.knowledge.domain.models.knowledge_type import KnowledgeType
    from contexts.knowledge.infrastructure.repositories.postgresql_knowledge_repository import (
        PostgreSQLKnowledgeRepository,
    )
except ImportError:
    PostgreSQLKnowledgeRepository = None
    KnowledgeEntry = None
    KnowledgeType = None
    AccessControlRule = None
    AccessLevel = None
    AgentIdentity = None


pytestmark = [
    pytest.mark.knowledge,
    pytest.mark.integration,
    pytest.mark.requires_services,
]


@pytest_asyncio.fixture
async def db_session():
    """
    Create database session for integration tests.

    NOTE: This fixture assumes PostgreSQL is running locally.
    Integration tests will be skipped if database is unavailable.
    """
    if PostgreSQLKnowledgeRepository is None:
        pytest.skip(
            "PostgreSQLKnowledgeRepository not yet implemented (TDD - expected to fail)"
        )

    try:
        from core_platform.persistence.database import db_manager

        # Initialize database if needed
        if not db_manager._is_initialized:
            await db_manager.initialize(
                {
                    "url": "postgresql://postgres:postgres@localhost:5432/novel_engine_test",
                    "pool_size": 5,
                    "echo": False,
                }
            )

        async with db_manager.get_async_session() as session:
            yield session
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest_asyncio.fixture
async def repository(db_session):
    """Create repository instance with database session."""
    if PostgreSQLKnowledgeRepository is None:
        pytest.skip(
            "PostgreSQLKnowledgeRepository not yet implemented (TDD - expected to fail)"
        )

    repo = PostgreSQLKnowledgeRepository(session=db_session)

    # Clean up any existing test data
    await db_session.execute(
        text("DELETE FROM knowledge_entries WHERE created_by LIKE 'test-user-%'")
    )
    await db_session.commit()

    yield repo

    # Cleanup after tests
    await db_session.execute(
        text("DELETE FROM knowledge_entries WHERE created_by LIKE 'test-user-%'")
    )
    await db_session.commit()


@pytest.fixture
def sample_entry():
    """Create a sample knowledge entry for testing."""
    if KnowledgeEntry is None:
        pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

    entry_id = str(uuid4())
    created_at = datetime.now(timezone.utc)

    return KnowledgeEntry(
        id=entry_id,
        content="Test character profile for integration testing",
        knowledge_type=KnowledgeType.PROFILE,
        owning_character_id="test-char-001",
        access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
        created_at=created_at,
        updated_at=created_at,
        created_by="test-user-001",
    )


class TestPostgreSQLKnowledgeRepositorySave:
    """Integration tests for repository.save method."""

    @pytest.mark.asyncio
    async def test_save_new_entry_persists_to_database(self, repository, sample_entry):
        """Test saving a new knowledge entry persists it to PostgreSQL."""
        # Act
        await repository.save(sample_entry)

        # Assert - retrieve and verify
        retrieved = await repository.get_by_id(sample_entry.id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.content == sample_entry.content
        assert retrieved.knowledge_type == sample_entry.knowledge_type
        assert retrieved.created_by == sample_entry.created_by

    @pytest.mark.asyncio
    async def test_save_entry_with_character_specific_access(self, repository):
        """Test saving entry with CHARACTER_SPECIFIC access level."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        # Arrange
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Private character knowledge",
            knowledge_type=KnowledgeType.MEMORY,
            owning_character_id="test-char-002",
            access_control=AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=("test-char-002", "test-char-003"),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-002",
        )

        # Act
        await repository.save(entry)

        # Assert
        retrieved = await repository.get_by_id(entry.id)
        assert retrieved.access_control.access_level == AccessLevel.CHARACTER_SPECIFIC
        assert "test-char-002" in retrieved.access_control.allowed_character_ids
        assert "test-char-003" in retrieved.access_control.allowed_character_ids

    @pytest.mark.asyncio
    async def test_save_entry_with_role_based_access(self, repository):
        """Test saving entry with ROLE_BASED access level."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        # Arrange
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Engineering technical documentation",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,  # World knowledge
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer", "medical"),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-003",
        )

        # Act
        await repository.save(entry)

        # Assert
        retrieved = await repository.get_by_id(entry.id)
        assert retrieved.access_control.access_level == AccessLevel.ROLE_BASED
        assert "engineer" in retrieved.access_control.allowed_roles
        assert "medical" in retrieved.access_control.allowed_roles

    @pytest.mark.asyncio
    async def test_save_updates_existing_entry(self, repository, sample_entry):
        """Test that saving an existing entry updates it."""
        # Arrange - save initial entry
        await repository.save(sample_entry)

        # Modify entry
        sample_entry.content = "Updated content for integration test"
        sample_entry.updated_at = datetime.now(timezone.utc)

        # Act - save updated entry
        await repository.save(sample_entry)

        # Assert
        retrieved = await repository.get_by_id(sample_entry.id)
        assert retrieved.content == "Updated content for integration test"
        assert retrieved.updated_at > retrieved.created_at

    @pytest.mark.asyncio
    async def test_save_with_empty_content_raises_database_constraint_error(
        self, repository
    ):
        """Test that database constraint prevents empty content."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        # Arrange - attempt to create entry with empty content
        # This should be prevented at domain layer, but database also enforces it
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="   ",  # Whitespace only
            knowledge_type=KnowledgeType.PROFILE,
            owning_character_id="test-char-001",
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-004",
        )

        # Act & Assert - database constraint should fail
        with pytest.raises(Exception):  # Database constraint violation
            await repository.save(entry)


class TestPostgreSQLKnowledgeRepositoryGetById:
    """Integration tests for repository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_entry_when_exists(self, repository, sample_entry):
        """Test retrieving an existing entry by ID."""
        # Arrange
        await repository.save(sample_entry)

        # Act
        retrieved = await repository.get_by_id(sample_entry.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.content == sample_entry.content
        assert retrieved.knowledge_type == sample_entry.knowledge_type

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_exists(self, repository):
        """Test retrieving a non-existent entry returns None."""
        # Arrange
        non_existent_id = str(uuid4())

        # Act
        retrieved = await repository.get_by_id(non_existent_id)

        # Assert
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_id_reconstructs_access_control_correctly(self, repository):
        """Test that access control rules are correctly reconstructed from database."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        # Arrange - save entry with complex access control
        entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Complex access control test",
            knowledge_type=KnowledgeType.OBJECTIVE,
            owning_character_id="test-char-001",
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer", "medical", "security"),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-005",
        )
        await repository.save(entry)

        # Act
        retrieved = await repository.get_by_id(entry.id)

        # Assert - access control preserved
        assert retrieved.access_control.access_level == AccessLevel.ROLE_BASED
        assert len(retrieved.access_control.allowed_roles) == 3
        assert "engineer" in retrieved.access_control.allowed_roles


class TestPostgreSQLKnowledgeRepositoryDelete:
    """Integration tests for repository.delete method."""

    @pytest.mark.asyncio
    async def test_delete_removes_entry_from_database(self, repository, sample_entry):
        """Test deleting an entry removes it from PostgreSQL."""
        # Arrange
        await repository.save(sample_entry)

        # Act
        await repository.delete(sample_entry.id)

        # Assert - entry should not be retrievable
        retrieved = await repository.get_by_id(sample_entry.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_non_existent_entry_succeeds(self, repository):
        """Test deleting a non-existent entry does not raise error."""
        # Arrange
        non_existent_id = str(uuid4())

        # Act & Assert - should succeed (idempotent operation)
        await repository.delete(non_existent_id)

    @pytest.mark.asyncio
    async def test_delete_cascades_to_audit_log(
        self, repository, sample_entry, db_session
    ):
        """Test that deleting entry also removes audit log entries (CASCADE)."""
        # Arrange - save entry
        await repository.save(sample_entry)

        # Insert audit log entry (would normally be done by audit log writer)
        await db_session.execute(
            text(
                """
            INSERT INTO knowledge_audit_log (timestamp, user_id, entry_id, change_type)
            VALUES (NOW(), :user_id, :entry_id, 'created')
            """
            ),
            {"user_id": "test-user-001", "entry_id": sample_entry.id},
        )
        await db_session.commit()

        # Act - delete entry
        await repository.delete(sample_entry.id)

        # Assert - audit log entries should also be deleted (CASCADE)
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM knowledge_audit_log WHERE entry_id = :entry_id"),
            {"entry_id": sample_entry.id},
        )
        audit_count = result.scalar()
        assert audit_count == 0


class TestPostgreSQLKnowledgeRepositoryRetrieveForAgent:
    """Integration tests for repository.retrieve_for_agent method (T055 - US2)."""

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_returns_only_accessible_entries(self, repository):
        """Test that retrieve_for_agent filters entries based on access control."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Models not yet implemented (TDD - expected to fail)")

        # Arrange - create entries with different access levels
        public_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Public world lore",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-100",
        )

        engineer_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Engineering technical specs",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-101",
        )

        medical_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Medical procedures",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("medical",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-102",
        )

        char_specific_entry = KnowledgeEntry(
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
            created_by="test-user-103",
        )

        # Save all entries
        await repository.save(public_entry)
        await repository.save(engineer_entry)
        await repository.save(medical_entry)
        await repository.save(char_specific_entry)

        # Act - retrieve for engineer agent
        engineer_agent = AgentIdentity(character_id="char-beta", roles=("engineer",))
        accessible_entries = await repository.retrieve_for_agent(engineer_agent)

        # Assert - should get public + engineer entries only
        entry_ids = [e.id for e in accessible_entries]
        assert public_entry.id in entry_ids
        assert engineer_entry.id in entry_ids
        assert medical_entry.id not in entry_ids  # Wrong role
        assert char_specific_entry.id not in entry_ids  # Wrong character

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_public_access_returns_all_public_entries(
        self, repository
    ):
        """Test that agents can access all PUBLIC entries."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Models not yet implemented (TDD - expected to fail)")

        # Arrange - create multiple public entries
        public_entry_1 = KnowledgeEntry(
            id=str(uuid4()),
            content="Public lore 1",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-200",
        )

        public_entry_2 = KnowledgeEntry(
            id=str(uuid4()),
            content="Public lore 2",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-201",
        )

        await repository.save(public_entry_1)
        await repository.save(public_entry_2)

        # Act - retrieve for agent with no roles
        agent = AgentIdentity(character_id="char-gamma", roles=())
        accessible_entries = await repository.retrieve_for_agent(agent)

        # Assert - should get both public entries
        entry_ids = [e.id for e in accessible_entries]
        assert public_entry_1.id in entry_ids
        assert public_entry_2.id in entry_ids

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_role_based_access_with_multiple_roles(
        self, repository
    ):
        """Test that agent with multiple roles gets all matching entries."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Models not yet implemented (TDD - expected to fail)")

        # Arrange
        engineer_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Engineering docs",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-300",
        )

        medical_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Medical docs",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("medical",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-301",
        )

        security_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Security protocols",
            knowledge_type=KnowledgeType.RULES,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("security",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-302",
        )

        await repository.save(engineer_entry)
        await repository.save(medical_entry)
        await repository.save(security_entry)

        # Act - agent with engineer + medical roles
        agent = AgentIdentity(character_id="char-delta", roles=("engineer", "medical"))
        accessible_entries = await repository.retrieve_for_agent(agent)

        # Assert - should get engineer + medical entries
        entry_ids = [e.id for e in accessible_entries]
        assert engineer_entry.id in entry_ids
        assert medical_entry.id in entry_ids
        assert security_entry.id not in entry_ids

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_character_specific_access_filters_correctly(
        self, repository
    ):
        """Test that CHARACTER_SPECIFIC entries are filtered by character ID."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Models not yet implemented (TDD - expected to fail)")

        # Arrange
        char_alpha_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Alpha's private memory",
            knowledge_type=KnowledgeType.MEMORY,
            owning_character_id="char-alpha",
            access_control=AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=("char-alpha",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-400",
        )

        char_beta_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Beta's private memory",
            knowledge_type=KnowledgeType.MEMORY,
            owning_character_id="char-beta",
            access_control=AccessControlRule(
                access_level=AccessLevel.CHARACTER_SPECIFIC,
                allowed_character_ids=("char-beta",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-401",
        )

        await repository.save(char_alpha_entry)
        await repository.save(char_beta_entry)

        # Act - retrieve for char-alpha
        agent_alpha = AgentIdentity(character_id="char-alpha", roles=())
        accessible_entries = await repository.retrieve_for_agent(agent_alpha)

        # Assert - should only get char-alpha's entry
        entry_ids = [e.id for e in accessible_entries]
        assert char_alpha_entry.id in entry_ids
        assert char_beta_entry.id not in entry_ids

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_returns_empty_list_when_no_access(
        self, repository
    ):
        """Test that agent with no permissions gets empty list."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Models not yet implemented (TDD - expected to fail)")

        # Arrange - only role-based entry
        engineer_entry = KnowledgeEntry(
            id=str(uuid4()),
            content="Engineering only",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_control=AccessControlRule(
                access_level=AccessLevel.ROLE_BASED,
                allowed_roles=("engineer",),
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-user-500",
        )

        await repository.save(engineer_entry)

        # Act - agent with no matching roles
        agent = AgentIdentity(character_id="char-epsilon", roles=("crew",))
        accessible_entries = await repository.retrieve_for_agent(agent)

        # Assert - should get empty list
        assert len(accessible_entries) == 0

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_performance_with_100_entries(self, repository):
        """Test retrieve_for_agent completes within 500ms for 100 entries (SC-002)."""
        if KnowledgeEntry is None or AgentIdentity is None:
            pytest.skip("Models not yet implemented (TDD - expected to fail)")

        import time

        # Arrange - create 100 entries with mixed access levels
        entries = []
        for i in range(100):
            if i % 3 == 0:
                access_level = AccessLevel.PUBLIC
                access_control = AccessControlRule(access_level=access_level)
            elif i % 3 == 1:
                access_level = AccessLevel.ROLE_BASED
                access_control = AccessControlRule(
                    access_level=access_level,
                    allowed_roles=("engineer",),
                )
            else:
                access_level = AccessLevel.CHARACTER_SPECIFIC
                access_control = AccessControlRule(
                    access_level=access_level,
                    allowed_character_ids=("char-test",),
                )

            entry = KnowledgeEntry(
                id=str(uuid4()),
                content=f"Test entry {i}",
                knowledge_type=KnowledgeType.LORE,
                owning_character_id=None,
                access_control=access_control,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=f"test-user-{600+i}",
            )
            entries.append(entry)

        # Save all entries
        for entry in entries:
            await repository.save(entry)

        # Act - retrieve for engineer agent
        agent = AgentIdentity(character_id="char-zeta", roles=("engineer",))
        start = time.time()
        accessible_entries = await repository.retrieve_for_agent(agent)
        duration_ms = (time.time() - start) * 1000

        # Assert - should complete within 500ms (SC-002)
        assert duration_ms < 500, f"Retrieval took {duration_ms}ms, expected <500ms"

        # Assert - should return public (33) + engineer (33) entries
        assert len(accessible_entries) >= 60  # Approximate expected count


class TestPostgreSQLKnowledgeRepositoryPerformance:
    """Performance tests for repository operations (SC-002: <500ms for ≤100 entries)."""

    @pytest.mark.asyncio
    async def test_save_performance_within_target(self, repository, sample_entry):
        """Test that save operation completes within performance target."""
        import time

        # Act
        start = time.time()
        await repository.save(sample_entry)
        duration_ms = (time.time() - start) * 1000

        # Assert - should be well under 500ms for single entry
        assert duration_ms < 100, f"Save took {duration_ms}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_get_by_id_performance_within_target(self, repository, sample_entry):
        """Test that get_by_id operation completes within performance target."""
        import time

        # Arrange
        await repository.save(sample_entry)

        # Act
        start = time.time()
        await repository.get_by_id(sample_entry.id)
        duration_ms = (time.time() - start) * 1000

        # Assert - should be well under 500ms
        assert duration_ms < 50, f"Get took {duration_ms}ms, expected <50ms"
