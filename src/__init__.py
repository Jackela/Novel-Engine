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
    from .core.subjective_reality import SubjectiveRealityEngine
    from .core.emergent_narrative import EmergentNarrativeEngine
    from .infrastructure.state_store import UnifiedStateManager
    from .infrastructure.observability import MetricsCollector
    
    # Add legacy exports to __all__
    LEGACY_EXPORTS = [
        "SubjectiveRealityEngine",
        "EmergentNarrativeEngine", 
        "UnifiedStateManager",
        "MetricsCollector"
    ]
except ImportError:
    # Legacy components not available
    LEGACY_EXPORTS = []

# Core agent system - Modular architecture
from .persona_agent import PersonaAgent
from .event_bus import EventBus

# DirectorAgent components - Exposed modularly
try:
    from .director_agent_base import DirectorAgentBase
    from .turn_orchestrator import TurnOrchestrator
    from .world_state_coordinator import WorldStateCoordinator
    from .agent_lifecycle_manager import AgentLifecycleManager
    
    DIRECTOR_COMPONENTS = [
        "DirectorAgentBase",
        "TurnOrchestrator", 
        "WorldStateCoordinator",
        "AgentLifecycleManager"
    ]
except ImportError:
    DIRECTOR_COMPONENTS = []

# PersonaAgent components - Exposed modularly
try:
    from .persona_agent_core import PersonaAgentCore
    from .decision_engine import DecisionEngine
    from .character_interpreter import CharacterInterpreter
    from .memory_interface import MemoryInterface
    
    PERSONA_COMPONENTS = [
        "PersonaAgentCore",
        "DecisionEngine",
        "CharacterInterpreter", 
        "MemoryInterface"
    ]
except ImportError:
    PERSONA_COMPONENTS = []

# Integrated architecture - Main exports
try:
    from .persona_agent_integrated import PersonaAgent as PersonaAgentIntegrated
    from ..director_agent_integrated import DirectorAgent as DirectorAgentIntegrated
    
    INTEGRATED_EXPORTS = [
        "PersonaAgentIntegrated",
        "DirectorAgentIntegrated"
    ]
except ImportError:
    INTEGRATED_EXPORTS = []

# Core agent interface
CORE_EXPORTS = [
    "PersonaAgent",
    "EventBus"
]

# Build complete export list
__all__ = CORE_EXPORTS + DIRECTOR_COMPONENTS + PERSONA_COMPONENTS + INTEGRATED_EXPORTS + LEGACY_EXPORTS