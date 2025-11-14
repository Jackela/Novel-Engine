#!/usr/bin/env python3
"""
Shared data models and enums used across Novel-Engine.

This module centralizes the Pydantic models that power schema validation in
tests under ``tests/test_schemas.py`` and the Iron Laws safety suite.  The
implementations intentionally follow the expectations encoded in the tests so
that serialization, validation, and helper methods behave deterministically.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ActionType(str, Enum):
    """Supported action categories for characters and agents."""

    MOVE = "move"
    ATTACK = "attack"
    DEFEND = "defend"
    COMMUNICATE = "communicate"
    OBSERVE = "observe"
    USE_ITEM = "use_item"
    SPECIAL_ABILITY = "special_ability"
    WAIT = "wait"
    RETREAT = "retreat"
    FORTIFY = "fortify"
    INVESTIGATE = "investigate"
    INTERACT = "interact"


class ActionIntensity(str, Enum):
    """Standardized intensity bands for actions."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


class EntityType(str, Enum):
    """Entity categories tracked inside `WorldState`."""

    CHARACTER = "character"
    OBJECT = "object"
    LOCATION = "location"
    EVENT = "event"
    RESOURCE = "resource"
    STRUCTURE = "structure"


class FogOfWarChannel(str, Enum):
    """Communication / perception channels for fog-of-war modelling."""

    VISUAL = "visual"
    RADIO = "radio"
    INTEL = "intel"
    RUMOR = "rumor"
    SENSOR = "sensor"


class SimulationPhase(str, Enum):
    """Lifecycle phases for a simulation turn."""

    INITIALIZATION = "initialization"
    PLANNING = "planning"
    EXECUTION = "execution"
    RESOLUTION = "resolution"
    CLEANUP = "cleanup"
    COMPLETED = "completed"


class ValidationResult(str, Enum):
    """Aggregate result values produced by Iron Laws validation."""

    VALID = "valid"
    INVALID = "invalid"
    REQUIRES_REPAIR = "requires_repair"
    CATASTROPHIC_FAILURE = "catastrophic_failure"
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    APPROVED_WITH_MODIFICATIONS = "approved_with_modifications"
    NEEDS_MODIFICATION = "needs_modification"
    REJECTED = "rejected"


class DecisionType(str, Enum):
    """Simple decision taxonomy used by quality framework tests."""

    IMMEDIATE = "immediate"
    STRATEGIC = "strategic"


class ActionPriority(str, Enum):
    """Priority buckets for downstream schedulers."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    NORMAL = "normal"
    LOW = "low"


# ---------------------------------------------------------------------------
# Spatial types
# ---------------------------------------------------------------------------


class Position(BaseModel):
    """Represents a point in space with accuracy metadata."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float = 0.0
    facing: float = 0.0
    accuracy: float = 1.0

    @field_validator("accuracy")
    @classmethod
    def _validate_accuracy(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("accuracy must be between 0.0 and 1.0")
        return value


class BoundingBox(BaseModel):
    """Axis-aligned bounding box."""

    model_config = ConfigDict(extra="forbid")

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @model_validator(mode="after")
    def _validate_bounds(self) -> "BoundingBox":
        if self.max_x <= self.min_x:
            raise ValueError("max_x must be greater than min_x")
        if self.max_y <= self.min_y:
            raise ValueError("max_y must be greater than min_y")
        return self


class Area(BaseModel):
    """Named area tied to a bounding box."""

    model_config = ConfigDict(extra="forbid")

    name: str
    bounds: BoundingBox
    area_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Resource and equipment types
# ---------------------------------------------------------------------------


class ResourceValue(BaseModel):
    """Tracks a resource with optional regen metadata."""

    model_config = ConfigDict(extra="forbid")

    current: float
    maximum: float
    regeneration_rate: float = 0.0

    @model_validator(mode="after")
    def _validate_values(self) -> "ResourceValue":
        if self.maximum <= 0:
            raise ValueError("maximum must be positive")
        if not 0.0 <= self.current <= self.maximum:
            raise ValueError("current must be between 0 and maximum")
        if self.regeneration_rate < 0.0:
            raise ValueError("regeneration_rate must be non-negative")
        return self

    @property
    def percentage(self) -> float:
        """Return the current percentage (0-100)."""
        if self.maximum == 0:
            return 0.0
        return (self.current / self.maximum) * 100.0


class Equipment(BaseModel):
    """Equipment metadata with durability information."""

    model_config = ConfigDict(extra="forbid")

    name: str
    equipment_type: str
    condition: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)
    quantity: int = 1

    @model_validator(mode="after")
    def _validate_values(self) -> "Equipment":
        if not 0.0 <= self.condition <= 1.0:
            raise ValueError("condition must be between 0.0 and 1.0")
        if self.quantity < 0:
            raise ValueError("quantity must be non-negative")
        return self


# ---------------------------------------------------------------------------
# Character-centric models
# ---------------------------------------------------------------------------


class CharacterStats(BaseModel):
    """Ability scores for a character."""

    model_config = ConfigDict(extra="forbid")

    strength: int
    dexterity: int
    intelligence: int
    willpower: int
    perception: int
    charisma: int

    @field_validator(
        "strength",
        "dexterity",
        "intelligence",
        "willpower",
        "perception",
        "charisma",
    )
    @classmethod
    def _validate_stat(cls, value: int) -> int:
        if not 1 <= value <= 10:
            raise ValueError("stats must be between 1 and 10")
        return value


class CharacterResources(BaseModel):
    """Wrapper for health/stamina/morale with optional extras."""

    model_config = ConfigDict(extra="forbid")

    health: ResourceValue
    stamina: ResourceValue
    morale: ResourceValue
    ammo: Dict[str, int] = Field(default_factory=dict)
    special_resources: Dict[str, ResourceValue] = Field(default_factory=dict)


class CharacterState(BaseModel):
    """Current survivability/injury state flags."""

    model_config = ConfigDict(extra="forbid")

    conscious: bool = True
    mobile: bool = True
    combat_ready: bool = True
    status_effects: List[str] = Field(default_factory=list)
    injuries: List[str] = Field(default_factory=list)
    fatigue_level: float = 0.0

    @field_validator("fatigue_level")
    @classmethod
    def _validate_fatigue(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("fatigue_level must be between 0.0 and 1.0")
        return value


class CharacterData(BaseModel):
    """High-level character description consumed by multiple systems."""

    model_config = ConfigDict(extra="forbid")

    character_id: str
    name: str
    faction: Optional[str] = None
    rank: Optional[str] = None
    position: Optional[Position] = None
    stats: Optional[CharacterStats] = None
    resources: Optional[CharacterResources] = None
    equipment: List[str] = Field(default_factory=list)
    status_effects: List[str] = Field(default_factory=list)
    ai_personality: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Action models
# ---------------------------------------------------------------------------


class ActionTarget(BaseModel):
    """Target metadata for an action."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    entity_type: EntityType
    position: Optional[Position] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class ActionParameters(BaseModel):
    """Tunable action parameters."""

    model_config = ConfigDict(extra="forbid")

    intensity: Union[ActionIntensity, float] = ActionIntensity.NORMAL
    duration: float = 1.0
    range: float = 1.0
    modifiers: Dict[str, float] = Field(default_factory=dict)
    resources_consumed: Dict[str, float] = Field(default_factory=dict)
    conditions: List[str] = Field(default_factory=list)

    @field_validator("duration", "range")
    @classmethod
    def _validate_non_negative(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("duration and range must be non-negative")
        return value

    @field_validator("intensity")
    @classmethod
    def _validate_intensity(
        cls, value: Union[ActionIntensity, float]
    ) -> Union[ActionIntensity, float]:
        if isinstance(value, float) and not 0.0 <= value <= 1.0:
            raise ValueError("numeric intensity must be between 0.0 and 1.0")
        return value


class ProposedAction(BaseModel):
    """Action proposed by an agent before validation."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    character_id: str
    action_type: ActionType
    target: Optional[ActionTarget] = None
    parameters: ActionParameters = Field(default_factory=ActionParameters)
    reasoning: str = ""
    confidence: float = 0.5
    alternatives: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


class CharacterAction(BaseModel):
    """Lightweight representation of an action selected by a PersonaAgent."""

    model_config = ConfigDict(extra="forbid")

    action_type: str
    target: Optional[Any] = None
    priority: ActionPriority = ActionPriority.NORMAL
    reasoning: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidatedAction(BaseModel):
    """Action after Iron Laws validation."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    character_id: str
    action_type: ActionType
    target: Optional[ActionTarget] = None
    parameters: ActionParameters = Field(default_factory=ActionParameters)
    validation_result: ValidationResult = ValidationResult.VALID
    validation_details: Dict[str, Any] = Field(default_factory=dict)
    repairs_applied: List[str] = Field(default_factory=list)
    estimated_effects: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IronLawsViolation(BaseModel):
    """Details about a single Iron Law violation."""

    model_config = ConfigDict(extra="forbid")

    law_code: str
    law_name: str
    severity: str
    description: str
    affected_entities: List[str] = Field(default_factory=list)
    suggested_repair: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_critical(self) -> bool:
        return self.severity.lower() == "critical"


class IronLawsReport(BaseModel):
    """Aggregate validation report for an action."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    character_id: Optional[str] = None
    action_summary: Optional[str] = None
    overall_result: ValidationResult = ValidationResult.VALID
    violations: List[IronLawsViolation] = Field(default_factory=list)
    checks_performed: List[str] = Field(default_factory=list)
    repair_attempts: List[str] = Field(default_factory=list)
    repair_log: List[str] = Field(default_factory=list)
    repaired_action: Optional[ValidatedAction | ProposedAction] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def has_critical_violations(self) -> bool:
        return any(v.is_critical for v in self.violations)

    @property
    def violation_count_by_severity(self) -> Dict[str, int]:
        buckets = {"critical": 0, "error": 0, "warning": 0, "info": 0}
        for violation in self.violations:
            severity = violation.severity.lower()
            if severity in buckets:
                buckets[severity] += 1
            else:
                buckets.setdefault(severity, 0)
                buckets[severity] += 1
        return buckets


# ---------------------------------------------------------------------------
# World state types
# ---------------------------------------------------------------------------


class WorldEntity(BaseModel):
    """Entity snapshot within the world."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    entity_type: EntityType
    name: str
    position: Optional[Position] = None
    state: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorldState(BaseModel):
    """Turn-level snapshot of the world."""

    model_config = ConfigDict(extra="forbid")

    turn_number: int = 0
    entities: Dict[str, WorldEntity] = Field(default_factory=dict)
    global_properties: Dict[str, Any] = Field(default_factory=dict)
    active_events: List[str] = Field(default_factory=list)
    environmental_conditions: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def get_entities_by_type(self, entity_type: EntityType) -> List[WorldEntity]:
        """Return entities filtered by type."""
        return [
            entity
            for entity in self.entities.values()
            if entity.entity_type == entity_type
        ]


# ---------------------------------------------------------------------------
# Fog-of-war and knowledge types
# ---------------------------------------------------------------------------


class InformationSource(BaseModel):
    """Describes how information was obtained."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_type: str
    reliability: float = 1.0
    access_channels: List[FogOfWarChannel] = Field(default_factory=list)
    range_modifiers: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("reliability")
    @classmethod
    def _validate_reliability(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("reliability must be between 0.0 and 1.0")
        return value


class InformationFragment(BaseModel):
    """Atomic piece of information derived from a source."""

    model_config = ConfigDict(extra="forbid")

    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_id: str
    information_type: str
    content: Dict[str, Any]
    source: InformationSource
    channel: FogOfWarChannel
    accuracy: float = 1.0
    freshness: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("accuracy", "freshness")
    @classmethod
    def _validate_probabilities(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("values must be between 0.0 and 1.0")
        return value


class FogOfWarFilter(BaseModel):
    """Configuration describing what an observer can perceive."""

    model_config = ConfigDict(extra="forbid")

    observer_id: str
    visual_range: float = 10.0
    radio_range: float = 50.0
    intel_range: float = 100.0
    sensor_range: float = 25.0
    rumor_reliability: float = 0.5
    channel_preferences: Dict[FogOfWarChannel, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("rumor_reliability")
    @classmethod
    def _validate_rumor(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("rumor_reliability must be between 0.0 and 1.0")
        return value


class FilteredWorldView(BaseModel):
    """World view after fog-of-war filtering."""

    model_config = ConfigDict(extra="forbid")

    observer_id: str
    base_world_state: Optional[str] = None
    visible_entities: Dict[str, WorldEntity] = Field(default_factory=dict)
    known_information: List[InformationFragment] = Field(default_factory=list)
    uncertainty_markers: List[str] = Field(default_factory=list)
    filter_config: Optional[FogOfWarFilter] = None


class KnowledgeFragment(BaseModel):
    """Knowledge snippet used for RAG injection."""

    model_config = ConfigDict(extra="forbid")

    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    source: str
    relevance_score: float = 0.5
    knowledge_type: str = "general"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("relevance_score")
    @classmethod
    def _validate_relevance(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        return value

    def touch(self) -> None:
        """Update access timestamp."""
        self.last_accessed = datetime.utcnow()


class ContextualPrompt(BaseModel):
    """Complete prompt compiled for PersonaAgent decisions."""

    model_config = ConfigDict(extra="forbid")

    base_prompt: str
    character_context: Optional[str] = None
    world_context: Optional[str] = None
    injected_knowledge: List[KnowledgeFragment] = Field(default_factory=list)
    fog_of_war_mask: Optional[str] = None
    prompt_tokens: int = 0

    def compile_prompt(self) -> str:
        """Assemble a structured prompt string for downstream models."""
        sections = [self.base_prompt]
        if self.character_context:
            sections.append("## Character Context")
            sections.append(self.character_context)
        if self.world_context:
            sections.append("## World State")
            sections.append(self.world_context)
        if self.injected_knowledge:
            sections.append("## Relevant Knowledge")
            knowledge_lines = [
                f"- {fragment.content}" for fragment in self.injected_knowledge
            ]
            sections.extend(knowledge_lines)
        if self.fog_of_war_mask:
            sections.append("## Information Constraints")
            sections.append(self.fog_of_war_mask)
        return "\n".join(sections)


class TurnBrief(BaseModel):
    """Brief delivered to a character before making a decision."""

    model_config = ConfigDict(extra="forbid")

    character_id: str
    turn_number: int
    filtered_world_view: FilteredWorldView
    available_actions: List[ActionType] = Field(default_factory=list)
    contextual_prompt: Optional[ContextualPrompt] = None
    tactical_situation: Optional[str] = None
    objectives: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    token_budget: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Simulation and turn results
# ---------------------------------------------------------------------------


class SimulationConfig(BaseModel):
    """Simulation knobs with validation."""

    model_config = ConfigDict(extra="forbid")

    max_turns: int = 10
    turn_timeout: float = 30.0
    max_agents: int = 20
    iron_laws_enabled: bool = True
    fog_of_war_enabled: bool = True
    rag_injection_enabled: bool = True
    performance_mode: str = "balanced"
    logging_level: str = "info"

    @model_validator(mode="after")
    def _validate_fields(self) -> "SimulationConfig":
        if not 1 <= self.max_turns <= 100:
            raise ValueError("max_turns must be between 1 and 100")
        if self.turn_timeout <= 0.0:
            raise ValueError("turn_timeout must be positive")
        if not 1 <= self.max_agents <= 100:
            raise ValueError("max_agents must be between 1 and 100")
        return self


class SimulationState(BaseModel):
    """Runtime state for a simulation session."""

    model_config = ConfigDict(extra="forbid")

    simulation_id: str
    current_turn: int = 0
    phase: SimulationPhase = SimulationPhase.INITIALIZATION
    active_characters: List[str] = Field(default_factory=list)
    world_state: WorldState = Field(default_factory=WorldState)
    config: SimulationConfig = Field(default_factory=SimulationConfig)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TurnResult(BaseModel):
    """Output of a completed turn."""

    model_config = ConfigDict(extra="forbid")

    turn_number: int
    executed_actions: List[ValidatedAction] = Field(default_factory=list)
    world_state_changes: Dict[str, Any] = Field(default_factory=dict)
    character_updates: Dict[str, CharacterData] = Field(default_factory=dict)
    events_generated: List[str] = Field(default_factory=list)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# API / telemetry models
# ---------------------------------------------------------------------------


class APIResponse(BaseModel):
    """Canonical API response payload."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class SystemStatus(BaseModel):
    """High-level system health snapshot."""

    model_config = ConfigDict(extra="forbid")

    system_name: str = "Novel Engine"
    version: str = "1.0.0"
    status: str
    uptime_seconds: float
    active_simulations: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    components: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_values(self) -> "SystemStatus":
        if self.uptime_seconds < 0.0:
            raise ValueError("uptime_seconds must be non-negative")
        if self.active_simulations < 0:
            raise ValueError("active_simulations must be non-negative")
        if not 0.0 <= self.cpu_usage_percent <= 100.0:
            raise ValueError("cpu_usage_percent must be between 0 and 100")
        if self.memory_usage_mb < 0.0:
            raise ValueError("memory_usage_mb must be non-negative")
        return self


class CacheEntry(BaseModel):
    """Cache bookkeeping entry."""

    model_config = ConfigDict(extra="forbid")

    key: str
    value: Any
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds


class PerformanceMetrics(BaseModel):
    """Timing/resource stats for a code path."""

    model_config = ConfigDict(extra="forbid")

    operation_name: str
    duration_ms: float
    memory_delta_mb: float = 0.0
    tokens_consumed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def _validate_non_negative(self) -> "PerformanceMetrics":
        if self.duration_ms < 0.0:
            raise ValueError("duration_ms must be non-negative")
        if self.tokens_consumed < 0:
            raise ValueError("tokens_consumed must be non-negative")
        if self.cache_hits < 0 or self.cache_misses < 0:
            raise ValueError("cache hit/miss counts must be non-negative")
        if self.error_count < 0:
            raise ValueError("error_count must be non-negative")
        return self


class StateHash(BaseModel):
    """Hash summary of a stateful entity."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    hash_type: str
    hash_value: str
    fields_included: List[str]
    salt: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("hash_value")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("hash_value must be at least 32 hex characters")
        try:
            int(value, 16)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("hash_value must be hexadecimal") from exc
        return value


class ConsistencyCheck(BaseModel):
    """Result of a consistency evaluation across entities."""

    model_config = ConfigDict(extra="forbid")

    check_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_ids: List[str]
    check_type: str
    is_consistent: bool
    inconsistencies: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    remediation_suggestions: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


# ---------------------------------------------------------------------------
# Shared registry + compatibility wrappers
# ---------------------------------------------------------------------------


MODEL_REGISTRY: Dict[str, type[BaseModel]] = {
    "character_data": CharacterData,
    "world_state": WorldState,
    "proposed_action": ProposedAction,
    "validated_action": ValidatedAction,
    "iron_laws_report": IronLawsReport,
    "turn_brief": TurnBrief,
    "simulation_state": SimulationState,
    "turn_result": TurnResult,
    "api_response": APIResponse,
}


class SharedTypes:
    """
    Lightweight namespace exposing enums for legacy callers.

    Only the pieces referenced by the quality framework tests are surfaced here.
    """

    ActionType = ActionType
    DecisionType = DecisionType


__all__ = [
    # Enums
    "ActionType",
    "ActionPriority",
    "ActionIntensity",
    "EntityType",
    "FogOfWarChannel",
    "SimulationPhase",
    "ValidationResult",
    "DecisionType",
    # Spatial types
    "Position",
    "BoundingBox",
    "Area",
    # Resources / equipment
    "ResourceValue",
    "Equipment",
    "CharacterStats",
    "CharacterResources",
    "CharacterState",
    "CharacterData",
    # Actions / validation
    "ActionTarget",
    "ActionParameters",
    "ProposedAction",
    "CharacterAction",
    "ValidatedAction",
    "IronLawsViolation",
    "IronLawsReport",
    # World + fog of war
    "WorldEntity",
    "WorldState",
    "InformationSource",
    "InformationFragment",
    "FogOfWarFilter",
    "FilteredWorldView",
    "KnowledgeFragment",
    "ContextualPrompt",
    "TurnBrief",
    # Simulation + performance
    "SimulationConfig",
    "SimulationState",
    "TurnResult",
    "APIResponse",
    "SystemStatus",
    "CacheEntry",
    "PerformanceMetrics",
    "StateHash",
    "ConsistencyCheck",
    # Registry / compatibility
    "MODEL_REGISTRY",
    "SharedTypes",
]
