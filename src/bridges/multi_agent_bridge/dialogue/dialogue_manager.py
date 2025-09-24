"""
Dialogue Manager
===============

Manages agent-to-agent dialogues and conversation coordination.
"""

import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.types import (
    AgentDialogue,
    CommunicationType,
    DialogueState,
    RequestPriority,
)
from ..llm_processing.llm_batch_processor import LLMBatchProcessor

__all__ = ["DialogueManager"]


class DialogueManager:
    """
    Manages agent-to-agent dialogues and conversations.

    Responsibilities:
    - Initiate and manage dialogue sessions between agents
    - Track dialogue state and progress
    - Generate contextual dialogue prompts
    - Process and interpret LLM dialogue responses
    - Update agent relationships based on dialogue outcomes
    - Provide dialogue quality assessment and metrics
    """

    def __init__(
        self,
        llm_processor: LLMBatchProcessor,
        logger: Optional[logging.Logger] = None,
    ):
        self.llm_processor = llm_processor
        self.logger = logger or logging.getLogger(__name__)

        # Active dialogues
        self._active_dialogues: Dict[str, AgentDialogue] = {}
        self._dialogue_history: List[AgentDialogue] = []

        # Agent data cache
        self._agent_cache: Dict[str, Dict[str, Any]] = {}

        # Dialogue statistics
        self._stats = {
            "total_dialogues_initiated": 0,
            "successful_dialogues": 0,
            "failed_dialogues": 0,
            "avg_dialogue_quality": 0.0,
            "dialogues_by_type": {
                comm_type.value: 0 for comm_type in CommunicationType
            },
        }

    async def initiate_dialogue(
        self,
        initiator_id: str,
        target_id: str,
        communication_type: CommunicationType = CommunicationType.DIALOGUE,
        context: Optional[Dict[str, Any]] = None,
        max_exchanges: int = 3,
    ) -> str:
        """
        Initiate a new dialogue between two agents.

        Args:
            initiator_id: ID of the agent starting the dialogue
            target_id: ID of the target agent
            communication_type: Type of communication
            context: Additional context for the dialogue
            max_exchanges: Maximum number of exchanges

        Returns:
            str: Dialogue ID
        """
        try:
            dialogue_id = str(uuid.uuid4())

            dialogue = AgentDialogue(
                dialogue_id=dialogue_id,
                communication_type=communication_type,
                participants=[initiator_id, target_id],
                initiator=initiator_id,
                state=DialogueState.INITIATING,
                max_exchanges=max_exchanges,
                context=context or {},
            )

            self._active_dialogues[dialogue_id] = dialogue
            self._stats["total_dialogues_initiated"] += 1
            self._stats["dialogues_by_type"][communication_type.value] += 1

            self.logger.info(
                f"Initiated {communication_type.value} dialogue {dialogue_id} between {initiator_id} and {target_id}"
            )

            return dialogue_id

        except Exception as e:
            self.logger.error(f"Error initiating dialogue: {e}")
            raise

    async def execute_dialogue(
        self, dialogue_id: str, fast_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a dialogue session.

        Args:
            dialogue_id: ID of the dialogue to execute
            fast_mode: Whether to use fast simulation mode

        Returns:
            Dict containing dialogue results
        """
        try:
            dialogue = self._active_dialogues.get(dialogue_id)
            if not dialogue:
                return {
                    "error": "dialogue_not_found",
                    "dialogue_id": dialogue_id,
                }

            if fast_mode:
                return await self._simulate_dialogue_fast(dialogue)
            else:
                return await self._execute_dialogue_with_llm(dialogue)

        except Exception as e:
            self.logger.error(f"Error executing dialogue {dialogue_id}: {e}")
            return {"error": str(e), "dialogue_id": dialogue_id}

    async def _execute_dialogue_with_llm(
        self, dialogue: AgentDialogue
    ) -> Dict[str, Any]:
        """Execute dialogue using LLM processing."""
        try:
            dialogue.state = DialogueState.ACTIVE

            # Create dialogue prompt
            prompt = self._create_dialogue_prompt(dialogue)
            priority = self._determine_dialogue_priority(dialogue)

            # Queue LLM request
            request_id = await self.llm_processor.queue_llm_request(
                request_type="dialogue",
                prompt=prompt,
                priority=priority,
                context={"dialogue_id": dialogue.dialogue_id},
                timeout_seconds=20.0,
            )

            # Wait for result
            llm_result = await self.llm_processor.wait_for_result(
                request_id, timeout_seconds=20.0
            )

            if llm_result.get("success"):
                # Process LLM response
                dialogue_result = self._process_llm_dialogue_result(
                    dialogue, llm_result
                )

                # Update dialogue state
                dialogue.state = DialogueState.CONCLUDED
                dialogue.resolution = dialogue_result

                # Move to history
                self._dialogue_history.append(dialogue)
                del self._active_dialogues[dialogue.dialogue_id]

                self._stats["successful_dialogues"] += 1

                # Calculate and record quality
                quality = self._calculate_dialogue_quality(
                    dialogue_result, llm_result
                )
                self._update_quality_stats(quality)

                return dialogue_result
            else:
                # LLM processing failed
                dialogue.state = DialogueState.FAILED
                self._stats["failed_dialogues"] += 1

                return {
                    "success": False,
                    "error": llm_result.get("error", "llm_processing_failed"),
                    "dialogue_id": dialogue.dialogue_id,
                }

        except Exception as e:
            dialogue.state = DialogueState.FAILED
            self.logger.error(f"Error in LLM dialogue execution: {e}")
            return {
                "success": False,
                "error": str(e),
                "dialogue_id": dialogue.dialogue_id,
            }

    async def _simulate_dialogue_fast(
        self, dialogue: AgentDialogue
    ) -> Dict[str, Any]:
        """Fast simulation mode for dialogue."""
        try:
            dialogue.state = DialogueState.ACTIVE

            # Generate quick dialogue outcome based on agent types and context
            outcome = self._generate_fast_dialogue_outcome(dialogue)

            dialogue.state = DialogueState.CONCLUDED
            dialogue.resolution = outcome

            # Move to history
            self._dialogue_history.append(dialogue)
            del self._active_dialogues[dialogue.dialogue_id]

            self._stats["successful_dialogues"] += 1

            return outcome

        except Exception as e:
            dialogue.state = DialogueState.FAILED
            self.logger.error(f"Error in fast dialogue simulation: {e}")
            return {
                "success": False,
                "error": str(e),
                "dialogue_id": dialogue.dialogue_id,
            }

    def _create_dialogue_prompt(self, dialogue: AgentDialogue) -> str:
        """Create contextual prompt for dialogue generation."""
        try:
            participants = dialogue.participants
            initiator = dialogue.initiator
            target = [p for p in participants if p != initiator][0]

            # Get agent information
            initiator_info = self._get_agent_info(initiator)
            target_info = self._get_agent_info(target)

            prompt_parts = [
                f"# Agent Dialogue: {dialogue.communication_type.value.title()}",
                "",
                f"**Dialogue Type:** {dialogue.communication_type.value}",
                f"**Initiator:** {initiator} ({initiator_info.get( 'role', 'Unknown')})",
                f"**Target:** {target} ({target_info.get('role', 'Unknown')})",
                "",
                "## Agent Profiles",
                f"**{initiator}:**",
                f"- Role: {initiator_info.get('role', 'Unknown')}",
                f"- Personality: {initiator_info.get('personality', {})}",
                f"- Current Status: {initiator_info.get('status', 'active')}",
                "",
                f"**{target}:**",
                f"- Role: {target_info.get('role', 'Unknown')}",
                f"- Personality: {target_info.get('personality', {})}",
                f"- Current Status: {target_info.get('status', 'active')}",
                "",
            ]

            # Add context if available
            if dialogue.context:
                prompt_parts.extend(
                    ["## Dialogue Context", str(dialogue.context), ""]
                )

            # Add dialogue type specific instructions
            if dialogue.communication_type == CommunicationType.NEGOTIATION:
                prompt_parts.extend(
                    [
                        "## Instructions",
                        "Generate a negotiation dialogue where both agents attempt to reach a mutually beneficial agreement.",
                        "Focus on compromise, trade-offs, and finding common ground.",
                        "Include emotional undertones and relationship dynamics.",
                    ]
                )
            elif (
                dialogue.communication_type == CommunicationType.COLLABORATION
            ):
                prompt_parts.extend(
                    [
                        "## Instructions",
                        "Generate a collaborative dialogue where agents plan joint actions.",
                        "Focus on strategy, resource sharing, and coordinated efforts.",
                        "Include tactical considerations and trust-building.",
                    ]
                )
            else:
                prompt_parts.extend(
                    [
                        "## Instructions",
                        "Generate a natural dialogue between these agents based on their personalities and current situation.",
                        "Keep responses in character and consider their relationship dynamics.",
                    ]
                )

            prompt_parts.extend(
                [
                    "",
                    "## Response Format",
                    "Provide the dialogue as a conversation with clear speaker indicators.",
                    "Include outcome summary and relationship impact assessment.",
                    "",
                    f"**{initiator}:** [opening statement]",
                    f"**{target}:** [response]",
                    f"**{initiator}:** [follow-up]",
                    "...",
                    "",
                    "**Outcome:** [summary of dialogue resolution]",
                    "**Relationship Impact:** [how this affects their relationship]",
                ]
            )

            return "\n".join(prompt_parts)

        except Exception as e:
            self.logger.error(f"Error creating dialogue prompt: {e}")
            return f"Generate a {dialogue.communication_type.value} between {dialogue.participants}"

    def _determine_dialogue_priority(
        self, dialogue: AgentDialogue
    ) -> RequestPriority:
        """Determine processing priority for dialogue."""
        try:
            # Critical communication types get high priority
            if dialogue.communication_type in [
                CommunicationType.NEGOTIATION,
                CommunicationType.STRATEGIC,
            ]:
                return RequestPriority.HIGH

            # Emergency or conflict situations
            context = dialogue.context
            if context.get("urgent") or context.get("conflict"):
                return RequestPriority.HIGH

            return RequestPriority.NORMAL

        except Exception:
            return RequestPriority.NORMAL

    def _process_llm_dialogue_result(
        self, dialogue: AgentDialogue, llm_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and structure LLM dialogue response."""
        try:
            content = llm_result.get("content", "")

            # Extract dialogue components
            dialogue_lines = []
            outcome = "No outcome determined"
            relationship_impact = "No relationship impact assessed"

            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue

                if line.startswith("**Outcome:**"):
                    outcome = line.replace("**Outcome:**", "").strip()
                elif line.startswith("**Relationship Impact:**"):
                    relationship_impact = line.replace(
                        "**Relationship Impact:**", ""
                    ).strip()
                elif any(
                    participant in line
                    for participant in dialogue.participants
                ):
                    dialogue_lines.append(line)

            return {
                "success": True,
                "dialogue_id": dialogue.dialogue_id,
                "communication_type": dialogue.communication_type.value,
                "participants": dialogue.participants,
                "dialogue_content": "\n".join(dialogue_lines),
                "outcome": outcome,
                "relationship_impact": relationship_impact,
                "exchanges": len(
                    [line for line in dialogue_lines if ":" in line]
                ),
                "llm_cost": llm_result.get("cost", 0.0),
                "processing_time": llm_result.get("processing_time", 0.0),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error processing LLM dialogue result: {e}")
            return {
                "success": False,
                "error": str(e),
                "dialogue_id": dialogue.dialogue_id,
            }

    def _generate_fast_dialogue_outcome(
        self, dialogue: AgentDialogue
    ) -> Dict[str, Any]:
        """Generate quick dialogue outcome without LLM."""
        try:
            participants = dialogue.participants

            # Simple outcome generation based on dialogue type
            outcomes = {
                CommunicationType.DIALOGUE: "Had a constructive conversation",
                CommunicationType.NEGOTIATION: "Reached a tentative agreement",
                CommunicationType.COLLABORATION: "Agreed to work together",
                CommunicationType.INFORMATION_SHARING: "Exchanged valuable information",
                CommunicationType.EMOTIONAL: "Shared emotional support",
                CommunicationType.STRATEGIC: "Discussed strategic options",
            }

            outcome = outcomes.get(
                dialogue.communication_type, "Completed their interaction"
            )

            return {
                "success": True,
                "dialogue_id": dialogue.dialogue_id,
                "communication_type": dialogue.communication_type.value,
                "participants": participants,
                "outcome": outcome,
                "relationship_impact": "Neutral interaction",
                "exchanges": 2,  # Simulated
                "fast_mode": True,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error generating fast dialogue outcome: {e}")
            return {
                "success": False,
                "error": str(e),
                "dialogue_id": dialogue.dialogue_id,
            }

    def _calculate_dialogue_quality(
        self, dialogue_outcome: Dict[str, Any], llm_result: Dict[str, Any]
    ) -> float:
        """Calculate dialogue quality score."""
        try:
            quality_score = 0.5  # Base quality

            # Content quality indicators
            content = llm_result.get("content", "")
            if len(content) > 200:  # Sufficient detail
                quality_score += 0.2

            if (
                dialogue_outcome.get("outcome")
                and len(dialogue_outcome.get("outcome", "")) > 20
            ):
                quality_score += 0.1

            if dialogue_outcome.get("relationship_impact"):
                quality_score += 0.1

            # Exchange quality
            exchanges = dialogue_outcome.get("exchanges", 0)
            if exchanges >= 2:
                quality_score += 0.1

            return min(1.0, quality_score)

        except Exception:
            return 0.5

    def _update_quality_stats(self, quality: float) -> None:
        """Update running quality statistics."""
        try:
            current_avg = self._stats["avg_dialogue_quality"]
            successful_count = self._stats["successful_dialogues"]

            # Running average
            self._stats["avg_dialogue_quality"] = (
                (current_avg * (successful_count - 1)) + quality
            ) / successful_count

        except Exception as e:
            self.logger.debug(f"Error updating quality stats: {e}")

    def _get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Get cached agent information."""
        return self._agent_cache.get(
            agent_id,
            {"role": "Unknown", "personality": {}, "status": "active"},
        )

    def update_agent_cache(
        self, agent_id: str, agent_info: Dict[str, Any]
    ) -> None:
        """Update agent information cache."""
        self._agent_cache[agent_id] = agent_info

    def get_active_dialogues(self) -> List[Dict[str, Any]]:
        """Get list of currently active dialogues."""
        return [
            asdict(dialogue) for dialogue in self._active_dialogues.values()
        ]

    def get_dialogue_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent dialogue history."""
        recent_history = (
            self._dialogue_history[-limit:] if self._dialogue_history else []
        )
        return [asdict(dialogue) for dialogue in recent_history]

    def get_dialogue_stats(self) -> Dict[str, Any]:
        """Get comprehensive dialogue statistics."""
        try:
            stats = self._stats.copy()
            stats.update(
                {
                    "active_dialogues": len(self._active_dialogues),
                    "total_dialogue_history": len(self._dialogue_history),
                    "success_rate": (
                        self._stats["successful_dialogues"]
                        / max(1, self._stats["total_dialogues_initiated"])
                    )
                    * 100,
                    "most_common_type": (
                        max(
                            self._stats["dialogues_by_type"].items(),
                            key=lambda x: x[1],
                        )[0]
                        if self._stats["dialogues_by_type"]
                        else "none"
                    ),
                }
            )

            return stats

        except Exception as e:
            self.logger.error(f"Error getting dialogue stats: {e}")
            return {}

    def cleanup_old_dialogues(self, max_history: int = 100) -> None:
        """Clean up old dialogue history."""
        try:
            if len(self._dialogue_history) > max_history:
                self._dialogue_history = self._dialogue_history[-max_history:]
                self.logger.debug(
                    f"Cleaned up dialogue history to {max_history} entries"
                )
        except Exception as e:
            self.logger.error(f"Error cleaning up dialogue history: {e}")

    async def shutdown(self) -> None:
        """Shutdown dialogue manager gracefully."""
        try:
            # Complete any pending dialogues in fast mode
            for dialogue_id in list(self._active_dialogues.keys()):
                result = await self._simulate_dialogue_fast(
                    self._active_dialogues[dialogue_id]
                )
                self.logger.info(
                    f"Completed dialogue {dialogue_id} during shutdown: {result.get( 'outcome', 'unknown')}"
                )

            self.logger.info("Dialogue manager shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during dialogue manager shutdown: {e}")
