"""Bridge Core Module.

Main orchestration class that coordinates all components of the enhanced multi-agent bridge.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import structlog

from src.agents.director_agent_integrated import DirectorAgent
from src.core.event_bus import EventBus
from src.core.llm_service import CostControl, LLMRequest, get_llm_service

from .dialogue_manager import DialogueManager
from .state_manager import StateManager
from .task_scheduler import TaskScheduler
from .types import (
    BridgeConfiguration,
    CommunicationType,
    CostTracker,
    LLMBatchRequest,
    LLMCoordinationConfig,
    PerformanceBudget,
    RequestPriority,
)

logger = structlog.get_logger(__name__)


class EnhancedMultiAgentBridge:
    """
    Enhanced bridge connecting Novel Engine core with advanced AI intelligence systems.

    Provides real-time agent communication, coordination, and narrative intelligence
    while maintaining backward compatibility with existing simulation flow.
    """

    def __init__(
        self,
        director_or_event_bus: Union[DirectorAgent, EventBus],
        config_or_director: Optional[Union[BridgeConfiguration, DirectorAgent]] = None,
        llm_coordination_config: Optional[LLMCoordinationConfig] = None,
    ) -> None:
        """
        Initialize the Enhanced Multi-Agent Bridge.

        Args:
            director_or_event_bus: Core event bus for agent communication or DirectorAgent
            config_or_director: Optional existing director agent or bridge configuration
            llm_coordination_config: Configuration for LLM-powered coordination
        """
        # Flexible init to support legacy tests
        if isinstance(director_or_event_bus, EventBus):
            event_bus: EventBus = director_or_event_bus
            director_agent = (
                config_or_director
                if isinstance(config_or_director, DirectorAgent)
                else None
            )
            self.llm_config = llm_coordination_config or LLMCoordinationConfig()
        else:
            director_agent = director_or_event_bus
            config = (
                config_or_director
                if isinstance(config_or_director, BridgeConfiguration)
                else None
            )
            event_bus = getattr(director_agent, "event_bus", EventBus())
            self.llm_config = (
                config.llm_coordination
                if isinstance(config, BridgeConfiguration)
                else LLMCoordinationConfig()
            )

        self.event_bus = event_bus
        self.director_agent = director_agent

        # Initialize LLM service
        self.llm_service = get_llm_service(
            CostControl(
                daily_budget=self.llm_config.dialogue_generation_budget * 24,
                hourly_limit=100,
                rate_limit_enabled=self.llm_config.cost_tracking_enabled,
            )
        )

        # Initialize core components
        self.cost_tracker = CostTracker(
            hourly_budget=self.llm_config.dialogue_generation_budget,
            daily_budget=self.llm_config.dialogue_generation_budget * 24,
        )

        self.performance_budget = PerformanceBudget(
            max_turn_time=self.llm_config.max_turn_time_seconds
        )

        # Coordination stats
        self.coordination_stats: Dict[str, Any] = {
            "total_llm_calls": 0,
            "batch_efficiency": 0.0,
            "cost_savings": 0.0,
            "dialogue_quality_score": 0.0,
            "batched_requests": 0,
            "priority_bypasses": 0,
            "budget_violations": 0,
            "average_batch_size": 0.0,
            "cost_per_request": 0.0,
            "performance_score": 1.0,
        }

        # Initialize subsystems
        self.dialogue_manager = DialogueManager(
            self.llm_config, self.performance_budget
        )
        self.state_manager = StateManager()
        self.task_scheduler = TaskScheduler(self.llm_config, self.performance_budget)

        # AI orchestrator placeholder
        self.ai_orchestrator: Any = None

        # State
        self.active_dialogues: Dict[str, Any] = {}
        self.agent_relationships: Dict[str, Dict[str, float]] = {}
        self.narrative_intelligence: Dict[str, Any] = {}
        self._initialized = False
        self._shutdown_requested = False

        # Setup event handlers
        try:
            self._setup_enhanced_event_handlers()
        except Exception:
            pass

        logger.info(
            "Enhanced Multi-Agent Bridge initialized with AI intelligence integration"
        )

    async def initialize(self) -> bool:
        """Lightweight initialization used by tests."""
        self._initialized = True
        return True

    def _setup_enhanced_event_handlers(self) -> None:
        """Setup enhanced event handlers for agent communication."""
        self.event_bus.subscribe(
            "AGENT_DIALOGUE_REQUEST", self._handle_dialogue_request
        )
        self.event_bus.subscribe(
            "AGENT_RELATIONSHIP_UPDATE", self._handle_relationship_update
        )
        self.event_bus.subscribe(
            "NARRATIVE_PRESSURE_CHANGE", self._handle_narrative_pressure
        )
        self.event_bus.subscribe("AI_INSIGHT_GENERATED", self._handle_ai_insight)

    async def queue_llm_request(
        self,
        request_type: str,
        prompt: str,
        context: Dict[str, Any],
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout_seconds: float = 5.0,
    ) -> Dict[str, Any]:
        """Queue an LLM request with smart batching and priority handling."""
        try:
            request_id = f"{request_type}_{datetime.now().strftime('%H%M%S%f')}"

            # Estimate cost and tokens
            estimated_tokens = len(prompt.split()) * 1.3
            estimated_cost = estimated_tokens * 0.00001

            # Check budget
            if not self._check_budget_availability(estimated_cost):
                return {
                    "success": False,
                    "error": "Budget exceeded",
                    "budget_status": self._get_budget_status(),
                }

            batch_request = LLMBatchRequest(
                request_id=request_id,
                priority=priority,
                request_type=request_type,
                prompt=prompt,
                context=context,
                created_at=time.time(),
                timeout_seconds=timeout_seconds,
                estimated_cost=estimated_cost,
                tokens_estimate=int(estimated_tokens),
            )

            return await self.task_scheduler.submit_request(
                batch_request, self._process_immediate_request
            )

        except Exception as e:
            logger.error(f"Failed to queue LLM request: {e}")
            return {"success": False, "error": str(e)}

    async def _process_immediate_request(
        self, batch_request: LLMBatchRequest
    ) -> Dict[str, Any]:
        """Process high-priority request immediately."""
        start_time = time.time()

        try:
            if self.performance_budget.is_budget_exceeded():
                self.coordination_stats["budget_violations"] += 1
                return {
                    "success": False,
                    "error": "Turn time budget exceeded",
                    "request_id": batch_request.request_id,
                }

            llm_request = LLMRequest(
                prompt=batch_request.prompt,
                response_format="text",
                temperature=0.8,
                requester="llm_coordination",
            )

            response = await self.llm_service.generate_response(llm_request)

            processing_time = time.time() - start_time
            self.performance_budget.record_llm_time(processing_time)

            actual_cost = (
                response.cost
                if hasattr(response, "cost")
                else batch_request.estimated_cost
            )
            actual_tokens = (
                response.tokens_used
                if hasattr(response, "tokens_used")
                else batch_request.tokens_estimate
            )

            self.cost_tracker.update_cost(
                batch_request.request_type, actual_cost, actual_tokens
            )

            self.coordination_stats["total_llm_calls"] += 1
            self.coordination_stats["cost_per_request"] = (
                self.cost_tracker.average_cost_per_request
            )

            return {
                "success": True,
                "request_id": batch_request.request_id,
                "response": response.content,
                "processing_time": processing_time,
                "cost": actual_cost,
                "tokens_used": actual_tokens,
                "processed_immediately": True,
            }

        except Exception as e:
            logger.error(f"Immediate request processing failed: {e}")
            return {
                "success": False,
                "request_id": batch_request.request_id,
                "error": str(e),
            }

    def _check_budget_availability(self, estimated_cost: float) -> bool:
        """Check if request can proceed within budget."""
        current_hour_remaining = (
            self.cost_tracker.hourly_budget - self.cost_tracker.current_hour_spend
        )
        current_day_remaining = (
            self.cost_tracker.daily_budget - self.cost_tracker.current_day_spend
        )
        return (
            estimated_cost <= current_hour_remaining
            and estimated_cost <= current_day_remaining
        )

    def _get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        hour_usage = self.cost_tracker.current_hour_spend / max(
            0.01, self.cost_tracker.hourly_budget
        )
        day_usage = self.cost_tracker.current_day_spend / max(
            0.01, self.cost_tracker.daily_budget
        )

        return {
            "hourly_usage_percent": min(100, hour_usage * 100),
            "daily_usage_percent": min(100, day_usage * 100),
            "remaining_hourly_budget": max(
                0,
                self.cost_tracker.hourly_budget - self.cost_tracker.current_hour_spend,
            ),
            "remaining_daily_budget": max(
                0, self.cost_tracker.daily_budget - self.cost_tracker.current_day_spend
            ),
            "total_requests_today": self.cost_tracker.total_requests,
            "average_cost_per_request": self.cost_tracker.average_cost_per_request,
        }

    async def enhanced_run_turn(
        self, turn_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Enhanced turn execution with AI intelligence."""
        try:
            self.performance_budget.start_turn()

            turn_start_time = datetime.now()
            turn_number = (turn_data or {}).get("turn_number", 0)

            logger.info(f"=== ENHANCED TURN {turn_number} START ===")

            # Pre-turn analysis
            pre_turn_analysis = self.state_manager.analyze_pre_turn_state(
                self.agent_relationships
            )

            # Prepare world state (side effect: updates internal state)
            self.state_manager.prepare_enhanced_world_state(
                turn_number,
                self.agent_relationships,
                list(self.active_dialogues.values()),
            )

            # Identify dialogue opportunities
            opportunities = self.state_manager.identify_dialogue_opportunities(
                self.active_dialogues, self.narrative_intelligence
            )

            # Execute dialogues
            dialogue_results: List[Dict[str, Any]] = []
            max_dialogues = 3

            for opportunity in opportunities[:max_dialogues]:
                if self.performance_budget.is_budget_exceeded():
                    logger.warning("Turn time budget exceeded, skipping dialogues")
                    break

                if opportunity["probability"] > 0.7:
                    dialogue = await self.dialogue_manager.create_dialogue(
                        opportunity["participants"][0],
                        opportunity["participants"][1],
                        CommunicationType(opportunity["type"]),
                        opportunity.get("context"),
                    )
                    self.active_dialogues[dialogue.dialogue_id] = dialogue

                    result = await self.dialogue_manager.execute_dialogue(
                        dialogue,
                        self.queue_llm_request,
                        self.dialogue_manager.simulate_dialogue,
                    )
                    dialogue_results.append(result)

                    remaining_time = self.performance_budget.get_remaining_time()
                    if remaining_time < 1.0:
                        break

            # Standard turn execution
            base_turn_result: Dict[str, Any]
            if self.director_agent:
                base_turn_result = self.director_agent.run_turn()
            else:
                base_turn_result = {
                    "status": "turn_started",
                    "turn_number": turn_number,
                    "timestamp": turn_start_time.isoformat(),
                }

            # Post-turn analysis
            post_turn_analysis = self.state_manager.analyze_post_turn_results(
                base_turn_result, dialogue_results
            )

            # Update relationships and narrative state
            await self._update_agent_relationships(dialogue_results)
            self.state_manager.update_narrative_intelligence(post_turn_analysis)

            # Generate summary
            remaining_time = self.performance_budget.get_remaining_time()
            if remaining_time > 0.5:
                turn_summary = self._generate_enhanced_turn_summary(
                    turn_number,
                    base_turn_result,
                    dialogue_results,
                    pre_turn_analysis,
                    post_turn_analysis,
                )
            else:
                turn_summary = self._generate_fast_turn_summary(
                    turn_number, base_turn_result, dialogue_results
                )

            execution_time = (datetime.now() - turn_start_time).total_seconds()

            return {
                "success": True,
                "turn_number": turn_number,
                "timestamp": turn_start_time.isoformat(),
                "execution_time": execution_time,
                "base_turn_result": base_turn_result,
                "dialogue_results": dialogue_results,
                "enhanced": True,
                "turn_summary": turn_summary,
            }

        except Exception as e:
            logger.error(f"Enhanced turn execution failed: {e}")
            return {
                "success": False,
                "turn_number": turn_data.get("turn_number", 0) if turn_data else 0,
                "error": str(e),
            }

    async def _update_agent_relationships(
        self, dialogue_results: List[Dict[str, Any]]
    ) -> None:
        """Update agent relationships based on dialogue results."""
        for dialogue_result in dialogue_results:
            if dialogue_result.get("relationship_impact"):
                for relationship_key, change in dialogue_result[
                    "relationship_impact"
                ].items():
                    agent_a, agent_b = relationship_key.split("_")

                    if agent_a not in self.agent_relationships:
                        self.agent_relationships[agent_a] = {}

                    current_value = self.agent_relationships[agent_a].get(agent_b, 0.0)
                    new_value = max(-1.0, min(1.0, current_value + change))
                    self.agent_relationships[agent_a][agent_b] = new_value

    def _generate_enhanced_turn_summary(
        self,
        turn_number: int,
        base_turn_result: Dict[str, Any],
        dialogue_results: List[Dict[str, Any]],
        pre_turn_analysis: Dict[str, Any],
        post_turn_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive turn summary."""
        return {
            "turn_number": turn_number,
            "timestamp": datetime.now().isoformat(),
            "base_simulation": {
                "status": base_turn_result.get("status"),
                "participants": base_turn_result.get("participants", []),
            },
            "enhanced_features": {
                "dialogues_executed": len(dialogue_results),
                "successful_dialogues": len(
                    [d for d in dialogue_results if d.get("success")]
                ),
                "relationship_changes": len(
                    post_turn_analysis.get("relationship_changes", [])
                ),
                "narrative_insights": len(
                    post_turn_analysis.get("narrative_insights", [])
                ),
            },
        }

    def _generate_fast_turn_summary(
        self,
        turn_number: int,
        base_turn_result: Dict[str, Any],
        dialogue_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate a fast turn summary when time is limited."""
        return {
            "turn_number": turn_number,
            "timestamp": datetime.now().isoformat(),
            "summary_type": "fast",
            "base_simulation": {"status": base_turn_result.get("status", "completed")},
            "enhanced_features": {
                "dialogues_executed": len(dialogue_results),
                "successful_dialogues": len(
                    [d for d in dialogue_results if d.get("success")]
                ),
            },
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown coordination systems."""
        self._shutdown_requested = True
        await self.task_scheduler.stop()
        await self.shutdown_coordination_systems()

    async def shutdown_coordination_systems(self) -> None:
        """Shutdown coordination systems."""
        try:
            remaining = self.task_scheduler.get_remaining_requests()
            if remaining:
                logger.info(f"Processing {len(remaining)} remaining requests")

            logger.info("LLM coordination systems shut down gracefully")
        except Exception as e:
            logger.error(f"Error during coordination system shutdown: {e}")

    async def get_bridge_status(self) -> Dict[str, Any]:
        """Return bridge status."""
        return {
            "initialized": self._initialized,
            "components": {
                "dialogue_manager": self.dialogue_manager is not None,
                "task_scheduler": self.task_scheduler is not None,
                "ai_orchestrator": self.ai_orchestrator is not None,
            },
            "metrics": self.get_coordination_performance_metrics(),
        }

    def get_coordination_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        budget_status = self._get_budget_status()

        avg_batch_time = sum(self.performance_budget.batch_timings[-10:]) / max(
            1, len(self.performance_budget.batch_timings[-10:])
        )
        avg_llm_time = sum(self.performance_budget.llm_call_timings[-10:]) / max(
            1, len(self.performance_budget.llm_call_timings[-10:])
        )

        performance_score = 1.0
        if avg_batch_time > self.performance_budget.max_batch_time:
            performance_score *= 0.8
        if avg_llm_time > self.performance_budget.max_llm_call_time:
            performance_score *= 0.8
        if self.performance_budget.budget_violations > 0:
            performance_score *= max(
                0.3, 1.0 - (self.performance_budget.budget_violations * 0.1)
            )

        self.coordination_stats["performance_score"] = performance_score

        return {
            "coordination_stats": self.coordination_stats.copy(),
            "budget_status": budget_status,
            "performance_metrics": {
                "average_batch_time": avg_batch_time,
                "average_llm_call_time": avg_llm_time,
                "budget_violations": self.performance_budget.budget_violations,
                "performance_score": performance_score,
            },
        }

    # Event handlers
    async def _handle_dialogue_request(self, request_data: Dict[str, Any]) -> None:
        """Handle dialogue requests from agents."""
        try:
            initiator = request_data.get("initiator")
            target = request_data.get("target")
            context = request_data.get("context", {})

            if initiator and target:
                dialogue = await self.dialogue_manager.create_dialogue(
                    initiator,
                    target,
                    CommunicationType(context.get("type", "dialogue")),
                    context,
                )
                self.active_dialogues[dialogue.dialogue_id] = dialogue

                result = await self.dialogue_manager.execute_dialogue(
                    dialogue,
                    self.queue_llm_request,
                    self.dialogue_manager.simulate_dialogue,
                )

                self.event_bus.emit(
                    "DIALOGUE_RESULT",
                    {"request_id": request_data.get("request_id"), "result": result},
                )

        except Exception as e:
            logger.error(f"Error handling dialogue request: {e}")

    async def _handle_relationship_update(self, update_data: Dict[str, Any]) -> None:
        """Handle relationship update events."""
        agent_a = update_data.get("agent_a")
        agent_b = update_data.get("agent_b")
        change = update_data.get("change", 0.0)

        if agent_a and agent_b:
            if agent_a not in self.agent_relationships:
                self.agent_relationships[agent_a] = {}

            current_value = self.agent_relationships[agent_a].get(agent_b, 0.0)
            new_value = max(-1.0, min(1.0, current_value + change))
            self.agent_relationships[agent_a][agent_b] = new_value

    async def _handle_narrative_pressure(self, pressure_data: Dict[str, Any]) -> None:
        """Handle narrative pressure changes."""
        self.state_manager.handle_narrative_pressure(pressure_data)

    async def _handle_ai_insight(self, insight_data: Dict[str, Any]) -> None:
        """Handle AI-generated insights."""
        self.state_manager.handle_ai_insight(insight_data)


# Factory functions
async def create_enhanced_bridge(
    director_agent: DirectorAgent, config: Optional[BridgeConfiguration] = None
) -> EnhancedMultiAgentBridge:
    """Factory to create and initialize the enhanced bridge for tests."""
    bridge = EnhancedMultiAgentBridge(director_agent, config)
    success = await bridge.initialize()
    if not success:
        raise RuntimeError("Failed to initialize enhanced multi-agent bridge")
    return bridge


def create_enhanced_multi_agent_bridge(
    event_bus: EventBus,
    director_agent: Optional[DirectorAgent] = None,
    llm_coordination_config: Optional[LLMCoordinationConfig] = None,
) -> EnhancedMultiAgentBridge:
    """Factory function to create and configure an Enhanced Multi-Agent Bridge."""
    if llm_coordination_config is None:
        llm_coordination_config = LLMCoordinationConfig()

    bridge = EnhancedMultiAgentBridge(
        event_bus, director_agent, llm_coordination_config
    )
    logger.info("Enhanced Multi-Agent Bridge created with advanced LLM coordination")
    return bridge


__all__ = [
    "EnhancedMultiAgentBridge",
    "create_enhanced_bridge",
    "create_enhanced_multi_agent_bridge",
]
