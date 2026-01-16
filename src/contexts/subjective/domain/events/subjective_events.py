#!/usr/bin/env python3
"""
Subjective Domain Events

This module implements domain events for the Subjective bounded context.
These events represent important state changes in perception, knowledge,
and awareness that may need to be communicated to other bounded contexts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..value_objects.awareness import AlertnessLevel, AttentionFocus
from ..value_objects.knowledge_level import KnowledgeItem
from ..value_objects.perception_range import PerceptionType, VisibilityLevel
from ..value_objects.subjective_id import SubjectiveId


@dataclass(frozen=True)
class SubjectiveDomainEvent(ABC):
    """
    Base class for all Subjective domain events.

    Domain events represent something that happened in the domain that
    other parts of the system care about.
    """

    event_id: str
    occurred_at: datetime
    entity_id: str  # The entity this event relates to

    @abstractmethod
    def get_event_type(self) -> str:
        """Return the event type identifier."""


@dataclass(frozen=True)
class TurnBriefCreated(SubjectiveDomainEvent):
    """
    Event raised when a new TurnBrief is created for an entity.

    This indicates that an entity now has a subjective view of the game state
    and can begin making perception-based decisions.
    """

    turn_brief_id: SubjectiveId
    world_state_version: int
    initial_alertness: AlertnessLevel

    def get_event_type(self) -> str:
        return "TurnBriefCreated"


@dataclass(frozen=True)
class TurnBriefUpdated(SubjectiveDomainEvent):
    """
    Event raised when a TurnBrief is updated with new information.

    This indicates that an entity's subjective view of the world has changed
    due to new perceptions or knowledge updates.
    """

    turn_brief_id: SubjectiveId
    update_reason: str
    previous_version: int
    new_version: int
    affected_subjects: List[str]  # What subjects were updated

    def get_event_type(self) -> str:
        return "TurnBriefUpdated"


@dataclass(frozen=True)
class PerceptionRangeUpdated(SubjectiveDomainEvent):
    """
    Event raised when an entity's perception capabilities change.

    This might be due to equipment changes, magical effects, injuries,
    or environmental conditions.
    """

    turn_brief_id: SubjectiveId
    perception_type: PerceptionType
    old_range: float
    new_range: float
    old_accuracy: float
    new_accuracy: float
    change_reason: str

    def get_event_type(self) -> str:
        return "PerceptionRangeUpdated"


@dataclass(frozen=True)
class NewPerceptionAcquired(SubjectiveDomainEvent):
    """
    Event raised when an entity perceives something new.

    This represents fresh sensory input that may lead to new knowledge
    or updates to existing knowledge.
    """

    turn_brief_id: SubjectiveId
    perceived_subject: str  # What was perceived
    perception_type: PerceptionType
    visibility_level: VisibilityLevel
    distance: float
    additional_details: Dict[str, Any]  # Context-specific perception data

    def get_event_type(self) -> str:
        return "NewPerceptionAcquired"


@dataclass(frozen=True)
class KnowledgeRevealed(SubjectiveDomainEvent):
    """
    Event raised when new knowledge is revealed to an entity.

    This can happen through direct observation, communication, deduction,
    or other means of information acquisition.
    """

    turn_brief_id: SubjectiveId
    knowledge_item: KnowledgeItem
    revelation_method: str  # How the knowledge was acquired
    confidence_change: Optional[
        float
    ] = None  # Change in confidence if updating existing knowledge

    def get_event_type(self) -> str:
        return "KnowledgeRevealed"


@dataclass(frozen=True)
class KnowledgeUpdated(SubjectiveDomainEvent):
    """
    Event raised when existing knowledge is updated with new information.

    This represents refinement or correction of previously held beliefs
    or information.
    """

    turn_brief_id: SubjectiveId
    subject: str
    old_knowledge: KnowledgeItem
    new_knowledge: KnowledgeItem
    update_reason: str

    def get_event_type(self) -> str:
        return "KnowledgeUpdated"


@dataclass(frozen=True)
class KnowledgeBecameStale(SubjectiveDomainEvent):
    """
    Event raised when knowledge becomes outdated or stale.

    This indicates that previously held information is no longer
    considered reliable or current.
    """

    turn_brief_id: SubjectiveId
    stale_knowledge: List[KnowledgeItem]
    reason: str  # Why the knowledge became stale

    def get_event_type(self) -> str:
        return "KnowledgeBecameStale"


@dataclass(frozen=True)
class AlertnessChanged(SubjectiveDomainEvent):
    """
    Event raised when an entity's alertness level changes.

    This affects perception capabilities and reaction times.
    """

    turn_brief_id: SubjectiveId
    old_alertness: AlertnessLevel
    new_alertness: AlertnessLevel
    change_trigger: str  # What caused the alertness change
    duration_estimate: Optional[float] = None  # How long the change might last

    def get_event_type(self) -> str:
        return "AlertnessChanged"


@dataclass(frozen=True)
class AttentionFocusChanged(SubjectiveDomainEvent):
    """
    Event raised when an entity changes their attention focus.

    This affects what they can perceive clearly and how they
    process incoming information.
    """

    turn_brief_id: SubjectiveId
    old_focus: AttentionFocus
    new_focus: AttentionFocus
    old_target: Optional[str]
    new_target: Optional[str]
    focus_reason: str

    def get_event_type(self) -> str:
        return "AttentionFocusChanged"


@dataclass(frozen=True)
class ThreatDetected(SubjectiveDomainEvent):
    """
    Event raised when an entity detects a potential threat.

    This represents the subjective assessment that something
    in the environment poses a danger.
    """

    turn_brief_id: SubjectiveId
    threat_subject: str
    threat_type: str
    threat_level: str  # "low", "medium", "high", "critical"
    confidence: float  # How confident they are about the threat
    detection_method: PerceptionType
    estimated_distance: Optional[float] = None

    def get_event_type(self) -> str:
        return "ThreatDetected"


@dataclass(frozen=True)
class ThreatLost(SubjectiveDomainEvent):
    """
    Event raised when an entity loses track of a previously detected threat.

    This might be due to the threat moving out of range, using stealth,
    or the observer being distracted.
    """

    turn_brief_id: SubjectiveId
    threat_subject: str
    last_known_position: Optional[str] = None
    loss_reason: str = "unknown"

    def get_event_type(self) -> str:
        return "ThreatLost"


@dataclass(frozen=True)
class InformationShared(SubjectiveDomainEvent):
    """
    Event raised when an entity shares information with others.

    This represents communication of knowledge between entities,
    which may affect multiple TurnBriefs.
    """

    turn_brief_id: SubjectiveId
    shared_knowledge: List[KnowledgeItem]
    target_entities: List[str]  # Who the information was shared with
    communication_method: str
    reliability_modifier: float  # How reliable others consider this source

    def get_event_type(self) -> str:
        return "InformationShared"


@dataclass(frozen=True)
class InformationReceived(SubjectiveDomainEvent):
    """
    Event raised when an entity receives information from others.

    This represents incoming communication that may update the
    entity's knowledge base.
    """

    turn_brief_id: SubjectiveId
    received_knowledge: List[KnowledgeItem]
    source_entity: str
    source_reliability: float
    communication_method: str

    def get_event_type(self) -> str:
        return "InformationReceived"


@dataclass(frozen=True)
class FogOfWarUpdated(SubjectiveDomainEvent):
    """
    Event raised when the fog of war state changes for an entity.

    This represents changes in what areas or subjects are visible
    or known to the entity.
    """

    turn_brief_id: SubjectiveId
    newly_revealed: List[str]  # Subjects that became visible
    newly_concealed: List[str]  # Subjects that became hidden
    visibility_changes: Dict[str, VisibilityLevel]  # Changes in visibility levels
    update_reason: str

    def get_event_type(self) -> str:
        return "FogOfWarUpdated"


@dataclass(frozen=True)
class SubjectiveAnalysisCompleted(SubjectiveDomainEvent):
    """
    Event raised when an entity completes analysis of their current situation.

    This represents higher-level cognitive processing of available
    information to form strategic assessments.
    """

    turn_brief_id: SubjectiveId
    analysis_type: str  # "tactical", "strategic", "threat_assessment", etc.
    conclusions: List[str]
    confidence_levels: Dict[str, float]  # Conclusion -> confidence
    recommended_actions: List[str]

    def get_event_type(self) -> str:
        return "SubjectiveAnalysisCompleted"


@dataclass(frozen=True)
class TurnBriefExpired(SubjectiveDomainEvent):
    """
    Event raised when a TurnBrief becomes outdated and needs refresh.

    This indicates that the subjective view is too stale to be reliable
    for decision-making.
    """

    turn_brief_id: SubjectiveId
    expiration_reason: str
    last_updated: datetime

    def get_event_type(self) -> str:
        return "TurnBriefExpired"
