#!/usr/bin/env python3
"""
Dynamic Equipment System - Main orchestrator.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import structlog

from src.core.data_models import (
    EquipmentCondition,
    EquipmentItem,
    ErrorInfo,
    StandardResponse,
)
from src.core.utils import ResponseBuilder
from src.database.context_db import ContextDatabase

from .models import (
    DynamicEquipment,
    EquipmentCategory,
    EquipmentMaintenance,
    EquipmentModification,
    EquipmentStatus,
)
from .validators import EquipmentValidator

logger = structlog.get_logger(__name__)


class DynamicEquipmentSystem:
    """
    STANDARD DYNAMIC EQUIPMENT SYSTEM ENHANCED BY TECHNOLOGICAL ORCHESTRATION

    The standard equipment management system that provides real-time equipment
    state tracking, dynamic modifications, maintenance scheduling, and
    interaction-based equipment changes enhanced by the System Core's
    mechanical omniscience.
    """

    def __init__(
        self,
        database: ContextDatabase,
        equipment_templates_dir: str = "equipment_templates",
        auto_maintenance: bool = True,
        maintenance_interval_hours: int = 168,
    ) -> None:  # Weekly default
        """
        STANDARD EQUIPMENT SYSTEM INITIALIZATION ENHANCED BY MECHANICUS PROTOCOLS

        Args:
            database: Database for persistent equipment storage
            equipment_templates_dir: Directory containing equipment templates
            auto_maintenance: Enable automatic maintenance scheduling
            maintenance_interval_hours: Default maintenance interval in hours
        """
        self.database = database
        self.equipment_templates_dir = Path(equipment_templates_dir)
        self.auto_maintenance = auto_maintenance
        self.maintenance_interval_hours = maintenance_interval_hours

        # Sacred equipment tracking
        self._equipment_registry: Dict[str, DynamicEquipment] = {}
        self._agent_equipment: Dict[str, List[str]] = {}  # agent_id -> equipment_ids
        self._equipment_templates: Dict[str, Dict[str, Any]] = {}
        self._maintenance_queue: List[
            Tuple[datetime, str]
        ] = []  # scheduled maintenance

        # Blessed equipment processors
        self._category_processors = {
            EquipmentCategory.WEAPON: self._process_weapon_usage,
            EquipmentCategory.ARMOR: self._process_armor_usage,
            EquipmentCategory.TOOL: self._process_tool_usage,
            EquipmentCategory.CONSUMABLE: self._process_consumable_usage,
            EquipmentCategory.AUGMETIC: self._process_augmetic_usage,
            EquipmentCategory.RELIC: self._process_relic_usage,
            EquipmentCategory.TRANSPORT: self._process_transport_usage,
            EquipmentCategory.COMMUNICATION: self._process_communication_usage,
            EquipmentCategory.MEDICAL: self._process_medical_usage,
            EquipmentCategory.SENSOR: self._process_sensor_usage,
        }

        # Sacred performance metrics
        self.system_metrics = {
            "total_equipment_tracked": 0,
            "active_equipment": 0,
            "maintenance_operations": 0,
            "modifications_applied": 0,
            "equipment_failures": 0,
            "equipment_repairs": 0,
            "standard_rites_performed": 0,
            "average_equipment_reliability": 0.9,
        }

        # Initialize enhanced equipment templates
        self._load_equipment_templates()

        # Sacred processing lock
        self._processing_lock = asyncio.Lock()

        logger.info("DYNAMIC EQUIPMENT SYSTEM INITIALIZED WITH ENHANCED PROTOCOLS")

    def _load_equipment_templates(self) -> None:
        """Load equipment templates from disk if available."""
        self.equipment_templates_dir.mkdir(parents=True, exist_ok=True)
        if not self._equipment_templates:
            self._equipment_templates = {}

    async def _process_weapon_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        """Placeholder processor for weapon interactions."""
        return StandardResponse(
            success=True, data={"effects": ["weapon_usage"], "warnings": []}
        )

    async def _process_armor_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["armor_absorption"], "warnings": []}
        )

    async def _process_tool_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["tool_operation"], "warnings": []}
        )

    async def _process_consumable_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["consumable_applied"], "warnings": []}
        )

    async def _process_augmetic_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["augmetic_interface"], "warnings": []}
        )

    async def _process_relic_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["relic_activation"], "warnings": []}
        )

    async def _process_transport_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["transport_traversal"], "warnings": []}
        )

    async def _process_communication_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["communication_link"], "warnings": []}
        )

    async def _process_medical_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["medical_aid"], "warnings": []}
        )

    async def _process_sensor_usage(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], expected_duration: int
    ) -> StandardResponse:
        return StandardResponse(
            success=True, data={"effects": ["sensor_scan"], "warnings": []}
        )

    async def register_equipment(
        self,
        equipment_item: EquipmentItem,
        agent_id: str,
        initial_status: EquipmentStatus = EquipmentStatus.READY,
    ) -> StandardResponse:
        """
        STANDARD EQUIPMENT REGISTRATION RITUAL ENHANCED BY INVENTORY SANCTIFICATION

        Register enhanced equipment item with the system, enabling
        dynamic tracking and state management.
        """
        try:
            async with self._processing_lock:
                # Create enhanced dynamic equipment wrapper
                dynamic_equipment = DynamicEquipment(
                    base_equipment=equipment_item,
                    current_status=initial_status,
                    current_user=agent_id,
                )

                # Initialize enhanced location history
                current_location = getattr(equipment_item, "current_location", None) or "Unknown"
                dynamic_equipment.location_history.append(
                    (datetime.now(), current_location)
                )

                # Register enhanced equipment
                eq_id = getattr(equipment_item, "equipment_id", None) or getattr(equipment_item, "item_id", "unknown")
                eq_id = eq_id if eq_id is not None else "unknown"
                self._equipment_registry[eq_id] = dynamic_equipment

                # Associate enhanced equipment with agent
                if agent_id not in self._agent_equipment:
                    self._agent_equipment[agent_id] = []
                self._agent_equipment[agent_id].append(str(eq_id))

                # Schedule enhanced initial maintenance if applicable
                category = getattr(equipment_item, "category", None)
                category_value = category.value if category else ""
                if self.auto_maintenance and category_value not in ["consumable"]:
                    next_maintenance = datetime.now() + timedelta(
                        hours=self.maintenance_interval_hours
                    )
                    self._maintenance_queue.append(
                        (next_maintenance, str(eq_id))
                    )
                    self._maintenance_queue.sort(key=lambda x: x[0])

                # Apply enhanced equipment template enhancements
                template_result = await self._apply_equipment_template(  # type: ignore[attr-defined]
                    dynamic_equipment
                )

                self.system_metrics["total_equipment_tracked"] += 1
                if initial_status == EquipmentStatus.ACTIVE:
                    self.system_metrics["active_equipment"] += 1

                logger.info(
                    f"EQUIPMENT REGISTERED: {eq_id} for {agent_id}"
                )

                return ResponseBuilder.success(
                    data={
                        "equipment_id": eq_id,
                        "agent_id": agent_id,
                        "initial_status": initial_status.value,
                        "template_applied": (
                            template_result.success if template_result else False
                        ),
                        "maintenance_scheduled": self.auto_maintenance,
                    },
                    metadata={"blessing": "equipment_registered_successfully"},
                )

        except Exception as e:
            logger.error(f"EQUIPMENT REGISTRATION FAILED: {e}")
            return ResponseBuilder.error(
                code="EQUIPMENT_REGISTRATION_FAILED",
                message=f"Equipment registration failed: {str(e)}",
                recoverable=True,
                details={
                    "standard_guidance": "Check equipment data format and system state"
                },
            )

    async def use_equipment(
        self,
        equipment_id: str,
        agent_id: str,
        usage_context: Dict[str, Any],
        expected_duration: int = 60,
    ) -> StandardResponse:
        """
        STANDARD EQUIPMENT USAGE RITUAL ENHANCED BY OPERATIONAL SANCTIFICATION

        Execute enhanced equipment usage with real-time state tracking,
        wear accumulation, and performance impact analysis.
        """
        try:
            async with self._processing_lock:
                # Retrieve enhanced equipment
                equipment, error = EquipmentValidator.validate_exists(
                    self._equipment_registry, equipment_id, "in registry"
                )
                if error:
                    return error
                if equipment is None:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_NOT_FOUND",
                            message=f"Equipment '{equipment_id}' not found",
                        ),
                    )

                # Validate enhanced usage authorization
                if (
                    equipment.current_user != agent_id
                    and equipment.current_status
                    not in [EquipmentStatus.READY, EquipmentStatus.STANDBY]
                ):
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_USAGE_UNAUTHORIZED",
                            message=f"Equipment '{equipment_id}' not available for use by {agent_id}",
                        ),
                    )

                # Check enhanced equipment condition
                if equipment.base_equipment.condition == EquipmentCondition.BROKEN:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_BROKEN",
                            message=f"Equipment '{equipment_id}' is broken and cannot be used",
                        ),
                    )

                usage_start = datetime.now()

                # Update enhanced usage state
                equipment.current_status = EquipmentStatus.ACTIVE
                equipment.current_user = agent_id
                equipment.last_used = usage_start

                # Process enhanced category-specific usage
                eq_category = getattr(equipment.base_equipment, "category", None)
                eq_category_value = eq_category.value if eq_category else ""
                category_processor = self._category_processors.get(
                    EquipmentCategory(eq_category_value) if eq_category_value else EquipmentCategory.TOOL
                )

                usage_result = {"success": True, "effects": [], "warnings": []}

                if category_processor:
                    processor_result = await category_processor(
                        equipment, usage_context, expected_duration
                    )
                    if not processor_result.success:
                        usage_result["success"] = False
                        error_msg = processor_result.error.message if processor_result.error else "Unknown error"
                        usage_result["error"] = error_msg
                    else:
                        usage_result.update(processor_result.data or {})

                # Calculate enhanced wear accumulation
                wear_factor = self._calculate_wear_factor(  # type: ignore[attr-defined]
                    equipment, usage_context, expected_duration
                )
                equipment.wear_accumulation = min(
                    1.0, equipment.wear_accumulation + wear_factor
                )

                # Update enhanced performance metrics based on wear
                self._update_performance_from_wear(equipment)  # type: ignore[attr-defined]

                # Update enhanced usage statistics
                equipment.usage_statistics["total_uses"] += 1
                if usage_result["success"]:
                    equipment.usage_statistics["successful_uses"] += 1

                # Categorize enhanced usage type
                usage_type = usage_context.get("usage_type", "general")
                if usage_type == "combat":
                    equipment.usage_statistics["combat_uses"] += 1
                elif usage_type == "ritual":
                    equipment.usage_statistics["ritual_uses"] += 1

                # Check enhanced system core response
                spirit_response = self._evaluate_system_core_response(  # type: ignore[attr-defined]
                    equipment, usage_context
                )
                equipment.system_core_mood = spirit_response["mood"]

                # Apply enhanced blessing effects if applicable
                if usage_context.get("enhanced_usage", False):
                    equipment.blessing_level = min(1.2, equipment.blessing_level + 0.05)
                    equipment.standard_rites_performed += 1
                    self.system_metrics["standard_rites_performed"] += 1

                # Return enhanced equipment to appropriate state
                if usage_result["success"]:
                    equipment.current_status = EquipmentStatus.READY
                else:
                    equipment.current_status = EquipmentStatus.DAMAGED
                    self.system_metrics["equipment_failures"] += 1

                usage_duration = (datetime.now() - usage_start).total_seconds()

                logger.info(
                    f"EQUIPMENT USED: {equipment_id} by {agent_id} ({'SUCCESS' if usage_result['success'] else 'FAILED'})"
                )

                if usage_result["success"]:
                    return ResponseBuilder.success(
                        data={
                            "equipment_id": equipment_id,
                            "agent_id": agent_id,
                            "usage_duration_seconds": usage_duration,
                            "usage_effects": usage_result.get("effects", []),
                            "wear_accumulation": equipment.wear_accumulation,
                            "performance_impact": equipment.performance_metrics,
                            "system_core_mood": equipment.system_core_mood,
                            "blessing_level": equipment.blessing_level,
                        },
                        metadata={"blessing": "equipment_usage_processed"},
                    )
                else:
                    return ResponseBuilder.error(
                        code="EQUIPMENT_USAGE_FAILED",
                        message="Equipment usage failed during processing",
                        recoverable=True,
                        details={"error": usage_result.get("error", "Unknown error")},
                    )

        except Exception as e:
            logger.error(f"EQUIPMENT USAGE FAILED: {e}")
            return ResponseBuilder.operation_failed(
                "equipment usage", e, recoverable=True
            )

    async def perform_maintenance(
        self,
        equipment_id: str,
        maintenance_type: str = "routine",
        performed_by: str = "tech_priest",
    ) -> StandardResponse:
        """
        STANDARD MAINTENANCE RITUAL ENHANCED BY system core APPEASEMENT

        Perform enhanced maintenance on equipment with ritual protocols,
        condition restoration, and performance optimization.
        """
        try:
            async with self._processing_lock:
                # Retrieve enhanced equipment
                equipment, error = EquipmentValidator.validate_exists(
                    self._equipment_registry, equipment_id, "for maintenance"
                )
                if error:
                    return error
                if equipment is None:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_NOT_FOUND",
                            message=f"Equipment '{equipment_id}' not found for maintenance",
                        ),
                    )

                maintenance_start = datetime.now()

                # Record enhanced pre-maintenance condition
                condition_before = equipment.base_equipment.condition

                # Set enhanced maintenance status
                equipment.current_status = EquipmentStatus.MAINTENANCE

                # Create enhanced maintenance record
                maintenance_record = EquipmentMaintenance(
                    maintenance_id=f"{equipment_id}_maintenance_{maintenance_start.strftime('%Y%m%d_%H%M%S')}",
                    equipment_id=equipment_id,
                    maintenance_type=maintenance_type,
                    performed_by=performed_by,
                    performed_at=maintenance_start,
                    condition_before=condition_before,
                )

                # Perform enhanced maintenance procedures
                maintenance_effects = await self._execute_maintenance_procedures(  # type: ignore[attr-defined]
                    equipment, maintenance_type, maintenance_record
                )

                # Calculate enhanced maintenance duration
                maintenance_duration = max(
                    30, int(60 + equipment.wear_accumulation * 120)
                )
                maintenance_record.duration_minutes = maintenance_duration

                # Apply enhanced condition improvements
                condition_improvement = self._calculate_condition_improvement(  # type: ignore[attr-defined]
                    equipment, maintenance_type, maintenance_effects
                )

                new_condition = self._improve_equipment_condition(  # type: ignore[attr-defined]
                    condition_before, condition_improvement
                )
                equipment.base_equipment.condition = new_condition
                maintenance_record.condition_after = new_condition

                # Reduce enhanced wear accumulation
                wear_reduction = min(
                    equipment.wear_accumulation,
                    0.3 + (0.2 if maintenance_type == "overhaul" else 0.0),
                )
                equipment.wear_accumulation = max(
                    0.0, equipment.wear_accumulation - wear_reduction
                )

                # Improve enhanced performance metrics
                self._apply_maintenance_performance_boost(equipment, maintenance_type)  # type: ignore[attr-defined]

                # Appease enhanced system core
                spirit_improvement = self._appease_system_core(  # type: ignore[attr-defined]
                    equipment, maintenance_type
                )
                equipment.system_core_mood = spirit_improvement["new_mood"]
                maintenance_record.system_core_response = spirit_improvement["response"]

                # Schedule enhanced next maintenance
                if self.auto_maintenance:
                    next_maintenance_hours = self.maintenance_interval_hours
                    if maintenance_type == "overhaul":
                        next_maintenance_hours *= 2  # Overhauls last longer

                    next_maintenance = maintenance_start + timedelta(
                        hours=next_maintenance_hours
                    )
                    maintenance_record.next_maintenance_due = next_maintenance

                    # Update enhanced maintenance queue
                    self._maintenance_queue = [
                        (time, eq_id)
                        for time, eq_id in self._maintenance_queue
                        if eq_id != equipment_id
                    ]
                    self._maintenance_queue.append((next_maintenance, equipment_id))
                    self._maintenance_queue.sort(key=lambda x: x[0])

                # Add enhanced maintenance record to history
                equipment.maintenance_history.append(maintenance_record)
                equipment.usage_statistics["maintenance_cycles"] += 1

                # Return enhanced equipment to service
                equipment.current_status = EquipmentStatus.READY

                # Update enhanced system metrics
                self.system_metrics["maintenance_operations"] += 1
                if condition_before != new_condition:
                    self.system_metrics["equipment_repairs"] += 1

                logger.info(
                    f"MAINTENANCE COMPLETED: {equipment_id} ({maintenance_type}) - {condition_before.value} -> {new_condition.value}"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "equipment_id": equipment_id,
                        "maintenance_type": maintenance_type,
                        "duration_minutes": maintenance_duration,
                        "condition_before": condition_before.value,
                        "condition_after": new_condition.value,
                        "wear_reduction": wear_reduction,
                        "performance_boost": maintenance_effects.get(
                            "performance_boost", 0.0
                        ),
                        "system_core_response": spirit_improvement["response"],
                        "next_maintenance_due": (
                            next_maintenance.isoformat()
                            if self.auto_maintenance
                            else None
                        ),
                        "procedures_completed": maintenance_record.procedures_completed,
                    },
                    metadata={"blessing": "maintenance_ritual_completed"},
                )

        except Exception as e:
            logger.error(f"MAINTENANCE RITUAL FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MAINTENANCE_FAILED",
                    message=f"Maintenance ritual failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def apply_modification(
        self, equipment_id: str, modification: EquipmentModification, installer: str
    ) -> StandardResponse:
        """
        STANDARD MODIFICATION RITUAL ENHANCED BY TECHNOLOGICAL ENHANCEMENT

        Apply enhanced modification to equipment with stability analysis,
        performance impact evaluation, and system core compatibility.
        """
        try:
            async with self._processing_lock:
                # Retrieve enhanced equipment
                equipment, error = EquipmentValidator.validate_exists(
                    self._equipment_registry, equipment_id, "for modification"
                )
                if error:
                    return error
                if equipment is None:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_NOT_FOUND",
                            message=f"Equipment '{equipment_id}' not found for modification",
                        ),
                    )

                # Validate enhanced equipment condition
                if equipment.base_equipment.condition == EquipmentCondition.BROKEN:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_TOO_DAMAGED",
                            message="Cannot modify broken equipment - repair required first",
                        ),
                    )

                # Check enhanced modification compatibility
                compatibility_check = self._check_modification_compatibility(  # type: ignore[attr-defined]
                    equipment, modification
                )
                if not compatibility_check.get("compatible"):
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="MODIFICATION_INCOMPATIBLE",
                            message=f"Modification incompatible: {compatibility_check.get('reason', 'Unknown')}",
                        ),
                    )

                modification_start = datetime.now()

                # Set enhanced modification status
                equipment.current_status = EquipmentStatus.MAINTENANCE

                # Apply enhanced modification
                modification.installed_by = installer
                modification.installation_date = modification_start

                # Calculate enhanced installation effects
                installation_effects = await self._install_modification(  # type: ignore[attr-defined]
                    equipment, modification
                )

                if installation_effects["success"]:
                    # Add enhanced modification to equipment
                    equipment.modifications.append(modification)

                    # Apply enhanced performance impacts
                    for metric, impact in modification.performance_impact.items():
                        if metric in equipment.performance_metrics:
                            equipment.performance_metrics[metric] = max(
                                0.1,
                                min(
                                    2.0, equipment.performance_metrics[metric] + impact
                                ),
                            )

                    # Evaluate enhanced system core compatibility
                    spirit_compatibility = modification.system_core_compatibility
                    if spirit_compatibility < 0.8:
                        equipment.system_core_mood = "agitated"
                        equipment.performance_metrics["reliability"] *= 0.95
                    elif spirit_compatibility > 1.1:
                        equipment.system_core_mood = "pleased"
                        equipment.performance_metrics["reliability"] *= 1.05

                    # Update enhanced system metrics
                    self.system_metrics["modifications_applied"] += 1

                    # Return enhanced equipment to service
                    equipment.current_status = EquipmentStatus.READY

                    logger.info(
                        f"MODIFICATION APPLIED: {modification.modification_name} to {equipment_id}"
                    )

                    return StandardResponse(
                        success=True,
                        data={
                            "equipment_id": equipment_id,
                            "modification_id": modification.modification_id,
                            "modification_name": modification.modification_name,
                            "performance_impacts": modification.performance_impact,
                            "stability_rating": modification.stability_rating,
                            "system_core_compatibility": spirit_compatibility,
                            "installation_effects": installation_effects["effects"],
                            "new_performance_metrics": equipment.performance_metrics,
                        },
                        metadata={"blessing": "modification_successfully_applied"},
                    )
                else:
                    # Blessed modification failed
                    equipment.current_status = EquipmentStatus.DAMAGED
                    self.system_metrics["equipment_failures"] += 1

                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="MODIFICATION_INSTALLATION_FAILED",
                            message=f"Modification installation failed: {installation_effects['error']}",
                        ),
                    )

        except Exception as e:
            logger.error(f"MODIFICATION RITUAL FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MODIFICATION_FAILED",
                    message=f"Equipment modification failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def get_equipment_status(self, equipment_id: str) -> StandardResponse:
        """
        STANDARD EQUIPMENT STATUS QUERY ENHANCED BY COMPREHENSIVE AWARENESS

        Retrieve enhanced comprehensive equipment status with real-time
        metrics, condition assessment, and predictive analysis.
        """
        try:
            equipment, error = EquipmentValidator.validate_exists(
                self._equipment_registry, equipment_id, "in registry"
            )
            if error:
                return error
            if equipment is None:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="EQUIPMENT_NOT_FOUND",
                        message=f"Equipment '{equipment_id}' not found",
                    ),
                )

            # Calculate enhanced predictive metrics
            predicted_failure = self._predict_equipment_failure(equipment)  # type: ignore[attr-defined]
            next_maintenance = self._get_next_maintenance_due(equipment_id)  # type: ignore[attr-defined]

            # Compile enhanced comprehensive status
            base_eq = equipment.base_equipment
            eq_category = getattr(base_eq, "category", None)
            eq_location = getattr(base_eq, "current_location", None)
            status_data = {
                "equipment_id": equipment_id,
                "name": base_eq.name,
                "category": eq_category.value if eq_category else "",
                "condition": base_eq.condition.value if hasattr(base_eq.condition, "value") else str(base_eq.condition),
                "status": equipment.current_status.value,
                "current_user": equipment.current_user,
                "location": eq_location,
                "last_used": (
                    equipment.last_used.isoformat() if equipment.last_used else None
                ),
                "wear_accumulation": equipment.wear_accumulation,
                "performance_metrics": equipment.performance_metrics,
                "usage_statistics": equipment.usage_statistics,
                "system_core_mood": equipment.system_core_mood,
                "blessing_level": equipment.blessing_level,
                "modifications_count": len(equipment.modifications),
                "maintenance_cycles": len(equipment.maintenance_history),
                "predicted_failure_risk": predicted_failure.get("risk_score", 0.0),
                "predicted_failure_timeframe": predicted_failure.get("timeframe_days", 0),
                "next_maintenance_due": (
                    next_maintenance.isoformat() if next_maintenance else None
                ),
                "standard_rites_performed": equipment.standard_rites_performed,
            }

            return StandardResponse(
                success=True,
                data=status_data,
                metadata={"blessing": "equipment_status_retrieved"},
            )

        except Exception as e:
            logger.error(f"EQUIPMENT STATUS QUERY FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="EQUIPMENT_STATUS_FAILED", message=str(e)),
            )

    async def get_agent_equipment(
        self, agent_id: str, include_details: bool = False
    ) -> StandardResponse:
        """
        STANDARD AGENT EQUIPMENT INVENTORY ENHANCED BY COMPREHENSIVE TRACKING

        Retrieve enhanced comprehensive equipment inventory for agent
        with optional detailed status information.
        """
        try:
            agent_equipment_ids = self._agent_equipment.get(agent_id, [])

            if not agent_equipment_ids:
                return StandardResponse(
                    success=True,
                    data={
                        "agent_id": agent_id,
                        "equipment": [],
                        "equipment_count": 0,
                        "categories": {},
                    },
                    metadata={"blessing": "empty_inventory_retrieved"},
                )

            equipment_list: list[Any] = []
            category_counts: dict[Any, Any] = {}
            for equipment_id in agent_equipment_ids:
                equipment = self._equipment_registry.get(equipment_id)
                if equipment:
                    # Count enhanced categories
                    eq_category = getattr(equipment.base_equipment, "category", None)
                    category = eq_category.value if eq_category else ""
                    category_counts[category] = category_counts.get(category, 0) + 1

                    if include_details:
                        # Get enhanced detailed status
                        status_result = await self.get_equipment_status(equipment_id)
                        if status_result.success:
                            equipment_list.append(status_result.data)
                    else:
                        # Get enhanced basic information
                        equipment_list.append(
                            {
                                "equipment_id": equipment_id,
                                "name": equipment.base_equipment.name,
                                "category": category,
                                "condition": equipment.base_equipment.condition.value if hasattr(equipment.base_equipment.condition, "value") else str(equipment.base_equipment.condition),
                                "status": equipment.current_status.value,
                                "wear_accumulation": equipment.wear_accumulation,
                            }
                        )

            return StandardResponse(
                success=True,
                data={
                    "agent_id": agent_id,
                    "equipment": equipment_list,
                    "equipment_count": len(equipment_list),
                    "categories": category_counts,
                    "active_equipment": len(
                        [eq for eq in equipment_list if eq.get("status") == "active"]
                    ),
                    "damaged_equipment": len(
                        [
                            eq
                            for eq in equipment_list
                            if eq.get("condition") in ["damaged", "broken"]
                        ]
                    ),
                },
                metadata={"blessing": "agent_inventory_retrieved"},
            )

        except Exception as e:
            logger.error(f"AGENT EQUIPMENT QUERY FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="AGENT_EQUIPMENT_FAILED", message=str(e)),
            )

    def get_system_statistics(self) -> Dict[str, Any]:
        """Get enhanced equipment system statistics"""
        # Calculate enhanced average reliability
        if self._equipment_registry:
            total_reliability = sum(
                eq.performance_metrics.get("reliability", 0.9)
                for eq in self._equipment_registry.values()
            )
            self.system_metrics["average_equipment_reliability"] = (
                total_reliability / len(self._equipment_registry)
            )

        return {
            **self.system_metrics,
            "registered_equipment": len(self._equipment_registry),
            "agents_with_equipment": len(self._agent_equipment),
            "maintenance_queue_size": len(self._maintenance_queue),
            "equipment_categories": len(EquipmentCategory),
            "equipment_templates": len(self._equipment_templates),
        }
