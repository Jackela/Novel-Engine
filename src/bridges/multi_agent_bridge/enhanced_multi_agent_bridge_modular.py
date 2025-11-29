"""
Enhanced Multi-Agent Bridge (Modular)
=====================================

Modular implementation of the enhanced multi-agent bridge using component-based architecture.
Maintains full backward compatibility while providing enterprise-grade modularity.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import modular components
from .core.types import (
    CommunicationType,
    EnhancedWorldState,
    LLMCoordinationConfig,
)
from .dialogue import DialogueManager
from .llm_processing import LLMBatchProcessor
from .performance import CostTracker, PerformanceBudget, PerformanceMetrics

# Import existing Novel Engine components (no legacy fallbacks)
from shared_types import CharacterAction
from src.agents.chronicler_agent import ChroniclerAgent
from src.agents.director_agent import DirectorAgent
from src.event_bus import EventBus
from src.persona_agent import PersonaAgent

# Import advanced AI intelligence systems (required)
from src.ai_intelligence.agent_coordination_engine import AgentCoordinationEngine
from src.ai_intelligence.ai_orchestrator import AIIntelligenceOrchestrator

__all__ = ["EnhancedMultiAgentBridge"]


class EnhancedMultiAgentBridge:
    """
    Modular enhanced multi-agent bridge implementation.

    This class provides a facade over specialized components while maintaining
    full backward compatibility with the original enhanced multi-agent bridge interface.

    Components:
    - CostTracker: LLM cost management and budget enforcement
    - PerformanceBudget: Timing constraints and performance optimization
    - LLMBatchProcessor: Intelligent batching and processing of LLM requests
    - DialogueManager: Agent-to-agent communication and conversation coordination
    - PerformanceMetrics: Comprehensive performance tracking and analysis
    """

    def __init__(
        self,
        event_bus: EventBus,
        director_agent: Optional[DirectorAgent] = None,
        chronicler_agent: Optional[ChroniclerAgent] = None,
        coordination_config: Optional[LLMCoordinationConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize modular enhanced multi-agent bridge.

        Args:
            event_bus: Novel Engine event bus
            director_agent: Optional director agent
            chronicler_agent: Optional chronicler agent
            coordination_config: LLM coordination configuration
            logger: Optional logger instance
        """
        self.event_bus = event_bus
        self.director_agent = director_agent
        self.chronicler_agent = chronicler_agent
        self.config = coordination_config or LLMCoordinationConfig()
        self.logger = logger or logging.getLogger(__name__)

        # Agent registry
        self._agents: Dict[str, PersonaAgent] = {}
        self._agent_states: Dict[str, Dict[str, Any]] = {}

        # Integration state
        self._is_initialized = False
        self._integration_stats = {
            "initialization_time": None,
            "component_status": {},
            "total_turns_processed": 0,
            "successful_coordinations": 0,
        }

        # Initialize components
        self._initialize_components()

        self.logger.info(
            "Enhanced multi-agent bridge initialized with modular architecture"
        )

    def _initialize_components(self) -> None:
        """Initialize all modular components."""
        try:
            # Core performance components
            self.cost_tracker = CostTracker(
                max_cost_per_turn=self.config.max_cost_per_turn, max_total_cost=1.0
            )

            self.performance_budget = PerformanceBudget(
                max_turn_time_seconds=self.config.fast_mode_threshold,
                max_batch_time_seconds=self.config.batch_timeout_ms / 1000.0,
                max_llm_wait_seconds=20.0,
            )

            # LLM batch processor
            self.llm_processor = LLMBatchProcessor(
                cost_tracker=self.cost_tracker,
                performance_budget=self.performance_budget,
                max_batch_size=self.config.max_batch_size,
                batch_timeout_ms=self.config.batch_timeout_ms,
                logger=self.logger.getChild("llm_processor"),
            )

            # Dialogue manager
            self.dialogue_manager = DialogueManager(
                llm_processor=self.llm_processor,
                logger=self.logger.getChild("dialogue"),
            )

            # Performance metrics
            self.performance_metrics = PerformanceMetrics(
                cost_tracker=self.cost_tracker,
                performance_budget=self.performance_budget,
            )

            # Advanced AI systems (optional)
            self._ai_orchestrator = None
            self._coordination_engine = None

            # Track component status
            self._integration_stats["component_status"] = {
                "cost_tracker": "initialized",
                "performance_budget": "initialized",
                "llm_processor": "initialized",
                "dialogue_manager": "initialized",
                "performance_metrics": "initialized",
            }

        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise

    async def initialize_ai_systems(self) -> Dict[str, Any]:
        """Initialize advanced AI intelligence systems."""
        try:
            start_time = datetime.now()

            # Initialize LLM processor
            if not await self.llm_processor.initialize():
                self.logger.warning("LLM processor initialization failed")

            # Initialize AI orchestrator if available
            try:
                if AIIntelligenceOrchestrator is not type(
                    "AIIntelligenceOrchestrator", (), {}
                ):
                    self._ai_orchestrator = AIIntelligenceOrchestrator()
                    # Additional initialization would go here
            except Exception as e:
                self.logger.debug(f"AI orchestrator initialization failed: {e}")

            # Initialize coordination engine if available
            try:
                if AgentCoordinationEngine is not type(
                    "AgentCoordinationEngine", (), {}
                ):
                    self._coordination_engine = AgentCoordinationEngine()
                    # Additional initialization would go here
            except Exception as e:
                self.logger.debug(f"Coordination engine initialization failed: {e}")

            self._is_initialized = True
            self._integration_stats["initialization_time"] = (
                datetime.now() - start_time
            ).total_seconds()

            self.logger.info("AI systems initialization completed successfully")

            return {
                "success": True,
                "initialization_time": self._integration_stats["initialization_time"],
                "ai_orchestrator_available": self._ai_orchestrator is not None,
                "coordination_engine_available": self._coordination_engine is not None,
            }

        except Exception as e:
            self.logger.error(f"AI systems initialization failed: {e}")
            return {"success": False, "error": str(e)}

    async def enhanced_run_turn(
        self, turn_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute enhanced turn with multi-agent coordination.

        Args:
            turn_data: Optional turn data and context

        Returns:
            Dict containing enhanced turn results
        """
        try:
            turn_start = datetime.now()
            turn_number = turn_data.get("turn_number", 0) if turn_data else 0

            # Ensure system is initialized
            if not self._is_initialized:
                await self.initialize_ai_systems()

            # Start performance tracking
            self.performance_budget.start_turn()
            self.cost_tracker.start_new_turn()

            # Pre-turn analysis
            pre_turn_analysis = await self._analyze_pre_turn_state()

            # Prepare enhanced world state
            enhanced_world_state = await self._prepare_enhanced_world_state(turn_number)

            # Identify dialogue opportunities
            dialogue_opportunities = await self._identify_dialogue_opportunities()

            # Execute agent dialogues
            dialogue_results = []
            fast_mode = self._should_use_fast_mode()

            for opportunity in dialogue_opportunities:
                if self.performance_budget.get_remaining_time() < 1.0:
                    fast_mode = True  # Force fast mode if running out of time

                dialogue_id = await self.dialogue_manager.initiate_dialogue(
                    initiator_id=opportunity["initiator"],
                    target_id=opportunity["target"],
                    communication_type=CommunicationType(
                        opportunity.get("type", "dialogue")
                    ),
                    context=opportunity.get("context", {}),
                    max_exchanges=3 if not fast_mode else 1,
                )

                dialogue_result = await self.dialogue_manager.execute_dialogue(
                    dialogue_id, fast_mode=fast_mode
                )
                dialogue_results.append(dialogue_result)

            # Run base simulation turn if director agent is available
            base_turn_result = {}
            if self.director_agent and hasattr(self.director_agent, "run_turn"):
                try:
                    base_turn_result = await self.director_agent.run_turn(turn_data)
                except Exception as e:
                    self.logger.warning(f"Base turn execution failed: {e}")
                    base_turn_result = {"error": str(e)}

            # Post-turn analysis
            post_turn_analysis = await self._analyze_post_turn_results(
                base_turn_result, dialogue_results
            )

            # Update metrics
            coordination_count = len([r for r in dialogue_results if r.get("success")])
            self.performance_metrics.record_coordination_event(
                "turn_coordination",
                list(self._agents.keys()),
                post_turn_analysis.get("quality_score", 0.5),
                coordination_count > 0,
            )

            # Complete performance tracking
            turn_performance = self.performance_budget.complete_turn()
            self.performance_metrics.record_turn_metrics(
                turn_number,
                {
                    "dialogue_count": len(dialogue_results),
                    "successful_dialogues": coordination_count,
                    "fast_mode_used": fast_mode,
                },
            )

            # Generate enhanced turn summary
            enhanced_summary = await self._generate_enhanced_turn_summary(
                turn_number, base_turn_result, dialogue_results, post_turn_analysis
            )

            # Update integration stats
            self._integration_stats["total_turns_processed"] += 1
            self._integration_stats["successful_coordinations"] += coordination_count

            total_time = (datetime.now() - turn_start).total_seconds()
            self.logger.info(
                f"Enhanced turn {turn_number} completed in {total_time:.3f}s with {coordination_count} coordinations"
            )

            return {
                "success": True,
                "turn_number": turn_number,
                "base_result": base_turn_result,
                "dialogue_results": dialogue_results,
                "enhanced_summary": enhanced_summary,
                "coordination_count": coordination_count,
                "performance_data": turn_performance,
                "fast_mode_used": fast_mode,
                "total_time": total_time,
                "pre_turn_analysis": pre_turn_analysis,
                "post_turn_analysis": post_turn_analysis,
            }

        except Exception as e:
            self.logger.error(f"Enhanced turn execution failed: {e}")

            # Emergency cleanup
            self.performance_budget.complete_turn()

            return {
                "success": False,
                "error": str(e),
                "turn_number": turn_number if "turn_number" in locals() else 0,
            }

    async def initiate_agent_dialogue(
        self,
        initiator_id: str,
        target_id: str,
        communication_type: CommunicationType = CommunicationType.DIALOGUE,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Initiate dialogue between two agents."""
        try:
            dialogue_id = await self.dialogue_manager.initiate_dialogue(
                initiator_id=initiator_id,
                target_id=target_id,
                communication_type=communication_type,
                context=context,
            )

            result = await self.dialogue_manager.execute_dialogue(dialogue_id)

            return {"success": True, "dialogue_id": dialogue_id, "result": result}

        except Exception as e:
            self.logger.error(f"Error initiating agent dialogue: {e}")
            return {"success": False, "error": str(e)}

    def register_agent(self, agent_id: str, agent: PersonaAgent) -> None:
        """Register an agent with the bridge."""
        self._agents[agent_id] = agent
        self.dialogue_manager.update_agent_cache(
            agent_id,
            {
                "role": getattr(agent, "role", "Unknown"),
                "personality": getattr(agent, "personality", {}),
                "status": "active",
            },
        )
        self.logger.info(f"Registered agent {agent_id}")

    def get_coordination_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive coordination performance metrics."""
        try:
            return self.performance_metrics.get_comprehensive_metrics()
        except Exception as e:
            self.logger.error(f"Error getting coordination metrics: {e}")
            return {}

    async def get_enhanced_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get enhanced status for a specific agent."""
        try:
            agent = self._agents.get(agent_id)
            if not agent:
                return {"error": "agent_not_found", "agent_id": agent_id}

            # Get basic agent data
            basic_status = {}
            if hasattr(agent, "get_current_state"):
                basic_status = await agent.get_current_state()

            # Get dialogue participation
            dialogue_stats = self.dialogue_manager.get_dialogue_stats()

            return {
                "agent_id": agent_id,
                "basic_status": basic_status,
                "dialogue_participation": dialogue_stats.get(
                    "agent_interactions", {}
                ).get(agent_id, 0),
                "last_interaction": self._agent_states.get(agent_id, {}).get(
                    "last_interaction"
                ),
                "coordination_score": self._calculate_agent_coordination_score(
                    agent_id
                ),
            }

        except Exception as e:
            self.logger.error(f"Error getting enhanced agent status: {e}")
            return {"error": str(e), "agent_id": agent_id}

    async def get_system_intelligence_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive system intelligence dashboard."""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "system_status": (
                    "operational" if self._is_initialized else "initializing"
                ),
                "performance_metrics": self.performance_metrics.get_comprehensive_metrics(),
                "dialogue_stats": self.dialogue_manager.get_dialogue_stats(),
                "llm_processing_stats": self.llm_processor.get_processing_stats(),
                "active_agents": len(self._agents),
                "integration_stats": self._integration_stats,
                "ai_systems_status": {
                    "orchestrator_active": self._ai_orchestrator is not None,
                    "coordination_engine_active": self._coordination_engine is not None,
                },
            }

        except Exception as e:
            self.logger.error(f"Error generating intelligence dashboard: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _analyze_pre_turn_state(self) -> Dict[str, Any]:
        """Analyze state before turn execution."""
        try:
            return {
                "active_agents": len(self._agents),
                "budget_status": self.cost_tracker.get_cost_efficiency_stats(),
                "performance_status": self.performance_budget.get_performance_stats(),
                "system_health": self.performance_metrics._calculate_system_health_score(),
            }
        except Exception as e:
            self.logger.error(f"Pre-turn analysis failed: {e}")
            return {}

    async def _prepare_enhanced_world_state(
        self, turn_number: int
    ) -> EnhancedWorldState:
        """Prepare enhanced world state with coordination data."""
        try:
            return EnhancedWorldState(
                turn_number=turn_number,
                base_world_state={},  # Would be populated from director agent
                agent_positions={agent_id: {} for agent_id in self._agents.keys()},
                active_dialogues=self.dialogue_manager.get_active_dialogues(),
                performance_metrics=self.performance_metrics.get_comprehensive_metrics(),
            )
        except Exception as e:
            self.logger.error(f"Enhanced world state preparation failed: {e}")
            return EnhancedWorldState(turn_number=turn_number, base_world_state={})

    async def _identify_dialogue_opportunities(self) -> List[Dict[str, Any]]:
        """Identify opportunities for agent dialogues."""
        try:
            opportunities = []
            agents = list(self._agents.keys())

            # Simple opportunity identification - could be enhanced with AI
            for i, agent1 in enumerate(agents):
                for agent2 in agents[i + 1 :]:
                    # Basic opportunity criteria
                    if len(opportunities) < 2:  # Limit opportunities
                        opportunities.append(
                            {
                                "initiator": agent1,
                                "target": agent2,
                                "type": "dialogue",
                                "priority": 0.5,
                                "context": {},
                            }
                        )

            return opportunities

        except Exception as e:
            self.logger.error(f"Dialogue opportunity identification failed: {e}")
            return []

    def _should_use_fast_mode(self) -> bool:
        """Determine if fast mode should be used."""
        try:
            # Check performance constraints
            remaining_time = self.performance_budget.get_remaining_time()
            if remaining_time < self.config.fast_mode_threshold:
                return True

            # Check cost constraints
            if not self.cost_tracker.is_under_budget(
                0.02
            ):  # Reserve for remaining operations
                return True

            return False

        except Exception:
            return True  # Default to fast mode on errors

    async def _analyze_post_turn_results(
        self, base_turn_result: Dict[str, Any], dialogue_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze results after turn execution."""
        try:
            successful_dialogues = sum(
                1 for result in dialogue_results if result.get("success", False)
            )
            total_dialogues = len(dialogue_results)

            return {
                "base_turn_success": base_turn_result.get("success", False),
                "dialogue_success_rate": (
                    successful_dialogues / max(1, total_dialogues)
                )
                * 100,
                "coordination_effectiveness": successful_dialogues
                / max(1, len(self._agents)),
                "quality_score": sum(
                    result.get("quality", 0.5)
                    for result in dialogue_results
                    if "quality" in result
                )
                / max(1, total_dialogues),
            }

        except Exception as e:
            self.logger.error(f"Post-turn analysis failed: {e}")
            return {}

    async def _generate_enhanced_turn_summary(
        self,
        turn_number: int,
        base_turn_result: Dict[str, Any],
        dialogue_results: List[Dict[str, Any]],
        post_turn_analysis: Dict[str, Any],
    ) -> str:
        """Generate enhanced turn summary."""
        try:
            successful_dialogues = sum(
                1 for result in dialogue_results if result.get("success", False)
            )

            summary_parts = [
                f"Turn {turn_number} Summary:",
                f"• {successful_dialogues}/{len(dialogue_results)} successful agent interactions",
                f"• Coordination effectiveness: {post_turn_analysis.get('coordination_effectiveness', 0):.1%}",
                f"• System health: {self.performance_metrics._calculate_system_health_score():.1%}",
            ]

            if base_turn_result.get("success"):
                summary_parts.append("• Base simulation: Successful")

            return "\n".join(summary_parts)

        except Exception as e:
            self.logger.error(f"Enhanced summary generation failed: {e}")
            return f"Turn {turn_number} completed with errors"

    def _calculate_agent_coordination_score(self, agent_id: str) -> float:
        """Calculate coordination score for an agent."""
        try:
            # Simple coordination score based on participation
            interactions = self.performance_metrics._coordination_stats[
                "agent_interactions"
            ]
            agent_interactions = interactions.get(agent_id, 0)
            total_interactions = sum(interactions.values())

            if total_interactions == 0:
                return 0.0

            return min(1.0, agent_interactions / total_interactions * len(self._agents))

        except Exception:
            return 0.5

    async def shutdown_coordination_systems(self) -> None:
        """Shutdown all coordination systems gracefully."""
        try:
            # Shutdown components in reverse order
            await self.dialogue_manager.shutdown()
            await self.llm_processor.shutdown()

            self.logger.info("Enhanced multi-agent bridge shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during coordination systems shutdown: {e}")

    # Backward compatibility methods

    def __getattr__(self, name: str):
        """Provide backward compatibility for legacy method calls."""
        # Common legacy method mappings
        legacy_mappings = {
            "queue_llm_request": "llm_processor.queue_llm_request",
            "get_dialogue_stats": "dialogue_manager.get_dialogue_stats",
            "get_performance_stats": "performance_metrics.get_comprehensive_metrics",
        }

        if name in legacy_mappings:
            self.logger.debug(f"Legacy method call: {name} -> {legacy_mappings[name]}")
            # Return the mapped method
            if "." in legacy_mappings[name]:
                component_name, method_name = legacy_mappings[name].split(".", 1)
                component = getattr(self, component_name)
                return getattr(component, method_name)
            else:
                return getattr(self, legacy_mappings[name])

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )


# Factory functions for backward compatibility
def create_enhanced_multi_agent_bridge(
    event_bus: EventBus,
    director_agent: Optional[DirectorAgent] = None,
    chronicler_agent: Optional[ChroniclerAgent] = None,
    coordination_config: Optional[LLMCoordinationConfig] = None,
    logger: Optional[logging.Logger] = None,
) -> EnhancedMultiAgentBridge:
    """
    Factory function to create enhanced multi-agent bridge.

    Args:
        event_bus: Novel Engine event bus
        director_agent: Optional director agent
        chronicler_agent: Optional chronicler agent
        coordination_config: LLM coordination configuration
        logger: Optional logger instance

    Returns:
        EnhancedMultiAgentBridge: Fully configured bridge instance
    """
    return EnhancedMultiAgentBridge(
        event_bus=event_bus,
        director_agent=director_agent,
        chronicler_agent=chronicler_agent,
        coordination_config=coordination_config,
        logger=logger,
    )


def create_performance_optimized_config(
    max_turn_time_seconds: float = 5.0,
    max_cost_per_turn: float = 0.10,
    enable_fast_mode: bool = True,
) -> LLMCoordinationConfig:
    """
    Create performance-optimized coordination configuration.

    Args:
        max_turn_time_seconds: Maximum turn execution time
        max_cost_per_turn: Maximum LLM cost per turn
        enable_fast_mode: Whether to enable fast mode fallbacks

    Returns:
        LLMCoordinationConfig: Optimized configuration
    """
    return LLMCoordinationConfig(
        enable_smart_batching=True,
        max_batch_size=3 if enable_fast_mode else 5,
        batch_timeout_ms=100 if enable_fast_mode else 150,
        max_cost_per_turn=max_cost_per_turn,
        enable_dialogue_intelligence=True,
        fast_mode_threshold=max_turn_time_seconds * 0.6,
        cost_optimization_level="balanced",
        enable_performance_monitoring=True,
    )
