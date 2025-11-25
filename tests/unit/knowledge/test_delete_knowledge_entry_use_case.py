"""
Unit Tests for DeleteKnowledgeEntryUseCase

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
    from contexts.knowledge.application.use_cases.delete_knowledge_entry import (
        DeleteKnowledgeEntryCommand,
        DeleteKnowledgeEntryUseCase,
    )
    from contexts.knowledge.domain.models.access_control_rule import AccessControlRule
    from contexts.knowledge.domain.models.access_level import AccessLevel
    from contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
    from contexts.knowledge.domain.models.knowledge_type import KnowledgeType
except ImportError:
    DeleteKnowledgeEntryUseCase = None
    DeleteKnowledgeEntryCommand = None
    IKnowledgeRepository = None
    IEventPublisher = None
    KnowledgeEntry = None
    KnowledgeType = None
    AccessControlRule = None
    AccessLevel = None


pytestmark = pytest.mark.knowledge


class TestDeleteKnowledgeEntryUseCase:
    """Test suite for DeleteKnowledgeEntryUseCase."""

    @pytest.fixture
    def existing_entry(self):
        """Create an existing knowledge entry for delete tests."""
        if KnowledgeEntry is None:
            pytest.skip("KnowledgeEntry not yet implemented (TDD - expected to fail)")

        entry_id = str(uuid4())
        created_at = datetime.now(timezone.utc)

        return KnowledgeEntry(
            id=entry_id,
            content="Entry to be deleted",
            knowledge_type=KnowledgeType.MEMORY,
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
        repository.delete.return_value = None
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
        if DeleteKnowledgeEntryUseCase is None:
            pytest.skip(
                "DeleteKnowledgeEntryUseCase not yet implemented (TDD - expected to fail)"
            )

        return DeleteKnowledgeEntryUseCase(
            repository=mock_repository,
            event_publisher=mock_event_publisher,
        )

    @pytest.fixture
    def valid_command(self, existing_entry):
        """Valid delete knowledge entry command."""
        if DeleteKnowledgeEntryCommand is None:
            pytest.skip(
                "DeleteKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        return DeleteKnowledgeEntryCommand(
            entry_id=existing_entry.id,
            deleted_by="user-002",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_entry_success(
        self, use_case, valid_command, mock_repository, mock_event_publisher
    ):
        """Test successful knowledge entry deletion."""
        # Act
        await use_case.execute(valid_command)

        # Assert - repository interactions
        mock_repository.get_by_id.assert_called_once_with(valid_command.entry_id)
        mock_repository.delete.assert_called_once_with(valid_command.entry_id)

        # Verify event was published
        mock_event_publisher.publish.assert_called_once()
        event_call = mock_event_publisher.publish.call_args
        assert event_call[1]["topic"] == "knowledge.entry.deleted"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_entry_not_found_raises_error(self, use_case, mock_repository):
        """Test that deleting non-existent entry raises error."""
        if DeleteKnowledgeEntryCommand is None:
            pytest.skip(
                "DeleteKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange
        mock_repository.get_by_id.return_value = None
        command = DeleteKnowledgeEntryCommand(
            entry_id=str(uuid4()),
            deleted_by="user-002",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Knowledge entry not found"):
            await use_case.execute(command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_entry_publishes_domain_event(
        self, use_case, valid_command, mock_event_publisher, existing_entry
    ):
        """Test that domain event is published after successful deletion."""
        # Act
        await use_case.execute(valid_command)

        # Assert
        mock_event_publisher.publish.assert_called_once()
        event_call = mock_event_publisher.publish.call_args

        # Check topic
        assert event_call[1]["topic"] == "knowledge.entry.deleted"

        # Check event payload
        event = event_call[1]["event"]
        assert event["entry_id"] == existing_entry.id
        assert event["deleted_by"] == "user-002"
        assert "timestamp" in event

        # Check partition key
        assert event_call[1]["key"] == existing_entry.id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_entry_repository_failure_does_not_publish_event(
        self, use_case, valid_command, mock_repository, mock_event_publisher
    ):
        """Test that event is not published if repository delete fails."""
        # Arrange
        mock_repository.delete.side_effect = Exception("Database connection error")

        # Act & Assert
        with pytest.raises(Exception, match="Database connection error"):
            await use_case.execute(valid_command)

        # Event should NOT be published
        mock_event_publisher.publish.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_entry_verifies_entry_exists_before_deletion(
        self, use_case, valid_command, mock_repository
    ):
        """Test that entry existence is verified before deletion."""
        # Act
        await use_case.execute(valid_command)

        # Assert - get_by_id called before delete
        assert mock_repository.get_by_id.call_count == 1
        assert mock_repository.delete.call_count == 1

        # Verify order: get_by_id was called before delete
        call_order = [call[0] for call in mock_repository.method_calls]
        get_index = call_order.index("get_by_id")
        delete_index = call_order.index("delete")
        assert get_index < delete_index

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_already_deleted_entry_raises_error(
        self, use_case, mock_repository
    ):
        """Test that attempting to delete already deleted entry raises error."""
        if DeleteKnowledgeEntryCommand is None:
            pytest.skip(
                "DeleteKnowledgeEntryCommand not yet implemented (TDD - expected to fail)"
            )

        # Arrange - entry already deleted (get_by_id returns None)
        mock_repository.get_by_id.return_value = None
        command = DeleteKnowledgeEntryCommand(
            entry_id=str(uuid4()),
            deleted_by="user-002",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Knowledge entry not found"):
            await use_case.execute(command)

        # Delete should NOT be called
        mock_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_entry_includes_snapshot_in_event(
        self, use_case, valid_command, mock_event_publisher, existing_entry
    ):
        """Test that deletion event includes entry snapshot for audit trail."""
        # Act
        await use_case.execute(valid_command)

        # Assert
        event_call = mock_event_publisher.publish.call_args
        event = event_call[1]["event"]

        # Event should include snapshot of deleted entry
        assert (
            "snapshot" in event
            or event.get("knowledge_type") == existing_entry.knowledge_type.value
        )
        # Snapshot allows audit trail reconstruction per FR-011
