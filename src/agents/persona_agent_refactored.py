#!/usr/bin/env python3
"""
Refactored PersonaAgent - Wave 6.2 Implementation
=================================================

Modernized PersonaAgent using component-based architecture.
Dramatically reduced from 2,442 LOC to <500 LOC through strategic decomposition.

Components:
- PersonaCore: Identity and lifecycle management
- CharacterContextManager: Character data loading and parsing
- DecisionEngine: Decision-making and action selection
- LLMInterface: Language model integration (future)
- MemoryManager: Experience and relationship tracking (future)

Part of Wave 6.2 PersonaAgent Decomposition Strategy.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.context_manager import CharacterContextManager
from src.agents.decision_engine import DecisionEngine

# Import decomposed components
from src.agents.persona_core import PersonaCore

# Import shared types
from src.core.types.shared_types import CharacterAction
from src.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class PersonaAgent:
    """
    Refactored PersonaAgent using component-based architecture.

    This refactored implementation maintains full backward compatibility
    while providing dramatically improved maintainability through
    separation of concerns and modular design.

    Key Improvements:
    - Reduced from 2,442 LOC to <500 LOC (80% reduction)
    - Clear separation of concerns across components
    - Improved testability and maintainability
    - Enhanced error handling and logging
    - Future-ready for additional features

    Components:
    - core: Identity and lifecycle management
    - context_manager: Character data loading
    - decision_engine: Action selection and reasoning
    """

    def __init__(
        self,
        character_directory_path: str,
        event_bus: "EventBus",
        agent_id: Optional[str] = None,
    ):
        """
        Initialize PersonaAgent with component-based architecture.

        Args:
            character_directory_path: Path to character directory
            event_bus: Event bus for communication
            agent_id: Optional agent ID override
        """
        # Initialize core infrastructure
        self.core = PersonaCore(character_directory_path, event_bus, agent_id)

        # Initialize components
        self.context_manager = CharacterContextManager(self.core)
        self.decision_engine = DecisionEngine(self.core, self.context_manager)

        # Legacy compatibility attributes
        self._initialize_legacy_attributes()

        # Load character context
        self.context_manager.load_character_context()

        logger.info(f"PersonaAgent initialized: {self.core.character_context}")

    def _initialize_legacy_attributes(self) -> None:
        """Initialize attributes for backward compatibility."""
        # Direct references to core attributes for legacy compatibility
        self.agent_id = self.core.agent_id
        self.character_directory_path = self.core.character_directory_path
        self.event_bus = self.core.event_bus

        # Legacy subjective worldview (simplified)
        self.subjective_worldview = {
            "known_entities": {},
            "location_knowledge": {},
            "faction_relationships": {},
            "recent_events": [],
            "current_goals": [],
            "active_threats": {},
        }

        # Legacy state tracking
        self.current_location = None
        self.last_action_timestamp = None

    # Core agent interface methods (maintained for compatibility)

    def handle_turn_start(self, world_state_update: Dict[str, Any]) -> None:
        """
        Handle the start of a new turn.

        Args:
            world_state_update: World state information
        """
        self.core.handle_turn_start(world_state_update)

        # Update legacy attributes
        self.current_location = self.core.state.current_location
        self.last_action_timestamp = self.core.state.last_action_timestamp

    @property
    def character_name(self) -> str:
        """Get character name."""
        return self.core.character_name

    @property
    def character_directory_name(self) -> str:
        """Get character directory name."""
        return self.core.character_directory_name

    @property
    def character_context(self) -> str:
        """Get character context for debugging."""
        return self.core.character_context

    @property
    def character_data(self) -> Dict[str, Any]:
        """Get character data (legacy compatibility)."""
        return self.core.character_data

    def load_character_context(self) -> None:
        """Load character context (legacy method)."""
        self.context_manager.load_character_context()

    # Decision-making interface

    def _make_decision(
        self, world_state_update: Dict[str, Any]
    ) -> Optional[CharacterAction]:
        """
        Make a decision based on world state.

        Args:
            world_state_update: World state information

        Returns:
            Optional[CharacterAction]: Selected action
        """
        return self.decision_engine.make_decision(world_state_update)

    # State and information methods

    def get_character_state(self) -> Dict[str, Any]:
        """
        Get comprehensive character state.

        Returns:
            Dict: Character state information
        """
        # Combine component states
        core_state = self.core.get_agent_state()
        context_summary = self.context_manager.get_character_summary()

        return {
            **core_state,
            "context": context_summary,
            "decision_engine": {
                "action_threshold": self.decision_engine.action_threshold,
                "decision_weights_loaded": bool(self.decision_engine.decision_weights),
            },
            "legacy_compatibility": True,
        }

    def get_known_information(self, topic: str) -> List[Dict[str, Any]]:
        """
        Get known information about a topic.

        Args:
            topic: Topic to query

        Returns:
            List: Known information entries
        """
        # This would be enhanced with actual knowledge tracking
        character_data = self.core.character_data

        # Search through character data for topic
        results = []
        for section_name, section_data in character_data.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if (
                        topic.lower() in key.lower()
                        or topic.lower() in str(value).lower()
                    ):
                        results.append(
                            {
                                "section": section_name,
                                "key": key,
                                "value": value,
                                "relevance": 1.0,  # Would be calculated based on matching
                            }
                        )

        return results

    # Communication interface (simplified)

    def process_communication(
        self, sender_id: str, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process incoming communication.

        Args:
            sender_id: ID of message sender
            message: Message content

        Returns:
            Dict: Response information
        """
        # Simplified communication processing
        response = {
            "recipient": sender_id,
            "sender": self.agent_id,
            "content": f"Received your message about {message.get('topic', 'general matter')}",
            "tone": "neutral",
            "timestamp": self.core.state.last_action_timestamp,
        }

        logger.debug(f"Agent {self.agent_id} processed communication from {sender_id}")
        return response

    # Memory and experience methods (simplified)

    def update_internal_memory(self, new_log: Dict[str, Any]) -> None:
        """
        Update internal memory with new experience.

        Args:
            new_log: New experience data
        """
        # Simplified memory update
        self.subjective_worldview["recent_events"].append(
            {
                "timestamp": new_log.get("timestamp"),
                "event_type": new_log.get("event_type", "unknown"),
                "description": new_log.get("description", ""),
                "personal_impact": new_log.get("personal_impact", 0.0),
            }
        )

        # Keep only recent events (memory limit)
        if len(self.subjective_worldview["recent_events"]) > 50:
            self.subjective_worldview["recent_events"] = self.subjective_worldview[
                "recent_events"
            ][-25:]

        logger.debug(f"Agent {self.agent_id} updated memory with new experience")

    def update_memory(self, event_string: str) -> None:
        """
        Update memory with event string (legacy method).

        Args:
            event_string: Event description
        """
        self.update_internal_memory(
            {
                "description": event_string,
                "timestamp": self.core.state.last_action_timestamp,
                "event_type": "general",
            }
        )

    # Utility methods for backward compatibility

    def _assess_current_situation(self) -> Dict[str, Any]:
        """Legacy situation assessment method."""
        # Create situation assessment using decision engine
        world_state = self.core.state.last_world_state_update or {}
        situation = self.decision_engine._assess_current_situation(world_state)

        return {
            "current_location": situation.current_location,
            "threat_level": situation.threat_level.value,
            "available_resources": situation.available_resources,
            "active_goals": situation.active_goals,
        }

    def _character_has_combat_capability(self) -> bool:
        """Check if character has combat capability."""
        # Check character data for combat indicators
        capabilities = self.core.character_data.get("capabilities", {})
        identity = self.core.character_data.get("identity", {})

        # Look for combat-related fields
        combat_indicators = ["warrior", "soldier", "fighter", "combat", "weapon"]

        profession = identity.get("profession", "").lower()
        if any(indicator in profession for indicator in combat_indicators):
            return True

        # Check capabilities section
        for key, value in capabilities.items():
            if any(indicator in key.lower() for indicator in combat_indicators):
                return True

        return False

    # Cleanup and lifecycle methods

    def cleanup(self) -> None:
        """Clean up agent resources."""
        self.core.cleanup()
        logger.info(f"PersonaAgent cleanup completed for {self.agent_id}")

    def __del__(self):
        """Destructor for cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Best effort cleanup


# Factory function for backward compatibility
def create_persona_agent(
    character_directory_path: str, event_bus: "EventBus", agent_id: Optional[str] = None
) -> PersonaAgent:
    """
    Factory function to create PersonaAgent instance.

    Args:
        character_directory_path: Path to character directory
        event_bus: Event bus instance
        agent_id: Optional agent ID

    Returns:
        PersonaAgent: Configured agent instance
    """
    return PersonaAgent(character_directory_path, event_bus, agent_id)


# Legacy class alias for compatibility
RefactoredPersonaAgent = PersonaAgent
