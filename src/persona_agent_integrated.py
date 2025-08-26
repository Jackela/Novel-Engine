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

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import event bus for communication
from src.event_bus import EventBus

# Import shared types
try:
    from src.core.types.shared_types import CharacterAction, ActionPriority
except ImportError:
    CharacterAction = dict
    class ActionPriority:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

# Import extracted components
from src.persona_agent_core import PersonaAgentCore
from src.decision_engine import DecisionEngine
from src.character_interpreter import CharacterInterpreter
from src.memory_interface import MemoryInterface

# Configure logging
logger = logging.getLogger(__name__)


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
    
    def __init__(self, character_directory_path: str, event_bus: EventBus, agent_id: Optional[str] = None):
        """
        Initialize the PersonaAgent with modular component coordination.
        
        Args:
            character_directory_path: Path to directory containing character files
            event_bus: EventBus instance for decoupled communication
            agent_id: Optional unique identifier for this agent
        """
        logger.info(f"Initializing integrated PersonaAgent with modular components: {character_directory_path}")
        
        # Initialize core component first
        self.core = PersonaAgentCore(character_directory_path, event_bus, agent_id)
        
        # Initialize character interpreter and load character data
        self.character_interpreter = CharacterInterpreter(character_directory_path)
        self._load_character_data()
        
        # Initialize decision engine with loaded character data
        self.decision_engine = DecisionEngine(self.core)
        
        # Initialize memory interface
        self.memory_interface = MemoryInterface(self.core, character_directory_path)
        
        # Set up component coordination
        self._setup_component_coordination()
        
        # Override core's basic action creation with decision engine
        self._integrate_decision_engine()
        
        logger.info(f"PersonaAgent integrated architecture initialized for '{self.character_name}'")
    
    def _load_character_data(self) -> None:
        """Load character data through character interpreter."""
        try:
            character_data = self.character_interpreter.load_character_context()
            
            # Integrate loaded data into core component
            self.core.character_data = character_data
            
            # Extract and apply character-specific settings
            self._apply_character_settings(character_data)
            
            logger.info(f"Character data loaded for {character_data.get('name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error loading character data: {e}")
            # Continue with default settings
    
    def _apply_character_settings(self, character_data: Dict[str, Any]) -> None:
        """Apply character-specific settings from loaded data."""
        try:
            # Apply decision weights if available
            decision_weights = character_data.get('decision_weights', {})
            if decision_weights:
                self.core.decision_weights.update(decision_weights)
            
            # Apply personality traits if available
            personality_scores = character_data.get('personality_scores', {})
            if personality_scores:
                self.core.personality_traits.update(personality_scores)
            
            # Apply relationships if available
            relationship_scores = character_data.get('relationship_scores', {})
            if relationship_scores:
                self.core.relationships.update(relationship_scores)
            
            # Apply behavioral modifiers
            if 'personality_scores' in character_data:
                for trait, value in personality_scores.items():
                    if trait in ['caution', 'aggression', 'cooperation']:
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
            # Store original handle_turn_start method
            original_handle_turn_start = self.core.handle_turn_start
            
            # Create new integrated turn handler
            def integrated_turn_handler(world_state_update: Dict[str, Any]) -> None:
                try:
                    # Process world state update through core
                    self.core._process_world_state_update(world_state_update)
                    
                    # Use decision engine for action creation
                    action = self.decision_engine.make_decision(world_state_update)
                    
                    # Emit action completion event
                    self.core.event_bus.emit("AGENT_ACTION_COMPLETE", agent=self, action=action)
                    
                except Exception as e:
                    logger.error(f"Error in integrated turn handler for {self.core.agent_id}: {e}")
                    # Fall back to original behavior
                    original_handle_turn_start(world_state_update)
            
            # Replace core's turn handler with integrated version
            self.core.handle_turn_start = integrated_turn_handler
            
        except Exception as e:
            logger.error(f"Error integrating decision engine: {e}")
    
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
    def event_bus(self) -> EventBus:
        """Get the event bus instance."""
        return self.core.event_bus
    
    # Additional utility methods
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get comprehensive agent information."""
        base_info = self.core.get_agent_info()
        
        # Add component-specific information
        base_info.update({
            'decision_metrics': self.decision_engine.get_decision_metrics(),
            'memory_metrics': self.memory_interface.get_memory_metrics(),
            'character_summary': self.character_interpreter.get_character_summary(),
            'component_architecture': 'integrated_modular'
        })
        
        return base_info
    
    def get_recent_memories(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent memories from short-term memory."""
        return self.memory_interface.get_recent_memories(count)
    
    def get_significant_memories(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get most significant memories from long-term memory."""
        return self.memory_interface.get_significant_memories(count)
    
    def search_memories(self, search_term: str, memory_type: str = 'all') -> List[Dict[str, Any]]:
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
                'core_component': {
                    'agent_id': self.core.agent_id,
                    'is_active': self.core.is_active(),
                    'core_metrics': self.core.get_core_metrics()
                },
                'decision_engine': {
                    'llm_available': self.decision_engine.llm_available,
                    'decision_metrics': self.decision_engine.get_decision_metrics()
                },
                'character_interpreter': {
                    'character_summary': self.character_interpreter.get_character_summary()
                },
                'memory_interface': {
                    'memory_metrics': self.memory_interface.get_memory_metrics()
                },
                'integration_status': 'healthy',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting component status: {e}")
            return {'error': str(e)}
    
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
    
    def update_character_state(self, status: Optional[str] = None, location: Optional[str] = None, 
                             morale: Optional[float] = None) -> None:
        """Update character state information."""
        self.core.update_character_state(status, location, morale)
    
    # Private methods for internal operations
    
    def _derive_agent_id_from_path(self, path: str) -> str:
        """Derive a unique agent ID from the character directory path."""
        return self.core._derive_agent_id_from_path(path)
    
    def _make_decision(self, world_state_update: Dict[str, Any]) -> Optional[CharacterAction]:
        """Core decision-making logic (delegated to decision engine)."""
        return self.decision_engine.make_decision(world_state_update)
    
    def _assess_current_situation(self) -> Dict[str, Any]:
        """Assess the current situation (delegated to decision engine)."""
        return self.decision_engine._assess_current_situation()
    
    def _generate_personal_interpretation(self, experience: Dict[str, Any]) -> str:
        """Generate personal interpretation of an experience."""
        return self.memory_interface._generate_personal_interpretation(experience)