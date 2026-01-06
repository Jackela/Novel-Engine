#!/usr/bin/env python3
"""
Equipment data models and enums.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.core.data_models import EquipmentCondition, EquipmentItem


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
    rituals_performed: List[str] = field(default_factory=list)
    condition_before: EquipmentCondition = EquipmentCondition.GOOD
    condition_after: EquipmentCondition = EquipmentCondition.GOOD
    next_maintenance_due: Optional[datetime] = None
    notes: str = ""
    system_core_response: str = "responsive"  # "responsive", "agitated", "dormant"


@dataclass
class DynamicEquipment:
    """
    ENHANCED DYNAMIC EQUIPMENT SANCTIFIED BY REAL-TIME TRACKING

    Enhanced equipment representation with real-time state tracking,
    usage history, and dynamic performance characteristics.
    """

    base_equipment: EquipmentItem
    current_status: EquipmentStatus = EquipmentStatus.READY
    usage_statistics: Dict[str, int] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    modifications: List[EquipmentModification] = field(default_factory=list)
    maintenance_history: List[EquipmentMaintenance] = field(default_factory=list)
    last_used: Optional[datetime] = None
    current_user: Optional[str] = None
    location_history: List[Tuple[datetime, str]] = field(default_factory=list)
    wear_accumulation: float = 0.0  # 0.0-1.0, affects condition over time
    system_core_mood: str = "content"  # Novel Engine flavor
    standard_rites_performed: int = 0
    blessing_level: float = 1.0  # Effectiveness multiplier from blessings

    def __post_init__(self):
        if not self.usage_statistics:
            self.usage_statistics = {
                "total_uses": 0,
                "successful_uses": 0,
                "maintenance_cycles": 0,
                "combat_uses": 0,
                "ritual_uses": 0,
            }

        if not self.performance_metrics:
            self.performance_metrics = {
                "reliability": 0.9,
                "effectiveness": 1.0,
                "efficiency": 1.0,
                "responsiveness": 1.0,
            }
