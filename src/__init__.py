"""
Novel Engine - Advanced AI Narrative Generation Platform
========================================================

Core package for Novel Engine providing:
- Multi-agent narrative generation with modular architecture
- Subjective reality modeling
- Real-time story coordination
- Production-ready infrastructure

Version: 2.0.0 - Modular Refactoring Update
"""

__version__ = "2.0.0"
__author__ = "Novel Engine Team"
__description__ = "Advanced AI Narrative Generation Platform"

# Core exports - Legacy architecture
try:
    from .core.emergent_narrative import EmergentNarrativeEngine  # noqa: F401
    from .core.subjective_reality import SubjectiveRealityEngine  # noqa: F401
    from .infrastructure.observability import MetricsCollector  # noqa: F401
    from .infrastructure.state_store import UnifiedStateManager  # noqa: F401

    # Add legacy exports to __all__
    LEGACY_EXPORTS = [
        "SubjectiveRealityEngine",
        "EmergentNarrativeEngine",
        "UnifiedStateManager",
        "MetricsCollector",
    ]
except ImportError:
    # Legacy components not available
    LEGACY_EXPORTS = []

from .event_bus import EventBus  # noqa: F401

# Core agent system - Modular architecture
from .persona_agent import PersonaAgent  # noqa: F401

# DirectorAgent components - Exposed modularly
try:
    from .agent_lifecycle_manager import AgentLifecycleManager  # noqa: F401
    from .director_agent_base import DirectorAgentBase  # noqa: F401
    from .turn_orchestrator import TurnOrchestrator  # noqa: F401
    from .world_state_coordinator import WorldStateCoordinator  # noqa: F401

    DIRECTOR_COMPONENTS = [
        "DirectorAgentBase",
        "TurnOrchestrator",
        "WorldStateCoordinator",
        "AgentLifecycleManager",
    ]
except ImportError:
    DIRECTOR_COMPONENTS = []

# PersonaAgent components - Exposed modularly
try:
    from .character_interpreter import CharacterInterpreter  # noqa: F401
    from .decision_engine import DecisionEngine  # noqa: F401
    from .memory_interface import MemoryInterface  # noqa: F401
    from .persona_agent_core import PersonaAgentCore  # noqa: F401

    PERSONA_COMPONENTS = [
        "PersonaAgentCore",
        "DecisionEngine",
        "CharacterInterpreter",
        "MemoryInterface",
    ]
except ImportError:
    PERSONA_COMPONENTS = []

# Integrated architecture - Main exports
try:
    from ..director_agent_integrated import (  # noqa: F401
        DirectorAgent as DirectorAgentIntegrated,
    )
    from .persona_agent_integrated import (  # noqa: F401
        PersonaAgent as PersonaAgentIntegrated,
    )

    INTEGRATED_EXPORTS = ["PersonaAgentIntegrated", "DirectorAgentIntegrated"]
except ImportError:
    INTEGRATED_EXPORTS = []

# Core agent interface
CORE_EXPORTS = ["PersonaAgent", "EventBus"]

# Build complete export list
__all__ = (
    CORE_EXPORTS
    + DIRECTOR_COMPONENTS
    + PERSONA_COMPONENTS
    + INTEGRATED_EXPORTS
    + LEGACY_EXPORTS
)
