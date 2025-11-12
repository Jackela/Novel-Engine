"""
KnowledgeEntryUpdated Domain Event

Domain event emitted when a knowledge entry's content is updated.

Constitution Compliance:
- Article VI (EDA): Pure domain event with immutable state
- Article I (DDD): Pure domain model with no infrastructure dependencies
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.shared_types import KnowledgeEntryId, UserId


@dataclass(frozen=True)
class KnowledgeEntryUpdated:
    """
    Domain event indicating a knowledge entry was updated.
    
    This event is emitted by KnowledgeEntry.update_content() after successful mutation.
    It is published to Kafka for event-driven processing and audit trail.
    
    Attributes:
        entry_id: Unique identifier of the updated knowledge entry
        updated_by: User ID who performed the update
        timestamp: When the update occurred (UTC)
        event_id: Unique identifier for this event instance
    
    Constitution Compliance:
    - Article VI (EDA): Immutable domain event for event-driven architecture
    - Article I (DDD): Pure domain model with no infrastructure coupling
    
    Example:
        >>> event = KnowledgeEntryUpdated(
        ...     entry_id="550e8400-e29b-41d4-a716-446655440000",
        ...     updated_by="user-123",
        ...     timestamp=datetime.now(timezone.utc)
        ... )
    """
    
    entry_id: KnowledgeEntryId
    updated_by: UserId
    timestamp: datetime
    event_id: str = field(default_factory=lambda: str(uuid4()))
