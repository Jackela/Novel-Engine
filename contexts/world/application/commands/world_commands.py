#!/usr/bin/env python3
"""
World Context Commands

This module contains command classes that represent intentions to change
the world state. Commands are used in the CQRS pattern to encapsulate
write operations with proper validation and authorization.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ...domain.aggregates.world_state import EntityType
from ...domain.value_objects.coordinates import Coordinates


class WorldOperationType(Enum):
    """Types of operations that can be performed on the world state."""

    ADD_ENTITY = "add_entity"
    REMOVE_ENTITY = "remove_entity"
    UPDATE_ENTITY = "update_entity"
    MOVE_ENTITY = "move_entity"
    UPDATE_ENVIRONMENT = "update_environment"
    ADVANCE_TIME = "advance_time"
    CREATE_SNAPSHOT = "create_snapshot"
    RESET_STATE = "reset_state"


@dataclass
class EntityOperation:
    """
    Represents an operation to be performed on an entity within the world.

    This encapsulates the data needed to perform entity-related operations
    like adding, removing, updating, or moving entities.
    """

    operation_type: WorldOperationType
    entity_id: Optional[str] = None
    entity_type: Optional[EntityType] = None
    entity_name: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    new_coordinates: Optional[Coordinates] = None
    properties: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None

    def __post_init__(self):
        """Validate entity operation data."""
        if self.operation_type == WorldOperationType.ADD_ENTITY:
            if not all([self.entity_id, self.entity_type, self.entity_name, self.coordinates]):
                raise ValueError(
                    "ADD_ENTITY requires entity_id, entity_type, entity_name, and coordinates"
                )

        elif self.operation_type == WorldOperationType.REMOVE_ENTITY:
            if not self.entity_id:
                raise ValueError("REMOVE_ENTITY requires entity_id")

        elif self.operation_type == WorldOperationType.UPDATE_ENTITY:
            if not self.entity_id:
                raise ValueError("UPDATE_ENTITY requires entity_id")
            if not (self.properties or self.metadata):
                raise ValueError("UPDATE_ENTITY requires properties or metadata to update")

        elif self.operation_type == WorldOperationType.MOVE_ENTITY:
            if not all([self.entity_id, self.new_coordinates]):
                raise ValueError("MOVE_ENTITY requires entity_id and new_coordinates")


@dataclass
class EnvironmentOperation:
    """
    Represents an operation to change the world environment.

    This encapsulates environment-related changes such as weather,
    lighting, or other global environmental properties.
    """

    environment_changes: Dict[str, Any]
    affected_area: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None

    def __post_init__(self):
        """Validate environment operation data."""
        if not self.environment_changes:
            raise ValueError("Environment operation requires environment_changes")


@dataclass
class TimeOperation:
    """
    Represents an operation to advance world time.

    This encapsulates time advancement operations with proper validation
    to ensure time only moves forward.
    """

    new_time: datetime
    reason: Optional[str] = None

    def __post_init__(self):
        """Validate time operation data."""
        if self.new_time <= datetime.now():
            raise ValueError("New time must be in the future for realistic world simulation")


@dataclass
class SnapshotOperation:
    """
    Represents an operation to create a world state snapshot.

    This encapsulates snapshot creation with proper reason tracking
    for audit and recovery purposes.
    """

    reason: str
    include_entities: bool = True
    include_environment: bool = True
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate snapshot operation data."""
        if not self.reason or not self.reason.strip():
            raise ValueError("Snapshot operation requires a valid reason")


@dataclass
class ResetOperation:
    """
    Represents an operation to reset the world state.

    This encapsulates world state reset operations with options
    for preserving certain aspects of the world.
    """

    reason: str
    preserve_entities: bool = False
    preserve_environment: bool = False
    create_backup: bool = True

    def __post_init__(self):
        """Validate reset operation data."""
        if not self.reason or not self.reason.strip():
            raise ValueError("Reset operation requires a valid reason")


@dataclass
class ApplyWorldDelta:
    """
    Command to apply a set of changes (delta) to a world state.

    This command encapsulates all the changes that need to be applied
    to a world state in a single atomic operation. It supports multiple
    types of operations including entity changes, environment updates,
    time advancement, and administrative operations.

    Following CQRS principles, this command:
    - Represents an intention to change state
    - Contains all data needed for the operation
    - Is validated before execution
    - Can be serialized for auditing
    - Supports idempotency through correlation_id

    Attributes:
        command_id: Unique identifier for this command
        world_state_id: ID of the world state to modify
        entity_operations: List of entity-related operations
        environment_operation: Optional environment change operation
        time_operation: Optional time advancement operation
        snapshot_operation: Optional snapshot creation operation
        reset_operation: Optional state reset operation
        batch_id: Optional ID for grouping related commands
        user_id: ID of the user initiating the command
        source: Source system or component issuing the command
        correlation_id: ID for tracking related operations
        reason: Overall reason for applying this delta
        metadata: Additional metadata for the command
        priority: Execution priority for the command
        timeout_seconds: Maximum time to wait for execution
    """

    # Core identifiers
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    world_state_id: str = ""

    # Operation specifications
    entity_operations: List[EntityOperation] = field(default_factory=list)
    environment_operation: Optional[EnvironmentOperation] = None
    time_operation: Optional[TimeOperation] = None
    snapshot_operation: Optional[SnapshotOperation] = None
    reset_operation: Optional[ResetOperation] = None

    # Grouping and tracking
    batch_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "world_application_service"
    correlation_id: Optional[str] = None

    # Documentation and metadata
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Execution parameters
    priority: str = "normal"  # low, normal, high, critical
    timeout_seconds: int = 30
    timestamp: datetime = field(default_factory=datetime.now)

    # Idempotency and versioning
    idempotency_key: Optional[str] = None
    expected_world_version: Optional[int] = None

    def __post_init__(self):
        """Validate the command after initialization."""
        self._validate_command()

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())

        # Generate idempotency key if not provided
        if not self.idempotency_key:
            self.idempotency_key = f"world_delta_{self.world_state_id}_{self.correlation_id}"

    def _validate_command(self) -> None:
        """
        Validate the command structure and data.

        Raises:
            ValueError: If command data is invalid
        """
        errors = []

        # Validate required fields
        if not self.world_state_id:
            errors.append("world_state_id is required")

        if not self.reason or not self.reason.strip():
            errors.append("reason is required for world state changes")

        # Validate that at least one operation is specified
        has_operations = any(
            [
                self.entity_operations,
                self.environment_operation,
                self.time_operation,
                self.snapshot_operation,
                self.reset_operation,
            ]
        )

        if not has_operations:
            errors.append("At least one operation must be specified")

        # Validate operation combinations
        if self.reset_operation and (self.entity_operations or self.environment_operation):
            errors.append(
                "Reset operation cannot be combined with entity or environment operations"
            )

        # Validate priority
        if self.priority not in ["low", "normal", "high", "critical"]:
            errors.append("priority must be one of: low, normal, high, critical")

        # Validate timeout
        if self.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")

        if errors:
            raise ValueError(f"ApplyWorldDelta validation failed: {'; '.join(errors)}")

    def add_entity_operation(self, operation: EntityOperation) -> None:
        """
        Add an entity operation to this command.

        Args:
            operation: EntityOperation to add
        """
        self.entity_operations.append(operation)

    def has_entity_operations(self) -> bool:
        """Check if this command has any entity operations."""
        return len(self.entity_operations) > 0

    def has_environment_operation(self) -> bool:
        """Check if this command has an environment operation."""
        return self.environment_operation is not None

    def has_time_operation(self) -> bool:
        """Check if this command has a time operation."""
        return self.time_operation is not None

    def has_administrative_operations(self) -> bool:
        """Check if this command has administrative operations (snapshot/reset)."""
        return self.snapshot_operation is not None or self.reset_operation is not None

    def get_operation_count(self) -> int:
        """Get the total number of operations in this command."""
        count = len(self.entity_operations)
        if self.environment_operation:
            count += 1
        if self.time_operation:
            count += 1
        if self.snapshot_operation:
            count += 1
        if self.reset_operation:
            count += 1
        return count

    def get_operation_summary(self) -> str:
        """Get a human-readable summary of operations in this command."""
        summary_parts = []

        if self.entity_operations:
            entity_counts = {}
            for op in self.entity_operations:
                op_type = op.operation_type.value
                entity_counts[op_type] = entity_counts.get(op_type, 0) + 1

            for op_type, count in entity_counts.items():
                summary_parts.append(f"{count} {op_type} operation{'s' if count > 1 else ''}")

        if self.environment_operation:
            summary_parts.append("environment update")

        if self.time_operation:
            summary_parts.append("time advancement")

        if self.snapshot_operation:
            summary_parts.append("snapshot creation")

        if self.reset_operation:
            summary_parts.append("state reset")

        if not summary_parts:
            return "no operations"

        return ", ".join(summary_parts)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert command to dictionary representation for serialization.

        Returns:
            Dictionary representation of the command
        """
        return {
            "command_id": self.command_id,
            "world_state_id": self.world_state_id,
            "entity_operations": [
                {
                    "operation_type": op.operation_type.value,
                    "entity_id": op.entity_id,
                    "entity_type": op.entity_type.value if op.entity_type else None,
                    "entity_name": op.entity_name,
                    "coordinates": op.coordinates.to_dict() if op.coordinates else None,
                    "new_coordinates": (
                        op.new_coordinates.to_dict() if op.new_coordinates else None
                    ),
                    "properties": op.properties,
                    "metadata": op.metadata,
                    "reason": op.reason,
                }
                for op in self.entity_operations
            ],
            "environment_operation": (
                {
                    "environment_changes": self.environment_operation.environment_changes,
                    "affected_area": self.environment_operation.affected_area,
                    "reason": self.environment_operation.reason,
                }
                if self.environment_operation
                else None
            ),
            "time_operation": (
                {
                    "new_time": self.time_operation.new_time.isoformat(),
                    "reason": self.time_operation.reason,
                }
                if self.time_operation
                else None
            ),
            "snapshot_operation": (
                {
                    "reason": self.snapshot_operation.reason,
                    "include_entities": self.snapshot_operation.include_entities,
                    "include_environment": self.snapshot_operation.include_environment,
                    "metadata": self.snapshot_operation.metadata,
                }
                if self.snapshot_operation
                else None
            ),
            "reset_operation": (
                {
                    "reason": self.reset_operation.reason,
                    "preserve_entities": self.reset_operation.preserve_entities,
                    "preserve_environment": self.reset_operation.preserve_environment,
                    "create_backup": self.reset_operation.create_backup,
                }
                if self.reset_operation
                else None
            ),
            "batch_id": self.batch_id,
            "user_id": self.user_id,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "reason": self.reason,
            "metadata": self.metadata,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "timestamp": self.timestamp.isoformat(),
            "idempotency_key": self.idempotency_key,
            "expected_world_version": self.expected_world_version,
            "operation_count": self.get_operation_count(),
            "operation_summary": self.get_operation_summary(),
        }

    @classmethod
    def create_entity_addition(
        cls,
        world_state_id: str,
        entity_id: str,
        entity_type: EntityType,
        entity_name: str,
        coordinates: Coordinates,
        reason: str,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> "ApplyWorldDelta":
        """
        Factory method to create a command for adding an entity.

        Args:
            world_state_id: ID of the world state
            entity_id: ID of the entity to add
            entity_type: Type of the entity
            entity_name: Name of the entity
            coordinates: Position of the entity
            reason: Reason for adding the entity
            properties: Optional entity properties
            metadata: Optional entity metadata
            user_id: Optional user ID

        Returns:
            ApplyWorldDelta command configured for entity addition
        """
        entity_op = EntityOperation(
            operation_type=WorldOperationType.ADD_ENTITY,
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            coordinates=coordinates,
            properties=properties,
            metadata=metadata,
            reason=reason,
        )

        return cls(
            world_state_id=world_state_id,
            entity_operations=[entity_op],
            reason=reason,
            user_id=user_id,
        )

    @classmethod
    def create_entity_removal(
        cls,
        world_state_id: str,
        entity_id: str,
        reason: str,
        user_id: Optional[str] = None,
    ) -> "ApplyWorldDelta":
        """
        Factory method to create a command for removing an entity.

        Args:
            world_state_id: ID of the world state
            entity_id: ID of the entity to remove
            reason: Reason for removing the entity
            user_id: Optional user ID

        Returns:
            ApplyWorldDelta command configured for entity removal
        """
        entity_op = EntityOperation(
            operation_type=WorldOperationType.REMOVE_ENTITY,
            entity_id=entity_id,
            reason=reason,
        )

        return cls(
            world_state_id=world_state_id,
            entity_operations=[entity_op],
            reason=reason,
            user_id=user_id,
        )

    @classmethod
    def create_environment_update(
        cls,
        world_state_id: str,
        environment_changes: Dict[str, Any],
        reason: str,
        user_id: Optional[str] = None,
        affected_area: Optional[Dict[str, Any]] = None,
    ) -> "ApplyWorldDelta":
        """
        Factory method to create a command for updating the environment.

        Args:
            world_state_id: ID of the world state
            environment_changes: Changes to apply to the environment
            reason: Reason for the environment update
            user_id: Optional user ID
            affected_area: Optional spatial area affected

        Returns:
            ApplyWorldDelta command configured for environment update
        """
        env_op = EnvironmentOperation(
            environment_changes=environment_changes,
            affected_area=affected_area,
            reason=reason,
        )

        return cls(
            world_state_id=world_state_id,
            environment_operation=env_op,
            reason=reason,
            user_id=user_id,
        )

    def __str__(self) -> str:
        """String representation of the command."""
        return f"ApplyWorldDelta(id={self.command_id[:8]}, world={self.world_state_id[:8]}, ops={self.get_operation_count()})"

    def __repr__(self) -> str:
        """Detailed string representation of the command."""
        return (
            f"ApplyWorldDelta(command_id={self.command_id}, "
            f"world_state_id={self.world_state_id}, "
            f"operations={self.get_operation_summary()})"
        )
