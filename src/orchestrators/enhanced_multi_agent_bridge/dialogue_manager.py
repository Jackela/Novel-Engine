"""Dialogue Manager Module.

Manages agent dialogues, execution, and quality tracking.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

if TYPE_CHECKING:
    from .types import (
        AgentDialogue,
        CommunicationType,
        LLMCoordinationConfig,
        PerformanceBudget,
        RequestPriority,
    )

logger = structlog.get_logger(__name__)


class DialogueManager:
    """Manages agent dialogues and their execution."""

    def __init__(
        self,
        llm_config: LLMCoordinationConfig,
        performance_budget: PerformanceBudget,
    ) -> None:
        """Initialize the dialogue manager.

        Args:
            llm_config: LLM coordination configuration
            performance_budget: Performance budget tracker
        """
        self.llm_config = llm_config
        self.performance_budget = performance_budget
        self.active_dialogues: Dict[str, AgentDialogue] = {}
        self.communication_history: List[Dict[str, Any]] = []
        self.coordination_stats: Dict[str, Any] = {
            "dialogue_quality_score": 0.0,
            "total_llm_calls": 0,
        }

    async def create_dialogue(
        self,
        initiator_id: str,
        target_id: str,
        communication_type: CommunicationType,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentDialogue:
        """Create a new dialogue between two agents."""
        from .types import AgentDialogue, DialogueState

        dialogue_id = (
            f"dialogue_{initiator_id}_{target_id}_{datetime.now().strftime('%H%M%S')}"
        )

        dialogue = AgentDialogue(
            dialogue_id=dialogue_id,
            communication_type=communication_type,
            participants=[initiator_id, target_id],
            initiator=initiator_id,
            state=DialogueState.INITIATING,
            context=context or {},
        )

        self.active_dialogues[dialogue_id] = dialogue
        return dialogue

    async def execute_dialogue(
        self,
        dialogue: AgentDialogue,
        llm_callback: Any,
        simulate_callback: Any,
    ) -> Dict[str, Any]:
        """Execute a dialogue between agents.

        Args:
            dialogue: The dialogue to execute
            llm_callback: Callback for LLM processing
            simulate_callback: Callback for simulation fallback

        Returns:
            Dialogue result
        """
        from .types import DialogueState

        try:
            dialogue.state = DialogueState.ACTIVE

            # Check performance budget
            if self.performance_budget.is_budget_exceeded():
                self.coordination_stats["budget_violations"] = (
                    self.coordination_stats.get("budget_violations", 0) + 1
                )
                logger.warning(
                    f"Turn time budget exceeded, falling back to fast dialogue for {dialogue.dialogue_id}"
                )
                dialogue_result = await simulate_callback(dialogue, fast_mode=True)
                return dialogue_result  # type: ignore[no-any-return]

            # Determine priority
            priority = self._determine_priority(dialogue)

            # Create dialogue prompt
            prompt = self._create_dialogue_prompt(dialogue)

            # Queue LLM request
            remaining_time = self.performance_budget.get_remaining_time()
            llm_result = await llm_callback(
                request_type="dialogue",
                prompt=prompt,
                context={
                    "dialogue_id": dialogue.dialogue_id,
                    "participants": dialogue.participants,
                    "communication_type": dialogue.communication_type.value,
                    "max_exchanges": dialogue.max_exchanges,
                    "context": dialogue.context,
                },
                priority=priority,
                timeout_seconds=min(remaining_time - 0.5, dialogue.max_exchanges * 0.5),
            )

            if llm_result.get("success"):
                dialogue_outcome = self._process_result(dialogue, llm_result)

                # Update quality score
                quality_score = self._calculate_quality(dialogue_outcome, llm_result)
                dialogue_outcome["quality_score"] = quality_score

                # Update stats
                current_avg = self.coordination_stats.get("dialogue_quality_score", 0.0)
                total_dialogues = self.coordination_stats.get("total_llm_calls", 0) + 1
                self.coordination_stats["dialogue_quality_score"] = (
                    current_avg * (total_dialogues - 1) + quality_score
                ) / total_dialogues

                dialogue.state = DialogueState.CONCLUDED
                dialogue.resolution = dialogue_outcome

                return dialogue_outcome
            else:
                logger.warning(
                    f"LLM dialogue generation failed for {dialogue.dialogue_id}"
                )
                dialogue.state = DialogueState.FAILED
                dialogue_result = await simulate_callback(dialogue, fast_mode=True)
                return dialogue_result  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Dialogue execution failed: {e}")
            dialogue.state = DialogueState.FAILED
            return {"success": False, "error": str(e)}

    def _determine_priority(self, dialogue: AgentDialogue) -> RequestPriority:
        """Determine priority for dialogue based on type and context."""
        from .types import CommunicationType, RequestPriority

        # Critical dialogues
        if dialogue.communication_type in [CommunicationType.NEGOTIATION]:
            return RequestPriority.HIGH

        # Important story dialogues
        if dialogue.context.get("narrative_requirement"):
            return RequestPriority.HIGH

        # Relationship-driven dialogues
        relationship_tension = abs(dialogue.context.get("relationship_tension", 0))
        if relationship_tension > 0.7:
            return RequestPriority.HIGH
        elif relationship_tension > 0.4:
            return RequestPriority.NORMAL

        return RequestPriority.NORMAL

    def _create_dialogue_prompt(self, dialogue: AgentDialogue) -> str:
        """Create optimized prompt for dialogue generation."""
        participants = dialogue.participants
        comm_type = dialogue.communication_type.value
        context = dialogue.context

        prompt_parts = [
            f"Generate a {comm_type} between {participants[0]} and {participants[1]}.",
            f"Maximum exchanges: {dialogue.max_exchanges}",
        ]

        # Add relationship context
        if "relationship_tension" in context:
            tension = context["relationship_tension"]
            if tension < -0.5:
                prompt_parts.append(
                    f"These characters have high conflict (tension: {tension:.2f})"
                )
            elif tension > 0.5:
                prompt_parts.append(
                    f"These characters have positive relationship (strength: {tension:.2f})"
                )

        # Add narrative context
        if context.get("narrative_requirement"):
            prompt_parts.append("This dialogue is important for story progression.")

        # Add dialogue type specific guidance
        from .types import CommunicationType

        if dialogue.communication_type == CommunicationType.NEGOTIATION:
            prompt_parts.append("Focus on conflict resolution and compromise.")
        elif dialogue.communication_type == CommunicationType.COLLABORATION:
            prompt_parts.append("Focus on teamwork and shared goals.")
        elif dialogue.communication_type == CommunicationType.EMOTIONAL:
            prompt_parts.append("Focus on emotional expression and connection.")

        prompt_parts.append("Provide realistic, character-appropriate dialogue.")

        return "\n".join(prompt_parts)

    def _process_result(
        self, dialogue: AgentDialogue, llm_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process LLM-generated dialogue result."""
        outcome = {
            "success": True,
            "dialogue_id": dialogue.dialogue_id,
            "participants": dialogue.participants,
            "communication_type": dialogue.communication_type.value,
            "llm_generated": True,
            "processing_time": llm_result.get("processing_time", 0),
            "cost": llm_result.get("cost", 0),
            "response": llm_result.get("response", ""),
            "relationship_impact": {},
            "narrative_impact": {},
            "resolution": "completed",
        }

        # Parse dialogue content and calculate relationship impacts
        dialogue_content = llm_result.get("response", "")

        # Simple sentiment analysis
        positive_indicators = [
            "agree",
            "understand",
            "help",
            "support",
            "thank",
            "appreciate",
        ]
        negative_indicators = [
            "disagree",
            "refuse",
            "angry",
            "disappointed",
            "conflict",
            "argue",
        ]

        positive_score = sum(
            1
            for word in positive_indicators
            if word.lower() in dialogue_content.lower()
        )
        negative_score = sum(
            1
            for word in negative_indicators
            if word.lower() in dialogue_content.lower()
        )

        net_sentiment = (positive_score - negative_score) / max(
            1, positive_score + negative_score
        )

        # Calculate relationship impact
        from .types import CommunicationType

        base_impact = 0.1
        if dialogue.communication_type == CommunicationType.COLLABORATION:
            base_impact = 0.2
        elif dialogue.communication_type == CommunicationType.NEGOTIATION:
            base_impact = 0.15
        elif dialogue.communication_type == CommunicationType.EMOTIONAL:
            base_impact = 0.25

        relationship_change = net_sentiment * base_impact

        for i, agent in enumerate(dialogue.participants):
            for j, other_agent in enumerate(dialogue.participants):
                if i != j:
                    outcome["relationship_impact"][f"{agent}_{other_agent}"] = (
                        relationship_change
                    )

        return outcome

    def _calculate_quality(
        self, dialogue_outcome: Dict[str, Any], llm_result: Dict[str, Any]
    ) -> float:
        """Calculate quality score for dialogue."""
        quality_factors: List[float] = []

        # Response length factor
        response_length = len(llm_result.get("response", ""))
        if 50 <= response_length <= 500:
            quality_factors.append(0.8)
        elif 20 <= response_length <= 1000:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.4)

        # Processing time factor
        processing_time = llm_result.get("processing_time", 1.0)
        if processing_time < 1.0:
            quality_factors.append(0.9)
        elif processing_time < 2.0:
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.5)

        # Relationship impact factor
        relationship_impact = dialogue_outcome.get("relationship_impact", {})
        avg_impact = sum(abs(impact) for impact in relationship_impact.values()) / max(
            1, len(relationship_impact)
        )
        if avg_impact > 0.1:
            quality_factors.append(0.8)
        elif avg_impact > 0.05:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.4)

        # Cost efficiency factor
        cost = llm_result.get("cost", 0.01)
        if cost < 0.005:
            quality_factors.append(0.9)
        elif cost < 0.02:
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.5)

        return sum(quality_factors) / len(quality_factors)

    async def simulate_dialogue(
        self, dialogue: AgentDialogue, fast_mode: bool = False
    ) -> Dict[str, Any]:
        """Simulate dialogue when AI coordination is not available."""
        from .types import CommunicationType

        start_time = time.time()

        # Basic dialogue simulation
        simulated_quality = 0.6 + (hash(dialogue.dialogue_id) % 40) / 100.0

        if fast_mode:
            simulated_quality *= 0.8
            exchanges = min(dialogue.max_exchanges, 1)
        else:
            exchanges = min(dialogue.max_exchanges, 2)

        base_impact = 0.05
        if dialogue.communication_type == CommunicationType.COLLABORATION:
            base_impact = 0.1
        elif dialogue.communication_type == CommunicationType.NEGOTIATION:
            base_impact = 0.08

        relationship_change = simulated_quality * base_impact
        processing_time = time.time() - start_time

        return {
            "success": True,
            "dialogue_id": dialogue.dialogue_id,
            "participants": dialogue.participants,
            "communication_type": dialogue.communication_type.value,
            "exchanges": exchanges,
            "quality_score": simulated_quality,
            "processing_time": processing_time,
            "cost": 0.0,
            "relationship_impact": {
                f"{dialogue.participants[0]}_{dialogue.participants[1]}": relationship_change,
                f"{dialogue.participants[1]}_{dialogue.participants[0]}": relationship_change,
            },
            "resolution": "simulated" + ("_fast" if fast_mode else ""),
        }

    def record_communication(
        self, dialogue: AgentDialogue, result: Dict[str, Any]
    ) -> None:
        """Record a communication event."""
        self.communication_history.append(
            {
                "dialogue_id": dialogue.dialogue_id,
                "timestamp": datetime.now(),
                "participants": dialogue.participants,
                "type": dialogue.communication_type.value,
                "result": result,
            }
        )

    def cleanup_dialogues(self) -> Dict[str, Any]:
        """Clean up concluded dialogues."""
        cleaned = 0
        active = 0

        for dialogue in list(self.active_dialogues.values()):
            from .types import DialogueState

            if dialogue.state in [DialogueState.CONCLUDED, DialogueState.FAILED]:
                del self.active_dialogues[dialogue.dialogue_id]
                cleaned += 1
            else:
                active += 1

        return {"active": active, "cleaned": cleaned}


__all__ = ["DialogueManager"]
