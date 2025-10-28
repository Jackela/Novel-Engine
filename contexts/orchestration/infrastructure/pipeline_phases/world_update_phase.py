#!/usr/bin/env python3
"""
World Update Phase Implementation

Coordinates world state updates including entity positioning,
time progression, environment changes, and state consistency.
"""

from datetime import datetime
from typing import Any, Dict, List

from ...domain.value_objects import PhaseType
from .base_phase import BasePhaseImplementation, PhaseExecutionContext, PhaseResult


class WorldUpdatePhase(BasePhaseImplementation):
    """
    Implementation of world state update pipeline phase.

    Coordinates with the World context to:
    - Advance world time based on configuration
    - Update entity positions and states
    - Process environment changes
    - Maintain world state consistency
    - Create rollback snapshots for saga compensation
    """

    def __init__(self):
        super().__init__(PhaseType.WORLD_UPDATE)
        self.execution_timeout_ms = 8000  # 8 seconds for world updates
        self.world_service_endpoint = "world_context"

    async def _execute_phase_implementation(self, context: PhaseExecutionContext) -> PhaseResult:
        """
        Execute world state update operations.

        Args:
            context: Phase execution context

        Returns:
            PhaseResult with world update results
        """
        # Initialize phase metrics
        entities_updated = 0
        environment_changes = 0
        time_advanced_seconds = 0

        try:
            # Step 1: Create world state snapshot for rollback
            await self._create_world_state_snapshot(context)

            # Step 2: Advance world time
            time_advanced_seconds = await self._advance_world_time(context)

            # Step 3: Update entity positions and states
            entities_updated = await self._update_entity_states(context)

            # Step 4: Process environment changes
            environment_changes = await self._process_environment_changes(context)

            # Step 5: Validate world state consistency
            await self._validate_world_consistency(context)

            # Step 6: Generate world update events
            world_events = await self._generate_world_events(
                context, entities_updated, time_advanced_seconds, environment_changes
            )

            # Record performance metrics
            context.record_performance_metric("entities_updated", float(entities_updated))
            context.record_performance_metric("time_advanced_seconds", float(time_advanced_seconds))
            context.record_performance_metric("environment_changes", float(environment_changes))
            context.record_performance_metric("world_events_generated", float(len(world_events)))

            return PhaseResult(
                success=True,
                events_processed=entities_updated + environment_changes,
                events_generated=world_events,
                artifacts_created=[
                    f"world_state_snapshot_{context.turn_id}",
                    f"time_advancement_{time_advanced_seconds}s",
                    f"entity_updates_{entities_updated}",
                ],
                metadata={
                    "world_update_summary": {
                        "time_advanced_seconds": time_advanced_seconds,
                        "entities_updated": entities_updated,
                        "environment_changes": environment_changes,
                        "world_consistency_validated": True,
                    }
                },
            )

        except Exception as e:
            # Handle world update failure
            return self._create_failure_result(
                context,
                f"World update failed: {e}",
                {
                    "partial_updates": {
                        "entities_updated": entities_updated,
                        "time_advanced_seconds": time_advanced_seconds,
                        "environment_changes": environment_changes,
                    },
                    "failure_stage": self._determine_failure_stage(e),
                },
            )

    def _validate_preconditions(self, context: PhaseExecutionContext) -> None:
        """
        Validate preconditions for world update execution.

        Args:
            context: Phase execution context

        Raises:
            ValueError: If preconditions are not met
        """
        # Check world time advance setting
        if context.configuration.world_time_advance <= 0:
            raise ValueError("World time advance must be positive")

        # Validate time manipulation permissions
        if not context.configuration.allow_time_manipulation:
            raise ValueError("Time manipulation not allowed by configuration")

        # Check for required world state access
        if not context.participants:
            # No participants means no entities to update - this is valid but limited
            pass

    async def _create_world_state_snapshot(self, context: PhaseExecutionContext) -> None:
        """
        Create comprehensive world state snapshot for rollback.

        Args:
            context: Phase execution context
        """
        # Get current world state
        world_state_response = await self._call_external_service(
            context,
            self.world_service_endpoint,
            "get_world_state",
            {
                "include_entities": True,
                "include_environment": True,
                "include_time_state": True,
            },
        )

        # Create snapshot
        snapshot_data = {
            "current_time": world_state_response.get("current_time"),
            "entity_states": world_state_response.get("entity_states", {}),
            "environment_state": world_state_response.get("environment_state", {}),
            "world_metadata": world_state_response.get("metadata", {}),
            "participant_positions": world_state_response.get("participant_positions", {}),
            "snapshot_created_at": datetime.now().isoformat(),
        }

        # Store for rollback
        self._create_rollback_snapshot(context, "world_state", snapshot_data)

        context.record_performance_metric("snapshot_size_kb", len(str(snapshot_data)) / 1024.0)

    async def _advance_world_time(self, context: PhaseExecutionContext) -> int:
        """
        Advance world time according to configuration.

        Args:
            context: Phase execution context

        Returns:
            Seconds of time advanced
        """
        time_advance_seconds = context.configuration.world_time_advance

        # Call world context to advance time
        response = await self._call_external_service(
            context,
            self.world_service_endpoint,
            "advance_time",
            {
                "seconds": time_advance_seconds,
                "turn_id": str(context.turn_id),
                "update_metadata": {
                    "source": "turn_orchestration",
                    "participants": context.participants,
                },
            },
        )

        if not response.get("success"):
            raise RuntimeError(f"Failed to advance world time: {response.get('error')}")

        # Record time advancement event
        self._record_event_generation(
            context,
            "world_time_advanced",
            {
                "seconds_advanced": time_advance_seconds,
                "new_world_time": response.get("new_world_time"),
                "previous_world_time": response.get("previous_world_time"),
            },
        )

        return time_advance_seconds

    async def _update_entity_states(self, context: PhaseExecutionContext) -> int:
        """
        Update entity states for all participants.

        Args:
            context: Phase execution context

        Returns:
            Number of entities updated
        """
        if not context.participants:
            return 0

        entities_updated = 0

        # Process each participant entity
        for participant_id in context.participants:
            try:
                # Get current entity state
                entity_response = await self._call_external_service(
                    context,
                    self.world_service_endpoint,
                    "get_entity_state",
                    {"entity_id": participant_id},
                )

                if not entity_response.get("success"):
                    continue  # Skip entities that can't be retrieved

                # Calculate entity updates based on time passage
                entity_updates = self._calculate_entity_updates(
                    entity_response.get("entity_data", {}),
                    context.configuration.world_time_advance,
                )

                if entity_updates:
                    # Apply entity updates
                    update_response = await self._call_external_service(
                        context,
                        self.world_service_endpoint,
                        "update_entity",
                        {
                            "entity_id": participant_id,
                            "updates": entity_updates,
                            "turn_id": str(context.turn_id),
                        },
                    )

                    if update_response.get("success"):
                        entities_updated += 1

                        # Record entity update event
                        self._record_event_generation(
                            context,
                            "entity_updated",
                            {
                                "entity_id": participant_id,
                                "updates_applied": entity_updates,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

            except Exception:
                # Log entity update failure but continue with others
                context.record_performance_metric(
                    "entity_update_failures",
                    context.performance_metrics.get("entity_update_failures", 0) + 1,
                )

        return entities_updated

    async def _process_environment_changes(self, context: PhaseExecutionContext) -> int:
        """
        Process environment changes based on time advancement.

        Args:
            context: Phase execution context

        Returns:
            Number of environment changes processed
        """
        # Get pending environment changes
        env_response = await self._call_external_service(
            context,
            self.world_service_endpoint,
            "get_pending_environment_changes",
            {
                "time_advanced": context.configuration.world_time_advance,
                "affected_areas": self._get_participant_areas(context.participants),
            },
        )

        pending_changes = env_response.get("pending_changes", [])
        changes_processed = 0

        for change in pending_changes:
            try:
                # Apply environment change
                change_response = await self._call_external_service(
                    context,
                    self.world_service_endpoint,
                    "apply_environment_change",
                    {
                        "change_id": change.get("id"),
                        "change_data": change,
                        "turn_id": str(context.turn_id),
                    },
                )

                if change_response.get("success"):
                    changes_processed += 1

                    # Record environment change event
                    self._record_event_generation(
                        context,
                        "environment_changed",
                        {
                            "change_type": change.get("type"),
                            "affected_area": change.get("area"),
                            "change_details": change.get("details"),
                        },
                    )

            except Exception:
                # Log environment change failure but continue
                context.record_performance_metric(
                    "environment_change_failures",
                    context.performance_metrics.get("environment_change_failures", 0) + 1,
                )

        return changes_processed

    async def _validate_world_consistency(self, context: PhaseExecutionContext) -> None:
        """
        Validate world state consistency after updates.

        Args:
            context: Phase execution context

        Raises:
            RuntimeError: If world state is inconsistent
        """
        # Perform world consistency check
        consistency_response = await self._call_external_service(
            context,
            self.world_service_endpoint,
            "validate_world_consistency",
            {
                "turn_id": str(context.turn_id),
                "check_entity_positions": True,
                "check_time_consistency": True,
                "check_environment_integrity": True,
            },
        )

        if not consistency_response.get("success"):
            raise RuntimeError(
                f"World consistency validation failed: {consistency_response.get('error')}"
            )

        consistency_issues = consistency_response.get("issues", [])
        if consistency_issues:
            # Log issues but determine if they're critical
            critical_issues = [
                issue for issue in consistency_issues if issue.get("severity") == "critical"
            ]

            if critical_issues:
                raise RuntimeError(f"Critical world consistency issues found: {critical_issues}")

        # Record consistency validation metrics
        context.record_performance_metric(
            "consistency_issues_found", float(len(consistency_issues))
        )
        context.record_performance_metric(
            "consistency_score", consistency_response.get("score", 1.0)
        )

    async def _generate_world_events(
        self,
        context: PhaseExecutionContext,
        entities_updated: int,
        time_advanced: int,
        environment_changes: int,
    ) -> List:
        """
        Generate events for world state changes.

        Args:
            context: Phase execution context
            entities_updated: Number of entities updated
            time_advanced: Seconds of time advanced
            environment_changes: Number of environment changes

        Returns:
            List of generated event IDs
        """
        events_generated = []

        # Generate turn world update summary event
        summary_event_id = self._record_event_generation(
            context,
            "turn_world_update_completed",
            {
                "turn_id": str(context.turn_id),
                "entities_updated": entities_updated,
                "time_advanced_seconds": time_advanced,
                "environment_changes": environment_changes,
                "participants": context.participants,
                "completed_at": datetime.now().isoformat(),
            },
        )
        events_generated.append(summary_event_id)

        # Generate time progression event if significant
        if time_advanced > 0:
            time_event_id = self._record_event_generation(
                context,
                "world_time_progression",
                {
                    "seconds_advanced": time_advanced,
                    "turn_context": str(context.turn_id),
                },
            )
            events_generated.append(time_event_id)

        return events_generated

    # Helper methods

    def _calculate_entity_updates(
        self, entity_data: Dict[str, Any], time_advanced_seconds: int
    ) -> Dict[str, Any]:
        """
        Calculate entity updates based on time passage.

        Args:
            entity_data: Current entity data
            time_advanced_seconds: Time advanced in seconds

        Returns:
            Dictionary of updates to apply
        """
        updates = {}

        # Example entity update calculations
        # In a real implementation, this would use game-specific logic

        # Update position based on movement
        current_position = entity_data.get("position", {})
        movement_speed = entity_data.get("movement_speed", 0)

        if movement_speed > 0 and current_position:
            # Simple movement calculation
            distance_moved = movement_speed * time_advanced_seconds
            if distance_moved > 0:
                updates["position_updated"] = True
                updates["distance_moved"] = distance_moved

        # Update status effects based on time
        status_effects = entity_data.get("status_effects", [])
        if status_effects:
            updated_effects = []
            for effect in status_effects:
                remaining_duration = effect.get("duration", 0) - time_advanced_seconds
                if remaining_duration > 0:
                    effect["duration"] = remaining_duration
                    updated_effects.append(effect)

            if len(updated_effects) != len(status_effects):
                updates["status_effects"] = updated_effects

        # Update resources (health, mana, etc.) based on regeneration
        resources = entity_data.get("resources", {})
        if resources:
            resource_updates = {}
            for resource_name, resource_value in resources.items():
                regen_rate = entity_data.get(f"{resource_name}_regen", 0)
                if regen_rate > 0:
                    new_value = min(
                        resource_value + (regen_rate * time_advanced_seconds),
                        entity_data.get(f"{resource_name}_max", resource_value),
                    )
                    if new_value != resource_value:
                        resource_updates[resource_name] = new_value

            if resource_updates:
                updates["resources"] = resource_updates

        return updates

    def _get_participant_areas(self, participants: List[str]) -> List[str]:
        """
        Get world areas affected by participants.

        Args:
            participants: List of participant IDs

        Returns:
            List of affected area identifiers
        """
        # In a real implementation, this would query participant locations
        # For now, return a default area
        return ["default_area"] if participants else []

    def _determine_failure_stage(self, error: Exception) -> str:
        """
        Determine which stage of world update failed.

        Args:
            error: Exception that occurred

        Returns:
            String identifying the failure stage
        """
        error_message = str(error).lower()

        if "snapshot" in error_message:
            return "snapshot_creation"
        elif "time" in error_message:
            return "time_advancement"
        elif "entity" in error_message:
            return "entity_updates"
        elif "environment" in error_message:
            return "environment_changes"
        elif "consistency" in error_message:
            return "consistency_validation"
        else:
            return "unknown"
