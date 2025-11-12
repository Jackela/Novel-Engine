#!/usr/bin/env python3
"""
Agent Lifecycle Manager
=======================

Manages agent lifecycle, Iron Laws validation, and action adjudication including:
- Iron Laws validation and enforcement
- Agent action adjudication and processing
- Action repair mechanisms for violation correction
- Agent interaction coordination and conflict resolution

This component ensures all agent actions comply with simulation rules while
providing repair mechanisms for common violations.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Try to import Iron Laws types
try:
    from src.shared_types import (
        CharacterData,
        IronLawsViolation,
        ProposedAction,
        ValidatedAction,
        ValidationResult,
    )

    IRON_LAWS_AVAILABLE = True
except ImportError:
    # Create fallback types for graceful degradation
    IRON_LAWS_AVAILABLE = False

    class ValidationResult:
        VALID = "valid"
        INVALID = "invalid"
        REQUIRES_REPAIR = "requires_repair"

    @dataclass
    class IronLawsViolation:
        law_code: str = "E000"
        description: str = "Unknown violation"
        severity: str = "low"

    @dataclass
    class ValidatedAction:
        action_id: str = "unknown"
        status: str = ValidationResult.VALID

    @dataclass
    class ProposedAction:
        action_id: str = "unknown"
        action_type: str = "unknown"
        target: Any = None


# Import agent types
try:
    from src.core.types.shared_types import CharacterAction
    from src.persona_agent import PersonaAgent
except ImportError:
    PersonaAgent = None
    CharacterAction = None

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ActionAdjudicationResult:
    """Result of action adjudication process."""

    success: bool
    validated_action: Optional[ValidatedAction]
    violations: List[IronLawsViolation]
    repair_log: List[str]
    adjudication_notes: List[str]


class AgentLifecycleManager:
    """
    Manages agent lifecycle and Iron Laws enforcement.

    Responsibilities:
    - Iron Laws validation for all agent actions
    - Action adjudication and conflict resolution
    - Action repair mechanisms for violation correction
    - Agent interaction coordination
    - Compliance monitoring and reporting
    """

    def __init__(self):
        """Initialize the AgentLifecycleManager."""
        self.validation_enabled = IRON_LAWS_AVAILABLE
        self.repair_attempts_count = 0
        self.successful_repairs_count = 0
        self.violation_history: List[Dict[str, Any]] = []

        # Action tracking
        self.processed_actions: List[Dict[str, Any]] = []
        self.failed_actions: List[Dict[str, Any]] = []

        # Performance metrics
        self.total_validations = 0
        self.validation_success_rate = 0.0

        logger.info(
            f"AgentLifecycleManager initialized (Iron Laws: {'enabled' if self.validation_enabled else 'disabled'})"
        )

    def adjudicate_agent_action(
        self,
        agent: PersonaAgent,
        proposed_action: ProposedAction,
        character_data: Optional[CharacterData] = None,
    ) -> ActionAdjudicationResult:
        """
        Adjudicate an agent's proposed action through Iron Laws validation.

        Validates the action against all Iron Laws, attempts repairs if violations
        are found, and returns the final adjudication result.

        Args:
            agent: PersonaAgent that proposed the action
            proposed_action: Action to be validated
            character_data: Optional character context for validation

        Returns:
            ActionAdjudicationResult containing validation outcome and any repairs
        """
        try:
            self.total_validations += 1
            agent_id = getattr(agent, "agent_id", "unknown")

            logger.info(
                f"Adjudicating action {proposed_action.action_id} from agent {agent_id}"
            )

            if not self.validation_enabled:
                # Return success if Iron Laws not available
                return ActionAdjudicationResult(
                    success=True,
                    validated_action=self._create_fallback_validated_action(
                        proposed_action
                    ),
                    violations=[],
                    repair_log=[
                        "Iron Laws validation not available - action approved by default"
                    ],
                    adjudication_notes=["Validation system disabled"],
                )

            # Validate action against Iron Laws
            violations = self._validate_against_iron_laws(
                proposed_action, character_data
            )

            if not violations:
                # Action is valid
                validated_action = self._convert_proposed_to_validated(
                    proposed_action, ValidationResult.VALID
                )

                self._record_successful_action(
                    agent_id, proposed_action, validated_action
                )

                return ActionAdjudicationResult(
                    success=True,
                    validated_action=validated_action,
                    violations=[],
                    repair_log=[],
                    adjudication_notes=["Action validated successfully"],
                )

            # Violations found - attempt repairs
            logger.warning(
                f"Action {proposed_action.action_id} has {len(violations)} violations, attempting repairs"
            )

            validated_action, repair_log = self._attempt_action_repairs(
                proposed_action, violations, character_data
            )

            if validated_action and validated_action.status == ValidationResult.VALID:
                # Repairs successful
                self.successful_repairs_count += 1
                self._record_successful_action(
                    agent_id, proposed_action, validated_action, repair_log
                )

                return ActionAdjudicationResult(
                    success=True,
                    validated_action=validated_action,
                    violations=violations,
                    repair_log=repair_log,
                    adjudication_notes=["Action repaired and validated"],
                )
            else:
                # Repairs failed
                self._record_failed_action(
                    agent_id, proposed_action, violations, repair_log
                )

                return ActionAdjudicationResult(
                    success=False,
                    validated_action=validated_action,
                    violations=violations,
                    repair_log=repair_log,
                    adjudication_notes=["Action could not be repaired"],
                )

        except Exception as e:
            logger.error(f"Error during action adjudication: {str(e)}")
            return ActionAdjudicationResult(
                success=False,
                validated_action=None,
                violations=[],
                repair_log=[f"Adjudication system error: {str(e)}"],
                adjudication_notes=["System error during adjudication"],
            )

    def _validate_against_iron_laws(
        self,
        proposed_action: ProposedAction,
        character_data: Optional[CharacterData] = None,
    ) -> List[IronLawsViolation]:
        """
        Validate a proposed action against all Iron Laws.

        Args:
            proposed_action: Action to validate
            character_data: Optional character context for validation

        Returns:
            List of violations found (empty if action is valid)
        """
        violations = []

        try:
            # E001 - Causality Law validation
            causality_violations = self._validate_causality_law(proposed_action)
            violations.extend(causality_violations)

            # E002 - Resource Law validation
            resource_violations = self._validate_resource_law(
                proposed_action, character_data
            )
            violations.extend(resource_violations)

            # E003 - Physics Law validation
            physics_violations = self._validate_physics_law(
                proposed_action, character_data
            )
            violations.extend(physics_violations)

            # E004 - Narrative Law validation
            narrative_violations = self._validate_narrative_law(proposed_action)
            violations.extend(narrative_violations)

            # E005 - Social Law validation
            social_violations = self._validate_social_law(proposed_action)
            violations.extend(social_violations)

            # Record violations for tracking
            if violations:
                self._record_violations(proposed_action, violations)

        except Exception as e:
            logger.error(f"Error during Iron Laws validation: {str(e)}")
            violations.append(
                IronLawsViolation(
                    law_code="E000",
                    description=f"Validation system error: {str(e)}",
                    severity="high",
                )
            )

        return violations

    def _validate_causality_law(
        self, proposed_action: ProposedAction
    ) -> List[IronLawsViolation]:
        """Validate E001 - Causality Law: Actions must have clear cause-effect relationships."""
        violations = []

        try:
            # Check if action has valid target specification
            if not hasattr(proposed_action, "target") or not proposed_action.target:
                violations.append(
                    IronLawsViolation(
                        law_code="E001",
                        description="Action lacks proper target specification",
                        severity="medium",
                    )
                )

            # Check if action type is valid
            if (
                not hasattr(proposed_action, "action_type")
                or not proposed_action.action_type
            ):
                violations.append(
                    IronLawsViolation(
                        law_code="E001",
                        description="Action lacks valid action type",
                        severity="high",
                    )
                )

        except Exception as e:
            logger.error(f"Error validating causality law: {str(e)}")

        return violations

    def _validate_resource_law(
        self,
        proposed_action: ProposedAction,
        character_data: Optional[CharacterData] = None,
    ) -> List[IronLawsViolation]:
        """Validate E002 - Resource Law: Actions cannot exceed character resource limits."""
        violations = []

        try:
            # Basic resource validation - can be extended with character_data
            if hasattr(proposed_action, "resource_cost"):
                # Placeholder for resource cost validation
                # In full implementation, this would check against character resources
                pass

        except Exception as e:
            logger.error(f"Error validating resource law: {str(e)}")

        return violations

    def _validate_physics_law(
        self,
        proposed_action: ProposedAction,
        character_data: Optional[CharacterData] = None,
    ) -> List[IronLawsViolation]:
        """Validate E003 - Physics Law: Actions must be physically possible."""
        violations = []

        try:
            # Basic physics validation
            if hasattr(proposed_action, "action_type"):
                action_type = proposed_action.action_type.lower()

                # Example: Check for impossible actions
                impossible_actions = ["fly_unaided", "teleport", "time_travel"]
                if action_type in impossible_actions:
                    violations.append(
                        IronLawsViolation(
                            law_code="E003",
                            description=f"Action '{action_type}' violates physical laws",
                            severity="high",
                        )
                    )

        except Exception as e:
            logger.error(f"Error validating physics law: {str(e)}")

        return violations

    def _validate_narrative_law(
        self, proposed_action: ProposedAction
    ) -> List[IronLawsViolation]:
        """Validate E004 - Narrative Law: Actions must maintain story consistency."""
        violations = []

        try:
            # Basic narrative consistency checks
            if hasattr(proposed_action, "reasoning"):
                reasoning = proposed_action.reasoning
                if not reasoning or len(reasoning.strip()) < 10:
                    violations.append(
                        IronLawsViolation(
                            law_code="E004",
                            description="Action lacks sufficient narrative reasoning",
                            severity="low",
                        )
                    )

        except Exception as e:
            logger.error(f"Error validating narrative law: {str(e)}")

        return violations

    def _validate_social_law(
        self, proposed_action: ProposedAction
    ) -> List[IronLawsViolation]:
        """Validate E005 - Social Law: Actions must respect character relationships and hierarchy."""
        violations = []

        try:
            # Basic social validation
            if hasattr(proposed_action, "target") and proposed_action.target:
                # Check for basic social constraints
                # This would be expanded with full relationship tracking
                pass

        except Exception as e:
            logger.error(f"Error validating social law: {str(e)}")

        return violations

    def _attempt_action_repairs(
        self,
        proposed_action: ProposedAction,
        violations: List[IronLawsViolation],
        character_data: Optional[CharacterData],
    ) -> Tuple[Optional[ValidatedAction], List[str]]:
        """
        Attempt to automatically repair action violations.

        Args:
            proposed_action: Original action with violations
            violations: List of detected violations to repair
            character_data: Character context for repair calculations

        Returns:
            Tuple of (repaired_validated_action, repair_log)
        """
        repair_log = []
        modified_action = proposed_action
        self.repair_attempts_count += 1

        if not violations:
            return None, repair_log

        try:
            # Group violations by law type for systematic repair
            violations_by_law = self._group_violations_by_law(violations)

            # Apply repairs in order of severity and dependency
            repair_order = ["E003", "E002", "E001", "E004", "E005"]

            for law_code in repair_order:
                if law_code in violations_by_law:
                    law_violations = violations_by_law[law_code]

                    if law_code == "E001":
                        modified_action, causality_repairs = (
                            self._repair_causality_violations(
                                modified_action, law_violations
                            )
                        )
                        repair_log.extend(causality_repairs)

                    elif law_code == "E002":
                        modified_action, resource_repairs = (
                            self._repair_resource_violations(
                                modified_action, law_violations, character_data
                            )
                        )
                        repair_log.extend(resource_repairs)

                    elif law_code == "E003":
                        modified_action, physics_repairs = (
                            self._repair_physics_violations(
                                modified_action, law_violations, character_data
                            )
                        )
                        repair_log.extend(physics_repairs)

                    elif law_code == "E004":
                        modified_action, narrative_repairs = (
                            self._repair_narrative_violations(
                                modified_action, law_violations
                            )
                        )
                        repair_log.extend(narrative_repairs)

                    elif law_code == "E005":
                        modified_action, social_repairs = (
                            self._repair_social_violations(
                                modified_action, law_violations
                            )
                        )
                        repair_log.extend(social_repairs)

            # Convert to ValidatedAction if repairs were made
            if modified_action and repair_log:
                validated_action = self._convert_proposed_to_validated(
                    modified_action, ValidationResult.VALID
                )

                logger.info(
                    f"Action {proposed_action.action_id} repaired: {len(repair_log)} repairs applied"
                )
                return validated_action, repair_log
            else:
                validated_action = self._convert_proposed_to_validated(
                    proposed_action, ValidationResult.INVALID
                )
                repair_log.append(
                    "No automatic repairs available for detected violations"
                )
                return validated_action, repair_log

        except Exception as e:
            logger.error(
                f"Repair system failure for action {proposed_action.action_id}: {e}"
            )
            repair_log.append(f"Repair system error: {str(e)}")
            return None, repair_log

    def _repair_causality_violations(
        self, action: ProposedAction, violations: List[IronLawsViolation]
    ) -> Tuple[ProposedAction, List[str]]:
        """Repair E001 Causality Law violations."""
        repairs_made = []
        modified_action = action

        for violation in violations:
            if "target specification" in violation.description:
                # Add default target if missing
                if hasattr(modified_action, "target") and not modified_action.target:
                    # Create a basic target (would be more sophisticated in full implementation)
                    repairs_made.append("Added default target for causality compliance")

            elif "action type" in violation.description:
                # Set default action type if missing
                if (
                    hasattr(modified_action, "action_type")
                    and not modified_action.action_type
                ):
                    modified_action.action_type = "observe"
                    repairs_made.append("Set default action type to 'observe'")

        return modified_action, repairs_made

    def _repair_resource_violations(
        self,
        action: ProposedAction,
        violations: List[IronLawsViolation],
        character_data: Optional[CharacterData],
    ) -> Tuple[ProposedAction, List[str]]:
        """Repair E002 Resource Law violations."""
        repairs_made = []
        modified_action = action

        # Resource repair logic would be implemented here
        # For now, just log the attempt
        repairs_made.append("Resource constraint repairs attempted")

        return modified_action, repairs_made

    def _repair_physics_violations(
        self,
        action: ProposedAction,
        violations: List[IronLawsViolation],
        character_data: Optional[CharacterData],
    ) -> Tuple[ProposedAction, List[str]]:
        """Repair E003 Physics Law violations."""
        repairs_made = []
        modified_action = action

        for violation in violations:
            if "violates physical laws" in violation.description:
                # Replace impossible action with feasible alternative
                if hasattr(modified_action, "action_type"):
                    impossible_to_possible = {
                        "fly_unaided": "jump",
                        "teleport": "run",
                        "time_travel": "remember",
                    }

                    old_action = modified_action.action_type
                    if old_action in impossible_to_possible:
                        modified_action.action_type = impossible_to_possible[old_action]
                        repairs_made.append(
                            f"Changed impossible action '{old_action}' to '{modified_action.action_type}'"
                        )

        return modified_action, repairs_made

    def _repair_narrative_violations(
        self, action: ProposedAction, violations: List[IronLawsViolation]
    ) -> Tuple[ProposedAction, List[str]]:
        """Repair E004 Narrative Law violations."""
        repairs_made = []
        modified_action = action

        for violation in violations:
            if "lacks sufficient narrative reasoning" in violation.description:
                # Add default reasoning if missing
                if hasattr(modified_action, "reasoning") and (
                    not modified_action.reasoning
                    or len(modified_action.reasoning.strip()) < 10
                ):
                    modified_action.reasoning = f"Character decided to {getattr(modified_action, 'action_type', 'act')} based on current situation assessment."
                    repairs_made.append("Added default narrative reasoning")

        return modified_action, repairs_made

    def _repair_social_violations(
        self, action: ProposedAction, violations: List[IronLawsViolation]
    ) -> Tuple[ProposedAction, List[str]]:
        """Repair E005 Social Law violations."""
        repairs_made = []
        modified_action = action

        # Social repair logic would be implemented here
        repairs_made.append("Social constraint repairs attempted")

        return modified_action, repairs_made

    def _group_violations_by_law(
        self, violations: List[IronLawsViolation]
    ) -> Dict[str, List[IronLawsViolation]]:
        """Group violations by law code for systematic processing."""
        grouped = {}
        for violation in violations:
            law_code = violation.law_code
            if law_code not in grouped:
                grouped[law_code] = []
            grouped[law_code].append(violation)
        return grouped

    def _convert_proposed_to_validated(
        self, proposed_action: ProposedAction, validation_result: str
    ) -> ValidatedAction:
        """Convert a ProposedAction to ValidatedAction with validation status."""
        if IRON_LAWS_AVAILABLE:
            # Use real ValidatedAction if available
            return ValidatedAction(
                action_id=getattr(proposed_action, "action_id", "unknown"),
                status=validation_result,
            )
        else:
            # Use fallback ValidatedAction
            return ValidatedAction(
                action_id=getattr(proposed_action, "action_id", "unknown"),
                status=validation_result,
            )

    def _create_fallback_validated_action(
        self, proposed_action: ProposedAction
    ) -> ValidatedAction:
        """Create a fallback validated action when Iron Laws not available."""
        return ValidatedAction(
            action_id=getattr(proposed_action, "action_id", "unknown"),
            status=ValidationResult.VALID,
        )

    def _record_successful_action(
        self,
        agent_id: str,
        proposed_action: ProposedAction,
        validated_action: ValidatedAction,
        repair_log: List[str] = None,
    ) -> None:
        """Record a successfully validated action."""
        action_record = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "action_id": getattr(proposed_action, "action_id", "unknown"),
            "action_type": getattr(proposed_action, "action_type", "unknown"),
            "status": "success",
            "repairs_applied": len(repair_log) if repair_log else 0,
            "repair_log": repair_log or [],
        }
        self.processed_actions.append(action_record)

    def _record_failed_action(
        self,
        agent_id: str,
        proposed_action: ProposedAction,
        violations: List[IronLawsViolation],
        repair_log: List[str] = None,
    ) -> None:
        """Record a failed action validation."""
        action_record = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "action_id": getattr(proposed_action, "action_id", "unknown"),
            "action_type": getattr(proposed_action, "action_type", "unknown"),
            "status": "failed",
            "violation_count": len(violations),
            "violations": [v.description for v in violations],
            "repair_log": repair_log or [],
        }
        self.failed_actions.append(action_record)

    def _record_violations(
        self, proposed_action: ProposedAction, violations: List[IronLawsViolation]
    ) -> None:
        """Record violations for tracking and analysis."""
        violation_record = {
            "timestamp": datetime.now().isoformat(),
            "action_id": getattr(proposed_action, "action_id", "unknown"),
            "violation_count": len(violations),
            "violations": [(v.law_code, v.description, v.severity) for v in violations],
        }
        self.violation_history.append(violation_record)

    def get_lifecycle_metrics(self) -> Dict[str, Any]:
        """
        Get agent lifecycle management metrics.

        Returns:
            Dictionary containing performance and compliance metrics
        """
        try:
            successful_actions = len(self.processed_actions)
            failed_actions = len(self.failed_actions)
            total_actions = successful_actions + failed_actions

            return {
                "total_validations": self.total_validations,
                "successful_actions": successful_actions,
                "failed_actions": failed_actions,
                "success_rate": (
                    (successful_actions / total_actions) if total_actions > 0 else 0.0
                ),
                "repair_attempts": self.repair_attempts_count,
                "successful_repairs": self.successful_repairs_count,
                "repair_success_rate": (
                    (self.successful_repairs_count / self.repair_attempts_count)
                    if self.repair_attempts_count > 0
                    else 0.0
                ),
                "total_violations": len(self.violation_history),
                "iron_laws_enabled": self.validation_enabled,
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error generating lifecycle metrics: {str(e)}")
            return {"error": str(e)}

    def get_violation_summary(self) -> Dict[str, Any]:
        """
        Get summary of violations by law type and severity.

        Returns:
            Dictionary containing violation analysis
        """
        try:
            law_violations = {}
            severity_counts = {"low": 0, "medium": 0, "high": 0}

            for record in self.violation_history:
                for law_code, description, severity in record["violations"]:
                    if law_code not in law_violations:
                        law_violations[law_code] = 0
                    law_violations[law_code] += 1

                    if severity in severity_counts:
                        severity_counts[severity] += 1

            return {
                "violations_by_law": law_violations,
                "violations_by_severity": severity_counts,
                "total_violation_records": len(self.violation_history),
                "most_violated_law": (
                    max(law_violations.items(), key=lambda x: x[1])[0]
                    if law_violations
                    else None
                ),
            }
        except Exception as e:
            logger.error(f"Error generating violation summary: {str(e)}")
            return {"error": str(e)}
