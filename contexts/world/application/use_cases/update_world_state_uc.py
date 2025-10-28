#!/usr/bin/env python3
"""
Update World State Use Case

This module contains the use case for applying delta changes to world state.
It orchestrates domain operations while maintaining Clean Architecture principles.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...domain.aggregates.world_state import WorldState
from ...domain.repositories.world_state_repo import (
    ConcurrencyException,
    EntityNotFoundException,
    IWorldStateRepository,
)
from ..commands.world_commands import (
    ApplyWorldDelta,
    EntityOperation,
    EnvironmentOperation,
    ResetOperation,
    SnapshotOperation,
    TimeOperation,
    WorldOperationType,
)

logger = logging.getLogger(__name__)


class UpdateWorldStateResult:
    """
    Result of executing the UpdateWorldState use case.

    Encapsulates the outcome of applying world delta changes,
    including success/failure status, updated aggregate,
    and any events generated.
    """

    def __init__(
        self,
        success: bool,
        world_state: Optional[WorldState] = None,
        error_message: Optional[str] = None,
        operations_applied: int = 0,
        events_generated: List[str] = None,
        execution_time_ms: float = 0.0,
        warnings: List[str] = None,
    ):
        self.success = success
        self.world_state = world_state
        self.error_message = error_message
        self.operations_applied = operations_applied
        self.events_generated = events_generated or []
        self.execution_time_ms = execution_time_ms
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "success": self.success,
            "world_state_id": self.world_state.id if self.world_state else None,
            "world_state_version": (self.world_state.version if self.world_state else None),
            "error_message": self.error_message,
            "operations_applied": self.operations_applied,
            "events_generated": self.events_generated,
            "execution_time_ms": self.execution_time_ms,
            "warnings": self.warnings,
        }


class UpdateWorldStateUC:
    """
    Use case for applying delta changes to world state.

    This use case orchestrates the application of complex world state changes
    by coordinating between the application layer and domain layer. It follows
    Clean Architecture principles by depending on abstractions and delegating
    business logic to domain objects.

    Responsibilities:
    - Validate and authorize the command
    - Retrieve the target world state aggregate
    - Orchestrate the application of delta changes
    - Handle concurrency conflicts and retries
    - Ensure transactional consistency
    - Publish domain events
    - Provide comprehensive error handling and logging
    """

    def __init__(self, world_repository: IWorldStateRepository):
        """
        Initialize the use case with required dependencies.

        Args:
            world_repository: Repository for world state persistence
        """
        self.world_repository = world_repository
        self._operation_handlers = {
            WorldOperationType.ADD_ENTITY: self._apply_add_entity,
            WorldOperationType.REMOVE_ENTITY: self._apply_remove_entity,
            WorldOperationType.UPDATE_ENTITY: self._apply_update_entity,
            WorldOperationType.MOVE_ENTITY: self._apply_move_entity,
        }

    async def execute(self, command: ApplyWorldDelta) -> UpdateWorldStateResult:
        """
        Execute the use case to apply world state delta changes.

        This is the main entry point that orchestrates the entire operation.
        It handles validation, retrieval, application, and persistence of changes.

        Args:
            command: ApplyWorldDelta command containing the changes to apply

        Returns:
            UpdateWorldStateResult with the outcome of the operation
        """
        start_time = datetime.now()
        operations_applied = 0
        warnings = []

        try:
            logger.info(f"Starting world delta application for command {command.command_id}")
            logger.debug(f"Command details: {command.get_operation_summary()}")

            # Phase 1: Validate command
            await self._validate_command(command)

            # Phase 2: Retrieve world state
            world_state = await self._retrieve_world_state(command)

            # Phase 3: Validate version for optimistic concurrency control
            if command.expected_world_version is not None:
                if world_state.version != command.expected_world_version:
                    raise ConcurrencyException(
                        f"Version conflict: expected {command.expected_world_version}, got {world_state.version}",
                        command.expected_world_version,
                        world_state.version,
                    )

            # Phase 4: Apply operations in order
            operations_applied += await self._apply_entity_operations(
                world_state, command.entity_operations
            )

            if command.environment_operation:
                await self._apply_environment_operation(world_state, command.environment_operation)
                operations_applied += 1

            if command.time_operation:
                await self._apply_time_operation(world_state, command.time_operation)
                operations_applied += 1

            if command.snapshot_operation:
                await self._apply_snapshot_operation(world_state, command.snapshot_operation)
                operations_applied += 1

            if command.reset_operation:
                await self._apply_reset_operation(world_state, command.reset_operation)
                operations_applied += 1

            # Phase 5: Save the updated world state
            updated_world_state = await self.world_repository.save(world_state)

            # Phase 6: Collect domain events
            domain_events = updated_world_state.get_domain_events()
            event_ids = [event.event_id for event in domain_events]

            # Clear events from aggregate (they should be handled by infrastructure)
            updated_world_state.clear_domain_events()

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"Successfully applied {operations_applied} operations to world {command.world_state_id}"
            )
            logger.debug(f"Generated {len(event_ids)} domain events in {execution_time:.2f}ms")

            return UpdateWorldStateResult(
                success=True,
                world_state=updated_world_state,
                operations_applied=operations_applied,
                events_generated=event_ids,
                execution_time_ms=execution_time,
                warnings=warnings,
            )

        except ConcurrencyException as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Concurrency conflict in world delta application: {str(e)}"
            logger.warning(error_msg)

            return UpdateWorldStateResult(
                success=False,
                error_message=error_msg,
                operations_applied=operations_applied,
                execution_time_ms=execution_time,
            )

        except EntityNotFoundException as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"World state not found: {str(e)}"
            logger.error(error_msg)

            return UpdateWorldStateResult(
                success=False,
                error_message=error_msg,
                operations_applied=operations_applied,
                execution_time_ms=execution_time,
            )

        except ValueError as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Validation error in world delta application: {str(e)}"
            logger.error(error_msg)

            return UpdateWorldStateResult(
                success=False,
                error_message=error_msg,
                operations_applied=operations_applied,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Unexpected error in world delta application: {str(e)}"
            logger.exception(error_msg)

            return UpdateWorldStateResult(
                success=False,
                error_message=error_msg,
                operations_applied=operations_applied,
                execution_time_ms=execution_time,
            )

    async def _validate_command(self, command: ApplyWorldDelta) -> None:
        """
        Validate the command before execution.

        Args:
            command: Command to validate

        Raises:
            ValueError: If command is invalid
        """
        # Basic command validation is done in __post_init__
        # Additional business rule validation can be added here

        # Validate world state exists
        if not await self.world_repository.exists(command.world_state_id):
            raise EntityNotFoundException(f"World state {command.world_state_id} not found")

        # Validate entity operations don't conflict
        entity_ids_being_added = set()
        entity_ids_being_modified = set()

        for op in command.entity_operations:
            if op.operation_type == WorldOperationType.ADD_ENTITY:
                if op.entity_id in entity_ids_being_added:
                    raise ValueError(f"Duplicate entity addition: {op.entity_id}")
                entity_ids_being_added.add(op.entity_id)
            elif op.entity_id:
                if op.entity_id in entity_ids_being_modified:
                    raise ValueError(f"Multiple operations on same entity: {op.entity_id}")
                entity_ids_being_modified.add(op.entity_id)

        # Validate that entities being modified don't conflict with entities being added
        conflicts = entity_ids_being_added.intersection(entity_ids_being_modified)
        if conflicts:
            raise ValueError(f"Cannot add and modify same entities in one command: {conflicts}")

    async def _retrieve_world_state(self, command: ApplyWorldDelta) -> WorldState:
        """
        Retrieve the world state aggregate for modification.

        Args:
            command: Command containing the world state ID

        Returns:
            WorldState aggregate

        Raises:
            EntityNotFoundException: If world state not found
        """
        world_state = await self.world_repository.get_by_id(command.world_state_id)
        if not world_state:
            raise EntityNotFoundException(f"World state {command.world_state_id} not found")

        return world_state

    async def _apply_entity_operations(
        self, world_state: WorldState, operations: List[EntityOperation]
    ) -> int:
        """
        Apply entity operations to the world state.

        Args:
            world_state: World state aggregate to modify
            operations: List of entity operations to apply

        Returns:
            Number of operations successfully applied
        """
        operations_applied = 0

        for operation in operations:
            try:
                handler = self._operation_handlers.get(operation.operation_type)
                if handler:
                    await handler(world_state, operation)
                    operations_applied += 1
                else:
                    logger.warning(f"No handler for operation type: {operation.operation_type}")
            except Exception as e:
                logger.error(f"Failed to apply entity operation {operation.operation_type}: {e}")
                raise

        return operations_applied

    async def _apply_add_entity(self, world_state: WorldState, operation: EntityOperation) -> None:
        """Apply add entity operation."""
        world_state.add_entity(
            entity_id=operation.entity_id,
            entity_type=operation.entity_type,
            name=operation.entity_name,
            coordinates=operation.coordinates,
            properties=operation.properties,
            metadata=operation.metadata,
        )

    async def _apply_remove_entity(
        self, world_state: WorldState, operation: EntityOperation
    ) -> None:
        """Apply remove entity operation."""
        removed_entity = world_state.remove_entity(
            entity_id=operation.entity_id, reason=operation.reason
        )
        if not removed_entity:
            logger.warning(f"Entity {operation.entity_id} not found for removal")

    async def _apply_update_entity(
        self, world_state: WorldState, operation: EntityOperation
    ) -> None:
        """Apply update entity operation."""
        success = world_state.update_entity(
            entity_id=operation.entity_id,
            properties=operation.properties,
            metadata=operation.metadata,
            reason=operation.reason,
        )
        if not success:
            logger.warning(f"Entity {operation.entity_id} not found for update")

    async def _apply_move_entity(self, world_state: WorldState, operation: EntityOperation) -> None:
        """Apply move entity operation."""
        success = world_state.move_entity(
            entity_id=operation.entity_id,
            new_coordinates=operation.new_coordinates,
            reason=operation.reason,
        )
        if not success:
            logger.warning(f"Entity {operation.entity_id} not found for movement")

    async def _apply_environment_operation(
        self, world_state: WorldState, operation: EnvironmentOperation
    ) -> None:
        """
        Apply environment operation to the world state.

        Args:
            world_state: World state aggregate to modify
            operation: Environment operation to apply
        """
        world_state.update_environment(
            environment_changes=operation.environment_changes, reason=operation.reason
        )

    async def _apply_time_operation(
        self, world_state: WorldState, operation: TimeOperation
    ) -> None:
        """
        Apply time operation to the world state.

        Args:
            world_state: World state aggregate to modify
            operation: Time operation to apply
        """
        world_state.advance_time(new_time=operation.new_time, reason=operation.reason)

    async def _apply_snapshot_operation(
        self, world_state: WorldState, operation: SnapshotOperation
    ) -> None:
        """
        Apply snapshot operation to the world state.

        Args:
            world_state: World state aggregate to modify
            operation: Snapshot operation to apply
        """
        world_state.create_snapshot(reason=operation.reason)

    async def _apply_reset_operation(
        self, world_state: WorldState, operation: ResetOperation
    ) -> None:
        """
        Apply reset operation to the world state.

        Args:
            world_state: World state aggregate to modify
            operation: Reset operation to apply
        """
        world_state.reset_state(
            reason=operation.reason, preserve_entities=operation.preserve_entities
        )

    async def retry_with_latest_version(
        self, command: ApplyWorldDelta, max_retries: int = 3
    ) -> UpdateWorldStateResult:
        """
        Retry command execution with the latest version in case of concurrency conflicts.

        Args:
            command: Command to retry
            max_retries: Maximum number of retry attempts

        Returns:
            UpdateWorldStateResult with the outcome
        """
        for attempt in range(max_retries + 1):
            # Get the latest version of the world state
            world_state = await self.world_repository.get_by_id(command.world_state_id)
            if not world_state:
                return UpdateWorldStateResult(
                    success=False,
                    error_message=f"World state {command.world_state_id} not found",
                )

            # Update command with latest version
            command.expected_world_version = world_state.version

            result = await self.execute(command)

            # If successful or not a concurrency issue, return result
            if result.success or "Concurrency conflict" not in (result.error_message or ""):
                if attempt > 0:
                    logger.info(f"Command succeeded after {attempt} retries")
                return result

            # If this was the last attempt, return the failed result
            if attempt == max_retries:
                logger.warning(
                    f"Command failed after {max_retries} retries due to concurrency conflicts"
                )
                return result

            logger.info(
                f"Retrying command due to concurrency conflict (attempt {attempt + 1}/{max_retries})"
            )

        # This should never be reached, but included for completeness
        return UpdateWorldStateResult(
            success=False, error_message="Maximum retry attempts exceeded"
        )
