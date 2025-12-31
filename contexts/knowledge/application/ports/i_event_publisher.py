"""
Domain Event Publisher Port (Interface)

Pure interface for publishing domain events to message infrastructure.
Part of Hexagonal Architecture - Application Layer defines the port,
Infrastructure Layer provides the adapter implementation.

Constitution Compliance:
- Article II (Hexagonal Architecture): Port abstraction for event publishing
- Article VI (Event-Driven Architecture): Domain events for all mutations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IEventPublisher(ABC):
    """
    Port interface for publishing domain events.

    This abstraction allows the domain and application layers to remain
    independent of specific messaging infrastructure (Kafka, RabbitMQ, etc.).

    Implementations must:
    - Serialize domain events to message format
    - Handle connection failures with appropriate retry logic
    - Ensure at-least-once delivery semantics
    - Provide idempotency through event_id
    """

    @abstractmethod
    async def publish(
        self,
        topic: str,
        event: Dict[str, Any],
        key: str | None = None,
        headers: Dict[str, str] | None = None,
    ) -> None:
        """
        Publish a single domain event to the specified topic.

        Args:
            topic: Target topic name (e.g., "knowledge.entry.created")
            event: Domain event data as dictionary
            key: Optional partition key for ordering guarantees
            headers: Optional message headers for metadata

        Raises:
            EventPublishException: If publishing fails after retries
        """
        pass

    @abstractmethod
    async def publish_batch(
        self,
        topic: str,
        events: list[Dict[str, Any]],
        keys: list[str | None] | None = None,
        headers: list[Dict[str, str] | None] | None = None,
    ) -> None:
        """
        Publish multiple domain events to the specified topic in a batch.

        Batch publishing improves throughput for bulk operations.

        Args:
            topic: Target topic name
            events: List of domain event data dictionaries
            keys: Optional list of partition keys (same length as events)
            headers: Optional list of headers (same length as events)

        Raises:
            EventPublishException: If batch publishing fails after retries
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the event publishing infrastructure.

        Returns:
            Dictionary with health status information:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "connected": bool,
                "errors": list[str]
            }
        """
        pass


class EventPublishException(Exception):
    """Raised when event publishing fails."""

    pass
