"""World domain errors."""

from typing import Any, Dict, Optional


class WorldDomainError(Exception):
    """Base error for world domain."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RumorError(WorldDomainError):
    """Error related to rumors."""

    pass


class RumorCreationError(WorldDomainError):
    """Error creating a rumor."""

    pass


class RumorPropagationError(WorldDomainError):
    """Error propagating rumors."""

    pass


class LocationError(WorldDomainError):
    """Error related to locations."""

    pass


class EventError(WorldDomainError):
    """Error related to events."""

    pass
