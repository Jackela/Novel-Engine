#!/usr/bin/env python3
"""
TurnBrief Aggregate Root

This module implements the TurnBrief aggregate root, which represents
an entity's subjective perception and knowledge of the game world at
a specific point in time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..events.subjective_events import (
    AlertnessChanged,
    AttentionFocusChanged,
    FogOfWarUpdated,
    KnowledgeRevealed,
    KnowledgeUpdated,
    NewPerceptionAcquired,
    PerceptionRangeUpdated,
    SubjectiveDomainEvent,
    ThreatDetected,
    ThreatLost,
    TurnBriefCreated,
    TurnBriefUpdated,
)
from ..value_objects.awareness import (
    AlertnessLevel,
    AttentionFocus,
    AwarenessState,
)
from ..value_objects.knowledge_level import (
    CertaintyLevel,
    KnowledgeBase,
    KnowledgeItem,
)
from ..value_objects.perception_range import (
    PerceptionCapabilities,
    PerceptionType,
    VisibilityLevel,
)
from ..value_objects.subjective_id import SubjectiveId


@dataclass
class TurnBrief:
    """
    TurnBrief Aggregate Root

    The TurnBrief represents an entity's subjective view of the game world,
    including their perception capabilities, current knowledge, awareness state,
    and the fog of war from their perspective.

    This aggregate enforces business rules around perception, knowledge
    propagation, and maintains consistency in the entity's subjective reality.
    """

    # Aggregate identity
    turn_brief_id: SubjectiveId
    entity_id: str  # The entity this TurnBrief belongs to

    # World state tracking
    world_state_version: int
    last_world_update: datetime

    # Perception capabilities and current state
    perception_capabilities: PerceptionCapabilities
    awareness_state: AwarenessState

    # Knowledge and information
    knowledge_base: KnowledgeBase
    visible_subjects: Dict[str, VisibilityLevel]  # What can currently be seen
    known_threats: Dict[str, Dict[str, Any]]  # Tracked threats with metadata

    # Temporal state
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_perception_update: datetime = field(default_factory=datetime.now)
    version: int = field(default=1)

    # Domain events (not persisted)
    _events: List[SubjectiveDomainEvent] = field(default_factory=list, init=False)

    def __post_init__(self):
        """Validate TurnBrief state after initialization."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("Entity ID cannot be empty")

        if self.world_state_version < 0:
            raise ValueError("World state version cannot be negative")

        if self.version < 1:
            raise ValueError("Version must be at least 1")

        # Validate temporal consistency
        if self.updated_at < self.created_at:
            raise ValueError("Updated time cannot be before creation time")

        if self.last_world_update < self.created_at:
            raise ValueError("Last world update cannot be before creation time")

    @classmethod
    def create_for_entity(
        cls,
        entity_id: str,
        perception_capabilities: PerceptionCapabilities,
        world_state_version: int,
        initial_alertness: AlertnessLevel = AlertnessLevel.RELAXED,
    ) -> "TurnBrief":
        """
        Create a new TurnBrief for an entity.

        Args:
            entity_id: The ID of the entity
            perception_capabilities: The entity's perception capabilities
            world_state_version: The current world state version
            initial_alertness: The entity's initial alertness level

        Returns:
            A new TurnBrief instance
        """
        turn_brief_id = SubjectiveId.generate()
        now = datetime.now()

        # Create initial awareness state
        awareness_state = AwarenessState(
            base_alertness=initial_alertness,
            current_alertness=initial_alertness,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={},
            fatigue_level=0.0,
            stress_level=0.0,
        )

        # Create empty knowledge base
        knowledge_base = KnowledgeBase(knowledge_items={})

        turn_brief = cls(
            turn_brief_id=turn_brief_id,
            entity_id=entity_id,
            world_state_version=world_state_version,
            last_world_update=now,
            perception_capabilities=perception_capabilities,
            awareness_state=awareness_state,
            knowledge_base=knowledge_base,
            visible_subjects={},
            known_threats={},
            created_at=now,
            updated_at=now,
            last_perception_update=now,
        )

        # Raise creation event
        event = TurnBriefCreated(
            event_id=str(uuid4()),
            occurred_at=now,
            entity_id=entity_id,
            turn_brief_id=turn_brief_id,
            world_state_version=world_state_version,
            initial_alertness=initial_alertness,
        )
        turn_brief._add_event(event)

        return turn_brief

    def update_perception_capabilities(
        self, new_capabilities: PerceptionCapabilities, change_reason: str
    ) -> None:
        """
        Update the entity's perception capabilities.

        Args:
            new_capabilities: The new perception capabilities
            change_reason: Reason for the change
        """
        old_capabilities = self.perception_capabilities
        self.perception_capabilities = new_capabilities
        self.updated_at = datetime.now()
        self.version += 1

        # Check for changes and raise events
        for perception_type in PerceptionType:
            old_range = old_capabilities.perception_ranges.get(perception_type)
            new_range = new_capabilities.perception_ranges.get(perception_type)

            if old_range != new_range:
                if old_range and new_range:
                    # Range updated
                    event = PerceptionRangeUpdated(
                        event_id=str(uuid4()),
                        occurred_at=self.updated_at,
                        entity_id=self.entity_id,
                        turn_brief_id=self.turn_brief_id,
                        perception_type=perception_type,
                        old_range=old_range.effective_range,
                        new_range=new_range.effective_range,
                        old_accuracy=old_range.accuracy_modifier,
                        new_accuracy=new_range.accuracy_modifier,
                        change_reason=change_reason,
                    )
                    self._add_event(event)

        self._add_update_event("perception_capabilities", [change_reason])

    def update_awareness_state(self, new_awareness: AwarenessState) -> None:
        """
        Update the entity's awareness state.

        Args:
            new_awareness: The new awareness state
        """
        old_awareness = self.awareness_state
        old_alertness = old_awareness.current_alertness
        old_focus = old_awareness.attention_focus
        old_target = old_awareness.focus_target

        self.awareness_state = new_awareness
        self.updated_at = datetime.now()
        self.version += 1

        # Raise alertness change event if needed
        if old_alertness != new_awareness.current_alertness:
            event = AlertnessChanged(
                event_id=str(uuid4()),
                occurred_at=self.updated_at,
                entity_id=self.entity_id,
                turn_brief_id=self.turn_brief_id,
                old_alertness=old_alertness,
                new_alertness=new_awareness.current_alertness,
                change_trigger="awareness_update",
            )
            self._add_event(event)

        # Raise attention focus change event if needed
        if (
            old_focus != new_awareness.attention_focus
            or old_target != new_awareness.focus_target
        ):
            event = AttentionFocusChanged(
                event_id=str(uuid4()),
                occurred_at=self.updated_at,
                entity_id=self.entity_id,
                turn_brief_id=self.turn_brief_id,
                old_focus=old_focus,
                new_focus=new_awareness.attention_focus,
                old_target=old_target,
                new_target=new_awareness.focus_target,
                focus_reason="awareness_update",
            )
            self._add_event(event)

        self._add_update_event("awareness_state", ["alertness_change", "focus_change"])

    def add_perception(
        self,
        subject: str,
        perception_type: PerceptionType,
        visibility_level: VisibilityLevel,
        distance: float,
        additional_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a new perception to the TurnBrief.

        Args:
            subject: What was perceived
            perception_type: How it was perceived
            visibility_level: How clearly it was seen
            distance: Distance to the perceived subject
            additional_details: Additional perception details
        """
        # Update visible subjects
        current_visibility = self.visible_subjects.get(
            subject, VisibilityLevel.INVISIBLE
        )

        # Choose the best visibility level
        visibility_order = [
            VisibilityLevel.CLEAR,
            VisibilityLevel.PARTIAL,
            VisibilityLevel.OBSCURED,
            VisibilityLevel.HIDDEN,
            VisibilityLevel.INVISIBLE,
        ]

        if visibility_order.index(visibility_level) < visibility_order.index(
            current_visibility
        ):
            self.visible_subjects[subject] = visibility_level

        self.last_perception_update = datetime.now()
        self.updated_at = self.last_perception_update
        self.version += 1

        # Raise perception event
        event = NewPerceptionAcquired(
            event_id=str(uuid4()),
            occurred_at=self.updated_at,
            entity_id=self.entity_id,
            turn_brief_id=self.turn_brief_id,
            perceived_subject=subject,
            perception_type=perception_type,
            visibility_level=visibility_level,
            distance=distance,
            additional_details=additional_details or {},
        )
        self._add_event(event)

        self._add_update_event("perception", [subject])

    def add_knowledge(
        self, knowledge_item: KnowledgeItem, revelation_method: str
    ) -> None:
        """
        Add new knowledge to the TurnBrief.

        Args:
            knowledge_item: The knowledge to add
            revelation_method: How the knowledge was acquired
        """
        existing_knowledge = self.knowledge_base.get_most_reliable_knowledge(
            knowledge_item.subject
        )

        # Update knowledge base
        self.knowledge_base = self.knowledge_base.add_knowledge(knowledge_item)
        self.updated_at = datetime.now()
        self.version += 1

        # Determine if this is new knowledge or an update
        if existing_knowledge:
            # This is an update to existing knowledge
            event = KnowledgeUpdated(
                event_id=str(uuid4()),
                occurred_at=self.updated_at,
                entity_id=self.entity_id,
                turn_brief_id=self.turn_brief_id,
                subject=knowledge_item.subject,
                old_knowledge=existing_knowledge,
                new_knowledge=knowledge_item,
                update_reason=revelation_method,
            )
        else:
            # This is new knowledge
            event = KnowledgeRevealed(
                event_id=str(uuid4()),
                occurred_at=self.updated_at,
                entity_id=self.entity_id,
                turn_brief_id=self.turn_brief_id,
                knowledge_item=knowledge_item,
                revelation_method=revelation_method,
            )

        self._add_event(event)
        self._add_update_event("knowledge", [knowledge_item.subject])

    def detect_threat(
        self,
        threat_subject: str,
        threat_type: str,
        threat_level: str,
        confidence: float,
        detection_method: PerceptionType,
        estimated_distance: Optional[float] = None,
    ) -> None:
        """
        Detect and track a new threat.

        Args:
            threat_subject: The threatening entity/object
            threat_type: Type of threat (e.g., "hostile_entity", "environmental_hazard")
            threat_level: Severity level ("low", "medium", "high", "critical")
            confidence: Confidence in threat assessment (0.0-1.0)
            detection_method: How the threat was detected
            estimated_distance: Estimated distance to threat
        """
        threat_info = {
            "threat_type": threat_type,
            "threat_level": threat_level,
            "confidence": confidence,
            "detection_method": detection_method,
            "estimated_distance": estimated_distance,
            "first_detected": datetime.now(),
            "last_seen": datetime.now(),
            "status": "active",
        }

        self.known_threats[threat_subject] = threat_info
        self.updated_at = datetime.now()
        self.version += 1

        # Raise threat detected event
        event = ThreatDetected(
            event_id=str(uuid4()),
            occurred_at=self.updated_at,
            entity_id=self.entity_id,
            turn_brief_id=self.turn_brief_id,
            threat_subject=threat_subject,
            threat_type=threat_type,
            threat_level=threat_level,
            confidence=confidence,
            detection_method=detection_method,
            estimated_distance=estimated_distance,
        )
        self._add_event(event)

        self._add_update_event("threats", [threat_subject])

    def lose_threat_tracking(
        self, threat_subject: str, loss_reason: str = "unknown"
    ) -> None:
        """
        Mark a threat as lost/no longer tracked.

        Args:
            threat_subject: The threat that was lost
            loss_reason: Why the threat was lost
        """
        if threat_subject in self.known_threats:
            threat_info = self.known_threats[threat_subject]
            last_position = threat_info.get("last_known_position")

            # Mark threat as lost
            threat_info["status"] = "lost"
            threat_info["lost_at"] = datetime.now()
            threat_info["loss_reason"] = loss_reason

            self.updated_at = datetime.now()
            self.version += 1

            # Raise threat lost event
            event = ThreatLost(
                event_id=str(uuid4()),
                occurred_at=self.updated_at,
                entity_id=self.entity_id,
                turn_brief_id=self.turn_brief_id,
                threat_subject=threat_subject,
                last_known_position=last_position,
                loss_reason=loss_reason,
            )
            self._add_event(event)

            self._add_update_event("threats", [threat_subject])

    def update_fog_of_war(
        self,
        newly_revealed: List[str],
        newly_concealed: List[str],
        visibility_changes: Dict[str, VisibilityLevel],
        update_reason: str,
    ) -> None:
        """
        Update the fog of war state.

        Args:
            newly_revealed: Subjects that became visible
            newly_concealed: Subjects that became hidden
            visibility_changes: Changes in visibility levels
            update_reason: Reason for the update
        """
        # Apply visibility changes
        for subject, new_visibility in visibility_changes.items():
            if new_visibility == VisibilityLevel.INVISIBLE:
                self.visible_subjects.pop(subject, None)
            else:
                self.visible_subjects[subject] = new_visibility

        # Remove concealed subjects
        for subject in newly_concealed:
            self.visible_subjects.pop(subject, None)

        self.updated_at = datetime.now()
        self.version += 1

        # Raise fog of war update event
        event = FogOfWarUpdated(
            event_id=str(uuid4()),
            occurred_at=self.updated_at,
            entity_id=self.entity_id,
            turn_brief_id=self.turn_brief_id,
            newly_revealed=newly_revealed,
            newly_concealed=newly_concealed,
            visibility_changes=visibility_changes,
            update_reason=update_reason,
        )
        self._add_event(event)

        affected_subjects = list(
            set(newly_revealed + newly_concealed + list(visibility_changes.keys()))
        )
        self._add_update_event("fog_of_war", affected_subjects)

    def update_world_state_version(self, new_version: int) -> None:
        """
        Update to a new world state version.

        Args:
            new_version: The new world state version
        """
        if new_version <= self.world_state_version:
            return  # No update needed

        old_version = self.world_state_version
        self.world_state_version = new_version
        self.last_world_update = datetime.now()
        self.updated_at = self.last_world_update
        self.version += 1

        self._add_update_event(
            "world_state_version", [f"v{old_version}_to_v{new_version}"]
        )

    def can_perceive_at_distance(
        self, distance: float, perception_type: Optional[PerceptionType] = None
    ) -> VisibilityLevel:
        """
        Check what visibility level is achievable at a given distance.

        Args:
            distance: The distance to check
            perception_type: Specific perception type to use (None for best available)

        Returns:
            The best visibility level achievable at that distance
        """
        if perception_type:
            if perception_type not in self.perception_capabilities.perception_ranges:
                return VisibilityLevel.INVISIBLE
            perception_range = self.perception_capabilities.perception_ranges[
                perception_type
            ]
            return perception_range.calculate_visibility_at_distance(distance)
        else:
            # Get the best visibility from any perception type
            focused_perception = None
            if (
                self.awareness_state.attention_focus == AttentionFocus.TARGET_SPECIFIC
                and self.awareness_state.focus_target
            ):
                # If focused on a specific target, we might have enhanced perception
                focused_perception = PerceptionType.VISUAL  # Default to visual focus

            return self.perception_capabilities.get_best_visibility_at_distance(
                distance, focused_perception
            )

    def is_subject_visible(self, subject: str) -> bool:
        """
        Check if a subject is currently visible.

        Args:
            subject: The subject to check visibility for

        Returns:
            True if the subject is visible (any level except invisible)
        """
        visibility = self.visible_subjects.get(subject, VisibilityLevel.INVISIBLE)
        return visibility != VisibilityLevel.INVISIBLE

    def get_subject_visibility(self, subject: str) -> VisibilityLevel:
        """
        Get the current visibility level of a subject.

        Args:
            subject: The subject to check

        Returns:
            The visibility level of the subject
        """
        return self.visible_subjects.get(subject, VisibilityLevel.INVISIBLE)

    def has_knowledge_about(
        self, subject: str, min_certainty: CertaintyLevel = CertaintyLevel.MINIMAL
    ) -> bool:
        """
        Check if the entity has knowledge about a specific subject.

        Args:
            subject: The subject to check knowledge about
            min_certainty: Minimum certainty level required

        Returns:
            True if the entity has knowledge meeting the certainty threshold
        """
        return self.knowledge_base.has_knowledge_about(subject, min_certainty)

    def get_current_threats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all currently active threats.

        Returns:
            Dictionary of active threats with their metadata
        """
        return {
            subject: info
            for subject, info in self.known_threats.items()
            if info.get("status") == "active"
        }

    def is_alert_to_threats(self) -> bool:
        """
        Check if the entity is currently alert enough to detect threats.

        Returns:
            True if the entity can detect threats in their current state
        """
        return self.awareness_state.can_detect_stealth()

    def get_reaction_time(self) -> float:
        """
        Get the current reaction time modifier for this entity.

        Returns:
            Reaction time modifier (1.0 = normal, higher = slower)
        """
        return self.awareness_state.get_reaction_time_modifier()

    def get_events(self) -> List[SubjectiveDomainEvent]:
        """Get all domain events raised by this aggregate."""
        return list(self._events)

    def clear_events(self) -> None:
        """Clear all domain events (typically called after publishing)."""
        self._events.clear()

    def _add_event(self, event: SubjectiveDomainEvent) -> None:
        """Add a domain event to the aggregate."""
        self._events.append(event)

    def _add_update_event(
        self, update_reason: str, affected_subjects: List[str]
    ) -> None:
        """Add a generic update event."""
        event = TurnBriefUpdated(
            event_id=str(uuid4()),
            occurred_at=self.updated_at,
            entity_id=self.entity_id,
            turn_brief_id=self.turn_brief_id,
            update_reason=update_reason,
            previous_version=self.version - 1,
            new_version=self.version,
            affected_subjects=affected_subjects,
        )
        self._add_event(event)
