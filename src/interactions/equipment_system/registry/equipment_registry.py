"""
Equipment Registry
=================

Equipment registration and state management system for the dynamic equipment system.
Handles equipment registration, agent assignment, and equipment discovery.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ..core.types import (
    DynamicEquipment,
    EquipmentCategory,
    EquipmentItem,
    EquipmentStatus,
    EquipmentSystemConfig,
)

# Import enhanced core systems
try:
    from src.core.data_models import ErrorInfo, StandardResponse
    from src.core.types import AgentID
    from src.database.context_db import ContextDatabase
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
    ContextDatabase = type(
        "ContextDatabase", (), {"save_memory_item": lambda *args: None}
    )

__all__ = ["EquipmentRegistry"]


class EquipmentRegistry:
    """
    Equipment Registration and State Management System

    Responsibilities:
    - Equipment registration and deregistration
    - Agent equipment assignment and tracking
    - Equipment state management and queries
    - Equipment categorization and filtering
    """

    def __init__(
        self,
        config: EquipmentSystemConfig,
        context_db: Optional[ContextDatabase] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize equipment registry.

        Args:
            config: Equipment system configuration
            context_db: Optional context database for persistence
            logger: Optional logger instance
        """
        self.config = config
        self.context_db = context_db
        self.logger = logger or logging.getLogger(__name__)

        # Equipment storage
        self._equipment_registry: Dict[str, DynamicEquipment] = {}
        self._agent_equipment: Dict[str, Set[str]] = {}  # agent_id -> equipment_ids
        self._equipment_by_category: Dict[EquipmentCategory, Set[str]] = {
            category: set() for category in EquipmentCategory
        }

        # State tracking
        self._processing_lock = asyncio.Lock()
        self._equipment_locations: Dict[str, str] = {}
        self._equipment_assignments: Dict[str, str] = {}  # equipment_id -> agent_id

        self.logger.info("Equipment registry initialized")

    async def register_equipment(
        self,
        equipment_item: EquipmentItem,
        owner_id: Optional[str] = None,
        location: str = "",
        initial_status: EquipmentStatus = EquipmentStatus.READY,
    ) -> StandardResponse:
        """
        Register new equipment in the system.

        Args:
            equipment_item: Base equipment item to register
            owner_id: Optional initial owner/agent ID
            location: Equipment location
            initial_status: Initial equipment status

        Returns:
            StandardResponse with registration result
        """
        try:
            async with self._processing_lock:
                # Generate equipment ID if not provided
                equipment_id = getattr(equipment_item, "equipment_id", None)
                if not equipment_id:
                    equipment_id = f"eq_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

                # Check for duplicate registration
                if equipment_id in self._equipment_registry:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_ALREADY_REGISTERED",
                            message=f"Equipment '{equipment_id}' is already registered",
                            recoverable=False,
                        ),
                    )

                # Create dynamic equipment wrapper
                dynamic_equipment = DynamicEquipment(
                    equipment_id=equipment_id,
                    base_equipment=equipment_item,
                    owner_id=owner_id,
                    current_status=initial_status,
                    location=location,
                    assigned_agent=owner_id,
                )

                # Register in main registry
                self._equipment_registry[equipment_id] = dynamic_equipment

                # Update category tracking
                category = self._determine_equipment_category(equipment_item)
                self._equipment_by_category[category].add(equipment_id)

                # Update location tracking
                if location:
                    self._equipment_locations[equipment_id] = location

                # Update agent assignment
                if owner_id:
                    await self._assign_equipment_to_agent(equipment_id, owner_id)

                # Save to context database if available
                if self.context_db and self.config.context_db_enabled:
                    try:
                        await self._save_equipment_registration(dynamic_equipment)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to save equipment registration to database: {e}"
                        )

                self.logger.info(f"Equipment '{equipment_id}' registered successfully")

                return StandardResponse(
                    success=True,
                    data={
                        "equipment_id": equipment_id,
                        "category": category.value,
                        "status": initial_status.value,
                        "owner": owner_id,
                        "location": location,
                    },
                    metadata={"blessing": "equipment_registered"},
                )

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

    async def get_equipment(self, equipment_id: str) -> Optional[DynamicEquipment]:
        """Get equipment by ID."""
        return self._equipment_registry.get(equipment_id)

    async def get_agent_equipment(
        self,
        agent_id: str,
        category: Optional[EquipmentCategory] = None,
        status_filter: Optional[List[EquipmentStatus]] = None,
    ) -> Dict[str, Any]:
        """
        Get equipment assigned to a specific agent.

        Args:
            agent_id: Agent identifier
            category: Optional category filter
            status_filter: Optional status filters

        Returns:
            Dict with agent's equipment information
        """
        try:
            agent_equipment_ids = self._agent_equipment.get(agent_id, set())
            equipment_list = []

            for eq_id in agent_equipment_ids:
                equipment = self._equipment_registry.get(eq_id)
                if not equipment:
                    continue

                # Apply category filter
                if category:
                    eq_category = self._determine_equipment_category(
                        equipment.base_equipment
                    )
                    if eq_category != category:
                        continue

                # Apply status filter
                if status_filter and equipment.current_status not in status_filter:
                    continue

                equipment_info = {
                    "equipment_id": eq_id,
                    "name": equipment.base_equipment.name,
                    "category": self._determine_equipment_category(
                        equipment.base_equipment
                    ).value,
                    "status": equipment.current_status.value,
                    "condition": getattr(
                        equipment.base_equipment, "condition", "unknown"
                    ),
                    "wear_accumulation": equipment.wear_accumulation,
                    "last_used": (
                        equipment.last_used.isoformat() if equipment.last_used else None
                    ),
                    "location": equipment.location,
                    "performance_metrics": equipment.performance_metrics.copy(),
                    "modifications_count": len(equipment.modifications),
                }

                equipment_list.append(equipment_info)

            return {
                "agent_id": agent_id,
                "equipment_count": len(equipment_list),
                "equipment": equipment_list,
                "categories_represented": list(
                    set([eq["category"] for eq in equipment_list])
                ),
                "total_wear_average": sum(
                    [eq["wear_accumulation"] for eq in equipment_list]
                )
                / max(1, len(equipment_list)),
            }

        except Exception as e:
            self.logger.error(f"Error getting agent equipment: {e}")
            return {"agent_id": agent_id, "error": str(e)}

    async def assign_equipment(
        self, equipment_id: str, agent_id: str
    ) -> StandardResponse:
        """
        Assign equipment to an agent.

        Args:
            equipment_id: Equipment to assign
            agent_id: Agent to assign to

        Returns:
            StandardResponse with assignment result
        """
        try:
            async with self._processing_lock:
                equipment = self._equipment_registry.get(equipment_id)
                if not equipment:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_NOT_FOUND",
                            message=f"Equipment '{equipment_id}' not found for assignment",
                        ),
                    )

                # Check if equipment is available for assignment
                if equipment.current_status in [
                    EquipmentStatus.DESTROYED,
                    EquipmentStatus.MISSING,
                ]:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_UNAVAILABLE",
                            message=f"Equipment '{equipment_id}' is not available for assignment",
                        ),
                    )

                # Remove from previous agent if assigned
                if equipment.assigned_agent:
                    await self._unassign_equipment_from_agent(
                        equipment_id, equipment.assigned_agent
                    )

                # Assign to new agent
                await self._assign_equipment_to_agent(equipment_id, agent_id)
                equipment.assigned_agent = agent_id
                equipment.owner_id = agent_id

                self.logger.info(
                    f"Equipment '{equipment_id}' assigned to agent '{agent_id}'"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "equipment_id": equipment_id,
                        "assigned_to": agent_id,
                        "assignment_time": datetime.now().isoformat(),
                    },
                    metadata={"blessing": "equipment_assigned"},
                )

        except Exception as e:
            self.logger.error(f"Equipment assignment failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="ASSIGNMENT_FAILED",
                    message=f"Equipment assignment failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def update_equipment_status(
        self, equipment_id: str, new_status: EquipmentStatus, reason: str = ""
    ) -> StandardResponse:
        """
        Update equipment status.

        Args:
            equipment_id: Equipment to update
            new_status: New status
            reason: Optional reason for status change

        Returns:
            StandardResponse with update result
        """
        try:
            async with self._processing_lock:
                equipment = self._equipment_registry.get(equipment_id)
                if not equipment:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="EQUIPMENT_NOT_FOUND",
                            message=f"Equipment '{equipment_id}' not found for status update",
                        ),
                    )

                old_status = equipment.current_status
                equipment.current_status = new_status

                # Log status change
                status_change = {
                    "timestamp": datetime.now().isoformat(),
                    "from_status": old_status.value,
                    "to_status": new_status.value,
                    "reason": reason,
                }

                # Add to usage statistics
                if "status_changes" not in equipment.usage_statistics:
                    equipment.usage_statistics["status_changes"] = []
                equipment.usage_statistics["status_changes"].append(status_change)

                self.logger.info(
                    f"Equipment '{equipment_id}' status changed: {old_status.value} -> {new_status.value}"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "equipment_id": equipment_id,
                        "old_status": old_status.value,
                        "new_status": new_status.value,
                        "change_time": status_change["timestamp"],
                        "reason": reason,
                    },
                    metadata={"blessing": "status_updated"},
                )

        except Exception as e:
            self.logger.error(f"Status update failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="STATUS_UPDATE_FAILED",
                    message=f"Status update failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def get_equipment_by_category(self, category: EquipmentCategory) -> List[str]:
        """Get all equipment IDs in a specific category."""
        return list(self._equipment_by_category.get(category, set()))

    def get_all_equipment_ids(self) -> List[str]:
        """Get all registered equipment IDs."""
        return list(self._equipment_registry.keys())

    def get_equipment_count(self) -> int:
        """Get total count of registered equipment."""
        return len(self._equipment_registry)

    def get_category_counts(self) -> Dict[str, int]:
        """Get equipment counts by category."""
        return {
            category.value: len(equipment_ids)
            for category, equipment_ids in self._equipment_by_category.items()
        }

    # Private helper methods

    async def _assign_equipment_to_agent(
        self, equipment_id: str, agent_id: str
    ) -> None:
        """Add equipment to agent's equipment list."""
        if agent_id not in self._agent_equipment:
            self._agent_equipment[agent_id] = set()
        self._agent_equipment[agent_id].add(equipment_id)
        self._equipment_assignments[equipment_id] = agent_id

    async def _unassign_equipment_from_agent(
        self, equipment_id: str, agent_id: str
    ) -> None:
        """Remove equipment from agent's equipment list."""
        if agent_id in self._agent_equipment:
            self._agent_equipment[agent_id].discard(equipment_id)
            if not self._agent_equipment[agent_id]:
                del self._agent_equipment[agent_id]
        self._equipment_assignments.pop(equipment_id, None)

    def _determine_equipment_category(
        self, equipment_item: EquipmentItem
    ) -> EquipmentCategory:
        """Determine equipment category from equipment item."""
        # Try to get category from equipment item attributes
        if hasattr(equipment_item, "category"):
            try:
                return EquipmentCategory(equipment_item.category)
            except ValueError:
                pass

        # Fallback based on equipment name/type
        name_lower = getattr(equipment_item, "name", "").lower()

        # Basic category inference
        if any(
            word in name_lower
            for word in ["weapon", "gun", "rifle", "pistol", "sword", "knife"]
        ):
            return EquipmentCategory.WEAPON
        elif any(word in name_lower for word in ["armor", "shield", "helmet", "vest"]):
            return EquipmentCategory.ARMOR
        elif any(word in name_lower for word in ["tool", "wrench", "hammer", "kit"]):
            return EquipmentCategory.TOOL
        elif any(word in name_lower for word in ["ammo", "battery", "fuel", "med"]):
            return EquipmentCategory.CONSUMABLE
        elif any(word in name_lower for word in ["augmetic", "implant", "cyber"]):
            return EquipmentCategory.AUGMETIC
        elif any(word in name_lower for word in ["relic", "artifact", "sacred"]):
            return EquipmentCategory.RELIC
        elif any(word in name_lower for word in ["vehicle", "transport", "bike"]):
            return EquipmentCategory.TRANSPORT
        elif any(word in name_lower for word in ["vox", "comm", "radio"]):
            return EquipmentCategory.COMMUNICATION
        elif any(word in name_lower for word in ["medical", "medic", "heal"]):
            return EquipmentCategory.MEDICAL
        elif any(word in name_lower for word in ["sensor", "scanner", "detector"]):
            return EquipmentCategory.SENSOR

        # Default to TOOL category
        return EquipmentCategory.TOOL

    async def _save_equipment_registration(self, equipment: DynamicEquipment) -> None:
        """Save equipment registration to context database."""
        if not self.context_db:
            return

        # This would save equipment registration as a memory item
        # Implementation depends on the specific ContextDatabase interface
        pass
