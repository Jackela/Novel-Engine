#!/usr/bin/env python3
"""
DirectorAgent Core Implementation.

This module implements the DirectorAgent class, which serves as the central
orchestrator for the multi-agent simulation. The DirectorAgent manages the
simulation by coordinating agent interactions, and maintaining a structured
event log.

The DirectorAgent is responsible for:
- Registering and managing multiple agent instances.
- Executing simulation turns by calling each agent's decision-making process.
- Logging all events and actions to a persistent campaign log.
- Managing world state data.
- Handling errors gracefully to maintain simulation stability.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

# Import agent and shared types
from src.persona_agent import PersonaAgent
from shared_types import CharacterAction
from src.event_bus import EventBus

# Import configuration loader
from config_loader import get_config, get_campaign_log_filename

# Import narrative components
from campaign_brief import CampaignBrief, CampaignBriefLoader, NarrativeEvent
from narrative_actions import NarrativeActionResolver, NarrativeOutcome


# Configure logging for the director agent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DirectorAgent:
    """
    Core implementation of the simulation's central orchestrator.
    
    The DirectorAgent manages the simulation by:
    - Registering and coordinating multiple PersonaAgent instances.
    - Executing simulation turns and collecting agent decisions.
    - Maintaining a comprehensive campaign log for narrative tracking.
    - Managing the world state.
    - Handling errors gracefully to ensure simulation stability.
    
    Key Responsibilities:
    - Agent lifecycle management (registration, validation, coordination).
    - Turn-based simulation execution with structured event processing.
    - Campaign narrative logging with timestamp and participant tracking.
    - Error handling and recovery for robust simulation operation.
    - Interface for world state database integration.
    
    Architecture Notes:
    - Designed for easy integration with AI/LLM systems.
    - Maintains clear separation between agent coordination and world state management.
    - Supports dynamic agent registration and deregistration during runtime.
    - Provides hooks for `WorldState_DB.json` integration.
    - Implements comprehensive logging for debugging and narrative purposes.
    """
    
    def __init__(self, event_bus: EventBus, world_state_file_path: Optional[str] = None, campaign_log_path: Optional[str] = None, campaign_brief_path: Optional[str] = None):
        """
        Initialize the DirectorAgent.
        
        Sets up the core director infrastructure including agent registry,
        campaign logging system, world state management preparation, and narrative engine.
        Handles file operations with comprehensive error checking.
        
        Args:
            event_bus: An instance of the EventBus for decoupled communication.
            world_state_file_path: Optional path to a world state database file.
                                  If provided, attempts to load existing world state.
                                  If None, uses configuration or defaults.
            campaign_log_path: Optional path to a campaign log file.
                             If None, uses configuration value.
            campaign_brief_path: Optional path to a campaign brief YAML/Markdown file
                               that defines the narrative context for the simulation.
                               If None, the simulation runs in a basic combat mode.
                                  
        Raises:
            ValueError: If files are provided but malformed.
            OSError: If file operations fail due to permissions or disk issues.
        """
        logger.info("Initializing DirectorAgent...")
        
        self.event_bus = event_bus

        # Load configuration
        try:
            config = get_config()
            self._config = config
        except Exception as e:
            logger.warning(f"Failed to load configuration, using defaults: {e}")
            self._config = None
        
        # Agent management system
        self.registered_agents: List[PersonaAgent] = []
        """List of registered PersonaAgent instances managed by this director."""
        
        # World state management
        if world_state_file_path is None and self._config:
            world_state_file_path = self._config.director.world_state_file
        self.world_state_file_path = world_state_file_path
        """Path to world state database file for persistence."""
        
        self.world_state_data: Dict[str, Any] = {}
        """Current world state data (placeholder for future implementation)."""
        
        # Campaign logging system
        if campaign_log_path is None:
            if self._config:
                campaign_log_path = self._config.paths.log_file_path
            else:
                campaign_log_path = "campaign_log.md"
        self.campaign_log_path = campaign_log_path
        """Path to the campaign log file for narrative tracking."""
        
        # Set configuration-driven parameters
        if self._config:
            self.max_turn_history = self._config.director.max_turn_history
            self.error_threshold = self._config.director.error_threshold
        else:
            self.max_turn_history = 100
            self.error_threshold = 10
        
        # Simulation state tracking
        self.current_turn_number = 0
        """Current simulation turn counter."""
        
        self.simulation_start_time = datetime.now()
        """Timestamp when the simulation was initialized."""
        
        self.total_actions_processed = 0
        """Counter for total actions processed across all turns."""
        
        # Error tracking
        self.error_count = 0
        """Count of errors encountered during simulation."""
        
        self.last_error_time: Optional[datetime] = None
        """Timestamp of the most recent error."""
        
        # Narrative engine components
        self.campaign_brief_path = campaign_brief_path
        """Path to campaign brief file for narrative context."""
        
        self.campaign_brief: Optional[CampaignBrief] = None
        """Loaded campaign brief defining narrative context."""
        
        self.narrative_resolver = NarrativeActionResolver()
        """Resolver for story-driven actions and outcomes."""
        
        self.story_state = {
            'current_phase': 'initialization',
            'triggered_events': [],
            'story_progression': [],
            'investigation_count': 0,
            'dialogue_count': 0,
            'character_relationships': {}
        }
        """Current narrative state tracking."""
        
        # Dynamic world state tracker
        self.world_state_tracker = {
            'discovered_clues': {},  # agent_id -> list of discovered clues
            'environmental_changes': {},  # location -> list of changes
            'agent_discoveries': {},  # turn_number -> {agent_id: discoveries}
            'temporal_markers': {},  # timestamp -> events
            'investigation_history': []  # chronological list of all investigations
        }
        """Dynamic world state tracker."""
        
        # Initialize director systems
        try:
            self._initialize_campaign_log()
            self._load_world_state()
            self._load_campaign_brief()

            # Subscribe to agent actions
            self.event_bus.subscribe("AGENT_ACTION_COMPLETE", self._handle_agent_action)
            
            logger.info(f"DirectorAgent initialized successfully")
            logger.info(f"Campaign log: {self.campaign_log_path}")
            logger.info(f"World state file: {self.world_state_file_path or 'None (using defaults)'}")
            logger.info(f"Campaign brief: {self.campaign_brief_path or 'None (combat mode)'}")
            logger.info(f"Registered agents: {len(self.registered_agents)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DirectorAgent: {str(e)}")
            raise ValueError(f"DirectorAgent initialization failed: {str(e)}")
    
    def _initialize_campaign_log(self) -> None:
        """
        Initialize the campaign log file with proper headers and initial entries.
        
        Creates a new campaign log if none exists, or validates the existing one.
        The log uses markdown format for human readability and tool compatibility.
        
        Raises:
            OSError: If file creation or writing fails
        """
        try:
            # Always create fresh campaign log for each simulation
            logger.info(f"Creating fresh campaign log: {self.campaign_log_path}")
            self._create_new_campaign_log()
                
        except Exception as e:
            logger.error(f"Failed to initialize campaign log: {str(e)}")
            raise OSError(f"Campaign log initialization failed: {str(e)}")
    
    def _create_new_campaign_log(self) -> None:
        """Create a new campaign log file with proper formatting and headers."""
        initial_content = f"""# Campaign Log

**Simulation Started:** {self.simulation_start_time.strftime('%Y-%m-%d %H:%M:%S')}  
**Director Agent:** DirectorAgent v1.0  
**Phase:** Phase 1 - Core Logic Implementation  

## Campaign Overview

This log tracks all events, decisions, and interactions in the StoryForge AI Interactive Story Engine.
Each entry includes timestamps, participating agents, and detailed event descriptions.

---

## Campaign Events

### Simulation Initialization
**Time:** {self.simulation_start_time.strftime('%Y-%m-%d %H:%M:%S')}  
**Event:** DirectorAgent initialized and campaign log created  
**Participants:** System  
**Details:** Game Master AI successfully started, ready for agent registration and simulation execution

"""
        
        try:
            with open(self.campaign_log_path, 'w', encoding='utf-8') as file:
                file.write(initial_content)
            
            logger.info(f"New campaign log created: {self.campaign_log_path}")
            logger.info(f"Campaign log file size: {os.path.getsize(self.campaign_log_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to create campaign log at {self.campaign_log_path}: {e}")
            raise
    
    def _backup_existing_log(self) -> None:
        """Create a backup of existing campaign log before reinitializing."""
        backup_path = f"{self.campaign_log_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(self.campaign_log_path, backup_path)
            logger.info(f"Existing campaign log backed up to: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create backup of existing log: {e}")
    
    def _load_world_state(self) -> None:
        """
        Load world state data from file if provided.
        
        This method prepares for future Phase 2 integration with WorldState_DB.json.
        Currently implements placeholder logic for world state management.
        
        Raises:
            ValueError: If world state file exists but contains invalid data
            OSError: If file operations fail
        """
        if self.world_state_file_path is None:
            logger.info("No world state file specified, using default world state")
            self._initialize_default_world_state()
            return
        
        try:
            if os.path.exists(self.world_state_file_path):
                logger.info(f"Loading world state from: {self.world_state_file_path}")
                
                with open(self.world_state_file_path, 'r', encoding='utf-8') as file:
                    self.world_state_data = json.load(file)
                
                # Validate the world state data structure.
                self._validate_world_state_data()
                
                logger.info(f"World state loaded successfully")
                logger.info(f"World state contains {len(self.world_state_data)} top-level entries")
                
            else:
                logger.warning(f"World state file not found: {self.world_state_file_path}")
                logger.info("Initializing with default world state")
                self._initialize_default_world_state()
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in world state file: {str(e)}")
            raise ValueError(f"World state file contains invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to load world state: {str(e)}")
            raise OSError(f"World state loading failed: {str(e)}")
    
    def _initialize_default_world_state(self) -> None:
        """Initialize default world state for simulation operation."""
        self.world_state_data = {
            'simulation_info': {
                'phase': 'Phase 1 - Core Logic',
                'version': '1.0.0',
                'initialized_at': self.simulation_start_time.isoformat(),
            },
            'locations': {
                'default_location': {
                    'name': 'Simulation Space',
                    'description': 'Default location for Phase 1 testing',
                    'threat_level': 'low',
                    'faction_control': 'neutral',
                }
            },
            'factions': {
                'imperium': {'status': 'active', 'influence': 0.6},
                'chaos': {'status': 'active', 'influence': 0.3},
                'ork': {'status': 'active', 'influence': 0.1},
            },
            'global_events': [],
            'turn_history': [],
        }
        
        logger.info("Default world state initialized")
    
    def _load_campaign_brief(self) -> None:
        """
        Load campaign brief file to define narrative context for story-driven simulation.
        
        Campaign briefs transform the simulation from basic combat mechanics to rich
        story-driven character interactions. If no brief is provided, simulation
        runs in traditional combat-focused mode.
        
        Raises:
            ValueError: If campaign brief file exists but contains invalid data
            OSError: If file operations fail
        """
        if self.campaign_brief_path is None:
            logger.info("No campaign brief specified - running in combat mode")
            self.narrative_resolver = NarrativeActionResolver(None)
            return
        
        try:
            campaign_brief_path = Path(self.campaign_brief_path)
            
            if not campaign_brief_path.exists():
                logger.warning(f"Campaign brief file not found: {self.campaign_brief_path}")
                logger.info("Running in combat mode without narrative context")
                self.narrative_resolver = NarrativeActionResolver(None)
                return
            
            # Load campaign brief.
            logger.info(f"Loading campaign brief from: {self.campaign_brief_path}")
            
            brief_loader = CampaignBriefLoader()
            self.campaign_brief = brief_loader.load_from_file(campaign_brief_path)
            
            # Validate campaign brief.
            brief_loader.validate_campaign_brief(self.campaign_brief)
            
            # Initialize narrative resolver.
            self.narrative_resolver = NarrativeActionResolver(self.campaign_brief)
            
            # Update story state.
            self.story_state['current_phase'] = 'campaign_loaded'
            
            logger.info(f"Campaign brief loaded successfully: {self.campaign_brief.title}")
            logger.info(f"Setting: {self.campaign_brief.setting[:100]}...")
            logger.info(f"Narrative events available: {len(self.campaign_brief.key_events)}")
            
            # Trigger initial narrative events.
            self._trigger_initial_narrative_events()
            
        except Exception as e:
            logger.error(f"Failed to load campaign brief: {str(e)}")
            logger.warning("Falling back to combat mode")
            self.campaign_brief = None
            self.narrative_resolver = NarrativeActionResolver(None)
    
    def _trigger_initial_narrative_events(self) -> None:
        """
        Trigger initial narrative events marked for simulation start.
        
        Processes campaign brief events with 'simulation_start' trigger condition
        to establish the initial story context for all agents.
        """
        if not self.campaign_brief:
            return
        
        for event in self.campaign_brief.key_events:
            if event.trigger_condition == "simulation_start":
                logger.info(f"Triggering initial narrative event: {event.description}")
                
                # Add event to story state.
                self.story_state['triggered_events'].append({
                    'event': event,
                    'turn_triggered': 0,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Log narrative event.
                event_description = f"**NARRATIVE EVENT:** {event.description}"
                self.log_event(event_description)
    
    def _validate_world_state_data(self) -> None:
        """
        Validate the structure and content of loaded world state data.
        
        Ensures that world state data contains required fields and valid values
        for proper simulation operation.
        
        Raises:
            ValueError: If world state data is missing required fields or has invalid structure
        """
        required_fields = ['simulation_info', 'locations', 'factions']
        
        for field in required_fields:
            if field not in self.world_state_data:
                logger.warning(f"World state missing required field: {field}")
                # Add default values to maintain system stability.
                if field == 'simulation_info':
                    self.world_state_data[field] = {'phase': 'Unknown', 'version': 'Unknown'}
                elif field == 'locations':
                    self.world_state_data[field] = {}
                elif field == 'factions':
                    self.world_state_data[field] = {}
        
        # Validate data types.
        if not isinstance(self.world_state_data['locations'], dict):
            raise ValueError("World state 'locations' must be a dictionary")
        
        if not isinstance(self.world_state_data['factions'], dict):
            raise ValueError("World state 'factions' must be a dictionary")
        
        logger.info("World state data validation completed")
    
    def register_agent(self, agent: PersonaAgent) -> bool:
        """
        Register a PersonaAgent instance with the DirectorAgent for simulation management.
        
        Validates the agent has required methods and adds it to the registered agents list.
        Includes comprehensive validation to ensure agent compatibility and prevent
        runtime errors during simulation execution.
        
        Args:
            agent: PersonaAgent instance to register
                  Must have decision_loop method and valid agent_id
                  
        Returns:
            bool: True if registration successful, False if validation failed
                  
        Example:
            >>> director = DirectorAgent()
            >>> agent = PersonaAgent("character_sheet.md")
            >>> success = director.register_agent(agent)
            >>> if success:
            ...     print("Agent registered successfully")
        """
        try:
            logger.info(f"Attempting to register agent for simulation management")
            
            # Validate the agent instance.
            if not isinstance(agent, PersonaAgent):
                logger.error(f"Invalid agent type: {type(agent)}. Expected PersonaAgent instance")
                return False
            
            # Validate that the agent has the required methods.
            if not hasattr(agent, 'handle_turn_start'):
                logger.error(f"Agent missing required 'handle_turn_start' method")
                return False
            
            if not callable(getattr(agent, 'handle_turn_start')):
                logger.error(f"Agent 'handle_turn_start' is not callable")
                return False
            
            # Validate that the agent has a valid ID.
            if not hasattr(agent, 'agent_id') or not agent.agent_id:
                logger.error(f"Agent missing valid agent_id")
                return False
            
            # Check for duplicate registration.
            existing_ids = [existing_agent.agent_id for existing_agent in self.registered_agents]
            if agent.agent_id in existing_ids:
                logger.warning(f"Agent with ID '{agent.agent_id}' already registered")
                return False
            
            # Validate that the agent has been properly initialized.
            if not hasattr(agent, 'character_data') or not isinstance(agent.character_data, dict):
                logger.error(f"Agent character_data not properly initialized")
                return False
            
            # Register the agent.
            self.registered_agents.append(agent)
            
            # Log the successful registration.
            character_name = agent.character_data.get('name', 'Unknown')
            faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
            
            logger.info(f"Agent registered successfully:")
            logger.info(f"  - Agent ID: {agent.agent_id}")
            logger.info(f"  - Character: {character_name}")
            logger.info(f"  - Faction: {faction}")
            logger.info(f"  - Total registered agents: {len(self.registered_agents)}")
            
            # Log the registration event to the campaign log.
            registration_event = (
                f"**Agent Registration:** {character_name} ({agent.agent_id}) joined the simulation\\n"
                f"**Faction:** {faction}\\n"
                f"**Registration Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                f"**Total Active Agents:** {len(self.registered_agents)}"
            )
            
            self.log_event(registration_event)
            
            return True
            
        except Exception as e:
            logger.error(f"Exception during agent registration: {str(e)}")
            self.error_count += 1
            self.last_error_time = datetime.now()
            return False
    
    def log_event(self, event_description: str) -> None:
        """
        Append an event description to the campaign log with timestamp and formatting.
        
        Creates properly formatted log entries with timestamps and handles file
        operations safely. Ensures campaign log remains readable and well-structured
        for both human review and potential future AI processing.
        
        Args:
            event_description: Human-readable description of the event to log
                             Can include markdown formatting for better presentation
                             Should describe what happened, who was involved, and the outcome
                             
        Example:
            >>> director.log_event("Brother Marcus engaged ork raiders in sector 7")
            >>> director.log_event("**Combat Result:** Imperial forces victorious")
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create a new campaign log if one doesn't exist.
            if not os.path.exists(self.campaign_log_path):
                self._create_new_campaign_log()
            
            # Format the event entry in markdown.
            log_entry = f"\n### Turn {self.current_turn_number + 1} Event\n"
            log_entry += f"**Time:** {timestamp}  \n"
            log_entry += f"**Event:** {event_description}  \n"
            log_entry += f"**Turn:** {self.current_turn_number + 1}  \n"
            log_entry += f"**Active Agents:** {len(self.registered_agents)}  \n"
            log_entry += "\n---\n"
            
            # Append the event to the campaign log file.
            with open(self.campaign_log_path, 'a', encoding='utf-8') as file:
                file.write(log_entry)
            
            logger.info(f"Event logged to campaign: {event_description[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to log event to campaign file: {str(e)}")
            self.error_count += 1
            self.last_error_time = datetime.now()
            
            # Log to console as a fallback.
            fallback_log = f"[{timestamp}] CAMPAIGN EVENT: {event_description}"
            logger.warning(f"Fallback logging: {fallback_log}")
    
    def run_turn(self) -> Dict[str, Any]:
        """
        Execute a single simulation turn by emitting a 'TURN_START' event.
        
        Orchestrates the turn-based simulation by:
        1. Incrementing the turn counter and logging the turn start.
        2. Emitting a `TURN_START` event to all subscribed agents.
        3. Agents will react to this event and perform their actions asynchronously.
        4. The Director will handle agent actions via the `_handle_agent_action` callback.
        
        Returns:
            A dictionary confirming the turn has started. Detailed turn results
            will be compiled as agents complete their actions.
        """
        turn_start_time = datetime.now()
        self.current_turn_number += 1
        
        logger.info(f"=== STARTING TURN {self.current_turn_number} ===")
        self.log_event(f"TURN {self.current_turn_number} BEGINS")
        
        if not self.registered_agents:
            logger.warning("No registered agents found - turn will be empty")
            self.log_event(f"TURN {self.current_turn_number} COMPLETED")
            return {'status': 'empty_turn'}

        # Prepare a generic world state update for this turn
        world_state_update = self._prepare_world_state_for_turn()
        
        # Emit the turn start event for all agents to hear
        self.event_bus.emit("TURN_START", world_state_update=world_state_update)
        
        # The rest of the turn processing is now handled by event callbacks
        return {
            'status': 'turn_started',
            'turn_number': self.current_turn_number,
            'timestamp': turn_start_time.isoformat()
        }

    def _prepare_world_state_for_turn(self) -> Dict[str, Any]:
        """Prepares a generic world state dictionary for the current turn."""
        return {
            'current_turn': self.current_turn_number,
            'simulation_time': datetime.now().isoformat(),
            'world_state': self.world_state_data,
        }

    def _handle_agent_action(self, agent: PersonaAgent, action: Optional[CharacterAction]):
        """Callback to handle an agent's action after they process a turn."""
        if action:
            logger.info(f"Received action from {agent.agent_id}: {action.action_type}")
            # Existing logic to process and log the action
            character_name = agent.character_data.get('name', 'Unknown')
            action_description = f"{character_name} ({agent.agent_id}) decided to {action.action_type}"
            if action.reasoning:
                action_description += f": {action.reasoning}"
            self.log_event(action_description)
            self.total_actions_processed += 1
        else:
            logger.info(f"{agent.agent_id} chose to wait.")
            self.log_event(f"{agent.character_data.get('name', agent.agent_id)} is waiting and observing.")
    
    def _prepare_world_state_for_agent(self, agent: PersonaAgent) -> Dict[str, Any]:
        """
        Prepare world state information for a specific agent's decision-making.
        
        This method creates a customized world state update that includes both tactical
        information and rich narrative context when a campaign brief is loaded. The
        agent receives character-specific story elements alongside traditional simulation data.
        
        Args:
            agent: PersonaAgent instance to prepare world state for
            
        Returns:
            Dict containing world state information and narrative context relevant to the agent
        """
        # Basic world state update.
        world_state_update = {
            'current_turn': self.current_turn_number,
            'simulation_time': datetime.now().isoformat(),
            'turn_number': self.current_turn_number,
            'world_state': {
                'current_turn': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'simulation_time': datetime.now().isoformat(),
            },
            'location_updates': {
                'current_area': {
                    'threat_level': 'moderate',
                    'faction_presence': 'mixed',
                    'resources_available': True,
                    'strategic_importance': 'normal',
                }
            },
            'entity_updates': {
                # Information about other agents/entities the agent might be aware of.
            },
            'faction_updates': {
                'imperium': {'activity': 'normal', 'influence': 0.6},
                'chaos': {'activity': 'low', 'influence': 0.2},
                'ork': {'activity': 'moderate', 'influence': 0.2},
            },
            'recent_events': [
                {
                    'id': f'event_{self.current_turn_number}',
                    'type': 'world_update',
                    'description': 'The world is calm, but tensions remain',
                    'scope': 'local',
                    'location': 'simulation_space',
                }
            ],
            'turn_info': {
                'current_turn': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'simulation_time': datetime.now().isoformat(),
            }
        }
        
        # Add information about other registered agents.
        other_agents = {}
        for other_agent in self.registered_agents:
            if other_agent.agent_id != agent.agent_id:
                other_agents[other_agent.agent_id] = {
                    'name': other_agent.character_data.get('name', 'Unknown'),
                    'faction': other_agent.subjective_worldview.get('primary_faction', 'Unknown'),
                    'status': other_agent.current_status,
                    'last_seen': 'recently',
                }
        
        world_state_update['entity_updates'] = other_agents
        
        # Add dynamic world state feedback.
        world_state_feedback = self._generate_world_state_feedback(agent.agent_id)
        if world_state_feedback:
            world_state_update['world_state_feedback'] = world_state_feedback
            logger.debug(f"Added dynamic world state feedback for agent {agent.agent_id}")
        
        # Generate and add narrative context.
        narrative_context = self.generate_narrative_context(agent.agent_id)
        if narrative_context:
            world_state_update['narrative_context'] = narrative_context
            logger.debug(f"Added narrative context for agent {agent.agent_id}")
        
        return world_state_update
    
    def _generate_world_state_feedback(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate dynamic world state feedback based on agent discoveries and world changes.
        
        This method creates the feedback that agents receive about the consequences of
        their previous actions and the evolving state of the world.
        
        Args:
            agent_id: ID of the agent to generate feedback for
            
        Returns:
            Dictionary containing world state feedback or None if no feedback available
        """
        feedback = {}
        has_feedback = False
        
        try:
            # Generate feedback on personal discoveries.
            personal_discoveries = self._get_agent_discoveries_feedback(agent_id)
            if personal_discoveries:
                feedback['personal_discoveries'] = personal_discoveries
                has_feedback = True
            
            # Generate feedback on environmental changes.
            environmental_changes = self._get_environmental_changes_feedback(agent_id)
            if environmental_changes:
                feedback['environmental_changes'] = environmental_changes
                has_feedback = True
            
            # Generate feedback on other agents' activities.
            other_agent_activities = self._get_other_agents_activities_feedback(agent_id)
            if other_agent_activities:
                feedback['other_agent_activities'] = other_agent_activities
                has_feedback = True
            
            # Generate a summary of the world state.
            world_state_summary = self._get_world_state_summary()
            if world_state_summary:
                feedback['world_state_summary'] = world_state_summary
                has_feedback = True
            
            return feedback if has_feedback else None
            
        except Exception as e:
            logger.error(f"Error generating world state feedback for {agent_id}: {str(e)}")
            return None
    
    def _get_agent_discoveries_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about the agent's recent discoveries.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of discovery feedback messages
        """
        feedback_messages = []
        
        # Check for recent discoveries by this agent.
        if agent_id in self.world_state_tracker['discovered_clues']:
            agent_clues = self.world_state_tracker['discovered_clues'][agent_id]
            
            # Get discoveries from this turn or the last.
            recent_clues = [
                clue for clue in agent_clues 
                if clue['turn_discovered'] >= self.current_turn_number - 1
            ]
            
            for clue in recent_clues:
                if clue['turn_discovered'] == self.current_turn_number - 1:
                    feedback_messages.append(f"You discovered a new clue: {clue['content']}")
                elif clue['turn_discovered'] == self.current_turn_number:
                    feedback_messages.append(f"You just discovered: {clue['content']}")
        
        return feedback_messages
    
    def _get_environmental_changes_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about environmental changes visible to the agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of environmental change messages
        """
        feedback_messages = []
        
        # Check for environmental changes.
        for location, changes_list in self.world_state_tracker['environmental_changes'].items():
            recent_changes = [
                change for change in changes_list 
                if change['turn'] >= self.current_turn_number - 2  # Show changes from the last 2 turns
            ]
            
            for change in recent_changes:
                if change['agent'] != agent_id:  # Don't show changes caused by the agent themselves
                    feedback_messages.append(f"In {location}, {change['change']}")
                else:
                    # Show the lingering effects of the agent's own actions.
                    if change['turn'] < self.current_turn_number:
                        feedback_messages.append(f"Your previous investigation in {location} has left visible traces.")
        
        return feedback_messages
    
    def _get_other_agents_activities_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about other agents' activities and discoveries.
        
        Args:
            agent_id: ID of the requesting agent
            
        Returns:
            List of other agents' activity messages
        """
        feedback_messages = []
        
        # Check for recent discoveries by other agents.
        current_turn = self.current_turn_number
        for turn_num in range(max(1, current_turn - 2), current_turn + 1):
            if turn_num in self.world_state_tracker['agent_discoveries']:
                turn_discoveries = self.world_state_tracker['agent_discoveries'][turn_num]
                
                for other_agent_id, discoveries in turn_discoveries.items():
                    if other_agent_id != agent_id:
                        # Find the agent's name.
                        other_agent_name = "Another agent"
                        for agent in self.registered_agents:
                            if agent.agent_id == other_agent_id:
                                other_agent_name = agent.character_data.get('name', 'Unknown Agent')
                                break
                        
                        for discovery in discoveries:
                            if turn_num == current_turn - 1:
                                feedback_messages.append(f"{other_agent_name} recently discovered: {discovery}")
                            elif turn_num == current_turn:
                                feedback_messages.append(f"{other_agent_name} just discovered: {discovery}")
        
        return feedback_messages
    
    def _get_world_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current world state.
        
        Returns:
            Dictionary containing world state summary information
        """
        total_clues = sum(len(clues) for clues in self.world_state_tracker['discovered_clues'].values())
        total_investigations = len(self.world_state_tracker['investigation_history'])
        total_locations_investigated = len(self.world_state_tracker['environmental_changes'])
        
        return {
            'total_clues_discovered': total_clues,
            'total_investigations': total_investigations,
            'locations_with_activity': total_locations_investigated,
            'current_phase': self.story_state.get('current_phase', 'unknown'),
            'world_activity_level': 'active' if total_investigations > 0 else 'quiet'
        }
    
    def generate_narrative_context(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate narrative context for a specific agent based on current story state.
        
        Creates rich story elements that transform basic simulation updates into
        compelling narrative situations. Character-specific context is tailored
        to their faction, personality, and relationship to the ongoing story.
        
        Args:
            agent_id: ID of the agent to generate context for
            
        Returns:
            Dict containing narrative context or None if no campaign brief loaded
        """
        if not self.campaign_brief:
            return None
        
        try:
            # Find the target agent to get character data.
            target_agent = None
            for agent in self.registered_agents:
                if agent.agent_id == agent_id:
                    target_agent = agent
                    break
            
            if not target_agent:
                logger.warning(f"Could not find agent {agent_id} for narrative context generation")
                return None
            
            # Basic narrative context structure.
            narrative_context = {
                'campaign_title': self.campaign_brief.title,
                'setting_description': self.campaign_brief.setting,
                'atmosphere': self.campaign_brief.atmosphere,
                'current_phase': self.story_state['current_phase'],
                'environmental_elements': [],
                'character_specific_context': '',
                'active_story_threads': [],
                'available_narrative_actions': []
            }
            
            # Add environmental narrative elements.
            if self.campaign_brief.environmental_elements:
                # Select relevant environmental elements (limit to 3 to avoid information overload).
                selected_elements = self.campaign_brief.environmental_elements[:3]
                narrative_context['environmental_elements'] = selected_elements
            
            # Generate character-specific narrative context.
            character_context = self._generate_character_specific_context(target_agent)
            narrative_context['character_specific_context'] = character_context
            
            # Check for triggered narrative events.
            active_events = self._check_narrative_event_triggers(target_agent)
            if active_events:
                narrative_context['active_story_threads'] = active_events
            
            # Add available narrative actions.
            narrative_actions = self._identify_available_narrative_actions(target_agent)
            narrative_context['available_narrative_actions'] = narrative_actions
            
            return narrative_context
            
        except Exception as e:
            logger.error(f"Failed to generate narrative context for agent {agent_id}: {str(e)}")
            return None
    
    def _generate_character_specific_context(self, agent: PersonaAgent) -> str:
        """
        Generate character-specific narrative context based on their faction and traits.
        
        Args:
            agent: PersonaAgent to generate context for
            
        Returns:
            String containing personalized narrative context
        """
        character_name = agent.character_data.get('name', 'Unknown')
        faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
        
        # Basic character context description.
        base_context = f"As {character_name} of {faction}, you find yourself in this unfolding story."
        
        # Add faction-specific narrative perspective.
        if 'imperial' in faction.lower():
            imperial_context = " Your duty to the Emperor guides your perception of these events."
            base_context += imperial_context
        elif 'ork' in faction.lower():
            ork_context = " Your ork instincts tell you there's a good fight brewing here."
            base_context += ork_context
        elif 'mechanicus' in faction.lower():
            mechanicus_context = " Your augmetic senses detect deeper mysteries in the machine spirits here."
            base_context += mechanicus_context
        
        # Add context based on the current story phase.
        if self.story_state['current_phase'] == 'investigation':
            base_context += " The mysteries here call for careful investigation."
        elif self.story_state['current_phase'] == 'revelation':
            base_context += " The truth begins to reveal itself through your actions."
        
        return base_context
    
    def _check_narrative_event_triggers(self, agent: PersonaAgent) -> List[Dict[str, Any]]:
        """
        Check which narrative events should trigger for the current turn and agent.
        
        Args:
            agent: Agent to check event triggers for
            
        Returns:
            List of active narrative events
        """
        active_events = []
        
        for event in self.campaign_brief.key_events:
            should_trigger = False
            
            # Check for turn-based triggers.
            if 'turn >=' in event.trigger_condition:
                try:
                    required_turn = int(event.trigger_condition.split('>=')[1].strip())
                    if self.current_turn_number >= required_turn:
                        should_trigger = True
                except ValueError:
                    logger.warning(f"Invalid turn trigger condition: {event.trigger_condition}")
            
            # Check for investigation count-based triggers.
            elif 'investigation_count >=' in event.trigger_condition:
                try:
                    required_count = int(event.trigger_condition.split('>=')[1].strip())
                    if self.story_state['investigation_count'] >= required_count:
                        should_trigger = True
                except ValueError:
                    logger.warning(f"Invalid investigation trigger condition: {event.trigger_condition}")
            
            # If the event should trigger and has not been triggered before.
            if should_trigger:
                # Check if this event has already been triggered.
                already_triggered = any(
                    triggered['event'].description == event.description 
                    for triggered in self.story_state['triggered_events']
                )
                
                if not already_triggered:
                    # Add to the list of triggered events.
                    self.story_state['triggered_events'].append({
                        'event': event,
                        'turn_triggered': self.current_turn_number,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Create the active event description.
                    active_event = {
                        'description': event.description,
                        'character_impact': event.character_impact.get(agent.agent_id, 
                                          event.character_impact.get('all', '')),
                        'environmental_change': event.environmental_change
                    }
                    active_events.append(active_event)
        
        return active_events
    
    def _identify_available_narrative_actions(self, agent: PersonaAgent) -> List[str]:
        """
        Identify narrative actions available to the character in current context.
        
        Args:
            agent: Agent to identify actions for
            
        Returns:
            List of available narrative action names
        """
        available_actions = ['investigate', 'observe_environment']  # Always available
        
        # Add actions based on story state.
        if self.story_state['investigation_count'] > 0:
            available_actions.append('analyze_data')
        
        if len(self.registered_agents) > 1:
            available_actions.extend(['dialogue', 'communicate_faction'])
        
        # Add actions based on character traits.
        personality_traits = agent.personality_traits
        decision_weights = agent.decision_weights
        
        if decision_weights.get('personal_relationships', 0) > 0.6:
            available_actions.append('diplomacy')
        
        if personality_traits.get('aggressive', 0) < 0.3 and personality_traits.get('cautious', 0) > 0.6:
            available_actions.append('search_area')
        
        # Remove duplicates and return.
        return list(set(available_actions))
    
    def _store_turn_in_history(self, turn_summary: Dict[str, Any]) -> None:
        """
        Store turn summary in world state history for future reference.
        
        Maintains a history of all turns for analysis and potential AI integration.
        Implements memory management to prevent unbounded growth.
        
        Args:
            turn_summary: Complete turn summary data to store
        """
        try:
            # Initialize turn history if it doesn't exist.
            if 'turn_history' not in self.world_state_data:
                self.world_state_data['turn_history'] = []
            
            # Add the turn data to the history.
            self.world_state_data['turn_history'].append(turn_summary)
            
            # Implement memory management - keep only configured number of turns
            max_history_length = self.max_turn_history
            if len(self.world_state_data['turn_history']) > max_history_length:
                self.world_state_data['turn_history'] = self.world_state_data['turn_history'][-max_history_length:]
                logger.info(f"Turn history trimmed to last {max_history_length} turns")
            
            logger.debug(f"Turn {turn_summary['turn_number']} stored in history")
            
        except Exception as e:
            logger.error(f"Failed to store turn in history: {str(e)}")
    
    # Utility methods for director management and debugging
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information about the current simulation state.
        
        Returns:
            Dict containing detailed simulation status information
        """
        current_time = datetime.now()
        simulation_duration = (current_time - self.simulation_start_time).total_seconds()
        
        # Calculate agent statistics
        agent_stats = {}
        for agent in self.registered_agents:
            character_name = agent.character_data.get('name', 'Unknown')
            faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
            agent_stats[agent.agent_id] = {
                'name': character_name,
                'faction': faction,
                'status': agent.current_status,
                'morale': agent.morale_level,
            }
        
        return {
            'simulation_info': {
                'start_time': self.simulation_start_time.isoformat(),
                'current_time': current_time.isoformat(),
                'duration_seconds': simulation_duration,
                'current_turn': self.current_turn_number,
                'total_actions_processed': self.total_actions_processed,
            },
            'agents': {
                'total_registered': len(self.registered_agents),
                'agent_details': agent_stats,
            },
            'system_health': {
                'error_count': self.error_count,
                'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
                'campaign_log_path': self.campaign_log_path,
                'world_state_file': self.world_state_file_path,
            },
            'world_state': {
                'locations_tracked': len(self.world_state_data.get('locations', {})),
                'factions_tracked': len(self.world_state_data.get('factions', {})),
                'turn_history_length': len(self.world_state_data.get('turn_history', [])),
            }
        }
    
    def get_agent_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all registered agents with basic information.
        
        Returns:
            List of dictionaries containing agent information
        """
        agent_list = []
        for agent in self.registered_agents:
            character_name = agent.character_data.get('name', 'Unknown')
            faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
            
            agent_list.append({
                'agent_id': agent.agent_id,
                'character_name': character_name,
                'faction': faction,
                'status': agent.current_status,
            })
        
        return agent_list
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the simulation.
        
        Args:
            agent_id: ID of the agent to remove
            
        Returns:
            bool: True if agent was found and removed, False otherwise
        """
        try:
            for i, agent in enumerate(self.registered_agents):
                if agent.agent_id == agent_id:
                    removed_agent = self.registered_agents.pop(i)
                    character_name = removed_agent.character_data.get('name', 'Unknown')
                    
                    logger.info(f"Agent removed: {agent_id} ({character_name})")
                    
                    # Log removal event
                    removal_event = (
                        f"**Agent Departure:** {character_name} ({agent_id}) left the simulation\\n"
                        f"**Departure Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                        f"**Remaining Agents:** {len(self.registered_agents)}"
                    )
                    self.log_event(removal_event)
                    
                    return True
            
            logger.warning(f"Agent not found for removal: {agent_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error removing agent {agent_id}: {str(e)}")
            return False
    
    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save current world state to file.
        
        Args:
            file_path: Optional path to save to (uses default if None)
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            save_path = file_path or self.world_state_file_path or "world_state_backup.json"
            
            # Add current timestamp to world state
            self.world_state_data['last_saved'] = datetime.now().isoformat()
            self.world_state_data['save_info'] = {
                'turn_number': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'total_actions': self.total_actions_processed,
            }
            
            with open(save_path, 'w', encoding='utf-8') as file:
                json.dump(self.world_state_data, file, indent=2, ensure_ascii=False)
            
            logger.info(f"World state saved to: {save_path}")
            self.log_event(f"World state saved to {save_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save world state: {str(e)}")
            return False
    
    def close_campaign_log(self) -> None:
        """
        Properly close the campaign log with summary information.
        
        Adds final summary statistics and closing information to the campaign log.
        Should be called when simulation ends or director is being shut down.
        """
        try:
            end_time = datetime.now()
            simulation_duration = (end_time - self.simulation_start_time).total_seconds()
            
            closing_summary = f"""

## Campaign Summary

**Simulation End Time:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}  
**Total Duration:** {simulation_duration:.2f} seconds ({simulation_duration/60:.1f} minutes)  
**Turns Executed:** {self.current_turn_number}  
**Total Actions Processed:** {self.total_actions_processed}  
**Agents Participated:** {len(self.registered_agents)}  
**System Errors:** {self.error_count}  

### Final Agent Roster

"""
            
            for agent in self.registered_agents:
                character_name = agent.character_data.get('name', 'Unknown')
                faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
                closing_summary += f"- **{character_name}** ({agent.agent_id}) - {faction}\\n"
            
            closing_summary += """

**Campaign Status:** Simulation completed successfully  
**Log Generated By:** DirectorAgent v1.0 - Warhammer 40k Multi-Agent Simulator  

---

*For the Emperor! In the grim darkness of the far future, there is only war...*
"""
            
            with open(self.campaign_log_path, 'a', encoding='utf-8') as file:
                file.write(closing_summary)
            
            logger.info("Campaign log closed with summary")
            
        except Exception as e:
            logger.error(f"Failed to close campaign log properly: {str(e)}")
    
    def _process_narrative_action(self, action: 'CharacterAction', agent: 'PersonaAgent') -> Optional['NarrativeOutcome']:
        """
        Process narrative actions and generate story-driven outcomes.
        
        This method handles story actions like investigation, dialogue, diplomacy, and betrayal
        by using the narrative action resolver to create meaningful story consequences.
        
        Args:
            action: The character action to process
            agent: The agent who performed the action
            
        Returns:
            NarrativeOutcome if the action is narrative-based, None otherwise
        """
        if not hasattr(action, 'action_type'):
            return None
        
        # Check if this is a narrative action
        narrative_action_types = ['investigate', 'dialogue', 'diplomacy', 'betrayal', 
                                 'observe_environment', 'communicate_faction']
        
        if action.action_type not in narrative_action_types:
            return None
        
        logger.info(f"Processing narrative action: {action.action_type} by {agent.agent_id}")
        
        # Get character data for narrative processing
        character_data = {
            'agent_id': agent.agent_id,
            'name': agent.character_data.get('name', 'Unknown'),
            'faction': agent.character_data.get('faction', 'Unknown'),
            'personality_traits': agent.personality_traits,
            'decision_weights': agent.decision_weights
        }
        
        # Get current world state for context
        world_state = {
            'current_turn': self.current_turn_number,
            'story_state': self.story_state,
            'campaign_brief': self.campaign_brief
        }
        
        # Use narrative resolver to process the action
        try:
            if action.action_type == 'investigate':
                outcome = self.narrative_resolver.resolve_investigate_action(action, character_data, world_state)
            elif action.action_type == 'dialogue':
                outcome = self.narrative_resolver.resolve_dialogue_action(action, character_data, world_state)
            elif action.action_type == 'diplomacy':
                outcome = self.narrative_resolver.resolve_diplomacy_action(action, character_data, world_state)
            elif action.action_type == 'betrayal':
                outcome = self.narrative_resolver.resolve_betrayal_action(action, character_data, world_state)
            else:
                # Handle other narrative actions as investigation-type
                outcome = self.narrative_resolver.resolve_investigate_action(action, character_data, world_state)
            
            return outcome
            
        except Exception as e:
            logger.error(f"Error processing narrative action {action.action_type}: {str(e)}")
            return None
    
    def _update_story_state(self, narrative_outcome: 'NarrativeOutcome') -> None:
        """
        Update the story state based on narrative action outcomes.
        
        This method processes the consequences of narrative actions and updates
        the ongoing story progression markers and character relationships.
        
        Args:
            narrative_outcome: The outcome of a narrative action to process
        """
        try:
            # Update story progression markers
            for advancement in narrative_outcome.story_advancement:
                if advancement not in self.story_state['story_progression']:
                    self.story_state['story_progression'].append(advancement)
                    logger.info(f"Story advancement: {advancement}")
            
            # Update character relationships
            for character, change in narrative_outcome.relationship_changes.items():
                if character not in self.story_state['character_relationships']:
                    self.story_state['character_relationships'][character] = 0.0
                
                self.story_state['character_relationships'][character] += change
                logger.info(f"Relationship change: {character} {change:+.2f} (now {self.story_state['character_relationships'][character]:.2f})")
            
            # Track investigation count for event triggers
            if 'investigation' in str(narrative_outcome.description).lower():
                self.story_state['investigation_count'] += 1
            
            # Track dialogue count for event triggers
            if 'dialogue' in str(narrative_outcome.description).lower() or 'communication' in str(narrative_outcome.description).lower():
                self.story_state['dialogue_count'] += 1
            
            # Update story phase based on progression
            total_investigations = self.story_state['investigation_count']
            total_dialogues = self.story_state['dialogue_count']
            
            if total_investigations >= 3 and self.story_state['current_phase'] == 'initialization':
                self.story_state['current_phase'] = 'investigation_phase'
                logger.info("Story phase advanced to: investigation_phase")
            
            if total_dialogues >= 2 and total_investigations >= 2:
                self.story_state['current_phase'] = 'interaction_phase'
                logger.info("Story phase advanced to: interaction_phase")
                
        except Exception as e:
            logger.error(f"Error updating story state: {str(e)}")
    
    def _process_action_world_impact(self, action: 'CharacterAction', agent: 'PersonaAgent') -> None:
        """
        Process Agent action and update world state tracker accordingly.
        
        This method analyzes PersonaAgent actions and updates the world_state_tracker
        to reflect the impact of actions on the world. Creates discoverable content
        for investigation actions and tracks environmental changes.
        
        Args:
            action: The character action being processed
            agent: The agent who performed the action
        """
        if not hasattr(action, 'action_type'):
            return
        
        try:
            action_type = action.action_type.lower()
            agent_id = agent.agent_id
            character_name = agent.character_data.get('name', 'Unknown')
            current_turn = self.current_turn_number
            timestamp = datetime.now().isoformat()
            
            # Process investigation-type actions to generate discoverable clues.
            if action_type in ['investigate', 'search', 'analyze', 'explore']:
                self._process_investigation_impact(action, agent_id, character_name, current_turn, timestamp)
            
            # Record all actions to history.
            self._record_action_to_history(action, agent_id, character_name, current_turn, timestamp)
            
            logger.info(f"World state updated for {action_type} action by {character_name}")
            
        except Exception as e:
            logger.error(f"Error processing action world impact: {str(e)}")
    
    def _process_investigation_impact(self, action: 'CharacterAction', agent_id: str, 
                                    character_name: str, turn_number: int, timestamp: str) -> None:
        """
        Process investigation-type actions and generate discoverable clues.
        
        Args:
            action: The investigation action
            agent_id: ID of the investigating agent
            character_name: Name of the investigating character
            turn_number: Current turn number
            timestamp: Action timestamp
        """
        target = action.target or 'unknown_area'
        
        # Generate clue content based on the target.
        clue_content = self._generate_clue_content(target, character_name, action.action_type)
        
        # Update discovered clues.
        if agent_id not in self.world_state_tracker['discovered_clues']:
            self.world_state_tracker['discovered_clues'][agent_id] = []
        
        clue_entry = {
            'content': clue_content,
            'target': target,
            'turn_discovered': turn_number,
            'timestamp': timestamp,
            'discoverer': character_name
        }
        
        self.world_state_tracker['discovered_clues'][agent_id].append(clue_entry)
        
        # Update agent discoveries record.
        if turn_number not in self.world_state_tracker['agent_discoveries']:
            self.world_state_tracker['agent_discoveries'][turn_number] = {}
        
        if agent_id not in self.world_state_tracker['agent_discoveries'][turn_number]:
            self.world_state_tracker['agent_discoveries'][turn_number][agent_id] = []
        
        self.world_state_tracker['agent_discoveries'][turn_number][agent_id].append(clue_content)
        
        # Update environmental changes.
        location = target
        if location not in self.world_state_tracker['environmental_changes']:
            self.world_state_tracker['environmental_changes'][location] = []
        
        environmental_change = f"Signs of {character_name}'s investigation are visible"
        self.world_state_tracker['environmental_changes'][location].append({
            'change': environmental_change,
            'turn': turn_number,
            'agent': character_name,
            'timestamp': timestamp
        })
        
        logger.info(f"Generated clue for {character_name}: {clue_content}")
    
    def _generate_clue_content(self, target: str, character_name: str, action_type: str) -> str:
        """
        Generate contextual clue content based on investigation target and character.
        
        Args:
            target: The target being investigated
            character_name: Name of the investigating character  
            action_type: Type of investigation action
            
        Returns:
            Generated clue content string
        """
        # Basic clue templates.
        clue_templates = [
            f"Strange markings found on {target}",
            f"Hidden compartment discovered within {target}",
            f"Unusual energy readings detected from {target}",
            f"Fragmentary data logs recovered from {target}",
            f"Traces of recent activity around {target}",
            f"Concealed passage revealed behind {target}",
            f"Mysterious symbols etched into {target}",
            f"Evidence of tampering discovered on {target}"
        ]
        
        # Adjust clues based on action type.
        if action_type == 'analyze':
            analysis_clues = [
                f"Pattern analysis reveals {target} was modified recently",
                f"Chemical residue on {target} suggests Imperial presence",
                f"Structural damage to {target} indicates forced entry",
                f"Data corruption in {target} appears to be intentional"
            ]
            clue_templates.extend(analysis_clues)
        
        elif action_type == 'search':
            search_clues = [
                f"Careful search of {target} reveals hidden cache",
                f"Thorough examination of {target} uncovers secret mechanism",
                f"Methodical search discovers concealed items in {target}",
                f"Detailed search reveals unauthorized modifications to {target}"
            ]
            clue_templates.extend(search_clues)
        
        # Select a random clue template.
        import random
        selected_clue = random.choice(clue_templates)
        
        return selected_clue
    
    def _record_action_to_history(self, action: 'CharacterAction', agent_id: str,
                                character_name: str, turn_number: int, timestamp: str) -> None:
        """
        Record action to investigation history for tracking.
        
        Args:
            action: The action being recorded
            agent_id: ID of the acting agent
            character_name: Name of the acting character
            turn_number: Current turn number
            timestamp: Action timestamp
        """
        history_entry = {
            'agent_id': agent_id,
            'character_name': character_name,
            'action_type': action.action_type,
            'target': action.target,
            'turn': turn_number,
            'timestamp': timestamp,
            'reasoning': action.reasoning or 'No reasoning provided'
        }
        
        self.world_state_tracker['investigation_history'].append(history_entry)
        
        # Update temporal markers.
        self.world_state_tracker['temporal_markers'][timestamp] = {
            'turn': turn_number,
            'agent': character_name,
            'action': action.action_type,
            'description': f"{character_name} performed {action.action_type} on {action.target or 'unknown'}"
        }

    def _build_turn_brief(self, character_id: str) -> Optional['TurnBrief']:
        """
        Build comprehensive turn briefing for a character including Fog of War filtering and RAG injection.
        
        This method implements the core Turn Brief generation system that provides characters
        with contextual information filtered through Fog of War constraints and enhanced
        with relevant knowledge base information via RAG (Retrieval-Augmented Generation).
        
        Args:
            character_id: ID of the character to generate brief for
            
        Returns:
            TurnBrief object with filtered world view and contextual prompts, or None if character not found
        """
        # Import shared types for Turn Brief generation
        try:
            from src.shared_types import (
                TurnBrief, FilteredWorldView, ContextualPrompt, KnowledgeFragment,
                FogOfWarFilter, InformationFragment, InformationSource, FogOfWarChannel,
                CharacterData, WorldState, ActionType
            )
        except ImportError as e:
            logger.error(f"❌ Failed to import shared types for TurnBrief: {e}")
            return None
        
        # Find the target character agent
        target_agent = None
        for agent in self.agents:
            if agent.character_id == character_id:
                target_agent = agent
                break
        
        if not target_agent:
            logger.warning(f"⚠️ Character {character_id} not found for TurnBrief generation")
            return None
        
        try:
            # Step 1: Apply Fog of War filtering to create character's world view
            filtered_world_view = self._apply_fog_of_war_filtering(character_id, target_agent)
            
            # Step 2: Generate available actions for the character
            available_actions = self._determine_available_actions(target_agent)
            
            # Step 3: Inject relevant knowledge via RAG system
            contextual_prompt = self._build_contextual_prompt_with_rag(target_agent, filtered_world_view)
            
            # Step 4: Generate tactical situation summary
            tactical_situation = self._generate_tactical_situation_summary(target_agent, filtered_world_view)
            
            # Step 5: Determine character objectives and constraints
            objectives = self._extract_character_objectives(target_agent)
            constraints = self._determine_action_constraints(target_agent, filtered_world_view)
            
            # Step 6: Calculate token budget for AI processing
            token_budget = self._calculate_token_budget(target_agent)
            
            # Construct the comprehensive Turn Brief
            turn_brief = TurnBrief(
                character_id=character_id,
                turn_number=self.turn_counter,
                filtered_world_view=filtered_world_view,
                available_actions=available_actions,
                contextual_prompt=contextual_prompt,
                tactical_situation=tactical_situation,
                objectives=objectives,
                constraints=constraints,
                token_budget=token_budget
            )
            
            logger.info(f"✅ Generated TurnBrief for {character_id}: "
                       f"{len(available_actions)} actions, {len(objectives)} objectives")
            
            return turn_brief
            
        except Exception as e:
            logger.error(f"❌ Error generating TurnBrief for {character_id}: {e}")
            return None
    
    def _apply_fog_of_war_filtering(self, character_id: str, agent: 'PersonaAgent') -> 'FilteredWorldView':
        """
        Apply Fog of War filtering to create character's limited view of world state.
        
        Implements information filtering based on character's sensory capabilities,
        position, communication networks, and intel sources. Information is tagged
        with reliability and freshness metrics.
        
        Args:
            character_id: ID of the observing character
            agent: PersonaAgent instance for the character
            
        Returns:
            FilteredWorldView with character's limited information
        """
        from src.shared_types import (
            FilteredWorldView, FogOfWarFilter, WorldEntity, InformationFragment,
            InformationSource, FogOfWarChannel, EntityType
        )
        
        # Create Fog of War filter based on character capabilities
        character_data = self._extract_character_data_from_agent(agent)
        fog_filter = self._create_fog_of_war_filter(character_data)
        
        # Filter visible entities based on range and conditions
        visible_entities = {}
        uncertainty_markers = []
        
        # Extract entities from current world state
        world_entities = self._extract_world_entities_from_state()
        
        for entity_id, entity in world_entities.items():
            if entity_id == character_id:
                # Character always knows their own state perfectly
                visible_entities[entity_id] = entity
                continue
            
            # Calculate visibility based on distance, conditions, and sensors
            visibility_info = self._calculate_entity_visibility(
                character_data, entity, fog_filter
            )
            
            if visibility_info['is_visible']:
                # Apply information degradation based on distance and conditions
                filtered_entity = self._apply_information_degradation(
                    entity, visibility_info
                )
                visible_entities[entity_id] = filtered_entity
            else:
                # Add uncertainty marker for potentially nearby entities
                if visibility_info['uncertainty_level'] > 0.3:
                    uncertainty_markers.append(
                        f"Unknown presence detected in {entity.position} area"
                    )
        
        # Collect available information fragments from various sources
        information_fragments = self._gather_information_fragments(
            character_id, fog_filter, visible_entities
        )
        
        # Create filtered world view
        filtered_world_view = FilteredWorldView(
            observer_id=character_id,
            base_world_state=f"turn_{self.turn_counter}",
            visible_entities=visible_entities,
            known_information=information_fragments,
            uncertainty_markers=uncertainty_markers,
            filter_config=fog_filter
        )
        
        logger.debug(f"🔍 Fog of War applied for {character_id}: "
                    f"{len(visible_entities)} visible entities, "
                    f"{len(information_fragments)} info fragments")
        
        return filtered_world_view
    
    def _build_contextual_prompt_with_rag(self, agent: 'PersonaAgent', 
                                         filtered_world_view: 'FilteredWorldView') -> 'ContextualPrompt':
        """
        Build contextual AI prompt enhanced with RAG knowledge injection.
        
        Retrieves relevant knowledge fragments from the knowledge base based on
        current situation and character context, then constructs comprehensive
        prompt for AI decision-making.
        
        Args:
            agent: PersonaAgent instance
            filtered_world_view: Character's filtered view of the world
            
        Returns:
            ContextualPrompt with RAG-enhanced information
        """
        from src.shared_types import ContextualPrompt, KnowledgeFragment
        
        # Generate base prompt from character sheet and situation
        base_prompt = self._generate_base_character_prompt(agent)
        
        # Extract character-specific context
        character_context = self._build_character_context_summary(agent)
        
        # Generate world state context from filtered view
        world_context = self._build_world_state_context(filtered_world_view)
        
        # Retrieve relevant knowledge fragments via RAG
        injected_knowledge = self._retrieve_relevant_knowledge_rag(
            agent, filtered_world_view
        )
        
        # Generate Fog of War information constraints
        fog_of_war_mask = self._generate_information_constraint_mask(filtered_world_view)
        
        # Estimate token count for the complete prompt
        prompt_tokens = self._estimate_prompt_token_count(
            base_prompt, character_context, world_context, injected_knowledge
        )
        
        contextual_prompt = ContextualPrompt(
            base_prompt=base_prompt,
            character_context=character_context,
            world_context=world_context,
            injected_knowledge=injected_knowledge,
            fog_of_war_mask=fog_of_war_mask,
            prompt_tokens=prompt_tokens
        )
        
        logger.debug(f"🧠 Generated contextual prompt for {agent.character_id}: "
                    f"{len(injected_knowledge)} knowledge fragments, ~{prompt_tokens} tokens")
        
        return contextual_prompt
    
    def _retrieve_relevant_knowledge_rag(self, agent: 'PersonaAgent', 
                                       filtered_world_view: 'FilteredWorldView') -> List['KnowledgeFragment']:
        """
        Retrieve relevant knowledge fragments using RAG (Retrieval-Augmented Generation).
        
        Searches knowledge base for information relevant to current character situation,
        tactical context, and available actions. Uses embedding similarity and
        keyword matching to find most relevant fragments.
        
        Args:
            agent: PersonaAgent instance
            filtered_world_view: Character's current world view
            
        Returns:
            List of relevant KnowledgeFragment objects
        """
        from src.shared_types import KnowledgeFragment
        
        knowledge_fragments = []
        
        try:
            # Extract key context for RAG retrieval
            context_keywords = self._extract_rag_context_keywords(agent, filtered_world_view)
            
            # Search knowledge base directories
            kb_path = Path("private/knowledge_base")
            if not kb_path.exists():
                logger.warning("⚠️ Knowledge base not found, creating minimal fragments")
                return self._create_default_knowledge_fragments(agent)
            
            # Search tactical knowledge
            tactical_fragments = self._search_tactical_knowledge(context_keywords, kb_path)
            knowledge_fragments.extend(tactical_fragments)
            
            # Search character-specific lore
            lore_fragments = self._search_character_lore(agent, kb_path)
            knowledge_fragments.extend(lore_fragments)
            
            # Search situational guidance
            situation_fragments = self._search_situational_guidance(
                filtered_world_view, context_keywords, kb_path
            )
            knowledge_fragments.extend(situation_fragments)
            
            # Search rules and constraints
            rules_fragments = self._search_rules_knowledge(context_keywords, kb_path)
            knowledge_fragments.extend(rules_fragments)
            
            # Rank fragments by relevance and limit to top selections
            ranked_fragments = self._rank_knowledge_fragments(
                knowledge_fragments, context_keywords
            )
            
            # Limit to top 10 most relevant fragments to manage token usage
            final_fragments = ranked_fragments[:10]
            
            logger.debug(f"📚 RAG retrieval for {agent.character_id}: "
                        f"{len(final_fragments)} relevant fragments selected")
            
            return final_fragments
            
        except Exception as e:
            logger.error(f"❌ RAG retrieval failed for {agent.character_id}: {e}")
            return self._create_default_knowledge_fragments(agent)
    
    def _create_default_knowledge_fragments(self, agent: 'PersonaAgent') -> List['KnowledgeFragment']:
        """Create default knowledge fragments when RAG system is unavailable."""
        from src.shared_types import KnowledgeFragment
        
        return [
            KnowledgeFragment(
                content="Maintain tactical awareness of surroundings and potential threats",
                source="default_tactical_knowledge",
                relevance_score=0.8,
                knowledge_type="tactical_guidance",
                tags=["tactics", "awareness", "combat"]
            ),
            KnowledgeFragment(
                content="Follow chain of command and coordinate with fellow soldiers",
                source="default_military_doctrine",
                relevance_score=0.7,
                knowledge_type="doctrine",
                tags=["command", "coordination", "teamwork"]
            ),
            KnowledgeFragment(
                content="Preserve ammunition and equipment, use resources efficiently",
                source="default_logistics_guidance",
                relevance_score=0.6,
                knowledge_type="logistics",
                tags=["resources", "equipment", "efficiency"]
            )
        ]

    # Helper methods for TurnBrief generation system
    
    def _extract_character_data_from_agent(self, agent: 'PersonaAgent') -> Optional['CharacterData']:
        """Extract CharacterData from PersonaAgent for Fog of War filtering."""
        from src.shared_types import CharacterData, CharacterStats, CharacterResources, Position, ResourceValue
        try:
            # Mock character data extraction - would integrate with agent's character sheet
            return CharacterData(
                character_id=agent.character_id,
                name=getattr(agent, 'character_name', agent.character_id),
                faction="Imperial Guard",  # Default faction
                position=Position(x=100.0, y=100.0, z=0.0),  # Default position
                stats=CharacterStats(strength=5, dexterity=5, intelligence=5, 
                                   willpower=5, perception=5, charisma=5),
                resources=CharacterResources(
                    health=ResourceValue(current=100, maximum=100),
                    stamina=ResourceValue(current=100, maximum=100),
                    morale=ResourceValue(current=100, maximum=100)
                )
            )
        except Exception:
            return None
    
    def _create_fog_of_war_filter(self, character_data: Optional['CharacterData']) -> 'FogOfWarFilter':
        """Create Fog of War filter configuration for character."""
        from src.shared_types import FogOfWarFilter, FogOfWarChannel
        
        if not character_data:
            # Default filter for unknown characters
            return FogOfWarFilter(
                observer_id="unknown",
                visual_range=10.0,
                radio_range=50.0,
                intel_range=100.0,
                sensor_range=25.0,
                rumor_reliability=0.3
            )
        
        return FogOfWarFilter(
            observer_id=character_data.character_id,
            visual_range=20.0 + (character_data.stats.perception * 2),
            radio_range=100.0,  # Standard radio range
            intel_range=200.0 + (character_data.stats.intelligence * 10),
            sensor_range=50.0 + (character_data.stats.perception * 5),
            rumor_reliability=0.4 + (character_data.stats.charisma * 0.1),
            channel_preferences={
                FogOfWarChannel.VISUAL: 1.0,
                FogOfWarChannel.RADIO: 0.8,
                FogOfWarChannel.INTEL: 0.6,
                FogOfWarChannel.SENSOR: 0.9,
                FogOfWarChannel.RUMOR: 0.3
            }
        )
    
    def _extract_world_entities_from_state(self) -> Dict[str, 'WorldEntity']:
        """Extract world entities from current simulation state."""
        from src.shared_types import WorldEntity, EntityType, Position
        
        entities = {}
        
        # Add all registered agents as character entities
        for agent in self.agents:
            entities[agent.character_id] = WorldEntity(
                entity_id=agent.character_id,
                entity_type=EntityType.CHARACTER,
                name=getattr(agent, 'character_name', agent.character_id),
                position=Position(x=100.0, y=100.0),  # Default position
                properties={
                    'faction': 'Imperial Guard',
                    'status': 'active',
                    'last_action': getattr(agent, 'last_action', 'unknown')
                },
                visibility=1.0
            )
        
        # Add environmental entities from world state if available
        if hasattr(self, 'world_state') and self.world_state:
            # Would extract from actual world state database
            pass
            
        return entities
    
    def _calculate_entity_visibility(self, observer: Optional['CharacterData'], 
                                   entity: 'WorldEntity', fog_filter: 'FogOfWarFilter') -> Dict[str, Any]:
        """Calculate visibility of an entity for the observer."""
        if not observer or not observer.position:
            return {'is_visible': False, 'uncertainty_level': 0.0}
        
        # Calculate distance between observer and entity
        if entity.position:
            distance = ((observer.position.x - entity.position.x) ** 2 + 
                       (observer.position.y - entity.position.y) ** 2) ** 0.5
        else:
            distance = float('inf')
        
        # Check visibility based on range
        is_visible = distance <= fog_filter.visual_range
        
        # Calculate uncertainty based on distance and conditions
        if distance <= fog_filter.visual_range:
            uncertainty_level = min(distance / fog_filter.visual_range, 1.0)
        else:
            uncertainty_level = min(0.8, distance / fog_filter.sensor_range)
        
        return {
            'is_visible': is_visible,
            'distance': distance,
            'uncertainty_level': uncertainty_level,
            'detection_method': 'visual' if is_visible else 'sensor'
        }
    
    def _apply_information_degradation(self, entity: 'WorldEntity', 
                                     visibility_info: Dict[str, Any]) -> 'WorldEntity':
        """Apply information degradation based on visibility conditions."""
        from src.shared_types import WorldEntity
        
        # Create degraded copy of entity
        degraded_properties = entity.properties.copy()
        
        # Apply degradation based on distance and uncertainty
        uncertainty = visibility_info['uncertainty_level']
        if uncertainty > 0.3:
            # Remove detailed information at higher uncertainty
            degraded_properties = {k: v for k, v in degraded_properties.items() 
                                 if k in ['faction', 'status']}
            
        if uncertainty > 0.6:
            # Remove most information at very high uncertainty
            degraded_properties = {'status': 'unknown'}
        
        return WorldEntity(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            name=entity.name if uncertainty < 0.5 else "Unknown Entity",
            position=entity.position,
            properties=degraded_properties,
            visibility=max(0.1, entity.visibility - uncertainty)
        )
    
    def _gather_information_fragments(self, character_id: str, fog_filter: 'FogOfWarFilter',
                                    visible_entities: Dict[str, 'WorldEntity']) -> List['InformationFragment']:
        """Gather information fragments from various sources."""
        from src.shared_types import InformationFragment, InformationSource, FogOfWarChannel
        
        fragments = []
        
        # Create information source for the character
        character_source = InformationSource(
            source_id=character_id,
            source_type="personal_observation",
            reliability=0.9,
            access_channels=[FogOfWarChannel.VISUAL, FogOfWarChannel.SENSOR]
        )
        
        # Generate information fragments for visible entities
        for entity_id, entity in visible_entities.items():
            if entity_id != character_id:  # Don't create fragments about self
                fragment = InformationFragment(
                    entity_id=entity_id,
                    information_type="entity_status",
                    content={
                        'name': entity.name,
                        'type': entity.entity_type.value,
                        'position': {'x': entity.position.x, 'y': entity.position.y} if entity.position else None,
                        'properties': entity.properties
                    },
                    source=character_source,
                    channel=FogOfWarChannel.VISUAL,
                    accuracy=entity.visibility,
                    freshness=1.0  # Current turn information
                )
                fragments.append(fragment)
        
        return fragments
    
    def _determine_available_actions(self, agent: 'PersonaAgent') -> List['ActionType']:
        """Determine available actions for the character."""
        from src.shared_types import ActionType
        
        # Standard military actions available to all characters
        standard_actions = [
            ActionType.MOVE,
            ActionType.OBSERVE,
            ActionType.COMMUNICATE,
            ActionType.WAIT
        ]
        
        # Add combat actions if character is combat-ready
        combat_actions = [
            ActionType.ATTACK,
            ActionType.DEFEND,
            ActionType.RETREAT
        ]
        
        # Add special actions based on character capabilities
        special_actions = [
            ActionType.USE_ITEM,
            ActionType.SPECIAL_ABILITY
        ]
        
        # For now, return all basic actions
        return standard_actions + combat_actions
    
    def _generate_tactical_situation_summary(self, agent: 'PersonaAgent', 
                                           filtered_world_view: 'FilteredWorldView') -> str:
        """Generate tactical situation summary."""
        visible_entities = len(filtered_world_view.visible_entities)
        uncertainty_markers = len(filtered_world_view.uncertainty_markers)
        
        situation = f"Current tactical assessment for {agent.character_id}:\n"
        situation += f"- {visible_entities} entities in visual range\n"
        
        if uncertainty_markers > 0:
            situation += f"- {uncertainty_markers} areas of uncertainty detected\n"
        
        # Add threat assessment
        potential_threats = sum(1 for entity in filtered_world_view.visible_entities.values()
                               if entity.entity_type.value == "character" and 
                               entity.entity_id != agent.character_id)
        
        if potential_threats > 0:
            situation += f"- {potential_threats} potential contacts identified\n"
        else:
            situation += "- No immediate threats detected\n"
        
        return situation
    
    def _extract_character_objectives(self, agent: 'PersonaAgent') -> List[str]:
        """Extract character objectives from agent configuration."""
        # Default military objectives
        default_objectives = [
            "Maintain unit cohesion and readiness",
            "Follow orders from command structure",
            "Protect fellow soldiers and civilians"
        ]
        
        # Would extract from character sheet or mission briefing
        return default_objectives
    
    def _determine_action_constraints(self, agent: 'PersonaAgent', 
                                    filtered_world_view: 'FilteredWorldView') -> List[str]:
        """Determine action constraints based on situation."""
        constraints = []
        
        # Standard military constraints
        constraints.extend([
            "Follow rules of engagement",
            "Maintain radio discipline",
            "Preserve ammunition and equipment"
        ])
        
        # Situational constraints
        if len(filtered_world_view.visible_entities) > 5:
            constraints.append("High activity area - exercise caution")
        
        if len(filtered_world_view.uncertainty_markers) > 3:
            constraints.append("Multiple unknown contacts - maintain alertness")
        
        return constraints
    
    def _calculate_token_budget(self, agent: 'PersonaAgent') -> int:
        """Calculate token budget for AI processing."""
        # Base token budget
        base_budget = 2000
        
        # Adjust based on character complexity and situation
        complexity_modifier = 1.0
        
        # Would factor in character sheet complexity, current situation, etc.
        
        return int(base_budget * complexity_modifier)
    
    # RAG system helper methods
    
    def _generate_base_character_prompt(self, agent: 'PersonaAgent') -> str:
        """Generate base character prompt from agent configuration."""
        return f"You are {getattr(agent, 'character_name', agent.character_id)}, " \
               f"an Imperial Guard soldier. Make tactical decisions based on your training, " \
               f"current situation, and available information."
    
    def _build_character_context_summary(self, agent: 'PersonaAgent') -> str:
        """Build character context summary."""
        return f"Character: {getattr(agent, 'character_name', agent.character_id)}\n" \
               f"Role: Imperial Guard Soldier\n" \
               f"Current Status: Active and ready for orders"
    
    def _build_world_state_context(self, filtered_world_view: 'FilteredWorldView') -> str:
        """Build world state context from filtered view."""
        context = f"Current Situation Assessment:\n"
        context += f"- Visible entities: {len(filtered_world_view.visible_entities)}\n"
        context += f"- Information sources: {len(filtered_world_view.known_information)}\n"
        
        if filtered_world_view.uncertainty_markers:
            context += f"- Areas of uncertainty: {len(filtered_world_view.uncertainty_markers)}\n"
            for marker in filtered_world_view.uncertainty_markers[:3]:  # Limit to top 3
                context += f"  • {marker}\n"
        
        return context
    
    def _generate_information_constraint_mask(self, filtered_world_view: 'FilteredWorldView') -> str:
        """Generate information constraint mask for Fog of War."""
        mask = "Information Constraints:\n"
        mask += "- Only act on information you can directly observe or have received through reliable channels\n"
        mask += "- Uncertainty areas should be approached with caution\n"
        
        if filtered_world_view.uncertainty_markers:
            mask += "- The following areas have limited visibility and require careful assessment\n"
        
        return mask
    
    def _extract_rag_context_keywords(self, agent: 'PersonaAgent', 
                                    filtered_world_view: 'FilteredWorldView') -> List[str]:
        """Extract keywords for RAG knowledge retrieval."""
        keywords = ['tactics', 'combat', 'imperial', 'guard']
        
        # Add keywords based on visible entities
        for entity in filtered_world_view.visible_entities.values():
            if entity.entity_type.value == "character":
                keywords.append('personnel')
            elif entity.entity_type.value == "structure":
                keywords.append('fortification')
            
        # Add situational keywords
        if len(filtered_world_view.uncertainty_markers) > 0:
            keywords.extend(['reconnaissance', 'scouting'])
        
        return list(set(keywords))  # Remove duplicates
    
    def _search_tactical_knowledge(self, keywords: List[str], kb_path: Path) -> List['KnowledgeFragment']:
        """Search tactical knowledge in knowledge base."""
        from src.shared_types import KnowledgeFragment
        
        fragments = []
        tactical_path = kb_path / "tactical"
        
        if tactical_path.exists():
            # Would implement actual file search and content extraction
            # For now, return mock tactical knowledge
            fragments.append(KnowledgeFragment(
                content="Maintain overwatch positions when advancing in unknown territory",
                source=str(tactical_path / "movement_doctrine.md"),
                relevance_score=0.8,
                knowledge_type="tactical_doctrine",
                tags=keywords + ["movement", "overwatch"]
            ))
        
        return fragments
    
    def _search_character_lore(self, agent: 'PersonaAgent', kb_path: Path) -> List['KnowledgeFragment']:
        """Search character-specific lore.""" 
        from src.shared_types import KnowledgeFragment
        
        fragments = []
        lore_path = kb_path / "lore"
        
        if lore_path.exists():
            fragments.append(KnowledgeFragment(
                content="The Imperial Guard is humanity's first line of defense against xenos threats",
                source=str(lore_path / "imperial_guard_lore.md"),
                relevance_score=0.7,
                knowledge_type="lore",
                tags=["imperial", "guard", "duty", "humanity"]
            ))
        
        return fragments
    
    def _search_situational_guidance(self, filtered_world_view: 'FilteredWorldView',
                                   keywords: List[str], kb_path: Path) -> List['KnowledgeFragment']:
        """Search situational guidance based on current context."""
        from src.shared_types import KnowledgeFragment
        
        fragments = []
        guidance_path = kb_path / "guidance"
        
        if guidance_path.exists():
            # Determine situation type
            if len(filtered_world_view.uncertainty_markers) > 2:
                fragments.append(KnowledgeFragment(
                    content="In areas with limited visibility, use cautious advance techniques and maintain communication",
                    source=str(guidance_path / "low_visibility_operations.md"),
                    relevance_score=0.9,
                    knowledge_type="tactical_guidance",
                    tags=keywords + ["visibility", "caution"]
                ))
        
        return fragments
    
    def _search_rules_knowledge(self, keywords: List[str], kb_path: Path) -> List['KnowledgeFragment']:
        """Search rules and constraints knowledge."""
        from src.shared_types import KnowledgeFragment
        
        fragments = []
        rules_path = kb_path / "rules"
        
        if rules_path.exists():
            fragments.append(KnowledgeFragment(
                content="Always follow chain of command and coordinate actions with unit members",
                source=str(rules_path / "command_structure.md"),
                relevance_score=0.8,
                knowledge_type="regulations",
                tags=keywords + ["command", "coordination"]
            ))
        
        return fragments
    
    def _rank_knowledge_fragments(self, fragments: List['KnowledgeFragment'], 
                                 keywords: List[str]) -> List['KnowledgeFragment']:
        """Rank knowledge fragments by relevance to current context."""
        # Simple relevance ranking based on keyword matches and base relevance scores
        for fragment in fragments:
            keyword_matches = sum(1 for keyword in keywords if keyword in fragment.tags)
            fragment.relevance_score *= (1 + keyword_matches * 0.1)
        
        # Sort by relevance score descending
        return sorted(fragments, key=lambda f: f.relevance_score, reverse=True)
    
    def _estimate_prompt_token_count(self, base_prompt: str, character_context: str,
                                   world_context: str, knowledge_fragments: List['KnowledgeFragment']) -> int:
        """Estimate token count for the complete prompt."""
        # Simple token estimation (approximately 4 characters per token)
        total_chars = len(base_prompt) + len(character_context) + len(world_context)
        
        # Add knowledge fragments
        for fragment in knowledge_fragments:
            total_chars += len(fragment.content) + 20  # Include formatting overhead
        
        # Add formatting overhead
        total_chars += 500
        
        return int(total_chars / 4)  # Rough token estimation

    def _adjudicate_action(self, proposed_action: 'ProposedAction', agent: 'PersonaAgent') -> 'IronLawsReport':
        """
        Validate proposed action against all 5 Iron Laws of the Novel Engine.
        
        The Iron Laws represent the fundamental constraints that govern all character
        actions in the simulation, ensuring narrative consistency, physical plausibility,
        and game balance. This method provides comprehensive validation with automatic
        repair capabilities for minor violations.
        
        The 5 Iron Laws:
        - E001 Causality Law: Actions must have logical consequences
        - E002 Resource Law: Characters cannot exceed their capabilities/resources  
        - E003 Physics Law: Actions must obey basic physical constraints
        - E004 Narrative Law: Actions must maintain story coherence
        - E005 Social Law: Actions must respect established relationships/hierarchies
        
        Args:
            proposed_action: Action proposed by the character agent
            agent: PersonaAgent instance for context and character data
            
        Returns:
            IronLawsReport with validation results, violations, and repair suggestions
        """
        try:
            from src.shared_types import (
                IronLawsReport, IronLawsViolation, ValidatedAction, ValidationResult
            )
        except ImportError as e:
            logger.error(f"❌ Failed to import Iron Laws types: {e}")
            return None
        
        start_time = datetime.now()
        logger.info(f"🔍 Iron Laws adjudication started for action {proposed_action.action_id}")
        
        # Initialize validation tracking
        all_violations = []
        checks_performed = []
        repair_attempts = []
        
        try:
            # Extract character data and world context for validation
            character_data = self._extract_character_data_from_agent(agent)
            world_context = self._get_current_world_context()
            
            # Execute each Iron Law validation
            e001_violations = self._validate_causality_law(proposed_action, character_data, world_context)
            all_violations.extend(e001_violations)
            checks_performed.append("E001_Causality_Law")
            
            e002_violations = self._validate_resource_law(proposed_action, character_data)
            all_violations.extend(e002_violations)
            checks_performed.append("E002_Resource_Law")
            
            e003_violations = self._validate_physics_law(proposed_action, character_data, world_context)
            all_violations.extend(e003_violations)
            checks_performed.append("E003_Physics_Law")
            
            e004_violations = self._validate_narrative_law(proposed_action, agent, world_context)
            all_violations.extend(e004_violations)
            checks_performed.append("E004_Narrative_Law")
            
            e005_violations = self._validate_social_law(proposed_action, agent, world_context)
            all_violations.extend(e005_violations)
            checks_performed.append("E005_Social_Law")
            
            # Determine overall validation result
            overall_result = self._determine_overall_validation_result(all_violations)
            
            # Attempt automatic repairs for fixable violations
            final_action = None
            if overall_result in [ValidationResult.INVALID, ValidationResult.REQUIRES_REPAIR]:
                final_action, repair_log = self._attempt_action_repairs(
                    proposed_action, all_violations, character_data
                )
                repair_attempts.extend(repair_log)
                
                # Re-validate repaired action
                if final_action and final_action != proposed_action:
                    logger.info(f"🔧 Re-validating repaired action {final_action.action_id}")
                    # Quick re-validation of critical laws only
                    repair_violations = self._quick_revalidation(final_action, character_data, world_context)
                    if not repair_violations:
                        overall_result = ValidationResult.VALID
                        logger.info(f"✅ Action successfully repaired and validated")
            else:
                final_action = self._convert_proposed_to_validated(proposed_action, ValidationResult.VALID)
            
            # Generate comprehensive Iron Laws report
            report = IronLawsReport(
                action_id=proposed_action.action_id,
                timestamp=start_time,
                overall_result=overall_result,
                violations=all_violations,
                checks_performed=checks_performed,
                repair_attempts=repair_attempts,
                final_action=final_action
            )
            
            # Log validation summary
            duration = (datetime.now() - start_time).total_seconds()
            violation_count = len(all_violations)
            critical_violations = sum(1 for v in all_violations if v.severity == "critical")
            
            logger.info(f"⚖️ Iron Laws adjudication completed in {duration:.3f}s: "
                       f"{violation_count} violations ({critical_violations} critical), "
                       f"result: {overall_result.value}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Iron Laws adjudication failed for action {proposed_action.action_id}: {e}")
            
            # Create error report
            error_report = IronLawsReport(
                action_id=proposed_action.action_id,
                timestamp=start_time,
                overall_result=ValidationResult.CATASTROPHIC_FAILURE,
                violations=[IronLawsViolation(
                    law_code="E000",
                    law_name="System_Error", 
                    severity="critical",
                    description=f"Adjudication system failure: {str(e)}",
                    affected_entities=[agent.character_id],
                    suggested_repair="Manual review required"
                )],
                checks_performed=checks_performed,
                repair_attempts=repair_attempts,
                final_action=None
            )
            
            return error_report

    # Iron Laws validation methods - The 5 fundamental constraints

    def _validate_causality_law(self, action: 'ProposedAction', character_data: Optional['CharacterData'], 
                               world_context: Dict[str, Any]) -> List['IronLawsViolation']:
        """
        E001 Causality Law: Actions must have logical consequences.
        
        Validates that proposed actions have realistic cause-effect relationships
        and don't violate basic logical consistency within the simulation.
        """
        from src.shared_types import IronLawsViolation
        violations = []
        
        # Check for impossible action sequences
        if hasattr(action, 'prerequisites') and action.prerequisites:
            for prereq in action.prerequisites:
                if not self._check_prerequisite_met(prereq, character_data, world_context):
                    violations.append(IronLawsViolation(
                        law_code="E001",
                        law_name="Causality_Law",
                        severity="error",
                        description=f"Action prerequisite not met: {prereq}",
                        affected_entities=[character_data.character_id if character_data else "unknown"],
                        suggested_repair=f"Ensure {prereq} condition is satisfied before attempting action"
                    ))
        
        # Check for logical inconsistencies in action parameters
        if action.action_type.value == "attack" and not action.target:
            violations.append(IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law", 
                severity="critical",
                description="Attack action requires a target",
                affected_entities=[character_data.character_id if character_data else "unknown"],
                suggested_repair="Specify valid target for attack action"
            ))
        
        # Check for temporal consistency
        if hasattr(action, 'duration') and action.parameters.duration and action.parameters.duration < 0:
            violations.append(IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law",
                severity="error", 
                description="Action duration cannot be negative",
                affected_entities=[character_data.character_id if character_data else "unknown"],
                suggested_repair="Set duration to positive value"
            ))
        
        return violations
    
    def _validate_resource_law(self, action: 'ProposedAction', 
                              character_data: Optional['CharacterData']) -> List['IronLawsViolation']:
        """
        E002 Resource Law: Characters cannot exceed their capabilities/resources.
        
        Validates that characters have sufficient resources (health, stamina, ammo, etc.)
        and capabilities (stats, equipment) to perform the proposed action.
        """
        from src.shared_types import IronLawsViolation
        violations = []
        
        if not character_data:
            violations.append(IronLawsViolation(
                law_code="E002",
                law_name="Resource_Law",
                severity="critical",
                description="Cannot validate resources - character data unavailable",
                affected_entities=["unknown"],
                suggested_repair="Ensure character data is properly loaded"
            ))
            return violations
        
        # Check stamina requirements for physically demanding actions
        stamina_cost = self._calculate_action_stamina_cost(action)
        if stamina_cost > 0:
            current_stamina = character_data.resources.stamina.current
            if current_stamina < stamina_cost:
                violations.append(IronLawsViolation(
                    law_code="E002",
                    law_name="Resource_Law",
                    severity="error",
                    description=f"Insufficient stamina: {current_stamina}/{stamina_cost} required",
                    affected_entities=[character_data.character_id],
                    suggested_repair="Rest to recover stamina or choose less demanding action"
                ))
        
        # Check equipment requirements
        required_equipment = self._get_action_equipment_requirements(action)
        available_equipment = {item.name: item for item in character_data.equipment}
        
        for required_item in required_equipment:
            if required_item not in available_equipment:
                violations.append(IronLawsViolation(
                    law_code="E002", 
                    law_name="Resource_Law",
                    severity="error",
                    description=f"Required equipment not available: {required_item}",
                    affected_entities=[character_data.character_id],
                    suggested_repair=f"Acquire {required_item} before attempting action"
                ))
            elif available_equipment[required_item].condition < 0.3:
                violations.append(IronLawsViolation(
                    law_code="E002",
                    law_name="Resource_Law", 
                    severity="warning",
                    description=f"Equipment in poor condition: {required_item} ({available_equipment[required_item].condition:.1%})",
                    affected_entities=[character_data.character_id],
                    suggested_repair=f"Repair or replace {required_item}"
                ))
        
        # Check skill/stat requirements
        required_stats = self._get_action_stat_requirements(action)
        for stat_name, min_value in required_stats.items():
            character_stat = getattr(character_data.stats, stat_name.lower(), 0)
            if character_stat < min_value:
                violations.append(IronLawsViolation(
                    law_code="E002",
                    law_name="Resource_Law",
                    severity="error",
                    description=f"Insufficient {stat_name}: {character_stat}/{min_value} required",
                    affected_entities=[character_data.character_id],
                    suggested_repair=f"Improve {stat_name} or choose action suited to current capabilities"
                ))
        
        return violations
    
    def _validate_physics_law(self, action: 'ProposedAction', character_data: Optional['CharacterData'],
                             world_context: Dict[str, Any]) -> List['IronLawsViolation']:
        """
        E003 Physics Law: Actions must obey basic physical constraints.
        
        Validates that actions respect fundamental physical limitations like distance,
        line of sight, environmental conditions, and basic physics.
        """
        from src.shared_types import IronLawsViolation
        violations = []
        
        if not character_data or not character_data.position:
            return violations  # Cannot validate without position data
        
        # Check movement distance constraints
        if action.action_type.value == "move" and action.target and hasattr(action.target, 'position'):
            if action.target.position:
                distance = self._calculate_distance(character_data.position, action.target.position)
                max_move_distance = self._calculate_max_movement_distance(character_data)
                
                if distance > max_move_distance:
                    violations.append(IronLawsViolation(
                        law_code="E003",
                        law_name="Physics_Law",
                        severity="error",
                        description=f"Movement distance exceeds capability: {distance:.1f}m > {max_move_distance:.1f}m",
                        affected_entities=[character_data.character_id],
                        suggested_repair="Choose closer destination or break movement into multiple turns"
                    ))
        
        # Check line of sight for ranged actions
        if action.action_type.value in ["attack", "observe"] and action.target:
            if not self._check_line_of_sight(character_data.position, action.target, world_context):
                violations.append(IronLawsViolation(
                    law_code="E003",
                    law_name="Physics_Law",
                    severity="error",
                    description="No line of sight to target",
                    affected_entities=[character_data.character_id],
                    suggested_repair="Move to position with clear line of sight or choose different target"
                ))
        
        # Check environmental constraints
        environmental_restrictions = world_context.get('environmental_restrictions', [])
        for restriction in environmental_restrictions:
            if self._action_violates_environmental_restriction(action, character_data, restriction):
                violations.append(IronLawsViolation(
                    law_code="E003",
                    law_name="Physics_Law",
                    severity="warning",
                    description=f"Action restricted by environmental condition: {restriction['type']}",
                    affected_entities=[character_data.character_id],
                    suggested_repair=f"Wait for {restriction['type']} to clear or adapt action"
                ))
        
        # Check for physically impossible actions
        if action.parameters.intensity and action.parameters.intensity > 1.0:
            violations.append(IronLawsViolation(
                law_code="E003",
                law_name="Physics_Law",
                severity="error",
                description=f"Action intensity exceeds maximum: {action.parameters.intensity} > 1.0",
                affected_entities=[character_data.character_id],
                suggested_repair="Reduce action intensity to maximum of 1.0"
            ))
        
        return violations
    
    def _validate_narrative_law(self, action: 'ProposedAction', agent: 'PersonaAgent',
                               world_context: Dict[str, Any]) -> List['IronLawsViolation']:
        """
        E004 Narrative Law: Actions must maintain story coherence.
        
        Validates that actions are consistent with established narrative, character
        personalities, ongoing story arcs, and don't break immersion.
        """
        from src.shared_types import IronLawsViolation
        violations = []
        
        # Check character personality consistency
        character_traits = getattr(agent, 'personality_traits', {})
        if self._action_contradicts_personality(action, character_traits):
            violations.append(IronLawsViolation(
                law_code="E004",
                law_name="Narrative_Law",
                severity="warning",
                description="Action inconsistent with established character personality",
                affected_entities=[agent.character_id],
                suggested_repair="Choose action that aligns with character traits and motivation"
            ))
        
        # Check faction/allegiance consistency  
        if hasattr(agent, 'faction') and action.target:
            target_faction = self._get_target_faction(action.target, world_context)
            if target_faction and self._check_faction_hostility(agent.faction, target_faction):
                if action.action_type.value == "communicate" and action.parameters.modifiers.get('diplomatic', 0) < 0.5:
                    violations.append(IronLawsViolation(
                        law_code="E004",
                        law_name="Narrative_Law",
                        severity="warning",
                        description="Non-diplomatic communication with hostile faction without justification",
                        affected_entities=[agent.character_id],
                        suggested_repair="Add diplomatic context or choose appropriate hostile action"
                    ))
        
        # Check story arc consistency
        current_story_phase = world_context.get('story_phase', 'unknown')
        if current_story_phase == 'stealth_mission' and action.action_type.value == "attack":
            if not action.parameters.modifiers.get('silent', False):
                violations.append(IronLawsViolation(
                    law_code="E004",
                    law_name="Narrative_Law",
                    severity="error",
                    description="Loud attack action violates stealth mission requirements",
                    affected_entities=[agent.character_id],
                    suggested_repair="Use silent attack method or abort stealth approach"
                ))
        
        # Check dialogue/communication appropriateness
        if action.action_type.value == "communicate" and hasattr(action, 'message'):
            if self._contains_inappropriate_content(action.message):
                violations.append(IronLawsViolation(
                    law_code="E004",
                    law_name="Narrative_Law",
                    severity="critical",
                    description="Communication contains inappropriate or immersion-breaking content",
                    affected_entities=[agent.character_id],
                    suggested_repair="Revise message to maintain narrative consistency and appropriateness"
                ))
        
        return violations
    
    def _validate_social_law(self, action: 'ProposedAction', agent: 'PersonaAgent',
                            world_context: Dict[str, Any]) -> List['IronLawsViolation']:
        """
        E005 Social Law: Actions must respect established relationships/hierarchies.
        
        Validates that actions respect military hierarchy, social relationships,
        command structure, and established group dynamics.
        """
        from src.shared_types import IronLawsViolation
        violations = []
        
        # Check command hierarchy
        if action.action_type.value == "communicate" and action.target:
            target_rank = self._get_character_rank(action.target.entity_id, world_context)
            agent_rank = getattr(agent, 'military_rank', 'private')
            
            if self._is_insubordinate_communication(action, agent_rank, target_rank):
                violations.append(IronLawsViolation(
                    law_code="E005",
                    law_name="Social_Law",
                    severity="warning",
                    description=f"Communication may be insubordinate: {agent_rank} to {target_rank}",
                    affected_entities=[agent.character_id],
                    suggested_repair="Modify communication to show appropriate respect for rank"
                ))
        
        # Check unit cohesion
        if action.action_type.value in ["retreat", "abandon"] and not self._has_authorization_to_retreat(agent, world_context):
            violations.append(IronLawsViolation(
                law_code="E005",
                law_name="Social_Law",
                severity="error",
                description="Retreat action without proper authorization compromises unit cohesion",
                affected_entities=[agent.character_id],
                suggested_repair="Obtain authorization from commanding officer or justify emergency retreat"
            ))
        
        # Check friendly fire prevention
        if action.action_type.value == "attack" and action.target:
            target_faction = self._get_target_faction(action.target, world_context)
            agent_faction = getattr(agent, 'faction', 'unknown')
            
            if target_faction == agent_faction:
                violations.append(IronLawsViolation(
                    law_code="E005",
                    law_name="Social_Law",
                    severity="critical", 
                    description="Attack against friendly forces (friendly fire)",
                    affected_entities=[agent.character_id, action.target.entity_id],
                    suggested_repair="Confirm target identity and hostile status before attacking"
                ))
        
        # Check group coordination
        if action.action_type.value == "special_ability" and self._requires_team_coordination(action):
            if not self._has_team_coordination(agent, action, world_context):
                violations.append(IronLawsViolation(
                    law_code="E005",
                    law_name="Social_Law",
                    severity="warning",
                    description="Special action requires team coordination that is not established",
                    affected_entities=[agent.character_id],
                    suggested_repair="Coordinate with team members before executing special action"
                ))
        
        return violations

    # Iron Laws repair system - Automatic action modification

    def _attempt_action_repairs(self, proposed_action: 'ProposedAction', violations: List['IronLawsViolation'], 
                               character_data: Optional['CharacterData']) -> Tuple[Optional['ValidatedAction'], List[str]]:
        """
        Attempt to automatically repair action violations through systematic modification.
        
        Applies law-specific repair strategies to fix violations while preserving
        action intent. Returns repaired action and log of repair attempts.
        
        Args:
            proposed_action: Original action with violations
            violations: List of detected violations to repair
            character_data: Character context for repair calculations
            
        Returns:
            Tuple of (repaired_validated_action, repair_log)
        """
        repair_log = []
        modified_action = proposed_action
        
        try:
            # Group violations by law type for systematic repair
            violations_by_law = self._group_violations_by_law(violations)
            
            # Apply repairs in order of severity and dependency
            repair_order = ['E003', 'E002', 'E001', 'E004', 'E005']  # Physics -> Resources -> Causality -> Narrative -> Social
            
            for law_code in repair_order:
                if law_code in violations_by_law:
                    law_violations = violations_by_law[law_code]
                    
                    if law_code == 'E001':
                        modified_action, causality_repairs = self._repair_causality_violations(
                            modified_action, law_violations
                        )
                        repair_log.extend(causality_repairs)
                    
                    elif law_code == 'E002':
                        modified_action, resource_repairs = self._repair_resource_violations(
                            modified_action, law_violations, character_data
                        )
                        repair_log.extend(resource_repairs)
                    
                    elif law_code == 'E003':
                        modified_action, physics_repairs = self._repair_physics_violations(
                            modified_action, law_violations, character_data
                        )
                        repair_log.extend(physics_repairs)
                    
                    elif law_code == 'E004':
                        modified_action, narrative_repairs = self._repair_narrative_violations(
                            modified_action, law_violations
                        )
                        repair_log.extend(narrative_repairs)
                    
                    elif law_code == 'E005':
                        modified_action, social_repairs = self._repair_social_violations(
                            modified_action, law_violations
                        )
                        repair_log.extend(social_repairs)
            
            # Convert to ValidatedAction if repairs were successful
            if modified_action and repair_log:
                validated_action = self._convert_proposed_to_validated(
                    modified_action, 
                    ValidationResult.VALID if len(repair_log) > 0 else ValidationResult.REQUIRES_REPAIR
                )
                
                logger.info(f"🔧 Action {proposed_action.action_id} repaired: {len(repair_log)} repairs applied")
                return validated_action, repair_log
            else:
                # No repairs possible or no violations requiring repair
                validated_action = self._convert_proposed_to_validated(
                    proposed_action, ValidationResult.INVALID
                )
                repair_log.append("No automatic repairs available for detected violations")
                return validated_action, repair_log
                
        except Exception as e:
            logger.error(f"❌ Repair system failure for action {proposed_action.action_id}: {e}")
            repair_log.append(f"Repair system error: {str(e)}")
            return None, repair_log
    
    def _repair_causality_violations(self, action: 'ProposedAction', 
                                   violations: List['IronLawsViolation']) -> Tuple['ProposedAction', List[str]]:
        """Repair E001 Causality Law violations through logical action modification."""
        repairs_made = []
        modified_action = action
        
        for violation in violations:
            if "Attack action requires a target" in violation.description:
                # Attempt to find valid nearby target
                if hasattr(modified_action, 'target') or not modified_action.target:
                    # Convert to defensive action if no valid target available
                    modified_action.action_type = ActionType.DEFEND
                    repairs_made.append("Converted targetless attack to defensive stance")
            
            elif "duration cannot be negative" in violation.description:
                # Fix negative duration
                if modified_action.parameters.duration and modified_action.parameters.duration < 0:
                    modified_action.parameters.duration = abs(modified_action.parameters.duration)
                    repairs_made.append(f"Corrected negative duration to {modified_action.parameters.duration}")
            
            elif "prerequisite not met" in violation.description:
                # Attempt to modify action to meet prerequisites
                if modified_action.action_type == ActionType.SPECIAL_ABILITY:
                    # Downgrade to basic action
                    modified_action.action_type = ActionType.WAIT
                    repairs_made.append("Downgraded special ability to basic action due to unmet prerequisites")
        
        return modified_action, repairs_made
    
    def _repair_resource_violations(self, action: 'ProposedAction', violations: List['IronLawsViolation'],
                                  character_data: Optional['CharacterData']) -> Tuple['ProposedAction', List[str]]:
        """Repair E002 Resource Law violations through resource-aware action scaling."""
        repairs_made = []
        modified_action = action
        
        if not character_data:
            return action, ["Cannot repair resource violations - character data unavailable"]
        
        for violation in violations:
            if "Insufficient stamina" in violation.description:
                # Scale down action intensity to match available stamina
                current_stamina = character_data.resources.stamina.current
                required_stamina = self._calculate_action_stamina_cost(action)
                
                if required_stamina > 0 and current_stamina > 0:
                    stamina_ratio = min(current_stamina / required_stamina, 1.0)
                    modified_action.parameters.intensity *= stamina_ratio
                    repairs_made.append(f"Reduced action intensity to {modified_action.parameters.intensity:.2f} to match available stamina")
                else:
                    # Convert to less demanding action
                    modified_action.action_type = ActionType.WAIT
                    repairs_made.append("Converted action to rest due to insufficient stamina")
            
            elif "Required equipment not available" in violation.description:
                # Find alternative action that doesn't require missing equipment
                missing_equipment = self._extract_missing_equipment_from_violation(violation)
                alternative_action = self._find_equipment_alternative(modified_action, missing_equipment)
                if alternative_action:
                    modified_action.action_type = alternative_action
                    repairs_made.append(f"Changed action to {alternative_action.value} - no equipment required")
            
            elif "Insufficient" in violation.description and any(stat in violation.description.lower() 
                                                               for stat in ['strength', 'dexterity', 'intelligence']):
                # Scale action based on character capabilities
                modified_action.parameters.intensity *= 0.7  # Reduce intensity for capability mismatch
                repairs_made.append("Reduced action intensity to match character capabilities")
        
        return modified_action, repairs_made
    
    def _repair_physics_violations(self, action: 'ProposedAction', violations: List['IronLawsViolation'],
                                 character_data: Optional['CharacterData']) -> Tuple['ProposedAction', List[str]]:
        """Repair E003 Physics Law violations through physical constraint adjustment."""
        repairs_made = []
        modified_action = action
        
        for violation in violations:
            if "Movement distance exceeds capability" in violation.description:
                # Scale movement to maximum possible distance
                if character_data and character_data.position and action.target and hasattr(action.target, 'position'):
                    max_distance = self._calculate_max_movement_distance(character_data)
                    current_distance = self._calculate_distance(character_data.position, action.target.position)
                    
                    if current_distance > max_distance:
                        # Scale target position to maximum reachable distance
                        scale_factor = max_distance / current_distance
                        # Move proportionally toward target
                        repairs_made.append(f"Reduced movement distance to maximum capability: {max_distance:.1f}m")
            
            elif "No line of sight" in violation.description:
                # Convert ranged action to movement toward target
                if action.action_type in [ActionType.ATTACK, ActionType.OBSERVE]:
                    modified_action.action_type = ActionType.MOVE
                    repairs_made.append("Converted ranged action to movement due to line of sight obstruction")
            
            elif "intensity exceeds maximum" in violation.description:
                # Cap intensity at maximum allowable value
                modified_action.parameters.intensity = 1.0
                repairs_made.append("Capped action intensity at maximum value (1.0)")
            
            elif "environmental condition" in violation.description:
                # Reduce action effectiveness for environmental constraints
                modified_action.parameters.intensity *= 0.5
                repairs_made.append("Reduced action effectiveness due to environmental constraints")
        
        return modified_action, repairs_made
    
    def _repair_narrative_violations(self, action: 'ProposedAction', 
                                   violations: List['IronLawsViolation']) -> Tuple['ProposedAction', List[str]]:
        """Repair E004 Narrative Law violations through story-consistent modification."""
        repairs_made = []
        modified_action = action
        
        for violation in violations:
            if "personality" in violation.description.lower():
                # Add personality-consistent modifiers
                if not hasattr(modified_action.parameters, 'modifiers'):
                    modified_action.parameters.modifiers = {}
                modified_action.parameters.modifiers['personality_adjusted'] = True
                repairs_made.append("Added personality-consistent action modifiers")
            
            elif "stealth mission" in violation.description:
                # Make action stealthy
                if not hasattr(modified_action.parameters, 'modifiers'):
                    modified_action.parameters.modifiers = {}
                modified_action.parameters.modifiers['silent'] = True
                modified_action.parameters.intensity *= 0.7  # Reduce intensity for stealth
                repairs_made.append("Modified action for stealth requirements")
            
            elif "inappropriate content" in violation.description:
                # This requires manual intervention - cannot automatically repair
                repairs_made.append("WARNING: Communication content requires manual review")
        
        return modified_action, repairs_made
    
    def _repair_social_violations(self, action: 'ProposedAction', 
                                violations: List['IronLawsViolation']) -> Tuple['ProposedAction', List[str]]:
        """Repair E005 Social Law violations through hierarchy-aware modification."""
        repairs_made = []
        modified_action = action
        
        for violation in violations:
            if "insubordinate" in violation.description.lower():
                # Add respectful communication modifiers
                if not hasattr(modified_action.parameters, 'modifiers'):
                    modified_action.parameters.modifiers = {}
                modified_action.parameters.modifiers['respectful'] = True
                repairs_made.append("Added respectful communication tone")
            
            elif "friendly fire" in violation.description:
                # Critical violation - convert to non-hostile action
                if modified_action.action_type == ActionType.ATTACK:
                    modified_action.action_type = ActionType.COMMUNICATE
                    repairs_made.append("CRITICAL REPAIR: Converted friendly fire attack to communication")
            
            elif "retreat" in violation.description and "authorization" in violation.description:
                # Convert unauthorized retreat to defensive position
                if modified_action.action_type == ActionType.RETREAT:
                    modified_action.action_type = ActionType.DEFEND
                    repairs_made.append("Converted unauthorized retreat to defensive stance")
            
            elif "team coordination" in violation.description:
                # Add coordination delay
                modified_action.parameters.duration *= 1.5  # Extra time for coordination
                if not hasattr(modified_action.parameters, 'modifiers'):
                    modified_action.parameters.modifiers = {}
                modified_action.parameters.modifiers['coordinated'] = True
                repairs_made.append("Added team coordination requirements")
        
        return modified_action, repairs_made
    
    def _convert_proposed_to_validated(self, proposed_action: 'ProposedAction', iron_laws_report: Dict[str, Any]) -> 'ValidatedAction':
        """
        Convert a ProposedAction to ValidatedAction after Iron Laws validation.
        
        Creates a ValidatedAction with the validation results and any repairs
        that were applied during the Iron Laws adjudication process.
        
        Args:
            proposed_action: The original proposed action
            iron_laws_report: Iron Laws validation and repair report
            
        Returns:
            ValidatedAction with validation results
        """
        try:
            # Import ValidatedAction if available
            from src.shared_types import ValidatedAction, ValidationStatus
            
            # Determine validation status
            validation_result = iron_laws_report.get('validation_result', 'UNKNOWN')
            if validation_result == 'APPROVED':
                status = ValidationStatus.APPROVED
            elif validation_result == 'APPROVED_WITH_WARNINGS':
                status = ValidationStatus.APPROVED_WITH_WARNINGS
            elif validation_result == 'REQUIRES_REPAIR':
                status = ValidationStatus.REQUIRES_REPAIR
            elif validation_result == 'REJECTED':
                status = ValidationStatus.REJECTED
            else:
                status = ValidationStatus.PENDING
            
            # Use repaired action if available, otherwise original
            final_action = iron_laws_report.get('repaired_action', proposed_action)
            
            validated_action = ValidatedAction(
                action_id=final_action.action_id,
                original_action_id=proposed_action.action_id,
                action_type=final_action.action_type,
                target=final_action.target,
                agent_id=final_action.agent_id,
                parameters=final_action.parameters,
                reasoning=final_action.reasoning,
                validation_status=status,
                violations_found=iron_laws_report.get('violations_found', []),
                repair_attempts=iron_laws_report.get('repair_attempts', []),
                processing_time=iron_laws_report.get('processing_time', 0.0),
                validated_at=datetime.now()
            )
            
            logger.debug(f"✅ Converted proposed action {proposed_action.action_id} to validated action with status {status}")
            return validated_action
            
        except ImportError:
            logger.warning("⚠️ ValidatedAction not available, creating mock validated action")
            # Create a basic mock if ValidatedAction not available
            mock_validated = type('ValidatedAction', (), {
                'action_id': proposed_action.action_id,
                'validation_status': validation_result,
                'violations_found': iron_laws_report.get('violations_found', []),
                'processing_time': iron_laws_report.get('processing_time', 0.0)
            })
            return mock_validated
        
        except Exception as e:
            logger.error(f"❌ Error converting proposed to validated action: {e}")
            # Return a basic result on error
            return type('ValidatedAction', (), {
                'action_id': getattr(proposed_action, 'action_id', 'unknown'),
                'validation_status': 'ERROR',
                'violations_found': [],
                'processing_time': 0.0
            })
    
    # Iron Laws helper methods for validation and repair system support
    
    def _group_violations_by_law(self, violations: List['IronLawsViolation']) -> Dict[str, List['IronLawsViolation']]:
        """
        Group violations by their Iron Law code for organized repair processing.
        
        Args:
            violations: List of Iron Laws violations to group
            
        Returns:
            Dictionary mapping law codes to their violations
        """
        grouped_violations = {}
        for violation in violations:
            law_code = violation.law_code
            if law_code not in grouped_violations:
                grouped_violations[law_code] = []
            grouped_violations[law_code].append(violation)
        
        logger.debug(f"🏷️ Grouped {len(violations)} violations into {len(grouped_violations)} law categories")
        return grouped_violations
    
    def _get_current_world_context(self) -> Dict[str, Any]:
        """
        Get current world context for Iron Laws validation.
        
        Provides comprehensive world state information needed for Iron Laws
        validation including environmental conditions, narrative state, and
        character relationships.
        
        Returns:
            Dictionary containing current world context information
        """
        try:
            world_context = {
                # Basic simulation state
                'current_turn': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'active_agents': [agent.agent_id for agent in self.registered_agents],
                
                # Environmental conditions
                'environment': {
                    'time_of_day': 'day',  # Could be dynamic based on turn
                    'weather_conditions': 'clear',
                    'visibility': 'normal',
                    'combat_status': 'peaceful'
                },
                
                # Narrative context
                'story_state': getattr(self, 'story_state', {
                    'current_phase': 'initialization',
                    'story_progression': [],
                    'character_relationships': {},
                    'investigation_count': 0,
                    'dialogue_count': 0
                }),
                
                # World tracker information
                'world_tracker': getattr(self, 'world_state_tracker', {
                    'discovered_clues': {},
                    'agent_discoveries': {},
                    'environmental_changes': {},
                    'investigation_history': []
                }),
                
                # Physical constraints
                'physics': {
                    'gravity': 'standard',
                    'time_flow': 'normal',
                    'space_constraints': 'standard',
                    'energy_conservation': True
                },
                
                # Available resources in the world
                'world_resources': {
                    'available_equipment': [],
                    'accessible_locations': [],
                    'time_remaining': 'unlimited',
                    'communication_channels': ['standard']
                }
            }
            
            # Add campaign brief context if available
            if hasattr(self, 'campaign_brief') and self.campaign_brief:
                world_context['campaign_context'] = {
                    'setting': getattr(self.campaign_brief, 'setting', 'Unknown'),
                    'faction_tensions': getattr(self.campaign_brief, 'faction_tensions', {}),
                    'active_events': getattr(self.campaign_brief, 'active_events', []),
                    'story_hooks': getattr(self.campaign_brief, 'story_hooks', [])
                }
            
            logger.debug(f"🌍 Generated world context with {len(world_context)} categories")
            return world_context
            
        except Exception as e:
            logger.warning(f"⚠️ Error generating world context, using minimal context: {e}")
            return {
                'current_turn': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'environment': {'status': 'unknown'},
                'story_state': {'current_phase': 'initialization'},
                'physics': {'constraints': 'standard'}
            }
    
    def _determine_overall_validation_result(self, violations: List['IronLawsViolation']) -> str:
        """
        Determine overall validation result based on violation analysis.
        
        Analyzes all violations to determine if the action should be:
        - APPROVED: No significant violations
        - APPROVED_WITH_WARNINGS: Minor violations only
        - REQUIRES_REPAIR: Significant violations that can be fixed
        - REJECTED: Critical violations that cannot be repaired
        
        Args:
            violations: List of all Iron Laws violations found
            
        Returns:
            Overall validation result string
        """
        if not violations:
            return "APPROVED"
        
        # Categorize violations by severity
        critical_violations = [v for v in violations if v.severity == "critical"]
        high_violations = [v for v in violations if v.severity == "high"] 
        medium_violations = [v for v in violations if v.severity == "medium"]
        low_violations = [v for v in violations if v.severity == "low"]
        
        # Determine result based on severity distribution
        if critical_violations:
            # Critical violations mean automatic rejection
            logger.info(f"🚫 Action rejected due to {len(critical_violations)} critical violations")
            return "REJECTED"
        
        if high_violations and len(high_violations) >= 2:
            # Multiple high-severity violations require repair
            logger.info(f"🔧 Action requires repair due to {len(high_violations)} high-severity violations")
            return "REQUIRES_REPAIR"
        
        if high_violations or (medium_violations and len(medium_violations) >= 3):
            # Single high or multiple medium violations need repair
            logger.info(f"🔧 Action requires repair: {len(high_violations)} high, {len(medium_violations)} medium violations")
            return "REQUIRES_REPAIR"
        
        if medium_violations or low_violations:
            # Minor violations warrant warnings but allow approval
            logger.info(f"⚠️ Action approved with warnings: {len(medium_violations)} medium, {len(low_violations)} low violations")
            return "APPROVED_WITH_WARNINGS"
        
        # Shouldn't reach here with violations present, but safety fallback
        logger.warning("🤷 Unexpected violation analysis result, defaulting to repair")
        return "REQUIRES_REPAIR"
    
    def _calculate_action_stamina_cost(self, action: 'ProposedAction') -> int:
        """
        Calculate stamina cost for a proposed action.
        
        Analyzes the action's complexity, duration, intensity, and type to
        determine how much stamina/energy it would require from the character.
        
        Args:
            action: Proposed action to calculate cost for
            
        Returns:
            Stamina cost as integer value
        """
        try:
            base_cost = 10  # Default base stamina cost
            
            # Modify cost based on action type
            action_costs = {
                'attack': 20,
                'defend': 15,
                'move': 10,
                'investigate': 15,
                'communicate': 5,
                'wait': 2,
                'search': 12,
                'analyze': 18,
                'interact': 8,
                'cast_spell': 25,
                'use_item': 5,
                'hide': 10,
                'run': 15
            }
            
            action_type = getattr(action, 'action_type', 'move').lower()
            base_cost = action_costs.get(action_type, base_cost)
            
            # Modify based on action parameters
            if hasattr(action, 'parameters') and action.parameters:
                params = action.parameters
                
                # Intensity modifier
                if hasattr(params, 'intensity') and params.intensity:
                    intensity_value = str(params.intensity).lower() if params.intensity else 'normal'
                    intensity_multiplier = {
                        'low': 0.7,
                        'normal': 1.0,
                        'high': 1.3,
                        'extreme': 1.6
                    }
                    base_cost = int(base_cost * intensity_multiplier.get(intensity_value, 1.0))
                
                # Duration modifier
                if hasattr(params, 'duration'):
                    if params.duration > 1.0:  # Extended actions cost more
                        base_cost = int(base_cost * (1.0 + (params.duration - 1.0) * 0.3))
                
                # Range modifier for ranged actions
                if hasattr(params, 'range') and params.range > 10:
                    base_cost = int(base_cost * (1.0 + (params.range - 10) * 0.1))
            
            # Ensure minimum cost
            final_cost = max(1, base_cost)
            
            logger.debug(f"💪 Calculated stamina cost: {final_cost} for {action_type} action")
            return final_cost
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating stamina cost, using default: {e}")
            return 10  # Safe default


# Utility functions for DirectorAgent management

def create_director_with_agents(world_state_path: Optional[str] = None, 
                               character_sheet_paths: Optional[List[str]] = None) -> Tuple[DirectorAgent, List[bool]]:
    """
    Utility function to create a DirectorAgent and register multiple agents at once.
    
    Args:
        world_state_path: Optional path to world state file
        character_sheet_paths: List of paths to character sheet files
        
    Returns:
        Tuple of (DirectorAgent instance, list of registration success booleans)
    """
    director = DirectorAgent(world_state_path)
    registration_results = []
    
    if character_sheet_paths:
        for sheet_path in character_sheet_paths:
            try:
                agent = PersonaAgent(sheet_path)
                success = director.register_agent(agent)
                registration_results.append(success)
            except Exception as e:
                logger.error(f"Failed to create agent from {sheet_path}: {e}")
                registration_results.append(False)
    
    return director, registration_results


def run_simulation_batch(director: DirectorAgent, num_turns: int) -> List[Dict[str, Any]]:
    """
    Utility function to run multiple simulation turns in batch.
    
    Args:
        director: DirectorAgent instance to run
        num_turns: Number of turns to execute
        
    Returns:
        List of turn summary dictionaries
    """
    turn_results = []
    
    logger.info(f"Starting batch simulation: {num_turns} turns")
    
    for turn_num in range(num_turns):
        try:
            turn_result = director.run_turn()
            turn_results.append(turn_result)
            
            logger.info(f"Batch turn {turn_num + 1}/{num_turns} completed")
            
        except Exception as e:
            logger.error(f"Batch simulation failed at turn {turn_num + 1}: {e}")
            break
    
    logger.info(f"Batch simulation completed: {len(turn_results)} turns executed")
    
    return turn_results


# Example usage and testing functions

def example_usage():
    """
    Example usage of the DirectorAgent class.
    
    Demonstrates how to create and use DirectorAgent for orchestrating
    multi-agent simulations.
    """
    print("DirectorAgent Example Usage:")
    print("============================")
    
    try:
        # Create DirectorAgent
        director = DirectorAgent()
        print(f"✓ DirectorAgent created successfully")
        print(f"  Campaign log: {director.campaign_log_path}")
        
        # Example agent registration (would need actual character sheet file)
        # agent = PersonaAgent("test_character.md")
        # success = director.register_agent(agent)
        # print(f"✓ Agent registration: {'Success' if success else 'Failed'}")
        
        # Example turn execution
        # turn_result = director.run_turn()
        # print(f"✓ Turn executed: {turn_result['total_actions']} actions generated")
        
        # Get simulation status
        status = director.get_simulation_status()
        print(f"✓ Simulation status: {status['agents']['total_registered']} agents registered")
        
        # Close campaign log
        director.close_campaign_log()
        print(f"✓ Campaign log closed successfully")
        
        print("\nDirectorAgent is ready for multi-agent orchestration!")
        
    except Exception as e:
        print(f"✗ Example failed: {e}")


if __name__ == "__main__":
    # Run example usage when script is executed directly
    example_usage()