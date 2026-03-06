"""World Simulation Service Package.

Provides world simulation functionality including calendar advancement,
faction intent generation, and simulation tick processing.
"""

from src.contexts.world.application.services.simulation.exceptions import (
    InvalidDaysError,
    SnapshotFailedError,
)
from src.contexts.world.application.services.simulation.models import ResolutionResult
from src.contexts.world.application.services.simulation.protocols import (
    IFactionRepository,
    ISnapshotService,
    IWorldStateRepository,
)
from src.contexts.world.application.services.simulation.service import (
    WorldSimulationService,
)

__all__ = [
    "ResolutionResult",
    "IFactionRepository",
    "ISnapshotService",
    "IWorldStateRepository",
    "WorldSimulationService",
    "InvalidDaysError",
    "SnapshotFailedError",
]
