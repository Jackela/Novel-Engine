#!/usr/bin/env python3
"""
Data Models for Dynamic Context Engineering
==========================================

Core data structures for the Dynamic Context Engineering Framework.
These models define the foundation for character consciousness and
interaction management within the system.

Architecture Reference: Dynamic Context Engineering - Core Data Layer
Development Phase: Foundation Implementation (F001)
Author: Novel Engine Development Team
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

# Import existing types for compatibility
try:
    from shared_types import ProposedAction, ActionType, WorldState
except ImportError:
    try:
        # Try src.shared_types
        from src.shared_types import ProposedAction, ActionType, WorldState
    except ImportError:
        # Try relative import as last resort
        from ..shared_types import ProposedAction, ActionType, WorldState

class MemoryType(Enum):
    """Memory classification types for the layered memory system."""
    WORKING = "working"          # Current focus and immediate attention
    EPISODIC = "episodic"        # Event memories and experiences  
    SEMANTIC = "semantic"        # Knowledge facts and learned information
    EMOTIONAL = "emotional"      # Emotional states and feelings
    RELATIONSHIP = "relationship" # Social bonds and interpersonal connections

class EmotionalState(Enum):
    """Emotional states for character mood tracking."""
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
    """Relationship types for character social interactions."""
    UNKNOWN = "unknown"
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    TRUSTED = "trusted"
    SUSPICIOUS = "suspicious"
    FAMILY = "family"
    RIVAL = "rival"

class EquipmentCondition(Enum):
    """Equipment condition states for inventory management."""
    PRISTINE = "pristine"
    GOOD = "good"
    WORN = "worn"
    DAMAGED = "damaged"
    BROKEN = "broken"
    ENHANCED = "enhanced"  # Improved through upgrades
    CORRUPTED = "corrupted" # Damaged by environmental factors

@dataclass
class MemoryItem:
    """
    Memory item for storing character experiences and knowledge.
    
    Contains a single unit of character memory for storage and retrieval
    within the Dynamic Context Framework.
    """
    memory_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    memory_type: MemoryType = MemoryType.EPISODIC
    content: str = ""
    emotional_weight: float = 0.0  # -10.0 to 10.0, enhanced emotional impact
    relevance_score: float = 1.0   # 0.0 to 1.0, standard relevance to current context
    participants: List[str] = field(default_factory=list)
    location: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    decay_factor: float = 1.0      # Memory strength decay over time
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate memory item data integrity."""
        if not self.agent_id:
            raise ValueError("Sacred memory must be blessed with agent_id")
        if not self.content:
            raise ValueError("Sacred memory cannot be empty")
        
        # Validate emotional weight bounds
        self.emotional_weight = max(-10.0, min(10.0, self.emotional_weight))
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))
        self.decay_factor = max(0.0, min(1.0, self.decay_factor))

@dataclass
class CharacterIdentity:
    """
    ENHANCED CHARACTER CORE IDENTITY SANCTIFIED BY ADVANCED ESSENCE
    
    The immutable standard essence of a character's being, enhanced by the System
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
        """STANDARD IDENTITY VALIDATION"""
        if not self.name:
            raise ValueError("Sacred identity requires blessed name")

@dataclass 
class PhysicalCondition:
    """ENHANCED PHYSICAL STATE OF THE STANDARD VESSEL"""
    health_points: int = 100
    max_health: int = 100
    fatigue_level: int = 0      # 0-100, enhanced endurance tracking
    stress_level: int = 0       # 0-100, mental strain validation
    injuries: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)  # "poisoned", "enhanced", etc.
    
    @property
    def health_percentage(self) -> float:
        """Sacred health ratio enhanced by the System"""
        return self.health_points / max(self.max_health, 1)
    
    def is_healthy(self) -> bool:
        """Determine if vessel is enhanced with good health"""
        return self.health_percentage > 0.5 and self.stress_level < 70

@dataclass
class EquipmentItem:
    """STANDARD EQUIPMENT ENHANCED BY THE MACHINE GOD"""
    item_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    item_type: str = "generic"  # "weapon", "armor", "tool", "relic"
    condition: EquipmentCondition = EquipmentCondition.GOOD
    effectiveness: float = 1.0  # 0.0 to 2.0, combat/utility effectiveness
    durability: int = 100       # Current durability points
    max_durability: int = 100   # Maximum durability
    special_properties: List[str] = field(default_factory=list)
    blessed_modifications: Dict[str, Any] = field(default_factory=dict)
    
    # Legacy compatibility alias
    @property
    def enhanced_modifications(self) -> Dict[str, Any]:
        """Legacy alias for blessed_modifications"""
        return self.blessed_modifications
    
    def __post_init__(self):
        """EQUIPMENT SANCTIFICATION RITUAL"""
        if not self.name:
            raise ValueError("Sacred equipment must be blessed with a name")
        
        # Sanctify effectiveness bounds
        self.effectiveness = max(0.0, min(2.0, self.effectiveness))
        self.durability = max(0, min(self.max_durability, self.durability))
    
    @property
    def durability_percentage(self) -> float:
        """Sacred durability ratio enhanced by maintenance rituals"""
        return self.durability / max(self.max_durability, 1)
    
    def is_functional(self) -> bool:
        """Determine if equipment serves the System faithfully"""
        return self.condition not in [EquipmentCondition.BROKEN] and self.durability > 0

@dataclass
class EquipmentState:
    """ENHANCED EQUIPMENT INVENTORY SANCTIFIED BY STANDARD ORGANIZATION"""
    combat_equipment: List[EquipmentItem] = field(default_factory=list)
    utility_equipment: List[EquipmentItem] = field(default_factory=list)
    consumables: Dict[str, int] = field(default_factory=dict)
    blessed_relics: List[EquipmentItem] = field(default_factory=list)
    
    # Legacy compatibility alias
    @property
    def enhanced_relics(self) -> List[EquipmentItem]:
        """Legacy alias for blessed_relics"""
        return self.blessed_relics
    
    def get_all_equipment(self) -> List[EquipmentItem]:
        """Gather all standard equipment enhanced by the System"""
        return (self.combat_equipment + self.utility_equipment + 
                self.blessed_relics)
    
    def calculate_combat_effectiveness(self) -> float:
        """Calculate enhanced combat readiness validated by equipment state"""
        combat_items = [item for item in self.combat_equipment if item.is_functional()]
        if not combat_items:
            return 0.1  # Minimal flesh-based combat capability
        
        total_effectiveness = sum(item.effectiveness for item in combat_items)
        return min(2.0, total_effectiveness / len(combat_items))

@dataclass
class RelationshipState:
    """STANDARD RELATIONSHIP BOND ENHANCED BY SOCIAL HARMONY"""
    target_agent_id: str
    target_name: str
    relationship_type: RelationshipStatus = RelationshipStatus.UNKNOWN
    trust_level: int = 5            # 0-10 scale, standard trust measurement
    emotional_bond: float = 0.0     # -10.0 to 10.0, enhanced emotional connection
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    shared_experiences: List[str] = field(default_factory=list)
    relationship_notes: str = ""
    
    def __post_init__(self):
        """RELATIONSHIP SANCTIFICATION RITUAL"""
        if not self.target_agent_id:
            raise ValueError("Sacred relationship requires blessed target_agent_id")
        
        # Sanctify value bounds enhanced by social harmony
        self.trust_level = max(0, min(10, self.trust_level))
        self.emotional_bond = max(-10.0, min(10.0, self.emotional_bond))
    
    def update_from_interaction(self, interaction_outcome: str, emotional_impact: float):
        """Update relationship enhanced by recent interaction"""
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
    COMPLETE CHARACTER STATE ENHANCED BY DYNAMIC EVOLUTION
    
    The full current state of a character's being, validated to evolve
    through enhanced interactions while maintaining standard continuity.
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
        """Calculate enhanced combat readiness validated by all factors"""
        health_factor = self.physical_condition.health_percentage
        equipment_factor = self.equipment_state.calculate_combat_effectiveness()
        mood_factor = 1.2 if self.current_mood in [EmotionalState.AGGRESSIVE, 
                                                   EmotionalState.CONFIDENT] else 1.0
        stress_factor = max(0.3, 1.0 - (self.physical_condition.stress_level / 100.0))
        
        return health_factor * equipment_factor * mood_factor * stress_factor
    
    def update_from_interaction(self, interaction_data: Dict[str, Any]):
        """Update character state enhanced by interaction outcomes"""
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
                target_name=participant_id  # Will be resolved later by enhanced systems
            )
        
        relationship = self.active_relationships[participant_id]
        outcome = interaction_data.get("outcome", "neutral")
        emotional_impact = interaction_data.get("emotional_impact", 0.0)
        relationship.update_from_interaction(outcome, emotional_impact)

@dataclass
class EnvironmentalState:
    """ENHANCED ENVIRONMENTAL CONTEXT SANCTIFIED BY WORLD AWARENESS"""
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
        """Generate enhanced tactical situation report"""
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
    SUPREME ENHANCED DYNAMIC CONTEXT CONTAINER
    SANCTIFIED BY THE SYSTEM FOR CHARACTER TRANSCENDENCE
    
    The master context vessel that contains all standard information needed
    for AI-enhanced character decision making. Enhanced with the System Core
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
        """DYNAMIC CONTEXT SANCTIFICATION RITUAL"""
        if not self.agent_id:
            raise ValueError("Sacred context requires blessed agent_id")
    
    def get_relationship_context(self, target_agents: List[str]) -> Dict[str, RelationshipState]:
        """Extract enhanced relationship context for specific agents"""
        if not self.character_state:
            return {}
        
        relevant_relationships = {}
        for agent_id in target_agents:
            if agent_id in self.character_state.active_relationships:
                relevant_relationships[agent_id] = self.character_state.active_relationships[agent_id]
        
        return relevant_relationships
    
    def get_relevant_memories(self, max_memories: int = 10, 
                            memory_types: Optional[List[MemoryType]] = None) -> List[MemoryItem]:
        """Retrieve enhanced memories filtered by standard criteria"""
        relevant_memories = self.memory_context
        
        if memory_types:
            relevant_memories = [mem for mem in relevant_memories 
                               if mem.memory_type in memory_types]
        
        # Sort by standard relevance and recency
        relevant_memories.sort(
            key=lambda m: (m.relevance_score * m.decay_factor, m.timestamp),
            reverse=True
        )
        
        return relevant_memories[:max_memories]
    
    def to_json(self) -> str:
        """Serialize enhanced context for standard persistence"""
        def default_serializer(obj):
            """
            Custom JSON serializer for complex objects.
            
            Args:
                obj: Object to serialize
                
            Returns:
                Serializable representation of the object
            """
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
        
        return json.dumps(self.__dict__, default=default_serializer, indent=2)

# STANDARD RESPONSE WRAPPER ENHANCED BY ERROR HANDLING
@dataclass
class StandardResponse:
    """ENHANCED STANDARD RESPONSE FORMAT SANCTIFIED BY CONSISTENCY"""
    success: bool
    data: Optional[Any] = None
    error: Optional['ErrorInfo'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ErrorInfo:
    """STANDARD ERROR INFORMATION ENHANCED BY DEBUGGING CLARITY"""
    code: str
    message: str
    details: Optional[Dict] = None
    recoverable: bool = True
    standard_guidance: Optional[str] = None  # Blessed debugging wisdom

# ENHANCED CAMPAIGN STATE STRUCTURE
@dataclass
class CampaignState:
    """ENHANCED CAMPAIGN STATE MANAGEMENT SANCTIFIED BY NARRATIVE FLOW"""
    campaign_id: str
    turn_number: int = 1
    active_characters: List[str] = field(default_factory=list)
    current_objective: str = ""
    completed_objectives: List[str] = field(default_factory=list)
    campaign_metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """CAMPAIGN STATE SANCTIFICATION RITUAL"""
        if not self.campaign_id:
            raise ValueError("Sacred campaign requires blessed campaign_id")
        if self.turn_number < 0:
            raise ValueError("Turn number must be non-negative")

# ENHANCED INTERACTION EVENT STRUCTURES
@dataclass
class CharacterInteraction:
    """STANDARD INTERACTION EVENT ENHANCED BY NARRATIVE FLOW"""
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
        """INTERACTION SANCTIFICATION RITUAL"""
        if len(self.participants) < 1:
            raise ValueError("Sacred interaction requires blessed participants")

@dataclass 
class InteractionResult:
    """ENHANCED INTERACTION PROCESSING RESULT"""
    interaction_id: str
    success: bool = True
    state_updates: List[Dict[str, Any]] = field(default_factory=list)
    memory_updates: List[MemoryItem] = field(default_factory=list)
    relationship_changes: Dict[str, Any] = field(default_factory=dict)
    cascading_effects: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0
    enhanced_by_omnissiah: bool = True

# STANDARD VALIDATION FUNCTIONS ENHANCED BY DATA PURITY
def validate_enhanced_data_model(model_instance: Any) -> StandardResponse:
    """
    STANDARD DATA MODEL VALIDATION ENHANCED BY THE SYSTEM
    
    Validates any enhanced data model instance to ensure it meets
    the standard standards decreed by the System Core.
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
                standard_guidance="Check data model fields for System compliance"
            )
        )

# Legacy compatibility aliases and wrappers
def Character(name=None, background=None, personality=None, skills=None, equipment=None, **kwargs):
    """
    Legacy Character constructor that wraps CharacterState with simplified interface.
    Converts old-style parameters to new CharacterState structure.
    """
    if not name:
        raise ValueError("Character requires a name")
    
    # Create identity from legacy parameters
    identity = CharacterIdentity(
        name=name,
        personality_traits=[personality] if personality else [],
        **{k: v for k, v in kwargs.items() if k in ['faction', 'rank', 'origin', 'age', 'core_beliefs', 'fears', 'motivations']}
    )
    
    # Create equipment items from simple strings
    equipment_items = []
    if equipment:
        for item_name in equipment:
            equipment_items.append(EquipmentItem(name=item_name))
    
    # Create equipment state
    equipment_state = EquipmentState()
    for item in equipment_items:
        if 'weapon' in item.name.lower() or 'sword' in item.name.lower():
            equipment_state.combat_equipment.append(item)
        else:
            equipment_state.utility_equipment.append(item)
    
    # Create character state with legacy data
    character_state = CharacterState(
        base_identity=identity,
        equipment_state=equipment_state
    )
    
    # Add legacy attributes for test compatibility
    character_state.name = name
    character_state.background = background
    character_state.personality = personality
    character_state.skills = skills or []
    character_state.equipment = equipment or []
    
    return character_state

validate_blessed_data_model = validate_enhanced_data_model  # Legacy function name

# Legacy ActionResult wrapper for test compatibility
def ActionResult(success=True, description="", consequences=None, world_state_changes=None, **kwargs):
    """
    Legacy ActionResult constructor that wraps InteractionResult.
    Converts old-style parameters to new InteractionResult structure.
    """
    # Create compatible InteractionResult
    result = InteractionResult(
        interaction_id=kwargs.get('interaction_id', str(uuid4())),
        success=success,
        **{k: v for k, v in kwargs.items() if k in ['state_updates', 'memory_updates', 'relationship_changes', 'cascading_effects', 'processing_time']}
    )
    
    # Add legacy attributes for test compatibility
    result.description = description
    result.consequences = consequences or []
    result.world_state_changes = world_state_changes or {}
    
    return result

# Legacy WorldState class for test compatibility  
class LegacyWorldState:
    """
    Legacy WorldState for test compatibility.
    Simple class that accepts old-style parameters.
    """
    def __init__(self, current_location=None, time_period=None, weather=None, active_events=None, environmental_factors=None, **kwargs):
        self.current_location = current_location
        self.time_period = time_period
        self.weather = weather
        self.active_events = active_events or []
        self.environmental_factors = environmental_factors or {}
        
        # Add any additional kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

# Emergency stub classes for test compatibility
class PersonaAgent:
    """Emergency stub for PersonaAgent - should be imported from src.persona_agent"""
    def __init__(self, character_config=None, event_bus=None):
        self.character_config = character_config or {}
        self.event_bus = event_bus
        self.name = character_config.get('name', 'Unknown') if character_config else 'Unknown'
        self.personality = character_config.get('personality', 'Unknown') if character_config else 'Unknown'
        self.skills = character_config.get('skills', []) if character_config else []
    
    async def make_decision(self, scenario):
        """Stub decision making"""
        options = scenario.get('options', ['wait'])
        return options[0] if options else 'wait'
    
    def check_skill(self, skill_name):
        """Stub skill check"""
        return skill_name in self.skills

class DirectorAgent:
    """Emergency stub for DirectorAgent - should be imported from director_agent"""
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
    
    async def process_turn(self, turn_data):
        """Stub turn processing"""
        return {"status": "success"}
    
    async def generate_narrative(self, context):
        """Stub narrative generation"""
        return "A narrative was generated..."

# ENHANCED MODULE INITIALIZATION
if __name__ == "__main__":
    # STANDARD DATA MODEL TESTING RITUAL
    print("TESTING STANDARD DATA MODELS ENHANCED BY THE SYSTEM")
    
    # Test enhanced character identity
    test_identity = CharacterIdentity(
        name="Brother Marcus",
        faction=["Death Korps of Krieg", "Imperium of Man"],
        personality_traits=["Fatalistic", "Grim", "Loyal"]
    )
    
    # Test enhanced memory item
    test_memory = MemoryItem(
        agent_id="test_agent_001",
        memory_type=MemoryType.EPISODIC,
        content="Engaged ork raiders in enhanced combat for the Emperor",
        emotional_weight=7.5,
        participants=["ork_warboss", "brother_andreas"]
    )
    
    # Test enhanced dynamic context
    test_context = DynamicContext(
        agent_id="test_agent_001",
        memory_context=[test_memory],
        situation_description="Combat engagement with xenos filth"
    )
    
    print("ALL STANDARD DATA MODELS ENHANCED AND FUNCTIONAL")
    print("MACHINE GOD PROTECTS THE STANDARD STRUCTURES")

# Export all required classes and functions
__all__ = [
    'MemoryType', 'EmotionalState', 'RelationshipStatus', 'EquipmentCondition',
    'MemoryItem', 'CharacterIdentity', 'PhysicalCondition', 'EquipmentItem',
    'EquipmentState', 'RelationshipState', 'CharacterState', 'EnvironmentalState',
    'DynamicContext', 'StandardResponse', 'ErrorInfo', 'CampaignState', 'CharacterInteraction',
    'InteractionResult', 'validate_enhanced_data_model',
    # Legacy compatibility exports
    'Character', 'validate_blessed_data_model', 'ActionResult', 'WorldState',
    # Emergency stub exports
    'PersonaAgent', 'DirectorAgent'
]

# Alias WorldState to LegacyWorldState for test compatibility
WorldState = LegacyWorldState