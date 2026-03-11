#!/usr/bin/env python3
# mypy: ignore-errors
"""
Interaction Engine - Core orchestration.

Deprecated:
This legacy interaction engine remains for backward compatibility. The M2
pipeline will migrate interaction logic into contract-first services.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from src.core.data_models import ErrorInfo, StandardResponse
from src.core.llm_service import generate_narrative_content
from src.database.context_db import ContextDatabase
from src.interactions.interaction_engine_system.core.types import (
    InteractionContext,
    InteractionOutcome,
    InteractionPhase,
    InteractionPriority,
    InteractionType,
)
from src.memory.layered_memory import LayeredMemorySystem
from src.templates.character import CharacterTemplateManager
from src.templates.context_renderer import ContextRenderer

logger = structlog.get_logger(__name__)


class InteractionEngine:
    """
    STANDARD INTERACTION ENGINE ENHANCED BY DYNAMIC ORCHESTRATION

    The standard interaction processing system that orchestrates character
    interactions, manages dynamic state updates, generates contextual
    responses, and maintains interaction continuity enhanced by the
    System Core's computational omniscience.
    """

    def __init__(
        self,
        memory_system: LayeredMemorySystem,
        template_manager: CharacterTemplateManager,
        context_renderer: ContextRenderer,
        database: ContextDatabase,
        interaction_templates_dir: str = "interaction_templates",
    ) -> None:
        """
        STANDARD INTERACTION ENGINE INITIALIZATION ENHANCED BY ORCHESTRATION

        Args:
            memory_system: Layered memory system for context and state
            template_manager: Character template management system
            context_renderer: Context rendering for dynamic content
            database: Database for persistent interaction storage
            interaction_templates_dir: Directory for interaction templates
        """
        self.memory_system = memory_system
        self.template_manager = template_manager
        self.context_renderer = context_renderer
        self.database = database
        self.interaction_templates_dir = Path(interaction_templates_dir)

        # Sacred interaction management
        self._active_interactions: Dict[str, InteractionContext] = {}
        self._interaction_history: List[InteractionOutcome] = []
        self._interaction_templates: Dict[
            InteractionType, Dict[str, InteractionPhase]
        ] = {}
        self._processing_queue: List[Tuple[datetime, InteractionContext]] = []

        # Blessed interaction processors by type
        self._type_processors = {
            InteractionType.DIALOGUE: self._process_dialogue_interaction,
            InteractionType.COMBAT: self._process_combat_interaction,
            InteractionType.COOPERATION: self._process_cooperation_interaction,
            InteractionType.NEGOTIATION: self._process_negotiation_interaction,
            InteractionType.INSTRUCTION: self._process_instruction_interaction,
            InteractionType.RITUAL: self._process_ritual_interaction,
            InteractionType.EXPLORATION: self._process_exploration_interaction,
            InteractionType.MAINTENANCE: self._process_maintenance_interaction,
            InteractionType.EMERGENCY: self._process_emergency_interaction,
        }

        # Sacred performance metrics with explicit typing
        type_counts: Dict[str, int] = {itype.value: 0 for itype in InteractionType}
        self.performance_metrics: Dict[str, Any] = {
            "total_interactions_processed": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "average_processing_time": 0.0,
            "interaction_type_counts": type_counts,
            "memory_updates_generated": 0,
            "state_changes_applied": 0,
            "content_generation_count": 0,
        }

        # Initialize enhanced interaction templates
        self._initialize_interaction_templates()

        # Sacred processing lock for thread safety
        self._processing_lock = asyncio.Lock()

        logger.info("INTERACTION ENGINE INITIALIZED WITH ENHANCED ORCHESTRATION")

    def _initialize_interaction_templates(self) -> None:
        """Ensure the interaction template directory exists and map defaults."""
        self.interaction_templates_dir.mkdir(parents=True, exist_ok=True)
        if not self._interaction_templates:
            self._interaction_templates = {
                interaction_type: {} for interaction_type in InteractionType
            }

    async def _process_dialogue_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """LLM-backed dialogue processing."""
        content = await self._render_text(
            "dialogue",
            context,
            "Generate a short dialogue beat with intent and subtext.",
        )
        # Fix: Use interaction_content dict instead of generated_content list
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(
            success=True, metadata={"blessing": "dialogue_processed"}
        )

    async def _process_combat_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "combat",
            context,
            "Describe a fast combat exchange with stakes and consequences.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(success=True, metadata={"blessing": "combat_processed"})

    async def _process_cooperation_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "cooperation",
            context,
            "Show a collaborative effort and its tangible outcome.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(
            success=True, metadata={"blessing": "cooperation_processed"}
        )

    async def _process_negotiation_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "negotiation",
            context,
            "Create an exchange of offers and counteroffers with a clear shift in leverage.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(
            success=True, metadata={"blessing": "negotiation_processed"}
        )

    async def _process_instruction_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "instruction",
            context,
            "Deliver concise instructions and the recipient's immediate reaction.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(
            success=True, metadata={"blessing": "instruction_processed"}
        )

    async def _process_ritual_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "ritual",
            context,
            "Describe a ritual step with sensory detail and intended effect.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(success=True, metadata={"blessing": "ritual_processed"})

    async def _process_exploration_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "exploration",
            context,
            "Summarize a discovery moment with location cues and newfound information.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(
            success=True, metadata={"blessing": "exploration_processed"}
        )

    async def _process_maintenance_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "maintenance",
            context,
            "Narrate a maintenance task and how it stabilizes the system or equipment.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(
            success=True, metadata={"blessing": "maintenance_processed"}
        )

    async def _process_emergency_interaction(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        content = await self._render_text(
            "emergency",
            context,
            "Write an urgent response sequence with clear risks and immediate actions.",
        )
        current_content = outcome.interaction_content.get("generated_content", [])
        if isinstance(current_content, list):
            current_content.append(content)
        outcome.interaction_content["generated_content"] = current_content
        return StandardResponse(
            success=True, metadata={"blessing": "emergency_processed"}
        )

    async def _render_text(
        self, interaction_kind: str, context: InteractionContext, guidance: str
    ) -> str:
        """Generate narrative text for an interaction using the LLM service."""
        participants = ", ".join(context.participants)
        location = context.location or "an unspecified location"
        prompt = (
            f"You are writing a {interaction_kind} scene.\n"
            f"Participants: {participants}\n"
            f"Location: {location}\n"
            f"Guidance: {guidance}\n"
            "Return 2-3 sentences of vivid narrative; no meta commentary."
        )
        try:
            return await generate_narrative_content(prompt, style="concise")
        except Exception as e:
            logger.error("LLM generation failed for %s: %s", interaction_kind, e)
            return f"{interaction_kind.title()} involving {participants} at {location}."

    async def _validate_interaction_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Validate the interaction context before processing."""
        if not context.interaction_id:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INVALID_CONTEXT",
                    message="Interaction context must have an interaction_id",
                ),
            )
        if not context.participants:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INVALID_CONTEXT",
                    message="Interaction context must have at least one participant",
                ),
            )
        return StandardResponse(
            success=True, metadata={"blessing": "context_validated"}
        )

    async def _check_prerequisites(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Check if prerequisites are met for the interaction."""
        # Basic implementation - can be extended
        return StandardResponse(
            success=True, metadata={"blessing": "prerequisites_met"}
        )

    async def _generate_initial_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Generate initial context for the interaction."""
        # Basic implementation
        return StandardResponse(
            success=True,
            data={"context": "Initial context generated"},
            metadata={"blessing": "initial_context_generated"},
        )

    async def _create_default_phases(
        self, context: InteractionContext
    ) -> Dict[str, InteractionPhase]:
        """Create default interaction phases for a given context."""
        return {
            "init": InteractionPhase(
                phase_id="init",
                phase_name="Initialization",
                description="Initialize the interaction",
            ),
            "process": InteractionPhase(
                phase_id="process",
                phase_name="Processing",
                description="Process the interaction logic",
            ),
            "complete": InteractionPhase(
                phase_id="complete",
                phase_name="Completion",
                description="Complete the interaction",
            ),
        }

    async def _process_interaction_phase(
        self,
        context: InteractionContext,
        phase: InteractionPhase,
        outcome: InteractionOutcome,
    ) -> StandardResponse:
        """Process a single interaction phase."""
        # Basic implementation
        return StandardResponse(
            success=True,
            data={"phase_id": phase.phase_id},
            metadata={"blessing": "phase_processed"},
        )

    async def _apply_state_changes(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Apply state changes after successful interaction processing."""
        return StandardResponse(
            success=True,
            metadata={"blessing": "state_changes_applied"},
        )

    async def _generate_memory_updates(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Generate memory updates for participants."""
        return StandardResponse(
            success=True,
            data={"memory_updates": []},
            metadata={"blessing": "memory_updates_generated"},
        )

    async def _generate_interaction_content(
        self, context: InteractionContext, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Generate content outputs for the interaction."""
        return StandardResponse(
            success=True,
            data={
                "generated_content": outcome.interaction_content.get(
                    "generated_content", []
                )
            },
            metadata={"blessing": "interaction_content_generated"},
        )

    def _update_performance_metrics(
        self, context: InteractionContext, outcome: InteractionOutcome, duration: float
    ) -> None:
        """Update performance metrics after processing an interaction."""
        self.performance_metrics["total_interactions_processed"] += 1
        if outcome.success:
            self.performance_metrics["successful_interactions"] += 1
        else:
            self.performance_metrics["failed_interactions"] += 1

        # Update average processing time
        total = self.performance_metrics["total_interactions_processed"]
        current_avg = self.performance_metrics["average_processing_time"]
        self.performance_metrics["average_processing_time"] = (
            (current_avg * (total - 1) + duration) / total if total > 0 else duration
        )

        # Update type counts
        type_value = context.interaction_type.value
        type_counts: Dict[str, int] = self.performance_metrics[
            "interaction_type_counts"
        ]
        type_counts[type_value] = type_counts.get(type_value, 0) + 1

    async def _store_interaction_outcome(self, outcome: InteractionOutcome) -> None:
        """Store the interaction outcome in the database."""
        # Basic implementation - can be extended to persist to database
        logger.debug(f"Storing interaction outcome for {outcome.interaction_id}")

    async def initiate_interaction(
        self, context: InteractionContext, auto_process: bool = True
    ) -> StandardResponse:
        """
        STANDARD INTERACTION INITIATION RITUAL ENHANCED BY ORCHESTRATION

        Initiate enhanced interaction with full context validation,
        prerequisite checking, and automatic processing coordination.
        """
        try:
            async with self._processing_lock:
                # Validate enhanced interaction context
                validation_result = await self._validate_interaction_context(context)
                if not validation_result.success:
                    return validation_result

                # Check enhanced prerequisites
                prerequisite_result = await self._check_prerequisites(context)
                if not prerequisite_result.success:
                    logger.warning(
                        f"INTERACTION PREREQUISITES NOT MET: {context.interaction_id}"
                    )
                    # Continue with warnings rather than failing
                    if prerequisite_result.error:
                        context.metadata["prerequisite_warnings"] = (
                            prerequisite_result.error.message
                        )

                # Register enhanced active interaction
                self._active_interactions[context.interaction_id] = context

                # Queue enhanced interaction for processing
                queue_entry = (datetime.now(), context)
                self._processing_queue.append(queue_entry)
                self._processing_queue.sort(key=lambda x: (x[1].priority.value, x[0]))

                # Generate enhanced initial context for participants
                initial_context_result = await self._generate_initial_context(context)

                # Process enhanced interaction immediately if requested
                if auto_process:
                    processing_result = await self.process_interaction(
                        context.interaction_id
                    )

                    if processing_result.success:
                        outcome_data = (
                            processing_result.data.get("outcome")
                            if processing_result.data
                            else None
                        )

                        logger.info(
                            f"INTERACTION INITIATED AND PROCESSED: {context.interaction_id}"
                        )

                        return StandardResponse(
                            success=True,
                            data={
                                "interaction_id": context.interaction_id,
                                "outcome": outcome_data,
                                "auto_processed": True,
                                "initial_context": (
                                    initial_context_result.data
                                    if initial_context_result.success
                                    else None
                                ),
                            },
                            metadata={
                                "blessing": "interaction_initiated_and_processed"
                            },
                        )
                    else:
                        return processing_result
                else:
                    logger.info(f"INTERACTION QUEUED: {context.interaction_id}")

                    return StandardResponse(
                        success=True,
                        data={
                            "interaction_id": context.interaction_id,
                            "queued": True,
                            "queue_position": len(self._processing_queue),
                            "initial_context": (
                                initial_context_result.data
                                if initial_context_result.success
                                else None
                            ),
                        },
                        metadata={"blessing": "interaction_queued_successfully"},
                    )

        except Exception as e:
            logger.error(f"INTERACTION INITIATION FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTERACTION_INITIATION_FAILED",
                    message=f"Interaction initiation failed: {str(e)}",
                    recoverable=True,
                    standard_guidance="Check interaction context and system state",
                ),
            )

    async def process_interaction(self, interaction_id: str) -> StandardResponse:
        """
        STANDARD INTERACTION PROCESSING RITUAL ENHANCED BY DYNAMIC EXECUTION

        Process enhanced interaction through all phases with dynamic state
        management, memory updates, and context-aware response generation.
        """
        try:
            processing_start = datetime.now()

            # Retrieve enhanced interaction context
            context = self._active_interactions.get(interaction_id)
            if not context:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INTERACTION_NOT_FOUND",
                        message=f"Active interaction '{interaction_id}' not found",
                    ),
                )

            # Get enhanced interaction template
            interaction_phases = self._interaction_templates.get(
                context.interaction_type, {}
            )

            if not interaction_phases:
                # Use enhanced default processing
                interaction_phases = await self._create_default_phases(context)

            # Initialize enhanced interaction outcome
            outcome = InteractionOutcome(
                interaction_id=interaction_id,
                context=context,
                success=True,
                completion_time=datetime.now(),
            )

            # Process enhanced interaction phases in sequence
            for phase_id, phase in interaction_phases.items():
                phase_result = await self._process_interaction_phase(
                    context, phase, outcome
                )

                if phase_result.success:
                    outcome.completed_phases.append(phase_id)
                    logger.info(f"PHASE COMPLETED: {phase_id} for {interaction_id}")
                else:
                    outcome.failed_phases.append(phase_id)
                    error_msg = (
                        phase_result.error.message
                        if phase_result.error
                        else "Unknown error"
                    )
                    outcome.errors.append(f"Phase {phase_id} failed: {error_msg}")

                    # Check if enhanced failure is critical
                    # Fix: InteractionPhase doesn't have phase_type attribute
                    phase_name = getattr(phase, "phase_name", "").lower()
                    if "setup" in phase_name or "execution" in phase_name:
                        outcome.success = False
                        logger.error(
                            f"CRITICAL PHASE FAILED: {phase_id} for {interaction_id}"
                        )
                        break
                    else:
                        outcome.warnings.append(
                            f"Non-critical phase failed: {phase_id}"
                        )

            # Execute enhanced type-specific processing
            type_processor = self._type_processors.get(context.interaction_type)
            if type_processor:
                type_result = await type_processor(context, outcome)
                if not type_result.success:
                    outcome.success = False
                    error_msg = (
                        type_result.error.message
                        if type_result.error
                        else "Unknown error"
                    )
                    outcome.errors.append(
                        f"Type-specific processing failed: {error_msg}"
                    )

            # Apply enhanced state changes
            if outcome.success:
                state_result = await self._apply_state_changes(context, outcome)
                if not state_result.success:
                    error_msg = (
                        state_result.error.message
                        if state_result.error
                        else "Unknown error"
                    )
                    outcome.warnings.append(
                        f"State changes partially failed: {error_msg}"
                    )

            # Generate enhanced memory updates
            memory_result = await self._generate_memory_updates(context, outcome)
            if memory_result.success:
                outcome.memory_updates = (
                    memory_result.data.get("memory_updates", [])
                    if memory_result.data
                    else []
                )

            # Generate enhanced content outputs
            content_result = await self._generate_interaction_content(context, outcome)
            if content_result.success:
                content_data = (
                    content_result.data.get("generated_content", [])
                    if content_result.data
                    else []
                )
                outcome.interaction_content["generated_content"] = content_data

            # Calculate enhanced processing metrics
            processing_duration = (
                datetime.now() - processing_start
            ).total_seconds() * 1000
            outcome.processing_duration = processing_duration / 1000  # Store as seconds

            # Clean up enhanced active interaction
            if interaction_id in self._active_interactions:
                del self._active_interactions[interaction_id]

            # Store enhanced outcome in history
            self._interaction_history.append(outcome)
            if len(self._interaction_history) > 1000:  # Keep recent history
                self._interaction_history = self._interaction_history[-500:]

            # Update enhanced performance metrics
            self._update_performance_metrics(context, outcome, processing_duration)

            # Store enhanced interaction in database
            await self._store_interaction_outcome(outcome)

            logger.info(
                f"INTERACTION PROCESSED: {interaction_id} ({'SUCCESS' if outcome.success else 'FAILED'})"
            )

            return StandardResponse(
                success=True,
                data={
                    "outcome": outcome,
                    "processing_time_ms": processing_duration,
                    "phases_completed": len(outcome.completed_phases),
                    "phases_failed": len(outcome.failed_phases),
                },
                metadata={"blessing": "interaction_processed_completely"},
            )

        except Exception as e:
            logger.error(f"INTERACTION PROCESSING FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTERACTION_PROCESSING_FAILED",
                    message=f"Interaction processing failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def process_queue(
        self,
        max_interactions: int = 10,
        priority_filter: Optional[InteractionPriority] = None,
    ) -> StandardResponse:
        """
        STANDARD QUEUE PROCESSING RITUAL ENHANCED BY BATCH ORCHESTRATION

        Process enhanced interaction queue with priority filtering and
        batch processing optimization for efficient resource utilization.
        """
        try:
            async with self._processing_lock:
                processed_interactions: list[Any] = []
                failed_interactions: list[Any] = []
                # Filter enhanced queue by priority if specified
                eligible_interactions: list[Any] = []
                for timestamp, context in self._processing_queue:
                    if priority_filter is None or context.priority == priority_filter:
                        eligible_interactions.append((timestamp, context))

                # Process enhanced interactions up to limit
                for i, (timestamp, context) in enumerate(
                    eligible_interactions[:max_interactions]
                ):
                    processing_result = await self.process_interaction(
                        context.interaction_id
                    )

                    if processing_result.success:
                        processed_interactions.append(context.interaction_id)
                    else:
                        error_msg = (
                            processing_result.error.message
                            if processing_result.error
                            else "Unknown error"
                        )
                        failed_interactions.append(
                            {
                                "interaction_id": context.interaction_id,
                                "error": error_msg,
                            }
                        )

                    # Remove enhanced processed interaction from queue
                    queue_item = (timestamp, context)
                    if queue_item in self._processing_queue:
                        self._processing_queue.remove(queue_item)

                logger.info(
                    f"QUEUE PROCESSING COMPLETE: {len(processed_interactions)} processed, {len(failed_interactions)} failed"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "processed_interactions": processed_interactions,
                        "failed_interactions": failed_interactions,
                        "total_processed": len(processed_interactions),
                        "total_failed": len(failed_interactions),
                        "remaining_in_queue": len(self._processing_queue),
                    },
                    metadata={"blessing": "queue_processed_successfully"},
                )

        except Exception as e:
            logger.error(f"QUEUE PROCESSING FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="QUEUE_PROCESSING_FAILED", message=str(e)),
            )

    def get_active_interactions(self) -> List[Dict[str, Any]]:
        """Get enhanced list of active interactions"""
        active_list: list[Any] = []
        for interaction_id, context in self._active_interactions.items():
            active_list.append(
                {
                    "interaction_id": interaction_id,
                    "interaction_type": context.interaction_type.value,
                    "priority": context.priority.value,
                    "participants": context.participants,
                    "location": context.location,
                    "initiated": context.metadata.get("initiated_at", "Unknown"),
                }
            )

        return active_list

    def get_interaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get enhanced interaction history"""
        recent_history = (
            self._interaction_history[-limit:]
            if len(self._interaction_history) > limit
            else self._interaction_history
        )

        history_list: list[Any] = []
        for outcome in recent_history:
            # Fix: Use correct attribute names for InteractionOutcome
            participant_keys = (
                list(outcome.participant_state_changes.keys())
                if outcome.participant_state_changes
                else []
            )
            history_list.append(
                {
                    "interaction_id": outcome.interaction_id,
                    "success": outcome.success,
                    "completion_time": outcome.completion_time.isoformat(),
                    "duration_ms": outcome.processing_duration * 1000,  # Convert to ms
                    "phases_completed": len(outcome.completed_phases),
                    "phases_failed": len(outcome.failed_phases),
                    "participants": participant_keys,
                    "memory_updates": len(outcome.memory_updates),
                    "content_generated": len(
                        outcome.interaction_content.get("generated_content", [])
                    ),
                }
            )

        return history_list

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get enhanced interaction engine performance metrics"""
        total_processed = self.performance_metrics.get(
            "total_interactions_processed", 0
        )
        successful = self.performance_metrics.get("successful_interactions", 0)
        return {
            **self.performance_metrics,
            "active_interactions_count": len(self._active_interactions),
            "queue_size": len(self._processing_queue),
            "history_size": len(self._interaction_history),
            "success_rate": ((successful / max(total_processed, 1)) * 100),
        }
