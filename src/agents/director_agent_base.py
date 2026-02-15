#!/usr/bin/env python3
"""
DirectorAgent Base Implementation
=================================

Core foundation class for the DirectorAgent system containing:
- Core initialization logic
- Agent registration and management
- Basic simulation interfaces
- Public API methods

This module provides the fundamental infrastructure that other director components
build upon while maintaining clean separation of concerns.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import agent and shared types
from src.agents.persona_agent.agent import PersonaAgent
from src.core.event_bus import EventBus

# Try to import configuration loader
try:
    from src.core.config.config_loader import get_config
except ImportError:

    def get_config():
        return None


# Import narrative components
try:
    from campaign_brief import CampaignBrief

    from src.core.narrative.narrative_actions import NarrativeActionResolver
except ImportError:
    CampaignBrief = None

    class NarrativeActionResolver:
        def __init__(self):
            pass


# Configure logging for the director agent base
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DirectorAgentBase:
    """
    Core foundation class for DirectorAgent system.

    Provides:
    - Core initialization and configuration management
    - Agent registration and lifecycle tracking
    - Basic simulation state and interfaces
    - Public API methods for external integration
    - Error handling and logging infrastructure

    This base class is designed to be extended by the full DirectorAgent
    implementation while maintaining clean separation of core functionality.
    """

    def __init__(
        self,
        event_bus: EventBus,
        world_state_file_path: Optional[str] = None,
        campaign_log_path: Optional[str] = None,
        campaign_brief_path: Optional[str] = None,
    ):
        """
        Initialize the DirectorAgent base infrastructure.

        Sets up core systems including agent registry, configuration management,
        logging system, and basic simulation state tracking.

        Args:
            event_bus: EventBus instance for decoupled communication
            world_state_file_path: Optional path to world state database file
            campaign_log_path: Optional path to campaign log file
            campaign_brief_path: Optional path to campaign brief file

        Raises:
            ValueError: If configuration is invalid
            OSError: If file operations fail
        """
        logger.info("Initializing DirectorAgent base infrastructure...")

        self.event_bus = event_bus

        # Load and validate configuration
        try:
            config = get_config()
            self._config = config
        except Exception as e:
            logger.warning(f"Failed to load configuration, using defaults: {e}")
            self._config = None

        # Core agent management system
        self.registered_agents: List[PersonaAgent] = []
        """List of registered PersonaAgent instances managed by this director."""

        # Path management with configuration fallbacks
        self._setup_file_paths(
            world_state_file_path, campaign_log_path, campaign_brief_path
        )

        # Configuration-driven parameters
        self._setup_configuration_parameters()

        # Simulation state tracking
        self._initialize_simulation_state()

        # Error tracking infrastructure
        self._initialize_error_tracking()

        # Narrative engine components
        self._initialize_narrative_components()

        # Dynamic world state tracker
        self._initialize_world_state_tracker()

        logger.info("DirectorAgent base infrastructure initialized successfully")

    def _setup_file_paths(
        self,
        world_state_file_path: Optional[str],
        campaign_log_path: Optional[str],
        campaign_brief_path: Optional[str],
    ) -> None:
        """Set up file paths with configuration fallbacks."""
        # World state management
        if world_state_file_path is None and self._config:
            try:
                world_state_file_path = self._config.director.world_state_file
            except AttributeError:
                world_state_file_path = None
        self.world_state_file_path = world_state_file_path

        self.world_state_data: Dict[str, Any] = {}
        """Current world state data."""

        # Campaign logging system
        if campaign_log_path is None:
            if self._config:
                try:
                    campaign_log_path = self._config.paths.log_file_path
                except AttributeError:
                    campaign_log_path = "campaign_log.md"
            else:
                campaign_log_path = "campaign_log.md"
        self.campaign_log_path = campaign_log_path

        # Campaign brief path
        self.campaign_brief_path = campaign_brief_path

    def _setup_configuration_parameters(self) -> None:
        """Set up configuration-driven parameters with fallbacks."""
        if self._config:
            try:
                self.max_turn_history = self._config.director.max_turn_history
                self.error_threshold = self._config.director.error_threshold
            except AttributeError:
                self.max_turn_history = 100
                self.error_threshold = 10
        else:
            self.max_turn_history = 100
            self.error_threshold = 10

    def _initialize_simulation_state(self) -> None:
        """Initialize core simulation state tracking."""
        self.current_turn_number = 0
        """Current simulation turn counter."""

        self.simulation_start_time = datetime.now()
        """Timestamp when the simulation was initialized."""

        self.total_actions_processed = 0
        """Counter for total actions processed across all turns."""

    def _initialize_error_tracking(self) -> None:
        """Initialize error tracking infrastructure."""
        self.error_count = 0
        """Count of errors encountered during simulation."""

        self.last_error_time: Optional[datetime] = None
        """Timestamp of the most recent error."""

    def _initialize_narrative_components(self) -> None:
        """Initialize narrative engine components."""
        self.campaign_brief: Optional[CampaignBrief] = None
        """Loaded campaign brief defining narrative context."""

        self.narrative_resolver = NarrativeActionResolver()
        """Resolver for story-driven actions and outcomes."""

        self.story_state = {
            "current_phase": "initialization",
            "triggered_events": [],
            "story_progression": [],
            "investigation_count": 0,
            "dialogue_count": 0,
            "character_relationships": {},
        }
        """Current narrative state tracking."""

    def _initialize_world_state_tracker(self) -> None:
        """Initialize dynamic world state tracking system."""
        self.world_state_tracker = {
            "discovered_clues": {},  # agent_id -> list of discovered clues
            "environmental_changes": {},  # location -> list of changes
            "agent_discoveries": {},  # turn_number -> {agent_id: discoveries}
            "temporal_markers": {},  # timestamp -> events
            "investigation_history": [],  # chronological list of all investigations
        }
        """Dynamic world state tracker."""

    def register_agent(self, agent: PersonaAgent) -> bool:
        """
        Register a PersonaAgent instance with the DirectorAgent.

        Validates agent compatibility and adds it to the managed agents list.
        Includes comprehensive validation to ensure runtime stability.

        Args:
            agent: PersonaAgent instance to register
                  Must have required methods and valid agent_id

        Returns:
            bool: True if registration successful, False if validation failed
        """
        try:
            logger.info("Attempting to register agent for simulation management")

            # Validate the agent instance
            if not isinstance(agent, PersonaAgent):
                logger.error(
                    f"Invalid agent type: {type(agent)}. Expected PersonaAgent instance"
                )
                return False

            # Validate required methods
            if not hasattr(agent, "handle_turn_start"):
                logger.error("Agent missing required 'handle_turn_start' method")
                return False

            if not callable(getattr(agent, "handle_turn_start")):
                logger.error("Agent 'handle_turn_start' is not callable")
                return False

            # Validate agent ID
            if not hasattr(agent, "agent_id") or not agent.agent_id:
                logger.error("Agent missing valid agent_id")
                return False

            # Check for duplicate registration
            existing_ids = [
                existing_agent.agent_id for existing_agent in self.registered_agents
            ]
            if agent.agent_id in existing_ids:
                logger.warning(f"Agent with ID '{agent.agent_id}' already registered")
                return False

            # Register the agent
            self.registered_agents.append(agent)
            logger.info(
                f"Successfully registered agent '{agent.agent_id}' (total: {len(self.registered_agents)})"
            )

            return True

        except Exception as e:
            logger.error(f"Error during agent registration: {str(e)}")
            return False

    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove a registered agent by ID.

        Args:
            agent_id: ID of the agent to remove

        Returns:
            bool: True if agent was found and removed, False otherwise
        """
        try:
            initial_count = len(self.registered_agents)
            self.registered_agents = [
                agent for agent in self.registered_agents if agent.agent_id != agent_id
            ]

            if len(self.registered_agents) < initial_count:
                logger.info(
                    f"Successfully removed agent '{agent_id}' (remaining: {len(self.registered_agents)})"
                )
                return True
            else:
                logger.warning(f"Agent '{agent_id}' not found for removal")
                return False

        except Exception as e:
            logger.error(f"Error removing agent '{agent_id}': {str(e)}")
            return False

    def get_agent_list(self) -> List[Dict[str, str]]:
        """
        Get list of registered agents with basic information.

        Returns:
            List of dictionaries containing agent information
        """
        try:
            agent_list = []
            for agent in self.registered_agents:
                agent_info = {
                    "agent_id": getattr(agent, "agent_id", "Unknown"),
                    "character_name": getattr(agent, "character_name", "Unknown"),
                    "faction": getattr(agent, "faction", "Unknown"),
                    "status": "active",
                }
                agent_list.append(agent_info)

            return agent_list

        except Exception as e:
            logger.error(f"Error getting agent list: {str(e)}")
            return []

    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get comprehensive simulation status information.

        Returns:
            Dictionary containing simulation metrics and state
        """
        try:
            current_time = datetime.now()
            elapsed_time = (current_time - self.simulation_start_time).total_seconds()

            status = {
                "simulation_status": (
                    "running" if self.registered_agents else "initialized"
                ),
                "current_turn": self.current_turn_number,
                "registered_agents": len(self.registered_agents),
                "total_actions_processed": self.total_actions_processed,
                "simulation_start_time": self.simulation_start_time.isoformat(),
                "elapsed_time_seconds": elapsed_time,
                "error_count": self.error_count,
                "last_error_time": (
                    self.last_error_time.isoformat() if self.last_error_time else None
                ),
                "world_state_file": self.world_state_file_path,
                "campaign_log_path": self.campaign_log_path,
                "campaign_brief_loaded": self.campaign_brief is not None,
                "story_phase": self.story_state.get("current_phase", "unknown"),
            }

            return status

        except Exception as e:
            logger.error(f"Error getting simulation status: {str(e)}")
            return {"simulation_status": "error", "error_message": str(e)}

    def log_event(self, event_description: str) -> None:
        """
        Log an event to the campaign log.

        Args:
            event_description: Description of the event to log
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"\n### {timestamp}\n{event_description}\n"

            with open(self.campaign_log_path, "a", encoding="utf-8") as file:
                file.write(log_entry)

            logger.info(f"Event logged to campaign log: {event_description[:50]}...")

        except Exception as e:
            logger.error(f"Error logging event: {str(e)}")

    def _handle_error(
        self, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        """
        Handle errors with consistent logging and tracking.

        Args:
            error_message: Human-readable error description
            exception: Optional exception that caused the error
        """
        self.error_count += 1
        self.last_error_time = datetime.now()

        if exception:
            logger.error(
                f"DirectorAgent error: {error_message} - Exception: {str(exception)}"
            )
        else:
            logger.error(f"DirectorAgent error: {error_message}")

        # Log to campaign log if possible
        try:
            self.log_event(f"ERROR: {error_message}")
        except Exception:
            logger.debug("Failed to log error event", exc_info=True)

    def get_config(self) -> Optional[Any]:
        """
        Get current configuration object.

        Returns:
            Configuration object or None if not loaded
        """
        return self._config

    def is_initialized(self) -> bool:
        """
        Check if the DirectorAgent is properly initialized.

        Returns:
            bool: True if all core systems are initialized
        """
        try:
            return (
                self.event_bus is not None
                and self.registered_agents is not None
                and self.simulation_start_time is not None
                and self.narrative_resolver is not None
            )
        except Exception:
            return False
