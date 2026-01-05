"""
Unit Tests for CreateKnowledgeEntryUseCase

TDD Approach: Tests written FIRST, must FAIL before implementation.

Constitution Compliance:
- Article III (TDD): Red-Green-Refactor cycle
- Article I (DDD): Application layer use case testing
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

# NOTE: These imports will fail until application layer is implemented
try:
    from contexts.knowledge.application.ports.i_event_publisher import IEventPublisher
    from contexts.knowledge.application.ports.i_knowledge_repository import (
        IKnowledgeRepository,
    )
    from contexts.knowledge.application.use_cases.create_knowledge_entry import (
        CreateKnowledgeEntryCommand,
        CreateKnowledgeEntryUseCase,
    )
    from contexts.knowledge.domain.models.access_level import AccessLevel
    from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
    from contexts.knowledge.domain.models.knowledge_type import KnowledgeType
except ImportError:
    CreateKnowledgeEntryUseCase = None
    CreateKnowledgeEntryCommand = None
    IKnowledgeRepository = None
    IEventPublisher = None
    KnowledgeEntry = None
    KnowledgeType = None
    AccessLevel = None


pytestmark = pytest.mark.knowledge


class TestCreateKnowledgeEntryUseCase:
    """Test suite for CreateKnowledgeEntryUseCase."""

    @pytest.fixture
    def mock_repository(self):
        """Mock knowledge repository."""
        if IKnowledgeRepository is None:
            pytest.skip(
                "IKnowledgeRepository not yet implemented (TDD - expected to fail)"
            )

        repository = AsyncMock(spec=IKnowledgeRepository)
        return repository

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock event publisher."""
        if IEventPublisher is None:
            pytest.skip("IEventPublisher not yet implemented (TDD - expected to fail)")

        publisher = AsyncMock(spec=IEventPublisher)
        return publisher

    @pytest.fixture
    def use_case(self, mock_repository, mock_event_publisher):
        """Create use case instance with mocked dependencies."""
        if CreateKnowledgeEntryUseCase is None:
            pytest.skip(
                "CreateKnowledgeEntryUseCase not yet implemented (TDD - expected to fail)"
            )

        return CreateKnowledgeEntryUseCase(
            repository=mock_repository,
            event_publisher=mock_event_publisher,
        )

    @pytest.fixture
    def valid_command(self):
        """Valid create knowledge entry command."""
        if CreateKnowledgeEntryCommand is None:
            pytest.skip(
                "CreateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        return CreateKnowledgeEntryCommand(
            content="Character is a skilled engineer with 10 years experience",
            knowledge_type=KnowledgeType.PROFILE,
            owning_character_id="char-001",
            access_level=AccessLevel.CHARACTER_SPECIFIC,
            allowed_character_ids=["char-001"],
            created_by="user-001",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_success(
        self, use_case, valid_command, mock_repository, mock_event_publisher
    ):
        """Test successful knowledge entry creation."""
        # Arrange
        mock_repository.save.return_value = None
        mock_event_publisher.publish.return_value = None

        # Act
        entry_id = await use_case.execute(valid_command)

        # Assert
        assert entry_id is not None
        assert isinstance(entry_id, str)

        # Verify repository.save was called
        mock_repository.save.assert_called_once()
        saved_entry = mock_repository.save.call_args[0][0]
        assert isinstance(saved_entry, KnowledgeEntry)
        assert saved_entry.content == valid_command.content
        assert saved_entry.knowledge_type == valid_command.knowledge_type
        assert saved_entry.created_by == valid_command.created_by

        # Verify event was published
        mock_event_publisher.publish.assert_called_once()
        event_call = mock_event_publisher.publish.call_args
        assert event_call[1]["topic"] == "knowledge.entry.created"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_with_empty_content_raises_error(self, use_case):
        """Test that empty content raises ValueError."""
        if CreateKnowledgeEntryCommand is None:
            pytest.skip(
                "CreateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        invalid_command = CreateKnowledgeEntryCommand(
            content="",  # Empty content
            knowledge_type=KnowledgeType.PROFILE,
            owning_character_id="char-001",
            access_level=AccessLevel.PUBLIC,
            created_by="user-001",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await use_case.execute(invalid_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_sets_timestamps(
        self, use_case, valid_command, mock_repository
    ):
        """Test that created_at and updated_at are set to current UTC time."""
        # Arrange
        before_creation = datetime.now(timezone.utc)

        # Act
        await use_case.execute(valid_command)

        # Assert
        after_creation = datetime.now(timezone.utc)
        saved_entry = mock_repository.save.call_args[0][0]

        assert before_creation <= saved_entry.created_at <= after_creation
        assert before_creation <= saved_entry.updated_at <= after_creation
        assert saved_entry.created_at == saved_entry.updated_at

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_generates_unique_id(
        self, use_case, valid_command, mock_repository
    ):
        """Test that each created entry has a unique ID."""
        # Act
        await use_case.execute(valid_command)
        await use_case.execute(valid_command)

        # Assert
        first_entry = mock_repository.save.call_args_list[0][0][0]
        second_entry = mock_repository.save.call_args_list[1][0][0]

        assert first_entry.id != second_entry.id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_with_public_access(self, use_case, mock_repository):
        """Test creating entry with PUBLIC access level."""
        if CreateKnowledgeEntryCommand is None:
            pytest.skip(
                "CreateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        command = CreateKnowledgeEntryCommand(
            content="Public world lore entry",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,  # World knowledge
            access_level=AccessLevel.PUBLIC,
            created_by="user-001",
        )

        # Act
        await use_case.execute(command)

        # Assert
        saved_entry = mock_repository.save.call_args[0][0]
        assert saved_entry.owning_character_id is None
        assert saved_entry.access_control.access_level == AccessLevel.PUBLIC

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_with_role_based_access(self, use_case, mock_repository):
        """Test creating entry with ROLE_BASED access level."""
        if CreateKnowledgeEntryCommand is None:
            pytest.skip(
                "CreateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        command = CreateKnowledgeEntryCommand(
            content="Engineering documentation",
            knowledge_type=KnowledgeType.LORE,
            owning_character_id=None,
            access_level=AccessLevel.ROLE_BASED,
            allowed_roles=["engineer", "medical"],
            created_by="user-001",
        )

        # Act
        await use_case.execute(command)

        # Assert
        saved_entry = mock_repository.save.call_args[0][0]
        assert saved_entry.access_control.access_level == AccessLevel.ROLE_BASED
        assert "engineer" in saved_entry.access_control.allowed_roles
        assert "medical" in saved_entry.access_control.allowed_roles

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_publishes_domain_event(
        self, use_case, valid_command, mock_event_publisher
    ):
        """Test that domain event is published after successful creation."""
        # Act
        entry_id = await use_case.execute(valid_command)

        # Assert
        mock_event_publisher.publish.assert_called_once()
        event_call = mock_event_publisher.publish.call_args

        # Check topic
        assert event_call[1]["topic"] == "knowledge.entry.created"

        # Check event payload
        event = event_call[1]["event"]
        assert event["entry_id"] == entry_id
        assert event["knowledge_type"] == KnowledgeType.PROFILE.value
        assert event["created_by"] == "user-001"
        assert "timestamp" in event

        # Check partition key (should be entry_id for ordering)
        assert event_call[1]["key"] == entry_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_entry_repository_failure_does_not_publish_event(
        self, use_case, valid_command, mock_repository, mock_event_publisher
    ):
        """Test that event is not published if repository save fails."""
        # Arrange
        mock_repository.save.side_effect = Exception("Database connection error")

        # Act & Assert
        with pytest.raises(Exception, match="Database connection error"):
            await use_case.execute(valid_command)

        # Event should NOT be published
        mock_event_publisher.publish.assert_not_called()
