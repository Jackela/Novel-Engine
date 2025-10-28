#!/usr/bin/env python3
"""
PersonaAgent Integrated Implementation
======================================

Maintains backward compatibility by integrating the extracted modular components
into a unified PersonaAgent interface. This ensures existing imports continue
to work while providing the benefits of modular architecture.

The integrated PersonaAgent coordinates:
- PersonaAgentCore: Core initialization and basic interfaces
- DecisionEngine: Decision-making and action selection
- CharacterInterpreter: Character data loading and interpretation
- MemoryInterface: Memory management and experience processing
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import event bus for communication
from src.event_bus import EventBus

# Import shared types
try:
    from src.core.types.shared_types import ActionPriority, CharacterAction
except ImportError:
    CharacterAction = dict

    class ActionPriority:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"


from src.character_interpreter import CharacterInterpreter
from src.decision_engine import DecisionEngine
from src.memory_interface import MemoryInterface

# Import extracted components
from src.context_integrator import ContextIntegrator
from src.persona_agent_core import PersonaAgentCore

# Configure logging
logger = logging.getLogger(__name__)

try:
    from contexts.character.application.services.context_loader import (
        ContextLoaderService,
    )

    from src.enhanced_decision_engine import EnhancedDecisionEngine

    CONTEXT_LOADER_AVAILABLE = True
except ImportError:
    logger.warning(
        "ContextLoaderService not available - context loading will be disabled"
    )
    CONTEXT_LOADER_AVAILABLE = False


class PersonaAgent:
    """
    Integrated PersonaAgent maintaining backward compatibility with modular architecture.

    This class provides the same public interface as the original PersonaAgent
    while internally coordinating modular components for improved maintainability.

    All existing functionality is preserved while gaining benefits of:
    - Modular component architecture
    - Clear separation of concerns
    - Enhanced testability
    - Improved maintainability
    """

    def __init__(
        self,
        character_directory_path: str,
        event_bus: EventBus,
        agent_id: Optional[str] = None,
    ):
        """
        Initialize the PersonaAgent with modular component coordination.

        Args:
            character_directory_path: Path to directory containing character files
            event_bus: EventBus instance for decoupled communication
            agent_id: Optional unique identifier for this agent
        """
        logger.info(
            f"Initializing integrated PersonaAgent with modular components: {character_directory_path}"
        )

        # Initialize core component first (skip auto-subscription, we'll handle it after integration)
        self.core = PersonaAgentCore(
            character_directory_path, event_bus, agent_id, auto_subscribe=False
        )

        # Initialize character interpreter and load character data
        self.character_interpreter = CharacterInterpreter(character_directory_path)
        self._load_character_data()

        # Initialize context loading components (new)
        self.context_integrator = ContextIntegrator()
        self.context_loader = None
        if CONTEXT_LOADER_AVAILABLE:
            try:
                # Determine base characters path from character directory
                base_characters_path = os.path.dirname(character_directory_path)
                self.context_loader = ContextLoaderService(
                    base_characters_path=base_characters_path
                )
                # Attempt initial context loading
                asyncio.create_task(self._load_enhanced_context())
                logger.info(f"Context loading initialized for {self.core.agent_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize context loading: {e}")
                self.context_loader = None

        # Initialize decision engine with loaded character data (enhanced if context available)
        if CONTEXT_LOADER_AVAILABLE and self.context_loader:
            self.decision_engine = EnhancedDecisionEngine(self.core)
            logger.info(f"Enhanced DecisionEngine initialized for {self.core.agent_id}")
        else:
            self.decision_engine = DecisionEngine(self.core)
            logger.info(f"Standard DecisionEngine initialized for {self.core.agent_id}")

        # Initialize memory interface
        self.memory_interface = MemoryInterface(self.core, character_directory_path)

        # Set up component coordination
        self._setup_component_coordination()

        # Override core's basic action creation with decision engine
        self._integrate_decision_engine()

        logger.info(
            f"PersonaAgent integrated architecture initialized for '{self.character_name}'"
        )

    def _load_character_data(self) -> None:
        """Load character data through character interpreter."""
        try:
            character_data = self.character_interpreter.load_character_context()

            # Integrate loaded data into core component
            self.core.character_data = character_data

            # Extract and apply character-specific settings
            self._apply_character_settings(character_data)

            logger.info(
                f"Character data loaded for {character_data.get('name', 'Unknown')}"
            )

        except Exception as e:
            logger.error(f"Error loading character data: {e}")
            # Continue with default settings

    def _apply_character_settings(self, character_data: Dict[str, Any]) -> None:
        """Apply character-specific settings from loaded data."""
        try:
            # Apply decision weights if available
            decision_weights = character_data.get("decision_weights", {})
            if decision_weights:
                self.core.decision_weights.update(decision_weights)

            # Apply personality traits if available
            personality_scores = character_data.get("personality_scores", {})
            if personality_scores:
                self.core.personality_traits.update(personality_scores)

            # Apply relationships if available
            relationship_scores = character_data.get("relationship_scores", {})
            if relationship_scores:
                self.core.relationships.update(relationship_scores)

            # Apply behavioral modifiers
            if "personality_scores" in character_data:
                for trait, value in personality_scores.items():
                    if trait in ["caution", "aggression", "cooperation"]:
                        self.core.behavioral_modifiers[trait] = value

        except Exception as e:
            logger.error(f"Error applying character settings: {e}")

    def _setup_component_coordination(self) -> None:
        """Set up coordination between components."""
        try:
            # Ensure all components have access to the same core data
            self.decision_engine.agent_core = self.core
            self.memory_interface.agent_core = self.core

            logger.debug(f"Component coordination established for {self.core.agent_id}")

        except Exception as e:
            logger.error(f"Error setting up component coordination: {e}")

    def _integrate_decision_engine(self) -> None:
        """Integrate decision engine with core turn handling."""
        try:
            # Create new integrated turn handler that will be PersonaAgent's method
            def integrated_turn_handler(world_state_update: Dict[str, Any]) -> None:
                try:
                    # Process world state update through core
                    self.core._process_world_state_update(world_state_update)

                    # Use _make_decision for action creation (allows test mocking)
                    action = self._make_decision(world_state_update)

                    # Emit action completion event with self (PersonaAgent) as agent
                    self.core.event_bus.emit(
                        "AGENT_ACTION_COMPLETE", agent=self, action=action
                    )

                except Exception as e:
                    logger.error(
                        f"Error in integrated turn handler for {self.core.agent_id}: {e}"
                    )
                    # Emit safe fallback
                    self.core.event_bus.emit(
                        "AGENT_ACTION_COMPLETE", agent=self, action=None
                    )

            # Set PersonaAgent's turn handler method
            # This ensures the event subscription points to PersonaAgent.handle_turn_start
            self.handle_turn_start = integrated_turn_handler

            # Also update core's handler to point to PersonaAgent's method for consistency
            self.core.handle_turn_start = self.handle_turn_start

            # Now subscribe PersonaAgent.handle_turn_start to TURN_START
            # (PersonaAgentCore was initialized with auto_subscribe=False, so no prior subscription)
            self.core.event_bus.subscribe("TURN_START", self.handle_turn_start)
            logger.info(
                f"PersonaAgent '{self.core.agent_id}' subscribed to TURN_START events"
            )

        except Exception as e:
            logger.error(f"Error integrating decision engine: {e}")

    async def _load_enhanced_context(self) -> bool:
        """Load structured context and integrate with existing character data."""
        if not self.context_loader:
            return False

        try:
            character_id = os.path.basename(self.core.character_directory_path)
            context = await self.context_loader.load_character_context(character_id)

            # Integrate contexts
            self.core.character_data = self.context_integrator.merge_contexts(
                existing_data=self.core.character_data, new_context=context
            )

            logger.info(f"Enhanced context loaded for {context.character_name}")
            return True

        except Exception as e:
            logger.warning(
                f"Enhanced context loading failed, using traditional data: {e}"
            )
            return False

    async def refresh_context(self) -> bool:
        """Refresh context at turn start for dynamic updates."""
        if not self.context_loader:
            return False

        return await self._load_enhanced_context()

    # Public API methods - maintaining backward compatibility

    def handle_turn_start(self, world_state_update: Dict[str, Any]) -> None:
        """
        Handle the TURN_START event by processing world state and making decisions.

        Args:
            world_state_update: Current world state information from DirectorAgent
        """
        self.core.handle_turn_start(world_state_update)

    def load_character_context(self) -> None:
        """Load and parse character files from the directory."""
        # This is handled during initialization, but maintain method for compatibility
        try:
            self._load_character_data()
            logger.info(f"Character context reloaded for {self.character_name}")
        except Exception as e:
            logger.error(f"Error reloading character context: {e}")

    def update_internal_memory(self, new_log: Dict[str, Any]) -> None:
        """
        Update the character's internal memory system with new experiences.

        Args:
            new_log: Dictionary containing new experience/event information
        """
        self.memory_interface.update_internal_memory(new_log)

    def update_memory(self, event_string: str) -> None:
        """
        Append a new event string to the memory.log file.

        Args:
            event_string: String describing the event to be logged
        """
        self.memory_interface.update_memory(event_string)

    # Property accessors for backward compatibility

    @property
    def agent_id(self) -> str:
        """Get the agent's unique identifier."""
        return self.core.agent_id

    @property
    def character_name(self) -> str:
        """Get the character's name from loaded character data."""
        return self.core.character_name

    @property
    def character_directory_path(self) -> str:
        """Get the character directory path."""
        return self.core.character_directory_path

    @property
    def character_directory_name(self) -> str:
        """Get the character's directory name."""
        return self.core.character_directory_name

    @property
    def character_context(self) -> str:
        """Get the character's loaded context (markdown content)."""
        return self.core.character_context

    @property
    def faction(self) -> str:
        """Get the character's faction affiliation."""
        return self.core.faction

    @property
    def character_data(self) -> Dict[str, Any]:
        """Get character data dictionary."""
        return self.core.character_data

    @property
    def subjective_worldview(self) -> Dict[str, Any]:
        """Get character's subjective worldview."""
        return self.core.subjective_worldview

    @property
    def current_location(self) -> Optional[str]:
        """Get character's current location."""
        return self.core.current_location

    @current_location.setter
    def current_location(self, location: str) -> None:
        """Set character's current location."""
        self.core.current_location = location

    @property
    def current_status(self) -> str:
        """Get character's current status."""
        return self.core.current_status

    @current_status.setter
    def current_status(self, status: str) -> None:
        """Set character's current status."""
        self.core.current_status = status

    @property
    def morale_level(self) -> float:
        """Get character's morale level."""
        return self.core.morale_level

    @morale_level.setter
    def morale_level(self, morale: float) -> None:
        """Set character's morale level."""
        self.core.morale_level = max(-1.0, min(1.0, morale))

    @property
    def decision_weights(self) -> Dict[str, float]:
        """Get character's decision-making weights."""
        return self.core.decision_weights

    @decision_weights.setter
    def decision_weights(self, weights: Dict[str, float]) -> None:
        """Set character's decision-making weights."""
        self.core.decision_weights = weights

    @property
    def short_term_memory(self) -> List[Dict[str, Any]]:
        """Get character's short-term memory."""
        return self.core.short_term_memory

    @property
    def long_term_memory(self) -> List[Dict[str, Any]]:
        """Get character's long-term memory."""
        return self.core.long_term_memory

    @property
    def personality_traits(self) -> Dict[str, float]:
        """Get character's personality traits."""
        return self.core.personality_traits

    @property
    def behavioral_modifiers(self) -> Dict[str, float]:
        """Get character's behavioral modifiers."""
        return self.core.behavioral_modifiers

    @property
    def relationships(self) -> Dict[str, float]:
        """Get character's relationships."""
        return self.core.relationships

    @property
    def communication_style(self) -> str:
        """Get character's communication style."""
        return self.core.communication_style

    @communication_style.setter
    def communication_style(self, style: str) -> None:
        """Set character's communication style."""
        self.core.communication_style = style

    @property
    def character(self):
        """Get character object for backward compatibility with api_server.py expectations."""

        # Create a character object that provides the expected interface
        class CharacterCompatibilityWrapper:
            def __init__(self, persona_agent):
                self._agent = persona_agent

            @property
            def name(self) -> str:
                return self._agent.character_name

            @property
            def background_summary(self) -> str:
                return self._agent.character_data.get(
                    "background_summary", "No background available"
                )

            @property
            def personality_traits(self) -> str:
                traits = self._agent.personality_traits
                if isinstance(traits, dict):
                    return ", ".join([f"{k}: {v}" for k, v in traits.items()])
                return str(traits) if traits else "No personality traits available"

            @property
            def current_status(self) -> str:
                return self._agent.current_status

            @property
            def narrative_context(self) -> str:
                return self._agent.character_context or "No narrative context"

            @property
            def skills(self) -> Dict[str, float]:
                return self._agent.character_data.get("skills", {})

            @property
            def relationships(self) -> Dict[str, float]:
                return self._agent.relationships

            @property
            def current_location(self) -> str:
                return self._agent.current_location or "Unknown"

            @property
            def inventory(self) -> List[str]:
                return self._agent.character_data.get("inventory", [])

            @property
            def metadata(self) -> Dict[str, Any]:
                return self._agent.character_data.get("metadata", {})

        return CharacterCompatibilityWrapper(self)

    @property
    def event_bus(self) -> EventBus:
        """Get the event bus instance."""
        return self.core.event_bus

    # Additional utility methods

    def get_agent_info(self) -> Dict[str, Any]:
        """Get comprehensive agent information."""
        base_info = self.core.get_agent_info()

        # Add component-specific information
        base_info.update(
            {
                "decision_metrics": self.decision_engine.get_decision_metrics(),
                "memory_metrics": self.memory_interface.get_memory_metrics(),
                "character_summary": self.character_interpreter.get_character_summary(),
                "component_architecture": "integrated_modular",
            }
        )

        return base_info

    def get_recent_memories(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent memories from short-term memory."""
        return self.memory_interface.get_recent_memories(count)

    def get_significant_memories(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most significant memories from long-term memory."""
        return self.memory_interface.get_significant_memories(count)

    def search_memories(
        self, search_term: str, memory_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """Search memories for specific content."""
        return self.memory_interface.search_memories(search_term, memory_type)

    def validate_character_data(self) -> tuple[bool, List[str]]:
        """Validate the integrity and completeness of character data."""
        return self.character_interpreter.validate_character_data()

    def get_component_status(self) -> Dict[str, Any]:
        """
        Get status information for all components.

        Returns:
            Dictionary containing component status information
        """
        try:
            return {
                "core_component": {
                    "agent_id": self.core.agent_id,
                    "is_active": self.core.is_active(),
                    "core_metrics": self.core.get_core_metrics(),
                },
                "decision_engine": {
                    "llm_available": self.decision_engine.llm_available,
                    "decision_metrics": self.decision_engine.get_decision_metrics(),
                },
                "character_interpreter": {
                    "character_summary": self.character_interpreter.get_character_summary()
                },
                "memory_interface": {
                    "memory_metrics": self.memory_interface.get_memory_metrics()
                },
                "integration_status": "healthy",
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting component status: {e}")
            return {"error": str(e)}

    def consolidate_memories(self) -> int:
        """Consolidate memories by promoting important short-term memories to long-term."""
        return self.memory_interface.consolidate_memories()

    def is_active(self) -> bool:
        """Check if the agent is currently active and able to take actions."""
        return self.core.is_active()

    def add_relationship(self, entity_id: str, relationship_strength: float) -> None:
        """Add or update a relationship with another entity."""
        self.core.add_relationship(entity_id, relationship_strength)

    def get_relationship_strength(self, entity_id: str) -> float:
        """Get relationship strength with a specific entity."""
        return self.core.get_relationship_strength(entity_id)

    def update_character_state(
        self,
        status: Optional[str] = None,
        location: Optional[str] = None,
        morale: Optional[float] = None,
    ) -> None:
        """Update character state information."""
        self.core.update_character_state(status, location, morale)

    # Private methods for internal operations

    def _derive_agent_id_from_path(self, path: str) -> str:
        """Derive a unique agent ID from the character directory path."""
        return self.core._derive_agent_id_from_path(path)

    def _make_decision(
        self, world_state_update: Dict[str, Any]
    ) -> Optional[CharacterAction]:
        """Core decision-making logic (delegated to decision engine)."""
        return self.decision_engine.make_decision(world_state_update)

    def _assess_current_situation(self) -> Dict[str, Any]:
        """Assess the current situation (delegated to decision engine)."""
        return self.decision_engine._assess_current_situation()

    def _generate_personal_interpretation(self, experience: Dict[str, Any]) -> str:
        """Generate personal interpretation of an experience."""
        return self.memory_interface._generate_personal_interpretation(experience)

    def get_context_decision_summary(
        self, action: Dict[str, Any], situation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get summary of context-driven decision factors."""
        if hasattr(self.decision_engine, "get_context_decision_summary"):
            return self.decision_engine.get_context_decision_summary(action, situation)
        else:
            return {"context_available": False, "decision_engine": "standard"}

    def get_context_integration_status(self) -> Dict[str, Any]:
        """Get status of context integration for this agent."""
        try:
            # Determine decision engine type
            decision_engine_type = "standard"
            if CONTEXT_LOADER_AVAILABLE:
                try:
                    from src.enhanced_decision_engine import EnhancedDecisionEngine

                    if isinstance(self.decision_engine, EnhancedDecisionEngine):
                        decision_engine_type = "enhanced"
                except ImportError:
                    pass

            status = {
                "context_loader_available": CONTEXT_LOADER_AVAILABLE,
                "context_loader_initialized": self.context_loader is not None,
                "decision_engine_type": decision_engine_type,
                "context_integrator_initialized": hasattr(self, "context_integrator"),
            }

            if (
                hasattr(self.core, "character_data")
                and "enhanced_context" in self.core.character_data
            ):
                context_data = self.core.character_data
                status.update(
                    {
                        "context_loaded": True,
                        "context_load_success": context_data.get(
                            "context_load_success", False
                        ),
                        "context_timestamp": context_data.get("context_timestamp"),
                        "context_warnings_count": len(
                            context_data.get("context_warnings", [])
                        ),
                        "integration_summary": self.context_integrator.get_integration_summary(
                            context_data
                        ),
                    }
                )
            else:
                status["context_loaded"] = False

            return status

        except Exception as e:
            logger.error(f"Error getting context integration status: {e}")
            return {"error": str(e)}

    # Stub methods for backward compatibility with tests
    # These methods existed in the original PersonaAgent but were moved to components
    # Tests may try to patch these methods, so we provide stubs

    def _extract_core_identity(self, character_sheet_content: str) -> Dict[str, Any]:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        return (
            self.character_interpreter._extract_core_identity(character_sheet_content)
            if hasattr(self.character_interpreter, "_extract_core_identity")
            else {}
        )

    def _extract_personality_traits(
        self, character_sheet_content: str
    ) -> Dict[str, float]:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        return (
            self.character_interpreter._extract_personality_traits(
                character_sheet_content
            )
            if hasattr(self.character_interpreter, "_extract_personality_traits")
            else {}
        )

    def _extract_decision_weights(
        self, character_sheet_content: str
    ) -> Dict[str, float]:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        return (
            self.character_interpreter._extract_decision_weights(
                character_sheet_content
            )
            if hasattr(self.character_interpreter, "_extract_decision_weights")
            else {}
        )

    def _extract_relationships(self, character_sheet_content: str) -> Dict[str, float]:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        return (
            self.character_interpreter._extract_relationships(character_sheet_content)
            if hasattr(self.character_interpreter, "_extract_relationships")
            else {}
        )

    def _extract_knowledge_domains(self, character_sheet_content: str) -> List[str]:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        return (
            self.character_interpreter._extract_knowledge_domains(
                character_sheet_content
            )
            if hasattr(self.character_interpreter, "_extract_knowledge_domains")
            else []
        )

    def _initialize_subjective_worldview(self) -> Dict[str, Any]:
        """Stub for backward compatibility - actual logic in PersonaAgentCore."""
        return (
            self.core._initialize_subjective_worldview()
            if hasattr(self.core, "_initialize_subjective_worldview")
            else {}
        )

    def _derive_agent_id_from_path(self, path: str) -> str:
        """Stub for backward compatibility - actual logic in PersonaAgentCore."""
        return self.core._derive_agent_id_from_path(path)

    def _estimate_trait_strength(self, description: str) -> float:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        # Extract intensity modifier from description
        intensity_map = {
            "extremely": 0.9,
            "very": 0.8,
            "highly": 0.8,
            "moderately": 0.6,
            "somewhat": 0.5,
            "slightly": 0.3,
            "barely": 0.2,
        }

        description_lower = description.lower()
        for modifier, strength in intensity_map.items():
            if modifier in description_lower:
                return strength

        # Default to moderate strength
        return 0.6

    def _make_decision(
        self, world_state_update: Dict[str, Any]
    ) -> Optional[CharacterAction]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        return self.decision_engine.make_decision(world_state_update)

    # Additional decision-making stub methods
    def _llm_enhanced_decision_making(
        self, world_state_update: Dict[str, Any]
    ) -> Optional[CharacterAction]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        return (
            self.decision_engine._llm_enhanced_decision_making(world_state_update)
            if hasattr(self.decision_engine, "_llm_enhanced_decision_making")
            else None
        )

    def _process_world_state_update(self, world_state_update: Dict[str, Any]) -> None:
        """Stub for backward compatibility - actual logic in PersonaAgentCore."""
        self.core._process_world_state_update(world_state_update)

    def _identify_available_actions(
        self, world_state_update: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        return (
            self.decision_engine._identify_available_actions(world_state_update)
            if hasattr(self.decision_engine, "_identify_available_actions")
            else []
        )

    def _select_best_action(
        self, available_actions: List[Dict[str, Any]]
    ) -> Optional[CharacterAction]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        return (
            self.decision_engine._select_best_action(available_actions)
            if hasattr(self.decision_engine, "_select_best_action")
            else None
        )

    def _assess_overall_threat_level(self, world_state_update: Dict[str, Any]) -> str:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_assess_overall_threat_level"):
            return self.decision_engine._assess_overall_threat_level(world_state_update)
        return "moderate"

    def _evaluate_action_option(
        self, action_option: Dict[str, Any], situation: Dict[str, Any]
    ) -> float:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_evaluate_action_option"):
            return self.decision_engine._evaluate_action_option(
                action_option, situation
            )
        return 0.5

    def _parse_llm_response(
        self, response: str, available_actions: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[CharacterAction]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_parse_llm_response"):
            if available_actions is not None:
                return self.decision_engine._parse_llm_response(
                    response, available_actions
                )
            return self.decision_engine._parse_llm_response(response)
        return None

    def _call_llm(self, prompt: str) -> str:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_call_llm"):
            try:
                return self.decision_engine._call_llm(prompt)
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")
                return ""
        return ""

    def _read_cached_file(self, file_path: str) -> Optional[str]:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        if hasattr(self.character_interpreter, "_read_cached_file"):
            return self.character_interpreter._read_cached_file(file_path)
        return None

    def _parse_character_sheet_content(self, content: str) -> Dict[str, Any]:
        """Stub for backward compatibility - actual logic in CharacterInterpreter."""
        if hasattr(self.character_interpreter, "_parse_character_sheet_content"):
            return self.character_interpreter._parse_character_sheet_content(content)
        return {}

    def _assess_available_resources(
        self, world_state_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_assess_available_resources"):
            return self.decision_engine._assess_available_resources(world_state_update)
        return {}

    def _assess_threat_from_description(self, description: str):
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_assess_threat_from_description"):
            return self.decision_engine._assess_threat_from_description(description)
        # Simple keyword-based threat assessment - return ThreatLevel enum
        from src.agents.persona_agent.protocols import ThreatLevel

        description_lower = description.lower()
        if any(word in description_lower for word in ["critical", "extreme", "dire"]):
            return ThreatLevel.HIGH
        elif any(
            word in description_lower
            for word in ["enemy", "approaching", "moderate", "battle"]
        ):
            return ThreatLevel.MODERATE
        elif any(word in description_lower for word in ["minor", "skirmish", "low"]):
            return ThreatLevel.LOW
        else:
            return ThreatLevel.NEGLIGIBLE

    def _assess_social_obligations(
        self, world_state_update: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_assess_social_obligations"):
            return self.decision_engine._assess_social_obligations(world_state_update)
        return []

    def _assess_mission_status(
        self, world_state_update: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_assess_mission_status"):
            return self.decision_engine._assess_mission_status(world_state_update)
        return {"status": "active"}

    def _assess_environmental_factors(
        self, world_state_update: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_assess_environmental_factors"):
            return self.decision_engine._assess_environmental_factors(
                world_state_update
            )
        return {}

    def _interpret_event_description(self, event_data: Dict[str, Any]) -> str:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_interpret_event_description"):
            return self.decision_engine._interpret_event_description(event_data)
        # Simple fallback interpretation
        return event_data.get("description", "Unknown event")

    def _assess_current_situation(
        self, world_state_update: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Stub for backward compatibility - actual logic in DecisionEngine."""
        if hasattr(self.decision_engine, "_assess_current_situation"):
            # Get the real assessment from DecisionEngine (no args)
            result = self.decision_engine._assess_current_situation()
            # If result has 'resource_status', map it to 'available_resources' for backward compatibility
            if "resource_status" in result and "available_resources" not in result:
                result["available_resources"] = result.get("resource_status", {})
            return result
        # Simple fallback
        return {
            "threat_level": "low",
            "available_resources": {},
            "social_obligations": [],
            "mission_status": {"status": "active"},
            "environmental_factors": {},
        }
