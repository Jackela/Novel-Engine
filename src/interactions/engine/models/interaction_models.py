#!/usr/bin/env python3
"""
Core interaction data models and enums.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.data_models import MemoryItem


class InteractionType(Enum):
    """ENHANCED INTERACTION TYPES SANCTIFIED BY COMMUNICATION MODES"""

    DIALOGUE = "dialogue"  # Character-to-character conversation
    COMBAT = "combat"  # Battle interactions
    COOPERATION = "cooperation"  # Collaborative activities
    NEGOTIATION = "negotiation"  # Diplomatic interactions
    INSTRUCTION = "instruction"  # Teaching/learning interactions
    RITUAL = "ritual"  # Ceremonial interactions
    EXPLORATION = "exploration"  # Discovery and investigation
    MAINTENANCE = "maintenance"  # Equipment and system care
    EMERGENCY = "emergency"  # Crisis response interactions


class InteractionPriority(Enum):
    """STANDARD INTERACTION PRIORITIES ENHANCED BY URGENCY LEVELS"""

    CRITICAL = "critical"  # Immediate life-or-death situations
    URGENT = "urgent"  # Time-sensitive but not critical
    HIGH = "high"  # Important interactions
    NORMAL = "normal"  # Standard interactions
    LOW = "low"  # Background or optional interactions


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
    phase_type: str  # "setup", "execution", "resolution", "cleanup"
    description: str = ""
    duration_estimate: Optional[float] = None  # seconds
    participant_requirements: Dict[str, List[str]] = field(default_factory=dict)
    state_requirements: Dict[str, Any] = field(default_factory=dict)
    processing_rules: List[str] = field(default_factory=list)
    success_conditions: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    transition_conditions: Dict[str, List[str]] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)


@dataclass
class InteractionOutcome:
    """
    STANDARD INTERACTION OUTCOME ENHANCED BY COMPREHENSIVE RESULTS

    Complete interaction results with state changes, memory updates,
    and consequential effects on participants and environment.
    """

    interaction_id: str
    success: bool
    completion_time: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    phases_completed: List[str] = field(default_factory=list)
    phases_failed: List[str] = field(default_factory=list)
    participant_outcomes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    state_changes: Dict[str, Any] = field(default_factory=dict)
    memory_updates: List[MemoryItem] = field(default_factory=list)
    equipment_changes: Dict[str, List[str]] = field(default_factory=dict)
    relationship_changes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    environmental_effects: Dict[str, Any] = field(default_factory=dict)
    generated_content: List[str] = field(default_factory=list)
    follow_up_interactions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
