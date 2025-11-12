#!/usr/bin/env python3
"""
Iron Laws Integration Module for Novel Engine.

This module handles validation and processing of all actions against the 5 Iron Laws
of the Novel Engine. It provides comprehensive validation with automatic repair
capabilities for minor violations. Extracted from DirectorAgent for better modularity.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.persona_agent import PersonaAgent

# Try to import Iron Laws types
try:
    from src.shared_types import (
        IronLawsReport,
        IronLawsViolation,
        Position,
        ProposedAction,
        ResourceValue,
        ValidationResult,
    )

    IRON_LAWS_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"Iron Laws types not available: {e}")
    IRON_LAWS_AVAILABLE = False

logger = logging.getLogger(__name__)


class IronLawsProcessor:
    """
    Manages validation and processing of actions against the 5 Iron Laws.

    The 5 Iron Laws:
    - E001 Causality Law: Actions must have logical consequences
    - E002 Resource Law: Characters cannot exceed their capabilities/resources
    - E003 Physics Law: Actions must obey basic physical constraints
    - E004 Narrative Law: Actions must maintain story coherence
    - E005 Social Law: Actions must respect established relationships/hierarchies

    Responsibilities:
    - Action validation against all Iron Laws
    - Automatic repair of minor violations
    - Comprehensive violation reporting
    - Law-specific validation logic
    """

    def __init__(self):
        """Initialize the Iron Laws Processor."""
        self.validation_enabled = IRON_LAWS_AVAILABLE
        if not self.validation_enabled:
            logger.warning("Iron Laws validation disabled - types not available")

    def adjudicate_action(
        self,
        proposed_action: "ProposedAction",
        agent: "PersonaAgent",
        world_context: Dict[str, Any],
    ) -> "IronLawsReport":
        """
        Validate proposed action against all 5 Iron Laws of the Novel Engine.

        The Iron Laws represent the fundamental constraints that govern all character
        actions in the simulation, ensuring narrative consistency, physical plausibility,
        and game balance. This method provides comprehensive validation with automatic
        repair capabilities for minor violations.

        Args:
            proposed_action: Action proposed by the character agent
            agent: PersonaAgent instance for context and character data
            world_context: Current world state context

        Returns:
            IronLawsReport containing validation results and any repaired action
        """
        if not self.validation_enabled:
            # Return a dummy approval if validation is disabled
            from src.shared_types import (
                IronLawsReport,
                ValidationResult,
            )

            return IronLawsReport(
                character_id=getattr(proposed_action, "character_id", "unknown"),
                action_summary=f"Action: {getattr(proposed_action, 'action_type', 'unknown')}",
                validation_result=ValidationResult.APPROVED,
                violations=[],
                repaired_action=None,
                repair_log=["Iron Laws validation disabled"],
            )

        try:
            # Extract character data from agent
            character_data = self._extract_character_data_from_agent(agent)

            # Initialize violation collection
            all_violations = []

            # Validate against each Iron Law
            all_violations.extend(
                self._validate_causality_law(
                    proposed_action, character_data, world_context
                )
            )
            all_violations.extend(
                self._validate_resource_law(proposed_action, character_data)
            )
            all_violations.extend(
                self._validate_physics_law(
                    proposed_action, character_data, world_context
                )
            )
            all_violations.extend(
                self._validate_narrative_law(proposed_action, agent, world_context)
            )
            all_violations.extend(
                self._validate_social_law(proposed_action, agent, world_context)
            )

            # Determine overall validation result
            validation_result = self._determine_overall_validation_result(
                all_violations
            )

            # Attempt repairs if there are violations
            repaired_action = None
            repair_log = []
            if all_violations and validation_result != ValidationResult.REJECTED:
                repaired_action, repair_log = self._attempt_action_repairs(
                    proposed_action, all_violations, character_data
                )

            # Create comprehensive report
            report = IronLawsReport(
                character_id=proposed_action.character_id,
                action_summary=f"{proposed_action.action_type}: {getattr(proposed_action, 'description', 'No description')}",
                validation_result=validation_result,
                violations=all_violations,
                repaired_action=repaired_action,
                repair_log=repair_log,
            )

            return report

        except Exception as e:
            logger.error(f"Error during Iron Laws validation: {str(e)}")
            # Return rejection on unexpected errors
            return IronLawsReport(
                character_id=getattr(proposed_action, "character_id", "unknown"),
                action_summary="Validation Error",
                validation_result=ValidationResult.REJECTED,
                violations=[
                    IronLawsViolation(
                        law_code="E000",
                        law_name="System_Error",
                        severity="critical",
                        description=f"Validation system error: {str(e)}",
                        affected_entities=[
                            getattr(proposed_action, "character_id", "unknown")
                        ],
                        suggested_repair="Check system logs and action format",
                    )
                ],
                repaired_action=None,
                repair_log=[f"System error: {str(e)}"],
            )

    def _validate_causality_law(
        self,
        action: "ProposedAction",
        character_data: Optional["CharacterData"],
        world_context: Dict[str, Any],
    ) -> List["IronLawsViolation"]:
        """
        E001 Causality Law: Actions must have logical consequences.

        Validates that proposed actions have realistic cause-effect relationships
        and don't violate basic logical consistency within the simulation.
        """
        violations = []

        # Check for missing or inadequate reasoning
        if (
            not action.reasoning
            or action.reasoning.strip() == ""
            or len(action.reasoning.strip()) < 3
        ):
            violations.append(
                IronLawsViolation(
                    law_code="E001",
                    law_name="Causality_Law",
                    severity="error",
                    description="Action lacks proper reasoning or justification",
                    affected_entities=[action.character_id],
                    suggested_repair="Provide clear reasoning for why this action is being taken",
                )
            )

        # Check for contradictory actions
        if (
            hasattr(action, "contradicts_previous_action")
            and action.contradicts_previous_action
        ):
            violations.append(
                IronLawsViolation(
                    law_code="E001",
                    law_name="Causality_Law",
                    severity="warning",
                    description="Action contradicts previous character behavior",
                    affected_entities=[action.character_id],
                    suggested_repair="Ensure action consistency with character history",
                )
            )

        return violations

    def _validate_resource_law(
        self, action: "ProposedAction", character_data: Optional["CharacterData"]
    ) -> List["IronLawsViolation"]:
        """
        E002 Resource Law: Characters cannot exceed their capabilities/resources.

        Validates that characters have sufficient resources (health, stamina, ammo, etc.)
        and capabilities (stats, equipment) to perform the proposed action.
        """
        violations = []

        if not character_data:
            violations.append(
                IronLawsViolation(
                    law_code="E002",
                    law_name="Resource_Law",
                    severity="critical",
                    description="Cannot validate resources - character data unavailable",
                    affected_entities=["unknown"],
                    suggested_repair="Ensure character data is properly loaded",
                )
            )
            return violations

        # Check stamina requirements
        stamina_cost = self._calculate_action_stamina_cost(action)
        current_stamina = getattr(
            character_data.resources, "stamina", ResourceValue(current=100, maximum=100)
        )

        if current_stamina.current < stamina_cost:
            violations.append(
                IronLawsViolation(
                    law_code="E002",
                    law_name="Resource_Law",
                    severity="error",
                    description=f"Insufficient stamina: need {stamina_cost}, have {current_stamina.current}",
                    affected_entities=[action.character_id],
                    suggested_repair="Choose a less demanding action or rest to recover stamina",
                )
            )

        # Check equipment requirements
        required_equipment = self._get_action_equipment_requirements(action)
        for equipment in required_equipment:
            if not self._character_has_equipment(character_data, equipment):
                violations.append(
                    IronLawsViolation(
                        law_code="E002",
                        law_name="Resource_Law",
                        severity="error",
                        description=f"Missing required equipment: {equipment}",
                        affected_entities=[action.character_id],
                        suggested_repair=f"Acquire {equipment} before attempting this action",
                    )
                )

        return violations

    def _validate_physics_law(
        self,
        action: "ProposedAction",
        character_data: Optional["CharacterData"],
        world_context: Dict[str, Any],
    ) -> List["IronLawsViolation"]:
        """
        E003 Physics Law: Actions must obey basic physical constraints.

        Validates that actions respect fundamental physical limitations like distance,
        line of sight, environmental conditions, and basic physics.
        """
        violations = []

        # Handle both CharacterData objects and dictionary format
        if hasattr(character_data, "position"):
            character_position = character_data.position
        else:
            character_position = (
                character_data.get("position") if character_data else None
            )

        if not character_data or not character_position:
            return violations  # Cannot validate without position data

        # Check movement distance constraints
        if action.action_type == ActionType.MOVE and action.target:
            if hasattr(action.target, "position"):
                target_position = action.target.position
                distance = self._calculate_distance(character_position, target_position)
                max_movement = self._calculate_max_movement_distance(character_data)

                if distance > max_movement:
                    violations.append(
                        IronLawsViolation(
                            law_code="E003",
                            law_name="Physics_Law",
                            severity="error",
                            description=f"Movement distance {distance:.1f} exceeds maximum {max_movement:.1f}",
                            affected_entities=[action.character_id],
                            suggested_repair="Choose a closer destination or move in stages",
                        )
                    )

        # Check line of sight for ranged actions
        if (
            action.action_type in [ActionType.ATTACK, ActionType.OBSERVE]
            and action.target
        ):
            if not self._check_line_of_sight(
                character_position, action.target, world_context
            ):
                violations.append(
                    IronLawsViolation(
                        law_code="E003",
                        law_name="Physics_Law",
                        severity="error",
                        description="Target not in line of sight",
                        affected_entities=[action.character_id],
                        suggested_repair="Move to a position with clear line of sight",
                    )
                )

        return violations

    def _validate_narrative_law(
        self,
        action: "ProposedAction",
        agent: "PersonaAgent",
        world_context: Dict[str, Any],
    ) -> List["IronLawsViolation"]:
        """
        E004 Narrative Law: Actions must maintain story coherence.

        Validates that actions are consistent with established narrative, character
        personalities, ongoing story arcs, and don't break immersion.
        """
        violations = []

        # Check for attacking allies/friendlies - narratively inconsistent
        if action.action_type == ActionType.ATTACK and action.target:
            target_id = action.target.entity_id
            if any(
                keyword in target_id.lower()
                for keyword in ["ally", "friend", "team", "companion"]
            ):
                violations.append(
                    IronLawsViolation(
                        law_code="E004",
                        law_name="Narrative_Law",
                        severity="error",
                        description="Attacking allies without justification breaks narrative coherence",
                        affected_entities=[agent.character_id],
                        suggested_repair="Target enemies instead of allies, or provide compelling narrative reason",
                    )
                )

        # Check personality consistency
        if self._action_contradicts_personality(action, agent.personality_traits):
            violations.append(
                IronLawsViolation(
                    law_code="E004",
                    law_name="Narrative_Law",
                    severity="warning",
                    description="Action contradicts established personality traits",
                    affected_entities=[agent.character_id],
                    suggested_repair="Choose action more consistent with character personality",
                )
            )

        return violations

    def _validate_social_law(
        self,
        action: "ProposedAction",
        agent: "PersonaAgent",
        world_context: Dict[str, Any],
    ) -> List["IronLawsViolation"]:
        """
        E005 Social Law: Actions must respect established relationships/hierarchies.

        Validates that actions respect military hierarchy, social relationships,
        command structure, and established group dynamics.
        """
        violations = []

        # Check command hierarchy
        if action.action_type.value == "communicate" and action.target:
            target_rank = self._get_character_rank(
                action.target.entity_id, world_context
            )
            agent_rank = getattr(agent, "military_rank", "private")

            if self._is_insubordinate_communication(action, agent_rank, target_rank):
                violations.append(
                    IronLawsViolation(
                        law_code="E005",
                        law_name="Social_Law",
                        severity="warning",
                        description="Communication violates military hierarchy",
                        affected_entities=[agent.character_id],
                        suggested_repair="Follow proper chain of command",
                    )
                )

        return violations

    def _attempt_action_repairs(
        self,
        proposed_action: "ProposedAction",
        violations: List["IronLawsViolation"],
        character_data: Optional["CharacterData"],
    ) -> Tuple[Optional["ValidatedAction"], List[str]]:
        """
        Attempt to automatically repair action violations through systematic modification.

        Applies law-specific repair strategies to fix violations while preserving
        action intent. Returns repaired action and log of repair attempts.

        Args:
            proposed_action: Original action with violations
            violations: List of detected violations to repair
            character_data: Character context for repair calculations

        Returns:
            Tuple of (repaired_validated_action, repair_log)
        """
        repair_log = []
        modified_action = proposed_action

        if not IRON_LAWS_AVAILABLE:
            return None, ["Iron Laws types not available for repair"]

        # Group violations by law for systematic repair
        grouped_violations = self._group_violations_by_law(violations)

        # Attempt repairs for each law
        for law_name, law_violations in grouped_violations.items():
            if law_name == "Causality_Law":
                modified_action, law_repair_log = self._repair_causality_violations(
                    modified_action, law_violations, character_data
                )
            elif law_name == "Resource_Law":
                modified_action, law_repair_log = self._repair_resource_violations(
                    modified_action, law_violations, character_data
                )
            elif law_name == "Physics_Law":
                modified_action, law_repair_log = self._repair_physics_violations(
                    modified_action, law_violations, character_data
                )
            elif law_name == "Narrative_Law":
                modified_action, law_repair_log = self._repair_narrative_violations(
                    modified_action, law_violations, character_data
                )
            elif law_name == "Social_Law":
                modified_action, law_repair_log = self._repair_social_violations(
                    modified_action, law_violations, character_data
                )

            repair_log.extend(law_repair_log)

        # Convert to validated action if repairs were successful
        if modified_action != proposed_action or repair_log:
            validation_result = ValidationResult.APPROVED_WITH_MODIFICATIONS
            validated_action = self._convert_proposed_to_validated(
                modified_action, validation_result
            )
            return validated_action, repair_log

        return None, repair_log

    # Helper methods for validation and repair
    def _extract_character_data_from_agent(
        self, agent: "PersonaAgent"
    ) -> Optional["CharacterData"]:
        """Extract character data from agent for validation purposes."""
        # Implementation would depend on agent structure
        return None  # Placeholder

    def _calculate_action_stamina_cost(self, action: "ProposedAction") -> int:
        """Calculate stamina cost for an action."""
        return 10  # Placeholder

    def _get_action_equipment_requirements(self, action: "ProposedAction") -> List[str]:
        """Get equipment requirements for an action."""
        return []  # Placeholder

    def _character_has_equipment(
        self, character_data: "CharacterData", equipment: str
    ) -> bool:
        """Check if character has required equipment."""
        return True  # Placeholder

    def _calculate_distance(self, pos1: "Position", pos2: "Position") -> float:
        """Calculate distance between two positions."""
        return 0.0  # Placeholder

    def _calculate_max_movement_distance(self, character_data) -> float:
        """Calculate maximum movement distance for character."""
        return 10.0  # Placeholder

    def _check_line_of_sight(
        self, from_pos: "Position", target, world_context: Dict[str, Any]
    ) -> bool:
        """Check if there's line of sight to target."""
        return True  # Placeholder

    def _action_contradicts_personality(
        self, action: "ProposedAction", personality_traits: Dict[str, Any]
    ) -> bool:
        """Check if action contradicts personality traits."""
        return False  # Placeholder

    def _get_character_rank(
        self, character_id: str, world_context: Dict[str, Any]
    ) -> str:
        """Get character's military rank."""
        return "private"  # Placeholder

    def _is_insubordinate_communication(
        self, action: "ProposedAction", agent_rank: str, target_rank: str
    ) -> bool:
        """Check if communication violates hierarchy."""
        return False  # Placeholder

    def _group_violations_by_law(
        self, violations: List["IronLawsViolation"]
    ) -> Dict[str, List["IronLawsViolation"]]:
        """Group violations by law type."""
        grouped = {}
        for violation in violations:
            if violation.law_name not in grouped:
                grouped[violation.law_name] = []
            grouped[violation.law_name].append(violation)
        return grouped

    def _repair_causality_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair causality law violations."""
        return action, ["Causality repair not implemented"]

    def _repair_resource_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair resource law violations."""
        return action, ["Resource repair not implemented"]

    def _repair_physics_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair physics law violations."""
        return action, ["Physics repair not implemented"]

    def _repair_narrative_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair narrative law violations."""
        return action, ["Narrative repair not implemented"]

    def _repair_social_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair social law violations."""
        return action, ["Social repair not implemented"]

    def _convert_proposed_to_validated(
        self, proposed_action: "ProposedAction", validation_result: "ValidationResult"
    ) -> "ValidatedAction":
        """Convert proposed action to validated action."""
        # Placeholder implementation
        return None

    def _determine_overall_validation_result(
        self, violations: List["IronLawsViolation"]
    ) -> "ValidationResult":
        """Determine overall validation result from violations."""
        if not violations:
            return ValidationResult.APPROVED

        # Check for critical violations
        critical_violations = [v for v in violations if v.severity == "critical"]
        if critical_violations:
            return ValidationResult.REJECTED

        # Check for error violations
        error_violations = [v for v in violations if v.severity == "error"]
        if error_violations:
            return ValidationResult.NEEDS_MODIFICATION

        # Only warnings remain
        return ValidationResult.APPROVED_WITH_WARNINGS
