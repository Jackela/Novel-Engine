#!/usr/bin/env python3
"""
Subjective Context Commands

This module implements command objects for the Subjective bounded context.
Commands represent requests to perform operations on the subjective domain
and are handled by command handlers in the application layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ...domain.value_objects.awareness import (
    AlertnessLevel,
    AttentionFocus,
    AwarenessModifier,
)
from ...domain.value_objects.knowledge_level import (
    KnowledgeItem,
)
from ...domain.value_objects.perception_range import (
    PerceptionCapabilities,
    PerceptionType,
)


@dataclass(frozen=True)
class SubjectiveCommand(ABC):
    """
    Base class for all Subjective context commands.

    Commands are immutable data transfer objects that represent
    requests to perform operations in the subjective domain.
    """

    @abstractmethod
    def validate(self) -> None:
        """
        Validate the command parameters.

        Raises:
            ValueError: If the command is invalid
        """
        pass


@dataclass(frozen=True)
class CreateTurnBriefCommand(SubjectiveCommand):
    """
    Command to create a new TurnBrief for an entity.

    This represents a request to establish subjective perception
    and knowledge tracking for an entity.
    """

    entity_id: str
    perception_capabilities: PerceptionCapabilities
    world_state_version: int
    initial_alertness: AlertnessLevel = AlertnessLevel.RELAXED
    initial_position: Optional[Tuple[float, float, float]] = None

    def validate(self) -> None:
        """Validate the create TurnBrief command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if self.world_state_version < 0:
            raise ValueError("World state version cannot be negative")

        if not isinstance(self.perception_capabilities, PerceptionCapabilities):
            raise ValueError("Perception capabilities must be a PerceptionCapabilities object")

        if not isinstance(self.initial_alertness, AlertnessLevel):
            raise ValueError("Initial alertness must be an AlertnessLevel")

        if self.initial_position and len(self.initial_position) != 3:
            raise ValueError("Initial position must be a 3-tuple (x, y, z)")


@dataclass(frozen=True)
class UpdatePerceptionCapabilitiesCommand(SubjectiveCommand):
    """
    Command to update an entity's perception capabilities.

    This might be used when equipment changes, magical effects
    are applied, or injuries affect perception.
    """

    entity_id: str
    new_perception_capabilities: PerceptionCapabilities
    change_reason: str

    def validate(self) -> None:
        """Validate the update perception capabilities command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not isinstance(self.new_perception_capabilities, PerceptionCapabilities):
            raise ValueError("New perception capabilities must be a PerceptionCapabilities object")

        if not self.change_reason or not self.change_reason.strip():
            raise ValueError("Change reason cannot be empty")


@dataclass(frozen=True)
class UpdateAwarenessStateCommand(SubjectiveCommand):
    """
    Command to update an entity's awareness state.

    This includes changes to alertness level, attention focus,
    fatigue, stress, and awareness modifiers.
    """

    entity_id: str
    new_alertness: Optional[AlertnessLevel] = None
    new_attention_focus: Optional[AttentionFocus] = None
    new_focus_target: Optional[str] = None
    fatigue_level: Optional[float] = None
    stress_level: Optional[float] = None
    awareness_modifiers: Optional[Dict[AwarenessModifier, float]] = None

    def validate(self) -> None:
        """Validate the update awareness state command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        # At least one field must be specified
        if not any(
            [
                self.new_alertness is not None,
                self.new_attention_focus is not None,
                self.new_focus_target is not None,
                self.fatigue_level is not None,
                self.stress_level is not None,
                self.awareness_modifiers is not None,
            ]
        ):
            raise ValueError("At least one awareness parameter must be specified")

        if self.fatigue_level is not None and not 0.0 <= self.fatigue_level <= 1.0:
            raise ValueError("Fatigue level must be between 0.0 and 1.0")

        if self.stress_level is not None and not 0.0 <= self.stress_level <= 1.0:
            raise ValueError("Stress level must be between 0.0 and 1.0")

        if self.new_attention_focus == AttentionFocus.TARGET_SPECIFIC and not self.new_focus_target:
            raise ValueError("Target-specific focus requires a focus target")


@dataclass(frozen=True)
class AddPerceptionCommand(SubjectiveCommand):
    """
    Command to add a new perception to an entity's TurnBrief.

    This represents sensory input that the entity has received
    about their environment.
    """

    entity_id: str
    perceived_subject: str
    perception_type: PerceptionType
    distance: float
    environmental_conditions: Dict[str, Any]
    additional_details: Optional[Dict[str, Any]] = None
    observer_position: Optional[Tuple[float, float, float]] = None
    target_position: Optional[Tuple[float, float, float]] = None

    def validate(self) -> None:
        """Validate the add perception command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not self.perceived_subject or not self.perceived_subject.strip():
            raise ValueError("Perceived subject cannot be empty")

        if not isinstance(self.perception_type, PerceptionType):
            raise ValueError("Perception type must be a PerceptionType")

        if self.distance < 0:
            raise ValueError("Distance cannot be negative")

        if not isinstance(self.environmental_conditions, dict):
            raise ValueError("Environmental conditions must be a dictionary")

        if self.observer_position and len(self.observer_position) != 3:
            raise ValueError("Observer position must be a 3-tuple (x, y, z)")

        if self.target_position and len(self.target_position) != 3:
            raise ValueError("Target position must be a 3-tuple (x, y, z)")


@dataclass(frozen=True)
class RevealKnowledgeCommand(SubjectiveCommand):
    """
    Command to reveal new knowledge to an entity.

    This can happen through observation, communication, deduction,
    or other means of information acquisition.
    """

    entity_id: str
    knowledge_item: KnowledgeItem
    revelation_method: str

    def validate(self) -> None:
        """Validate the reveal knowledge command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not isinstance(self.knowledge_item, KnowledgeItem):
            raise ValueError("Knowledge item must be a KnowledgeItem object")

        if not self.revelation_method or not self.revelation_method.strip():
            raise ValueError("Revelation method cannot be empty")


@dataclass(frozen=True)
class UpdateKnowledgeCommand(SubjectiveCommand):
    """
    Command to update existing knowledge with new information.

    This represents refinement or correction of previously
    held beliefs or information.
    """

    entity_id: str
    subject: str
    updated_knowledge_item: KnowledgeItem
    update_reason: str

    def validate(self) -> None:
        """Validate the update knowledge command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not self.subject or not self.subject.strip():
            raise ValueError("Subject cannot be empty")

        if not isinstance(self.updated_knowledge_item, KnowledgeItem):
            raise ValueError("Updated knowledge item must be a KnowledgeItem object")

        if self.updated_knowledge_item.subject != self.subject:
            raise ValueError("Knowledge item subject must match command subject")

        if not self.update_reason or not self.update_reason.strip():
            raise ValueError("Update reason cannot be empty")


@dataclass(frozen=True)
class DetectThreatCommand(SubjectiveCommand):
    """
    Command to detect and track a threat.

    This represents the identification of something potentially
    dangerous in the entity's environment.
    """

    entity_id: str
    threat_subject: str
    threat_type: str
    threat_level: str
    confidence: float
    detection_method: PerceptionType
    estimated_distance: Optional[float] = None
    threat_capabilities: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        """Validate the detect threat command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not self.threat_subject or not self.threat_subject.strip():
            raise ValueError("Threat subject cannot be empty")

        if not self.threat_type or not self.threat_type.strip():
            raise ValueError("Threat type cannot be empty")

        if self.threat_level not in ["low", "medium", "high", "critical"]:
            raise ValueError("Threat level must be 'low', 'medium', 'high', or 'critical'")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        if not isinstance(self.detection_method, PerceptionType):
            raise ValueError("Detection method must be a PerceptionType")

        if self.estimated_distance is not None and self.estimated_distance < 0:
            raise ValueError("Estimated distance cannot be negative")


@dataclass(frozen=True)
class LoseThreatTrackingCommand(SubjectiveCommand):
    """
    Command to mark a threat as lost/no longer tracked.

    This might happen when a threat moves out of range,
    uses stealth, or the observer is distracted.
    """

    entity_id: str
    threat_subject: str
    loss_reason: str = "unknown"

    def validate(self) -> None:
        """Validate the lose threat tracking command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not self.threat_subject or not self.threat_subject.strip():
            raise ValueError("Threat subject cannot be empty")

        if not self.loss_reason or not self.loss_reason.strip():
            raise ValueError("Loss reason cannot be empty")


@dataclass(frozen=True)
class UpdateFogOfWarCommand(SubjectiveCommand):
    """
    Command to update the fog of war state for an entity.

    This represents changes in what areas or subjects are
    visible or known to the entity.
    """

    entity_id: str
    world_positions: Dict[str, Tuple[float, float, float]]
    environmental_conditions: Dict[str, Any]
    update_reason: str = "world_state_change"

    def validate(self) -> None:
        """Validate the update fog of war command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not isinstance(self.world_positions, dict):
            raise ValueError("World positions must be a dictionary")

        # Validate positions
        for subject_id, position in self.world_positions.items():
            if not isinstance(subject_id, str) or not subject_id.strip():
                raise ValueError("Subject IDs must be non-empty strings")

            if not isinstance(position, (tuple, list)) or len(position) != 3:
                raise ValueError(f"Position for {subject_id} must be a 3-tuple (x, y, z)")

            try:
                float(position[0]), float(position[1]), float(position[2])
            except (ValueError, TypeError):
                raise ValueError(f"Position coordinates for {subject_id} must be numeric")

        if not isinstance(self.environmental_conditions, dict):
            raise ValueError("Environmental conditions must be a dictionary")

        if not self.update_reason or not self.update_reason.strip():
            raise ValueError("Update reason cannot be empty")


@dataclass(frozen=True)
class ShareInformationCommand(SubjectiveCommand):
    """
    Command to share information between entities.

    This represents communication of knowledge from one
    entity to others.
    """

    source_entity_id: str
    target_entity_ids: List[str]
    knowledge_items: List[KnowledgeItem]
    communication_method: str
    reliability_modifier: float = 0.9
    max_sharing_distance: float = 10.0

    def validate(self) -> None:
        """Validate the share information command."""
        if not self.source_entity_id or not self.source_entity_id.strip():
            raise ValueError("Source entity ID cannot be empty")

        if not self.target_entity_ids:
            raise ValueError("Target entity IDs list cannot be empty")

        for target_id in self.target_entity_ids:
            if not target_id or not target_id.strip():
                raise ValueError("Target entity IDs cannot be empty")

        if not self.knowledge_items:
            raise ValueError("Knowledge items list cannot be empty")

        for item in self.knowledge_items:
            if not isinstance(item, KnowledgeItem):
                raise ValueError("All knowledge items must be KnowledgeItem objects")

        if not self.communication_method or not self.communication_method.strip():
            raise ValueError("Communication method cannot be empty")

        if not 0.0 <= self.reliability_modifier <= 1.0:
            raise ValueError("Reliability modifier must be between 0.0 and 1.0")

        if self.max_sharing_distance <= 0:
            raise ValueError("Max sharing distance must be positive")


@dataclass(frozen=True)
class UpdateWorldStateVersionCommand(SubjectiveCommand):
    """
    Command to update TurnBriefs to a new world state version.

    This ensures that all subjective views are synchronized
    with the current state of the world.
    """

    entity_ids: List[str]
    new_world_state_version: int

    def validate(self) -> None:
        """Validate the update world state version command."""
        if not self.entity_ids:
            raise ValueError("Entity IDs list cannot be empty")

        for entity_id in self.entity_ids:
            if not entity_id or not entity_id.strip():
                raise ValueError("Entity IDs cannot be empty")

        if self.new_world_state_version < 0:
            raise ValueError("World state version cannot be negative")


@dataclass(frozen=True)
class CleanupStaleKnowledgeCommand(SubjectiveCommand):
    """
    Command to clean up stale or expired knowledge.

    This removes outdated information that is no longer
    reliable for decision-making.
    """

    entity_id: str
    staleness_threshold_hours: float = 24.0
    min_reliability_threshold: float = 0.1

    def validate(self) -> None:
        """Validate the cleanup stale knowledge command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if self.staleness_threshold_hours <= 0:
            raise ValueError("Staleness threshold must be positive")

        if not 0.0 <= self.min_reliability_threshold <= 1.0:
            raise ValueError("Min reliability threshold must be between 0.0 and 1.0")


@dataclass(frozen=True)
class DeleteTurnBriefCommand(SubjectiveCommand):
    """
    Command to delete a TurnBrief.

    This removes all subjective state for an entity,
    typically when the entity is removed from the game.
    """

    entity_id: str
    deletion_reason: str = "entity_removed"

    def validate(self) -> None:
        """Validate the delete TurnBrief command."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if not self.deletion_reason or not self.deletion_reason.strip():
            raise ValueError("Deletion reason cannot be empty")
