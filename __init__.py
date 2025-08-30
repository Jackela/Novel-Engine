"""
Novel Engine - Advanced AI Narrative Generation Platform
========================================================

Top-level package exports for the Novel Engine with modular refactored architecture.

This package maintains backward compatibility while providing access to the new
modular component architecture implemented in Wave 4 refactoring.

Main Components:
- DirectorAgent: Central simulation orchestrator (now modular)
- PersonaAgent: Character AI agents (now modular)
- EventBus: Decoupled communication system
- Modular Components: Individual specialized components

Version: 2.0.0 - Modular Architecture
"""

__version__ = "2.0.0"
__author__ = "Novel Engine Team"
__description__ = "Advanced AI Narrative Generation Platform with Modular Architecture"

# Main agent classes - backward compatible interfaces
from director_agent import DirectorAgent  # noqa: F401

from src.event_bus import EventBus  # noqa: F401
from src.persona_agent import PersonaAgent  # noqa: F401

# Integrated implementations for advanced usage
try:
    from director_agent_integrated import DirectorAgent as DirectorAgentIntegrated  # noqa: F401

    from src.persona_agent_integrated import PersonaAgent as PersonaAgentIntegrated  # noqa: F401

    INTEGRATED_AVAILABLE = True
except ImportError:
    INTEGRATED_AVAILABLE = False

# Modular components for advanced users
try:
    from src import (
        AgentLifecycleManager,  # noqa: F401
        CharacterInterpreter,  # noqa: F401
        DecisionEngine,  # noqa: F401
        DirectorAgentBase,  # noqa: F401
        MemoryInterface,  # noqa: F401
        PersonaAgentCore,  # noqa: F401
        TurnOrchestrator,  # noqa: F401
        WorldStateCoordinator,  # noqa: F401
    )

    MODULAR_COMPONENTS = [
        "DirectorAgentBase",
        "TurnOrchestrator",
        "WorldStateCoordinator",
        "AgentLifecycleManager",
        "PersonaAgentCore",
        "DecisionEngine",
        "CharacterInterpreter",
        "MemoryInterface",
    ]
except ImportError:
    MODULAR_COMPONENTS = []

# Core exports - backward compatibility maintained
CORE_EXPORTS = ["DirectorAgent", "PersonaAgent", "EventBus"]

# Advanced exports if available
ADVANCED_EXPORTS = []
if INTEGRATED_AVAILABLE:
    ADVANCED_EXPORTS.extend(["DirectorAgentIntegrated", "PersonaAgentIntegrated"])

# Complete export list
__all__ = CORE_EXPORTS + ADVANCED_EXPORTS + MODULAR_COMPONENTS
