"""
CreateKnowledgeEntryUseCase

Application use case for creating new knowledge entries.

Constitution Compliance:
- Article I (DDD): Application service orchestrating domain logic
- Article II (Hexagonal): Use case depends on ports, not adapters
- Article VI (EDA): Publishes KnowledgeEntryCreated domain event
- Article VII (Observability): Structured logging for all operations
"""

from datetime import datetime, timezone
from uuid import uuid4

from src.core.types.shared_types import CharacterId, KnowledgeEntryId, UserId

from ...domain.events.knowledge_entry_created import KnowledgeEntryCreated
from ...domain.models.access_control_rule import AccessControlRule
from ...domain.models.access_level import AccessLevel
from ...domain.models.knowledge_entry import KnowledgeEntry
from ...domain.models.knowledge_type import KnowledgeType
from ...infrastructure.logging_config import (
    get_knowledge_logger,
    log_knowledge_entry_created,
)
from ..ports.i_event_publisher import IEventPublisher
from ..ports.i_knowledge_repository import IKnowledgeRepository


class CreateKnowledgeEntryUseCase:
    """
    Use case for creating new knowledge entries.

    Orchestrates:
    1. Domain model creation (KnowledgeEntry aggregate)
    2. Persistence via repository port
    3. Domain event publishing via event publisher port

    Constitution Compliance:
    - Article I (DDD): Application service with domain orchestration
    - Article II (Hexagonal): Depends on ports (IKnowledgeRepository, IEventPublisher)
    - Article VI (EDA): Publishes KnowledgeEntryCreated event
    - Article V (SOLID): SRP - Single responsibility (create knowledge entry)
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
        content: str,
        knowledge_type: KnowledgeType,
        owning_character_id: CharacterId | None,
        access_level: AccessLevel,
        created_by: UserId,
        allowed_roles: tuple[str, ...] = (),
        allowed_character_ids: tuple[str, ...] = (),
    ) -> KnowledgeEntryId:
        """
        Create a new knowledge entry.

        Args:
            content: Knowledge content text (must not be empty)
            knowledge_type: Category of knowledge
            owning_character_id: Character this belongs to (None for world knowledge)
            access_level: Access control level
            allowed_roles: Roles permitted (for ROLE_BASED access)
            allowed_character_ids: Character IDs permitted (for CHARACTER_SPECIFIC)
            created_by: User ID creating this entry

        Returns:
            KnowledgeEntryId of the created entry

        Raises:
            ValueError: If domain invariants are violated
            RepositoryError: If persistence fails
            EventPublishError: If event publishing fails (non-blocking warning)

        Constitution Compliance:
        - Article I (DDD): Domain model enforces invariants
        - Article VI (EDA): Publishes KnowledgeEntryCreated event
        """
        # Create access control rule (validates invariants)
        access_control = AccessControlRule(
            access_level=access_level,
            allowed_roles=allowed_roles,
            allowed_character_ids=allowed_character_ids,
        )

        # Generate unique ID
        entry_id = str(uuid4())

        # Create timestamp
        now = datetime.now(timezone.utc)

        # Create KnowledgeEntry aggregate (validates invariants)
        entry = KnowledgeEntry(
            id=entry_id,
            content=content,
            knowledge_type=knowledge_type,
            owning_character_id=owning_character_id,
            access_control=access_control,
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )

        # Log operation start (Article VII - Observability)
        logger = get_knowledge_logger(
            component="CreateKnowledgeEntryUseCase",
            user_id=created_by,
        )
        logger.info(
            "Creating knowledge entry",
            knowledge_type=knowledge_type.value,
            access_level=access_level.value,
        )

        # Persist to repository (SSOT)
        await self._repository.save(entry)

        # Log successful creation
        log_knowledge_entry_created(
            entry_id=entry.id,
            knowledge_type=entry.knowledge_type.value,
            created_by=entry.created_by,
            metadata={
                "access_level": entry.access_control.access_level.value,
                "owning_character_id": entry.owning_character_id,
            },
        )

        # Create and publish domain event
        event = KnowledgeEntryCreated(
            entry_id=entry.id,
            knowledge_type=entry.knowledge_type,
            owning_character_id=entry.owning_character_id,
            created_by=entry.created_by,
            timestamp=entry.created_at,
        )

        # Publish event to Kafka (non-blocking, best-effort)
        try:
            await self._event_publisher.publish(
                topic="knowledge.entry.created",
                event={
                    "event_id": event.event_id,
                    "entry_id": event.entry_id,
                    "knowledge_type": event.knowledge_type.value,
                    "owning_character_id": event.owning_character_id,
                    "created_by": event.created_by,
                    "timestamp": event.timestamp.isoformat(),
                },
                key=event.entry_id,
                headers={
                    "event_type": "KnowledgeEntryCreated",
                    "source": "knowledge-management",
                },
            )
            logger.info("Domain event published successfully", event_id=event.event_id)
        except Exception as e:
            # Event publishing failure is non-blocking (log warning)
            logger.warning(
                "Failed to publish domain event", error=str(e), event_id=event.event_id
            )

        return entry.id
