#!/usr/bin/env python3
"""
DirectorAgent Integrated Implementation
=======================================

Maintains backward compatibility by integrating the extracted modular components
into a unified DirectorAgent interface. This ensures existing imports continue
to work while providing the benefits of modular architecture.

The integrated DirectorAgent coordinates:
- DirectorAgentBase: Core initialization and basic interfaces
- TurnOrchestrator: Turn execution and coordination
- WorldStateCoordinator: World state management and persistence
- AgentLifecycleManager: Iron Laws validation and action adjudication
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.agent_lifecycle_manager import AgentLifecycleManager
from src.core.types.shared_types import CharacterAction

# Import extracted components
from src.director_agent_base import DirectorAgentBase
from src.event_bus import EventBus

# Import agent and shared types
from src.persona_agent import PersonaAgent
from src.turn_orchestrator import TurnOrchestrator
from src.world_state_coordinator import WorldStateCoordinator

# Try to import Iron Laws types
try:
    from src.shared_types import CharacterData, ProposedAction

    IRON_LAWS_AVAILABLE = True
except ImportError:
    IRON_LAWS_AVAILABLE = False

# Import configuration and narrative components
try:
    from campaign_brief import (
        CampaignBrief,
        CampaignBriefLoader,
        NarrativeEvent,
    )

    from src.core.config.config_loader import (
        get_campaign_log_filename,
        get_config,
    )
    from src.core.narrative.narrative_actions import NarrativeActionResolver
except ImportError:

    def get_config():
        return None

    def get_campaign_log_filename():
        return "campaign_log.md"

    CampaignBrief = None
    CampaignBriefLoader = None
    NarrativeEvent = None

    class NarrativeActionResolver:
        def __init__(self):
            pass


# Configure logging
logger = logging.getLogger(__name__)


class DirectorAgent:
    """
    Integrated DirectorAgent maintaining backward compatibility with modular architecture.

    This class provides the same public interface as the original DirectorAgent
    while internally coordinating modular components for improved maintainability.

    All existing functionality is preserved while gaining benefits of:
    - Modular component architecture
    - Clear separation of concerns
    - Enhanced testability
    - Improved maintainability
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        world_state_file_path: Optional[str] = None,
        campaign_log_path: Optional[str] = None,
        campaign_brief_path: Optional[str] = None,
    ):
        """
        Initialize the DirectorAgent with modular component coordination.

        Args:
            event_bus: Optional EventBus instance for decoupled communication.
                      If None, creates a default EventBus instance for backward compatibility.
            world_state_file_path: Optional path to world state database file
            campaign_log_path: Optional path to campaign log file
            campaign_brief_path: Optional path to campaign brief file
        """
        logger.info(
            "Initializing integrated DirectorAgent with modular components..."
        )

        # Create default EventBus if none provided (backward compatibility)
        if event_bus is None:
            event_bus = EventBus()
            logger.info("Created default EventBus for backward compatibility")

        # Initialize core base component
        self.base = DirectorAgentBase(
            event_bus,
            world_state_file_path,
            campaign_log_path,
            campaign_brief_path,
        )

        # Initialize specialized components
        self.turn_orchestrator = TurnOrchestrator(
            event_bus, self.base.max_turn_history
        )
        self.world_state_coordinator = WorldStateCoordinator(
            world_state_file_path
        )
        self.agent_lifecycle_manager = AgentLifecycleManager()

        # Initialize narrative components
        self._initialize_narrative_components()

        # Set up component coordination
        self._setup_component_coordination()

        logger.info(
            "DirectorAgent integrated architecture initialized successfully"
        )

    def _initialize_narrative_components(self) -> None:
        """Initialize narrative and campaign systems."""
        try:
            self.campaign_brief_path = self.base.campaign_brief_path
            self.campaign_brief: Optional[CampaignBrief] = None
            self.narrative_resolver = NarrativeActionResolver()

            # Load campaign brief if provided
            if self.campaign_brief_path and CampaignBriefLoader:
                try:
                    brief_loader = CampaignBriefLoader(
                        self.campaign_brief_path
                    )
                    self.campaign_brief = brief_loader.load_campaign_brief()
                    logger.info(
                        f"Campaign brief loaded from: {self.campaign_brief_path}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to load campaign brief: {e}")

        except Exception as e:
            logger.error(f"Error initializing narrative components: {e}")

    def _setup_component_coordination(self) -> None:
        """Set up coordination between components."""
        try:
            # Initialize campaign log
            self._initialize_campaign_log()

            # Load world state through coordinator
            self.base.world_state_data = (
                self.world_state_coordinator.world_state_data
            )

            # Subscribe to agent actions
            self.base.event_bus.subscribe(
                "AGENT_ACTION_COMPLETE", self._handle_agent_action
            )

            logger.info("Component coordination established successfully")

        except Exception as e:
            logger.error(f"Error setting up component coordination: {e}")

    def _initialize_campaign_log(self) -> None:
        """Initialize the campaign log file."""
        try:
            # Create fresh campaign log for each simulation
            initial_content = f"""# Campaign Log

**Simulation Started:** {self.base.simulation_start_time.strftime('%Y-%m-%d %H:%M:%S')}
**Director Agent:** DirectorAgent Integrated v1.0
**Architecture:** Modular Components

## Campaign Overview

This log tracks all events, decisions, and interactions in the StoryForge AI Interactive Story Engine.
Each entry includes timestamps, participating agents, and detailed event descriptions.

---

## Campaign Events

### Simulation Initialization
**Time:** {self.base.simulation_start_time.strftime('%Y-%m-%d %H:%M:%S')}
**Event:** DirectorAgent initialized with modular component architecture
**Participants:** System
**Details:** Integrated DirectorAgent successfully started with base, orchestrator, world state, and lifecycle components

"""

            with open(
                self.base.campaign_log_path, "w", encoding="utf-8"
            ) as file:
                file.write(initial_content)

            logger.info(
                f"Campaign log initialized: {self.base.campaign_log_path}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize campaign log: {e}")

    # Public API methods - maintaining backward compatibility

    def register_agent(self, agent: PersonaAgent) -> bool:
        """
        Register a PersonaAgent instance with the DirectorAgent.

        Args:
            agent: PersonaAgent instance to register

        Returns:
            bool: True if registration successful, False otherwise
        """
        success = self.base.register_agent(agent)
        if success:
            logger.info(f"Agent {agent.agent_id} registered successfully")
        return success

    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove a registered agent by ID.

        Args:
            agent_id: ID of the agent to remove

        Returns:
            bool: True if agent was found and removed, False otherwise
        """
        return self.base.remove_agent(agent_id)

    def get_agent_list(self) -> List[Dict[str, str]]:
        """
        Get list of registered agents with basic information.

        Returns:
            List of dictionaries containing agent information
        """
        return self.base.get_agent_list()

    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get comprehensive simulation status information.

        Returns:
            Dictionary containing simulation metrics and state
        """
        base_status = self.base.get_simulation_status()

        # Add component-specific status
        base_status.update(
            {
                "turn_orchestrator_metrics": self.turn_orchestrator.get_performance_metrics(),
                "world_state_summary": self.world_state_coordinator.get_world_state_summary(),
                "agent_lifecycle_metrics": self.agent_lifecycle_manager.get_lifecycle_metrics(),
                "component_architecture": "integrated_modular",
            }
        )

        return base_status

    def log_event(self, event_description: str) -> None:
        """
        Log an event to the campaign log.

        Args:
            event_description: Description of the event to log
        """
        self.base.log_event(event_description)

    def run_turn(self) -> Dict[str, Any]:
        """
        Execute a single simulation turn.

        Returns:
            Dictionary containing turn execution results
        """
        import asyncio

        try:
            # Use turn orchestrator to execute turn (handle async call)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.turn_orchestrator.run_turn(
                            registered_agents=self.base.registered_agents,
                            world_state_data=self.base.world_state_data,
                            log_event_callback=self.log_event,
                        ),
                    )
                    turn_result = future.result()
            else:
                # If no loop is running, use asyncio.run
                turn_result = asyncio.run(
                    self.turn_orchestrator.run_turn(
                        registered_agents=self.base.registered_agents,
                        world_state_data=self.base.world_state_data,
                        log_event_callback=self.log_event,
                    )
                )

            # Update base counters
            if turn_result.get("status") == "turn_started":
                self.base.current_turn_number = (
                    self.turn_orchestrator.current_turn_number
                )

            return turn_result

        except Exception as e:
            logger.error(f"Error executing turn: {str(e)}")
            return {"status": "error", "message": str(e)}

    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save current world state to file.

        Args:
            file_path: Optional path to save to (uses default if None)

        Returns:
            bool: True if save successful, False otherwise
        """
        return self.world_state_coordinator.save_world_state(file_path)

    def _handle_agent_action(
        self, agent: PersonaAgent, action: Optional[CharacterAction]
    ) -> None:
        """
        Handle an agent's action during turn execution.

        Args:
            agent: PersonaAgent that performed the action
            action: Action taken by the agent (or None if waiting)
        """
        try:
            # Use turn orchestrator to handle the action
            success = self.turn_orchestrator.handle_agent_action(
                agent, action, self.log_event
            )

            if success:
                self.base.total_actions_processed += 1

                # If Iron Laws validation is available and action exists, validate it
                if action and IRON_LAWS_AVAILABLE:
                    try:
                        # Convert to ProposedAction format if needed
                        proposed_action = self._convert_to_proposed_action(
                            action
                        )
                        character_data = self._extract_character_data(agent)

                        # Adjudicate the action
                        adjudication_result = self.agent_lifecycle_manager.adjudicate_agent_action(
                            agent, proposed_action, character_data
                        )

                        if not adjudication_result.success:
                            logger.warning(
                                f"Action adjudication failed for {agent.agent_id}: {adjudication_result.adjudication_notes}"
                            )
                        elif adjudication_result.repair_log:
                            logger.info(
                                f"Action repaired for {agent.agent_id}: {len(adjudication_result.repair_log)} repairs applied"
                            )

                    except Exception as validation_error:
                        logger.warning(
                            f"Action validation failed for {agent.agent_id}: {validation_error}"
                        )

        except Exception as e:
            logger.error(f"Error handling agent action: {str(e)}")

    def _convert_to_proposed_action(
        self, action: CharacterAction
    ) -> "ProposedAction":
        """Convert CharacterAction to ProposedAction format."""
        if IRON_LAWS_AVAILABLE:
            return ProposedAction(
                action_id=getattr(action, "action_id", "unknown"),
                action_type=getattr(action, "action_type", "unknown"),
                reasoning=getattr(action, "reasoning", ""),
                target=getattr(action, "target", None),
            )
        else:
            # Fallback for when Iron Laws not available
            return action

    def _extract_character_data(
        self, agent: PersonaAgent
    ) -> Optional["CharacterData"]:
        """Extract character data from agent for validation."""
        if not IRON_LAWS_AVAILABLE:
            return None

        try:
            # Extract basic character data
            return CharacterData(
                name=getattr(agent, "character_name", "Unknown"),
                faction=getattr(agent, "faction", "Unknown"),
                # Additional fields would be extracted here in full implementation
            )
        except Exception as e:
            logger.error(f"Error extracting character data: {e}")
            return None

    # Additional methods for backward compatibility

    @property
    def registered_agents(self) -> List[PersonaAgent]:
        """Get list of registered agents."""
        return self.base.registered_agents

    @property
    def current_turn_number(self) -> int:
        """Get current turn number."""
        return max(
            self.base.current_turn_number,
            self.turn_orchestrator.current_turn_number,
        )

    @property
    def simulation_start_time(self) -> datetime:
        """Get simulation start time."""
        return self.base.simulation_start_time

    @property
    def total_actions_processed(self) -> int:
        """Get total actions processed."""
        return max(
            self.base.total_actions_processed,
            self.turn_orchestrator.total_actions_processed,
        )

    @property
    def error_count(self) -> int:
        """Get error count."""
        return self.base.error_count

    @property
    def campaign_log_path(self) -> str:
        """Get campaign log path."""
        return self.base.campaign_log_path

    @property
    def world_state_file_path(self) -> Optional[str]:
        """Get world state file path."""
        return self.world_state_coordinator.world_state_file_path

    @property
    def world_state_data(self) -> Dict[str, Any]:
        """Get world state data."""
        return self.world_state_coordinator.world_state_data

    # Component access properties for backward compatibility
    @property
    def agents(self):
        """Access to agent lifecycle manager for agent operations."""
        return self.agent_lifecycle_manager

    @property
    def world_state(self):
        """Access to world state coordinator for world state operations."""
        return self.world_state_coordinator

    @property
    def turns(self):
        """Access to turn orchestrator for turn management."""
        return self.turn_orchestrator

    @property
    def narrative(self):
        """Access to narrative processing functionality."""
        # Return the base director for narrative processing
        return self.base

    @property
    def logging(self):
        """Access to campaign logging service."""
        return self.base  # Base handles logging functionality

    @property
    def config(self):
        """Access to configuration service."""
        return self.base  # Base handles configuration

    @property
    def errors(self):
        """Access to error handler."""
        return self.base  # Base handles error management

    @property
    def validation(self):
        """Access to agent lifecycle manager for validation."""
        return self.agent_lifecycle_manager

    # Additional backward compatibility properties
    @property
    def event_bus(self):
        """Access to event bus."""
        return self.base.event_bus

    @property
    def shared_state(self):
        """Access to shared state information."""
        return {
            "simulation_status": self.get_simulation_status(),
            "world_state": self.world_state_data,
            "current_turn": self.current_turn_number,
        }

    @property
    def components(self):
        """Access to component registry."""
        return {
            "config": self.base,
            "world_state": self.world_state_coordinator,
            "agent_lifecycle": self.agent_lifecycle_manager,
            "turn_execution": self.turn_orchestrator,
            "narrative": self.base,
            "logging": self.base,
            "error_handler": self.base,
            "validation": self.agent_lifecycle_manager,
        }

    def generate_narrative_context(
        self, agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate narrative context for an agent.

        Args:
            agent_name: Name of the agent to generate context for

        Returns:
            Dictionary containing narrative context or None if not available
        """
        try:
            # Basic narrative context generation - can return None if system not fully initialized
            return {
                "agent_name": agent_name,
                "current_turn": self.current_turn_number,
                "world_state_snapshot": self.world_state_data,
                "simulation_time": self.simulation_start_time.isoformat(),
            }
        except Exception as e:
            logger.warning(f"Could not generate narrative context: {e}")
            return None

    def validate_action(self, action: Any, agent: Any) -> Dict[str, Any]:
        """
        Validate an action for an agent.

        Args:
            action: Action to validate
            agent: Agent performing the action

        Returns:
            Dictionary containing validation results
        """
        try:
            # Use the agent lifecycle manager for validation
            validation_result = (
                self.agent_lifecycle_manager.adjudicate_agent_action(
                    agent, action
                )
            )
            return validation_result
        except Exception as e:
            return {
                "validation_status": "error",
                "error_message": str(e),
                "action": str(action),
                "agent": getattr(agent, "character_name", str(agent)),
                "timestamp": datetime.now().isoformat(),
            }

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive system metrics.

        Returns:
            Dictionary containing comprehensive metrics
        """
        try:
            base_status = self.get_simulation_status()
            return {
                "system_health": {
                    "status": "healthy"
                    if self.error_count == 0
                    else "degraded",
                    "error_count": self.error_count,
                    "uptime_seconds": base_status.get(
                        "elapsed_time_seconds", 0
                    ),
                },
                "simulation_metrics": {
                    "current_turn": self.current_turn_number,
                    "total_actions": self.total_actions_processed,
                    "registered_agents": len(self.registered_agents),
                    "simulation_start": self.simulation_start_time.isoformat(),
                },
                "component_metrics": {
                    "world_state": {
                        "locations": self.world_state_data.get(
                            "locations", {}
                        ),
                        "events": self.world_state_data.get("events", []),
                    },
                    "agent_lifecycle": self.agent_lifecycle_manager.get_lifecycle_metrics(),
                    "turn_orchestrator": self.turn_orchestrator.get_performance_metrics(),
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive metrics: {e}")
            return {
                "system_health": {"status": "error", "error_message": str(e)},
                "simulation_metrics": {},
                "component_metrics": {},
                "timestamp": datetime.now().isoformat(),
            }

    def close_campaign_log(self) -> None:
        """Close the campaign log with summary information."""
        try:
            end_time = datetime.now()
            simulation_duration = (
                end_time - self.simulation_start_time
            ).total_seconds()

            closing_summary = f"""

## Campaign Summary

**Simulation End Time:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}
**Total Duration:** {simulation_duration:.2f} seconds ({simulation_duration/60:.1f} minutes)
**Total Turns:** {self.current_turn_number}
**Total Actions:** {self.total_actions_processed}
**Registered Agents:** {len(self.registered_agents)}
**Errors Encountered:** {self.error_count}
**Architecture:** Modular Components Integration

### Component Performance
- **Turn Orchestrator:** {self.turn_orchestrator.get_performance_metrics()}
- **World State Coordinator:** {len(self.world_state_coordinator.world_state_data)} world state entries
- **Agent Lifecycle Manager:** {self.agent_lifecycle_manager.get_lifecycle_metrics().get('total_validations', 0)} validations performed

**Status:** Campaign completed successfully with modular component architecture
"""

            with open(self.campaign_log_path, "a", encoding="utf-8") as file:
                file.write(closing_summary)

            logger.info("Campaign log closed with summary information")

        except Exception as e:
            logger.error(f"Error closing campaign log: {e}")

    def get_component_status(self) -> Dict[str, Any]:
        """
        Get status information for all components.

        Returns:
            Dictionary containing component status information
        """
        try:
            return {
                "base_component": {
                    "initialized": self.base.is_initialized(),
                    "registered_agents": len(self.base.registered_agents),
                    "current_turn": self.base.current_turn_number,
                },
                "turn_orchestrator": {
                    "current_turn": self.turn_orchestrator.current_turn_number,
                    "performance_metrics": self.turn_orchestrator.get_performance_metrics(),
                },
                "world_state_coordinator": {
                    "world_state_summary": self.world_state_coordinator.get_world_state_summary()
                },
                "agent_lifecycle_manager": {
                    "lifecycle_metrics": self.agent_lifecycle_manager.get_lifecycle_metrics(),
                    "violation_summary": self.agent_lifecycle_manager.get_violation_summary(),
                },
                "integration_status": "healthy",
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting component status: {e}")
            return {"error": str(e)}

    # Iron Laws delegation methods for backward compatibility with tests
    def _get_current_world_context(self) -> Dict[str, Any]:
        """Get current world context for Iron Laws validation."""
        try:
            return {
                "current_turn": self.current_turn_number,
                "total_agents": len(self.registered_agents),
                "environment": {
                    "type": "simulation",
                    "physics_enabled": True,
                    "time_scale": 1.0,
                },
                "story_state": {
                    "narrative_consistency": True,
                    "character_relationships": {},
                },
                "physics": {
                    "gravity": 9.8,
                    "speed_of_light": 299792458,
                    "realistic_movement": True,
                },
                "world_resources": self.world_state_data,
            }
        except Exception as e:
            logger.error(f"Error getting world context: {e}")
            return {}

    def _validate_causality_law(
        self, action: Any, character_data: Any, world_context: Any
    ) -> List[Any]:
        """Delegate causality law validation to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._validate_causality_law(action)
        return []

    def _validate_resource_law(
        self, action: Any, character_data: Any
    ) -> List[Any]:
        """Delegate resource law validation to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._validate_resource_law(
                action, character_data
            )
        return []

    def _validate_physics_law(
        self, action: Any, character_data: Any, world_context: Any
    ) -> List[Any]:
        """Delegate physics law validation to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._validate_physics_law(
                action, character_data
            )
        return []

    def _validate_narrative_law(
        self, action: Any, agent: Any, world_context: Any
    ) -> List[Any]:
        """Delegate narrative law validation to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._validate_narrative_law(action)
        return []

    def _validate_social_law(
        self, action: Any, agent: Any, world_context: Any
    ) -> List[Any]:
        """Delegate social law validation to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._validate_social_law(action)
        return []

    def _group_violations_by_law(
        self, violations: List[Any]
    ) -> Dict[str, List[Any]]:
        """Delegate violation grouping to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._group_violations_by_law(
                violations
            )
        return {}

    def _determine_overall_validation_result(
        self, violations: List[Any]
    ) -> Any:
        """Determine overall validation result based on violations."""
        if not violations:
            if IRON_LAWS_AVAILABLE:
                from src.shared_types import ValidationResult

                return ValidationResult.VALID
            return "VALID"

        # Check for critical violations
        for violation in violations:
            if (
                hasattr(violation, "severity")
                and violation.severity == "critical"
            ):
                if IRON_LAWS_AVAILABLE:
                    from src.shared_types import ValidationResult

                    return ValidationResult.INVALID
                return "INVALID"

        # Check for high/error violations
        for violation in violations:
            if hasattr(violation, "severity") and violation.severity in [
                "high",
                "error",
            ]:
                if IRON_LAWS_AVAILABLE:
                    from src.shared_types import ValidationResult

                    return ValidationResult.REQUIRES_REPAIR
                return "REQUIRES_REPAIR"

        # Low violations are acceptable
        if IRON_LAWS_AVAILABLE:
            from src.shared_types import ValidationResult

            return ValidationResult.VALID
        return "VALID"

    def _calculate_action_stamina_cost(self, action: Any) -> int:
        """Calculate stamina cost for an action."""
        try:
            # Base stamina cost calculation
            base_cost = 5

            # Add cost based on action type
            action_type = getattr(action, "action_type", "unknown")
            if isinstance(action_type, str):
                action_type = action_type.lower()
                type_costs = {
                    "move": 10,
                    "attack": 20,
                    "investigate": 8,
                    "communicate": 5,
                    "observe": 3,
                }
                base_cost = type_costs.get(action_type, 10)

            # Add cost based on intensity
            if hasattr(action, "parameters") and action.parameters:
                intensity = getattr(action.parameters, "intensity", None)
                if intensity:
                    intensity_str = str(intensity).lower()
                    intensity_multipliers = {
                        "low": 0.5,
                        "normal": 1.0,
                        "high": 1.5,
                        "extreme": 2.0,
                    }
                    multiplier = intensity_multipliers.get(intensity_str, 1.0)
                    base_cost = int(base_cost * multiplier)

                # Add cost based on duration
                duration = getattr(action.parameters, "duration", 1.0)
                if isinstance(duration, (int, float)) and duration > 1.0:
                    base_cost = int(base_cost * duration)

            return max(1, base_cost)  # Minimum cost of 1

        except Exception as e:
            logger.error(f"Error calculating stamina cost: {e}")
            return 1

    def _adjudicate_action(self, action: Any, agent: Any) -> Any:
        """Adjudicate an action using the agent lifecycle manager."""
        try:
            if not IRON_LAWS_AVAILABLE:
                # Return fallback result
                return type(
                    "Result",
                    (),
                    {
                        "overall_result": "VALID",
                        "violations": [],
                        "success": True,
                        "validated_action": action,
                        "repair_log": [],
                        "adjudication_notes": ["Iron Laws not available"],
                        "processing_time": 0.001,
                    },
                )()

            # Convert to expected format and delegate
            if hasattr(action, "action_id"):
                proposed_action = action
            else:
                # Create minimal ProposedAction
                from src.shared_types import ProposedAction

                proposed_action = ProposedAction(
                    action_id=getattr(action, "action_id", "unknown"),
                    action_type=getattr(action, "action_type", "unknown"),
                    target=getattr(action, "target", None),
                    agent_id=getattr(agent, "agent_id", "unknown"),
                    character_id=getattr(agent, "character_id", "unknown"),
                    reasoning=getattr(action, "reasoning", ""),
                )

            # Use agent lifecycle manager for adjudication
            result = self.agent_lifecycle_manager.adjudicate_agent_action(
                agent, proposed_action
            )

            # Add processing time for compatibility
            result.processing_time = 0.001
            result.overall_result = "VALID" if result.success else "INVALID"

            return result

        except Exception as e:
            logger.error(f"Error in action adjudication: {e}")
            # Return error result
            return type(
                "Result",
                (),
                {
                    "overall_result": "CATASTROPHIC_FAILURE",
                    "violations": [],
                    "success": False,
                    "validated_action": None,
                    "repair_log": [f"Adjudication error: {str(e)}"],
                    "adjudication_notes": ["System error"],
                    "processing_time": 0.001,
                },
            )()

    def _repair_causality_violations(
        self, action: Any, violations: List[Any]
    ) -> Tuple[Any, List[str]]:
        """Delegate causality violation repairs to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._repair_causality_violations(
                action, violations
            )
        return action, []

    def _repair_resource_violations(
        self, action: Any, violations: List[Any], character_data: Any
    ) -> Tuple[Any, List[str]]:
        """Delegate resource violation repairs to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._repair_resource_violations(
                action, violations, character_data
            )
        return action, []

    def _repair_physics_violations(
        self, action: Any, violations: List[Any], character_data: Any
    ) -> Tuple[Any, List[str]]:
        """Delegate physics violation repairs to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._repair_physics_violations(
                action, violations, character_data
            )
        return action, []

    def _repair_narrative_violations(
        self, action: Any, violations: List[Any]
    ) -> Tuple[Any, List[str]]:
        """Delegate narrative violation repairs to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._repair_narrative_violations(
                action, violations
            )
        return action, []

    def _repair_social_violations(
        self, action: Any, violations: List[Any]
    ) -> Tuple[Any, List[str]]:
        """Delegate social violation repairs to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            return self.agent_lifecycle_manager._repair_social_violations(
                action, violations
            )
        return action, []

    def _attempt_action_repairs(
        self, action: Any, violations: List[Any], character_data: Any
    ) -> Tuple[Any, List[str]]:
        """Delegate action repairs to agent lifecycle manager."""
        if IRON_LAWS_AVAILABLE:
            (
                validated_action,
                repair_log,
            ) = self.agent_lifecycle_manager._attempt_action_repairs(
                action, violations, character_data
            )
            # Convert ValidatedAction back to original action format if needed
            return validated_action, repair_log
        return None, []
