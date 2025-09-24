#!/usr/bin/env python3
"""
Dialogue Manager
================

Manages agent-to-agent dialogue sessions and communication coordination.
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from .types import AgentDialogue, CommunicationType, DialogueState


class DialogueManager:
    """
    Manages agent-to-agent dialogue sessions.

    Responsibilities:
    - Dialogue session lifecycle management
    - Participant coordination and turn-taking
    - Communication type classification
    - Session state tracking and cleanup
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize dialogue manager."""
        self.logger = logger or logging.getLogger(__name__)
        self.active_dialogues: Dict[str, AgentDialogue] = {}
        self.agent_dialogues: Dict[str, Set[str]] = defaultdict(set)
        self.dialogue_history: List[Dict[str, Any]] = []
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = datetime.now()

    async def initiate_dialogue(
        self,
        initiator_id: str,
        target_id: str,
        communication_type: CommunicationType,
        context: Optional[Dict[str, Any]] = None,
        max_exchanges: int = 3,
    ) -> str:
        """
        Initiate a new dialogue between agents.

        Args:
            initiator_id: ID of the agent starting the dialogue
            target_id: ID of the target agent
            communication_type: Type of communication
            context: Optional context information
            max_exchanges: Maximum number of exchanges allowed

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

            # Check if agents are available for dialogue
            if not await self._are_agents_available([initiator_id, target_id]):
                self.logger.warning(
                    f"One or more agents unavailable for dialogue: {initiator_id}, {target_id}"
                )
                return None

            # Register dialogue
            self.active_dialogues[dialogue_id] = dialogue
            self.agent_dialogues[initiator_id].add(dialogue_id)
            self.agent_dialogues[target_id].add(dialogue_id)

            self.logger.info(
                f"Dialogue {dialogue_id} initiated: {initiator_id} -> {target_id} ({communication_type.value})"
            )

            return dialogue_id

        except Exception as e:
            self.logger.error(f"Failed to initiate dialogue: {e}")
            return None

    async def add_message(
        self,
        dialogue_id: str,
        sender_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a message to an active dialogue.

        Args:
            dialogue_id: ID of the dialogue
            sender_id: ID of the sender agent
            content: Message content
            metadata: Optional message metadata

        Returns:
            bool: True if message was added successfully
        """
        try:
            if dialogue_id not in self.active_dialogues:
                self.logger.error(f"Dialogue {dialogue_id} not found")
                return False

            dialogue = self.active_dialogues[dialogue_id]

            # Validate sender is a participant
            if sender_id not in dialogue.participants:
                self.logger.error(
                    f"Agent {sender_id} not a participant in dialogue {dialogue_id}"
                )
                return False

            # Check if dialogue is in valid state for messages
            if dialogue.state not in [
                DialogueState.ACTIVE,
                DialogueState.INITIATING,
            ]:
                self.logger.warning(
                    f"Cannot add message to dialogue {dialogue_id} in state {dialogue.state}"
                )
                return False

            # Add message
            message = {
                "sender_id": sender_id,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }

            dialogue.messages.append(message)
            dialogue.current_exchange += 1
            dialogue.state = DialogueState.ACTIVE

            # Check if dialogue should be concluded
            await self._check_dialogue_completion(dialogue)

            self.logger.debug(
                f"Message added to dialogue {dialogue_id}: {sender_id}"
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to add message to dialogue {dialogue_id}: {e}"
            )
            return False

    async def conclude_dialogue(
        self,
        dialogue_id: str,
        resolution: Optional[Dict[str, Any]] = None,
        forced: bool = False,
    ) -> bool:
        """
        Conclude an active dialogue.

        Args:
            dialogue_id: ID of the dialogue
            resolution: Optional resolution information
            forced: Whether this is a forced conclusion

        Returns:
            bool: True if dialogue was concluded successfully
        """
        try:
            if dialogue_id not in self.active_dialogues:
                self.logger.error(f"Dialogue {dialogue_id} not found")
                return False

            dialogue = self.active_dialogues[dialogue_id]

            # Update dialogue state
            dialogue.state = (
                DialogueState.INTERRUPTED
                if forced
                else DialogueState.CONCLUDED
            )
            dialogue.resolution = resolution

            # Archive dialogue
            await self._archive_dialogue(dialogue)

            # Clean up references
            for participant in dialogue.participants:
                self.agent_dialogues[participant].discard(dialogue_id)

            del self.active_dialogues[dialogue_id]

            self.logger.info(
                f"Dialogue {dialogue_id} concluded ({'forced' if forced else 'natural'})"
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to conclude dialogue {dialogue_id}: {e}"
            )
            return False

    async def get_agent_dialogues(self, agent_id: str) -> List[AgentDialogue]:
        """Get active dialogues for an agent."""
        try:
            dialogue_ids = self.agent_dialogues.get(agent_id, set())
            return [
                self.active_dialogues[did]
                for did in dialogue_ids
                if did in self.active_dialogues
            ]
        except Exception as e:
            self.logger.error(
                f"Failed to get dialogues for agent {agent_id}: {e}"
            )
            return []

    async def get_dialogue(self, dialogue_id: str) -> Optional[AgentDialogue]:
        """Get dialogue by ID."""
        return self.active_dialogues.get(dialogue_id)

    async def get_dialogue_status(self) -> Dict[str, Any]:
        """Get current dialogue system status."""
        return {
            "active_dialogues": len(self.active_dialogues),
            "dialogue_types": self._get_dialogue_type_distribution(),
            "avg_exchanges": self._get_average_exchanges(),
            "agent_participation": len(self.agent_dialogues),
            "archived_dialogues": len(self.dialogue_history),
        }

    async def _are_agents_available(self, agent_ids: List[str]) -> bool:
        """Check if agents are available for new dialogue."""
        # Simplified availability check
        for agent_id in agent_ids:
            active_dialogues = len(self.agent_dialogues.get(agent_id, set()))
            if active_dialogues >= 3:  # Max 3 concurrent dialogues per agent
                return False
        return True

    async def _check_dialogue_completion(
        self, dialogue: AgentDialogue
    ) -> None:
        """Check if dialogue should be automatically concluded."""
        try:
            # Auto-conclude if max exchanges reached
            if dialogue.current_exchange >= dialogue.max_exchanges:
                await self.conclude_dialogue(
                    dialogue.dialogue_id,
                    {
                        "reason": "max_exchanges_reached",
                        "total_exchanges": dialogue.current_exchange,
                    },
                )
                return

            # Auto-conclude if inactive for too long
            if dialogue.messages:
                last_message_time = datetime.fromisoformat(
                    dialogue.messages[-1]["timestamp"]
                )
                if datetime.now() - last_message_time > timedelta(minutes=10):
                    await self.conclude_dialogue(
                        dialogue.dialogue_id,
                        {
                            "reason": "timeout",
                            "last_activity": last_message_time.isoformat(),
                        },
                    )

        except Exception as e:
            self.logger.error(f"Error checking dialogue completion: {e}")

    async def _archive_dialogue(self, dialogue: AgentDialogue) -> None:
        """Archive completed dialogue for analysis."""
        try:
            archive_entry = {
                "dialogue_id": dialogue.dialogue_id,
                "communication_type": dialogue.communication_type.value,
                "participants": dialogue.participants,
                "initiator": dialogue.initiator,
                "state": dialogue.state.value,
                "created_at": dialogue.created_at.isoformat(),
                "concluded_at": datetime.now().isoformat(),
                "total_exchanges": dialogue.current_exchange,
                "message_count": len(dialogue.messages),
                "resolution": dialogue.resolution,
            }

            self.dialogue_history.append(archive_entry)

            # Keep only recent history
            if len(self.dialogue_history) > 1000:
                self.dialogue_history = self.dialogue_history[-500:]

        except Exception as e:
            self.logger.error(f"Failed to archive dialogue: {e}")

    def _get_dialogue_type_distribution(self) -> Dict[str, int]:
        """Get distribution of dialogue types."""
        distribution = defaultdict(int)
        for dialogue in self.active_dialogues.values():
            distribution[dialogue.communication_type.value] += 1
        return dict(distribution)

    def _get_average_exchanges(self) -> float:
        """Get average number of exchanges across active dialogues."""
        if not self.active_dialogues:
            return 0.0

        total_exchanges = sum(
            d.current_exchange for d in self.active_dialogues.values()
        )
        return total_exchanges / len(self.active_dialogues)

    async def cleanup_expired_dialogues(self) -> int:
        """Clean up expired or stale dialogues."""
        try:
            now = datetime.now()
            if now - self._last_cleanup < timedelta(
                seconds=self._cleanup_interval
            ):
                return 0

            expired_dialogues = []
            cutoff_time = now - timedelta(hours=1)  # 1 hour timeout

            for dialogue_id, dialogue in self.active_dialogues.items():
                if dialogue.created_at < cutoff_time:
                    expired_dialogues.append(dialogue_id)

            # Clean up expired dialogues
            cleanup_count = 0
            for dialogue_id in expired_dialogues:
                if await self.conclude_dialogue(
                    dialogue_id, {"reason": "expired"}, forced=True
                ):
                    cleanup_count += 1

            self._last_cleanup = now

            if cleanup_count > 0:
                self.logger.info(
                    f"Cleaned up {cleanup_count} expired dialogues"
                )

            return cleanup_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup expired dialogues: {e}")
            return 0
