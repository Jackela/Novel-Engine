"""
State Manager
=============

Character state updates, memory management, and relationship tracking system.
Handles all state changes resulting from interaction processing.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core.types import (
    InteractionContext,
    InteractionEngineConfig,
    InteractionPriority,
    InteractionType,
)

# Import enhanced core systems
try:
    from src.core.character_manager import CharacterManager
    from src.core.data_models import (
        CharacterState,
        EmotionalState,
        ErrorInfo,
        InteractionResult,
        MemoryItem,
        MemoryType,
        StandardResponse,
    )
    from src.core.memory_system import MemoryManager
    from src.core.types import AgentID
except ImportError:
    # Fallback for testing
    class StandardResponse:
        def __init__(self, success=True, data=None, error=None, metadata=None):
            self.success = success
            self.data = data or {}
            self.error = error
            self.metadata = metadata or {}

        def get(self, key, default=None):
            return getattr(self, key, default)

        def __getitem__(self, key):
            return getattr(self, key)

    class ErrorInfo:
        def __init__(self, code="", message="", recoverable=True):
            self.code = code
            self.message = message
            self.recoverable = recoverable

    CharacterState = dict
    MemoryItem = dict
    InteractionResult = dict
    AgentID = str
    MemoryManager = None
    CharacterManager = None

    class MemoryType:
        EPISODIC = "episodic"
        SEMANTIC = "semantic"
        PROCEDURAL = "procedural"

    class EmotionalState:
        CALM = "calm"
        EXCITED = "excited"
        ANGRY = "angry"
        FEARFUL = "fearful"


__all__ = ["StateManager", "StateUpdate", "MemoryUpdate"]


@dataclass
class StateUpdate:
    """
    Character state update information.
    """

    agent_id: str
    state_type: str
    old_value: Any
    new_value: Any
    change_amount: float = 0.0
    change_reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryUpdate:
    """
    Memory system update information.
    """

    agent_id: str
    memory_item: MemoryItem
    memory_type: str
    significance: float = 0.5
    associated_agents: List[str] = field(default_factory=list)
    emotional_weight: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """
    Character State Updates and Memory Management System

    Responsibilities:
    - Update character states based on interaction outcomes
    - Generate and store memory items from interactions
    - Track relationship changes between characters
    - Manage emotional state transitions
    - Coordinate state persistence and synchronization
    """

    def __init__(
        self,
        config: InteractionEngineConfig,
        memory_manager: Optional[Any] = None,
        character_manager: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize state manager.

        Args:
            config: Interaction engine configuration
            memory_manager: Optional memory manager instance
            character_manager: Optional character manager instance
            logger: Optional logger instance
        """
        self.config = config
        self.memory_manager = memory_manager
        self.character_manager = character_manager
        self.logger = logger or logging.getLogger(__name__)

        # State tracking
        self.pending_state_updates: Dict[str, List[StateUpdate]] = {}
        self.pending_memory_updates: Dict[str, List[MemoryUpdate]] = {}

        # Relationship tracking
        self.relationship_changes: Dict[Tuple[str, str], float] = {}

        # Processing statistics
        self.state_update_stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "memory_items_generated": 0,
        }

        # State update thresholds
        self.state_thresholds = {
            "emotion_change_threshold": 0.1,
            "relationship_change_threshold": 0.05,
            "memory_significance_threshold": self.config.memory_significance_threshold,
        }

        self.logger.info("State manager initialized")

    async def update_interaction_states(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> StandardResponse:
        """
        Update all states based on interaction outcome.

        Args:
            context: Interaction context
            interaction_data: Data from processed interaction

        Returns:
            StandardResponse with state update results
        """
        try:
            self.logger.info(
                f"Updating states for interaction: {context.interaction_id}"
            )

            update_results = {
                "character_states": [],
                "memory_updates": [],
                "relationship_changes": [],
                "emotional_changes": [],
            }

            # Update character states
            character_updates = await self._update_character_states(
                context, interaction_data
            )
            update_results["character_states"] = character_updates.get(
                "data", {}
            ).get("state_updates", [])

            # Generate and store memories
            if (
                self.config.memory_integration_enabled
                and self.config.auto_generate_memories
            ):
                memory_updates = await self._generate_interaction_memories(
                    context, interaction_data
                )
                update_results["memory_updates"] = memory_updates.get(
                    "data", {}
                ).get("memory_updates", [])

            # Update relationships
            relationship_updates = await self._update_relationships(
                context, interaction_data
            )
            update_results["relationship_changes"] = relationship_updates.get(
                "data", {}
            ).get("relationship_changes", [])

            # Process emotional changes
            emotional_updates = await self._process_emotional_changes(
                context, interaction_data
            )
            update_results["emotional_changes"] = emotional_updates.get(
                "data", {}
            ).get("emotional_changes", [])

            # Apply all updates
            application_result = await self._apply_pending_updates(
                context.interaction_id
            )

            total_updates = (
                len(update_results["character_states"])
                + len(update_results["memory_updates"])
                + len(update_results["relationship_changes"])
                + len(update_results["emotional_changes"])
            )

            self.state_update_stats["total_updates"] += total_updates
            if application_result.success:
                self.state_update_stats["successful_updates"] += total_updates
            else:
                self.state_update_stats["failed_updates"] += total_updates

            return StandardResponse(
                success=True,
                data=update_results,
                metadata={
                    "blessing": "states_updated",
                    "total_updates": total_updates,
                    "application_success": application_result.success,
                },
            )

        except Exception as e:
            self.logger.error(f"State update failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="STATE_UPDATE_FAILED",
                    message=f"State update failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def generate_memory_from_interaction(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> StandardResponse:
        """
        Generate memory items from interaction data.

        Args:
            context: Interaction context
            interaction_data: Processed interaction data

        Returns:
            StandardResponse with generated memory items
        """
        try:
            memories = []

            # Generate episodic memories for each participant
            for participant in context.participants:
                episodic_memory = await self._create_episodic_memory(
                    participant, context, interaction_data
                )
                if episodic_memory:
                    memories.append(episodic_memory)

            # Generate semantic memories for significant interactions
            if (
                self._calculate_interaction_significance(
                    context, interaction_data
                )
                > self.state_thresholds["memory_significance_threshold"]
            ):
                semantic_memory = await self._create_semantic_memory(
                    context, interaction_data
                )
                if semantic_memory:
                    memories.append(semantic_memory)

            # Generate procedural memories for skill-based interactions
            if context.interaction_type in [
                InteractionType.INSTRUCTION,
                InteractionType.COOPERATION,
            ]:
                for participant in context.participants:
                    procedural_memory = await self._create_procedural_memory(
                        participant, context, interaction_data
                    )
                    if procedural_memory:
                        memories.append(procedural_memory)

            self.state_update_stats["memory_items_generated"] += len(memories)

            return StandardResponse(
                success=True,
                data={
                    "memories_generated": memories,
                    "memory_count": len(memories),
                    "participants": context.participants,
                },
                metadata={"blessing": "memories_generated"},
            )

        except Exception as e:
            self.logger.error(f"Memory generation failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MEMORY_GENERATION_FAILED",
                    message=f"Memory generation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def update_relationship_weights(
        self,
        participants: List[str],
        interaction_type: InteractionType,
        interaction_outcome: Dict[str, Any],
    ) -> StandardResponse:
        """
        Update relationship weights between participants.

        Args:
            participants: List of participant IDs
            interaction_type: Type of interaction
            interaction_outcome: Outcome data from interaction

        Returns:
            StandardResponse with relationship update results
        """
        try:
            relationship_updates = []

            # Calculate base relationship change
            base_change = self._calculate_base_relationship_change(
                interaction_type, interaction_outcome
            )

            # Update relationships between all participant pairs
            for i, participant_a in enumerate(participants):
                for participant_b in participants[i + 1 :]:
                    if participant_a != participant_b:
                        # Calculate specific relationship change
                        change_amount = (
                            self._calculate_specific_relationship_change(
                                participant_a,
                                participant_b,
                                base_change,
                                interaction_outcome,
                            )
                        )

                        if (
                            abs(change_amount)
                            >= self.state_thresholds[
                                "relationship_change_threshold"
                            ]
                        ):
                            update = {
                                "participant_a": participant_a,
                                "participant_b": participant_b,
                                "change_amount": change_amount,
                                "interaction_type": interaction_type.value,
                                "reason": self._determine_relationship_change_reason(
                                    interaction_type, interaction_outcome
                                ),
                            }
                            relationship_updates.append(update)

                            # Track for batch processing
                            self.relationship_changes[
                                (participant_a, participant_b)
                            ] = change_amount

            return StandardResponse(
                success=True,
                data={
                    "relationship_updates": relationship_updates,
                    "update_count": len(relationship_updates),
                },
                metadata={"blessing": "relationships_updated"},
            )

        except Exception as e:
            self.logger.error(f"Relationship update failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="RELATIONSHIP_UPDATE_FAILED",
                    message=f"Relationship update failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def get_pending_updates(
        self, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get pending state updates.

        Args:
            agent_id: Optional agent ID to filter updates

        Returns:
            Dict with pending updates
        """
        if agent_id:
            return {
                "state_updates": self.pending_state_updates.get(agent_id, []),
                "memory_updates": self.pending_memory_updates.get(
                    agent_id, []
                ),
            }

        return {
            "all_state_updates": self.pending_state_updates,
            "all_memory_updates": self.pending_memory_updates,
            "relationship_changes": dict(self.relationship_changes),
        }

    def get_state_statistics(self) -> Dict[str, Any]:
        """Get state management statistics."""
        return {
            **self.state_update_stats,
            "pending_state_updates": sum(
                len(updates) for updates in self.pending_state_updates.values()
            ),
            "pending_memory_updates": sum(
                len(updates)
                for updates in self.pending_memory_updates.values()
            ),
            "pending_relationship_changes": len(self.relationship_changes),
        }

    async def clear_pending_updates(self, agent_id: Optional[str] = None):
        """
        Clear pending updates.

        Args:
            agent_id: Optional agent ID to clear specific updates
        """
        if agent_id:
            self.pending_state_updates.pop(agent_id, None)
            self.pending_memory_updates.pop(agent_id, None)
        else:
            self.pending_state_updates.clear()
            self.pending_memory_updates.clear()
            self.relationship_changes.clear()

    # Private update methods

    async def _update_character_states(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> StandardResponse:
        """Update character states based on interaction."""
        try:
            state_updates = []

            for participant in context.participants:
                # Calculate state changes based on interaction type and outcome
                changes = self._calculate_character_state_changes(
                    participant, context, interaction_data
                )

                for state_type, change_data in changes.items():
                    if (
                        abs(change_data["change"]) > 0.01
                    ):  # Minimum change threshold
                        update = StateUpdate(
                            agent_id=participant,
                            state_type=state_type,
                            old_value=change_data.get("old_value", 0),
                            new_value=change_data.get("new_value", 0),
                            change_amount=change_data["change"],
                            change_reason=f"Interaction: {context.interaction_type.value}",
                            metadata={
                                "interaction_id": context.interaction_id
                            },
                        )

                        state_updates.append(update)

                        # Add to pending updates
                        if participant not in self.pending_state_updates:
                            self.pending_state_updates[participant] = []
                        self.pending_state_updates[participant].append(update)

            return StandardResponse(
                success=True,
                data={"state_updates": state_updates},
                metadata={"blessing": "character_states_calculated"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CHARACTER_STATE_UPDATE_FAILED",
                    message=f"Character state update failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _generate_interaction_memories(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> StandardResponse:
        """Generate memory items from interaction."""
        try:
            memory_updates = []

            for participant in context.participants:
                # Create episodic memory
                memory_item = {
                    "memory_id": f"{context.interaction_id}_{participant}_{datetime.now().timestamp()}",
                    "agent_id": participant,
                    "memory_type": MemoryType.EPISODIC,
                    "content": f"Participated in {context.interaction_type.value} interaction",
                    "associated_agents": [
                        p for p in context.participants if p != participant
                    ],
                    "location": context.location,
                    "timestamp": datetime.now(),
                    "emotional_weight": self._calculate_emotional_weight(
                        participant, interaction_data
                    ),
                    "significance": self._calculate_memory_significance(
                        participant, context, interaction_data
                    ),
                    "metadata": {
                        "interaction_id": context.interaction_id,
                        "interaction_type": context.interaction_type.value,
                        "participant_count": len(context.participants),
                    },
                }

                update = MemoryUpdate(
                    agent_id=participant,
                    memory_item=memory_item,
                    memory_type=MemoryType.EPISODIC,
                    significance=memory_item["significance"],
                    associated_agents=memory_item["associated_agents"],
                    emotional_weight=memory_item["emotional_weight"],
                )

                memory_updates.append(update)

                # Add to pending updates
                if participant not in self.pending_memory_updates:
                    self.pending_memory_updates[participant] = []
                self.pending_memory_updates[participant].append(update)

            return StandardResponse(
                success=True,
                data={"memory_updates": memory_updates},
                metadata={"blessing": "memories_generated"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MEMORY_GENERATION_FAILED",
                    message=f"Memory generation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _update_relationships(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> StandardResponse:
        """Update relationships between participants."""
        try:
            return await self.update_relationship_weights(
                context.participants,
                context.interaction_type,
                interaction_data,
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="RELATIONSHIP_UPDATE_FAILED",
                    message=f"Relationship update failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _process_emotional_changes(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> StandardResponse:
        """Process emotional state changes."""
        try:
            emotional_changes = []

            for participant in context.participants:
                emotional_impact = interaction_data.get(
                    "emotional_impacts", {}
                ).get(participant, {})

                if (
                    emotional_impact
                    and emotional_impact.get("mood_change", 0)
                    > self.state_thresholds["emotion_change_threshold"]
                ):
                    change = {
                        "agent_id": participant,
                        "emotion_type": "mood",
                        "change_amount": emotional_impact["mood_change"],
                        "new_state": emotional_impact.get(
                            "emotional_state", "content"
                        ),
                        "interaction_id": context.interaction_id,
                    }
                    emotional_changes.append(change)

            return StandardResponse(
                success=True,
                data={"emotional_changes": emotional_changes},
                metadata={"blessing": "emotional_changes_processed"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="EMOTIONAL_UPDATE_FAILED",
                    message=f"Emotional update failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _apply_pending_updates(
        self, interaction_id: str
    ) -> StandardResponse:
        """Apply all pending updates to the system."""
        try:
            applied_updates = {
                "state_updates": 0,
                "memory_updates": 0,
                "relationship_updates": 0,
            }

            # In a real implementation, this would persist updates to database/character systems
            # For now, simulate successful application

            applied_updates["state_updates"] = sum(
                len(updates) for updates in self.pending_state_updates.values()
            )
            applied_updates["memory_updates"] = sum(
                len(updates)
                for updates in self.pending_memory_updates.values()
            )
            applied_updates["relationship_updates"] = len(
                self.relationship_changes
            )

            # Clear applied updates
            self.pending_state_updates.clear()
            self.pending_memory_updates.clear()
            self.relationship_changes.clear()

            return StandardResponse(
                success=True,
                data=applied_updates,
                metadata={"blessing": "updates_applied"},
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="UPDATE_APPLICATION_FAILED",
                    message=f"Update application failed: {str(e)}",
                    recoverable=True,
                ),
            )

    # Helper calculation methods

    def _calculate_character_state_changes(
        self,
        agent_id: str,
        context: InteractionContext,
        interaction_data: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate character state changes."""
        changes = {}

        # Basic state changes based on interaction type
        if context.interaction_type == InteractionType.COMBAT:
            changes["stamina"] = {
                "change": -10,
                "old_value": 100,
                "new_value": 90,
            }
            changes["adrenaline"] = {
                "change": 5,
                "old_value": 0,
                "new_value": 5,
            }
        elif context.interaction_type == InteractionType.DIALOGUE:
            changes["social_energy"] = {
                "change": -2,
                "old_value": 100,
                "new_value": 98,
            }
            changes["mood"] = {"change": 1, "old_value": 50, "new_value": 51}
        elif context.interaction_type == InteractionType.COOPERATION:
            changes["teamwork_skill"] = {
                "change": 2,
                "old_value": 50,
                "new_value": 52,
            }
            changes["satisfaction"] = {
                "change": 5,
                "old_value": 50,
                "new_value": 55,
            }

        return changes

    def _calculate_interaction_significance(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> float:
        """Calculate significance score for interaction."""
        significance = 0.0

        # Base significance by type
        type_significance = {
            InteractionType.COMBAT: 0.8,
            InteractionType.DIALOGUE: 0.4,
            InteractionType.COOPERATION: 0.6,
            InteractionType.NEGOTIATION: 0.7,
            InteractionType.EMERGENCY: 0.9,
        }
        significance += type_significance.get(context.interaction_type, 0.5)

        # Priority modifier
        priority_modifier = {
            InteractionPriority.CRITICAL: 0.3,
            InteractionPriority.URGENT: 0.2,
            InteractionPriority.HIGH: 0.1,
            InteractionPriority.NORMAL: 0.0,
            InteractionPriority.LOW: -0.1,
        }
        significance += priority_modifier.get(context.priority, 0.0)

        # Participant count modifier
        significance += min(0.2, len(context.participants) * 0.05)

        return min(1.0, max(0.0, significance))

    def _calculate_base_relationship_change(
        self, interaction_type: InteractionType, outcome: Dict[str, Any]
    ) -> float:
        """Calculate base relationship change amount."""
        base_changes = {
            InteractionType.DIALOGUE: 0.05,
            InteractionType.COMBAT: -0.1,
            InteractionType.COOPERATION: 0.1,
            InteractionType.NEGOTIATION: 0.02,
        }

        base_change = base_changes.get(interaction_type, 0.01)

        # Modify based on outcome success
        if outcome.get("success", True):
            base_change = abs(base_change)
        else:
            base_change = -abs(base_change)

        return base_change

    def _calculate_specific_relationship_change(
        self,
        participant_a: str,
        participant_b: str,
        base_change: float,
        outcome: Dict[str, Any],
    ) -> float:
        """Calculate specific relationship change between two participants."""
        # For now, return base change
        # In full implementation, would consider participant-specific factors
        return base_change

    def _determine_relationship_change_reason(
        self, interaction_type: InteractionType, outcome: Dict[str, Any]
    ) -> str:
        """Determine reason for relationship change."""
        if outcome.get("success", True):
            return f"Successful {interaction_type.value} interaction"
        else:
            return f"Failed {interaction_type.value} interaction"

    def _calculate_emotional_weight(
        self, agent_id: str, interaction_data: Dict[str, Any]
    ) -> float:
        """Calculate emotional weight for memory."""
        return (
            interaction_data.get("emotional_impacts", {})
            .get(agent_id, {})
            .get("mood_change", 0.0)
        )

    def _calculate_memory_significance(
        self,
        agent_id: str,
        context: InteractionContext,
        interaction_data: Dict[str, Any],
    ) -> float:
        """Calculate memory significance for specific agent."""
        return self._calculate_interaction_significance(
            context, interaction_data
        )

    async def _create_episodic_memory(
        self,
        agent_id: str,
        context: InteractionContext,
        interaction_data: Dict[str, Any],
    ) -> Optional[MemoryItem]:
        """Create episodic memory item."""
        try:
            return {
                "memory_id": f"{context.interaction_id}_{agent_id}_episodic",
                "agent_id": agent_id,
                "memory_type": MemoryType.EPISODIC,
                "content": f"Participated in {context.interaction_type.value}",
                "timestamp": datetime.now(),
                "location": context.location,
                "participants": context.participants,
                "significance": self._calculate_memory_significance(
                    agent_id, context, interaction_data
                ),
            }
        except Exception as e:
            self.logger.error(f"Episodic memory creation failed: {e}")
            return None

    async def _create_semantic_memory(
        self, context: InteractionContext, interaction_data: Dict[str, Any]
    ) -> Optional[MemoryItem]:
        """Create semantic memory item."""
        try:
            return {
                "memory_id": f"{context.interaction_id}_semantic",
                "memory_type": MemoryType.SEMANTIC,
                "content": f"Knowledge about {context.interaction_type.value} interactions",
                "timestamp": datetime.now(),
                "participants": context.participants,
                "significance": self._calculate_interaction_significance(
                    context, interaction_data
                ),
            }
        except Exception as e:
            self.logger.error(f"Semantic memory creation failed: {e}")
            return None

    async def _create_procedural_memory(
        self,
        agent_id: str,
        context: InteractionContext,
        interaction_data: Dict[str, Any],
    ) -> Optional[MemoryItem]:
        """Create procedural memory item."""
        try:
            return {
                "memory_id": f"{context.interaction_id}_{agent_id}_procedural",
                "agent_id": agent_id,
                "memory_type": MemoryType.PROCEDURAL,
                "content": f"Skills used in {context.interaction_type.value}",
                "timestamp": datetime.now(),
                "significance": self._calculate_memory_significance(
                    agent_id, context, interaction_data
                ),
            }
        except Exception as e:
            self.logger.error(f"Procedural memory creation failed: {e}")
            return None
