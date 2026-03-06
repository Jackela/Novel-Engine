#!/usr/bin/env python3
"""World context application services.

This module exports services that provide higher-level business operations
beyond simple CRUD, such as graph analytics and social network analysis.
"""

from src.contexts.world.domain.errors import (
    InvalidDaysError,
    RepositoryError,
    RollbackError,
    SaveFailedError,
    SnapshotFailedError,
    WorldNotFoundError,
)
from src.contexts.world.domain.value_objects.simulation_tick import SimulationTick

from .event_service import EventListResult, EventService
from .faction_decision_service import (
    ACTION_DEFINITIONS,
    ActionDefinition,
    DecisionContext,
    FactionDecisionService,
)
from .rumor_propagation_service import (
    ILocationRepository,
    IRumorRepository,
    RumorPropagationService,
    RumorStatistics,
)
from .rumor_service import RumorService
from .simulation.exceptions import InvalidDaysError, SnapshotFailedError
from .simulation.models import ResolutionResult
from .simulation.protocols import (
    IFactionRepository,
    ISnapshotService,
    IWorldStateRepository,
)
from .simulation.service import WorldSimulationService
from .simulation_sanity_checker import (
    SanityCheckError,
    SanityViolation,
    Severity,
    SimulationSanityChecker,
)
from .social_graph_service import (
    CharacterCentrality,
    SocialAnalysisResult,
    SocialGraphService,
)

__all__ = [
    "ACTION_DEFINITIONS",
    "ActionDefinition",
    "CharacterCentrality",
    "DecisionContext",
    "EventListResult",
    "EventService",
    "FactionDecisionService",
    "IFactionRepository",
    "ILocationRepository",
    "IRumorRepository",
    "ISnapshotService",
    "IWorldStateRepository",
    "InvalidDaysError",
    "ResolutionResult",
    "RepositoryError",
    "RollbackError",
    "RumorPropagationService",
    "RumorService",
    "RumorStatistics",
    "SaveFailedError",
    "SanityCheckError",
    "SanityViolation",
    "Severity",
    "SimulationTick",
    "SnapshotFailedError",
    "SocialAnalysisResult",
    "SocialGraphService",
    "SimulationSanityChecker",
    "WorldNotFoundError",
    "WorldSimulationService",
]
