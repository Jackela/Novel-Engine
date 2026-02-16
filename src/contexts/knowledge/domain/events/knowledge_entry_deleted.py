"""
KnowledgeEntryDeleted Domain Event

Domain event emitted when a knowledge entry is deleted.

Constitution Compliance:
- Article VI (EDA): Pure domain event with immutable state
- Article I (DDD): Pure domain model with no infrastructure dependencies
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.core.types.shared_types import KnowledgeEntryId, UserId


@dataclass(frozen=True)
class KnowledgeEntryDeleted:
    """
    Domain event indicating a knowledge entry was deleted.

    This event is emitted by the delete use case after successful deletion.
    It is published to Kafka for event-driven processing, audit trail, and CASCADE cleanup.

    Attributes:
        entry_id: Unique identifier of the deleted knowledge entry
        deleted_by: User ID who performed the deletion
        timestamp: When the deletion occurred (UTC)
        event_id: Unique identifier for this event instance

    Constitution Compliance:
    - Article VI (EDA): Immutable domain event for event-driven architecture
    - Article I (DDD): Pure domain model with no infrastructure coupling

    Example:
        >>> event = KnowledgeEntryDeleted(
        ...     entry_id="550e8400-e29b-41d4-a716-446655440000",
        ...     deleted_by="user-123",
        ...     timestamp=datetime.now(timezone.utc)
        ... )
    """

    entry_id: KnowledgeEntryId
    deleted_by: UserId
    timestamp: datetime
    event_id: str = field(default_factory=lambda: str(uuid4()))
