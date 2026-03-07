#!/usr/bin/env python3
"""World Context Domain Errors.

This module provides centralized error types for the world context.
All errors use the Result[T, Error] pattern for explicit error handling.
"""

from typing import Any, Dict, List

from src.core.result import Error


class WorldError(Error):
    """Base error for world-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="WORLD_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class WorldNotFoundError(Error):
    """Error raised when a requested world is not found."""

    def __init__(self, world_id: str) -> None:
        super().__init__(
            code="WORLD_NOT_FOUND",
            message=f"World not found: {world_id}",
            recoverable=False,
            details={"world_id": world_id},
        )


class WorldValidationError(Error):
    """Error raised when world data validation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="WORLD_VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class EventError(Error):
    """Base error for event-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="EVENT_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class EventNotFoundError(Error):
    """Error raised when a requested event is not found."""

    def __init__(self, event_id: str) -> None:
        super().__init__(
            code="EVENT_NOT_FOUND",
            message=f"Event not found: {event_id}",
            recoverable=False,
            details={"event_id": event_id},
        )


class EventValidationError(Error):
    """Error raised when event data validation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="EVENT_VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class LocationError(Error):
    """Base error for location-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="LOCATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class LocationNotFoundError(Error):
    """Error raised when a requested location is not found."""

    def __init__(self, location_id: str) -> None:
        super().__init__(
            code="LOCATION_NOT_FOUND",
            message=f"Location not found: {location_id}",
            recoverable=False,
            details={"location_id": location_id},
        )


class LocationValidationError(Error):
    """Error raised when location data validation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="LOCATION_VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class FactionError(Error):
    """Base error for faction-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="FACTION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class FactionNotFoundError(Error):
    """Error raised when a requested faction is not found."""

    def __init__(self, faction_id: str) -> None:
        super().__init__(
            code="FACTION_NOT_FOUND",
            message=f"Faction not found: {faction_id}",
            recoverable=False,
            details={"faction_id": faction_id},
        )


class FactionValidationError(Error):
    """Error raised when faction data validation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="FACTION_VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class GeopoliticsError(Error):
    """Base error for geopolitics-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="GEOPOLITICS_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class DiplomacyError(Error):
    """Error raised when diplomatic operation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="DIPLOMACY_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class SimulationError(Error):
    """Base error for simulation-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SIMULATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class SimulationValidationError(Error):
    """Error raised when simulation data validation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SIMULATION_VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class InvalidDaysError(SimulationError):
    """Error raised when days parameter is invalid."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            details=details or {},
        )


class SaveFailedError(SimulationError):
    """Error raised when saving world state fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            details=details or {},
        )


class SnapshotFailedError(SimulationError):
    """Error raised when snapshot creation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            details=details or {},
        )


class SnapshotError(Error):
    """Error raised when snapshot operation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SNAPSHOT_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class SnapshotNotFoundError(Error):
    """Error raised when a requested snapshot is not found."""

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(
            code="SNAPSHOT_NOT_FOUND",
            message=f"Snapshot not found: {snapshot_id}",
            recoverable=False,
            details={"snapshot_id": snapshot_id},
        )


class RumorError(Error):
    """Base error for rumor-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="RUMOR_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class RumorNotFoundError(Error):
    """Error raised when a requested rumor is not found."""

    def __init__(self, rumor_id: str) -> None:
        super().__init__(
            code="RUMOR_NOT_FOUND",
            message=f"Rumor not found: {rumor_id}",
            recoverable=False,
            details={"rumor_id": rumor_id},
        )


class RumorValidationError(Error):
    """Error raised when rumor data validation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="RUMOR_VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class RumorPropagationError(Error):
    """Error raised when rumor propagation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="RUMOR_PROPAGATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class RumorCreationError(Error):
    """Error raised when rumor creation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="RUMOR_CREATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class TimeError(Error):
    """Base error for time-related operations."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="TIME_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class TimeValidationError(Error):
    """Error raised when time data validation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="TIME_VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class IntentGenerationError(Error):
    """Error raised when faction intent generation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="INTENT_GENERATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class FactionTickError(Error):
    """Error raised when faction tick processing fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="FACTION_TICK_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class SanityCheckError(Exception):
    """Exception raised when sanity check violations are found.
    
    This exception is raised by check_and_raise() when ERROR-level
    violations are detected. It contains the list of violations
    for inspection and reporting.
    
    Can also be used with a simple message string for backward compatibility
    with Result-pattern error handling.
    
    Attributes:
        violations: List of SanityViolation instances that caused the error.
                    Empty if initialized with just a message.
    """

    def __init__(self, violations: List[Any] | str) -> None:
        if isinstance(violations, str):
            # Backward compatibility: initialize with a message string
            self.violations: List[Any] = []
            super().__init__(violations)
        else:
            # Normal case: initialize with list of violations
            self.violations = violations
            # Build a readable message from violations
            messages = []
            for v in violations:
                messages.append(f"[{v.severity.value}] {v.rule_name}: {v.message}")
            message = "Sanity check failed with {} violation(s):\n  - {}".format(
                len(violations),
                "\n  - ".join(messages)
            )
            super().__init__(message)


class SocialGraphError(Error):
    """Error raised when social graph analysis fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SOCIAL_GRAPH_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class RepositoryError(Error):
    """Error raised when repository operation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="REPOSITORY_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class RollbackError(Error):
    """Error raised when rollback operation fails."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="ROLLBACK_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )


class ValidationError(Error):
    """Generic validation error."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=details,
        )
