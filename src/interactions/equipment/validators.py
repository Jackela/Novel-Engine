#!/usr/bin/env python3
"""
Equipment Validation Utilities

Centralized validation patterns for equipment operations.
"""

from typing import Optional, Tuple

from src.core.data_models import StandardResponse
from src.core.utils import ResponseBuilder

from .models import DynamicEquipment


class EquipmentValidator:
    """Validation utilities for equipment operations."""

    @staticmethod
    def validate_exists(
        equipment_registry: dict,
        equipment_id: str,
        context: str = "",
    ) -> Tuple[Optional[DynamicEquipment], Optional[StandardResponse]]:
        """
        Validate equipment exists in registry.

        Args:
            equipment_registry: Equipment registry to check
            equipment_id: ID of equipment to validate
            context: Optional context for error message

        Returns:
            Tuple of (equipment, error_response) - one will always be None
            If equipment exists: (equipment, None)
            If equipment not found: (None, error_response)
        """
        equipment = equipment_registry.get(equipment_id)
        if not equipment:
            error_msg = f"Equipment '{equipment_id}' not found"
            if context:
                error_msg += f" {context}"
            error = ResponseBuilder.not_found("equipment", equipment_id)
            return None, error
        return equipment, None


__all__ = ["EquipmentValidator"]
