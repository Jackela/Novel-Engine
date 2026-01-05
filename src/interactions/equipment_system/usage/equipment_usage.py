"""
Equipment Usage Processor
========================

Equipment usage processing, wear calculation, and performance degradation system.
Handles category-specific usage patterns and system core interactions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..core.types import (
    DynamicEquipment,
    EquipmentCategory,
    EquipmentStatus,
    EquipmentSystemConfig,
)

# Import enhanced core systems
try:
    from src.core.data_models import EquipmentCondition, ErrorInfo, StandardResponse
    from src.core.types import AgentID
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

    AgentID = str

    class EquipmentCondition:
        EXCELLENT = "excellent"
        GOOD = "good"
        FAIR = "fair"
        POOR = "poor"
        DAMAGED = "damaged"
        BROKEN = "broken"


__all__ = ["EquipmentUsageProcessor"]


class EquipmentUsageProcessor:
    """
    Equipment Usage and Wear Processing System

    Responsibilities:
    - Process equipment usage across all categories
    - Calculate wear accumulation and performance degradation
    - Handle category-specific usage effects
    - Track usage statistics and patterns
    - Manage system core responses to usage
    """

    def __init__(
        self, config: EquipmentSystemConfig, logger: Optional[logging.Logger] = None
    ):
        """
        Initialize equipment usage processor.

        Args:
            config: Equipment system configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Usage processing state
        self._processing_lock = asyncio.Lock()
        self._active_usage_sessions: Dict[str, Dict[str, Any]] = {}

        # Category-specific usage handlers
        self._category_handlers = {
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

        self.logger.info("Equipment usage processor initialized")

    async def process_equipment_usage(
        self,
        equipment: DynamicEquipment,
        agent_id: str,
        usage_context: Dict[str, Any],
        duration_seconds: float = 60.0,
    ) -> StandardResponse:
        """
        Process equipment usage with category-specific handling.

        Args:
            equipment: Equipment being used
            agent_id: Agent using the equipment
            usage_context: Context information about usage
            duration_seconds: Duration of usage

        Returns:
            StandardResponse with usage results
        """
        try:
            async with self._processing_lock:
                # Validate equipment status
                if equipment.current_status not in [
                    EquipmentStatus.READY,
                    EquipmentStatus.ACTIVE,
                ]:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_NOT_AVAILABLE",
                            message=f"Equipment '{equipment.equipment_id}' is not available for use (status: {equipment.current_status.value})",
                        ),
                    )

                # Set equipment to active during usage
                original_status = equipment.current_status
                equipment.current_status = EquipmentStatus.ACTIVE

                usage_start = datetime.now()

                # Determine equipment category for specific processing
                category = self._determine_equipment_category(equipment)

                # Process category-specific usage
                usage_handler = self._category_handlers.get(
                    category, self._process_generic_usage
                )
                usage_result = await usage_handler(
                    equipment, usage_context, duration_seconds
                )

                # Calculate wear and performance effects
                wear_factor = self._calculate_wear_factor(
                    equipment, usage_context, duration_seconds
                )
                equipment.wear_accumulation = min(
                    1.0, equipment.wear_accumulation + wear_factor
                )

                # Update performance metrics
                self._update_performance_from_wear(equipment)

                # Update usage statistics
                self._update_usage_statistics(equipment, duration_seconds, usage_result)

                # Handle system core response
                spirit_response = self._evaluate_system_core_response(
                    equipment, usage_context
                )
                equipment.system_core_mood = spirit_response["mood"]

                # Update timestamps
                equipment.last_used = usage_start

                # Restore equipment status (or set to maintenance if critically worn)
                if equipment.wear_accumulation >= self.config.wear_threshold:
                    equipment.current_status = EquipmentStatus.MAINTENANCE
                else:
                    equipment.current_status = original_status

                usage_duration = (datetime.now() - usage_start).total_seconds()

                self.logger.info(
                    f"Equipment '{equipment.equipment_id}' used by '{agent_id}' for {usage_duration:.2f}s"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "equipment_id": equipment.equipment_id,
                        "agent_id": agent_id,
                        "category": category.value,
                        "usage_duration_seconds": usage_duration,
                        "usage_effects": usage_result.get("effects", []),
                        "wear_accumulation": equipment.wear_accumulation,
                        "performance_impact": equipment.performance_metrics,
                        "system_core_mood": equipment.system_core_mood,
                        "new_status": equipment.current_status.value,
                    },
                    metadata={"blessing": "equipment_usage_processed"},
                )

        except Exception as e:
            self.logger.error(f"Equipment usage processing failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="USAGE_PROCESSING_FAILED",
                    message=f"Usage processing failed: {str(e)}",
                    recoverable=True,
                ),
            )

    # Category-specific usage processors

    async def _process_weapon_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process weapon-specific usage."""
        shots_fired = usage_context.get("shots_fired", 1)
        target_hit = usage_context.get("target_hit", False)
        combat_intensity = usage_context.get(
            "intensity", "normal"
        )  # low, normal, high, extreme

        effects = []

        # Calculate weapon wear based on usage intensity
        intensity_multipliers = {"low": 0.5, "normal": 1.0, "high": 1.5, "extreme": 2.0}
        intensity_factor = intensity_multipliers.get(combat_intensity, 1.0)

        # Track accuracy for performance metrics
        if "accuracy_stats" not in equipment.usage_statistics:
            equipment.usage_statistics["accuracy_stats"] = {"shots": 0, "hits": 0}

        equipment.usage_statistics["accuracy_stats"]["shots"] += shots_fired
        if target_hit:
            equipment.usage_statistics["accuracy_stats"]["hits"] += 1
            effects.append("Target hit successfully")

        # Update weapon-specific performance metrics
        accuracy = equipment.usage_statistics["accuracy_stats"]["hits"] / max(
            1, equipment.usage_statistics["accuracy_stats"]["shots"]
        )
        equipment.performance_metrics["accuracy"] = accuracy
        equipment.performance_metrics["reliability"] *= (
            1 - 0.01 * intensity_factor
        )  # Small reliability degradation

        effects.append(
            f"Weapon fired {shots_fired} shots at {combat_intensity} intensity"
        )

        return {
            "effects": effects,
            "category_specific": {
                "shots_fired": shots_fired,
                "combat_intensity": combat_intensity,
                "current_accuracy": accuracy,
            },
        }

    async def _process_armor_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process armor-specific usage."""
        damage_taken = usage_context.get("damage_absorbed", 0)
        usage_context.get("protection_level", "standard")
        environmental_exposure = usage_context.get(
            "environment", "normal"
        )  # normal, harsh, extreme

        effects = []

        # Track damage absorption
        if "damage_stats" not in equipment.usage_statistics:
            equipment.usage_statistics["damage_stats"] = {
                "total_absorbed": 0,
                "protection_events": 0,
            }

        equipment.usage_statistics["damage_stats"]["total_absorbed"] += damage_taken
        if damage_taken > 0:
            equipment.usage_statistics["damage_stats"]["protection_events"] += 1
            effects.append(f"Absorbed {damage_taken} points of damage")

        # Environmental wear
        env_multipliers = {"normal": 1.0, "harsh": 1.3, "extreme": 2.0}
        env_factor = env_multipliers.get(environmental_exposure, 1.0)

        # Update armor-specific performance metrics
        equipment.performance_metrics["protection"] = max(
            0.1,
            equipment.performance_metrics.get("protection", 1.0) - damage_taken * 0.01,
        )
        equipment.performance_metrics["durability"] *= 1 - 0.005 * env_factor

        effects.append(f"Provided protection in {environmental_exposure} environment")

        return {
            "effects": effects,
            "category_specific": {
                "damage_absorbed": damage_taken,
                "environment": environmental_exposure,
                "protection_rating": equipment.performance_metrics.get(
                    "protection", 1.0
                ),
            },
        }

    async def _process_tool_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process tool-specific usage."""
        task_type = usage_context.get("task", "general")
        complexity = usage_context.get(
            "complexity", "normal"
        )  # simple, normal, complex, expert
        success_rate = usage_context.get("success", True)

        effects = []

        # Track tool performance
        if "task_stats" not in equipment.usage_statistics:
            equipment.usage_statistics["task_stats"] = {
                "tasks_completed": 0,
                "successful_tasks": 0,
            }

        equipment.usage_statistics["task_stats"]["tasks_completed"] += 1
        if success_rate:
            equipment.usage_statistics["task_stats"]["successful_tasks"] += 1
            effects.append(f"Successfully completed {complexity} {task_type} task")

        # Complexity affects wear
        complexity_multipliers = {
            "simple": 0.5,
            "normal": 1.0,
            "complex": 1.5,
            "expert": 2.0,
        }
        complexity_factor = complexity_multipliers.get(complexity, 1.0)

        # Update tool-specific performance metrics
        success_ratio = equipment.usage_statistics["task_stats"][
            "successful_tasks"
        ] / max(1, equipment.usage_statistics["task_stats"]["tasks_completed"])
        equipment.performance_metrics["effectiveness"] = success_ratio
        equipment.performance_metrics["precision"] = equipment.performance_metrics.get(
            "precision", 1.0
        ) * (1 - 0.01 * complexity_factor)

        effects.append(f"Tool used for {task_type} task at {complexity} complexity")

        return {
            "effects": effects,
            "category_specific": {
                "task_type": task_type,
                "complexity": complexity,
                "success_rate": success_ratio,
            },
        }

    async def _process_consumable_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process consumable-specific usage."""
        quantity_used = usage_context.get("quantity", 1)
        effectiveness = usage_context.get("effectiveness", 1.0)

        effects = []

        # Consumables have quantity-based usage
        current_quantity = equipment.usage_statistics.get(
            "remaining_quantity", 100
        )  # Default quantity
        new_quantity = max(0, current_quantity - quantity_used)
        equipment.usage_statistics["remaining_quantity"] = new_quantity

        effects.append(f"Consumed {quantity_used} units (remaining: {new_quantity})")

        # If depleted, mark as destroyed
        if new_quantity <= 0:
            equipment.current_status = EquipmentStatus.DESTROYED
            effects.append("Consumable depleted")

        return {
            "effects": effects,
            "category_specific": {
                "quantity_used": quantity_used,
                "remaining_quantity": new_quantity,
                "effectiveness": effectiveness,
            },
        }

    async def _process_augmetic_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process augmetic-specific usage."""
        return {
            "effects": ["Augmetic systems active"],
            "category_specific": {"integration_level": 1.0},
        }

    async def _process_relic_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process relic-specific usage."""
        return {
            "effects": ["Sacred relic activated"],
            "category_specific": {"blessing_power": 1.0},
        }

    async def _process_transport_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process transport-specific usage."""
        distance = usage_context.get("distance_traveled", 0)
        terrain = usage_context.get("terrain", "normal")

        effects = [f"Traveled {distance} units over {terrain} terrain"]

        return {
            "effects": effects,
            "category_specific": {
                "distance_traveled": distance,
                "terrain_type": terrain,
            },
        }

    async def _process_communication_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process communication-specific usage."""
        return {
            "effects": ["Communication established"],
            "category_specific": {"signal_strength": 1.0},
        }

    async def _process_medical_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process medical-specific usage."""
        return {
            "effects": ["Medical treatment applied"],
            "category_specific": {"healing_effectiveness": 1.0},
        }

    async def _process_sensor_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process sensor-specific usage."""
        return {
            "effects": ["Sensor sweep completed"],
            "category_specific": {"detection_accuracy": 1.0},
        }

    async def _process_generic_usage(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> Dict[str, Any]:
        """Process generic equipment usage."""
        return {"effects": ["Equipment used"], "category_specific": {}}

    # Helper methods

    def _calculate_wear_factor(
        self,
        equipment: DynamicEquipment,
        usage_context: Dict[str, Any],
        duration: float,
    ) -> float:
        """Calculate wear factor for equipment usage."""
        base_wear = self.config.wear_accumulation_rate

        # Duration factor (longer usage = more wear)
        duration_factor = min(2.0, duration / 3600.0)  # Cap at 2x for 1 hour+ usage

        # Intensity factor from context
        intensity = usage_context.get("intensity", "normal")
        intensity_multipliers = {"low": 0.5, "normal": 1.0, "high": 1.5, "extreme": 2.0}
        intensity_factor = intensity_multipliers.get(intensity, 1.0)

        # Equipment condition factor (poor condition wears faster)
        condition_multipliers = {
            "excellent": 0.8,
            "good": 1.0,
            "fair": 1.2,
            "poor": 1.5,
            "damaged": 2.0,
            "broken": 3.0,
        }
        condition = getattr(equipment.base_equipment, "condition", "good")
        if hasattr(condition, "value"):
            condition = condition.value
        condition_factor = condition_multipliers.get(condition, 1.0)

        # System core mood factor
        mood_multipliers = {
            "pleased": 0.8,
            "content": 1.0,
            "agitated": 1.2,
            "angry": 1.5,
        }
        mood_factor = mood_multipliers.get(equipment.system_core_mood, 1.0)

        total_wear = (
            base_wear
            * duration_factor
            * intensity_factor
            * condition_factor
            * mood_factor
        )

        return min(0.1, total_wear)  # Cap wear per use at 10%

    def _update_performance_from_wear(self, equipment: DynamicEquipment) -> None:
        """Update equipment performance metrics based on wear."""
        wear_impact = (
            equipment.wear_accumulation * 0.3
        )  # Max 30% performance loss from wear

        for metric in equipment.performance_metrics:
            # Apply wear-based degradation
            original_value = equipment.performance_metrics[metric]
            degraded_value = max(0.1, original_value * (1 - wear_impact))
            equipment.performance_metrics[metric] = degraded_value

    def _update_usage_statistics(
        self, equipment: DynamicEquipment, duration: float, usage_result: Dict[str, Any]
    ) -> None:
        """Update equipment usage statistics."""
        stats = equipment.usage_statistics

        # Update basic counters
        stats["total_uses"] = stats.get("total_uses", 0) + 1
        stats["total_duration"] = stats.get("total_duration", 0.0) + duration

        # Track successful usage
        if usage_result.get("success", True):
            stats["successful_uses"] = stats.get("successful_uses", 0) + 1
        else:
            stats["failures"] = stats.get("failures", 0) + 1
            stats["last_failure"] = datetime.now().isoformat()

        # Calculate usage frequency
        if equipment.last_used:
            time_since_last = (datetime.now() - equipment.last_used).total_seconds()
            if "usage_intervals" not in stats:
                stats["usage_intervals"] = []
            stats["usage_intervals"].append(time_since_last)

            # Keep only recent intervals (last 10 uses)
            if len(stats["usage_intervals"]) > 10:
                stats["usage_intervals"] = stats["usage_intervals"][-10:]

    def _evaluate_system_core_response(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Evaluate system core mood changes."""
        current_mood = equipment.system_core_mood

        # Mood transition logic
        usage_care = usage_context.get(
            "care_level", "normal"
        )  # poor, normal, excellent
        equipment_condition = getattr(equipment.base_equipment, "condition", "good")
        if hasattr(equipment_condition, "value"):
            equipment_condition = equipment_condition.value

        # Define mood transitions
        transitions = {
            "pleased": equipment.wear_accumulation < 0.2 and usage_care == "excellent",
            "content": equipment.wear_accumulation < 0.5
            and usage_care in ["normal", "excellent"],
            "agitated": equipment.wear_accumulation > 0.5 or usage_care == "poor",
            "angry": equipment.wear_accumulation > 0.8
            or equipment_condition in ["damaged", "broken"],
        }

        new_mood = current_mood
        for mood, condition in transitions.items():
            if condition and mood != current_mood:
                new_mood = mood
                break

        responses = {
            "pleased": "The system core hums with satisfaction",
            "content": "The system core remains cooperative",
            "agitated": "The system core shows signs of displeasure",
            "angry": "The system core rebels against poor treatment",
        }

        return {
            "mood": new_mood,
            "response": responses.get(new_mood, "System core status unknown"),
        }

    def _determine_equipment_category(
        self, equipment: DynamicEquipment
    ) -> EquipmentCategory:
        """Determine equipment category from equipment data."""
        # Try to get category from equipment item attributes
        if hasattr(equipment.base_equipment, "category"):
            try:
                return EquipmentCategory(equipment.base_equipment.category)
            except (ValueError, AttributeError):
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)
        name_lower = getattr(equipment.base_equipment, "name", "").lower()

        # Basic category inference
        category_keywords = {
            EquipmentCategory.WEAPON: [
                "weapon",
                "gun",
                "rifle",
                "pistol",
                "sword",
                "knife",
            ],
            EquipmentCategory.ARMOR: ["armor", "shield", "helmet", "vest"],
            EquipmentCategory.TOOL: ["tool", "wrench", "hammer", "kit"],
            EquipmentCategory.CONSUMABLE: ["ammo", "battery", "fuel", "med"],
            EquipmentCategory.AUGMETIC: ["augmetic", "implant", "cyber"],
            EquipmentCategory.RELIC: ["relic", "artifact", "sacred"],
            EquipmentCategory.TRANSPORT: ["vehicle", "transport", "bike"],
            EquipmentCategory.COMMUNICATION: ["vox", "comm", "radio"],
            EquipmentCategory.MEDICAL: ["medical", "medic", "heal"],
            EquipmentCategory.SENSOR: ["sensor", "scanner", "detector"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                return category

        # Default to TOOL category
        return EquipmentCategory.TOOL
