"""
Interaction Engine Core Types
=============================

Core data models, enums, and type definitions for the interaction engine system.
Provides foundational types used across all interaction engine components.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum

# Import enhanced systems
try:
    from src.core.data_models import (
        MemoryItem, CharacterState, CharacterInteraction, InteractionResult,
        StandardResponse, ErrorInfo, MemoryType, EmotionalState, EquipmentItem
    )
    from src.core.types import AgentID
except ImportError:
    # Fallback for testing
    MemoryItem = dict
    CharacterState = dict
    CharacterInteraction = dict
    InteractionResult = dict
    AgentID = str
    
    class StandardResponse:
        def __init__(self, success=True, data=None, error=None, metadata=None):
            self.success = success
            self.data = data or {}
            self.error = error
            self.metadata = metadata or {}
        
        def get(self, key, default=None):
            return getattr(self, key, default)
        
        def __getitem__(self, key):
            return getattr(self, key)
    
    class ErrorInfo:
        def __init__(self, code="", message="", recoverable=True):
            self.code = code
            self.message = message
            self.recoverable = recoverable
    
    class MemoryType(Enum):
        EPISODIC = "episodic"
        SEMANTIC = "semantic"
        PROCEDURAL = "procedural"
    
    class EmotionalState(Enum):
        CALM = "calm"
        EXCITED = "excited"
        ANGRY = "angry"
        FEARFUL = "fearful"

__all__ = [
    'InteractionType', 'InteractionPriority', 'InteractionContext',
    'InteractionPhase', 'InteractionOutcome', 'InteractionEngineConfig'
]


class InteractionType(Enum):
    """ENHANCED INTERACTION TYPES SANCTIFIED BY COMMUNICATION MODES"""
    DIALOGUE = "dialogue"                # Character-to-character conversation
    COMBAT = "combat"                    # Battle interactions
    COOPERATION = "cooperation"          # Collaborative activities
    NEGOTIATION = "negotiation"          # Diplomatic interactions
    INSTRUCTION = "instruction"          # Teaching/learning interactions
    RITUAL = "ritual"                    # Ceremonial interactions
    EXPLORATION = "exploration"          # Discovery and investigation
    MAINTENANCE = "maintenance"          # Equipment and system care
    EMERGENCY = "emergency"              # Crisis response interactions


class InteractionPriority(Enum):
    """STANDARD INTERACTION PRIORITIES ENHANCED BY URGENCY LEVELS"""
    CRITICAL = "critical"                # Immediate life-or-death situations
    URGENT = "urgent"                    # Time-sensitive but not critical
    HIGH = "high"                        # Important interactions
    NORMAL = "normal"                    # Standard interactions
    LOW = "low"                          # Background or optional interactions


@dataclass
class InteractionContext:
    """
    STANDARD INTERACTION CONTEXT ENHANCED BY COMPREHENSIVE AWARENESS
    
    Complete context information for interaction processing with
    environmental factors, participant states, and situational data.
    """
    interaction_id: str
    interaction_type: InteractionType
    priority: InteractionPriority = InteractionPriority.NORMAL
    participants: List[str] = field(default_factory=list)
    initiator: Optional[str] = None
    location: str = ""
    environment_state: Dict[str, Any] = field(default_factory=dict)
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionPhase:
    """
    ENHANCED INTERACTION PHASE SANCTIFIED BY STRUCTURED PROCESSING
    
    Individual phase of a complex interaction with specific objectives,
    processing requirements, and state transition conditions.
    """
    phase_id: str
    phase_name: str
    description: str = ""
    sequence_order: int = 0
    prerequisites: List[str] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    expected_duration: float = 0.0  # seconds
    success_criteria: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    state_requirements: Dict[str, Any] = field(default_factory=dict)
    resource_costs: Dict[str, float] = field(default_factory=dict)
    risk_assessment: float = 0.0  # 0.0-1.0
    completion_status: str = "pending"  # pending, active, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionOutcome:
    """
    ENHANCED INTERACTION OUTCOME SANCTIFIED BY COMPREHENSIVE RESULTS
    
    Complete outcome data from processed interaction including state changes,
    memory updates, and performance metrics.
    """
    interaction_id: str
    context: InteractionContext
    success: bool = True
    completion_time: datetime = field(default_factory=datetime.now)
    processing_duration: float = 0.0  # seconds
    
    # Phase results
    completed_phases: List[str] = field(default_factory=list)
    failed_phases: List[str] = field(default_factory=list)
    
    # State changes
    participant_state_changes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    environment_changes: Dict[str, Any] = field(default_factory=dict)
    
    # Memory updates
    generated_memories: List[MemoryItem] = field(default_factory=list)
    updated_relationships: Dict[str, float] = field(default_factory=dict)
    
    # Generated content
    interaction_content: Dict[str, Any] = field(default_factory=dict)
    dialogue_content: List[Dict[str, str]] = field(default_factory=list)
    
    # Performance metrics
    emotional_impact: Dict[str, float] = field(default_factory=dict)
    relationship_changes: Dict[str, float] = field(default_factory=dict)
    narrative_significance: float = 0.0
    
    # Error information
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    quality_score: float = 1.0
    template_usage: Dict[str, str] = field(default_factory=dict)
    processing_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionEngineConfig:
    """
    Interaction Engine Configuration
    
    Centralized configuration for interaction engine behavior and policies.
    """
    # Processing settings
    max_concurrent_interactions: int = 5
    default_timeout_seconds: float = 300.0  # 5 minutes
    enable_parallel_processing: bool = True
    
    # Queue management
    max_queue_size: int = 100
    priority_processing: bool = True
    auto_queue_cleanup: bool = True
    
    # Content generation
    enable_dynamic_templates: bool = True
    template_cache_size: int = 50
    content_quality_threshold: float = 0.7
    
    # Memory integration
    memory_integration_enabled: bool = True
    auto_generate_memories: bool = True
    memory_significance_threshold: float = 0.5
    
    # Performance settings
    performance_monitoring: bool = True
    detailed_logging: bool = True
    metrics_collection: bool = True
    
    # Validation settings
    strict_prerequisite_checking: bool = True
    validate_participant_states: bool = True
    enforce_resource_requirements: bool = True
    
    # Phase processing
    enable_phase_validation: bool = True
    allow_phase_skipping: bool = False
    phase_timeout_seconds: float = 60.0
    
    # Content settings
    max_dialogue_exchanges: int = 10
    dialogue_quality_threshold: float = 0.6
    enable_emotional_modeling: bool = True
    
    # Template settings
    template_directory: Optional[str] = None
    custom_template_loading: bool = True
    template_validation: bool = True
    
    # Database settings
    context_db_enabled: bool = True
    store_all_interactions: bool = True
    interaction_history_limit: int = 1000