#!/usr/bin/env python3
"""WorldSimulationService - World Simulation Tick Service (Shim).

⚠️  DEPRECATION NOTICE:
    This module is kept for backward compatibility.
    Please use `src.contexts.world.application.services.simulation` instead.

    Old: from src.contexts.world.application.services.world_simulation_service import WorldSimulationService
    New: from src.contexts.world.application.services.simulation import WorldSimulationService
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "world_simulation_service.py is deprecated. "
    "Use src.contexts.world.application.services.simulation instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all symbols from the new package
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
