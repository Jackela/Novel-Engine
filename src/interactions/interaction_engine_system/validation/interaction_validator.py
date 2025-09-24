"""
Interaction Validator
====================

Interaction context validation, prerequisite checking, and constraint verification system.
Ensures interaction integrity and validates all requirements before processing.
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.types import (
    InteractionContext,
    InteractionEngineConfig,
    InteractionPriority,
    InteractionType,
)

# Import enhanced core systems
try:
    from src.core.data_models import (
        CharacterState,
        ErrorInfo,
        StandardResponse,
    )
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

    class ErrorInfo:
        def __init__(self, code="", message="", recoverable=True):
            self.code = code
            self.message = message
            self.recoverable = recoverable

    CharacterState = dict
    AgentID = str

__all__ = ["InteractionValidator"]


class InteractionValidator:
    """
    Interaction Context Validation and Prerequisite Checking System

    Responsibilities:
    - Validate interaction context completeness and correctness
    - Check participant availability and states
    - Verify prerequisites and constraints
    - Validate resource requirements
    - Assess risk factors and success criteria
    """

    def __init__(
        self,
        config: InteractionEngineConfig,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize interaction validator.

        Args:
            config: Interaction engine configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Validation rules and constraints
        self._validation_rules = {
            InteractionType.DIALOGUE: self._validate_dialogue_requirements,
            InteractionType.COMBAT: self._validate_combat_requirements,
            InteractionType.COOPERATION: self._validate_cooperation_requirements,
            InteractionType.NEGOTIATION: self._validate_negotiation_requirements,
            InteractionType.INSTRUCTION: self._validate_instruction_requirements,
            InteractionType.RITUAL: self._validate_ritual_requirements,
            InteractionType.EXPLORATION: self._validate_exploration_requirements,
            InteractionType.MAINTENANCE: self._validate_maintenance_requirements,
            InteractionType.EMERGENCY: self._validate_emergency_requirements,
        }

        # Required participant states by interaction type
        self._state_requirements = {
            InteractionType.DIALOGUE: {"conscious", "communicative"},
            InteractionType.COMBAT: {"conscious", "capable"},
            InteractionType.COOPERATION: {"conscious", "cooperative"},
            InteractionType.NEGOTIATION: {"conscious", "rational"},
            InteractionType.INSTRUCTION: {"conscious", "learning_capable"},
            InteractionType.RITUAL: {"conscious", "ritual_capable"},
            InteractionType.EXPLORATION: {"conscious", "mobile"},
            InteractionType.MAINTENANCE: {"conscious", "skilled"},
            InteractionType.EMERGENCY: {"conscious", "responsive"},
        }

        self.logger.info("Interaction validator initialized")

    async def validate_interaction_context(
        self, context: InteractionContext
    ) -> StandardResponse:
        """
        Comprehensive validation of interaction context.

        Args:
            context: Interaction context to validate

        Returns:
            StandardResponse with validation results
        """
        try:
            validation_results = []

            # Basic context validation
            basic_validation = self._validate_basic_context(context)
            if not basic_validation["valid"]:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INVALID_CONTEXT",
                        message=basic_validation["message"],
                        recoverable=False,
                    ),
                )
            validation_results.append("basic_context")

            # Participant validation
            participant_validation = await self._validate_participants(context)
            if not participant_validation["valid"]:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INVALID_PARTICIPANTS",
                        message=participant_validation["message"],
                        recoverable=True,
                    ),
                )
            validation_results.append("participants")

            # Type-specific validation
            type_validator = self._validation_rules.get(
                context.interaction_type
            )
            if type_validator:
                type_validation = await type_validator(context)
                if not type_validation["valid"]:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="TYPE_VALIDATION_FAILED",
                            message=type_validation["message"],
                            recoverable=True,
                        ),
                    )
                validation_results.append("type_specific")

            # Resource validation
            if self.config.enforce_resource_requirements:
                resource_validation = self._validate_resource_requirements(
                    context
                )
                if not resource_validation["valid"]:
                    return StandardResponse(
                        success=False,
                        error=ErrorInfo(
                            code="INSUFFICIENT_RESOURCES",
                            message=resource_validation["message"],
                            recoverable=True,
                        ),
                    )
                validation_results.append("resources")

            # Constraint validation
            constraint_validation = self._validate_constraints(context)
            if not constraint_validation["valid"]:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="CONSTRAINT_VIOLATION",
                        message=constraint_validation["message"],
                        recoverable=True,
                    ),
                )
            validation_results.append("constraints")

            self.logger.info(
                f"Interaction context '{context.interaction_id}' validation successful"
            )

            return StandardResponse(
                success=True,
                data={
                    "interaction_id": context.interaction_id,
                    "validation_passed": validation_results,
                    "validation_score": len(validation_results)
                    / 5.0,  # Max 5 validation types
                    "priority": context.priority.value,
                    "participant_count": len(context.participants),
                },
                metadata={"blessing": "interaction_validated"},
            )

        except Exception as e:
            self.logger.error(f"Interaction validation failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="VALIDATION_ERROR",
                    message=f"Validation error: {str(e)}",
                    recoverable=True,
                ),
            )

    async def check_prerequisites(
        self, context: InteractionContext
    ) -> StandardResponse:
        """
        Check interaction prerequisites and dependencies.

        Args:
            context: Interaction context with prerequisites

        Returns:
            StandardResponse with prerequisite check results
        """
        try:
            if not context.prerequisites:
                return StandardResponse(
                    success=True,
                    data={"prerequisites_checked": 0, "all_satisfied": True},
                    metadata={"blessing": "no_prerequisites"},
                )

            satisfied_prerequisites = []
            failed_prerequisites = []

            for prerequisite in context.prerequisites:
                if await self._check_single_prerequisite(
                    context, prerequisite
                ):
                    satisfied_prerequisites.append(prerequisite)
                else:
                    failed_prerequisites.append(prerequisite)

            all_satisfied = len(failed_prerequisites) == 0

            if not all_satisfied and self.config.strict_prerequisite_checking:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="PREREQUISITES_NOT_MET",
                        message=f"Prerequisites not satisfied: {', '.join(failed_prerequisites)}",
                        recoverable=True,
                    ),
                )

            return StandardResponse(
                success=True,
                data={
                    "prerequisites_checked": len(context.prerequisites),
                    "satisfied": satisfied_prerequisites,
                    "failed": failed_prerequisites,
                    "all_satisfied": all_satisfied,
                    "satisfaction_rate": len(satisfied_prerequisites)
                    / len(context.prerequisites),
                },
                metadata={"blessing": "prerequisites_checked"},
            )

        except Exception as e:
            self.logger.error(f"Prerequisite checking failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PREREQUISITE_CHECK_FAILED",
                    message=f"Prerequisite checking failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def calculate_risk_assessment(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """
        Calculate risk assessment for interaction.

        Args:
            context: Interaction context to assess

        Returns:
            Dict with risk assessment data
        """
        try:
            # Base risk factors
            base_risk = 0.0

            # Priority-based risk
            priority_risks = {
                InteractionPriority.CRITICAL: 0.8,
                InteractionPriority.URGENT: 0.6,
                InteractionPriority.HIGH: 0.4,
                InteractionPriority.NORMAL: 0.2,
                InteractionPriority.LOW: 0.1,
            }
            priority_risk = priority_risks.get(context.priority, 0.2)
            base_risk += priority_risk

            # Type-based risk
            type_risks = {
                InteractionType.COMBAT: 0.7,
                InteractionType.EMERGENCY: 0.6,
                InteractionType.RITUAL: 0.4,
                InteractionType.NEGOTIATION: 0.3,
                InteractionType.EXPLORATION: 0.2,
                InteractionType.DIALOGUE: 0.1,
                InteractionType.COOPERATION: 0.1,
                InteractionType.INSTRUCTION: 0.1,
                InteractionType.MAINTENANCE: 0.1,
            }
            type_risk = type_risks.get(context.interaction_type, 0.2)
            base_risk += type_risk

            # Participant count risk
            participant_risk = min(0.3, len(context.participants) * 0.05)
            base_risk += participant_risk

            # Explicit risk factors
            explicit_risk = min(0.4, len(context.risk_factors) * 0.1)
            base_risk += explicit_risk

            # Constraint complexity risk
            constraint_risk = min(0.2, len(context.constraints) * 0.05)
            base_risk += constraint_risk

            # Normalize risk score
            total_risk = min(1.0, base_risk / 2.0)  # Normalize to 0-1 range

            # Determine risk level
            if total_risk > 0.8:
                risk_level = "Critical"
            elif total_risk > 0.6:
                risk_level = "High"
            elif total_risk > 0.4:
                risk_level = "Medium"
            elif total_risk > 0.2:
                risk_level = "Low"
            else:
                risk_level = "Minimal"

            return {
                "risk_score": total_risk,
                "risk_level": risk_level,
                "contributing_factors": {
                    "priority_risk": priority_risk,
                    "type_risk": type_risk,
                    "participant_risk": participant_risk,
                    "explicit_risk": explicit_risk,
                    "constraint_risk": constraint_risk,
                },
                "risk_factors": context.risk_factors,
                "mitigation_suggestions": self._generate_risk_mitigations(
                    context, total_risk
                ),
            }

        except Exception as e:
            self.logger.error(f"Risk assessment failed: {e}")
            return {
                "risk_score": 0.5,
                "risk_level": "Unknown",
                "error": str(e),
            }

    # Private validation methods

    def _validate_basic_context(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate basic context requirements."""
        if not context.interaction_id:
            return {"valid": False, "message": "Missing interaction ID"}

        if not context.participants:
            return {"valid": False, "message": "No participants specified"}

        if len(context.participants) < 1:
            return {
                "valid": False,
                "message": "At least one participant required",
            }

        if context.initiator and context.initiator not in context.participants:
            return {
                "valid": False,
                "message": "Initiator must be a participant",
            }

        return {"valid": True, "message": "Basic context validation passed"}

    async def _validate_participants(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate participant states and availability."""
        # In a real implementation, this would check participant states from character manager
        # For now, simulate basic validation

        if len(context.participants) > 10:  # Arbitrary limit
            return {
                "valid": False,
                "message": "Too many participants (max 10)",
            }

        # Check for duplicate participants
        if len(context.participants) != len(set(context.participants)):
            return {
                "valid": False,
                "message": "Duplicate participants not allowed",
            }

        return {"valid": True, "message": "Participant validation passed"}

    def _validate_resource_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate resource requirements."""
        # Simulate resource validation
        required_resources = context.resource_requirements

        if not required_resources:
            return {"valid": True, "message": "No resources required"}

        # Check if resource requirements are reasonable
        for resource, amount in required_resources.items():
            if isinstance(amount, (int, float)) and amount < 0:
                return {
                    "valid": False,
                    "message": f"Invalid resource amount for {resource}: {amount}",
                }

        return {"valid": True, "message": "Resource validation passed"}

    def _validate_constraints(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate interaction constraints."""
        # Simulate constraint validation
        constraints = context.constraints

        if not constraints:
            return {"valid": True, "message": "No constraints specified"}

        # Check for conflicting constraints
        if (
            "no_combat" in constraints
            and context.interaction_type == InteractionType.COMBAT
        ):
            return {
                "valid": False,
                "message": "Combat interaction conflicts with no_combat constraint",
            }

        return {"valid": True, "message": "Constraint validation passed"}

    async def _check_single_prerequisite(
        self, context: InteractionContext, prerequisite: str
    ) -> bool:
        """Check a single prerequisite condition."""
        # Simulate prerequisite checking
        # In real implementation, this would check various system states

        # Simple prerequisite patterns
        if prerequisite.startswith("participant_"):
            return True  # Assume participant prerequisites are met
        elif prerequisite.startswith("location_"):
            return bool(context.location)  # Require location if specified
        elif prerequisite.startswith("resource_"):
            return True  # Assume resource prerequisites are met

        return True  # Default to satisfied for unknown prerequisites

    def _generate_risk_mitigations(
        self, context: InteractionContext, risk_score: float
    ) -> List[str]:
        """Generate risk mitigation suggestions."""
        mitigations = []

        if risk_score > 0.6:
            mitigations.append("Consider reducing participant count")
            mitigations.append("Add additional safety constraints")

        if context.interaction_type == InteractionType.COMBAT:
            mitigations.append("Ensure medical support is available")
            mitigations.append("Implement safety protocols")

        if context.priority in [
            InteractionPriority.CRITICAL,
            InteractionPriority.URGENT,
        ]:
            mitigations.append("Assign experienced participants")
            mitigations.append("Prepare contingency plans")

        return mitigations

    # Type-specific validation methods

    async def _validate_dialogue_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate dialogue-specific requirements."""
        if len(context.participants) < 2:
            return {
                "valid": False,
                "message": "Dialogue requires at least 2 participants",
            }
        return {"valid": True, "message": "Dialogue validation passed"}

    async def _validate_combat_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate combat-specific requirements."""
        if len(context.participants) < 2:
            return {
                "valid": False,
                "message": "Combat requires at least 2 participants",
            }
        return {"valid": True, "message": "Combat validation passed"}

    async def _validate_cooperation_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate cooperation-specific requirements."""
        if len(context.participants) < 2:
            return {
                "valid": False,
                "message": "Cooperation requires at least 2 participants",
            }
        return {"valid": True, "message": "Cooperation validation passed"}

    async def _validate_negotiation_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate negotiation-specific requirements."""
        return {"valid": True, "message": "Negotiation validation passed"}

    async def _validate_instruction_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate instruction-specific requirements."""
        return {"valid": True, "message": "Instruction validation passed"}

    async def _validate_ritual_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate ritual-specific requirements."""
        return {"valid": True, "message": "Ritual validation passed"}

    async def _validate_exploration_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate exploration-specific requirements."""
        return {"valid": True, "message": "Exploration validation passed"}

    async def _validate_maintenance_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate maintenance-specific requirements."""
        return {"valid": True, "message": "Maintenance validation passed"}

    async def _validate_emergency_requirements(
        self, context: InteractionContext
    ) -> Dict[str, Any]:
        """Validate emergency-specific requirements."""
        return {"valid": True, "message": "Emergency validation passed"}
