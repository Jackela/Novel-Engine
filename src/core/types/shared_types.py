#!/usr/bin/env python3
"""
Shared Type Definitions.
This module defines shared Pydantic models and enums used across the system.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.config import ConfigDict


class ActionPriority(str, Enum):
    """Priority levels for character actions."""

    LOW = "low"
    MEDIUM = "medium"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    """Structured action types for system-level adjudication."""

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
    OTHER = "other"


class ActionIntensity(str, Enum):
    """Normalized action intensity values."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


class EntityType(str, Enum):
    """Entity classification for world state."""

    CHARACTER = "character"
    OBJECT = "object"
    LOCATION = "location"
    EVENT = "event"
    RESOURCE = "resource"
    STRUCTURE = "structure"


class ValidationResult(str, Enum):
    """Validation result status for actions."""

    VALID = "valid"
    INVALID = "invalid"
    REQUIRES_REPAIR = "requires_repair"
    CATASTROPHIC_FAILURE = "catastrophic_failure"


class FogOfWarChannel(str, Enum):
    """Information channels for fog-of-war filtering."""

    VISUAL = "visual"
    RADIO = "radio"
    INTEL = "intel"
    RUMOR = "rumor"
    SENSOR = "sensor"


class SimulationPhase(str, Enum):
    """Phases in the simulation lifecycle."""

    INITIALIZATION = "initialization"
    PLANNING = "planning"
    EXECUTION = "execution"
    RESOLUTION = "resolution"
    CLEANUP = "cleanup"
    COMPLETED = "completed"


CharacterId = str
UserId = str
KnowledgeEntryId = str


class Position(BaseModel):
    """3D position with optional facing and accuracy metadata."""

    x: float
    y: float
    z: float = 0.0
    facing: Optional[float] = None
    accuracy: float = 1.0

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("facing")
    @classmethod
    def _validate_facing(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        if value < 0 or value >= 360:
            raise ValueError("facing must be between 0 and 360 degrees")
        return value

    @field_validator("accuracy")
    @classmethod
    def _validate_accuracy(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("accuracy must be between 0 and 1")
        return value


class BoundingBox(BaseModel):
    """Axis-aligned bounding box."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def _validate_bounds(self) -> "BoundingBox":
        if self.max_x <= self.min_x:
            raise ValueError("max_x must be greater than min_x")
        if self.max_y <= self.min_y:
            raise ValueError("max_y must be greater than min_y")
        return self


class Area(BaseModel):
    """Named area with bounding limits."""

    name: str
    bounds: BoundingBox
    area_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)


class ResourceValue(BaseModel):
    """Track a resource with current and maximum values."""

    current: float
    maximum: float
    minimum: float = 0.0
    regeneration_rate: float = 0.0

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def _validate_values(self) -> "ResourceValue":
        if self.maximum <= 0:
            raise ValueError("maximum must be positive")
        if self.current < self.minimum:
            raise ValueError("current cannot be below minimum")
        if self.current > self.maximum:
            raise ValueError("current cannot exceed maximum")
        if self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum")
        return self

    @property
    def percentage(self) -> float:
        return (self.current / self.maximum) * 100.0 if self.maximum else 0.0


class Equipment(BaseModel):
    """Equipment entry with condition and properties."""

    name: str
    equipment_type: str
    condition: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)
    quantity: int = 1

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("condition")
    @classmethod
    def _validate_condition(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("condition must be between 0 and 1")
        return value

    @field_validator("quantity")
    @classmethod
    def _validate_quantity(cls, value: int) -> int:
        if value < 0:
            raise ValueError("quantity cannot be negative")
        return value


class CharacterStats(BaseModel):
    """Core character attributes."""

    strength: int
    dexterity: int
    intelligence: int
    willpower: int
    perception: int
    charisma: int

    model_config = ConfigDict(validate_assignment=True)

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
        if value < 1 or value > 10:
            raise ValueError("stats must be between 1 and 10")
        return value


class CharacterResources(BaseModel):
    """Resource pools for a character."""

    health: ResourceValue
    stamina: ResourceValue
    morale: ResourceValue
    ammo: Dict[str, int] = Field(default_factory=dict)
    special_resources: Dict[str, ResourceValue] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)


class CharacterState(BaseModel):
    """State flags for a character."""

    conscious: bool = True
    mobile: bool = True
    combat_ready: bool = True
    status_effects: List[str] = Field(default_factory=list)
    injuries: List[str] = Field(default_factory=list)
    fatigue_level: float = 0.0

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("fatigue_level")
    @classmethod
    def _validate_fatigue(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("fatigue_level must be between 0 and 1")
        return value


class CharacterData(BaseModel):
    """Comprehensive character data model."""

    character_id: str
    name: str
    faction: str
    position: Position
    stats: CharacterStats
    resources: CharacterResources
    role: Optional[str] = None
    state: Optional[CharacterState] = None
    equipment: List[str] = Field(default_factory=list)
    ai_personality: Dict[str, Any] = Field(default_factory=dict)
    narrative_context: Optional[str] = None

    model_config = ConfigDict(validate_assignment=True)


class ActionTarget(BaseModel):
    """Target entity for an action."""

    entity_id: str
    entity_type: EntityType
    position: Optional[Position] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)


class ActionParameters(BaseModel):
    """Parameters that shape how an action is executed."""

    intensity: Union[ActionIntensity, float] = ActionIntensity.NORMAL
    duration: float = 1.0
    range: float = 1.0
    modifiers: Dict[str, Any] = Field(default_factory=dict)
    resources_consumed: Dict[str, float] = Field(default_factory=dict)
    conditions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("duration", "range")
    @classmethod
    def _validate_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("value must be non-negative")
        return value


class ProposedAction(BaseModel):
    """Action proposed by an agent before validation."""

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    character_id: str
    action_type: ActionType
    target: Optional[ActionTarget] = None
    parameters: ActionParameters = Field(default_factory=ActionParameters)
    reasoning: Optional[str] = None
    confidence: float = 0.5
    alternatives: List[str] = Field(default_factory=list)
    agent_id: Optional[str] = None

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class ValidatedAction(BaseModel):
    """Action that has passed validation."""

    action_id: str
    character_id: str
    action_type: ActionType
    target: Optional[ActionTarget] = None
    parameters: ActionParameters = Field(default_factory=ActionParameters)
    validation_result: ValidationResult
    validation_details: Dict[str, Any] = Field(default_factory=dict)
    repairs_applied: List[str] = Field(default_factory=list)
    estimated_effects: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)


class IronLawsViolation(BaseModel):
    """Individual Iron Laws violation."""

    law_code: str
    law_name: str
    severity: str
    description: str
    affected_entities: List[str] = Field(default_factory=list)
    suggested_repair: Optional[str] = None

    model_config = ConfigDict(validate_assignment=True)


class IronLawsReport(BaseModel):
    """Aggregated Iron Laws validation report."""

    action_id: str
    overall_result: ValidationResult
    violations: List[IronLawsViolation] = Field(default_factory=list)
    checks_performed: List[str] = Field(default_factory=list)
    repair_attempts: List[str] = Field(default_factory=list)
    final_action: Optional[ValidatedAction] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == "critical" for v in self.violations)

    @property
    def violation_count_by_severity(self) -> Dict[str, int]:
        counts = {"critical": 0, "error": 0, "warning": 0}
        for violation in self.violations:
            if violation.severity in counts:
                counts[violation.severity] += 1
        return counts


class WorldEntity(BaseModel):
    """Entity in the world state."""

    entity_id: str
    entity_type: EntityType
    name: Optional[str] = None
    position: Optional[Position] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    visibility: float = 1.0
    last_updated: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)


class EnvironmentalCondition(BaseModel):
    """Environmental condition affecting areas."""

    condition_type: str
    severity: float
    affected_area: Area
    duration_remaining: float
    effects: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("severity must be between 0 and 1")
        return value


class WorldState(BaseModel):
    """Snapshot of world state for a turn."""

    turn_number: int
    entities: Dict[str, WorldEntity] = Field(default_factory=dict)
    global_properties: Dict[str, Any] = Field(default_factory=dict)
    environmental_conditions: List[EnvironmentalCondition] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("turn_number")
    @classmethod
    def _validate_turn(cls, value: int) -> int:
        if value < 0:
            raise ValueError("turn_number must be non-negative")
        return value

    def get_entities_by_type(self, entity_type: EntityType) -> List[WorldEntity]:
        return [
            entity
            for entity in self.entities.values()
            if entity.entity_type == entity_type
        ]


class InformationSource(BaseModel):
    """Information source for fog-of-war data."""

    source_id: str
    source_type: str
    reliability: float
    access_channels: List[FogOfWarChannel] = Field(default_factory=list)
    range_modifiers: Dict[str, float] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)


class InformationFragment(BaseModel):
    """Information fragment filtered by fog-of-war."""

    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_id: str
    information_type: str
    content: Dict[str, Any]
    source: InformationSource
    channel: FogOfWarChannel
    accuracy: float = 1.0
    freshness: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)


class FogOfWarFilter(BaseModel):
    """Configuration for fog-of-war filtering."""

    observer_id: str
    visual_range: float = 10.0
    radio_range: float = 50.0
    intel_range: float = 100.0
    sensor_range: float = 20.0
    rumor_reliability: float = 0.5
    channel_preferences: Dict[FogOfWarChannel, float] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)


class FilteredWorldView(BaseModel):
    """World view filtered for a specific observer."""

    observer_id: str
    base_world_state: str
    visible_entities: Dict[str, WorldEntity] = Field(default_factory=dict)
    known_information: List[InformationFragment] = Field(default_factory=list)
    uncertainty_markers: List[str] = Field(default_factory=list)
    filter_config: FogOfWarFilter
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)


class KnowledgeFragment(BaseModel):
    """Knowledge fragment for RAG injection."""

    fragment_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    source: str
    relevance_score: float = 0.5
    knowledge_type: str
    tags: List[str] = Field(default_factory=list)
    last_accessed: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)


class ContextualPrompt(BaseModel):
    """Contextual prompt assembled for an agent."""

    base_prompt: str
    character_context: Optional[str] = None
    world_context: Optional[str] = None
    injected_knowledge: List[KnowledgeFragment] = Field(default_factory=list)
    fog_of_war_mask: Optional[str] = None
    prompt_tokens: int = 0

    model_config = ConfigDict(validate_assignment=True)

    def compile_prompt(self) -> str:
        sections = [self.base_prompt]
        if self.character_context:
            sections.append(f"## Character Context\n{self.character_context}")
        if self.world_context:
            sections.append(f"## World State\n{self.world_context}")
        if self.injected_knowledge:
            knowledge_text = "\n".join(
                f"- {item.content}" for item in self.injected_knowledge
            )
            sections.append(f"## Relevant Knowledge\n{knowledge_text}")
        if self.fog_of_war_mask:
            sections.append(f"## Information Constraints\n{self.fog_of_war_mask}")
        return "\n\n".join(sections)


class TurnBrief(BaseModel):
    """Aggregated turn brief for an agent."""

    character_id: str
    turn_number: int
    filtered_world_view: FilteredWorldView
    available_actions: List[ActionType] = Field(default_factory=list)
    contextual_prompt: ContextualPrompt
    tactical_situation: Optional[str] = None
    objectives: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    token_budget: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)


class SimulationConfig(BaseModel):
    """Configuration for simulations."""

    max_turns: int = 10
    turn_timeout: float = 30.0
    max_agents: int = 20
    iron_laws_enabled: bool = True
    fog_of_war_enabled: bool = True
    rag_injection_enabled: bool = True
    performance_mode: str = "balanced"
    logging_level: str = "info"

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("max_turns")
    @classmethod
    def _validate_max_turns(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("max_turns must be between 1 and 100")
        return value

    @field_validator("turn_timeout")
    @classmethod
    def _validate_turn_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("turn_timeout must be positive")
        return value

    @field_validator("max_agents")
    @classmethod
    def _validate_max_agents(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("max_agents must be between 1 and 100")
        return value


class SimulationState(BaseModel):
    """Runtime simulation state."""

    simulation_id: str
    current_turn: int
    phase: SimulationPhase
    active_characters: List[str] = Field(default_factory=list)
    world_state: WorldState
    config: SimulationConfig
    metrics: Dict[str, Any] = Field(default_factory=dict)
    start_time: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)


class TurnResult(BaseModel):
    """Result payload for a completed turn."""

    turn_number: int
    executed_actions: List[ValidatedAction] = Field(default_factory=list)
    world_state_changes: Dict[str, Any] = Field(default_factory=dict)
    character_updates: Dict[str, CharacterData] = Field(default_factory=dict)
    events_generated: List[str] = Field(default_factory=list)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0

    model_config = ConfigDict(validate_assignment=True)


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)


class SystemStatus(BaseModel):
    """System status payload."""

    system_name: str = "Novel Engine"
    version: str = "1.0.0"
    status: str
    uptime_seconds: float
    active_simulations: int
    memory_usage_mb: float
    cpu_usage_percent: float
    components: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("uptime_seconds", "memory_usage_mb")
    @classmethod
    def _validate_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("value must be non-negative")
        return value

    @field_validator("active_simulations")
    @classmethod
    def _validate_active_simulations(cls, value: int) -> int:
        if value < 0:
            raise ValueError("active_simulations must be non-negative")
        return value

    @field_validator("cpu_usage_percent")
    @classmethod
    def _validate_cpu_usage(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("cpu_usage_percent must be between 0 and 100")
        return value


class CacheEntry(BaseModel):
    """Cache entry with TTL support."""

    key: str
    value: Any
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)


class PerformanceMetrics(BaseModel):
    """Performance metrics record."""

    operation_name: str
    duration_ms: float
    memory_delta_mb: float = 0.0
    tokens_consumed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("duration_ms")
    @classmethod
    def _validate_duration(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration_ms must be non-negative")
        return value

    @field_validator("tokens_consumed")
    @classmethod
    def _validate_tokens(cls, value: int) -> int:
        if value < 0:
            raise ValueError("tokens_consumed must be non-negative")
        return value


class StateHash(BaseModel):
    """State hash record for consistency checks."""

    entity_id: str
    hash_type: str
    hash_value: str
    fields_included: List[str]
    salt: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("hash_value")
    @classmethod
    def _validate_hash_value(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("hash_value must be at least 32 hex characters")
        hex_chars = "0123456789abcdefABCDEF"
        if any(char not in hex_chars for char in value):
            raise ValueError("hash_value must be hexadecimal")
        return value


class ConsistencyCheck(BaseModel):
    """Consistency check report between components."""

    check_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_ids: List[str]
    check_type: str
    is_consistent: bool
    inconsistencies: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    remediation_suggestions: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class CharacterAction(BaseModel):
    """Lightweight action payload produced by agents."""

    agent_id: Optional[str] = None
    action_type: str
    target: Optional[str] = None
    priority: ActionPriority = ActionPriority.NORMAL
    reasoning: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("action_type")
    @classmethod
    def _validate_action_type(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("action_type cannot be empty")
        return value

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: ActionPriority | str) -> ActionPriority:
        if isinstance(value, ActionPriority):
            return value
        return ActionPriority(value.lower())


MODEL_REGISTRY = {
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


__all__ = [
    "ActionIntensity",
    "ActionParameters",
    "ActionPriority",
    "ActionTarget",
    "ActionType",
    "APIResponse",
    "Area",
    "BoundingBox",
    "CacheEntry",
    "CharacterAction",
    "CharacterData",
    "CharacterId",
    "CharacterResources",
    "CharacterState",
    "CharacterStats",
    "ConsistencyCheck",
    "ContextualPrompt",
    "EntityType",
    "EnvironmentalCondition",
    "Equipment",
    "FilteredWorldView",
    "FogOfWarChannel",
    "FogOfWarFilter",
    "InformationFragment",
    "InformationSource",
    "IronLawsReport",
    "IronLawsViolation",
    "KnowledgeEntryId",
    "KnowledgeFragment",
    "MODEL_REGISTRY",
    "PerformanceMetrics",
    "Position",
    "ProposedAction",
    "ResourceValue",
    "SimulationConfig",
    "SimulationPhase",
    "SimulationState",
    "StateHash",
    "SystemStatus",
    "TurnBrief",
    "TurnResult",
    "UserId",
    "ValidatedAction",
    "ValidationResult",
    "WorldEntity",
    "WorldState",
]
