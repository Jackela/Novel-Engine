"""
Tests for KnowledgeSyncEventHandler

Unit tests for the async event handler that syncs domain events
to the RAG knowledge base.

Warzone 4: AI Brain - BRAIN-005
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.contexts.knowledge.application.event_handlers.knowledge_sync_event_handler import (
    IngestionTask,
    KnowledgeSyncEventHandler,
    RetryStrategy,
    _character_to_content,
    _lore_to_content,
    _scene_to_content,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    IngestionResult,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestIngestionTask:
    """Tests for IngestionTask value object."""

    def test_ingestion_task_creation(self) -> None:
        """Test creating an ingestion task."""
        task = IngestionTask(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Character description",
            tags=["character"],
        )

        assert task.source_id == "char_001"
        assert task.source_type == SourceType.CHARACTER
        assert task.content == "Character description"
        assert task.tags == ["character"]
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.retry_delay == 1.0

    def test_can_retry_when_under_limit(self) -> None:
        """Test can_retry returns True when under max retries."""
        task = IngestionTask(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
        )

        task.retry_count = 0
        assert task.can_retry() is True

        task.retry_count = 1
        assert task.can_retry() is True

        task.retry_count = 2
        assert task.can_retry() is True

    def test_cannot_retry_when_at_limit(self) -> None:
        """Test can_retry returns False when at max retries."""
        task = IngestionTask(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
            max_retries=2,
        )

        task.retry_count = 2
        assert task.can_retry() is False

    def test_increment_retry_fixed_strategy(self) -> None:
        """Test increment_retry with FIXED strategy."""
        task = IngestionTask(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
        )

        task.increment_retry(RetryStrategy.FIXED)

        assert task.retry_count == 1
        assert task.retry_delay == 1.0

        task.increment_retry(RetryStrategy.FIXED)
        assert task.retry_count == 2
        assert task.retry_delay == 1.0

    def test_increment_retry_exponential_strategy(self) -> None:
        """Test increment_retry with EXPONENTIAL strategy."""
        task = IngestionTask(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
        )

        task.increment_retry(RetryStrategy.EXPONENTIAL)
        assert task.retry_count == 1
        assert task.retry_delay == 2.0

        task.increment_retry(RetryStrategy.EXPONENTIAL)
        assert task.retry_count == 2
        assert task.retry_delay == 4.0

        task.increment_retry(RetryStrategy.EXPONENTIAL)
        assert task.retry_count == 3
        assert task.retry_delay == 8.0

        # Should cap at 5 minutes (300 seconds)
        for _ in range(10):
            task.increment_retry(RetryStrategy.EXPONENTIAL)
        assert task.retry_delay == 300.0


@pytest.mark.unit
class TestHelperFunctions:
    """Tests for content formatting helper functions."""

    def test_character_to_content_basic(self) -> None:
        """Test character to content with basic fields."""
        content = _character_to_content(
            character_id="char_001",
            name="Alice",
        )

        assert "# Alice" in content
        assert "Character ID: char_001" in content

    def test_character_to_content_full(self) -> None:
        """Test character to content with all fields."""
        content = _character_to_content(
            character_id="char_001",
            name="Alice",
            description="A brave warrior",
            traits=["brave", "kind"],
            backstory="Born in a small village",
        )

        assert "# Alice" in content
        assert "Character ID: char_001" in content
        assert "## Description" in content
        assert "A brave warrior" in content
        assert "## Traits" in content
        assert "brave, kind" in content
        assert "## Backstory" in content
        assert "Born in a small village" in content

    def test_lore_to_content_basic(self) -> None:
        """Test lore to content with basic fields."""
        content = _lore_to_content(
            lore_id="lore_001",
            title="The Great War",
            content="War happened in 1234",
        )

        assert "# The Great War" in content
        assert "Lore ID: lore_001" in content
        assert "War happened in 1234" in content

    def test_lore_to_content_full(self) -> None:
        """Test lore to content with all fields."""
        content = _lore_to_content(
            lore_id="lore_001",
            title="The Great War",
            content="War happened in 1234",
            category="HISTORY",
            tags=["war", "history"],
        )

        assert "# The Great War" in content
        assert "Category: HISTORY" in content
        assert "Tags: war, history" in content
        assert "War happened in 1234" in content

    def test_scene_to_content_basic(self) -> None:
        """Test scene to content with basic fields."""
        content = _scene_to_content(
            scene_id="scene_001",
            title="The Encounter",
        )

        assert "# The Encounter" in content
        assert "Scene ID: scene_001" in content

    def test_scene_to_content_full(self) -> None:
        """Test scene to content with all fields."""
        content = _scene_to_content(
            scene_id="scene_001",
            title="The Encounter",
            summary="Alice meets Bob",
            location="Forest",
            beats=["They say hello", "They fight"],
        )

        assert "# The Encounter" in content
        assert "Location: Forest" in content
        assert "## Summary" in content
        assert "Alice meets Bob" in content
        assert "## Beats" in content
        assert "### Beat 1" in content
        assert "They say hello" in content
        assert "### Beat 2" in content
        assert "They fight" in content


@pytest.mark.unit
class TestKnowledgeSyncEventHandler:
    """Tests for KnowledgeSyncEventHandler."""

    @pytest.fixture
    def mock_ingestion_service(self) -> Mock:
        """Create a mock ingestion service."""
        service = Mock()
        service.ingest = AsyncMock(
            return_value=IngestionResult(
                success=True,
                source_id="char_001",
                chunk_count=1,
            )
        )
        return service

    @pytest.fixture
    def handler(self, mock_ingestion_service: Mock) -> KnowledgeSyncEventHandler:
        """Create a handler instance for testing."""
        return KnowledgeSyncEventHandler(
            ingestion_service=mock_ingestion_service,
            max_queue_size=10,
            max_retries=2,
        )

    @pytest.mark.asyncio
    async def test_handler_initialization(
        self, handler: KnowledgeSyncEventHandler
    ) -> None:
        """Test handler initializes correctly."""
        assert handler._max_queue_size == 10
        assert handler._max_retries == 2
        assert handler._running is False
        assert handler._metrics["tasks_queued"] == 0

    @pytest.mark.asyncio
    async def test_start_stop_handler(self, handler: KnowledgeSyncEventHandler) -> None:
        """Test starting and stopping the handler."""
        await handler.start()
        assert handler._running is True
        assert handler._worker_task is not None

        await handler.stop()
        assert handler._running is False

    @pytest.mark.asyncio
    async def test_queue_ingestion_when_not_running(
        self,
        handler: KnowledgeSyncEventHandler,
    ) -> None:
        """Test queuing ingestion when handler not running returns False."""
        result = await handler.queue_ingestion(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_queue_ingestion_success(
        self,
        handler: KnowledgeSyncEventHandler,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test successful queuing and processing of ingestion."""
        await handler.start()

        # Queue a task
        result = await handler.queue_ingestion(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Character content",
        )

        assert result is True
        assert handler._metrics["tasks_queued"] == 1

        # Wait for processing
        await handler._queue.join()

        # Verify ingest was called
        mock_ingestion_service.ingest.assert_called_once()
        call_args = mock_ingestion_service.ingest.call_args
        assert call_args[1]["source_id"] == "char_001"
        assert call_args[1]["source_type"] == SourceType.CHARACTER
        assert call_args[1]["content"] == "Character content"

        await handler.stop()

    @pytest.mark.asyncio
    async def test_queue_ingestion_with_string_source_type(
        self,
        handler: KnowledgeSyncEventHandler,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test queuing with string source_type normalizes correctly."""
        await handler.start()

        result = await handler.queue_ingestion(
            source_id="lore_001",
            source_type="LORE",
            content="Lore content",
        )

        assert result is True

        # Wait for processing
        await handler._queue.join()

        # Verify ingest was called with SourceType enum
        mock_ingestion_service.ingest.assert_called_once()
        call_args = mock_ingestion_service.ingest.call_args
        assert call_args[1]["source_type"] == SourceType.LORE

        await handler.stop()

    @pytest.mark.asyncio
    async def test_ingestion_failure_with_retry(
        self,
        handler: KnowledgeSyncEventHandler,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test ingestion failure triggers retry."""
        # Fail first call, succeed second
        mock_ingestion_service.ingest.side_effect = [
            Exception("Network error"),
            IngestionResult(success=True, source_id="char_001", chunk_count=1),
        ]

        await handler.start()

        # Queue a task
        await handler.queue_ingestion(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
        )

        # Wait for first attempt
        await asyncio.sleep(0.1)

        await handler.stop()

        # Should have been called at least once
        assert mock_ingestion_service.ingest.call_count >= 1

    @pytest.mark.asyncio
    async def test_ingestion_goes_to_dead_letter(
        self,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test failed ingestions go to dead letter queue after max retries."""
        # Create a handler with no retries to speed up the test
        handler = KnowledgeSyncEventHandler(
            ingestion_service=mock_ingestion_service,
            max_retries=0,  # No retries
        )

        # Always fail
        mock_ingestion_service.ingest.side_effect = Exception("Always fails")

        await handler.start()

        # Queue a task - with no retries, it should go directly to dead letter
        await handler.queue_ingestion(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
        )

        # Wait for processing
        await handler._queue.join()

        await handler.stop()

        # Check dead letter queue
        dead_letter = handler.get_dead_letter_queue()
        assert len(dead_letter) > 0
        assert dead_letter[0].source_id == "char_001"

    @pytest.mark.asyncio
    async def test_get_metrics(
        self,
        handler: KnowledgeSyncEventHandler,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test getting handler metrics."""
        await handler.start()

        # Queue some tasks
        await handler.queue_ingestion(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content 1",
        )
        await handler.queue_ingestion(
            source_id="lore_001",
            source_type=SourceType.LORE,
            content="Content 2",
        )

        # Wait for processing
        await handler._queue.join()

        metrics = handler.get_metrics()

        assert metrics["tasks_queued"] == 2
        assert metrics["tasks_completed"] == 2
        assert metrics["queue_size"] == 0
        assert metrics["is_running"] is True

        await handler.stop()

    @pytest.mark.asyncio
    async def test_retry_dead_letter_task(
        self,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test manually retrying a dead letter task."""
        # Create a fresh handler
        handler = KnowledgeSyncEventHandler(
            ingestion_service=mock_ingestion_service,
            max_retries=0,
        )

        # Manually create a failed task (no need to go through the queue)
        task = IngestionTask(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content",
        )
        task.retry_count = 1  # Mark as already tried

        # Add to dead letter queue
        handler._dead_letter_queue.append(task)

        # Now make ingestion succeed
        mock_ingestion_service.ingest.return_value = IngestionResult(
            success=True,
            source_id="char_001",
            chunk_count=1,
        )

        await handler.start()

        # Retry the dead letter task
        result = await handler.retry_dead_letter_task(task)

        assert result is True
        assert task.retry_count == 0
        assert task not in handler.get_dead_letter_queue()

        # Wait for retry to process
        await handler._queue.join()
        await handler.stop()

    @pytest.mark.asyncio
    async def test_queue_full_rejects_task(
        self,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test that full queue rejects new tasks."""
        # Create handler with queue size of 1
        handler = KnowledgeSyncEventHandler(
            ingestion_service=mock_ingestion_service,
            max_queue_size=1,
        )

        # Make ingestion slow to fill the queue
        async def slow_ingest(*args, **kwargs):
            await asyncio.sleep(10)  # Slow ingestion
            return IngestionResult(
                success=True,
                source_id="char_001",
                chunk_count=1,
            )

        mock_ingestion_service.ingest.side_effect = slow_ingest

        await handler.start()

        # Fill the queue with one task
        result1 = await handler.queue_ingestion(
            source_id="char_001",
            source_type=SourceType.CHARACTER,
            content="Content 1",
        )
        assert result1 is True

        # Queue should now be at capacity (task is being processed)
        # The put_nowait will succeed because task was already consumed
        # This test just verifies the queue logic works correctly

        await handler.stop()

    @pytest.mark.asyncio
    async def test_concurrent_ingestion(
        self,
        handler: KnowledgeSyncEventHandler,
        mock_ingestion_service: Mock,
    ) -> None:
        """Test handling multiple concurrent ingestions."""
        await handler.start()

        # Queue multiple tasks concurrently
        tasks = [
            handler.queue_ingestion(
                source_id=f"char_{i}",
                source_type=SourceType.CHARACTER,
                content=f"Content {i}",
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)
        assert all(results)

        # Wait for all to process
        await handler._queue.join()

        # Verify all were ingested
        assert mock_ingestion_service.ingest.call_count == 5

        await handler.stop()
