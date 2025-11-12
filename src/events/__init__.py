"""
Event-driven architecture components for the Novel Engine.
"""

from .event_bus import Event, EventBus, EventHandler
from .event_processor import EventProcessor, ProcessingStrategy
from .event_registry import EventRegistry, EventType
from .event_store import EventStore, EventStoreConfig

__all__ = [
    "EventBus",
    "EventHandler",
    "Event",
    "EventRegistry",
    "EventType",
    "EventStore",
    "EventStoreConfig",
    "EventProcessor",
    "ProcessingStrategy",
]
