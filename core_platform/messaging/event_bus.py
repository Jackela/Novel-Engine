"""
Event Bus and Domain Event Management
====================================

High-level event bus for domain event publishing and subscription
with type safety, event routing, and handler management.
"""

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar
from uuid import uuid4

from ..monitoring.metrics import EventBusMetrics
from .kafka_client import KafkaClient, get_kafka_client

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="DomainEvent")


class EventPriority(Enum):
    """Event priority levels for routing and processing."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DomainEvent:
    """
    Base class for all domain events.

    All domain events should inherit from this class and implement
    the required fields for event sourcing and messaging.
    """

    # Required fields (no defaults)
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    timestamp: str

    # Optional fields with defaults
    event_version: str = "1.0.0"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    retry_count: int = 0

    def __post_init__(self):
        """Ensure required fields are set."""
        if not self.event_id:
            self.event_id = str(uuid4())

        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

        if not self.event_type:
            # Auto-generate event type from class name
            self.event_type = f"{self.aggregate_type.lower()}.{self.__class__.__name__.lower()}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return asdict(self)

    def get_topic_name(self) -> str:
        """Get the Kafka topic name for this event."""
        return f"domain-events-{self.aggregate_type.lower()}"

    def get_partition_key(self) -> str:
        """Get the partition key for this event."""
        return self.aggregate_id


class EventHandler:
    """Base class for event handlers."""

    def __init__(self, handler_func: Callable, event_type: str, handler_id: str = None):
        self.handler_func = handler_func
        self.event_type = event_type
        self.handler_id = handler_id or f"{handler_func.__module__}.{handler_func.__name__}"
        self.is_async = asyncio.iscoroutinefunction(handler_func)

    async def handle(self, event: DomainEvent, context: Dict[str, Any]) -> None:
        """Handle the event."""
        try:
            if self.is_async:
                await self.handler_func(event, context)
            else:
                self.handler_func(event, context)
        except Exception as e:
            logger.error(f"Handler {self.handler_id} failed for event {event.event_type}: {e}")
            raise


class EventBus:
    """
    High-level event bus for domain event management.

    Features:
    - Type-safe event publishing and subscription
    - Automatic topic routing and partitioning
    - Event handler registration and management
    - Error handling and retry mechanisms
    - Event filtering and routing
    - Performance monitoring and metrics
    """

    def __init__(self, kafka_client: Optional[KafkaClient] = None):
        """Initialize event bus with Kafka client."""
        self._kafka_client = kafka_client or get_kafka_client()
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._metrics = EventBusMetrics()
        self._consumer_groups: Set[str] = set()
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize the event bus."""
        if self._is_initialized:
            return

        logger.info("Initializing Event Bus...")

        # Ensure Kafka client is connected
        await self._kafka_client.connect()

        self._is_initialized = True
        logger.info("Event Bus initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown the event bus."""
        if not self._is_initialized:
            return

        logger.info("Shutting down Event Bus...")

        # Stop all consumer groups
        for group_id in self._consumer_groups:
            await self._kafka_client.unsubscribe(group_id)

        self._consumer_groups.clear()
        self._is_initialized = False
        logger.info("Event Bus shutdown complete")

    async def publish(self, event: DomainEvent, headers: Optional[Dict[str, str]] = None) -> None:
        """
        Publish a domain event to the event bus.

        Args:
            event: Domain event to publish
            headers: Optional additional headers
        """
        if not self._is_initialized:
            await self.initialize()

        try:
            self._metrics.record_event_publish_start()

            # Prepare event data
            event_data = event.to_dict()
            topic = event.get_topic_name()
            partition_key = event.get_partition_key()

            # Prepare headers
            event_headers = headers or {}
            event_headers.update(
                {
                    "event_type": event.event_type,
                    "event_version": event.event_version,
                    "aggregate_type": event.aggregate_type,
                    "priority": event.priority.value,
                }
            )

            # Publish to Kafka
            await self._kafka_client.publish(
                topic=topic,
                message=event_data,
                key=partition_key,
                headers=event_headers,
            )

            self._metrics.record_event_published(event.event_type, topic)
            logger.debug(f"Published event {event.event_type} to topic {topic}")

        except Exception as e:
            self._metrics.record_event_publish_failed(event.event_type)
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            raise

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """
        Publish multiple events as a batch.

        Args:
            events: List of domain events to publish
        """
        if not events:
            return

        if not self._is_initialized:
            await self.initialize()

        try:
            self._metrics.record_batch_publish_start()

            # Group events by topic
            events_by_topic: Dict[str, List[DomainEvent]] = {}
            for event in events:
                topic = event.get_topic_name()
                if topic not in events_by_topic:
                    events_by_topic[topic] = []
                events_by_topic[topic].append(event)

            # Publish each topic batch
            for topic, topic_events in events_by_topic.items():
                messages = [event.to_dict() for event in topic_events]
                keys = [event.get_partition_key() for event in topic_events]
                headers = [
                    {
                        "event_type": event.event_type,
                        "event_version": event.event_version,
                        "aggregate_type": event.aggregate_type,
                        "priority": event.priority.value,
                    }
                    for event in topic_events
                ]

                await self._kafka_client.publish_batch(
                    topic=topic, messages=messages, keys=keys, headers=headers
                )

            self._metrics.record_batch_published(len(events))
            logger.debug(f"Published batch of {len(events)} events")

        except Exception as e:
            self._metrics.record_batch_publish_failed()
            logger.error(f"Failed to publish event batch: {e}")
            raise

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[DomainEvent, Dict[str, Any]], None],
        consumer_group: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Subscribe to domain events of a specific type.

        Args:
            event_type: Type of event to subscribe to
            handler: Function to handle received events
            consumer_group: Consumer group ID (auto-generated if not provided)
            filters: Optional event filters

        Returns:
            Handler ID for unsubscription
        """
        # Create handler wrapper
        handler_id = f"{handler.__module__}.{handler.__name__}_{uuid4().hex[:8]}"
        event_handler = EventHandler(handler, event_type, handler_id)

        # Register handler
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(event_handler)

        # Start consumer if needed
        if consumer_group:
            asyncio.create_task(self._start_consumer(consumer_group, event_type))

        logger.info(f"Subscribed handler {handler_id} to event type {event_type}")
        return handler_id

    def unsubscribe(self, handler_id: str) -> None:
        """Unsubscribe an event handler."""
        for event_type, handlers in self._handlers.items():
            self._handlers[event_type] = [h for h in handlers if h.handler_id != handler_id]

        logger.info(f"Unsubscribed handler {handler_id}")

    async def _start_consumer(self, consumer_group: str, event_type: str) -> None:
        """Start a consumer for the given event type."""
        if consumer_group in self._consumer_groups:
            return

        try:
            # Determine topics based on event type
            # For now, subscribe to all domain-events-* topics
            topics = [
                "domain-events-characters",
                "domain-events-stories",
                "domain-events-campaigns",
                "domain-events-interactions",
            ]

            # Start consumer
            await self._kafka_client.subscribe(
                topics=topics,
                consumer_group=consumer_group,
                message_handler=self._handle_message,
            )

            self._consumer_groups.add(consumer_group)
            logger.info(f"Started consumer group {consumer_group} for event type {event_type}")

        except Exception as e:
            logger.error(f"Failed to start consumer for group {consumer_group}: {e}")
            raise

    async def _handle_message(self, message_data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Handle received Kafka message."""
        try:
            # Extract event information
            event_type = message_data.get("event_type")
            if not event_type:
                logger.warning("Received message without event_type")
                return

            self._metrics.record_event_received(event_type)

            # Find handlers for this event type
            handlers = self._handlers.get(event_type, [])
            if not handlers:
                logger.debug(f"No handlers registered for event type {event_type}")
                return

            # Create domain event object
            event = self._create_event_from_data(message_data)

            # Execute all handlers
            for handler in handlers:
                try:
                    await handler.handle(event, context)
                    self._metrics.record_event_handled(event_type)
                except Exception as e:
                    self._metrics.record_event_handling_failed(event_type)
                    logger.error(f"Handler failed for event {event_type}: {e}")
                    # Continue with other handlers

        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

    def _create_event_from_data(self, data: Dict[str, Any]) -> DomainEvent:
        """Create a DomainEvent object from message data."""
        # For now, create a generic DomainEvent
        # In a full implementation, you'd have a registry of event types
        return DomainEvent(
            event_id=data.get("event_id", str(uuid4())),
            event_type=data.get("event_type", ""),
            event_version=data.get("event_version", "1.0.0"),
            aggregate_id=data.get("aggregate_id", ""),
            aggregate_type=data.get("aggregate_type", ""),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            user_id=data.get("user_id"),
            priority=EventPriority(data.get("priority", "normal")),
            retry_count=data.get("retry_count", 0),
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus performance metrics."""
        metrics = self._metrics.get_all_metrics()
        metrics.update(
            {
                "registered_handlers": sum(len(handlers) for handlers in self._handlers.values()),
                "active_consumers": len(self._consumer_groups),
                "event_types": len(self._handlers),
            }
        )
        return metrics

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the event bus."""
        health_status = {
            "status": "healthy",
            "initialized": self._is_initialized,
            "kafka_health": {},
            "handlers": len(self._handlers),
            "consumers": len(self._consumer_groups),
            "errors": [],
        }

        # Check Kafka health
        try:
            kafka_health = await self._kafka_client.health_check()
            health_status["kafka_health"] = kafka_health

            if kafka_health["status"] != "healthy":
                health_status["status"] = "degraded"
                health_status["errors"].append("Kafka client unhealthy")

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["errors"].append(f"Kafka health check failed: {str(e)}")

        return health_status


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def initialize_event_bus() -> None:
    """Initialize the global event bus."""
    bus = get_event_bus()
    await bus.initialize()


async def shutdown_event_bus() -> None:
    """Shutdown the global event bus."""
    global _event_bus
    if _event_bus:
        await _event_bus.shutdown()
        _event_bus = None


# Decorator for event handlers
def event_handler(event_type: str, consumer_group: Optional[str] = None):
    """
    Decorator to register event handlers.

    Usage:
        @event_handler("character.created")
        async def handle_character_created(event: DomainEvent, context: Dict[str, Any]):
            # Handle the event
            pass
    """

    def decorator(func: Callable):
        # Register handler when module is imported
        bus = get_event_bus()
        bus.subscribe(event_type, func, consumer_group)
        return func

    return decorator


# Convenience functions
async def publish_event(event: DomainEvent) -> None:
    """Publish a domain event."""
    bus = get_event_bus()
    await bus.publish(event)


async def publish_events(events: List[DomainEvent]) -> None:
    """Publish multiple domain events."""
    bus = get_event_bus()
    await bus.publish_batch(events)
