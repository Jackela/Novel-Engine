"""
Event-driven architecture components for the Novel Engine.
"""

from .event_bus import Event, EventBus, EventHandler, EventPriority, EventStatus
from .event_processor import EventProcessor, ProcessingStrategy
from .event_registry import EventRegistry, EventType
from .event_store import EventStore, EventStoreConfig
from .outbox import Outbox, OutboxEvent, OutboxMetrics, OutboxStatus

__all__ = [
    "EventBus",
    "EventHandler",
    "Event",
    "EventPriority",
    "EventStatus",
    "EventRegistry",
    "EventType",
    "EventStore",
    "EventStoreConfig",
    "EventProcessor",
    "ProcessingStrategy",
    "Outbox",
    "OutboxEvent",
    "OutboxMetrics",
    "OutboxStatus",
]
