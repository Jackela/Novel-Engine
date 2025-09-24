"""
Interaction Type Processors
===========================

Specialized processors for different interaction types with category-specific logic,
content generation, and outcome handling for each interaction category.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.types import (
    InteractionContext,
    InteractionEngineConfig,
    InteractionType,
)

# Import enhanced core systems
try:
    from src.core.character_manager import CharacterManager
    from src.core.data_models import (
        CharacterState,
        ErrorInfo,
        MemoryItem,
        StandardResponse,
    )
    from src.core.equipment_manager import EquipmentManager
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
    AgentID = str
    CharacterManager = None
    EquipmentManager = None

__all__ = ["InteractionTypeProcessorManager", "BaseInteractionProcessor"]


class BaseInteractionProcessor(ABC):
    """
    Abstract base class for interaction type processors.

    Defines the interface and common functionality for specialized
    interaction type processors.
    """

    def __init__(
        self,
        config: InteractionEngineConfig,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize base processor.

        Args:
            config: Interaction engine configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.processing_stats = {
            "processed_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "average_duration": 0.0,
        }

    @property
    @abstractmethod
    def supported_type(self) -> InteractionType:
        """Return the interaction type this processor handles."""
        pass

    @abstractmethod
    async def process_interaction(
        self, context: InteractionContext
    ) -> StandardResponse:
        """
        Process interaction of this processor's type.

        Args:
            context: Interaction context to process

        Returns:
            StandardResponse with processing results
        """
        pass

    @abstractmethod
    async def validate_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """
        Validate context for this interaction type.

        Args:
            context: Context to validate

        Returns:
            StandardResponse with validation results
        """
        pass

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics for this processor."""
        return {
            "interaction_type": self.supported_type.value,
            **self.processing_stats,
        }

    def _update_stats(self, success: bool, duration: float):
        """Update processing statistics."""
        self.processing_stats["processed_count"] += 1
        if success:
            self.processing_stats["success_count"] += 1
        else:
            self.processing_stats["failure_count"] += 1

        # Update average duration
        total_time = (
            self.processing_stats["average_duration"]
            * (self.processing_stats["processed_count"] - 1)
        ) + duration
        self.processing_stats["average_duration"] = (
            total_time / self.processing_stats["processed_count"]
        )


class DialogueProcessor(BaseInteractionProcessor):
    """Processor for dialogue interactions."""

    @property
    def supported_type(self) -> InteractionType:
        return InteractionType.DIALOGUE

    async def validate_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Validate dialogue context."""
        try:
            if len(context.participants) < 2:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INSUFFICIENT_PARTICIPANTS",
                        message="Dialogue requires at least 2 participants",
                        recoverable=True,
                    ),
                )

            return StandardResponse(
                success=True,
                data={
                    "validation": "passed",
                    "participant_count": len(context.participants),
                },
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="DIALOGUE_VALIDATION_ERROR",
                    message=f"Dialogue validation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def process_interaction(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Process dialogue interaction."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Processing dialogue interaction: {context.interaction_id}"
            )

            # Validate context first
            validation = await self.validate_context(context)
            if not validation.success:
                return validation

            # Generate dialogue content
            dialogue_content = await self._generate_dialogue_content(context)

            # Process conversational flow
            conversation_flow = await self._process_conversation_flow(
                context, dialogue_content
            )

            # Calculate emotional impacts
            emotional_impacts = await self._calculate_emotional_impacts(
                context, dialogue_content
            )

            # Generate dialogue outcome
            outcome_data = {
                "interaction_type": "dialogue",
                "dialogue_content": dialogue_content,
                "conversation_flow": conversation_flow,
                "emotional_impacts": emotional_impacts,
                "participant_count": len(context.participants),
                "exchange_count": len(dialogue_content.get("exchanges", [])),
            }

            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(True, duration)

            return StandardResponse(
                success=True,
                data=outcome_data,
                metadata={"blessing": "dialogue_processed"},
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration)

            self.logger.error(f"Dialogue processing failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="DIALOGUE_PROCESSING_FAILED",
                    message=f"Dialogue processing failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _generate_dialogue_content(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Generate dialogue content for participants."""
        try:
            # Simulate dialogue generation
            exchanges = []

            for i, participant in enumerate(
                context.participants[: self.config.max_dialogue_exchanges]
            ):
                exchange = {
                    "speaker": participant,
                    "content": f"Dialogue content from {participant} in interaction {context.interaction_id}",
                    "emotional_tone": "neutral",
                    "timestamp": datetime.now().isoformat(),
                }
                exchanges.append(exchange)

            return {
                "exchanges": exchanges,
                "total_exchanges": len(exchanges),
                "quality_score": 0.8,
                "coherence_score": 0.9,
            }

        except Exception as e:
            self.logger.error(f"Dialogue content generation failed: {e}")
            return {"exchanges": [], "error": str(e)}

    async def _process_conversation_flow(
        self, context: InteractionContext, dialogue_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process conversation flow and dynamics."""
        try:
            return {
                "flow_type": "sequential",
                "turn_taking": "balanced",
                "interruptions": 0,
                "topic_changes": 1,
                "engagement_level": 0.85,
            }
        except Exception as e:
            self.logger.error(f"Conversation flow processing failed: {e}")
            return {"flow_type": "error", "error": str(e)}

    async def _calculate_emotional_impacts(
        self, context: InteractionContext, dialogue_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate emotional impacts of dialogue."""
        try:
            impacts = {}
            for participant in context.participants:
                impacts[participant] = {
                    "mood_change": 0.1,
                    "relationship_changes": {
                        p: 0.05
                        for p in context.participants
                        if p != participant
                    },
                    "emotional_state": "content",
                }
            return impacts
        except Exception as e:
            self.logger.error(f"Emotional impact calculation failed: {e}")
            return {}


class CombatProcessor(BaseInteractionProcessor):
    """Processor for combat interactions."""

    @property
    def supported_type(self) -> InteractionType:
        return InteractionType.COMBAT

    async def validate_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Validate combat context."""
        try:
            if len(context.participants) < 2:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INSUFFICIENT_COMBATANTS",
                        message="Combat requires at least 2 participants",
                        recoverable=True,
                    ),
                )

            # Check for combat constraints
            if "no_combat" in context.constraints:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="COMBAT_CONSTRAINED",
                        message="Combat is not allowed by constraints",
                        recoverable=False,
                    ),
                )

            return StandardResponse(
                success=True,
                data={
                    "validation": "passed",
                    "combatant_count": len(context.participants),
                },
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="COMBAT_VALIDATION_ERROR",
                    message=f"Combat validation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def process_interaction(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Process combat interaction."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Processing combat interaction: {context.interaction_id}"
            )

            # Validate context first
            validation = await self.validate_context(context)
            if not validation.success:
                return validation

            # Initialize combat state
            combat_state = await self._initialize_combat_state(context)

            # Process combat rounds
            combat_results = await self._process_combat_rounds(
                context, combat_state
            )

            # Calculate combat outcome
            combat_outcome = await self._determine_combat_outcome(
                context, combat_results
            )

            # Generate combat outcome data
            outcome_data = {
                "interaction_type": "combat",
                "combat_state": combat_state,
                "combat_results": combat_results,
                "combat_outcome": combat_outcome,
                "participant_count": len(context.participants),
                "rounds_processed": len(combat_results.get("rounds", [])),
            }

            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(True, duration)

            return StandardResponse(
                success=True,
                data=outcome_data,
                metadata={"blessing": "combat_processed"},
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration)

            self.logger.error(f"Combat processing failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="COMBAT_PROCESSING_FAILED",
                    message=f"Combat processing failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _initialize_combat_state(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Initialize combat state for participants."""
        try:
            combat_state = {
                "participants": {},
                "initiative_order": context.participants.copy(),
                "current_round": 1,
                "combat_status": "active",
            }

            for participant in context.participants:
                combat_state["participants"][participant] = {
                    "health": 100,
                    "status_effects": [],
                    "actions_remaining": 1,
                    "position": "combat_ready",
                }

            return combat_state
        except Exception as e:
            self.logger.error(f"Combat state initialization failed: {e}")
            return {"error": str(e)}

    async def _process_combat_rounds(
        self, context: InteractionContext, combat_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process combat rounds."""
        try:
            rounds = []
            max_rounds = 5  # Prevent infinite combat

            for round_num in range(1, max_rounds + 1):
                round_result = {
                    "round": round_num,
                    "actions": [],
                    "round_outcome": "completed",
                }

                for participant in combat_state["initiative_order"]:
                    action = {
                        "actor": participant,
                        "action_type": "attack",
                        "target": next(
                            p for p in context.participants if p != participant
                        ),
                        "success": True,
                        "damage": 10,
                    }
                    round_result["actions"].append(action)

                rounds.append(round_result)

                # Check for combat end conditions
                if (
                    len(
                        [
                            p
                            for p in combat_state["participants"]
                            if combat_state["participants"][p]["health"] > 0
                        ]
                    )
                    <= 1
                ):
                    break

            return {"rounds": rounds, "total_rounds": len(rounds)}
        except Exception as e:
            self.logger.error(f"Combat round processing failed: {e}")
            return {"rounds": [], "error": str(e)}

    async def _determine_combat_outcome(
        self, context: InteractionContext, combat_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine final combat outcome."""
        try:
            return {
                "result": "victory",
                "winner": context.participants[0]
                if context.participants
                else "none",
                "casualties": [],
                "experience_gained": 100,
                "loot_generated": [],
            }
        except Exception as e:
            self.logger.error(f"Combat outcome determination failed: {e}")
            return {"result": "error", "error": str(e)}


class CooperationProcessor(BaseInteractionProcessor):
    """Processor for cooperation interactions."""

    @property
    def supported_type(self) -> InteractionType:
        return InteractionType.COOPERATION

    async def validate_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Validate cooperation context."""
        try:
            if len(context.participants) < 2:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INSUFFICIENT_COOPERATORS",
                        message="Cooperation requires at least 2 participants",
                        recoverable=True,
                    ),
                )

            return StandardResponse(
                success=True,
                data={
                    "validation": "passed",
                    "cooperator_count": len(context.participants),
                },
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="COOPERATION_VALIDATION_ERROR",
                    message=f"Cooperation validation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def process_interaction(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Process cooperation interaction."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Processing cooperation interaction: {context.interaction_id}"
            )

            # Validate context first
            validation = await self.validate_context(context)
            if not validation.success:
                return validation

            # Coordinate collaborative actions
            collaboration_plan = await self._create_collaboration_plan(context)

            # Execute collaborative activities
            execution_results = await self._execute_collaboration(
                context, collaboration_plan
            )

            # Measure cooperation success
            cooperation_metrics = await self._measure_cooperation_success(
                context, execution_results
            )

            outcome_data = {
                "interaction_type": "cooperation",
                "collaboration_plan": collaboration_plan,
                "execution_results": execution_results,
                "cooperation_metrics": cooperation_metrics,
                "participant_count": len(context.participants),
            }

            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(True, duration)

            return StandardResponse(
                success=True,
                data=outcome_data,
                metadata={"blessing": "cooperation_processed"},
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration)

            self.logger.error(f"Cooperation processing failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="COOPERATION_PROCESSING_FAILED",
                    message=f"Cooperation processing failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _create_collaboration_plan(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Create collaboration plan for participants."""
        try:
            return {
                "objectives": context.expected_outcomes or ["work_together"],
                "role_assignments": {
                    p: "collaborator" for p in context.participants
                },
                "coordination_method": "consensus",
                "success_criteria": [
                    "objective_completion",
                    "participant_satisfaction",
                ],
            }
        except Exception as e:
            self.logger.error(f"Collaboration plan creation failed: {e}")
            return {"error": str(e)}

    async def _execute_collaboration(
        self, context: InteractionContext, plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute collaborative activities."""
        try:
            return {
                "activities_completed": len(plan.get("objectives", [])),
                "participation_rate": 1.0,
                "coordination_success": 0.9,
                "conflicts_resolved": 0,
            }
        except Exception as e:
            self.logger.error(f"Collaboration execution failed: {e}")
            return {"error": str(e)}

    async def _measure_cooperation_success(
        self, context: InteractionContext, results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Measure cooperation success metrics."""
        try:
            return {
                "overall_success": 0.85,
                "participant_satisfaction": {
                    p: 0.8 for p in context.participants
                },
                "objective_completion": 0.9,
                "team_cohesion_improvement": 0.1,
            }
        except Exception as e:
            self.logger.error(f"Cooperation metrics calculation failed: {e}")
            return {"error": str(e)}


class InteractionTypeProcessorManager:
    """
    Manager for interaction type processors.

    Coordinates and delegates to specialized interaction processors
    based on interaction type.
    """

    def __init__(
        self,
        config: InteractionEngineConfig,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize processor manager.

        Args:
            config: Interaction engine configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Initialize processors
        self.processors: Dict[InteractionType, BaseInteractionProcessor] = {}
        self._initialize_processors()

        self.logger.info(
            f"Interaction type processor manager initialized with {len( self.processors)} processors"
        )

    def _initialize_processors(self):
        """Initialize all interaction type processors."""
        try:
            # Core processors
            self.processors[InteractionType.DIALOGUE] = DialogueProcessor(
                self.config, self.logger
            )
            self.processors[InteractionType.COMBAT] = CombatProcessor(
                self.config, self.logger
            )
            self.processors[
                InteractionType.COOPERATION
            ] = CooperationProcessor(self.config, self.logger)

            # Additional processors would be added here
            # self.processors[InteractionType.NEGOTIATION] = NegotiationProcessor(self.config, self.logger)
            # self.processors[InteractionType.INSTRUCTION] = InstructionProcessor(self.config, self.logger)
            # self.processors[InteractionType.RITUAL] = RitualProcessor(self.config, self.logger)
            # self.processors[InteractionType.EXPLORATION] = ExplorationProcessor(self.config, self.logger)
            # self.processors[InteractionType.MAINTENANCE] = MaintenanceProcessor(self.config, self.logger)
            # self.processors[InteractionType.EMERGENCY] = EmergencyProcessor(self.config, self.logger)

        except Exception as e:
            self.logger.error(f"Processor initialization failed: {e}")

    async def process_interaction(
        self, context: InteractionContext
    ) -> StandardResponse:
        """
        Process interaction using appropriate type processor.

        Args:
            context: Interaction context to process

        Returns:
            StandardResponse with processing results
        """
        try:
            processor = self.processors.get(context.interaction_type)

            if not processor:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="UNSUPPORTED_INTERACTION_TYPE",
                        message=f"No processor available for interaction type: {context.interaction_type.value}",
                        recoverable=False,
                    ),
                )

            self.logger.debug(
                f"Processing {context.interaction_type.value}interaction: {context.interaction_id}"
            )
            return await processor.process_interaction(context)

        except Exception as e:
            self.logger.error(f"Interaction processing failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PROCESSING_ERROR",
                    message=f"Interaction processing failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def validate_interaction_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """
        Validate interaction context using appropriate type processor.

        Args:
            context: Context to validate

        Returns:
            StandardResponse with validation results
        """
        try:
            processor = self.processors.get(context.interaction_type)

            if not processor:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="UNSUPPORTED_INTERACTION_TYPE",
                        message=f"No processor available for interaction type: {context.interaction_type.value}",
                        recoverable=False,
                    ),
                )

            return await processor.validate_context(context)

        except Exception as e:
            self.logger.error(f"Context validation failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="VALIDATION_ERROR",
                    message=f"Context validation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def get_supported_types(self) -> List[InteractionType]:
        """Get list of supported interaction types."""
        return list(self.processors.keys())

    def get_processor_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get processing statistics for all processors."""
        return {
            interaction_type.value: processor.get_processing_statistics()
            for interaction_type, processor in self.processors.items()
        }

    def get_processor(
        self, interaction_type: InteractionType
    ) -> Optional[BaseInteractionProcessor]:
        """Get processor for specific interaction type."""
        return self.processors.get(interaction_type)
