"""
KnowledgeEntryCreated Domain Event

Domain event emitted when a new knowledge entry is created.

Constitution Compliance:
- Article VI (EDA): Pure domain event with immutable state
- Article I (DDD): Pure domain model with no infrastructure dependencies
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.shared_types import KnowledgeEntryId, CharacterId, UserId

from ..models.knowledge_type import KnowledgeType


@dataclass(frozen=True)
class KnowledgeEntryCreated:
    """
    Domain event indicating a knowledge entry was created.
    
    This event is emitted by the KnowledgeEntry aggregate after successful creation.
    It is published to Kafka for event-driven processing by other bounded contexts.
    
    Attributes:
        entry_id: Unique identifier of the created knowledge entry
        knowledge_type: Category of knowledge (PROFILE, OBJECTIVE, etc.)
        owning_character_id: Character this knowledge belongs to (None for world knowledge)
        created_by: User ID who created this entry
        timestamp: When the entry was created (UTC)
        event_id: Unique identifier for this event instance
    
    Constitution Compliance:
    - Article VI (EDA): Immutable domain event for event-driven architecture
    - Article I (DDD): Pure domain model with no infrastructure coupling
    
    Example:
        >>> event = KnowledgeEntryCreated(
        ...     entry_id="550e8400-e29b-41d4-a716-446655440000",
        ...     knowledge_type=KnowledgeType.PROFILE,
        ...     owning_character_id="char-001",
        ...     created_by="user-123",
        ...     timestamp=datetime.now(timezone.utc)
        ... )
    """
    
    entry_id: KnowledgeEntryId
    knowledge_type: KnowledgeType
    owning_character_id: CharacterId | None
    created_by: UserId
    timestamp: datetime
    event_id: str = field(default_factory=lambda: str(uuid4()))
