"""
PersonaAgent Component Protocols
================================

Defines the interfaces and contracts for all PersonaAgent components.
Uses Python's Protocol for type safety and clear API definition.
"""

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

# Import shared types
try:
    from shared_types import ActionPriority, CharacterAction
except ImportError:
    CharacterAction = Dict
    ActionPriority = str


class ThreatLevel(Enum):
    """Enumeration for threat assessment levels used in character decision-making."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class WorldEvent:
    """
    Represents an event in the world that the PersonaAgent must process.

    Events are broadcast by the DirectorAgent and interpreted subjectively
    by each PersonaAgent based on their personality, knowledge, and biases.
    """

    event_id: str
    event_type: str  # e.g., "battle", "discovery", "political_change"
    source: str  # Entity ID that triggered the event
    affected_entities: List[str]
    location: Optional[str] = None
    description: str = ""
    data: Dict[str, Any] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.affected_entities is None:
            self.affected_entities = []
        if self.data is None:
            self.data = {}
        if self.timestamp == 0.0:
            from datetime import datetime

            self.timestamp = datetime.now().timestamp()


@dataclass
class SubjectiveInterpretation:
    """
    Represents how a PersonaAgent subjectively interprets a world event.

    This captures the character's personal understanding, emotional response,
    and how the event affects their worldview and future decision-making.
    """

    original_event_id: str
    character_understanding: str  # How the character interprets what happened
    emotional_response: str  # Character's emotional reaction
    belief_impact: Dict[str, float]  # Changes to beliefs (-1.0 to 1.0)
    threat_assessment: ThreatLevel = ThreatLevel.NEGLIGIBLE
    relationship_changes: Dict[str, float] = None  # Changes to relationships
    memory_priority: float = 0.5  # How likely this is to be remembered (0.0 to 1.0)

    def __post_init__(self):
        if self.belief_impact is None:
            self.belief_impact = {}
        if self.relationship_changes is None:
            self.relationship_changes = {}


class CharacterDataManagerProtocol(Protocol):
    """Protocol for character data management."""

    @abstractmethod
    async def load_character_data(
        self, character_directory_path: str
    ) -> Dict[str, Any]:
        """Load character data from directory."""
        ...

    @abstractmethod
    async def validate_character_data(self, character_data: Dict[str, Any]) -> bool:
        """Validate character data structure."""
        ...

    @abstractmethod
    async def get_character_trait(self, trait_name: str) -> Any:
        """Get specific character trait value."""
        ...


class DecisionEngineProtocol(Protocol):
    """Protocol for decision making engine."""

    @abstractmethod
    async def make_decision(
        self, world_state: Dict[str, Any], character_context: Dict[str, Any]
    ) -> CharacterAction:
        """Make a decision based on current world state and character context."""
        ...

    @abstractmethod
    async def evaluate_threat(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> ThreatLevel:
        """Evaluate threat level of an event."""
        ...

    @abstractmethod
    async def prioritize_goals(
        self, goals: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prioritize character goals based on context."""
        ...


class WorldInterpretationProtocol(Protocol):
    """Protocol for world event interpretation."""

    @abstractmethod
    async def interpret_event(
        self, event: WorldEvent, character_context: Dict[str, Any]
    ) -> SubjectiveInterpretation:
        """Interpret a world event from character's perspective."""
        ...

    @abstractmethod
    async def update_worldview(self, interpretation: SubjectiveInterpretation) -> None:
        """Update character's worldview based on event interpretation."""
        ...

    @abstractmethod
    async def get_relevant_memories(
        self, context: Dict[str, Any], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get relevant memories for decision making."""
        ...


class MemoryManagerProtocol(Protocol):
    """Protocol for memory management."""

    @abstractmethod
    async def store_memory(
        self, memory: Dict[str, Any], memory_type: str = "short_term"
    ) -> bool:
        """Store a memory."""
        ...

    @abstractmethod
    async def retrieve_memories(
        self, query: Dict[str, Any], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve memories based on query."""
        ...

    @abstractmethod
    async def consolidate_memories(self) -> None:
        """Move important short-term memories to long-term storage."""
        ...


class LLMIntegrationProtocol(Protocol):
    """Protocol for LLM integration."""

    @abstractmethod
    async def generate_character_response(
        self, prompt: str, context: Dict[str, Any]
    ) -> str:
        """Generate character response using LLM."""
        ...

    @abstractmethod
    async def validate_api_connection(self) -> bool:
        """Validate LLM API connection."""
        ...

    @abstractmethod
    async def format_prompt(
        self, base_prompt: str, character_data: Dict[str, Any]
    ) -> str:
        """Format prompt with character-specific context."""
        ...


class AgentStateManagerProtocol(Protocol):
    """Protocol for agent state management."""

    @abstractmethod
    async def update_state(self, state_updates: Dict[str, Any]) -> None:
        """Update agent state."""
        ...

    @abstractmethod
    async def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        ...

    @abstractmethod
    async def save_state(self, file_path: str) -> bool:
        """Save agent state to file."""
        ...

    @abstractmethod
    async def load_state(self, file_path: str) -> bool:
        """Load agent state from file."""
        ...
