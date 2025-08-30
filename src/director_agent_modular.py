#!/usr/bin/env python3
"""
DirectorAgent Modular Implementation
====================================

Refactored DirectorAgent using modular components for improved maintainability,
testability, and separation of concerns. This facade maintains backward compatibility
while providing enterprise-grade internal architecture.

The modular DirectorAgent provides:
- Component-based architecture with clear separation of responsibilities
- Protocol-based interfaces for type safety and testing
- Improved error handling and recovery
- Comprehensive logging and monitoring
- Configuration management and hot-reloading
- Narrative orchestration and world state management
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import existing components for compatibility
try:
    from src.persona_agent import PersonaAgent
except ImportError:
    PersonaAgent = None

try:
    from shared_types import (
        ProposedAction as CharacterAction,  # Use ProposedAction as CharacterAction
    )
except ImportError:
    CharacterAction = dict

try:
    from src.event_bus import EventBus
except ImportError:

    class EventBus:
        def __init__(self):
            pass


# Import our new modular components
from director_components import (
    AgentLifecycleManager,
    CampaignLoggingService,
    ConfigurationService,
    NarrativeOrchestrator,
    SystemErrorHandler,
    TurnExecutionEngine,
    WorldStateManager,
)

# Try to import Iron Laws types
try:
    from src.shared_types import (
        ActionIntensity,
        ActionParameters,
        ActionTarget,
        ActionType,
        CharacterData,
        CharacterResources,
        CharacterStats,
        EntityType,
        IronLawsReport,
        IronLawsViolation,
        Position,
        ProposedAction,
        ResourceValue,
        ValidatedAction,
        ValidationResult,
        ValidationStatus,
    )

    IRON_LAWS_AVAILABLE = True
except ImportError as e:
    temp_logger = logging.getLogger(__name__)
    temp_logger.warning(f"Iron Laws types not available: {e}")
    IRON_LAWS_AVAILABLE = False

# Import configuration and narrative components with error handling
try:
    from config_loader import get_campaign_log_filename, get_config
except ImportError:

    def get_config(config_file=None):
        return {
            "environment": "development",
            "logging": {"level": "INFO"},
            "world_state_file": "world_state.json",
            "log_directory": "logs",
        }

    def get_campaign_log_filename():
        return "campaign.log"


try:
    from campaign_brief import CampaignBrief, CampaignBriefLoader, NarrativeEvent
except ImportError:

    class CampaignBrief:
        pass

    class CampaignBriefLoader:
        def __init__(self, filename):
            pass

        async def load_campaign_brief(self):
            return None

    class NarrativeEvent:
        pass


class DirectorAgent:
    """
    Refactored DirectorAgent with modular component architecture.

    Maintains backward compatibility while providing improved:
    - Error handling and recovery
    - Performance monitoring
    - Configuration management
    - Logging and audit trails
    - Component isolation and testing
    """

    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize DirectorAgent with modular components.

        Args:
            config_file: Path to configuration file
        """
        # Core configuration
        self.config_file = config_file
        try:
            # get_config() takes no parameters and returns AppConfig object
            app_config = get_config()
            self.config = (
                app_config.__dict__
                if hasattr(app_config, "__dict__")
                else {
                    "environment": "development",
                    "logging": {"level": "INFO"},
                    "world_state_file": "world_state.json",
                    "log_directory": "logs",
                }
            )
        except Exception:
            # Fallback configuration if get_config fails
            self.config = {
                "environment": "development",
                "logging": {"level": "INFO"},
                "world_state_file": "world_state.json",
                "log_directory": "logs",
            }

        # Initialize logging first
        self.logger = self._setup_logging()

        # Initialize modular components
        self._initialize_components()

        # Backward compatibility attributes
        self.agents = []  # Will be managed by AgentLifecycleManager
        self.world_state = {}  # Will be managed by WorldStateManager
        self.campaign_log_data = []  # Will be managed by CampaignLoggingService
        self.turn_count = 0

        # Legacy attributes for compatibility
        self.campaign_brief = None
        self.event_bus = EventBus()

        # Component integration flags
        self._initialized = False
        self._shutdown_requested = False

    def _initialize_components(self) -> None:
        """Initialize all modular components."""
        try:
            # Configuration service
            self.config_service = ConfigurationService(
                config_dir="config",
                environment=self.config.get("environment", "development"),
                logger=self.logger,
            )

            # Error handler (initialize early)
            self.error_handler = SystemErrorHandler(logger=self.logger)

            # Agent lifecycle manager
            self.agent_manager = AgentLifecycleManager(logger=self.logger)

            # World state manager
            self.world_state_manager = WorldStateManager(
                state_file=self.config.get("world_state_file", "world_state.json"),
                logger=self.logger,
            )

            # Turn execution engine
            self.turn_engine = TurnExecutionEngine(
                agent_manager=self.agent_manager, logger=self.logger
            )

            # Narrative orchestrator
            self.narrative_orchestrator = NarrativeOrchestrator(logger=self.logger)

            # Campaign logging service
            log_dir = self.config.get("log_directory", "logs")
            self.campaign_logger = CampaignLoggingService(
                log_dir=log_dir, logger=self.logger
            )

            self.logger.info("DirectorAgent modular components initialized")

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Component initialization failed: {e}")
            raise

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(__name__)

        # Configure based on config
        log_level = self.config.get("logging", {}).get("level", "INFO")
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Create console handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def initialize(self) -> bool:
        """
        Initialize all components asynchronously.

        Returns:
            bool: True if initialization successful
        """
        if self._initialized:
            return True

        try:
            self.logger.info("Initializing DirectorAgent...")

            # Initialize components in order
            components = [
                ("Error Handler", self.error_handler),
                ("Configuration Service", self.config_service),
                ("Campaign Logger", self.campaign_logger),
                ("World State Manager", self.world_state_manager),
                ("Agent Manager", self.agent_manager),
                ("Narrative Orchestrator", self.narrative_orchestrator),
            ]

            for name, component in components:
                try:
                    if hasattr(component, "initialize"):
                        success = await component.initialize()
                        if not success:
                            raise RuntimeError(f"{name} initialization failed")
                    self.logger.info(f"{name} initialized successfully")
                except Exception as e:
                    await self._handle_initialization_error(name, e)
                    return False

            # Load campaign brief if available
            await self._load_campaign_brief()

            # Initialize world state
            await self._initialize_world_state()

            self._initialized = True

            # Log initialization success
            await self.campaign_logger.log_event(
                {
                    "level": "info",
                    "category": "system",
                    "message": "DirectorAgent initialized successfully",
                    "metadata": {
                        "config_file": self.config_file,
                        "components_initialized": len(components),
                    },
                }
            )

            self.logger.info("DirectorAgent initialization completed successfully")
            return True

        except Exception as e:
            error_context = {
                "operation": "director_initialization",
                "config_file": self.config_file,
                "component": "DirectorAgent",
            }
            await self.error_handler.handle_error(e, error_context)
            return False

    async def register_agent(self, agent: PersonaAgent) -> bool:
        """
        Register a new agent with backward compatibility.

        Args:
            agent: PersonaAgent instance to register

        Returns:
            bool: True if registration successful
        """
        try:
            if not self._initialized:
                await self.initialize()

            # Use component for registration
            success = await self.agent_manager.register_agent(agent)

            if success:
                # Maintain backward compatibility
                self.agents.append(agent)

                # Log registration
                await self.campaign_logger.log_event(
                    {
                        "level": "info",
                        "category": "agent",
                        "message": f"Agent {agent.agent_id} registered successfully",
                        "metadata": {
                            "agent_id": agent.agent_id,
                            "agent_type": type(agent).__name__,
                            "total_agents": len(self.agents),
                        },
                        "agent_id": agent.agent_id,
                    }
                )

            return success

        except Exception as e:
            error_context = {
                "operation": "agent_registration",
                "agent_id": getattr(agent, "agent_id", "unknown"),
                "component": "DirectorAgent",
            }
            await self.error_handler.handle_error(e, error_context)
            return False

    async def execute_turn(
        self, turn_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a simulation turn with full component integration.

        Args:
            turn_data: Optional turn configuration data

        Returns:
            Dict containing turn results
        """
        if not self._initialized:
            await self.initialize()

        self.turn_count += 1

        try:
            self.logger.info(f"=== Executing Turn {self.turn_count} ===")

            # Execute turn using turn engine
            turn_result = await self.turn_engine.execute_turn(turn_data)

            # Update world state with changes
            if turn_result.get("world_state_changes"):
                await self.world_state_manager.update_world_state(
                    turn_result["world_state_changes"]
                )

                # Update backward compatibility attribute
                self.world_state = await self.world_state_manager.get_world_state()

            # Process narrative events
            if turn_result.get("narrative_events"):
                narrative_result = (
                    await self.narrative_orchestrator.process_narrative_events(
                        turn_result["narrative_events"]
                    )
                )
                turn_result["narrative_processing"] = narrative_result

            # Log comprehensive turn summary
            await self.campaign_logger.log_turn_summary(
                {
                    "turn_number": self.turn_count,
                    "success": turn_result.get("success", False),
                    "agent_results": turn_result.get("agent_results", {}),
                    "world_state_changes": turn_result.get("world_state_changes", {}),
                    "narrative_events": turn_result.get("narrative_events", []),
                    "metrics": turn_result.get("metrics", {}),
                }
            )

            # Update legacy campaign log for backward compatibility
            if turn_result.get("success"):
                self._update_legacy_campaign_log(turn_result)

            self.logger.info(f"Turn {self.turn_count} completed successfully")
            return turn_result

        except Exception as e:
            error_context = {
                "operation": "turn_execution",
                "turn_number": self.turn_count,
                "component": "DirectorAgent",
            }
            error_result = await self.error_handler.handle_error(e, error_context)

            # Return error result with backward compatibility
            return {
                "success": False,
                "error": str(e),
                "turn_number": self.turn_count,
                "error_handling": error_result,
            }

    async def get_world_state(self) -> Dict[str, Any]:
        """Get current world state with backward compatibility."""
        try:
            if not self._initialized:
                await self.initialize()

            state = await self.world_state_manager.get_world_state()

            # Update backward compatibility attribute
            self.world_state = state

            return state

        except Exception as e:
            error_context = {
                "operation": "get_world_state",
                "component": "DirectorAgent",
            }
            await self.error_handler.handle_error(e, error_context)
            return self.world_state  # Return cached version on error

    async def update_world_state(self, updates: Dict[str, Any]) -> None:
        """Update world state with backward compatibility."""
        try:
            if not self._initialized:
                await self.initialize()

            await self.world_state_manager.update_world_state(updates)

            # Update backward compatibility attribute
            self.world_state = await self.world_state_manager.get_world_state()

        except Exception as e:
            error_context = {
                "operation": "update_world_state",
                "component": "DirectorAgent",
            }
            await self.error_handler.handle_error(e, error_context)

    async def save_campaign_log(self) -> bool:
        """Save campaign log with new logging service."""
        try:
            if not self._initialized:
                await self.initialize()

            # Export comprehensive log data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"campaign_export_{timestamp}.json"

            success = await self.campaign_logger.export_logs(export_path)

            if success:
                self.logger.info(f"Campaign log saved to {export_path}")

            return success

        except Exception as e:
            error_context = {
                "operation": "save_campaign_log",
                "component": "DirectorAgent",
            }
            await self.error_handler.handle_error(e, error_context)
            return False

    def get_agent_count(self) -> int:
        """Get number of registered agents (backward compatibility)."""
        return len(self.agents)

    def get_turn_count(self) -> int:
        """Get current turn count (backward compatibility)."""
        return self.turn_count

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            if not self._initialized:
                await self.initialize()

            # Gather status from all components
            status = {
                "initialized": self._initialized,
                "turn_count": self.turn_count,
                "agent_count": len(self.agents),
                "shutdown_requested": self._shutdown_requested,
            }

            # Get component-specific status
            if hasattr(self.agent_manager, "get_system_status"):
                status["agent_manager"] = await self.agent_manager.get_system_status()

            if hasattr(self.campaign_logger, "get_statistics"):
                status["logging"] = await self.campaign_logger.get_statistics()

            if hasattr(self.error_handler, "get_error_statistics"):
                status["error_handling"] = (
                    await self.error_handler.get_error_statistics()
                )

            if hasattr(self.world_state_manager, "get_state_statistics"):
                status["world_state"] = (
                    await self.world_state_manager.get_state_statistics()
                )

            if hasattr(self.narrative_orchestrator, "get_story_summary"):
                status["narrative"] = (
                    await self.narrative_orchestrator.get_story_summary()
                )

            return status

        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {"error": str(e), "initialized": self._initialized}

    async def _load_campaign_brief(self) -> None:
        """Load campaign brief if available."""
        try:
            campaign_file = self.config.get("campaign_brief_file")
            if campaign_file and Path(campaign_file).exists():
                loader = CampaignBriefLoader(campaign_file)
                self.campaign_brief = await loader.load_campaign_brief()
                self.logger.info(f"Campaign brief loaded from {campaign_file}")
        except Exception as e:
            self.logger.warning(f"Failed to load campaign brief: {e}")

    async def _initialize_world_state(self) -> None:
        """Initialize world state from configuration or defaults."""
        try:
            # Load world state
            state = await self.world_state_manager.get_world_state()

            # Apply any configuration overrides
            config_world_state = self.config.get("initial_world_state", {})
            if config_world_state:
                await self.world_state_manager.update_world_state(config_world_state)
                state = await self.world_state_manager.get_world_state()

            # Update backward compatibility attribute
            self.world_state = state

            self.logger.info("World state initialized")

        except Exception as e:
            self.logger.error(f"World state initialization failed: {e}")
            # Use empty state as fallback
            self.world_state = {}

    async def _handle_initialization_error(
        self, component_name: str, error: Exception
    ) -> None:
        """Handle component initialization errors."""
        self.logger.error(f"{component_name} initialization failed: {error}")

        if hasattr(self, "error_handler"):
            error_context = {
                "operation": "component_initialization",
                "component": component_name,
                "phase": "startup",
            }
            await self.error_handler.handle_error(error, error_context)

    def _update_legacy_campaign_log(self, turn_result: Dict[str, Any]) -> None:
        """Update legacy campaign log for backward compatibility."""
        try:
            log_entry = {
                "turn": self.turn_count,
                "timestamp": datetime.now().isoformat(),
                "success": turn_result.get("success", False),
                "agent_count": len(self.agents),
                "narrative_events": len(turn_result.get("narrative_events", [])),
                "world_state_changes": len(turn_result.get("world_state_changes", {})),
            }

            self.campaign_log_data.append(log_entry)

            # Keep only recent entries for memory management
            if len(self.campaign_log_data) > 1000:
                self.campaign_log_data = self.campaign_log_data[-500:]

        except Exception as e:
            self.logger.debug(f"Legacy campaign log update failed: {e}")

    # Legacy methods for backward compatibility

    def add_agent(self, agent: PersonaAgent) -> bool:
        """Legacy method for adding agents (synchronous wrapper)."""
        return asyncio.run(self.register_agent(agent))

    def run_turn(self, turn_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Legacy method for running turns (synchronous wrapper)."""
        return asyncio.run(self.execute_turn(turn_data))

    def get_campaign_log(self) -> List[Dict[str, Any]]:
        """Legacy method to get campaign log."""
        return self.campaign_log_data.copy()

    def save_world_state(self) -> bool:
        """Legacy method to save world state."""
        try:
            return asyncio.run(self.world_state_manager.save_world_state())
        except Exception as e:
            self.logger.error(f"World state save failed: {e}")
            return False

    def load_world_state(self) -> bool:
        """Legacy method to load world state."""
        try:
            return asyncio.run(self.world_state_manager.load_world_state())
        except Exception as e:
            self.logger.error(f"World state load failed: {e}")
            return False

    # Shutdown and cleanup

    async def shutdown(self) -> None:
        """Graceful shutdown of all components."""
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        self.logger.info("DirectorAgent shutdown requested...")

        try:
            # Log shutdown initiation
            if hasattr(self, "campaign_logger"):
                await self.campaign_logger.log_event(
                    {
                        "level": "info",
                        "category": "system",
                        "message": "DirectorAgent shutdown initiated",
                        "metadata": {
                            "turn_count": self.turn_count,
                            "agent_count": len(self.agents),
                        },
                    }
                )

            # Cleanup components in reverse order
            cleanup_components = [
                (
                    "Narrative Orchestrator",
                    getattr(self, "narrative_orchestrator", None),
                ),
                ("Agent Manager", getattr(self, "agent_manager", None)),
                ("World State Manager", getattr(self, "world_state_manager", None)),
                ("Campaign Logger", getattr(self, "campaign_logger", None)),
                ("Configuration Service", getattr(self, "config_service", None)),
                ("Error Handler", getattr(self, "error_handler", None)),
            ]

            for name, component in cleanup_components:
                if component and hasattr(component, "cleanup"):
                    try:
                        await component.cleanup()
                        self.logger.info(f"{name} cleanup completed")
                    except Exception as e:
                        self.logger.error(f"{name} cleanup failed: {e}")

            self.logger.info("DirectorAgent shutdown completed")

        except Exception as e:
            self.logger.error(f"Shutdown error: {e}")

    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, "_shutdown_requested") and not self._shutdown_requested:
            try:
                asyncio.run(self.shutdown())
            except Exception:
                pass  # Best effort cleanup

    # Context manager support

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


# Backward compatibility alias
ModularDirectorAgent = DirectorAgent
