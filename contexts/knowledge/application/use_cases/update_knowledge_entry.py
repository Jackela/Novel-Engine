"""
UpdateKnowledgeEntryUseCase

Application use case for updating existing knowledge entries.

Constitution Compliance:
- Article I (DDD): Application service orchestrating domain logic
- Article II (Hexagonal): Use case depends on ports, not adapters
- Article VI (EDA): Publishes KnowledgeEntryUpdated domain event
- Article VII (Observability): Structured logging for all operations
"""

from src.shared_types import KnowledgeEntryId, UserId

from ..ports.i_knowledge_repository import IKnowledgeRepository
from ..ports.i_event_publisher import IEventPublisher
from ...infrastructure.logging_config import get_knowledge_logger, log_knowledge_entry_updated


class UpdateKnowledgeEntryUseCase:
    """
    Use case for updating existing knowledge entries.
    
    Orchestrates:
    1. Retrieve existing entry from repository
    2. Call domain method (update_content) which returns event
    3. Persist updated aggregate
    4. Publish domain event
    
    Constitution Compliance:
    - Article I (DDD): Application service with domain orchestration
    - Article II (Hexagonal): Depends on ports (IKnowledgeRepository, IEventPublisher)
    - Article VI (EDA): Publishes KnowledgeEntryUpdated event
    - Article V (SOLID): SRP - Single responsibility (update knowledge entry)
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
        new_content: str,
        updated_by: UserId,
    ) -> None:
        """
        Update the content of an existing knowledge entry.
        
        Args:
            entry_id: Unique identifier of the entry to update
            new_content: New content text (must not be empty)
            updated_by: User ID performing the update
        
        Raises:
            ValueError: If entry not found or domain invariants violated
            RepositoryError: If persistence fails
            EventPublishError: If event publishing fails (non-blocking warning)
        
        Constitution Compliance:
        - Article I (DDD): Domain model (update_content) enforces invariants
        - Article VI (EDA): Publishes KnowledgeEntryUpdated event
        """
        # Log operation start (Article VII - Observability)
        logger = get_knowledge_logger(
            component="UpdateKnowledgeEntryUseCase",
            user_id=updated_by,
        )
        logger.info("Updating knowledge entry", entry_id=entry_id)
        
        # Retrieve existing entry
        entry = await self._repository.get_by_id(entry_id)
        if entry is None:
            logger.warning("Knowledge entry not found", entry_id=entry_id)
            raise ValueError(f"Knowledge entry not found: {entry_id}")
        
        # Store old content for change tracking
        old_content = entry.content
        
        # Call domain method (returns event)
        event = entry.update_content(new_content, updated_by)
        
        # Persist updated aggregate
        await self._repository.save(entry)
        
        # Log successful update
        log_knowledge_entry_updated(
            entry_id=entry.id,
            updated_by=updated_by,
            changes={"content": {"old": old_content[:50] + "..." if len(old_content) > 50 else old_content, "new": new_content[:50] + "..." if len(new_content) > 50 else new_content}},
        )
        
        # Publish domain event to Kafka (non-blocking, best-effort)
        try:
            await self._event_publisher.publish(
                topic="knowledge.entry.updated",
                event={
                    "event_id": event.event_id,
                    "entry_id": event.entry_id,
                    "updated_by": event.updated_by,
                    "timestamp": event.timestamp.isoformat(),
                },
                key=event.entry_id,
                headers={
                    "event_type": "KnowledgeEntryUpdated",
                    "source": "knowledge-management",
                },
            )
            logger.info("Domain event published successfully", event_id=event.event_id)
        except Exception as e:
            # Event publishing failure is non-blocking (log warning)
            logger.warning("Failed to publish domain event", error=str(e), event_id=event.event_id)
