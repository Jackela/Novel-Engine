"""
Modification System
==================

Equipment modification installation, compatibility checking, and enhancement management.
Handles modification installation, compatibility validation, and performance tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.types import (
    DynamicEquipment,
    EquipmentModification,
    EquipmentStatus,
    EquipmentSystemConfig,
)

# Import enhanced core systems
try:
    from src.core.data_models import ErrorInfo, StandardResponse
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


__all__ = ["ModificationSystem"]


class ModificationSystem:
    """
    Equipment Modification Management System

    Responsibilities:
    - Install and remove equipment modifications
    - Validate modification compatibility
    - Track modification effects on performance
    - Manage modification stacking and conflicts
    """

    def __init__(
        self, config: EquipmentSystemConfig, logger: Optional[logging.Logger] = None
    ):
        """Initialize modification system."""
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Modification templates and compatibility rules
        self._modification_templates = {
            "targeting_system": {
                "compatible_categories": ["weapon", "sensor"],
                "performance_impact": {"accuracy": 0.2, "effectiveness": 0.15},
                "conflicts_with": ["basic_scope"],
                "stability_rating": 0.9,
            },
            "reinforced_plating": {
                "compatible_categories": ["armor", "transport"],
                "performance_impact": {"durability": 0.25, "protection": 0.2},
                "conflicts_with": ["lightweight_alloy"],
                "stability_rating": 0.95,
            },
            "enhanced_motor": {
                "compatible_categories": ["tool", "weapon", "transport"],
                "performance_impact": {"efficiency": 0.3, "reliability": -0.05},
                "conflicts_with": ["power_saver"],
                "stability_rating": 0.8,
            },
        }

        self.logger.info("Modification system initialized")

    async def install_modification(
        self,
        equipment: DynamicEquipment,
        modification: EquipmentModification,
        installer: str = "tech_adept",
    ) -> StandardResponse:
        """
        Install modification on equipment with compatibility checking.

        Args:
            equipment: Equipment to modify
            modification: Modification to install
            installer: Who is installing the modification

        Returns:
            StandardResponse with installation result
        """
        try:
            # Check if modification limit would be exceeded
            if len(equipment.modifications) >= self.config.max_modifications_per_item:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="MODIFICATION_LIMIT_EXCEEDED",
                        message=f"Equipment already has maximum modifications ({self.config.max_modifications_per_item})",
                    ),
                )

            # Check compatibility if enabled
            if self.config.compatibility_checking:
                compatibility_result = self._check_modification_compatibility(
                    equipment, modification
                )
                if not compatibility_result["compatible"]:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="INCOMPATIBLE_MODIFICATION",
                            message=compatibility_result["reason"],
                            recoverable=False,
                        ),
                    )

            # Set equipment to maintenance during installation
            original_status = equipment.current_status
            equipment.current_status = EquipmentStatus.MAINTENANCE

            # Perform installation
            installation_result = await self._install_modification(
                equipment, modification, installer
            )

            # Apply modification effects
            self._apply_modification_effects(equipment, modification)

            # Add to equipment modifications list
            modification.installation_date = datetime.now()
            modification.installed_by = installer
            equipment.modifications.append(modification)

            # Update compatibility sets
            equipment.compatible_modifications.discard(modification.modification_id)
            if "conflicts_with" in installation_result:
                equipment.incompatible_with.update(
                    installation_result["conflicts_with"]
                )

            # Restore operational status
            equipment.current_status = original_status

            self.logger.info(
                f"Modification '{modification.modification_id}' installed on equipment '{equipment.equipment_id}'"
            )

            return StandardResponse(
                success=True,
                data={
                    "equipment_id": equipment.equipment_id,
                    "modification_id": modification.modification_id,
                    "installer": installer,
                    "installation_date": modification.installation_date.isoformat(),
                    "performance_impact": modification.performance_impact,
                    "stability_rating": modification.stability_rating,
                    "total_modifications": len(equipment.modifications),
                },
                metadata={"blessing": "modification_installed"},
            )

        except Exception as e:
            self.logger.error(f"Modification installation failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INSTALLATION_FAILED",
                    message=f"Modification installation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def get_compatible_modifications(self, equipment: DynamicEquipment) -> List[str]:
        """Get list of compatible modifications for equipment."""
        compatible = []
        equipment_category = self._get_equipment_category(equipment)

        for mod_id, template in self._modification_templates.items():
            # Skip if already installed
            if any(mod.modification_id == mod_id for mod in equipment.modifications):
                continue

            # Check category compatibility
            if equipment_category in template.get("compatible_categories", []):
                # Check for conflicts
                conflicts = template.get("conflicts_with", [])
                has_conflict = any(
                    any(
                        mod.modification_id == conflict
                        for mod in equipment.modifications
                    )
                    for conflict in conflicts
                )

                if not has_conflict:
                    compatible.append(mod_id)

        return compatible

    def _check_modification_compatibility(
        self, equipment: DynamicEquipment, modification: EquipmentModification
    ) -> Dict[str, Any]:
        """Check if modification is compatible with equipment."""
        mod_template = self._modification_templates.get(modification.modification_name)

        if not mod_template:
            return {
                "compatible": True,
                "reason": "Unknown modification - no compatibility rules",
            }

        # Check category compatibility
        equipment_category = self._get_equipment_category(equipment)
        compatible_categories = mod_template.get("compatible_categories", [])

        if equipment_category not in compatible_categories:
            return {
                "compatible": False,
                "reason": f"Modification not compatible with {equipment_category} equipment",
            }

        # Check for conflicts with existing modifications
        conflicts = mod_template.get("conflicts_with", [])
        for existing_mod in equipment.modifications:
            if existing_mod.modification_name in conflicts:
                return {
                    "compatible": False,
                    "reason": f"Conflicts with existing modification: {existing_mod.modification_name}",
                }

        return {"compatible": True, "reason": "Modification is compatible"}

    async def _install_modification(
        self,
        equipment: DynamicEquipment,
        modification: EquipmentModification,
        installer: str,
    ) -> Dict[str, Any]:
        """Perform the physical modification installation."""
        # Simulate installation process
        template = self._modification_templates.get(modification.modification_name, {})

        return {
            "success": True,
            "installation_time": 120,  # 2 hours
            "conflicts_with": template.get("conflicts_with", []),
            "stability_impact": template.get("stability_rating", 1.0),
        }

    def _apply_modification_effects(
        self, equipment: DynamicEquipment, modification: EquipmentModification
    ) -> None:
        """Apply modification performance effects to equipment."""
        # Apply performance impacts from modification
        for metric, impact in modification.performance_impact.items():
            if metric in equipment.performance_metrics:
                equipment.performance_metrics[metric] += impact
            else:
                equipment.performance_metrics[metric] = 1.0 + impact

        # Apply template effects if available
        template = self._modification_templates.get(modification.modification_name, {})
        template_impacts = template.get("performance_impact", {})

        for metric, impact in template_impacts.items():
            current_value = equipment.performance_metrics.get(metric, 1.0)
            equipment.performance_metrics[metric] = current_value + impact

    def _get_equipment_category(self, equipment: DynamicEquipment) -> str:
        """Get equipment category for compatibility checking."""
        # Try to get category from equipment
        if hasattr(equipment.base_equipment, "category"):
            return equipment.base_equipment.category

        # Fallback based on name
        name_lower = getattr(equipment.base_equipment, "name", "").lower()

        if any(word in name_lower for word in ["weapon", "gun", "rifle"]):
            return "weapon"
        elif any(word in name_lower for word in ["armor", "shield"]):
            return "armor"
        elif any(word in name_lower for word in ["tool", "kit"]):
            return "tool"

        return "generic"
