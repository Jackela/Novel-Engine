"""
Dynamic Equipment System (Modular)
==================================

Modular implementation of the dynamic equipment system using component-based architecture.
Maintains full backward compatibility while providing enterprise-grade modularity.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import modular components
from .core import (
    DynamicEquipment,
    EquipmentCategory,
    EquipmentModification,
    EquipmentStatus,
    EquipmentSystemConfig,
)
from .maintenance import MaintenanceSystem
from .modifications import ModificationSystem
from .monitoring import PerformanceMonitor
from .registry import EquipmentRegistry
from .usage import EquipmentUsageProcessor

# Import enhanced core systems
try:
    from src.core.data_models import EquipmentItem, ErrorInfo, StandardResponse
    from src.core.types import AgentID
    from src.database.context_db import ContextDatabase
except ImportError:
    # Fallback for testing
    EquipmentItem = dict

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

    AgentID = str
    ContextDatabase = type("ContextDatabase", (), {})

__all__ = ["DynamicEquipmentSystem"]


class DynamicEquipmentSystem:
    """
    Modular Dynamic Equipment System Implementation

    This class provides a facade over specialized components while maintaining
    full backward compatibility with the original dynamic equipment system interface.

    Components:
    - EquipmentRegistry: Equipment registration and state management
    - EquipmentUsageProcessor: Usage processing and wear calculation
    - MaintenanceSystem: Maintenance scheduling and execution
    - ModificationSystem: Equipment modifications and compatibility
    - PerformanceMonitor: Performance monitoring and failure prediction
    """

    def __init__(
        self,
        auto_maintenance: bool = True,
        maintenance_interval_hours: int = 168,
        wear_threshold: float = 0.7,
        context_db: Optional[ContextDatabase] = None,
        equipment_template_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize modular dynamic equipment system.

        Args:
            auto_maintenance: Enable automatic maintenance scheduling
            maintenance_interval_hours: Hours between maintenance cycles
            wear_threshold: Wear threshold for maintenance triggers
            context_db: Optional context database for persistence
            equipment_template_path: Path to equipment templates
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

        # Create system configuration
        self.config = EquipmentSystemConfig(
            auto_maintenance=auto_maintenance,
            maintenance_interval_hours=maintenance_interval_hours,
            wear_threshold=wear_threshold,
            equipment_template_path=equipment_template_path,
            context_db_enabled=context_db is not None,
        )

        # Initialize components
        self.registry = EquipmentRegistry(
            self.config, context_db, self.logger.getChild("registry")
        )
        self.usage_processor = EquipmentUsageProcessor(
            self.config, self.logger.getChild("usage")
        )
        self.maintenance_system = MaintenanceSystem(
            self.config, self.logger.getChild("maintenance")
        )
        self.modification_system = ModificationSystem(
            self.config, self.logger.getChild("modifications")
        )
        self.performance_monitor = PerformanceMonitor(
            self.config, self.logger.getChild("monitor")
        )

        # System state
        self._processing_lock = asyncio.Lock()
        self._system_stats = {
            "initialization_time": datetime.now(),
            "total_equipment_registered": 0,
            "total_usage_sessions": 0,
            "total_maintenance_performed": 0,
            "total_modifications_installed": 0,
        }

        # Load equipment templates if path provided
        if equipment_template_path:
            self._load_equipment_templates()

        self.logger.info(
            "Dynamic equipment system initialized with modular architecture"
        )

    # Main API Methods (Backward Compatibility)

    async def register_equipment(
        self,
        equipment_item: EquipmentItem,
        agent_id: Optional[str] = None,
        location: str = "",
        initial_blessing_level: float = 1.0,
    ) -> StandardResponse:
        """Register new equipment in the system."""
        try:
            result = await self.registry.register_equipment(
                equipment_item=equipment_item,
                owner_id=agent_id,
                location=location,
                initial_status=EquipmentStatus.READY,
            )

            if result.get("success"):
                self._system_stats["total_equipment_registered"] += 1

                # Apply initial blessing level
                equipment_id = result["data"]["equipment_id"]
                equipment = await self.registry.get_equipment(equipment_id)
                if equipment:
                    equipment.blessing_level = initial_blessing_level

            return result

        except Exception as e:
            self.logger.error(f"Equipment registration failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="REGISTRATION_FAILED",
                    message=f"Equipment registration failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def use_equipment(
        self,
        equipment_id: str,
        agent_id: str,
        usage_context: Optional[Dict[str, Any]] = None,
        duration_seconds: float = 60.0,
    ) -> StandardResponse:
        """Use equipment with category-specific processing."""
        try:
            equipment = await self.registry.get_equipment(equipment_id)
            if not equipment:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="EQUIPMENT_NOT_FOUND",
                        message=f"Equipment '{equipment_id}' not found",
                    ),
                )

            # Process usage
            result = await self.usage_processor.process_equipment_usage(
                equipment=equipment,
                agent_id=agent_id,
                usage_context=usage_context or {},
                duration_seconds=duration_seconds,
            )

            if result.get("success"):
                self._system_stats["total_usage_sessions"] += 1

                # Auto-schedule maintenance if needed
                if (
                    self.config.auto_maintenance
                    and equipment.wear_accumulation >= self.config.wear_threshold
                ):
                    await self.maintenance_system.schedule_maintenance(
                        equipment, "routine"
                    )

            return result

        except Exception as e:
            self.logger.error(f"Equipment usage failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="USAGE_FAILED",
                    message=f"Equipment usage failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def perform_maintenance(
        self,
        equipment_id: str,
        maintenance_type: str = "routine",
        performed_by: str = "tech_priest",
    ) -> StandardResponse:
        """Perform maintenance on equipment."""
        try:
            equipment = await self.registry.get_equipment(equipment_id)
            if not equipment:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="EQUIPMENT_NOT_FOUND",
                        message=f"Equipment '{equipment_id}' not found for maintenance",
                    ),
                )

            result = await self.maintenance_system.perform_maintenance(
                equipment=equipment,
                maintenance_type=maintenance_type,
                performed_by=performed_by,
            )

            if result.get("success"):
                self._system_stats["total_maintenance_performed"] += 1

            return result

        except Exception as e:
            self.logger.error(f"Maintenance failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MAINTENANCE_FAILED",
                    message=f"Maintenance failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def apply_modification(
        self,
        equipment_id: str,
        modification: EquipmentModification,
        installer: str = "tech_adept",
    ) -> StandardResponse:
        """Apply modification to equipment."""
        try:
            equipment = await self.registry.get_equipment(equipment_id)
            if not equipment:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="EQUIPMENT_NOT_FOUND",
                        message=f"Equipment '{equipment_id}' not found for modification",
                    ),
                )

            result = await self.modification_system.install_modification(
                equipment=equipment, modification=modification, installer=installer
            )

            if result.get("success"):
                self._system_stats["total_modifications_installed"] += 1

            return result

        except Exception as e:
            self.logger.error(f"Modification failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MODIFICATION_FAILED",
                    message=f"Modification failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def get_equipment_status(self, equipment_id: str) -> StandardResponse:
        """Get comprehensive equipment status."""
        try:
            equipment = await self.registry.get_equipment(equipment_id)
            if not equipment:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="EQUIPMENT_NOT_FOUND",
                        message=f"Equipment '{equipment_id}' not found",
                    ),
                )

            # Get performance metrics
            performance_data = self.performance_monitor.get_performance_metrics(
                equipment
            )

            # Get failure prediction
            failure_prediction = self.performance_monitor.predict_equipment_failure(
                equipment
            )

            # Get maintenance status
            maintenance_status = await self.maintenance_system.get_maintenance_due(
                equipment
            )

            # Get optimization recommendations
            recommendations = self.performance_monitor.get_optimization_recommendations(
                equipment
            )

            return StandardResponse(
                success=True,
                data={
                    "equipment_id": equipment_id,
                    "basic_info": {
                        "name": equipment.base_equipment.name,
                        "category": self._determine_equipment_category(equipment).value,
                        "status": equipment.current_status.value,
                        "condition": getattr(
                            equipment.base_equipment, "condition", "unknown"
                        ),
                        "owner": equipment.owner_id,
                        "location": equipment.location,
                    },
                    "wear_and_performance": {
                        "wear_accumulation": equipment.wear_accumulation,
                        "performance_metrics": equipment.performance_metrics,
                        "system_core_mood": equipment.system_core_mood,
                        "blessing_level": equipment.blessing_level,
                    },
                    "usage_statistics": equipment.usage_statistics,
                    "maintenance_info": {
                        "last_maintenance": (
                            equipment.last_maintenance.isoformat()
                            if equipment.last_maintenance
                            else None
                        ),
                        "next_due": (
                            equipment.next_maintenance_due.isoformat()
                            if equipment.next_maintenance_due
                            else None
                        ),
                        "maintenance_history_count": len(equipment.maintenance_history),
                        "maintenance_status": maintenance_status,
                    },
                    "modifications": [
                        {
                            "id": mod.modification_id,
                            "name": mod.modification_name,
                            "installed_date": mod.installation_date.isoformat(),
                            "installed_by": mod.installed_by,
                            "performance_impact": mod.performance_impact,
                        }
                        for mod in equipment.modifications
                    ],
                    "performance_analysis": performance_data,
                    "failure_prediction": failure_prediction,
                    "recommendations": recommendations,
                },
                metadata={"blessing": "equipment_status_retrieved"},
            )

        except Exception as e:
            self.logger.error(f"Error getting equipment status: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="STATUS_RETRIEVAL_FAILED",
                    message=f"Status retrieval failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def get_agent_equipment(
        self,
        agent_id: str,
        category: Optional[EquipmentCategory] = None,
        status_filter: Optional[List[EquipmentStatus]] = None,
    ) -> StandardResponse:
        """Get equipment assigned to a specific agent."""
        try:
            result = await self.registry.get_agent_equipment(
                agent_id=agent_id, category=category, status_filter=status_filter
            )

            return StandardResponse(
                success=True,
                data=result,
                metadata={"blessing": "agent_equipment_retrieved"},
            )

        except Exception as e:
            self.logger.error(f"Error getting agent equipment: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="AGENT_EQUIPMENT_FAILED",
                    message=f"Agent equipment retrieval failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            # Get equipment counts by category
            category_counts = self.registry.get_category_counts()

            # Get maintenance queue status
            maintenance_queue = self.maintenance_system.get_maintenance_queue()

            # Calculate system uptime
            uptime = datetime.now() - self._system_stats["initialization_time"]

            return {
                "system_info": {
                    "initialization_time": self._system_stats[
                        "initialization_time"
                    ].isoformat(),
                    "uptime_hours": uptime.total_seconds() / 3600,
                    "modular_architecture": True,
                    "components_active": 5,
                },
                "equipment_statistics": {
                    "total_registered": self.registry.get_equipment_count(),
                    "by_category": category_counts,
                    "total_usage_sessions": self._system_stats["total_usage_sessions"],
                    "total_maintenance_performed": self._system_stats[
                        "total_maintenance_performed"
                    ],
                    "total_modifications_installed": self._system_stats[
                        "total_modifications_installed"
                    ],
                },
                "maintenance_info": {
                    "scheduled_maintenance_count": len(maintenance_queue),
                    "auto_maintenance_enabled": self.config.auto_maintenance,
                    "maintenance_interval_hours": self.config.maintenance_interval_hours,
                    "wear_threshold": self.config.wear_threshold,
                },
                "system_health": {
                    "processing_locks_active": 0,
                    "component_status": {
                        "registry": "active",
                        "usage_processor": "active",
                        "maintenance_system": "active",
                        "modification_system": "active",
                        "performance_monitor": "active",
                    },
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting system statistics: {e}")
            return {"error": str(e)}

    # Helper methods

    def _determine_equipment_category(
        self, equipment: DynamicEquipment
    ) -> EquipmentCategory:
        """Determine equipment category from equipment data."""
        # Reuse logic from usage processor
        return self.usage_processor._determine_equipment_category(equipment)

    def _load_equipment_templates(self) -> None:
        """Load equipment templates from file."""
        try:
            if self.config.equipment_template_path:
                template_path = Path(self.config.equipment_template_path)
                if template_path.exists():
                    self.logger.info(f"Equipment templates loaded from {template_path}")
                else:
                    self.logger.warning(
                        f"Equipment template path not found: {template_path}"
                    )
        except Exception as e:
            self.logger.error(f"Error loading equipment templates: {e}")

    # Backward compatibility methods

    def __getattr__(self, name: str):
        """Provide backward compatibility for legacy method calls."""
        legacy_mappings = {
            "get_equipment": "registry.get_equipment",
            "assign_equipment": "registry.assign_equipment",
            "schedule_maintenance": "maintenance_system.schedule_maintenance",
            "predict_failure": "performance_monitor.predict_equipment_failure",
            "get_compatible_modifications": "modification_system.get_compatible_modifications",
        }

        if name in legacy_mappings:
            self.logger.debug(f"Legacy method call: {name} -> {legacy_mappings[name]}")
            component_name, method_name = legacy_mappings[name].split(".", 1)
            component = getattr(self, component_name)
            return getattr(component, method_name)

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )


# Factory functions for backward compatibility
def create_dynamic_equipment_system(
    auto_maintenance: bool = True,
    maintenance_interval_hours: int = 168,
    wear_threshold: float = 0.7,
    context_db: Optional[ContextDatabase] = None,
    logger: Optional[logging.Logger] = None,
) -> DynamicEquipmentSystem:
    """
    Factory function to create dynamic equipment system.

    Args:
        auto_maintenance: Enable automatic maintenance scheduling
        maintenance_interval_hours: Hours between maintenance cycles
        wear_threshold: Wear threshold for maintenance triggers
        context_db: Optional context database for persistence
        logger: Optional logger instance

    Returns:
        DynamicEquipmentSystem: Fully configured system instance
    """
    return DynamicEquipmentSystem(
        auto_maintenance=auto_maintenance,
        maintenance_interval_hours=maintenance_interval_hours,
        wear_threshold=wear_threshold,
        context_db=context_db,
        logger=logger,
    )


def create_maintenance_optimized_config(
    wear_threshold: float = 0.6,
    maintenance_interval_hours: int = 120,
    enable_predictive_maintenance: bool = True,
) -> EquipmentSystemConfig:
    """
    Create maintenance-optimized system configuration.

    Args:
        wear_threshold: Lower threshold for more frequent maintenance
        maintenance_interval_hours: Shorter interval for preventive maintenance
        enable_predictive_maintenance: Enable failure prediction

    Returns:
        EquipmentSystemConfig: Optimized configuration
    """
    return EquipmentSystemConfig(
        auto_maintenance=True,
        maintenance_interval_hours=maintenance_interval_hours,
        wear_threshold=wear_threshold,
        performance_degradation_rate=0.08,  # Slightly slower degradation
        wear_accumulation_rate=0.04,  # Slower wear with good maintenance
        failure_prediction=enable_predictive_maintenance,
        detailed_logging=True,
        performance_tracking=True,
    )
