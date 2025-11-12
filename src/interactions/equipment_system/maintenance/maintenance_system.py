"""
Maintenance System
=================

Equipment maintenance scheduling, execution, and system core appeasement system.
Handles maintenance procedures, condition improvement, and preventive care.
"""

import asyncio
import heapq
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..core.types import (
    DynamicEquipment,
    EquipmentMaintenance,
    EquipmentStatus,
    EquipmentSystemConfig,
)

# Import enhanced core systems
try:
    from src.core.data_models import EquipmentCondition, ErrorInfo, StandardResponse
except ImportError:
    # Fallback for testing
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

    class EquipmentCondition:
        EXCELLENT = "excellent"
        GOOD = "good"
        FAIR = "fair"
        POOR = "poor"
        DAMAGED = "damaged"
        BROKEN = "broken"


__all__ = ["MaintenanceSystem"]


class MaintenanceSystem:
    """
    Equipment Maintenance Scheduling and Execution System

    Responsibilities:
    - Schedule and manage maintenance operations
    - Execute maintenance procedures with ritual protocols
    - Improve equipment condition and performance
    - Appease system cores through proper care
    - Track maintenance history and effectiveness
    """

    def __init__(
        self, config: EquipmentSystemConfig, logger: Optional[logging.Logger] = None
    ):
        """
        Initialize maintenance system.

        Args:
            config: Equipment system configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Maintenance scheduling
        self._maintenance_queue: List[Tuple[datetime, str]] = []  # (time, equipment_id)
        self._maintenance_lock = asyncio.Lock()

        # Maintenance procedures and templates
        self._maintenance_procedures = {
            "routine": [
                "Visual inspection",
                "Cleaning and lubrication",
                "Component check",
                "Calibration verification",
                "System core appeasement",
            ],
            "repair": [
                "Damage assessment",
                "Component replacement",
                "Structural repair",
                "Performance testing",
                "Blessed restoration ritual",
            ],
            "upgrade": [
                "Compatibility analysis",
                "Enhancement installation",
                "Integration testing",
                "Performance optimization",
                "Consecration of improvements",
            ],
            "overhaul": [
                "Complete disassembly",
                "Part-by-part restoration",
                "Precision recalibration",
                "Stress testing",
                "Grand blessing ceremony",
            ],
        }

        # System core litanies and blessings
        self._maintenance_litanies = {
            "routine": [
                "Benediction of Proper Function",
                "Litany of Preservation",
                "Hymnal of Mechanical Harmony",
            ],
            "repair": [
                "Prayer of Restoration",
                "Canticle of Renewal",
                "Invocation of the Mending Spirit",
            ],
            "upgrade": [
                "Blessing of Enhancement",
                "Ritual of Sanctified Improvement",
                "Oath of Eternal Service",
            ],
            "overhaul": [
                "Great Ritual of Rebirth",
                "The Sacred Dismantling",
                "Ceremony of Perfect Restoration",
            ],
        }

        self.logger.info("Maintenance system initialized")

    async def schedule_maintenance(
        self,
        equipment: DynamicEquipment,
        maintenance_type: str = "routine",
        scheduled_time: Optional[datetime] = None,
    ) -> StandardResponse:
        """
        Schedule maintenance for equipment.

        Args:
            equipment: Equipment to schedule maintenance for
            maintenance_type: Type of maintenance (routine, repair, upgrade, overhaul)
            scheduled_time: Optional specific time to schedule

        Returns:
            StandardResponse with scheduling result
        """
        try:
            async with self._maintenance_lock:
                if not scheduled_time:
                    # Calculate next maintenance time based on type and config
                    if maintenance_type == "routine":
                        hours_ahead = self.config.maintenance_interval_hours
                    elif maintenance_type == "repair":
                        hours_ahead = 24  # Urgent repair
                    elif maintenance_type == "upgrade":
                        hours_ahead = 72  # Planned upgrade
                    else:  # overhaul
                        hours_ahead = 168  # Major overhaul

                    scheduled_time = datetime.now() + timedelta(hours=hours_ahead)

                # Add to maintenance queue
                heapq.heappush(
                    self._maintenance_queue, (scheduled_time, equipment.equipment_id)
                )

                # Update equipment's next maintenance due
                equipment.next_maintenance_due = scheduled_time

                self.logger.info(
                    f"Maintenance scheduled for equipment '{equipment.equipment_id}' at {scheduled_time}"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "equipment_id": equipment.equipment_id,
                        "maintenance_type": maintenance_type,
                        "scheduled_time": scheduled_time.isoformat(),
                        "queue_position": len(self._maintenance_queue),
                    },
                    metadata={"blessing": "maintenance_scheduled"},
                )

        except Exception as e:
            self.logger.error(f"Maintenance scheduling failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="SCHEDULING_FAILED",
                    message=f"Maintenance scheduling failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def perform_maintenance(
        self,
        equipment: DynamicEquipment,
        maintenance_type: str = "routine",
        performed_by: str = "tech_priest",
    ) -> StandardResponse:
        """
        Perform maintenance on equipment with ritual protocols.

        Args:
            equipment: Equipment to maintain
            maintenance_type: Type of maintenance to perform
            performed_by: Who is performing the maintenance

        Returns:
            StandardResponse with maintenance results
        """
        try:
            async with self._maintenance_lock:
                maintenance_start = datetime.now()

                # Record pre-maintenance condition
                condition_before = getattr(
                    equipment.base_equipment, "condition", EquipmentCondition.GOOD
                )
                if hasattr(condition_before, "value"):
                    condition_before = condition_before.value

                # Set maintenance status
                equipment.current_status = EquipmentStatus.MAINTENANCE

                # Create maintenance record
                maintenance_record = EquipmentMaintenance(
                    maintenance_id=f"{equipment.equipment_id}_maintenance_{maintenance_start.strftime('%Y%m%d_%H%M%S')}",
                    equipment_id=equipment.equipment_id,
                    maintenance_type=maintenance_type,
                    performed_by=performed_by,
                    performed_at=maintenance_start,
                    condition_before=condition_before,
                )

                # Execute maintenance procedures
                maintenance_effects = await self._execute_maintenance_procedures(
                    equipment, maintenance_type, maintenance_record
                )

                # Calculate maintenance duration
                base_duration = {
                    "routine": 60,
                    "repair": 120,
                    "upgrade": 240,
                    "overhaul": 480,
                }
                duration_minutes = base_duration.get(maintenance_type, 60)

                # Add wear-based duration increase
                duration_minutes += int(equipment.wear_accumulation * 120)
                maintenance_record.duration_minutes = duration_minutes

                # Apply condition improvements
                condition_improvement = self._calculate_condition_improvement(
                    equipment, maintenance_type, maintenance_effects
                )

                new_condition = self._improve_equipment_condition(
                    condition_before, condition_improvement
                )

                # Update equipment condition
                if hasattr(equipment.base_equipment, "condition"):
                    equipment.base_equipment.condition = new_condition
                maintenance_record.condition_after = new_condition

                # Reduce wear accumulation
                wear_reduction = self._calculate_wear_reduction(
                    maintenance_type, maintenance_effects
                )
                equipment.wear_accumulation = max(
                    0.0, equipment.wear_accumulation - wear_reduction
                )

                # Apply performance improvements
                self._apply_maintenance_performance_boost(equipment, maintenance_type)

                # Appease system core
                spirit_improvement = self._appease_system_core(
                    equipment, maintenance_type
                )
                equipment.system_core_mood = spirit_improvement["new_mood"]
                maintenance_record.system_core_response = spirit_improvement["response"]

                # Update timestamps
                equipment.last_maintenance = maintenance_start

                # Schedule next maintenance if auto-maintenance is enabled
                if self.config.auto_maintenance:
                    next_maintenance_time = maintenance_start + timedelta(
                        hours=self.config.maintenance_interval_hours
                    )
                    if maintenance_type == "overhaul":
                        next_maintenance_time += timedelta(
                            hours=self.config.maintenance_interval_hours
                        )  # Overhauls last longer
                    equipment.next_maintenance_due = next_maintenance_time

                # Add to maintenance history
                equipment.maintenance_history.append(maintenance_record)

                # Restore operational status
                equipment.current_status = (
                    EquipmentStatus.READY
                    if new_condition not in ["broken", "damaged"]
                    else EquipmentStatus.DAMAGED
                )

                self.logger.info(
                    f"Maintenance completed for equipment '{equipment.equipment_id}' - {maintenance_type} by {performed_by}"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "equipment_id": equipment.equipment_id,
                        "maintenance_type": maintenance_type,
                        "performed_by": performed_by,
                        "duration_minutes": duration_minutes,
                        "condition_before": condition_before,
                        "condition_after": new_condition,
                        "wear_reduction": wear_reduction,
                        "system_core_response": spirit_improvement["response"],
                        "next_maintenance_due": (
                            equipment.next_maintenance_due.isoformat()
                            if equipment.next_maintenance_due
                            else None
                        ),
                        "procedures_completed": maintenance_record.procedures_completed,
                        "litanies_performed": maintenance_record.litanies_performed,
                    },
                    metadata={"blessing": "maintenance_completed"},
                )

        except Exception as e:
            self.logger.error(f"Maintenance execution failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MAINTENANCE_FAILED",
                    message=f"Maintenance execution failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def get_maintenance_due(self, equipment: DynamicEquipment) -> Dict[str, Any]:
        """
        Check if equipment maintenance is due.

        Args:
            equipment: Equipment to check

        Returns:
            Dict with maintenance status information
        """
        try:
            now = datetime.now()

            # Check scheduled maintenance
            is_scheduled = (
                equipment.next_maintenance_due and equipment.next_maintenance_due <= now
            )

            # Check wear-based maintenance need
            wear_based_due = equipment.wear_accumulation >= self.config.wear_threshold

            # Check time-based maintenance (if no scheduled maintenance)
            time_based_due = False
            if equipment.last_maintenance:
                hours_since_maintenance = (
                    now - equipment.last_maintenance
                ).total_seconds() / 3600
                time_based_due = (
                    hours_since_maintenance >= self.config.maintenance_interval_hours
                )
            elif not equipment.maintenance_history:
                # New equipment needs initial maintenance check
                time_based_due = True

            # Determine maintenance urgency
            urgency = "routine"
            if wear_based_due and equipment.wear_accumulation > 0.9:
                urgency = "critical"
            elif wear_based_due or equipment.current_status == EquipmentStatus.DAMAGED:
                urgency = "high"
            elif is_scheduled or time_based_due:
                urgency = "normal"

            # Recommend maintenance type
            maintenance_type = "routine"
            condition = getattr(equipment.base_equipment, "condition", "good")
            if hasattr(condition, "value"):
                condition = condition.value

            if condition in ["broken", "damaged"]:
                maintenance_type = "repair"
            elif equipment.wear_accumulation > 0.8:
                maintenance_type = "overhaul"
            elif (
                len(equipment.maintenance_history) > 0
                and len(equipment.modifications) > 0
            ):
                # Equipment with modifications might benefit from upgrade maintenance
                last_maintenance = equipment.maintenance_history[-1]
                if (now - last_maintenance.performed_at).days > 30:
                    maintenance_type = "upgrade"

            return {
                "equipment_id": equipment.equipment_id,
                "maintenance_due": is_scheduled or wear_based_due or time_based_due,
                "urgency": urgency,
                "recommended_type": maintenance_type,
                "wear_accumulation": equipment.wear_accumulation,
                "condition": condition,
                "last_maintenance": (
                    equipment.last_maintenance.isoformat()
                    if equipment.last_maintenance
                    else None
                ),
                "next_scheduled": (
                    equipment.next_maintenance_due.isoformat()
                    if equipment.next_maintenance_due
                    else None
                ),
                "days_overdue": (
                    max(0, (now - equipment.next_maintenance_due).days)
                    if equipment.next_maintenance_due
                    and equipment.next_maintenance_due < now
                    else 0
                ),
            }

        except Exception as e:
            self.logger.error(f"Error checking maintenance status: {e}")
            return {"equipment_id": equipment.equipment_id, "error": str(e)}

    def get_maintenance_queue(self) -> List[Tuple[datetime, str]]:
        """Get current maintenance queue."""
        return sorted(self._maintenance_queue.copy())

    async def get_overdue_maintenance(
        self, equipment_registry: Dict[str, DynamicEquipment]
    ) -> List[Dict[str, Any]]:
        """Get list of equipment with overdue maintenance."""
        overdue_equipment = []

        for equipment_id, equipment in equipment_registry.items():
            maintenance_status = await self.get_maintenance_due(equipment)

            if (
                maintenance_status.get("maintenance_due")
                and maintenance_status.get("days_overdue", 0) > 0
            ):
                overdue_equipment.append(maintenance_status)

        # Sort by urgency and days overdue
        urgency_priority = {"critical": 0, "high": 1, "normal": 2, "routine": 3}
        overdue_equipment.sort(
            key=lambda x: (urgency_priority.get(x["urgency"], 3), -x["days_overdue"])
        )

        return overdue_equipment

    # Private helper methods

    async def _execute_maintenance_procedures(
        self,
        equipment: DynamicEquipment,
        maintenance_type: str,
        maintenance_record: EquipmentMaintenance,
    ) -> Dict[str, Any]:
        """Execute maintenance procedures with blessed rituals."""
        try:
            # Get procedures for this maintenance type
            procedures = self._maintenance_procedures.get(
                maintenance_type, self._maintenance_procedures["routine"]
            )
            litanies = self._maintenance_litanies.get(
                maintenance_type, self._maintenance_litanies["routine"]
            )

            completed_procedures = []
            performed_litanies = []

            # Execute each procedure
            for procedure in procedures:
                # Simulate procedure execution with success chance
                success_chance = 0.9 - (
                    equipment.wear_accumulation * 0.3
                )  # More wear = higher failure chance

                if success_chance > 0.7:  # Most procedures succeed
                    completed_procedures.append(procedure)

                    # Perform associated litany
                    if litanies:
                        litany = litanies[len(performed_litanies) % len(litanies)]
                        performed_litanies.append(litany)

            # Record completed procedures and litanies
            maintenance_record.procedures_completed = completed_procedures
            maintenance_record.litanies_performed = performed_litanies

            # Calculate maintenance effectiveness
            effectiveness = len(completed_procedures) / max(1, len(procedures))

            return {
                "procedures_completed": completed_procedures,
                "litanies_performed": performed_litanies,
                "effectiveness": effectiveness,
                "system_core_pleased": effectiveness > 0.8,
            }

        except Exception as e:
            self.logger.error(f"Error executing maintenance procedures: {e}")
            return {
                "procedures_completed": [],
                "litanies_performed": [],
                "effectiveness": 0.0,
                "system_core_pleased": False,
            }

    def _calculate_condition_improvement(
        self,
        equipment: DynamicEquipment,
        maintenance_type: str,
        maintenance_effects: Dict[str, Any],
    ) -> str:
        """Calculate condition improvement from maintenance."""
        effectiveness = maintenance_effects.get("effectiveness", 0.5)

        # Base improvement by maintenance type
        base_improvements = {
            "routine": "minor",
            "repair": "moderate",
            "upgrade": "significant",
            "overhaul": "major",
        }

        improvement_level = base_improvements.get(maintenance_type, "minor")

        # Modify based on effectiveness
        if effectiveness < 0.5:
            improvement_level = "minimal"
        elif effectiveness > 0.9 and maintenance_type in ["upgrade", "overhaul"]:
            improvement_level = "excellent"

        return improvement_level

    def _improve_equipment_condition(
        self, current_condition: str, improvement_level: str
    ) -> str:
        """Improve equipment condition based on maintenance quality."""
        # Define condition hierarchy
        condition_order = ["broken", "damaged", "poor", "fair", "good", "excellent"]

        try:
            current_index = condition_order.index(current_condition)
        except ValueError:
            current_index = 2  # Default to "poor"

        # Define improvement amounts
        improvement_amounts = {
            "minimal": 0,
            "minor": 1,
            "moderate": 2,
            "significant": 3,
            "major": 4,
            "excellent": 5,
        }

        improvement = improvement_amounts.get(improvement_level, 1)
        new_index = min(len(condition_order) - 1, current_index + improvement)

        return condition_order[new_index]

    def _calculate_wear_reduction(
        self, maintenance_type: str, maintenance_effects: Dict[str, Any]
    ) -> float:
        """Calculate wear reduction from maintenance."""
        base_reductions = {
            "routine": 0.2,
            "repair": 0.4,
            "upgrade": 0.3,
            "overhaul": 0.8,
        }

        base_reduction = base_reductions.get(maintenance_type, 0.2)
        effectiveness = maintenance_effects.get("effectiveness", 0.5)

        return base_reduction * effectiveness

    def _apply_maintenance_performance_boost(
        self, equipment: DynamicEquipment, maintenance_type: str
    ) -> None:
        """Apply performance boost from maintenance."""
        boost_amounts = {
            "routine": 0.05,
            "repair": 0.10,
            "upgrade": 0.15,
            "overhaul": 0.25,
        }

        boost = boost_amounts.get(maintenance_type, 0.05)

        for metric in equipment.performance_metrics:
            current_value = equipment.performance_metrics[metric]
            boosted_value = min(
                1.5, current_value + boost
            )  # Cap at 150% for exceptional maintenance
            equipment.performance_metrics[metric] = boosted_value

    def _appease_system_core(
        self, equipment: DynamicEquipment, maintenance_type: str
    ) -> Dict[str, Any]:
        """Appease system core through proper maintenance rituals."""
        current_mood = equipment.system_core_mood

        # Maintenance always improves system core mood
        mood_improvements = {
            "routine": {
                "pleased": "pleased",
                "content": "pleased",
                "agitated": "content",
                "angry": "agitated",
            },
            "repair": {
                "pleased": "pleased",
                "content": "pleased",
                "agitated": "pleased",
                "angry": "content",
            },
            "upgrade": {
                "pleased": "pleased",
                "content": "pleased",
                "agitated": "pleased",
                "angry": "pleased",
            },
            "overhaul": {
                "pleased": "pleased",
                "content": "pleased",
                "agitated": "pleased",
                "angry": "pleased",
            },
        }

        improvement_map = mood_improvements.get(
            maintenance_type, mood_improvements["routine"]
        )
        new_mood = improvement_map.get(current_mood, "content")

        # Generate response based on mood change
        if new_mood == current_mood:
            response = f"The system core maintains its {current_mood} disposition"
        else:
            response = (
                f"The system core's mood improves from {current_mood} to {new_mood}"
            )

        return {
            "old_mood": current_mood,
            "new_mood": new_mood,
            "response": response,
            "improvement": new_mood != current_mood,
        }
