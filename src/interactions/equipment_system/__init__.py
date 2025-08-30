"""
Dynamic Equipment System - Modular Architecture
===============================================

Enterprise-grade modular dynamic equipment management system.

Components:
- Core Types & Data Models: Equipment enums, dataclasses, and type definitions
- Equipment Registry: Equipment registration and state management
- Equipment Usage: Usage processing and wear calculation
- Maintenance System: Maintenance scheduling and execution
- Modification System: Equipment modification and compatibility
- Performance Monitor: Performance tracking and failure prediction
- Main Facade: Unified interface maintaining backward compatibility
"""

# Core components
from .core import (
    DynamicEquipment,
    EquipmentCategory,
    EquipmentMaintenance,
    EquipmentModification,
    EquipmentStatus,
)

# Factory functions
# Main facade
from .dynamic_equipment_system_modular import (
    DynamicEquipmentSystem,
    create_dynamic_equipment_system,
    create_maintenance_optimized_config,
)

__all__ = [
    # Core types
    "EquipmentCategory",
    "EquipmentStatus",
    "EquipmentModification",
    "EquipmentMaintenance",
    "DynamicEquipment",
    # Main system
    "DynamicEquipmentSystem",
    # Factory functions
    "create_dynamic_equipment_system",
    "create_maintenance_optimized_config",
]

__version__ = "3.0.0"
__author__ = "Novel Engine Development Team"
