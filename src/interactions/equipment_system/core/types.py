"""
Equipment System Core Types
===========================

Core data models, enums, and type definitions for the dynamic equipment system.
Provides foundational types used across all equipment system components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

# Import enhanced core systems
try:
    from src.core.data_models import (
        EquipmentCondition,
        EquipmentItem,
    )
except ImportError:
    # Fallback for testing
    EquipmentItem = dict

    class EquipmentCondition(Enum):
        EXCELLENT = "excellent"
        GOOD = "good"
        FAIR = "fair"
        POOR = "poor"
        DAMAGED = "damaged"
        BROKEN = "broken"


__all__ = [
    "EquipmentCategory",
    "EquipmentStatus",
    "EquipmentModification",
    "EquipmentMaintenance",
    "DynamicEquipment",
    "EquipmentSystemConfig",
]


class EquipmentCategory(Enum):
    """ENHANCED EQUIPMENT CATEGORIES SANCTIFIED BY CLASSIFICATION"""

    WEAPON = "weapon"  # Combat weapons and armaments
    ARMOR = "armor"  # Protective equipment and shields
    TOOL = "tool"  # Utility and maintenance tools
    CONSUMABLE = "consumable"  # Ammunition, supplies, consumables
    AUGMETIC = "augmetic"  # Cybernetic enhancements
    RELIC = "relic"  # Sacred artifacts and relics
    TRANSPORT = "transport"  # Vehicles and transport
    COMMUNICATION = "communication"  # Vox systems and communication gear
    MEDICAL = "medical"  # Medical and healing equipment
    SENSOR = "sensor"  # Detection and scanning equipment


class EquipmentStatus(Enum):
    """STANDARD EQUIPMENT STATUS ENHANCED BY OPERATIONAL STATES"""

    ACTIVE = "active"  # Currently in use
    READY = "ready"  # Ready for immediate use
    STANDBY = "standby"  # Available but not active
    MAINTENANCE = "maintenance"  # Under maintenance or repair
    DAMAGED = "damaged"  # Damaged but potentially repairable
    DESTROYED = "destroyed"  # Beyond repair, non-functional
    MISSING = "missing"  # Lost or unaccounted for
    STORED = "stored"  # In storage, not immediately available


@dataclass
class EquipmentModification:
    """
    ENHANCED EQUIPMENT MODIFICATION SANCTIFIED BY ENHANCEMENT

    Equipment enhancement or modification record with technical
    specifications and performance impacts.
    """

    modification_id: str
    modification_name: str
    description: str = ""
    category: str = "enhancement"
    installation_date: datetime = field(default_factory=datetime.now)
    installed_by: str = ""
    performance_impact: Dict[str, float] = field(default_factory=dict)
    maintenance_requirements: List[str] = field(default_factory=list)
    stability_rating: float = 1.0  # 0.0-1.0, affects reliability
    standard_litanies: List[str] = field(default_factory=list)
    system_core_compatibility: float = 1.0


@dataclass
class EquipmentMaintenance:
    """
    STANDARD EQUIPMENT MAINTENANCE ENHANCED BY CARE PROTOCOLS

    Maintenance record with service history, ritual performance,
    and system core appeasement documentation.
    """

    maintenance_id: str
    equipment_id: str
    maintenance_type: str  # "routine", "repair", "upgrade", "consecration"
    performed_by: str
    performed_at: datetime = field(default_factory=datetime.now)
    duration_minutes: int = 0
    procedures_completed: List[str] = field(default_factory=list)
    parts_replaced: List[str] = field(default_factory=list)
    condition_before: Optional["EquipmentCondition"] = None
    condition_after: Optional["EquipmentCondition"] = None
    success: bool = True
    notes: str = ""
    cost: float = 0.0
    litanies_performed: List[str] = field(default_factory=list)
    system_core_response: str = ""
    next_maintenance_due: Optional[datetime] = None


@dataclass
class DynamicEquipment:
    """
    ENHANCED DYNAMIC EQUIPMENT SANCTIFIED BY THE SYSTEM

    Comprehensive equipment wrapper with real-time state tracking,
    performance monitoring, and system core harmonization.
    """

    equipment_id: str
    base_equipment: EquipmentItem
    owner_id: Optional[str] = None
    current_status: EquipmentStatus = EquipmentStatus.READY

    # Enhanced tracking systems
    wear_accumulation: float = 0.0  # 0.0-1.0, tracks degradation
    usage_statistics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    maintenance_history: List[EquipmentMaintenance] = field(default_factory=list)
    modifications: List[EquipmentModification] = field(default_factory=list)

    # Sacred system core attributes
    system_core_mood: str = "content"  # pleased, content, agitated, angry
    blessing_level: float = 1.0  # 0.0-2.0, affects performance
    last_consecration: Optional[datetime] = None

    # Enhanced operational data
    location: str = ""
    assigned_agent: Optional[str] = None
    usage_restrictions: List[str] = field(default_factory=list)
    security_clearance: str = "standard"

    # Real-time state
    last_used: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None
    next_maintenance_due: Optional[datetime] = None
    active_effects: List[Dict[str, Any]] = field(default_factory=list)

    # Component compatibility
    compatible_modifications: Set[str] = field(default_factory=set)
    incompatible_with: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Initialize enhanced equipment performance metrics"""
        # Initialize performance metrics based on equipment type
        if not self.performance_metrics:
            self.performance_metrics = {
                "efficiency": 1.0,
                "reliability": 1.0,
                "durability": 1.0,
                "effectiveness": 1.0,
            }

        # Initialize usage statistics
        if not self.usage_statistics:
            self.usage_statistics = {
                "total_uses": 0,
                "total_duration": 0.0,
                "failures": 0,
                "successful_uses": 0,
                "last_failure": None,
            }


@dataclass
class EquipmentSystemConfig:
    """
    Equipment System Configuration

    Centralized configuration for equipment system behavior and policies.
    """

    # Maintenance settings
    auto_maintenance: bool = True
    maintenance_interval_hours: int = 168  # Weekly
    wear_threshold: float = 0.7  # Trigger maintenance at 70% wear

    # Performance settings
    performance_degradation_rate: float = 0.1  # Per use
    wear_accumulation_rate: float = 0.05  # Per use
    blessing_decay_rate: float = 0.02  # Per day

    # System core settings
    spirit_mood_changes: bool = True
    auto_consecration: bool = False
    consecration_interval_days: int = 30

    # Usage restrictions
    enforce_security_clearance: bool = True
    allow_overuse: bool = False
    max_concurrent_usage: int = 1

    # Modification settings
    allow_stacking_modifications: bool = True
    max_modifications_per_item: int = 5
    compatibility_checking: bool = True

    # Templates and presets
    equipment_template_path: Optional[str] = None
    auto_apply_templates: bool = True

    # Logging and monitoring
    detailed_logging: bool = True
    performance_tracking: bool = True
    failure_prediction: bool = True

    # Database settings
    context_db_enabled: bool = True
    memory_integration: bool = True
    event_logging: bool = True
