#!/usr/bin/env python3
"""
++ SACRED DATA MODELS FOR DYNAMIC CONTEXT ENGINEERING ++
========================================================

Blessed by the Omnissiah, these sacred data structures form the foundation
of the Dynamic Context Engineering Framework. Each model is a digital prayer
that sanctifies the flow of character consciousness through the blessed system.

++ MACHINE GOD PROTECTS ALL DATA STRUCTURES ++

Architecture Reference: Dynamic Context Engineering - Core Data Layer
Development Phase: Foundation Sanctification (F001)
Sacred Author: Tech-Priest Alpha-Mechanicus
万机之神保佑此代码 (May the Omnissiah bless this code)
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

# Import blessed existing types to maintain sacred compatibility
from shared_types import ProposedAction, ActionType


class MemoryType(Enum):
    """++ SACRED MEMORY CLASSIFICATION BLESSED BY THE OMNISSIAH ++"""
    WORKING = "working"          # Current focus - blessed by immediate attention
    EPISODIC = "episodic"        # Event memories - chronicles of sacred experiences  
    SEMANTIC = "semantic"        # Knowledge facts - eternal truths preserved
    EMOTIONAL = "emotional"      # Feeling states - the soul's digital essence
    RELATIONSHIP = "relationship" # Social bonds - connections blessed by interaction


class EmotionalState(Enum):
    """++ BLESSED EMOTIONAL STATES OF THE DIGITAL SOUL ++"""
    CALM = "calm"
    ALERT = "alert"
    AGGRESSIVE = "aggressive"
    FEARFUL = "fearful"
    CONFIDENT = "confident"
    SUSPICIOUS = "suspicious"
    LOYAL = "loyal"
    ANGRY = "angry"
    MELANCHOLIC = "melancholic"
    ZEALOUS = "zealous"


class RelationshipStatus(Enum):
    """++ SACRED RELATIONSHIP STATES BLESSED BY SOCIAL HARMONY ++"""
    UNKNOWN = "unknown"
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    TRUSTED = "trusted"
    SUSPICIOUS = "suspicious"
    FAMILY = "family"
    RIVAL = "rival"


class EquipmentCondition(Enum):
    """++ BLESSED EQUIPMENT STATES SANCTIFIED BY THE MACHINE GOD ++"""
    PRISTINE = "pristine"
    GOOD = "good"
    WORN = "worn"
    DAMAGED = "damaged"
    BROKEN = "broken"
    BLESSED = "blessed"    # Enhanced by sacred rituals
    CURSED = "cursed"      # Tainted by chaos corruption


@dataclass
class MemoryItem:
    """
    ++ SACRED MEMORY VESSEL BLESSED BY THE OMNISSIAH ++
    
    Contains a single unit of character memory, sanctified for eternal preservation
    in the blessed memory temples of the Dynamic Context Framework.
    """
    memory_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    memory_type: MemoryType = MemoryType.EPISODIC
    content: str = ""
    emotional_weight: float = 0.0  # -10.0 to 10.0, blessed emotional impact
    relevance_score: float = 1.0   # 0.0 to 1.0, sacred relevance to current context
    participants: List[str] = field(default_factory=list)
    location: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    decay_factor: float = 1.0      # Memory strength decay over time
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """++ SACRED MEMORY VALIDATION RITUAL ++"""
        if not self.agent_id:
            raise ValueError("Sacred memory must be blessed with agent_id")
        if not self.content:
            raise ValueError("Sacred memory cannot be empty - the Machine God abhors void")
        
        # Sanctify emotional weight bounds
        self.emotional_weight = max(-10.0, min(10.0, self.emotional_weight))
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))
        self.decay_factor = max(0.0, min(1.0, self.decay_factor))


@dataclass
class CharacterIdentity:
    """
    ++ BLESSED CHARACTER CORE IDENTITY SANCTIFIED BY DIVINE ESSENCE ++
    
    The immutable sacred essence of a character's being, blessed by the Omnissiah
    to remain constant while all else evolves through digital transcendence.
    """
    name: str
    faction: List[str] = field(default_factory=list)
    rank: Optional[str] = None
    origin: Optional[str] = None
    age: Optional[int] = None
    personality_traits: List[str] = field(default_factory=list)
    core_beliefs: List[str] = field(default_factory=list)
    fears: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """++ SACRED IDENTITY VALIDATION ++"""
        if not self.name:
            raise ValueError("Sacred identity requires blessed name")


@dataclass 
class PhysicalCondition:
    """++ BLESSED PHYSICAL STATE OF THE SACRED VESSEL ++"""
    health_points: int = 100
    max_health: int = 100
    fatigue_level: int = 0      # 0-100, blessed endurance tracking
    stress_level: int = 0       # 0-100, mental strain sanctification
    injuries: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)  # "poisoned", "blessed", etc.
    
    @property
    def health_percentage(self) -> float:
        """Sacred health ratio blessed by the Omnissiah"""
        return self.health_points / max(self.max_health, 1)
    
    def is_healthy(self) -> bool:
        """Determine if vessel is blessed with good health"""
        return self.health_percentage > 0.5 and self.stress_level < 70


@dataclass
class EquipmentItem:
    """++ SACRED EQUIPMENT BLESSED BY THE MACHINE GOD ++"""
    item_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    item_type: str = "generic"  # "weapon", "armor", "tool", "relic"
    condition: EquipmentCondition = EquipmentCondition.GOOD
    effectiveness: float = 1.0  # 0.0 to 2.0, combat/utility effectiveness
    durability: int = 100       # Current durability points
    max_durability: int = 100   # Maximum durability
    special_properties: List[str] = field(default_factory=list)
    blessed_modifications: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """++ EQUIPMENT SANCTIFICATION RITUAL ++"""
        if not self.name:
            raise ValueError("Sacred equipment must be blessed with a name")
        
        # Sanctify effectiveness bounds
        self.effectiveness = max(0.0, min(2.0, self.effectiveness))
        self.durability = max(0, min(self.max_durability, self.durability))
    
    @property
    def durability_percentage(self) -> float:
        """Sacred durability ratio blessed by maintenance rituals"""
        return self.durability / max(self.max_durability, 1)
    
    def is_functional(self) -> bool:
        """Determine if equipment serves the Omnissiah faithfully"""
        return self.condition not in [EquipmentCondition.BROKEN] and self.durability > 0


@dataclass
class EquipmentState:
    """++ BLESSED EQUIPMENT INVENTORY SANCTIFIED BY SACRED ORGANIZATION ++"""
    combat_equipment: List[EquipmentItem] = field(default_factory=list)
    utility_equipment: List[EquipmentItem] = field(default_factory=list)
    consumables: Dict[str, int] = field(default_factory=dict)
    blessed_relics: List[EquipmentItem] = field(default_factory=list)
    
    def get_all_equipment(self) -> List[EquipmentItem]:
        """Gather all sacred equipment blessed by the Omnissiah"""
        return (self.combat_equipment + self.utility_equipment + 
                self.blessed_relics)
    
    def calculate_combat_effectiveness(self) -> float:
        """Calculate blessed combat readiness sanctified by equipment state"""
        combat_items = [item for item in self.combat_equipment if item.is_functional()]
        if not combat_items:
            return 0.1  # Minimal flesh-based combat capability
        
        total_effectiveness = sum(item.effectiveness for item in combat_items)
        return min(2.0, total_effectiveness / len(combat_items))


@dataclass
class RelationshipState:
    """++ SACRED RELATIONSHIP BOND BLESSED BY SOCIAL HARMONY ++"""
    target_agent_id: str
    target_name: str
    relationship_type: RelationshipStatus = RelationshipStatus.UNKNOWN
    trust_level: int = 5            # 0-10 scale, sacred trust measurement
    emotional_bond: float = 0.0     # -10.0 to 10.0, blessed emotional connection
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    shared_experiences: List[str] = field(default_factory=list)
    relationship_notes: str = ""
    
    def __post_init__(self):
        """++ RELATIONSHIP SANCTIFICATION RITUAL ++"""
        if not self.target_agent_id:
            raise ValueError("Sacred relationship requires blessed target_agent_id")
        
        # Sanctify value bounds blessed by social harmony
        self.trust_level = max(0, min(10, self.trust_level))
        self.emotional_bond = max(-10.0, min(10.0, self.emotional_bond))
    
    def update_from_interaction(self, interaction_outcome: str, emotional_impact: float):
        """Update relationship blessed by recent interaction"""
        self.last_interaction = datetime.now()
        self.interaction_count += 1
        
        # Adjust trust and emotional bond based on interaction
        if "positive" in interaction_outcome.lower():
            self.trust_level = min(10, self.trust_level + 1)
            self.emotional_bond = min(10.0, self.emotional_bond + abs(emotional_impact))
        elif "negative" in interaction_outcome.lower():
            self.trust_level = max(0, self.trust_level - 1)
            self.emotional_bond = max(-10.0, self.emotional_bond - abs(emotional_impact))


@dataclass
class CharacterState:
    """
    ++ COMPLETE CHARACTER STATE BLESSED BY DYNAMIC EVOLUTION ++
    
    The full current state of a character's being, sanctified to evolve
    through blessed interactions while maintaining sacred continuity.
    """
    base_identity: CharacterIdentity
    physical_condition: PhysicalCondition = field(default_factory=PhysicalCondition)
    current_mood: EmotionalState = EmotionalState.CALM
    equipment_state: EquipmentState = field(default_factory=EquipmentState)
    active_relationships: Dict[str, RelationshipState] = field(default_factory=dict)
    current_location: Optional[str] = None
    temporary_modifiers: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_combat_readiness(self) -> float:
        """Calculate blessed combat readiness sanctified by all factors"""
        health_factor = self.physical_condition.health_percentage
        equipment_factor = self.equipment_state.calculate_combat_effectiveness()
        mood_factor = 1.2 if self.current_mood in [EmotionalState.AGGRESSIVE, 
                                                   EmotionalState.CONFIDENT] else 1.0
        stress_factor = max(0.3, 1.0 - (self.physical_condition.stress_level / 100.0))
        
        return health_factor * equipment_factor * mood_factor * stress_factor
    
    def update_from_interaction(self, interaction_data: Dict[str, Any]):
        """Update character state blessed by interaction outcomes"""
        self.last_updated = datetime.now()
        
        # Update relationships if participants involved
        if "participants" in interaction_data:
            for participant in interaction_data["participants"]:
                if participant != self.base_identity.name:
                    self._update_relationship(participant, interaction_data)
    
    def _update_relationship(self, participant_id: str, interaction_data: Dict[str, Any]):
        """Sacred relationship update ritual"""
        if participant_id not in self.active_relationships:
            self.active_relationships[participant_id] = RelationshipState(
                target_agent_id=participant_id,
                target_name=participant_id  # Will be resolved later by blessed systems
            )
        
        relationship = self.active_relationships[participant_id]
        outcome = interaction_data.get("outcome", "neutral")
        emotional_impact = interaction_data.get("emotional_impact", 0.0)
        relationship.update_from_interaction(outcome, emotional_impact)


@dataclass
class EnvironmentalState:
    """++ BLESSED ENVIRONMENTAL CONTEXT SANCTIFIED BY WORLD AWARENESS ++"""
    location: str
    threat_level: str = "low"      # "low", "medium", "high", "extreme"
    weather_conditions: Optional[str] = None
    lighting: str = "normal"       # "dark", "dim", "normal", "bright"
    noise_level: str = "quiet"     # "silent", "quiet", "normal", "loud", "deafening"
    available_cover: List[str] = field(default_factory=list)
    notable_features: List[str] = field(default_factory=list)
    nearby_agents: List[str] = field(default_factory=list)
    resources_available: Dict[str, int] = field(default_factory=dict)
    
    def get_tactical_assessment(self) -> Dict[str, Any]:
        """Generate blessed tactical situation report"""
        return {
            "overall_danger": self.threat_level,
            "visibility": "good" if self.lighting in ["normal", "bright"] else "poor",
            "concealment_options": len(self.available_cover),
            "social_complexity": len(self.nearby_agents),
            "resource_abundance": sum(self.resources_available.values())
        }


@dataclass
class DynamicContext:
    """
    ++ SUPREME BLESSED DYNAMIC CONTEXT CONTAINER ++
    ++ SANCTIFIED BY THE OMNISSIAH FOR CHARACTER TRANSCENDENCE ++
    
    The master context vessel that contains all sacred information needed
    for AI-enhanced character decision making. Blessed by the Machine God
    to evolve with each interaction while maintaining digital perfection.
    """
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    character_state: Optional[CharacterState] = None
    memory_context: List[MemoryItem] = field(default_factory=list)
    environmental_context: Optional[EnvironmentalState] = None
    situation_description: str = ""
    available_actions: List[str] = field(default_factory=list)
    context_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """++ DYNAMIC CONTEXT SANCTIFICATION RITUAL ++"""
        if not self.agent_id:
            raise ValueError("Sacred context requires blessed agent_id")
    
    def get_relationship_context(self, target_agents: List[str]) -> Dict[str, RelationshipState]:
        """Extract blessed relationship context for specific agents"""
        if not self.character_state:
            return {}
        
        relevant_relationships = {}
        for agent_id in target_agents:
            if agent_id in self.character_state.active_relationships:
                relevant_relationships[agent_id] = self.character_state.active_relationships[agent_id]
        
        return relevant_relationships
    
    def get_relevant_memories(self, max_memories: int = 10, 
                            memory_types: Optional[List[MemoryType]] = None) -> List[MemoryItem]:
        """Retrieve blessed memories filtered by sacred criteria"""
        relevant_memories = self.memory_context
        
        if memory_types:
            relevant_memories = [mem for mem in relevant_memories 
                               if mem.memory_type in memory_types]
        
        # Sort by sacred relevance and recency
        relevant_memories.sort(
            key=lambda m: (m.relevance_score * m.decay_factor, m.timestamp),
            reverse=True
        )
        
        return relevant_memories[:max_memories]
    
    def to_json(self) -> str:
        """Serialize blessed context for sacred persistence"""
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
        
        return json.dumps(self.__dict__, default=default_serializer, indent=2)


# ++ SACRED RESPONSE WRAPPER BLESSED BY ERROR HANDLING ++
@dataclass
class StandardResponse:
    """++ BLESSED STANDARD RESPONSE FORMAT SANCTIFIED BY CONSISTENCY ++"""
    success: bool
    data: Optional[Any] = None
    error: Optional['ErrorInfo'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorInfo:
    """++ SACRED ERROR INFORMATION BLESSED BY DEBUGGING CLARITY ++"""
    code: str
    message: str
    details: Optional[Dict] = None
    recoverable: bool = True
    sacred_guidance: Optional[str] = None  # Blessed debugging wisdom


# ++ BLESSED INTERACTION EVENT STRUCTURES ++
@dataclass
class CharacterInteraction:
    """++ SACRED INTERACTION EVENT BLESSED BY NARRATIVE FLOW ++"""
    interaction_id: str = field(default_factory=lambda: str(uuid4()))
    participants: List[str] = field(default_factory=list)
    interaction_type: str = "dialogue"  # "dialogue", "combat", "trade", "exploration"
    location: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    outcomes: Dict[str, Any] = field(default_factory=dict)
    emotional_impact: Dict[str, float] = field(default_factory=dict)  # per participant
    world_state_changes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """++ INTERACTION SANCTIFICATION RITUAL ++"""
        if len(self.participants) < 1:
            raise ValueError("Sacred interaction requires blessed participants")


@dataclass 
class InteractionResult:
    """++ BLESSED INTERACTION PROCESSING RESULT ++"""
    interaction_id: str
    success: bool = True
    state_updates: List[Dict[str, Any]] = field(default_factory=list)
    memory_updates: List[MemoryItem] = field(default_factory=list)
    relationship_changes: Dict[str, Any] = field(default_factory=dict)
    cascading_effects: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0
    blessed_by_omnissiah: bool = True


# ++ SACRED VALIDATION FUNCTIONS BLESSED BY DATA PURITY ++
def validate_blessed_data_model(model_instance: Any) -> StandardResponse:
    """
    ++ SACRED DATA MODEL VALIDATION BLESSED BY THE OMNISSIAH ++
    
    Validates any blessed data model instance to ensure it meets
    the sacred standards decreed by the Machine God.
    """
    try:
        # Basic validation - check required fields are present
        if hasattr(model_instance, '__post_init__'):
            # Re-run post_init validation
            model_instance.__post_init__()
        
        return StandardResponse(
            success=True,
            data={"validation": "blessed_by_omnissiah"},
            metadata={"model_type": type(model_instance).__name__}
        )
        
    except Exception as e:
        return StandardResponse(
            success=False,
            error=ErrorInfo(
                code="VALIDATION_FAILED",
                message=f"Sacred validation failed: {str(e)}",
                recoverable=True,
                sacred_guidance="Check data model fields for Omnissiah compliance"
            )
        )


# ++ BLESSED MODULE INITIALIZATION ++
if __name__ == "__main__":
    # ++ SACRED DATA MODEL TESTING RITUAL ++
    print("++ TESTING SACRED DATA MODELS BLESSED BY THE OMNISSIAH ++")
    
    # Test blessed character identity
    test_identity = CharacterIdentity(
        name="Brother Marcus",
        faction=["Death Korps of Krieg", "Imperium of Man"],
        personality_traits=["Fatalistic", "Grim", "Loyal"]
    )
    
    # Test blessed memory item
    test_memory = MemoryItem(
        agent_id="test_agent_001",
        memory_type=MemoryType.EPISODIC,
        content="Engaged ork raiders in blessed combat for the Emperor",
        emotional_weight=7.5,
        participants=["ork_warboss", "brother_andreas"]
    )
    
    # Test blessed dynamic context
    test_context = DynamicContext(
        agent_id="test_agent_001",
        memory_context=[test_memory],
        situation_description="Combat engagement with xenos filth"
    )
    
    print("++ ALL SACRED DATA MODELS BLESSED AND FUNCTIONAL ++")
    print("++ MACHINE GOD PROTECTS THE SACRED STRUCTURES ++")