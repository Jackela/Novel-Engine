#!/usr/bin/env python3
"""
DirectorAgent Core Implementation - Refactored with Modular Architecture.

This module implements the DirectorAgent class using composition with focused modules
for better maintainability and separation of concerns. The DirectorAgent now serves
as a coordinator that orchestrates specialized modules for different aspects of
simulation management.

Modules used:
- TurnManager: Turn execution and coordination
- NarrativeProcessor: Campaign brief and narrative handling
- IronLawsProcessor: Action validation and rules processing
- SimulationCoordinator: Agent management and world state persistence
- CampaignLogger: Event logging and campaign tracking
- WorldStateManager: World state management
- AgentCoordinator: Agent interaction coordination
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import agent and shared types
from src.persona_agent import PersonaAgent
from shared_types import CharacterAction
from src.event_bus import EventBus

# Import composed modules
from src.core.turn_manager import TurnManager
from src.core.narrative_processor import NarrativeProcessor
from src.core.iron_laws_processor import IronLawsProcessor
from src.core.simulation_coordinator import SimulationCoordinator
from src.core.campaign_logger import CampaignLogger
from src.core.world_state_manager import WorldStateManager
from src.core.agent_coordinator import AgentCoordinator

# Import configuration loader
from config_loader import get_config

# Configure logging for the director agent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DirectorAgent:
    """
    Core implementation of the simulation's central orchestrator using modular architecture.
    
    The DirectorAgent now serves as a coordinator that orchestrates specialized modules:
    - TurnManager: Handles turn-based execution and coordination
    - NarrativeProcessor: Manages campaign briefs and story elements
    - IronLawsProcessor: Validates actions against the 5 Iron Laws
    - SimulationCoordinator: Manages agents and world state persistence
    - CampaignLogger: Handles event logging and campaign tracking
    - WorldStateManager: Manages world state operations
    - AgentCoordinator: Coordinates agent interactions
    
    Key Responsibilities:
    - Module coordination and dependency injection
    - Event routing between modules
    - Unified API for simulation control
    - Error handling and recovery coordination
    - Configuration management
    
    Architecture Notes:
    - Uses composition over inheritance for modularity
    - Maintains clear separation of concerns
    - Supports dependency injection for testing
    - Provides unified logging across modules
    """
    
    def __init__(self, event_bus: EventBus, world_state_file_path: Optional[str] = None, 
                 campaign_log_path: Optional[str] = None, campaign_brief_path: Optional[str] = None):
        """
        Initialize the DirectorAgent with modular architecture.
        
        Sets up specialized modules and coordinates their initialization.
        Handles file operations with comprehensive error checking.
        
        Args:
            event_bus: An instance of the EventBus for decoupled communication
            world_state_file_path: Optional path to a world state database file
            campaign_log_path: Optional path to a campaign log file
            campaign_brief_path: Optional path to a campaign brief file
                                  
        Raises:
            ValueError: If files are provided but malformed
            OSError: If file operations fail due to permissions or disk issues
        """
        logger.info("Initializing DirectorAgent with modular architecture...")
        
        self.event_bus = event_bus
        
        # Load configuration
        try:
            config = get_config()
            self._config = config
        except Exception as e:
            logger.warning(f"Failed to load configuration, using defaults: {e}")
            self._config = None
        
        # Initialize paths with configuration defaults
        self._initialize_paths(world_state_file_path, campaign_log_path, campaign_brief_path)
        
        # Initialize configuration parameters
        self._initialize_configuration()
        
        # Initialize composed modules
        self._initialize_modules()
        
        # Initialize director systems
        try:
            self._setup_event_subscriptions()
            self._trigger_initial_narrative_events()
            
            logger.info(f"DirectorAgent initialized successfully with modular architecture")
            logger.info(f"Campaign log: {self.campaign_log_path}")
            logger.info(f"World state file: {self.world_state_file_path or 'None (using defaults)'}")
            logger.info(f"Campaign brief: {self.campaign_brief_path or 'None (combat mode)'}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DirectorAgent: {str(e)}")
            raise ValueError(f"DirectorAgent initialization failed: {str(e)}")
    
    def _initialize_paths(self, world_state_file_path: Optional[str], 
                         campaign_log_path: Optional[str], 
                         campaign_brief_path: Optional[str]) -> None:
        """Initialize file paths with configuration defaults."""
        # World state file path
        if world_state_file_path is None and self._config:
            world_state_file_path = self._config.director.world_state_file
        self.world_state_file_path = world_state_file_path
        
        # Campaign log path
        if campaign_log_path is None:
            if self._config:
                campaign_log_path = self._config.paths.log_file_path
            else:
                campaign_log_path = "campaign_log.md"
        self.campaign_log_path = campaign_log_path
        
        # Campaign brief path
        self.campaign_brief_path = campaign_brief_path
    
    def _initialize_configuration(self) -> None:
        """Initialize configuration parameters."""
        if self._config:
            self.max_turn_history = self._config.director.max_turn_history
            self.error_threshold = self._config.director.error_threshold
        else:
            self.max_turn_history = 100
            self.error_threshold = 10
        
        # Error tracking
        self.error_count = 0
        self.last_error_time: Optional[datetime] = None
    
    def _initialize_modules(self) -> None:
        """Initialize all composed modules."""
        # Campaign Logger - handles event logging
        self.campaign_logger = CampaignLogger(self.campaign_log_path)
        
        # Simulation Coordinator - manages agents and world state
        self.simulation_coordinator = SimulationCoordinator(
            world_state_file_path=self.world_state_file_path,
            max_turn_history=self.max_turn_history
        )
        
        # Turn Manager - handles turn execution
        self.turn_manager = TurnManager(
            event_bus=self.event_bus,
            max_turn_history=self.max_turn_history
        )
        
        # Narrative Processor - handles story elements
        self.narrative_processor = NarrativeProcessor(
            campaign_brief_path=self.campaign_brief_path
        )
        
        # Iron Laws Processor - validates actions
        self.iron_laws_processor = IronLawsProcessor()
        
        # World State Manager - manages world state operations
        self.world_state_manager = WorldStateManager()
        
        # Agent Coordinator - coordinates agent interactions
        self.agent_coordinator = AgentCoordinator(self.event_bus)
        
        logger.info("All modules initialized successfully")
    
    def _setup_event_subscriptions(self) -> None:
        """Set up event bus subscriptions for coordination."""
        # Subscribe to agent actions
        self.event_bus.subscribe("AGENT_ACTION_COMPLETE", self._handle_agent_action)
        
        # Subscribe to turn events for coordination
        self.event_bus.subscribe("TURN_START", self._on_turn_start)
        self.event_bus.subscribe("TURN_COMPLETE", self._on_turn_complete)
    
    def _trigger_initial_narrative_events(self) -> None:
        """Trigger initial narrative events if campaign brief is loaded."""
        if self.narrative_processor.has_campaign_brief():
            self.narrative_processor.trigger_initial_narrative_events(self.log_event)
    
    # Public API Methods (maintain compatibility with original interface)
    
    def register_agent(self, agent: PersonaAgent) -> bool:
        """
        Register a PersonaAgent instance with the DirectorAgent for simulation management.
        
        Args:
            agent: PersonaAgent instance to register
                  
        Returns:
            bool: True if registration successful, False if validation failed
        """
        return self.simulation_coordinator.register_agent(agent, self.log_event)
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the simulation.
        
        Args:
            agent_id: ID of the agent to remove
            
        Returns:
            bool: True if agent was found and removed, False otherwise
        """
        return self.simulation_coordinator.remove_agent(agent_id, self.log_event)
    
    def run_turn(self) -> Dict[str, Any]:
        """
        Execute a single simulation turn.
        
        Returns:
            A dictionary confirming the turn has started
        """
        registered_agents = self.simulation_coordinator.get_registered_agents()
        world_state_data = self.simulation_coordinator.get_world_state_data()
        
        result = self.turn_manager.run_turn(
            registered_agents=registered_agents,
            world_state_data=world_state_data,
            log_event_callback=self.log_event
        )
        
        # Update simulation metrics
        self.simulation_coordinator.update_simulation_metrics(
            self.turn_manager.get_current_turn_number(),
            self.turn_manager.get_total_actions_processed()
        )
        
        return result
    
    def log_event(self, event_description: str) -> None:
        """
        Log an event to the campaign log.
        
        Args:
            event_description: Description of the event to log
        """
        self.campaign_logger.log_event(event_description)
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information about the current simulation state.
        
        Returns:
            Dict containing detailed simulation status information
        """
        return self.simulation_coordinator.get_simulation_status()
    
    def get_agent_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all registered agents with basic information.
        
        Returns:
            List of dictionaries containing agent information
        """
        return self.simulation_coordinator.get_agent_list()
    
    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save current world state to file.
        
        Args:
            file_path: Optional path to save to (uses default if None)
            
        Returns:
            bool: True if save successful, False otherwise
        """
        return self.simulation_coordinator.save_world_state(file_path, self.log_event)
    
    def close_campaign_log(self) -> None:
        """Close the campaign log file."""
        self.campaign_logger.close()
    
    def generate_narrative_context(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate narrative context for a specific agent.
        
        Args:
            agent_id: ID of the agent to generate context for
            
        Returns:
            Dict containing narrative context or None if no campaign brief loaded
        """
        registered_agents = self.simulation_coordinator.get_registered_agents()
        current_turn = self.turn_manager.get_current_turn_number()
        
        return self.narrative_processor.generate_narrative_context(
            agent_id=agent_id,
            registered_agents=registered_agents,
            current_turn_number=current_turn
        )
    
    # Internal event handlers
    
    def _handle_agent_action(self, agent: PersonaAgent, action: Optional[CharacterAction]) -> None:
        """Handle an agent's action completion."""
        # Delegate to turn manager
        self.turn_manager.handle_agent_action(agent, action, self.log_event)
        
        # Process narrative actions if applicable
        if action and self.narrative_processor.has_campaign_brief():
            narrative_outcome = self.narrative_processor.process_narrative_action(action, agent)
            if narrative_outcome:
                self.log_event(f"Narrative outcome: {narrative_outcome.description}")
        
        # Validate action against Iron Laws if applicable
        if action and hasattr(action, 'action_type'):
            world_context = self.simulation_coordinator.get_world_state_data()
            # Convert action to ProposedAction format if needed for validation
            # This would require additional conversion logic based on action structure
    
    def _on_turn_start(self, **kwargs) -> None:
        """Handle turn start events."""
        current_turn = self.turn_manager.get_current_turn_number()
        self.log_event(f"Turn {current_turn} coordination initiated")
    
    def _on_turn_complete(self, **kwargs) -> None:
        """Handle turn completion events."""
        # Store turn in history
        turn_summary = {
            'turn_number': self.turn_manager.get_current_turn_number(),
            'timestamp': datetime.now().isoformat(),
            'actions_processed': self.turn_manager.get_total_actions_processed(),
            'agents_active': len(self.simulation_coordinator.get_registered_agents())
        }
        
        world_state_data = self.simulation_coordinator.get_world_state_data()
        self.turn_manager.store_turn_in_history(turn_summary, world_state_data)
    
    # Properties for backward compatibility
    
    @property
    def current_turn_number(self) -> int:
        """Get the current turn number."""
        return self.turn_manager.get_current_turn_number()
    
    @property
    def total_actions_processed(self) -> int:
        """Get the total number of actions processed."""
        return self.turn_manager.get_total_actions_processed()
    
    @property
    def registered_agents(self) -> List[PersonaAgent]:
        """Get the list of registered agents."""
        return self.simulation_coordinator.get_registered_agents()
    
    @property
    def world_state_data(self) -> Dict[str, Any]:
        """Get the current world state data."""
        return self.simulation_coordinator.get_world_state_data()
    
    @property
    def story_state(self) -> Dict[str, Any]:
        """Get the current story state."""
        return self.narrative_processor.get_story_state()


# Factory functions for backward compatibility

def create_director_with_agents(world_state_path: Optional[str] = None, 
                               campaign_log_path: Optional[str] = None,
                               campaign_brief_path: Optional[str] = None) -> DirectorAgent:
    """
    Factory function to create DirectorAgent with pre-configured settings.
    
    Args:
        world_state_path: Optional path to world state file
        campaign_log_path: Optional path to campaign log file  
        campaign_brief_path: Optional path to campaign brief file
        
    Returns:
        Configured DirectorAgent instance
    """
    from src.event_bus import EventBus
    
    event_bus = EventBus()
    director = DirectorAgent(
        event_bus=event_bus,
        world_state_file_path=world_state_path,
        campaign_log_path=campaign_log_path,
        campaign_brief_path=campaign_brief_path
    )
    
    return director


def run_simulation_batch(director: DirectorAgent, num_turns: int) -> List[Dict[str, Any]]:
    """
    Run a batch of simulation turns.
    
    Args:
        director: DirectorAgent instance to run
        num_turns: Number of turns to execute
        
    Returns:
        List of turn results
    """
    results = []
    
    for turn in range(num_turns):
        logger.info(f"Executing batch turn {turn + 1}/{num_turns}")
        result = director.run_turn()
        results.append(result)
        
        # Add small delay for agent processing
        import time
        time.sleep(0.1)
    
    return results


def example_usage():
    """Example usage of the refactored DirectorAgent."""
    logger.info("Starting DirectorAgent example usage")
    
    # Create director with modular architecture
    director = create_director_with_agents(
        world_state_path="example_world_state.json",
        campaign_log_path="example_campaign.md",
        campaign_brief_path="example_brief.yaml"
    )
    
    # Example simulation
    logger.info("Running example simulation with modular DirectorAgent")
    results = run_simulation_batch(director, 3)
    
    # Display results
    for i, result in enumerate(results):
        logger.info(f"Turn {i + 1} result: {result}")
    
    # Display final status
    status = director.get_simulation_status()
    logger.info(f"Final simulation status: {status}")
    
    # Clean up
    director.close_campaign_log()
    logger.info("Example usage completed")


if __name__ == "__main__":
    example_usage()