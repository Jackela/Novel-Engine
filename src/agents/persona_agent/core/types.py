"""
PersonaAgent Core Types
======================

Type definitions and configuration for the PersonaAgent system.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PersonaAgentConfig:
    """
    Configuration for PersonaAgent behavior and resource limits.

    Attributes:
        max_memory_size: Maximum number of memories to retain
        llm_temperature: Temperature for LLM generation (0.0-2.0)
        llm_max_tokens: Maximum tokens for LLM responses
        decision_timeout_seconds: Timeout for decision-making operations
        enable_logging: Enable detailed logging
        cache_size: Size of response cache
        threat_sensitivity: Sensitivity to threats (0.0-1.0)
        goal_priority_threshold: Minimum priority for goal activation (0.0-1.0)
    """

    max_memory_size: int = 100
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500
    decision_timeout_seconds: float = 30.0
    enable_logging: bool = True
    cache_size: int = 50
    threat_sensitivity: float = 0.5
    goal_priority_threshold: float = 0.3

    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.0 <= self.llm_temperature <= 2.0:
            raise ValueError("llm_temperature must be between 0.0 and 2.0")

        if self.llm_max_tokens <= 0:
            raise ValueError("llm_max_tokens must be positive")

        if self.decision_timeout_seconds <= 0:
            raise ValueError("decision_timeout_seconds must be positive")

        if not 0.0 <= self.threat_sensitivity <= 1.0:
            raise ValueError("threat_sensitivity must be between 0.0 and 1.0")

        if not 0.0 <= self.goal_priority_threshold <= 1.0:
            raise ValueError("goal_priority_threshold must be between 0.0 and 1.0")


@dataclass
class CharacterData:
    """
    Character data structure for PersonaAgent.

    Attributes:
        character_id: Unique character identifier
        name: Character name
        traits: Personality traits and attributes
        background: Character backstory and context
        goals: Character goals and motivations
        relationships: Relationships with other characters
        metadata: Additional character metadata
    """

    character_id: str
    name: str
    traits: Dict[str, Any] = field(default_factory=dict)
    background: Optional[str] = None
    goals: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionContext:
    """
    Context for decision-making operations.

    Attributes:
        world_state: Current world state information
        recent_events: Recent events affecting the character
        active_goals: Currently active character goals
        available_actions: Actions available to the character
        constraints: Decision-making constraints
        metadata: Additional contextual metadata
    """

    world_state: Dict[str, Any] = field(default_factory=dict)
    recent_events: list = field(default_factory=list)
    active_goals: list = field(default_factory=list)
    available_actions: list = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "PersonaAgentConfig",
    "CharacterData",
    "DecisionContext",
]
