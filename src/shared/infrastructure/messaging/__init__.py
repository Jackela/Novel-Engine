"""Event-driven messaging infrastructure.

This module provides event bus and event store implementations for
building event-driven architectures.
"""

from src.shared.infrastructure.messaging.event_bus import (
    DomainEvent,
    EventBus,
    EventBusError,
    EventBusNotStartedError,
    EventHandler,
    EventPublishError,
    EventSubscribeError,
)
from src.shared.infrastructure.messaging.event_store import (
    ConcurrencyError,
    EventNotFoundError,
    EventStore,
    EventStoreError,
    InMemoryEventStore,
    StoredEvent,
)
from src.shared.infrastructure.messaging.memory_event_bus import MemoryEventBus

# Kafka is optional - only import if aiokafka is installed
try:
    from src.shared.infrastructure.messaging.kafka_event_bus import KafkaEventBus

    __all__ = [
        # Event Bus
        "DomainEvent",
        "EventBus",
        "EventHandler",
        "MemoryEventBus",
        "KafkaEventBus",
        # Event Bus Exceptions
        "EventBusError",
        "EventBusNotStartedError",
        "EventPublishError",
        "EventSubscribeError",
        # Event Store
        "EventStore",
        "InMemoryEventStore",
        "StoredEvent",
        # Event Store Exceptions
        "EventStoreError",
        "ConcurrencyError",
        "EventNotFoundError",
    ]
except ImportError:
    __all__ = [
        # Event Bus
        "DomainEvent",
        "EventBus",
        "EventHandler",
        "MemoryEventBus",
        # Event Bus Exceptions
        "EventBusError",
        "EventBusNotStartedError",
        "EventPublishError",
        "EventSubscribeError",
        # Event Store
        "EventStore",
        "InMemoryEventStore",
        "StoredEvent",
        # Event Store Exceptions
        "EventStoreError",
        "ConcurrencyError",
        "EventNotFoundError",
    ]
