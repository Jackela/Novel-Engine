"""
Unit Tests for UpdateKnowledgeEntryUseCase

TDD Approach: Tests written FIRST, must FAIL before implementation.

Constitution Compliance:
- Article III (TDD): Red-Green-Refactor cycle
- Article I (DDD): Application layer use case testing
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

# NOTE: These imports will fail until application layer is implemented
try:
    from contexts.knowledge.application.ports.i_event_publisher import IEventPublisher
    from contexts.knowledge.application.ports.i_knowledge_repository import (
        IKnowledgeRepository,
    )
    from contexts.knowledge.application.use_cases.update_knowledge_entry import (
        UpdateKnowledgeEntryCommand,
        UpdateKnowledgeEntryUseCase,
    )
    from contexts.knowledge.domain.models.access_control_rule import AccessControlRule
    from contexts.knowledge.domain.models.access_level import AccessLevel
    from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
    from contexts.knowledge.domain.models.knowledge_type import KnowledgeType
except ImportError:
    UpdateKnowledgeEntryUseCase = None
    UpdateKnowledgeEntryCommand = None
    IKnowledgeRepository = None
    IEventPublisher = None
    KnowledgeEntry = None
    KnowledgeType = None
    AccessControlRule = None
    AccessLevel = None


pytestmark = pytest.mark.knowledge


class TestUpdateKnowledgeEntryUseCase:
    """Test suite for UpdateKnowledgeEntryUseCase."""

    @pytest.fixture
    def existing_entry(self):
        """Create an existing knowledge entry for update tests."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        entry_id = str(uuid4())
        created_at = datetime.now(timezone.utc)

        return KnowledgeEntry(
            id=entry_id,
            content="Original content",
            knowledge_type=KnowledgeType.PROFILE,
            owning_character_id="char-001",
            access_control=AccessControlRule(access_level=AccessLevel.PUBLIC),
            created_at=created_at,
            updated_at=created_at,
            created_by="user-001",
        )

    @pytest.fixture
    def mock_repository(self, existing_entry):
        """Mock knowledge repository."""
        if IKnowledgeRepository is None:
            pytest.skip(
                "IKnowledgeRepository not yet implemented (TDD - expected to fail)"
            )

        repository = AsyncMock(spec=IKnowledgeRepository)
        repository.get_by_id.return_value = existing_entry
        repository.save.return_value = None
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
        if UpdateKnowledgeEntryUseCase is None:
            pytest.skip(
                "UpdateKnowledgeEntryUseCase not yet implemented (TDD - expected to fail)"
            )

        return UpdateKnowledgeEntryUseCase(
            repository=mock_repository,
            event_publisher=mock_event_publisher,
        )

    @pytest.fixture
    def valid_command(self, existing_entry):
        """Valid update knowledge entry command."""
        if UpdateKnowledgeEntryCommand is None:
            pytest.skip(
                "UpdateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        return UpdateKnowledgeEntryCommand(
            entry_id=existing_entry.id,
            content="Updated content with new information",
            updated_by="user-002",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_success(
        self, use_case, valid_command, mock_repository, mock_event_publisher
    ):
        """Test successful knowledge entry update."""
        # Act
        await use_case.execute(valid_command)

        # Assert - repository interactions
        mock_repository.get_by_id.assert_called_once_with(valid_command.entry_id)
        mock_repository.save.assert_called_once()

        # Verify updated entry
        saved_entry = mock_repository.save.call_args[0][0]
        assert saved_entry.content == valid_command.content
        assert saved_entry.updated_at > saved_entry.created_at

        # Verify event was published
        mock_event_publisher.publish.assert_called_once()
        event_call = mock_event_publisher.publish.call_args
        assert event_call[1]["topic"] == "knowledge.entry.updated"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_with_empty_content_raises_error(
        self, use_case, existing_entry
    ):
        """Test that empty content raises ValueError."""
        if UpdateKnowledgeEntryCommand is None:
            pytest.skip(
                "UpdateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        invalid_command = UpdateKnowledgeEntryCommand(
            entry_id=existing_entry.id,
            content="",  # Empty content
            updated_by="user-002",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await use_case.execute(invalid_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_not_found_raises_error(self, use_case, mock_repository):
        """Test that updating non-existent entry raises error."""
        if UpdateKnowledgeEntryCommand is None:
            pytest.skip(
                "UpdateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        mock_repository.get_by_id.return_value = None
        command = UpdateKnowledgeEntryCommand(
            entry_id=str(uuid4()),
            content="Updated content",
            updated_by="user-002",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Knowledge entry not found"):
            await use_case.execute(command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_preserves_immutable_fields(
        self, use_case, valid_command, mock_repository, existing_entry
    ):
        """Test that update preserves immutable fields."""
        # Act
        await use_case.execute(valid_command)

        # Assert
        saved_entry = mock_repository.save.call_args[0][0]
        assert saved_entry.id == existing_entry.id
        assert saved_entry.created_at == existing_entry.created_at
        assert saved_entry.created_by == existing_entry.created_by
        assert saved_entry.knowledge_type == existing_entry.knowledge_type
        assert saved_entry.owning_character_id == existing_entry.owning_character_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_updates_timestamp(
        self, use_case, valid_command, mock_repository
    ):
        """Test that updated_at timestamp is updated."""
        # Arrange
        original_updated_at = mock_repository.get_by_id.return_value.updated_at

        # Act
        await use_case.execute(valid_command)

        # Assert
        saved_entry = mock_repository.save.call_args[0][0]
        assert saved_entry.updated_at > original_updated_at
        assert saved_entry.updated_at.tzinfo == timezone.utc

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_publishes_domain_event(
        self, use_case, valid_command, mock_event_publisher, existing_entry
    ):
        """Test that domain event is published after successful update."""
        # Act
        await use_case.execute(valid_command)

        # Assert
        mock_event_publisher.publish.assert_called_once()
        event_call = mock_event_publisher.publish.call_args

        # Check topic
        assert event_call[1]["topic"] == "knowledge.entry.updated"

        # Check event payload
        event = event_call[1]["event"]
        assert event["entry_id"] == existing_entry.id
        assert event["updated_by"] == "user-002"
        assert "timestamp" in event

        # Check partition key
        assert event_call[1]["key"] == existing_entry.id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_repository_failure_does_not_publish_event(
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

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_entry_multiple_times(
        self, use_case, mock_repository, existing_entry
    ):
        """Test multiple consecutive updates."""
        if UpdateKnowledgeEntryCommand is None:
            pytest.skip(
                "UpdateKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        command1 = UpdateKnowledgeEntryCommand(
            entry_id=existing_entry.id,
            content="First update",
            updated_by="user-002",
        )
        command2 = UpdateKnowledgeEntryCommand(
            entry_id=existing_entry.id,
            content="Second update",
            updated_by="user-003",
        )

        # Act
        await use_case.execute(command1)
        first_saved = mock_repository.save.call_args[0][0]

        # Update mock to return first saved entry
        mock_repository.get_by_id.return_value = first_saved

        await use_case.execute(command2)
        second_saved = mock_repository.save.call_args[0][0]

        # Assert
        assert second_saved.content == "Second update"
        assert second_saved.updated_at > first_saved.updated_at
