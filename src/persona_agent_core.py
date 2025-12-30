#!/usr/bin/env python3
"""
PersonaAgent Core Implementation
===============================

Core foundation class for PersonaAgent containing:
- Core initialization and setup
- Character properties and identity management
- Basic agent interface implementation
- Agent registration and event handling

This module provides the fundamental infrastructure for character AI agents
while maintaining clean separation from decision-making and memory systems.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import event bus for communication
try:
    from src.event_bus import EventBus
except ImportError:

    class EventBus:
        def __init__(self):
            pass

        def subscribe(self, event, callback):
            pass

        def emit(self, event, **kwargs):
            pass


# Configure logging
logger = logging.getLogger(__name__)


class PersonaAgentCore:
    """
    Core foundation class for PersonaAgent system.

    Provides:
    - Core initialization and character data management
    - Character identity and property access
    - Basic agent interface implementation
    - Event system integration and turn handling
    - Agent registration and lifecycle management

    This core class establishes the foundation that decision-making,
    memory, and character interpretation components build upon.
    """

    def __init__(
        self,
        character_directory_path: str,
        event_bus: EventBus,
        agent_id: Optional[str] = None,
        auto_subscribe_turn_start: bool = True,
    ):
        """
        Initialize the PersonaAgent core infrastructure.

        Sets up basic agent identity, character data structures, and event system
        integration while preparing for component system integration.

        Args:
            character_directory_path: Path to directory containing character files
            event_bus: EventBus instance for decoupled communication
            agent_id: Optional unique identifier for this agent
        """
        logger.info("Initializing PersonaAgent core infrastructure")

        # Core agent identification
        self.character_directory_path = character_directory_path
        self.agent_id = agent_id or self._derive_agent_id_from_path(
            character_directory_path
        )
        self.event_bus = event_bus
        self._auto_subscribe_turn_start = auto_subscribe_turn_start

        # Core character data container
        self.character_data: Dict[str, Any] = {}
        """Container for loaded character data from files."""

        # Character state tracking
        self._initialize_character_state()

        # Subjective worldview foundation
        self._initialize_subjective_worldview()

        # Decision-making infrastructure
        self._initialize_decision_infrastructure()

        # Memory system foundation
        self._initialize_memory_foundation()

        # Behavioral and social systems
        self._initialize_behavioral_systems()

        # Communication systems
        self._initialize_communication_systems()

        # Event system integration
        self._setup_event_handling()

        logger.info("PersonaAgent core initialized successfully")

    def _derive_agent_id_from_path(self, path: str) -> str:
        """
        Derive a unique agent ID from the character directory path.

        Args:
            path: Character directory path

        Returns:
            str: Derived unique agent identifier
        """
        try:
            # Use the directory name as base, with timestamp for uniqueness
            base_name = os.path.basename(os.path.normpath(path))
            timestamp_suffix = datetime.now().strftime("%H%M%S")
            return f"{base_name}_{timestamp_suffix}"
        except Exception:
            logger.warning("Error deriving agent ID from path", exc_info=True)
            return f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _initialize_character_state(self) -> None:
        """Initialize basic character state tracking."""
        self.current_location: Optional[str] = None
        """Current location of the character."""

        self.current_status: str = "active"
        """Character status: active, injured, unconscious, dead."""

        self.morale_level: float = 1.0
        """Character morale level from -1.0 (broken) to 1.0 (fanatic)."""

    def _initialize_subjective_worldview(self) -> None:
        """Initialize the character's subjective worldview system."""
        self.subjective_worldview: Dict[str, Any] = {
            "known_entities": {},  # Other characters/factions known to character
            "location_knowledge": {},  # Places the character knows about
            "faction_relationships": {},  # Personal view of faction standings
            "recent_events": [],  # Character's memory of recent events
            "current_goals": [],  # Character's current objectives
            "active_threats": {},  # Perceived threats and their assessment
        }
        """Character's subjective understanding of the world."""

    def _initialize_decision_infrastructure(self) -> None:
        """Initialize decision-making infrastructure."""
        self.decision_weights: Dict[str, float] = {
            "self_preservation": 0.5,
            "faction_loyalty": 0.7,
            "personal_relationships": 0.6,
            "mission_success": 0.8,
            "moral_principles": 0.4,
        }
        """Decision-making weight matrix loaded from character data."""

    def _initialize_memory_foundation(self) -> None:
        """Initialize memory system foundation."""
        self.short_term_memory: List[Dict[str, Any]] = []
        """Recent events memory (last 10-20 events)."""

        self.long_term_memory: List[Dict[str, Any]] = []
        """Important events for character development."""

    def _initialize_behavioral_systems(self) -> None:
        """Initialize behavioral pattern systems."""
        self.personality_traits: Dict[str, float] = {}
        """Character personality trait mappings."""

        self.behavioral_modifiers: Dict[str, float] = {}
        """Situational behavior modification factors."""

    def _initialize_communication_systems(self) -> None:
        """Initialize communication and social systems."""
        self.relationships: Dict[str, float] = {}
        """Relationship strengths with other entities (-1.0 to 1.0)."""

        self.communication_style: str = "direct"
        """Communication style: direct, diplomatic, aggressive, cautious."""

    def _setup_event_handling(self) -> None:
        """Set up event system subscriptions."""
        if not self._auto_subscribe_turn_start:
            return
        try:
            self.event_bus.subscribe("TURN_START", self.handle_turn_start)
            logger.info("PersonaAgent subscribed to TURN_START events")
        except Exception:
            logger.error("Failed to set up event handling", exc_info=True)

    def handle_turn_start(self, world_state_update: Dict[str, Any]) -> None:
        """
        Handle the TURN_START event by processing the world state and initiating decision-making.

        This is the main entry point for agent turn processing. It coordinates with
        the decision-making and memory systems to produce appropriate actions.

        Args:
            world_state_update: Current world state information from the DirectorAgent
        """
        try:
            logger.info(f"Agent {self.agent_id} processing TURN_START event")

            # Update internal state with world information
            self._process_world_state_update(world_state_update)

            # This will be extended by decision-making components
            # For now, emit a simple response
            action = self._create_basic_action(world_state_update)

            # Emit action completion event
            self.event_bus.emit("AGENT_ACTION_COMPLETE", agent=self, action=action)

        except Exception as e:
            logger.error(
                f"Error handling TURN_START for agent {self.agent_id}: {str(e)}"
            )
            # Emit a safe fallback action
            self.event_bus.emit("AGENT_ACTION_COMPLETE", agent=self, action=None)

    def _process_world_state_update(self, world_state_update: Dict[str, Any]) -> None:
        """
        Process incoming world state information and update internal knowledge.

        Args:
            world_state_update: World state information to process
        """
        try:
            # Update recent events in subjective worldview
            if isinstance(world_state_update, dict):
                event_summary = {
                    "turn_number": world_state_update.get("current_turn", 0),
                    "timestamp": world_state_update.get("simulation_time", ""),
                    "world_state": world_state_update.get("world_state", {}),
                    "processed_at": datetime.now().isoformat(),
                }

                self.subjective_worldview["recent_events"].append(event_summary)

                # Keep only recent events (last 10)
                if len(self.subjective_worldview["recent_events"]) > 10:
                    self.subjective_worldview[
                        "recent_events"
                    ] = self.subjective_worldview["recent_events"][-10:]

                logger.debug(
                    f"Agent {self.agent_id} processed world state update for turn {event_summary['turn_number']}"
                )

        except Exception as e:
            logger.error(
                f"Error processing world state update for agent {self.agent_id}: {str(e)}"
            )

    def _create_basic_action(
        self, world_state_update: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a basic action response.

        This is a fallback implementation that will be enhanced by decision-making components.

        Args:
            world_state_update: Current world state information

        Returns:
            Basic action dictionary or None for waiting
        """
        try:
            # Create a simple observation action as fallback
            basic_action = {
                "action_id": f"{self.agent_id}_action_{datetime.now().strftime('%H%M%S')}",
                "action_type": "observe",
                "agent_id": self.agent_id,
                "reasoning": f"Character {self.character_name} is observing the situation and assessing options.",
                "timestamp": datetime.now().isoformat(),
            }

            return basic_action

        except Exception as e:
            logger.error(
                f"Error creating basic action for agent {self.agent_id}: {str(e)}"
            )
            return None

    # Character property accessors
    @property
    def character_name(self) -> str:
        """
        Get the character's name from loaded character data.

        Returns:
            str: Character's name or 'Unknown' if not available
        """
        return self.character_data.get("name", f"Agent_{self.agent_id}")

    @property
    def character_directory_name(self) -> str:
        """
        Get the character's directory name for file organization.

        Returns:
            str: Directory name of the character
        """
        return os.path.basename(os.path.normpath(self.character_directory_path))

    @property
    def character_context(self) -> str:
        """
        Get the character's loaded context (markdown content).

        Returns:
            str: Character's context from loaded files
        """
        try:
            hybrid_context = self.character_data.get("hybrid_context", {})
            return hybrid_context.get("markdown_content", "")
        except Exception as e:
            logger.error(f"Error accessing character context for {self.agent_id}: {e}")
            return ""

    @property
    def faction(self) -> str:
        """
        Get the character's faction affiliation.

        Returns:
            str: Character's faction or 'Unknown' if not available
        """
        return self.character_data.get("faction", "Unknown")

    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get comprehensive agent information for monitoring and debugging.

        Returns:
            Dictionary containing agent state and configuration
        """
        try:
            return {
                "agent_id": self.agent_id,
                "character_name": self.character_name,
                "character_directory": self.character_directory_name,
                "current_location": self.current_location,
                "current_status": self.current_status,
                "morale_level": self.morale_level,
                "faction": self.faction,
                "communication_style": self.communication_style,
                "known_entities_count": len(
                    self.subjective_worldview.get("known_entities", {})
                ),
                "recent_events_count": len(
                    self.subjective_worldview.get("recent_events", [])
                ),
                "relationships_count": len(self.relationships),
                "short_term_memory_count": len(self.short_term_memory),
                "long_term_memory_count": len(self.long_term_memory),
                "initialization_time": getattr(self, "_initialization_time", "unknown"),
            }
        except Exception as e:
            logger.error(f"Error generating agent info for {self.agent_id}: {e}")
            return {"agent_id": self.agent_id, "error": str(e)}

    def update_character_state(
        self,
        status: Optional[str] = None,
        location: Optional[str] = None,
        morale: Optional[float] = None,
    ) -> None:
        """
        Update character state information.

        Args:
            status: New character status
            location: New character location
            morale: New morale level
        """
        try:
            if status is not None:
                self.current_status = status
                logger.info(f"Agent {self.agent_id} status updated to: {status}")

            if location is not None:
                old_location = self.current_location
                self.current_location = location
                logger.info(
                    f"Agent {self.agent_id} moved from {old_location} to {location}"
                )

            if morale is not None:
                # Clamp morale to valid range
                self.morale_level = max(-1.0, min(1.0, morale))
                logger.info(
                    f"Agent {self.agent_id} morale updated to: {self.morale_level}"
                )

        except Exception as e:
            logger.error(f"Error updating character state for {self.agent_id}: {e}")

    def add_relationship(self, entity_id: str, relationship_strength: float) -> None:
        """
        Add or update a relationship with another entity.

        Args:
            entity_id: ID of the entity to establish relationship with
            relationship_strength: Strength of relationship (-1.0 to 1.0)
        """
        try:
            # Clamp relationship strength to valid range
            strength = max(-1.0, min(1.0, relationship_strength))
            self.relationships[entity_id] = strength

            logger.info(
                f"Agent {self.agent_id} relationship with {entity_id} set to {strength}"
            )

        except Exception as e:
            logger.error(f"Error adding relationship for {self.agent_id}: {e}")

    def get_relationship_strength(self, entity_id: str) -> float:
        """
        Get relationship strength with a specific entity.

        Args:
            entity_id: ID of the entity to check relationship with

        Returns:
            float: Relationship strength (-1.0 to 1.0), 0.0 if no relationship exists
        """
        return self.relationships.get(entity_id, 0.0)

    def add_to_subjective_worldview(self, category: str, key: str, value: Any) -> None:
        """
        Add information to the character's subjective worldview.

        Args:
            category: Category of information (known_entities, location_knowledge, etc.)
            key: Specific key for the information
            value: Information value to store
        """
        try:
            if category in self.subjective_worldview:
                if isinstance(self.subjective_worldview[category], dict):
                    self.subjective_worldview[category][key] = value
                elif isinstance(self.subjective_worldview[category], list):
                    self.subjective_worldview[category].append({key: value})

                logger.debug(
                    f"Agent {self.agent_id} updated subjective worldview: {category}[{key}]"
                )
            else:
                logger.warning(
                    f"Unknown worldview category '{category}' for agent {self.agent_id}"
                )

        except Exception as e:
            logger.error(
                f"Error updating subjective worldview for {self.agent_id}: {e}"
            )

    def is_active(self) -> bool:
        """
        Check if the agent is currently active and able to take actions.

        Returns:
            bool: True if agent is active, False otherwise
        """
        return self.current_status == "active"

    def get_core_metrics(self) -> Dict[str, Any]:
        """
        Get core agent metrics for monitoring.

        Returns:
            Dictionary containing core performance and state metrics
        """
        try:
            return {
                "agent_id": self.agent_id,
                "is_active": self.is_active(),
                "morale_level": self.morale_level,
                "current_status": self.current_status,
                "memory_usage": {
                    "short_term": len(self.short_term_memory),
                    "long_term": len(self.long_term_memory),
                },
                "worldview_size": {
                    "known_entities": len(
                        self.subjective_worldview.get("known_entities", {})
                    ),
                    "location_knowledge": len(
                        self.subjective_worldview.get("location_knowledge", {})
                    ),
                    "recent_events": len(
                        self.subjective_worldview.get("recent_events", [])
                    ),
                },
                "relationships_count": len(self.relationships),
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error generating core metrics for {self.agent_id}: {e}")
            return {"agent_id": self.agent_id, "error": str(e)}
