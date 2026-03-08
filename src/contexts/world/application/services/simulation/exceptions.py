"""World Simulation Exceptions.

Exception classes for simulation errors.
"""

from src.contexts.world.domain.errors import SimulationError


class InvalidDaysError(SimulationError):
    """Error raised when the days parameter is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            details={},
        )


class SnapshotFailedError(SimulationError):
    """Error raised when snapshot creation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            details={},
        )
