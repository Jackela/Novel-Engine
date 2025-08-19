"""
Novel Engine Shared Type Definitions
====================================

Comprehensive Pydantic model definitions for the Novel Engine system.
This module provides type-safe data structures for all major system components
including simulation state, character data, world state, actions, and validation.

These models serve as the foundation for:
- Iron Laws validation system
- Fog of War information filtering
- Turn Brief generation and RAG injection
- API request/response validation
- Inter-component data exchange
- State persistence and serialization

Architecture Reference: 
- docs/SCHEMAS.md - Detailed schema documentation
- docs/ADRs/ADR-003-pydantic-schemas.md - Architecture decision record
"""

from typing import Dict, List, Optional, Union, Any, Literal, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from uuid import uuid4
import json

# =============================================================================
# Base Types and Enums
# =============================================================================

class ActionType(str, Enum):
    """Enumeration of possible action types in the simulation."""
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
    SEARCH = "search"
    HIDE = "hide"
    INTERACT = "interact"
    CAST_SPELL = "cast_spell"

class ValidationStatus(str, Enum):
    """Enumeration of Iron Laws validation results."""
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    REQUIRES_REPAIR = "requires_repair"
    REJECTED = "rejected"
    ERROR = "error"

class ActionIntensity(str, Enum):
    """Enumeration of action intensity levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"

class EntityType(str, Enum):
    """Enumeration of entity types in the world state."""
    CHARACTER = "character"
    OBJECT = "object"
    LOCATION = "location"
    EVENT = "event"
    RESOURCE = "resource"
    STRUCTURE = "structure"

class ValidationResult(str, Enum):
    """Iron Laws validation results."""
    VALID = "valid"
    INVALID = "invalid"
    REQUIRES_REPAIR = "requires_repair"
    CATASTROPHIC_FAILURE = "catastrophic_failure"

class FogOfWarChannel(str, Enum):
    """Information channels for Fog of War filtering."""
    VISUAL = "visual"
    RADIO = "radio"
    INTEL = "intel"
    RUMOR = "rumor"
    SENSOR = "sensor"

class SimulationPhase(str, Enum):
    """Current phase of simulation execution."""
    INITIALIZATION = "initialization"
    PLANNING = "planning"
    EXECUTION = "execution"
    RESOLUTION = "resolution"
    CLEANUP = "cleanup"
    COMPLETED = "completed"

# =============================================================================
# Coordinate and Spatial Types
# =============================================================================

class Position(BaseModel):
    """3D position coordinates with optional metadata."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate") 
    z: float = Field(default=0.0, description="Z coordinate (elevation)")
    facing: Optional[float] = Field(default=None, ge=0.0, lt=360.0, description="Facing direction in degrees")
    accuracy: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Position accuracy (0.0-1.0)")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "x": 150.5,
                "y": 200.0,
                "z": 10.0,
                "facing": 270.0,
                "accuracy": 0.95
            }
        }
    )

class BoundingBox(BaseModel):
    """Rectangular bounding area definition."""
    min_x: float = Field(..., description="Minimum X coordinate")
    min_y: float = Field(..., description="Minimum Y coordinate")
    max_x: float = Field(..., description="Maximum X coordinate")
    max_y: float = Field(..., description="Maximum Y coordinate")
    
    @model_validator(mode='after')
    def validate_bounds(self):
        """
        Validate that bounding box dimensions are logical.
        
        Returns:
            Self if validation passes
            
        Raises:
            ValueError: If max values are not greater than min values
        """
        if self.max_x <= self.min_x:
            raise ValueError('max_x must be greater than min_x')
        if self.max_y <= self.min_y:
            raise ValueError('max_y must be greater than min_y')
        return self

class Area(BaseModel):
    """Named area with bounding box and properties."""
    name: str = Field(..., min_length=1, max_length=100, description="Area identifier")
    bounds: BoundingBox = Field(..., description="Area boundaries")
    area_type: str = Field(..., description="Type of area (battlefield, building, etc.)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Area-specific properties")

# =============================================================================
# Resource and Equipment Types
# =============================================================================

class ResourceValue(BaseModel):
    """Resource with current and maximum values."""
    current: float = Field(..., ge=0.0, description="Current resource amount")
    maximum: float = Field(..., gt=0.0, description="Maximum resource capacity")
    regeneration_rate: Optional[float] = Field(default=0.0, description="Per-turn regeneration rate")
    
    @model_validator(mode='after')
    def validate_current_not_exceed_maximum(self):
        """
        Validate that current value does not exceed maximum.
        
        Returns:
            Self if validation passes
            
        Raises:
            ValueError: If current value exceeds maximum
        """
        if self.current > self.maximum:
            raise ValueError('Current value cannot exceed maximum')
        return self
    
    @property
    def percentage(self) -> float:
        """Get resource as percentage of maximum."""
        return (self.current / self.maximum) * 100.0 if self.maximum > 0 else 0.0

class Equipment(BaseModel):
    """Equipment item with properties and condition."""
    name: str = Field(..., min_length=1, max_length=100, description="Equipment name")
    equipment_type: str = Field(..., description="Category of equipment")
    condition: float = Field(default=1.0, ge=0.0, le=1.0, description="Condition rating (0.0-1.0)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Equipment-specific properties")
    quantity: int = Field(default=1, ge=0, description="Number of items")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Lasgun",
                "equipment_type": "weapon",
                "condition": 0.85,
                "properties": {
                    "damage": 15,
                    "range": 150,
                    "ammo_type": "las_cell"
                },
                "quantity": 1
            }
        }
    )

# =============================================================================
# Character and Agent Types  
# =============================================================================

class CharacterStats(BaseModel):
    """Character statistics and attributes."""
    strength: int = Field(..., ge=1, le=10, description="Physical strength")
    dexterity: int = Field(..., ge=1, le=10, description="Agility and coordination")
    intelligence: int = Field(..., ge=1, le=10, description="Reasoning ability")
    willpower: int = Field(..., ge=1, le=10, description="Mental fortitude")
    perception: int = Field(..., ge=1, le=10, description="Awareness and observation")
    charisma: int = Field(..., ge=1, le=10, description="Social influence")
    
    @field_validator('strength', 'dexterity', 'intelligence', 'willpower', 'perception', 'charisma')
    @classmethod
    def validate_stats_range(cls, v):
        """
        Validate that all stats are within acceptable range.
        
        Args:
            v: Dictionary of stat values to validate
            
        Returns:
            Validated stats dictionary
            
        Raises:
            ValueError: If any stat is outside the 0-100 range
        """
        if not isinstance(v, int) or v < 1 or v > 10:
            raise ValueError('All stats must be integers between 1 and 10')
        return v

class CharacterResources(BaseModel):
    """Character resource pools."""
    health: ResourceValue = Field(..., description="Physical health/hit points")
    stamina: ResourceValue = Field(..., description="Physical endurance")
    morale: ResourceValue = Field(..., description="Mental/spiritual strength")
    ammo: Dict[str, int] = Field(default_factory=dict, description="Ammunition by type")
    special_resources: Dict[str, ResourceValue] = Field(default_factory=dict, description="Custom resource pools")

class CharacterState(BaseModel):
    """Current state and status effects of a character."""
    conscious: bool = Field(default=True, description="Whether character is conscious")
    mobile: bool = Field(default=True, description="Whether character can move")
    combat_ready: bool = Field(default=True, description="Whether character can fight")
    status_effects: List[str] = Field(default_factory=list, description="Active status effects")
    injuries: List[str] = Field(default_factory=list, description="Current injuries")
    fatigue_level: float = Field(default=0.0, ge=0.0, le=1.0, description="Fatigue level (0.0-1.0)")

class CharacterData(BaseModel):
    """Complete character data structure."""
    character_id: str = Field(..., min_length=1, description="Unique character identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    faction: str = Field(..., description="Character's faction/allegiance")
    position: Position = Field(..., description="Current position")
    stats: CharacterStats = Field(..., description="Character attributes")
    resources: CharacterResources = Field(..., description="Resource pools")
    equipment: List[Equipment] = Field(default_factory=list, description="Equipped items")
    state: CharacterState = Field(default_factory=CharacterState, description="Current status")
    ai_personality: Dict[str, Any] = Field(default_factory=dict, description="AI behavior parameters")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "character_id": "char_001",
                "name": "Brother Marcus",
                "faction": "Death Korps of Krieg",
                "position": {
                    "x": 100.0,
                    "y": 150.0,
                    "z": 0.0,
                    "facing": 90.0
                },
                "stats": {
                    "strength": 7,
                    "dexterity": 6,
                    "intelligence": 5,
                    "willpower": 9,
                    "perception": 6,
                    "charisma": 4
                }
            }
        }
    )

# =============================================================================
# Action and Decision Types
# =============================================================================

class ActionTarget(BaseModel):
    """Target specification for actions."""
    entity_id: str = Field(..., description="Target entity identifier")
    entity_type: EntityType = Field(..., description="Type of target entity")
    position: Optional[Position] = Field(default=None, description="Target position if applicable")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Target-specific properties")

class ActionParameters(BaseModel):
    """Parameters for action execution."""
    intensity: Optional[Union[ActionIntensity, float]] = Field(default=ActionIntensity.NORMAL, description="Action intensity level or numeric value")
    duration: Optional[float] = Field(default=1.0, ge=0.0, description="Duration in time units")
    range: Optional[float] = Field(default=1.0, ge=0.0, description="Action range in units")
    modifiers: Dict[str, float] = Field(default_factory=dict, description="Action modifiers")
    resources_consumed: Dict[str, float] = Field(default_factory=dict, description="Resources required")
    conditions: List[str] = Field(default_factory=list, description="Required conditions")

class ProposedAction(BaseModel):
    """Action proposed by an agent before validation."""
    action_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique action identifier")
    character_id: str = Field(..., description="Character performing the action")
    action_type: ActionType = Field(..., description="Type of action to perform")
    target: Optional[ActionTarget] = Field(default=None, description="Action target")
    parameters: ActionParameters = Field(default_factory=ActionParameters, description="Action parameters")
    reasoning: str = Field(..., min_length=1, description="AI reasoning for this action")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="AI confidence in action choice")
    alternatives: List[str] = Field(default_factory=list, description="Alternative actions considered")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "character_id": "char_001", 
                "action_type": "attack",
                "target": {
                    "entity_id": "enemy_001",
                    "entity_type": "character"
                },
                "reasoning": "Enemy is within range and vulnerable",
                "confidence": 0.8
            }
        }
    )

class ValidatedAction(BaseModel):
    """Action that has passed Iron Laws validation."""
    action_id: str = Field(..., description="Unique action identifier")
    character_id: str = Field(..., description="Character performing the action")
    action_type: ActionType = Field(..., description="Type of action to perform")
    target: Optional[ActionTarget] = Field(default=None, description="Action target")
    parameters: ActionParameters = Field(..., description="Action parameters")
    validation_result: ValidationResult = Field(..., description="Validation outcome")
    validation_details: Dict[str, Any] = Field(default_factory=dict, description="Validation specifics")
    repairs_applied: List[str] = Field(default_factory=list, description="Repairs made during validation")
    estimated_effects: Dict[str, Any] = Field(default_factory=dict, description="Predicted action effects")

# =============================================================================
# Iron Laws Validation Types
# =============================================================================

class IronLawsViolation(BaseModel):
    """Specific Iron Laws rule violation."""
    law_code: str = Field(..., description="Law identifier (E001-E005)")
    law_name: str = Field(..., description="Human-readable law name")
    severity: Literal["warning", "error", "critical"] = Field(..., description="Violation severity")
    description: str = Field(..., description="Violation description")
    affected_entities: List[str] = Field(default_factory=list, description="Entities affected by violation")
    suggested_repair: Optional[str] = Field(default=None, description="Suggested fix for violation")

class IronLawsReport(BaseModel):
    """Complete Iron Laws validation report."""
    action_id: str = Field(..., description="Action being validated")
    timestamp: datetime = Field(default_factory=datetime.now, description="Validation timestamp")
    overall_result: ValidationResult = Field(..., description="Overall validation result")
    violations: List[IronLawsViolation] = Field(default_factory=list, description="Rule violations found")
    checks_performed: List[str] = Field(..., description="Validation checks executed")
    repair_attempts: List[str] = Field(default_factory=list, description="Repairs attempted")
    final_action: Optional[ValidatedAction] = Field(default=None, description="Final validated action")
    
    @property
    def has_critical_violations(self) -> bool:
        """Check if report contains critical violations."""
        return any(v.severity == "critical" for v in self.violations)
    
    @property
    def violation_count_by_severity(self) -> Dict[str, int]:
        """Count violations by severity level."""
        counts = {"warning": 0, "error": 0, "critical": 0}
        for violation in self.violations:
            counts[violation.severity] += 1
        return counts

# =============================================================================
# World State and Environment Types
# =============================================================================

class WorldEntity(BaseModel):
    """Generic world entity with properties."""
    entity_id: str = Field(..., description="Unique entity identifier")
    entity_type: EntityType = Field(..., description="Type of entity")
    name: str = Field(..., min_length=1, description="Entity name or identifier")
    position: Optional[Position] = Field(default=None, description="Entity position if applicable")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity-specific properties")
    visibility: float = Field(default=1.0, ge=0.0, le=1.0, description="Base visibility factor")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

class EnvironmentalCondition(BaseModel):
    """Environmental factors affecting the simulation."""
    condition_type: str = Field(..., description="Type of environmental condition")
    severity: float = Field(..., ge=0.0, le=1.0, description="Condition intensity")
    affected_area: Optional[Area] = Field(default=None, description="Area affected by condition")
    duration_remaining: Optional[float] = Field(default=None, ge=0.0, description="Remaining duration")
    effects: Dict[str, float] = Field(default_factory=dict, description="Condition effects on entities")

class WorldState(BaseModel):
    """Complete world state snapshot."""
    turn_number: int = Field(..., ge=0, description="Current turn number")
    timestamp: datetime = Field(default_factory=datetime.now, description="State timestamp")
    entities: Dict[str, WorldEntity] = Field(default_factory=dict, description="All world entities")
    environmental_conditions: List[EnvironmentalCondition] = Field(default_factory=list)
    active_areas: Dict[str, Area] = Field(default_factory=dict, description="Defined areas")
    global_properties: Dict[str, Any] = Field(default_factory=dict, description="Global world properties")
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[WorldEntity]:
        """Get all entities of a specific type."""
        return [entity for entity in self.entities.values() if entity.entity_type == entity_type]
    
    def get_entities_in_area(self, area: Area) -> List[WorldEntity]:
        """Get all entities within a specified area."""
        entities_in_area = []
        for entity in self.entities.values():
            if entity.position:
                if (area.bounds.min_x <= entity.position.x <= area.bounds.max_x and
                    area.bounds.min_y <= entity.position.y <= area.bounds.max_y):
                    entities_in_area.append(entity)
        return entities_in_area

# =============================================================================
# Fog of War and Information Types
# =============================================================================

class InformationSource(BaseModel):
    """Source of information for Fog of War system."""
    source_id: str = Field(..., description="Information source identifier")
    source_type: str = Field(..., description="Type of information source")
    reliability: float = Field(..., ge=0.0, le=1.0, description="Source reliability factor")
    access_channels: List[FogOfWarChannel] = Field(..., description="Available information channels")
    range_modifiers: Dict[str, float] = Field(default_factory=dict, description="Channel-specific range modifiers")

class InformationFragment(BaseModel):
    """Piece of information with provenance and reliability."""
    fragment_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique fragment identifier")
    entity_id: str = Field(..., description="Entity this information is about")
    information_type: str = Field(..., description="Type of information")
    content: Dict[str, Any] = Field(..., description="Information content")
    source: InformationSource = Field(..., description="Information source")
    channel: FogOfWarChannel = Field(..., description="Information channel")
    timestamp: datetime = Field(default_factory=datetime.now, description="Information timestamp")
    accuracy: float = Field(default=1.0, ge=0.0, le=1.0, description="Information accuracy")
    freshness: float = Field(default=1.0, ge=0.0, le=1.0, description="Information recency factor")

class FogOfWarFilter(BaseModel):
    """Fog of War filtering configuration."""
    observer_id: str = Field(..., description="Character/entity observing")
    visual_range: float = Field(default=10.0, ge=0.0, description="Visual observation range")
    radio_range: float = Field(default=50.0, ge=0.0, description="Radio communication range")
    intel_range: float = Field(default=100.0, ge=0.0, description="Intelligence network range")
    sensor_range: float = Field(default=25.0, ge=0.0, description="Electronic sensor range")
    rumor_reliability: float = Field(default=0.3, ge=0.0, le=1.0, description="Rumor information reliability")
    channel_preferences: Dict[FogOfWarChannel, float] = Field(default_factory=dict, description="Channel weighting")

class FilteredWorldView(BaseModel):
    """World state as seen by a specific observer through Fog of War."""
    observer_id: str = Field(..., description="Observer character/entity")
    base_world_state: str = Field(..., description="Reference to base world state")
    visible_entities: Dict[str, WorldEntity] = Field(default_factory=dict, description="Entities visible to observer")
    known_information: List[InformationFragment] = Field(default_factory=list, description="Information available")
    uncertainty_markers: List[str] = Field(default_factory=list, description="Areas of uncertainty")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last filter update")
    filter_config: FogOfWarFilter = Field(..., description="Filter configuration used")

# =============================================================================
# Turn Brief and RAG Types
# =============================================================================

class KnowledgeFragment(BaseModel):
    """Piece of knowledge for RAG injection."""
    fragment_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique fragment identifier")
    content: str = Field(..., min_length=1, description="Knowledge content text")
    source: str = Field(..., description="Source of knowledge (file, database, etc.)")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance to current context")
    knowledge_type: str = Field(..., description="Type of knowledge (rule, fact, strategy, etc.)")
    tags: List[str] = Field(default_factory=list, description="Content tags for categorization")
    last_accessed: datetime = Field(default_factory=datetime.now, description="Last access timestamp")

class ContextualPrompt(BaseModel):
    """AI prompt with context injection."""
    base_prompt: str = Field(..., min_length=1, description="Base prompt template")
    character_context: str = Field(default="", description="Character-specific context")
    world_context: str = Field(default="", description="World state context")
    injected_knowledge: List[KnowledgeFragment] = Field(default_factory=list, description="RAG knowledge fragments")
    fog_of_war_mask: Optional[str] = Field(default=None, description="Information filtering mask")
    prompt_tokens: Optional[int] = Field(default=None, ge=0, description="Estimated token count")
    
    def compile_prompt(self) -> str:
        """Compile all components into final prompt."""
        components = [self.base_prompt]
        
        if self.character_context:
            components.append(f"\n## Character Context\n{self.character_context}")
        
        if self.world_context:
            components.append(f"\n## World State\n{self.world_context}")
        
        if self.injected_knowledge:
            knowledge_text = "\n".join(f"- {frag.content}" for frag in self.injected_knowledge)
            components.append(f"\n## Relevant Knowledge\n{knowledge_text}")
        
        if self.fog_of_war_mask:
            components.append(f"\n## Information Constraints\n{self.fog_of_war_mask}")
        
        return "\n".join(components)

class TurnBrief(BaseModel):
    """Complete briefing package for a character's turn."""
    character_id: str = Field(..., description="Character receiving the brief")
    turn_number: int = Field(..., ge=0, description="Current turn number")
    timestamp: datetime = Field(default_factory=datetime.now, description="Brief generation timestamp")
    filtered_world_view: FilteredWorldView = Field(..., description="Character's view of world state")
    available_actions: List[ActionType] = Field(..., description="Actions available to character")
    contextual_prompt: ContextualPrompt = Field(..., description="AI prompt with context")
    tactical_situation: str = Field(default="", description="Summary of tactical situation")
    objectives: List[str] = Field(default_factory=list, description="Current character objectives")
    constraints: List[str] = Field(default_factory=list, description="Action constraints")
    token_budget: Optional[int] = Field(default=None, ge=0, description="Token budget for AI processing")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "character_id": "char_001",
                "turn_number": 5,
                "tactical_situation": "Enemy forces advancing from the east",
                "objectives": ["Hold current position", "Maintain communication"],
                "constraints": ["Limited ammunition", "Maintain radio discipline"]
            }
        }
    )

# =============================================================================
# Simulation Control Types
# =============================================================================

class SimulationConfig(BaseModel):
    """Configuration parameters for simulation execution."""
    max_turns: int = Field(default=10, ge=1, le=100, description="Maximum simulation turns")
    turn_timeout: float = Field(default=30.0, gt=0.0, description="Per-turn timeout in seconds")
    max_agents: int = Field(default=20, ge=1, le=100, description="Maximum number of agents")
    iron_laws_enabled: bool = Field(default=True, description="Enable Iron Laws validation")
    fog_of_war_enabled: bool = Field(default=True, description="Enable Fog of War filtering")
    rag_injection_enabled: bool = Field(default=True, description="Enable RAG knowledge injection")
    performance_mode: Literal["accuracy", "balanced", "speed"] = Field(default="balanced")
    logging_level: Literal["debug", "info", "warning", "error"] = Field(default="info")

class SimulationState(BaseModel):
    """Current state of simulation execution."""
    simulation_id: str = Field(..., description="Unique simulation identifier")
    current_turn: int = Field(default=0, ge=0, description="Current turn number")
    phase: SimulationPhase = Field(default=SimulationPhase.INITIALIZATION, description="Current simulation phase")
    active_characters: List[str] = Field(default_factory=list, description="Active character IDs")
    world_state: WorldState = Field(..., description="Current world state")
    config: SimulationConfig = Field(..., description="Simulation configuration")
    start_time: datetime = Field(default_factory=datetime.now, description="Simulation start time")
    last_update: datetime = Field(default_factory=datetime.now, description="Last state update")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Simulation metrics")

class TurnResult(BaseModel):
    """Results of a completed simulation turn."""
    turn_number: int = Field(..., ge=0, description="Completed turn number")
    executed_actions: List[ValidatedAction] = Field(default_factory=list, description="Actions executed this turn")
    world_state_changes: Dict[str, Any] = Field(default_factory=dict, description="Changes to world state")
    character_updates: Dict[str, CharacterData] = Field(default_factory=dict, description="Updated character data")
    events_generated: List[str] = Field(default_factory=list, description="Events generated this turn")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Turn performance data")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during turn")
    warnings: List[str] = Field(default_factory=list, description="Warnings generated during turn")
    duration_seconds: float = Field(..., ge=0.0, description="Turn execution time")

# =============================================================================
# API and Communication Types
# =============================================================================

class APIResponse(BaseModel):
    """Standard API response format."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(default="", description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier for tracing")

class SystemStatus(BaseModel):
    """System health and status information."""
    system_name: str = Field(default="Novel Engine", description="System name")
    version: str = Field(default="1.0.0", description="System version")
    status: Literal["healthy", "degraded", "error", "offline"] = Field(..., description="Overall system status")
    uptime_seconds: float = Field(..., ge=0.0, description="System uptime in seconds")
    active_simulations: int = Field(default=0, ge=0, description="Number of active simulations")
    memory_usage_mb: Optional[float] = Field(default=None, ge=0.0, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="CPU usage percentage")
    last_error: Optional[str] = Field(default=None, description="Last error message")
    components: Dict[str, str] = Field(default_factory=dict, description="Component status")

# =============================================================================
# Caching and Performance Types
# =============================================================================

class CacheEntry(BaseModel):
    """Cache entry with metadata."""
    key: str = Field(..., description="Cache key")
    value: Any = Field(..., description="Cached value")
    created_at: datetime = Field(default_factory=datetime.now, description="Cache creation time")
    last_accessed: datetime = Field(default_factory=datetime.now, description="Last access time")
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")
    ttl_seconds: Optional[float] = Field(default=None, ge=0.0, description="Time to live in seconds")
    tags: List[str] = Field(default_factory=list, description="Cache entry tags")
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

class PerformanceMetrics(BaseModel):
    """Performance tracking metrics."""
    operation_name: str = Field(..., description="Name of operation being measured")
    duration_ms: float = Field(..., ge=0.0, description="Operation duration in milliseconds")
    memory_delta_mb: Optional[float] = Field(default=None, description="Memory usage change in MB")
    tokens_consumed: Optional[int] = Field(default=None, ge=0, description="AI tokens consumed")
    cache_hits: int = Field(default=0, ge=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, ge=0, description="Number of cache misses")
    error_count: int = Field(default=0, ge=0, description="Number of errors encountered")
    timestamp: datetime = Field(default_factory=datetime.now, description="Measurement timestamp")

# =============================================================================
# State Hashing and Consistency Types
# =============================================================================

class StateHash(BaseModel):
    """Hash representation of system state for consistency checks."""
    entity_id: str = Field(..., description="Entity being hashed")
    hash_type: str = Field(..., description="Type of hash (character, world, action)")
    hash_value: str = Field(..., min_length=32, max_length=128, description="Computed hash value")
    timestamp: datetime = Field(default_factory=datetime.now, description="Hash computation time")
    fields_included: List[str] = Field(..., description="Fields included in hash computation")
    salt: Optional[str] = Field(default=None, description="Salt used for hash computation")
    
    @field_validator('hash_value')
    @classmethod 
    def validate_hash_format(cls, v):
        """Validate hash value format."""
        import re
        if not re.match(r'^[a-fA-F0-9]{32,128}$', v):
            raise ValueError('Hash value must be a valid hexadecimal string')
        return v

class ConsistencyCheck(BaseModel):
    """Consistency validation results."""
    check_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique check identifier")
    entity_ids: List[str] = Field(..., description="Entities involved in consistency check")
    check_type: str = Field(..., description="Type of consistency check performed")
    is_consistent: bool = Field(..., description="Whether entities are consistent")
    inconsistencies: List[str] = Field(default_factory=list, description="Inconsistencies found")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in consistency check")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check execution time")
    remediation_suggestions: List[str] = Field(default_factory=list, description="Suggested fixes")

# =============================================================================
# Model Registry and Exports
# =============================================================================

# All models for easy importing
__all__ = [
    # Enums
    "ActionType", "EntityType", "ValidationResult", "FogOfWarChannel", "SimulationPhase",
    
    # Spatial Types
    "Position", "BoundingBox", "Area",
    
    # Resource Types  
    "ResourceValue", "Equipment",
    
    # Character Types
    "CharacterStats", "CharacterResources", "CharacterState", "CharacterData",
    
    # Action Types
    "ActionTarget", "ActionParameters", "ProposedAction", "ValidatedAction",
    
    # Iron Laws Types
    "IronLawsViolation", "IronLawsReport",
    
    # World Types
    "WorldEntity", "EnvironmentalCondition", "WorldState",
    
    # Fog of War Types
    "InformationSource", "InformationFragment", "FogOfWarFilter", "FilteredWorldView",
    
    # Turn Brief Types
    "KnowledgeFragment", "ContextualPrompt", "TurnBrief",
    
    # Simulation Types
    "SimulationConfig", "SimulationState", "TurnResult",
    
    # API Types
    "APIResponse", "SystemStatus",
    
    # Performance Types
    "CacheEntry", "PerformanceMetrics",
    
    # Consistency Types
    "StateHash", "ConsistencyCheck"
]

# Model validation registry for runtime type checking
MODEL_REGISTRY = {
    "character_data": CharacterData,
    "world_state": WorldState,
    "proposed_action": ProposedAction,
    "validated_action": ValidatedAction,
    "iron_laws_report": IronLawsReport,
    "turn_brief": TurnBrief,
    "simulation_state": SimulationState,
    "turn_result": TurnResult,
    "api_response": APIResponse
}