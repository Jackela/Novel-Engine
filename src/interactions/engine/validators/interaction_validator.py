#!/usr/bin/env python3
"""
Interaction context validation and prerequisite checking.
"""

import logging

from src.core.data_models import ErrorInfo, StandardResponse
from src.interactions.interaction_engine_system.core.types import (
    InteractionContext,
    InteractionType,
)

logger = logging.getLogger(__name__)


class InteractionValidator:
    """Validates interaction contexts and prerequisites."""

    async def _validate_interaction_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Validate enhanced interaction context completeness and consistency"""
        errors = []
        warnings = []

        # Check enhanced required fields
        if not context.interaction_id:
            errors.append("Interaction ID is required")

        if not context.participants:
            errors.append("At least one participant is required")

        if context.interaction_type not in InteractionType:
            errors.append(f"Invalid interaction type: {context.interaction_type}")

        # Check enhanced participant existence
        for participant in context.participants:
            # This would check against registered agents in a real system
            if not participant:
                errors.append(f"Empty participant ID: {participant}")

        # Check enhanced resource requirements
        for resource, requirement in context.resource_requirements.items():
            if isinstance(requirement, dict) and "required" in requirement:
                if requirement["required"] and not requirement.get("available", False):
                    warnings.append(f"Required resource not available: {resource}")

        if errors:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTERACTION_VALIDATION_FAILED",
                    message=f"Validation errors: {'; '.join(errors)}",
                ),
            )

        if warnings:
            return StandardResponse(
                success=True,
                data={"warnings": warnings},
                metadata={"blessing": "validation_completed_with_warnings"},
            )

        return StandardResponse(
            success=True, metadata={"blessing": "validation_successful"}
        )

    async def _check_prerequisites(
        self, context: InteractionContext
    ) -> StandardResponse:
        """Check enhanced interaction prerequisites and requirements"""
        if not context.prerequisites:
            return StandardResponse(
                success=True, metadata={"blessing": "no_prerequisites"}
            )

        unmet_prerequisites = []

        for prerequisite in context.prerequisites:
            # This would implement actual prerequisite checking logic
            # For now, we'll simulate basic checks
            if prerequisite.startswith("agent_state:"):
                # Check agent state requirements
                agent_id, required_state = prerequisite.split(":", 1)[1].split("=")
                # Placeholder logic - would check actual agent state
                if agent_id not in context.participants:
                    unmet_prerequisites.append(f"Agent {agent_id} not in participants")

            elif prerequisite.startswith("location:"):
                # Check location requirements
                required_location = prerequisite.split(":", 1)[1]
                if context.location != required_location:
                    unmet_prerequisites.append(
                        f"Wrong location: expected {required_location}, got {context.location}"
                    )

            elif prerequisite.startswith("time:"):
                # Check temporal requirements
                prerequisite.split(":", 1)[1]
                # Placeholder logic for time checks

        if unmet_prerequisites:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PREREQUISITES_NOT_MET",
                    message=f"Unmet prerequisites: {'; '.join(unmet_prerequisites)}",
                ),
            )

        return StandardResponse(
            success=True, metadata={"blessing": "prerequisites_satisfied"}
        )
