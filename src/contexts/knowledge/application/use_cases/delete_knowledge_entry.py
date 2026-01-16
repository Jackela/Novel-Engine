"""
DeleteKnowledgeEntryUseCase

Application use case for deleting knowledge entries.

Constitution Compliance:
- Article I (DDD): Application service orchestrating domain logic
- Article II (Hexagonal): Use case depends on ports, not adapters
- Article VI (EDA): Publishes KnowledgeEntryDeleted domain event
- Article VII (Observability): Structured logging for all operations
"""

from datetime import datetime, timezone

from src.core.types.shared_types import KnowledgeEntryId, UserId

from ..ports.i_knowledge_repository import IKnowledgeRepository
from ..ports.i_event_publisher import IEventPublisher
from ...domain.events.knowledge_entry_deleted import KnowledgeEntryDeleted
from ...infrastructure.logging_config import (
    get_knowledge_logger,
    log_knowledge_entry_deleted,
)


class DeleteKnowledgeEntryUseCase:
    """
    Use case for deleting knowledge entries.

    Orchestrates:
    1. Verify entry exists
    2. Delete from repository (hard delete with CASCADE)
    3. Publish KnowledgeEntryDeleted domain event

    Constitution Compliance:
    - Article I (DDD): Application service with domain orchestration
    - Article II (Hexagonal): Depends on ports (IKnowledgeRepository, IEventPublisher)
    - Article VI (EDA): Publishes KnowledgeEntryDeleted event
    - Article V (SOLID): SRP - Single responsibility (delete knowledge entry)
    """

    def __init__(
        self,
        repository: IKnowledgeRepository,
        event_publisher: IEventPublisher,
    ):
        """
        Initialize use case with required ports.

        Args:
            repository: Knowledge repository port for persistence
            event_publisher: Event publisher port for domain events

        Constitution Compliance:
        - Article V (SOLID): DIP - Depend on abstractions (ports), not concretions
        """
        self._repository = repository
        self._event_publisher = event_publisher

    async def execute(
        self,
        entry_id: KnowledgeEntryId,
        deleted_by: UserId,
    ) -> None:
        """
        Delete a knowledge entry.

        Args:
            entry_id: Unique identifier of the entry to delete
            deleted_by: User ID performing the deletion

        Raises:
            ValueError: If entry not found
            RepositoryError: If deletion fails
            EventPublishError: If event publishing fails (non-blocking warning)

        Constitution Compliance:
        - Article IV (SSOT): Hard delete from PostgreSQL (CASCADE on audit log)
        - Article VI (EDA): Publishes KnowledgeEntryDeleted event
        """
        # Log operation start (Article VII - Observability)
        logger = get_knowledge_logger(
            component="DeleteKnowledgeEntryUseCase",
            user_id=deleted_by,
        )
        logger.info("Deleting knowledge entry", entry_id=entry_id)

        # Verify entry exists before deletion
        entry = await self._repository.get_by_id(entry_id)
        if entry is None:
            logger.warning("Knowledge entry not found for deletion", entry_id=entry_id)
            raise ValueError(f"Knowledge entry not found: {entry_id}")

        # Create snapshot for audit log
        snapshot = {
            "id": entry.id,
            "content": entry.content,
            "knowledge_type": entry.knowledge_type.value,
            "owning_character_id": entry.owning_character_id,
            "access_level": entry.access_control.access_level.value,
        }

        # Delete from repository (hard delete, CASCADE on audit log)
        await self._repository.delete(entry_id)

        # Log successful deletion
        log_knowledge_entry_deleted(
            entry_id=entry_id,
            deleted_by=deleted_by,
            snapshot=snapshot,
        )

        # Create domain event
        now = datetime.now(timezone.utc)
        event = KnowledgeEntryDeleted(
            entry_id=entry_id,
            deleted_by=deleted_by,
            timestamp=now,
        )

        # Publish domain event to Kafka (non-blocking, best-effort)
        try:
            await self._event_publisher.publish(
                topic="knowledge.entry.deleted",
                event={
                    "event_id": event.event_id,
                    "entry_id": event.entry_id,
                    "deleted_by": event.deleted_by,
                    "timestamp": event.timestamp.isoformat(),
                },
                key=event.entry_id,
                headers={
                    "event_type": "KnowledgeEntryDeleted",
                    "source": "knowledge-management",
                },
            )
            logger.info("Domain event published successfully", event_id=event.event_id)
        except Exception as e:
            # Event publishing failure is non-blocking (log warning)
            logger.warning(
                "Failed to publish domain event", error=str(e), event_id=event.event_id
            )

