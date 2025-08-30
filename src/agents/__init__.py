"""
PersonaAgent Components Package
==============================

Component-based PersonaAgent architecture for Wave 6.2 refactoring.

Components:
- PersonaCore: Core agent infrastructure
- CharacterContextManager: Character data management
- DecisionEngine: Decision-making logic
- PersonaAgent: Refactored main agent class
"""

from .context_manager import CharacterContextManager
from .decision_engine import (
    ActionEvaluation,
    DecisionEngine,
    SituationAssessment,
    ThreatLevel,
)
from .persona_agent_refactored import PersonaAgent, create_persona_agent
from .persona_core import AgentIdentity, AgentState, PersonaCore

__all__ = [
    "PersonaCore",
    "AgentIdentity",
    "AgentState",
    "CharacterContextManager",
    "DecisionEngine",
    "ThreatLevel",
    "SituationAssessment",
    "ActionEvaluation",
    "PersonaAgent",
    "create_persona_agent",
]
