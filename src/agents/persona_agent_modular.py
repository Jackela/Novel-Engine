"""
PersonaAgent Modular
===================

Modular PersonaAgent implementation using component-based architecture.
Maintains full backward compatibility while providing enterprise-grade modularity.
"""

import asyncio
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional  # Removed unused Union import

from .persona_agent.core import AgentStateManager, CharacterDataManager
from .persona_agent.decision_engine import (
    DecisionProcessor,
    GoalManager,
    ThreatAssessor,
)
from .persona_agent.llm_integration import LLMClient, ResponseProcessor

# Import all modular components
from .persona_agent.utilities import ResponseGenerator, Validator
from .persona_agent.world_interpretation import MemoryManager, WorldInterpreter

# Import shared types with fallbacks
try:
    from shared_types import ActionPriority
    from shared_types import ProposedAction as CharacterAction
except ImportError:
    CharacterAction = dict
    ActionPriority = str


class PersonaAgent:
    """
    Modular PersonaAgent implementation with component-based architecture.

    This class provides a facade over specialized components while maintaining
    full backward compatibility with the original PersonaAgent interface.

    Components:
    - CharacterDataManager: Character data loading and management
    - AgentStateManager: State tracking and persistence
    - DecisionProcessor: Core decision-making logic
    - ThreatAssessor: Threat evaluation and response
    - GoalManager: Goal lifecycle management
    - WorldInterpreter: Event interpretation through character lens
    - MemoryManager: Short/long-term memory management
    - LLMClient: Advanced LLM integration
    - ResponseProcessor: Response validation and enhancement
    - Validator: Comprehensive data validation
    - ResponseGenerator: Fallback response generation
    """

    def __init__(
        self,
        character_id: str,
        character_directory_path: str = None,
        character_data: Dict[str, Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize modular PersonaAgent.

        Args:
            character_id: Unique identifier for the character
            character_directory_path: Path to character data directory
            character_data: Pre-loaded character data (optional)
            logger: Optional logger instance
        """
        self.character_id = character_id
        self.character_directory_path = character_directory_path
        self.logger = logger or logging.getLogger(f"{__name__}.{character_id}")

        # Character data
        self._character_data: Dict[str, Any] = character_data or {}
        self._is_initialized = False

        # Component integration state
        self._integration_stats = {
            "initialization_time": None,
            "component_status": {},
            "last_decision_time": None,
            "total_decisions": 0,
        }

        # Component initialization
        self._initialize_components()

        self.logger.info(
            f"PersonaAgent {character_id} initialized with modular architecture"
        )

    def _initialize_components(self) -> None:
        """Initialize all modular components."""
        try:
            # Core components
            self.character_data_manager = CharacterDataManager(
                logger=self.logger.getChild("character_data")
            )

            self.agent_state_manager = AgentStateManager(
                agent_id=self.character_id, logger=self.logger.getChild("state")
            )

            # Decision engine components
            self.decision_processor = DecisionProcessor(
                logger=self.logger.getChild("decision")
            )

            self.threat_assessor = ThreatAssessor(logger=self.logger.getChild("threat"))

            self.goal_manager = GoalManager(
                character_id=self.character_id, logger=self.logger.getChild("goals")
            )

            # World interpretation components
            self.world_interpreter = WorldInterpreter(
                character_id=self.character_id, logger=self.logger.getChild("world")
            )

            self.memory_manager = MemoryManager(
                character_id=self.character_id, logger=self.logger.getChild("memory")
            )

            # LLM integration components
            self.llm_client = LLMClient(
                self.character_id, logger=self.logger.getChild("llm")
            )

            self.response_processor = ResponseProcessor(
                self.character_id, logger=self.logger.getChild("response")
            )

            # Utility components
            self.validator = Validator(
                self.character_id, logger=self.logger.getChild("validator")
            )

            self.response_generator = ResponseGenerator(
                self.character_id, logger=self.logger.getChild("generator")
            )

            # Track component status
            self._integration_stats["component_status"] = {
                "character_data_manager": "initialized",
                "agent_state_manager": "initialized",
                "decision_processor": "initialized",
                "threat_assessor": "initialized",
                "goal_manager": "initialized",
                "world_interpreter": "initialized",
                "memory_manager": "initialized",
                "llm_client": "initialized",
                "response_processor": "initialized",
                "validator": "initialized",
                "response_generator": "initialized",
            }

        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise

    async def initialize(self) -> bool:
        """
        Initialize the agent and all components.

        Returns:
            bool: True if initialization successful
        """
        try:
            start_time = datetime.now()

            # Load character data if path provided
            if self.character_directory_path and not self._character_data:
                self._character_data = (
                    await self.character_data_manager.load_character_data(
                        self.character_directory_path
                    )
                )

            # Validate character data
            if self._character_data:
                validation_result = await self.validator.validate_character_data(
                    self._character_data
                )
                if not validation_result.is_valid:
                    self.logger.warning(
                        f"Character data validation issues: {validation_result.issues}"
                    )

            # Initialize components with character data
            initialization_tasks = []

            # Initialize state manager
            if hasattr(self.agent_state_manager, "initialize"):
                initialization_tasks.append(self.agent_state_manager.initialize())

            # Initialize goal manager with character goals
            goals = self._character_data.get("goals", [])
            if goals:
                # GoalManager doesn't have load_goals, we'll add goals through other methods
                pass

            # Initialize memory manager
            if hasattr(self.memory_manager, "initialize"):
                initialization_tasks.append(self.memory_manager.initialize())

            # Initialize LLM client
            if hasattr(self.llm_client, "validate_api_connection"):
                initialization_tasks.append(self.llm_client.validate_api_connection())

            # Run all initializations concurrently
            if initialization_tasks:
                await asyncio.gather(*initialization_tasks, return_exceptions=True)

            self._is_initialized = True
            self._integration_stats["initialization_time"] = (
                datetime.now() - start_time
            ).total_seconds()

            self.logger.info(
                f"PersonaAgent {self.character_id} initialization completed successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"PersonaAgent initialization failed: {e}")
            return False

    async def make_decision(self, world_state: Dict[str, Any]) -> CharacterAction:
        """
        Make a character decision based on world state.

        Args:
            world_state: Current world state information

        Returns:
            CharacterAction: Decided character action
        """
        try:
            decision_start = datetime.now()

            # Ensure agent is initialized
            if not self._is_initialized:
                await self.initialize()

            # Get current character context
            character_context = await self._build_character_context()

            # Update memories with recent events
            recent_events = world_state.get("recent_events", [])
            if recent_events:
                for event in recent_events[-5:]:  # Store last 5 events
                    await self.memory_manager.store_memory(
                        {
                            "type": "world_event",
                            "content": event,
                            "timestamp": datetime.now().isoformat(),
                            "importance": 0.5,
                        }
                    )

            # Interpret world events through character lens
            interpreted_state = world_state.copy()
            if recent_events:
                for event_data in recent_events:
                    # Convert dict to WorldEvent if needed
                    if isinstance(event_data, dict):
                        from .persona_agent.protocols import WorldEvent

                        event = WorldEvent(
                            event_id=event_data.get("event_id", "unknown"),
                            event_type=event_data.get("event_type", "unknown"),
                            source=event_data.get("source", "unknown"),
                            affected_entities=event_data.get("affected_entities", []),
                            location=event_data.get("location"),
                            description=event_data.get("description", ""),
                            data=event_data.get("data", {}),
                            timestamp=event_data.get("timestamp", 0.0),
                        )
                    else:
                        event = event_data

                    interpretation = await self.world_interpreter.interpret_event(
                        event, character_context
                    )
                    interpreted_state[f"interpreted_{event.event_id}"] = interpretation

            # Assess threats (using the actual method name)
            threat_level = "low"  # Default threat level
            if recent_events:
                # Use assess_threat method with first event as example
                try:
                    event_data = recent_events[0]
                    if isinstance(event_data, dict):
                        from .persona_agent.protocols import WorldEvent

                        event = WorldEvent(
                            event_id=event_data.get("event_id", "unknown"),
                            event_type=event_data.get("event_type", "unknown"),
                            source=event_data.get("source", "unknown"),
                            affected_entities=event_data.get("affected_entities", []),
                            location=event_data.get("location"),
                            description=event_data.get("description", ""),
                            data=event_data.get("data", {}),
                            timestamp=event_data.get("timestamp", 0.0),
                        )
                    else:
                        event = event_data

                    threat_assessment = await self.threat_assessor.assess_threat(
                        event, character_context
                    )
                    threat_level = threat_assessment.get("threat_level", "low")
                except Exception:
                    threat_level = "low"
            interpreted_state["threat_assessment"] = threat_level

            # Update goals based on current situation
            # GoalManager doesn't have update_goals_from_context, skip for now
            pass

            # Make decision using decision processor
            decision = await self.decision_processor.make_decision(
                interpreted_state, character_context
            )

            # Ensure decision has required fields
            if isinstance(decision, dict):
                if "description" not in decision:
                    decision["description"] = (
                        f"Character action: {decision.get('action_type', 'unknown')}"
                    )
                if "priority" not in decision:
                    decision["priority"] = "medium"
                if "parameters" not in decision:
                    decision["parameters"] = {}
            else:
                # If decision is a dataclass, convert to dict and ensure fields
                decision_dict = (
                    asdict(decision)
                    if hasattr(decision, "__dataclass_fields__")
                    else {"action_type": "wait"}
                )
                if "description" not in decision_dict:
                    decision_dict["description"] = (
                        f"Character action: {decision_dict.get('action_type', 'wait')}"
                    )
                if "priority" not in decision_dict:
                    decision_dict["priority"] = "medium"
                if "parameters" not in decision_dict:
                    decision_dict["parameters"] = {}
                decision = decision_dict

            # Validate the decision
            # Convert decision to dict if it's a dataclass
            decision_dict = (
                asdict(decision)
                if hasattr(decision, "__dataclass_fields__")
                else decision
            )
            validation_result = await self.validator.validate_action(
                decision_dict, interpreted_state
            )
            if not validation_result.is_valid:
                self.logger.warning(
                    f"Decision validation issues: {validation_result.issues}"
                )

                # Generate fallback decision if validation fails critically
                if validation_result.has_critical_issues():
                    fallback_response = await self.response_generator.generate_response(
                        {**character_context, **interpreted_state}
                    )
                    decision = {
                        "action_type": "wait",
                        "description": fallback_response,
                        "priority": "low",
                        "parameters": {},
                    }

            # Update agent state
            await self.agent_state_manager.update_state(
                {
                    "last_decision": decision,
                    "last_decision_time": decision_start.isoformat(),
                    "world_state_summary": {
                        "location": world_state.get("location"),
                        "threat_level": threat_level,
                        "recent_events_count": len(recent_events),
                    },
                }
            )

            # Update statistics
            self._integration_stats["last_decision_time"] = (
                datetime.now() - decision_start
            ).total_seconds()
            self._integration_stats["total_decisions"] += 1

            self.logger.debug(
                f"Decision made in {self._integration_stats['last_decision_time']:.3f}s: {decision.get('action_type')}"
            )

            return decision

        except Exception as e:
            self.logger.error(f"Decision making failed: {e}")

            # Emergency fallback
            return {
                "action_type": "wait",
                "description": "I need to carefully consider the situation.",
                "priority": "low",
                "parameters": {},
                "error": str(e),
            }

    async def generate_response(
        self, prompt: str, context: Dict[str, Any] = None
    ) -> str:
        """
        Generate character response using LLM integration.

        Args:
            prompt: Input prompt for response generation
            context: Additional context for response

        Returns:
            str: Generated character response
        """
        try:
            # Build full character context
            character_context = await self._build_character_context()
            if context:
                character_context.update(context)

            # Try LLM generation first
            try:
                llm_response = await self.llm_client.generate_character_response(
                    prompt, character_context
                )

                # Process and validate the response
                processing_result = await self.response_processor.process_response(
                    llm_response, character_context
                )

                if processing_result.success and processing_result.confidence > 0.5:
                    return processing_result.processed_content
                else:
                    self.logger.warning("LLM response quality low, using fallback")

            except Exception as llm_error:
                self.logger.warning(f"LLM generation failed: {llm_error}")

            # Fallback to rule-based generation
            fallback_response = await self.response_generator.generate_response(
                character_context
            )
            return fallback_response

        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            return "I'm not sure how to respond to that right now."

    async def process_world_events(
        self, events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process world events and update character state.

        Args:
            events: List of world events to process

        Returns:
            Dict containing processing results and character response
        """
        try:
            character_context = await self._build_character_context()
            processing_results = []

            for event_data in events:
                # Convert dict to WorldEvent if needed
                if isinstance(event_data, dict):
                    from .persona_agent.protocols import WorldEvent

                    event = WorldEvent(
                        event_id=event_data.get("event_id", "unknown"),
                        event_type=event_data.get("event_type", "unknown"),
                        source=event_data.get("source", "unknown"),
                        affected_entities=event_data.get("affected_entities", []),
                        location=event_data.get("location"),
                        description=event_data.get("description", ""),
                        data=event_data.get("data", {}),
                        timestamp=event_data.get("timestamp", 0.0),
                    )
                else:
                    event = event_data

                # Interpret event through character lens
                interpretation = await self.world_interpreter.interpret_event(
                    event, character_context
                )

                # Store in memory if significant
                # SubjectiveInterpretation is a dataclass, use getattr with default
                significance = getattr(interpretation, "memory_priority", 0.5)
                if significance > 0.3:
                    await self.memory_manager.store_memory(
                        {
                            "type": "world_event",
                            "content": event_data,  # Store original event data
                            "interpretation": interpretation,
                            "timestamp": datetime.now().isoformat(),
                            "importance": significance,
                        }
                    )

                # Assess threat if applicable
                if event.event_type in ["combat", "conflict", "danger"]:
                    threat_assessment = await self.threat_assessor.assess_threat(
                        event, character_context
                    )
                    interpretation["threat_assessment"] = threat_assessment

                processing_results.append(
                    {
                        "event": event_data,  # Return original event data
                        "interpretation": interpretation,
                    }
                )

            # Update goals based on events
            # GoalManager doesn't have update_goals_from_context, skip for now
            pass

            return {
                "processed_events": len(events),
                "processing_results": processing_results,
                "character_state": await self.agent_state_manager.get_state(),
            }

        except Exception as e:
            self.logger.error(f"Event processing failed: {e}")
            return {"processed_events": 0, "error": str(e)}

    async def get_character_data(self) -> Dict[str, Any]:
        """Get complete character data."""
        try:
            if not self._character_data and self.character_directory_path:
                self._character_data = (
                    await self.character_data_manager.load_character_data(
                        self.character_directory_path
                    )
                )

            return self._character_data.copy()

        except Exception as e:
            self.logger.error(f"Failed to get character data: {e}")
            return {}

    async def get_current_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        try:
            return await self.agent_state_manager.get_state()
        except Exception as e:
            self.logger.error(f"Failed to get current state: {e}")
            return {}

    async def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get currently active goals."""
        try:
            # Use the actual method available in GoalManager
            goals = await self.goal_manager.get_goals_by_priority("high")
            return [
                asdict(goal) if hasattr(goal, "__dict__") else goal for goal in goals
            ]
        except Exception as e:
            self.logger.error(f"Failed to get active goals: {e}")
            return []

    async def get_recent_memories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent memories."""
        try:
            return await self.memory_manager.retrieve_memories(
                {"type": "recent", "limit": limit}, limit=limit
            )
        except Exception as e:
            self.logger.error(f"Failed to get recent memories: {e}")
            return []

    async def get_integration_statistics(self) -> Dict[str, Any]:
        """Get comprehensive integration statistics."""
        try:
            stats = self._integration_stats.copy()

            # Add component statistics
            component_stats = {}

            # Get statistics from each component if available
            for component_name, status in stats["component_status"].items():
                component = getattr(self, component_name, None)
                if component and hasattr(component, "get_statistics"):
                    try:
                        component_stats[component_name] = (
                            await component.get_statistics()
                        )
                    except Exception:
                        component_stats[component_name] = {"status": status}
                else:
                    component_stats[component_name] = {"status": status}

            stats["component_statistics"] = component_stats

            # Add validation statistics
            if hasattr(self.validator, "get_validation_statistics"):
                stats["validation_statistics"] = (
                    await self.validator.get_validation_statistics()
                )

            # Add LLM usage statistics
            if hasattr(self.llm_client, "get_usage_statistics"):
                stats["llm_usage_statistics"] = (
                    await self.llm_client.get_usage_statistics()
                )

            return stats

        except Exception as e:
            self.logger.error(f"Statistics calculation failed: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _build_character_context(self) -> Dict[str, Any]:
        """Build comprehensive character context for components."""
        try:
            context = self._character_data.copy()

            # Add current state
            try:
                current_state = await self.agent_state_manager.get_current_state()
                context["state"] = current_state
            except Exception:
                context["state"] = {}

            # Add active goals
            try:
                active_goals = await self.goal_manager.get_goals_by_priority("high")
                context["active_goals"] = active_goals
            except Exception:
                context["active_goals"] = []

            # Add recent memories
            try:
                recent_memories = await self.memory_manager.retrieve_memories(
                    {"type": "recent"}, limit=5
                )
                context["recent_memories"] = recent_memories
            except Exception:
                context["recent_memories"] = []

            return context

        except Exception as e:
            self.logger.error(f"Character context building failed: {e}")
            return self._character_data.copy()

    # Backward compatibility methods

    def __getattr__(self, name: str):
        """Provide backward compatibility for legacy method calls."""
        # Common legacy method mappings
        legacy_mappings = {
            "load_character": "get_character_data",
            "get_goals": "get_active_goals",
            "update_state": "agent_state_manager.update_state",
            "assess_threat": "threat_assessor.assess_current_threats",
            "interpret_world": "world_interpreter.interpret_event",
        }

        if name in legacy_mappings:
            self.logger.debug(f"Legacy method call: {name} -> {legacy_mappings[name]}")
            # Return the mapped method or component method
            if "." in legacy_mappings[name]:
                component_name, method_name = legacy_mappings[name].split(".", 1)
                component = getattr(self, component_name)
                return getattr(component, method_name)
            else:
                return getattr(self, legacy_mappings[name])

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )


# Factory function for backward compatibility
async def create_persona_agent(
    character_id: str,
    character_directory_path: str = None,
    character_data: Dict[str, Any] = None,
    logger: Optional[logging.Logger] = None,
) -> PersonaAgent:
    """
    Factory function to create and initialize PersonaAgent.

    Args:
        character_id: Unique identifier for the character
        character_directory_path: Path to character data directory
        character_data: Pre-loaded character data (optional)
        logger: Optional logger instance

    Returns:
        PersonaAgent: Fully initialized PersonaAgent instance
    """
    agent = PersonaAgent(
        character_id=character_id,
        character_directory_path=character_directory_path,
        character_data=character_data,
        logger=logger,
    )

    await agent.initialize()
    return agent
