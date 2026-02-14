"""
Knowledge Sync Event Handlers

Auto-sync domain events to the RAG knowledge base.
Triggers ingestion when entities are created or updated.

Constitution Compliance:
- Article II (Hexagonal): Application layer event handlers
- Article V (SOLID): SRP - each handler handles one event type

Warzone 4: AI Brain - BRAIN-005
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from ...application.services.knowledge_ingestion_service import (
    IngestionResult,
    KnowledgeIngestionService,
)
from ...domain.models.source_type import SourceType

logger = structlog.get_logger()


class RetryStrategy(str, Enum):
    """Retry strategy for failed ingestions."""

    NONE = "none"  # No retry
    FIXED = "fixed"  # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff


@dataclass
class IngestionTask:
    """
    A task for asynchronous ingestion.

    Attributes:
        source_id: ID of the source entity
        source_type: Type of source
        content: Content to ingest
        tags: Optional tags
        extra_metadata: Optional additional metadata
        retry_count: Number of retries attempted
        max_retries: Maximum number of retries allowed
        retry_delay: Delay before next retry (seconds)
        created_at: When the task was created
    """

    source_id: str
    source_type: SourceType
    content: str
    tags: list[str] | None = None
    extra_metadata: dict[str, Any] | None = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)

    def can_retry(self) -> bool:
        """Check if this task can be retried."""
        return self.retry_count < self.max_retries

    def increment_retry(
        self, strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    ) -> None:
        """Increment retry count and update delay based on strategy."""
        self.retry_count += 1

        if strategy == RetryStrategy.EXPONENTIAL:
            self.retry_delay = min(300, 2**self.retry_count)  # Cap at 5 minutes
        elif strategy == RetryStrategy.FIXED:
            self.retry_delay = 1.0  # Fixed 1 second delay


class KnowledgeSyncEventHandler:
    """
    Handles domain events for automatic knowledge synchronization.

    Subscribes to domain events (CharacterCreated, LoreCreated, etc.)
    and triggers asynchronous ingestion into the RAG system.

    Features:
    - Async queue to avoid blocking
    - Retry logic with exponential backoff
    - Dead letter queue for failed tasks
    - Progress tracking

    Example:
        >>> handler = KnowledgeSyncEventHandler(ingestion_service)
        >>> await handler.start()
        >>> # Events are now processed asynchronously
        >>> await handler.stop()
    """

    def __init__(
        self,
        ingestion_service: KnowledgeIngestionService,
        max_queue_size: int = 1000,
        max_retries: int = 3,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    ):
        """
        Initialize the event handler.

        Args:
            ingestion_service: Service for ingesting knowledge
            max_queue_size: Maximum number of pending tasks
            max_retries: Default maximum retries for tasks
            retry_strategy: Strategy for retrying failed tasks
        """
        self._ingestion_service = ingestion_service
        self._max_queue_size = max_queue_size
        self._max_retries = max_retries
        self._retry_strategy = retry_strategy

        # Async queue for pending tasks
        self._queue: asyncio.Queue[IngestionTask] = asyncio.Queue(
            maxsize=max_queue_size
        )

        # Dead letter queue for failed tasks
        self._dead_letter_queue: list[IngestionTask] = []

        # Worker task
        self._worker_task: asyncio.Task[None] | None = None

        # Track pending retry tasks for cleanup
        self._pending_retry_tasks: set[asyncio.Task[None]] = set()

        # Event subscription IDs (for cleanup)
        self._subscriptions: list[Any] = []

        # Metrics
        self._metrics = {
            "tasks_queued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
        }

        # Running state
        self._running = False

    async def start(self) -> None:
        """Start the background worker for processing ingestion tasks."""
        if self._running:
            logger.warning("KnowledgeSyncEventHandler already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())

        logger.info(
            "knowledge_sync_handler_started",
            max_queue_size=self._max_queue_size,
            max_retries=self._max_retries,
            retry_strategy=self._retry_strategy.value,
        )

    async def stop(self) -> None:
        """Stop the background worker and wait for queue to drain."""
        if not self._running:
            return

        self._running = False

        # Wait for queue to drain (with timeout)
        try:
            remaining = self._queue.qsize()
            if remaining > 0:
                logger.info(
                    "knowledge_sync_handler_draining_queue",
                    remaining_tasks=remaining,
                )
                await asyncio.wait_for(self._queue.join(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning(
                "knowledge_sync_handler_drain_timeout",
                remaining_tasks=self._queue.qsize(),
            )

        # Cancel worker task
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        # Cancel all pending retry tasks
        if self._pending_retry_tasks:
            for retry_task in list(self._pending_retry_tasks):
                retry_task.cancel()
            # Wait for cancellations
            await asyncio.gather(*self._pending_retry_tasks, return_exceptions=True)
            self._pending_retry_tasks.clear()

        logger.info(
            "knowledge_sync_handler_stopped",
            metrics=self._metrics,
            dead_letter_queue_size=len(self._dead_letter_queue),
        )

    async def queue_ingestion(
        self,
        source_id: str,
        source_type: SourceType | str,
        content: str,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Queue an ingestion task for asynchronous processing.

        Args:
            source_id: ID of the source entity
            source_type: Type of source
            content: Content to ingest
            tags: Optional tags
            extra_metadata: Optional additional metadata

        Returns:
            True if queued successfully, False if queue is full
        """
        if not self._running:
            logger.warning("knowledge_sync_handler_not_running")
            return False

        # Normalize source_type
        if isinstance(source_type, str):
            source_type = SourceType.from_string(source_type)

        task = IngestionTask(
            source_id=source_id,
            source_type=source_type,
            content=content,
            tags=tags,
            extra_metadata=extra_metadata,
            max_retries=self._max_retries,
        )

        try:
            self._queue.put_nowait(task)
            self._metrics["tasks_queued"] += 1

            logger.debug(
                "knowledge_sync_task_queued",
                source_id=source_id,
                source_type=source_type.value,
                queue_size=self._queue.qsize(),
            )
            return True
        except asyncio.QueueFull:
            logger.error(
                "knowledge_sync_queue_full",
                source_id=source_id,
                source_type=source_type.value,
            )
            return False

    async def _process_queue(self) -> None:
        """Background worker that processes ingestion tasks."""
        logger.info("knowledge_sync_worker_started")

        while self._running:
            try:
                # Get task with timeout to allow checking _running
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Process the task
                await self._process_task(task)

                # Mark task as done
                self._queue.task_done()

            except asyncio.TimeoutError:
                # No task available, continue loop
                continue
            except asyncio.CancelledError:
                # Worker was cancelled
                break
            except Exception as e:
                logger.error(
                    "knowledge_sync_worker_error",
                    error=str(e),
                    exc_info=True,
                )

        logger.info("knowledge_sync_worker_stopped")

    async def _process_task(self, task: IngestionTask) -> None:
        """
        Process a single ingestion task.

        Args:
            task: The ingestion task to process
        """
        logger.debug(
            "knowledge_sync_processing_task",
            source_id=task.source_id,
            source_type=task.source_type.value,
            retry_count=task.retry_count,
        )

        try:
            result: IngestionResult = await self._ingestion_service.ingest(
                content=task.content,
                source_type=task.source_type,
                source_id=task.source_id,
                tags=task.tags,
                extra_metadata=task.extra_metadata,
            )

            if result.success:
                self._metrics["tasks_completed"] += 1
                logger.info(
                    "knowledge_sync_ingestion_success",
                    source_id=task.source_id,
                    source_type=task.source_type.value,
                    chunk_count=result.chunk_count,
                )
            else:
                # Ingestion failed - retry or dead letter
                await self._handle_failure(task, result.error or "Unknown error")

        except Exception as e:
            # Exception during ingestion - retry or dead letter
            await self._handle_failure(task, str(e))

    async def _handle_failure(self, task: IngestionTask, error: str) -> None:
        """
        Handle a failed ingestion task.

        Args:
            task: The failed task
            error: Error message
        """
        logger.warning(
            "knowledge_sync_ingestion_failed",
            source_id=task.source_id,
            source_type=task.source_type.value,
            error=error,
            retry_count=task.retry_count,
        )

        if task.can_retry():
            # Increment retry count and re-queue
            task.increment_retry(self._retry_strategy)

            # Create retry task and track it
            retry_task = asyncio.create_task(self._retry_after_delay(task))
            self._pending_retry_tasks.add(retry_task)
            retry_task.add_done_callback(lambda t: self._pending_retry_tasks.discard(t))

            self._metrics["tasks_retried"] += 1
        else:
            # Move to dead letter queue
            self._dead_letter_queue.append(task)
            self._metrics["tasks_failed"] += 1

            logger.error(
                "knowledge_sync_task_dead_letter",
                source_id=task.source_id,
                source_type=task.source_type.value,
                final_error=error,
                retry_count=task.retry_count,
            )

    async def _retry_after_delay(self, task: IngestionTask) -> None:
        """
        Re-queue a task after the configured delay.

        Args:
            task: The task to retry
        """
        try:
            await asyncio.sleep(task.retry_delay)

            if self._running:
                try:
                    self._queue.put_nowait(task)
                    logger.debug(
                        "knowledge_sync_task_retried",
                        source_id=task.source_id,
                        retry_count=task.retry_count,
                    )
                except asyncio.QueueFull:
                    self._dead_letter_queue.append(task)
                    logger.error(
                        "knowledge_sync_retry_queue_full",
                        source_id=task.source_id,
                    )
        except asyncio.CancelledError:
            # Task was cancelled during shutdown
            logger.debug(
                "knowledge_sync_retry_cancelled",
                source_id=task.source_id,
            )
            raise

    def get_metrics(self) -> dict[str, Any]:
        """Get handler metrics."""
        return {
            **self._metrics,
            "queue_size": self._queue.qsize(),
            "dead_letter_queue_size": len(self._dead_letter_queue),
            "is_running": self._running,
        }

    def get_dead_letter_queue(self) -> list[IngestionTask]:
        """Get all failed tasks in the dead letter queue."""
        return self._dead_letter_queue.copy()

    async def retry_dead_letter_task(self, task: IngestionTask) -> bool:
        """
        Manually retry a task from the dead letter queue.

        Args:
            task: The task to retry

        Returns:
            True if task was re-queued, False otherwise
        """
        # Reset retry count
        task.retry_count = 0
        task.retry_delay = 1.0

        # Remove from dead letter queue
        if task in self._dead_letter_queue:
            self._dead_letter_queue.remove(task)

        # Re-queue
        return await self.queue_ingestion(
            source_id=task.source_id,
            source_type=task.source_type,
            content=task.content,
            tags=task.tags,
            extra_metadata=task.extra_metadata,
        )


# Helper functions for specific event types


def _character_to_content(
    character_id: str,
    name: str,
    description: str | None = None,
    traits: list[str] | None = None,
    backstory: str | None = None,
) -> str:
    """
    Convert character data to text content for ingestion.

    Args:
        character_id: Character ID
        name: Character name
        description: Character description
        traits: Character traits
        backstory: Character backstory

    Returns:
        Formatted text content
    """
    parts = [f"# {name}", f"Character ID: {character_id}"]

    if description:
        parts.append(f"\n## Description\n{description}")

    if traits:
        parts.append(f"\n## Traits\n{', '.join(traits)}")

    if backstory:
        parts.append(f"\n## Backstory\n{backstory}")

    return "\n".join(parts)


def _lore_to_content(
    lore_id: str,
    title: str,
    content: str,
    category: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """
    Convert lore entry to text content for ingestion.

    Args:
        lore_id: Lore entry ID
        title: Lore title
        content: Lore content
        category: Lore category
        tags: Lore tags

    Returns:
        Formatted text content
    """
    parts = [f"# {title}", f"Lore ID: {lore_id}"]

    if category:
        parts.append(f"Category: {category}")

    if tags:
        parts.append(f"Tags: {', '.join(tags)}")

    parts.append(f"\n## Content\n{content}")

    return "\n".join(parts)


def _scene_to_content(
    scene_id: str,
    title: str,
    summary: str | None = None,
    location: str | None = None,
    beats: list[str] | None = None,
) -> str:
    """
    Convert scene data to text content for ingestion.

    Args:
        scene_id: Scene ID
        title: Scene title
        summary: Scene summary
        location: Scene location
        beats: List of beat content

    Returns:
        Formatted text content
    """
    parts = [f"# {title}", f"Scene ID: {scene_id}"]

    if location:
        parts.append(f"Location: {location}")

    if summary:
        parts.append(f"\n## Summary\n{summary}")

    if beats:
        parts.append("\n## Beats")
        for i, beat in enumerate(beats, 1):
            parts.append(f"\n### Beat {i}\n{beat}")

    return "\n".join(parts)


__all__ = [
    "KnowledgeSyncEventHandler",
    "IngestionTask",
    "RetryStrategy",
    "_character_to_content",
    "_lore_to_content",
    "_scene_to_content",
]
