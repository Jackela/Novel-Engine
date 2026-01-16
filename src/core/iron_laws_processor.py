#!/usr/bin/env python3
"""
Iron Laws Integration Module for Novel Engine.

This module handles validation and processing of all actions against the 5 Iron Laws
of the Novel Engine. It provides comprehensive validation with automatic repair
capabilities for minor violations. Extracted from DirectorAgent for better modularity.
"""

import logging
import math
import time
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from src.agents.persona_agent.agent import PersonaAgent

# Try to import Iron Laws types
try:
    from src.core.types.shared_types import (
        ActionIntensity,
        ActionParameters,
        ActionTarget,
        ActionType,
        CharacterData,
        EntityType,
        IronLawsReport,
        IronLawsViolation,
        Position,
        ProposedAction,
        ResourceValue,
        ValidatedAction,
        ValidationResult,
    )

    IRON_LAWS_AVAILABLE = True
except ImportError as e:  # pragma: no cover - fallback for tooling-only contexts
    logging.getLogger(__name__).warning(f"Iron Laws types not available: {e}")
    IRON_LAWS_AVAILABLE = False
    ActionIntensity = ActionTarget = ActionType = EntityType = CharacterData = object  # type: ignore
    IronLawsReport = IronLawsViolation = Position = ProposedAction = object  # type: ignore
    ResourceValue = ValidatedAction = ValidationResult = object  # type: ignore

logger = logging.getLogger(__name__)


class _ReportWrapper(dict):
    """Dict-like view of an IronLawsReport that still exposes attributes."""

    def __init__(self, report: IronLawsReport, **extra: Any):
        data = report.model_dump()
        data.update(extra)
        super().__init__(data)
        self._report = report

    def __getattr__(self, item: str) -> Any:
        if hasattr(self._report, item):
            return getattr(self._report, item)
        try:
            return self[item]
        except KeyError as exc:  # pragma: no cover - debugging helper
            raise AttributeError(item) from exc

    def __dir__(self) -> List[str]:
        return sorted(set(super().__dir__()) | set(self._report.__dir__()))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _ReportWrapper):
            return dict.__eq__(self, other) and self._report == other._report
        return dict.__eq__(self, other)


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
        started_at = time.perf_counter()
        raw_action = proposed_action
        action_id = getattr(raw_action, "action_id", "unknown")

        if not self.validation_enabled:
            return self._wrap_report(
                IronLawsReport(
                    action_id=action_id,
                    overall_result=ValidationResult.VALID,
                    violations=[],
                    checks_performed=[
                        "E001_Causality_Law",
                        "E002_Resource_Law",
                        "E003_Physics_Law",
                        "E004_Narrative_Law",
                        "E005_Social_Law",
                    ],
                    repair_attempts=["Iron Laws validation disabled"],
                    final_action=None,
                ),
                started_at,
            )

        if raw_action is None:
            return self._wrap_report(
                self._build_failure_report(
                    action_id, "No action provided for validation"
                ),
                started_at,
            )

        try:
            proposed_action = self._ensure_proposed_action(raw_action, agent)
            action_id = proposed_action.action_id
            # Extract character data from agent
            character_data = self._extract_character_data_from_agent(agent)
            if character_data is None:
                return self._wrap_report(
                    self._build_failure_report(
                        action_id, "Character data unavailable for validation"
                    ),
                    started_at,
                )

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
            if all_violations and validation_result not in {
                ValidationResult.INVALID,
                ValidationResult.CATASTROPHIC_FAILURE,
            }:
                repaired_action, repair_log = self._attempt_action_repairs(
                    proposed_action, all_violations, character_data
                )

            report = IronLawsReport(
                action_id=proposed_action.action_id,
                overall_result=validation_result,
                violations=all_violations,
                checks_performed=[
                    "E001_Causality_Law",
                    "E002_Resource_Law",
                    "E003_Physics_Law",
                    "E004_Narrative_Law",
                    "E005_Social_Law",
                ],
                repair_attempts=repair_log,
                final_action=repaired_action,
            )

            return self._wrap_report(report, started_at)

        except Exception as e:  # pragma: no cover - defensive path
            logger.error(f"Error during Iron Laws validation: {str(e)}")
            return self._wrap_report(
                IronLawsReport(
                    action_id=action_id,
                    overall_result=ValidationResult.CATASTROPHIC_FAILURE,
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
                    checks_performed=[
                        "E001_Causality_Law",
                        "E002_Resource_Law",
                        "E003_Physics_Law",
                        "E004_Narrative_Law",
                        "E005_Social_Law",
                    ],
                    repair_attempts=[f"System error: {str(e)}"],
                    final_action=None,
                ),
                started_at,
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
        violations: List[IronLawsViolation] = []
        reasoning = (action.reasoning or "").strip()
        if len(reasoning) < 3:
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

        target = action.target
        if target is None or not getattr(target, "entity_id", "").strip():
            violations.append(
                IronLawsViolation(
                    law_code="E001",
                    law_name="Causality_Law",
                    severity="error",
                    description="Action is missing a concrete target",
                    affected_entities=[action.character_id],
                    suggested_repair="Specify a valid target entity",
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
        violations: List[IronLawsViolation] = []

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
        current_stamina = self._get_resource_value(character_data, "stamina")

        if current_stamina is not None and current_stamina.current < stamina_cost:
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
        violations: List[IronLawsViolation] = []

        if not character_data:
            return violations

        character_position = self._get_position(character_data)
        if character_position is None:
            return violations

        if action.action_type == ActionType.MOVE and action.target:
            target_position = self._get_position(action.target)
            if target_position:
                distance = self._calculate_distance(character_position, target_position)
                max_movement = self._calculate_max_movement_distance(character_data)
                allowable = max_movement * max(1.0, action.parameters.duration or 1.0)
                if distance > allowable:
                    violations.append(
                        IronLawsViolation(
                            law_code="E003",
                            law_name="Physics_Law",
                            severity="error",
                            description=f"Movement distance {distance:.1f} exceeds allowable {allowable:.1f}",
                            affected_entities=[action.character_id],
                            suggested_repair="Increase duration or choose a nearer location",
                        )
                    )

        if (
            action.action_type in [ActionType.ATTACK, ActionType.OBSERVE]
            and action.target
        ):
            target_pos = self._get_position(action.target)
            if target_pos:
                distance = self._calculate_distance(character_position, target_pos)
                action_range = action.parameters.range or 0.0
                if action_range and distance > action_range:
                    violations.append(
                        IronLawsViolation(
                            law_code="E003",
                            law_name="Physics_Law",
                            severity="warning",
                            description="Action range shorter than required distance",
                            affected_entities=[action.character_id],
                            suggested_repair="Move closer before executing the action",
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
        violations: List[IronLawsViolation] = []

        reasoning = (action.reasoning or "").lower()
        target_id = (action.target.entity_id if action.target else "").lower()

        if action.action_type == ActionType.ATTACK:
            if any(keyword in target_id for keyword in ("ally", "friend")) or any(
                keyword in reasoning for keyword in ("ally", "friend")
            ):
                violations.append(
                    IronLawsViolation(
                        law_code="E004",
                        law_name="Narrative_Law",
                        severity="error",
                        description="Attacking allies without justification breaks narrative coherence",
                        affected_entities=[agent.character_id],
                        suggested_repair="Coordinate with allies instead of attacking them",
                    )
                )

        if not reasoning:
            violations.append(
                IronLawsViolation(
                    law_code="E004",
                    law_name="Narrative_Law",
                    severity="warning",
                    description="Action lacks narrative intent or motivation",
                    affected_entities=[agent.character_id],
                    suggested_repair="Describe the narrative purpose of the action",
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
        violations: List[IronLawsViolation] = []

        target_id = (action.target.entity_id if action.target else "").lower()
        intensity = self._normalize_intensity(action.parameters.intensity)

        if intensity in {"high", "extreme"} and (
            "command" in target_id or "superior" in target_id
        ):
            violations.append(
                IronLawsViolation(
                    law_code="E005",
                    law_name="Social_Law",
                    severity="warning",
                    description="Communication violates command hierarchy expectations",
                    affected_entities=[agent.character_id],
                    suggested_repair="Reduce communication intensity with superiors",
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
        if not violations:
            return None, []

        if not isinstance(proposed_action, ProposedAction):
            dummy_agent = SimpleNamespace(
                character_id=getattr(proposed_action, "character_id", "unknown")
            )
            proposed_action = self._ensure_proposed_action(proposed_action, dummy_agent)

        repair_log: List[str] = []
        modified_action = self._clone_action(proposed_action)

        if not IRON_LAWS_AVAILABLE:
            return None, ["Iron Laws types not available for repair"]

        # Group violations by law for systematic repair
        grouped_violations = self._group_violations_by_law(violations)

        # Attempt repairs for each law
        for law_code, law_violations in grouped_violations.items():
            if law_code == "E001":
                modified_action, law_repair_log = self._repair_causality_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E002":
                modified_action, law_repair_log = self._repair_resource_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E003":
                modified_action, law_repair_log = self._repair_physics_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E004":
                modified_action, law_repair_log = self._repair_narrative_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E005":
                modified_action, law_repair_log = self._repair_social_violations(
                    modified_action, law_violations, character_data
                )
            else:
                law_repair_log = [f"No repair strategy for {law_code}"]

            repair_log.extend(law_repair_log)

        # Convert to validated action if repairs were successful
        if modified_action != proposed_action or repair_log:
            validation_result = (
                ValidationResult.REQUIRES_REPAIR
                if repair_log
                else ValidationResult.VALID
            )
            validated_action = self._convert_proposed_to_validated(
                modified_action, validation_result
            )
            return validated_action, repair_log

        return None, repair_log

    def _calculate_action_stamina_cost(self, action: "ProposedAction") -> int:
        """Calculate stamina cost for an action."""
        parameters = getattr(action, "parameters", None)
        intensity_value = getattr(parameters, "intensity", ActionIntensity.NORMAL)
        duration_value = getattr(parameters, "duration", 1.0)
        intensity = self._normalize_intensity(intensity_value)
        intensity_factor = {
            "low": 0.6,
            "normal": 1.0,
            "high": 1.5,
            "extreme": 2.0,
        }.get(intensity, 1.0)

        duration = max(0.5, duration_value or 1.0)
        action_type = getattr(action, "action_type", ActionType.MOVE)
        is_move = (
            action_type == ActionType.MOVE
            if isinstance(action_type, ActionType)
            else str(action_type).lower() == "move"
        )
        base_cost = 10 if is_move else 12
        return max(1, int(round(base_cost * intensity_factor * duration)))

    def _get_action_equipment_requirements(self, action: "ProposedAction") -> List[str]:
        """Get equipment requirements for an action."""
        if action.action_type == ActionType.ATTACK:
            return ["basic_weapon"]
        if action.action_type == ActionType.DEFEND:
            return ["standard_armor"]
        return []

    def _character_has_equipment(
        self, character_data: "CharacterData", equipment: str
    ) -> bool:
        """Check if character has required equipment."""
        items = getattr(character_data, "equipment", None)
        if items is None and isinstance(character_data, dict):
            items = character_data.get("equipment")
        if items is None:
            return False
        return equipment in items

    @staticmethod
    def _calculate_distance(pos1: "Position", pos2: "Position") -> float:
        """Calculate distance between two positions."""
        if pos1 is None or pos2 is None:
            return 0.0
        return math.sqrt(
            (pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2 + (pos1.z - pos2.z) ** 2
        )

    def _calculate_max_movement_distance(self, character_data) -> float:
        """Calculate maximum movement distance for character."""
        stats = getattr(character_data, "stats", None)
        if stats is None and isinstance(character_data, dict):
            stats = character_data.get("stats")
        dexterity = getattr(stats, "dexterity", 5) if stats else 5
        strength = getattr(stats, "strength", 5) if stats else 5
        return 4.0 + (dexterity + strength) * 0.5

    def _group_violations_by_law(
        self, violations: List["IronLawsViolation"]
    ) -> Dict[str, List["IronLawsViolation"]]:
        """Group violations by law type."""
        grouped: Dict[str, List[IronLawsViolation]] = {}
        for violation in violations:
            grouped.setdefault(violation.law_code, []).append(violation)
        return grouped

    def _repair_causality_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair causality law violations."""
        repaired = self._clone_action(action)
        repair_log: List[str] = []

        if repaired.target is None or not repaired.target.entity_id.strip():
            repaired.target = ActionTarget(
                entity_id="auto_target",
                entity_type=getattr(repaired.target, "entity_type", EntityType.OBJECT),
            )
            repair_log.append("Added default target for causality compliance")

        if len((repaired.reasoning or "").strip()) < 3:
            repaired.reasoning = (
                "Acting to preserve continuity and achieve strategic objectives."
            )
            repair_log.append("Inserted reasoning to justify action")

        return repaired, repair_log or ["Causality repair not required"]

    def _repair_resource_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair resource law violations."""
        repaired = self._clone_action(action)
        repair_log: List[str] = []

        stamina = self._get_resource_value(character_data, "stamina")
        if stamina:
            allowable = stamina.current
            repaired.parameters.intensity = self._coerce_intensity(
                repaired.parameters.intensity
            )
            current_cost = self._calculate_action_stamina_cost(repaired)
            intensity_chain = [
                ActionIntensity.LOW,
                ActionIntensity.NORMAL,
                ActionIntensity.HIGH,
                ActionIntensity.EXTREME,
            ]
            while current_cost > allowable:
                current_intensity = self._coerce_intensity(
                    repaired.parameters.intensity
                )
                idx = intensity_chain.index(current_intensity)
                if idx == 0:
                    break
                repaired.parameters.intensity = intensity_chain[idx - 1]
                repair_log.append("Reduced intensity to satisfy stamina limits")
                current_cost = self._calculate_action_stamina_cost(repaired)

            if current_cost > allowable and repaired.parameters.duration:
                repaired.parameters.duration = max(
                    1.0, repaired.parameters.duration - 1.0
                )
                repair_log.append("Reduced action duration for resource compliance")

        return repaired, repair_log or ["Resource repair not required"]

    def _repair_physics_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair physics law violations."""
        repaired = self._clone_action(action)
        repair_log: List[str] = []

        character_position = self._get_position(character_data)
        target_position = self._get_position(repaired.target)
        if character_position and target_position:
            distance = self._calculate_distance(character_position, target_position)
            max_distance = self._calculate_max_movement_distance(character_data)
            if repaired.parameters.range and distance > repaired.parameters.range:
                repaired.parameters.range = distance
                repair_log.append("Adjusted movement range to cover target distance")
            if distance > max_distance * max(1.0, repaired.parameters.duration or 1.0):
                repaired.parameters.duration = max(
                    1.0, math.ceil(distance / max_distance)
                )
                repair_log.append(
                    "Adjusted movement duration to satisfy physics limits"
                )
        else:
            if repaired.parameters.duration <= 0.1:
                repaired.parameters.duration = 1.0
                repair_log.append(
                    "Adjusted movement duration for physical plausibility"
                )
            if repaired.parameters.range and repaired.parameters.range > 200.0:
                repaired.parameters.range = 200.0
                repair_log.append("Adjusted movement range to realistic bounds")

        return repaired, repair_log or ["Physics repair not required"]

    def _repair_narrative_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair narrative law violations."""
        repaired = self._clone_action(action)
        repair_log: List[str] = []

        if (
            repaired.action_type == ActionType.ATTACK
            and repaired.target
            and "ally" in repaired.target.entity_id.lower()
        ):
            repaired.action_type = ActionType.COMMUNICATE
            repaired.reasoning = "Coordinating with ally to maintain story cohesion."
            repair_log.append(
                "Changed hostile action into supportive communication with ally"
            )

        return repaired, repair_log or ["Narrative repair not required"]

    def _repair_social_violations(
        self, action, violations, character_data
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair social law violations."""
        repaired = self._clone_action(action)
        repair_log: List[str] = []

        if self._normalize_intensity(repaired.parameters.intensity) in {
            "high",
            "extreme",
        }:
            repaired.parameters.intensity = ActionIntensity.NORMAL
            repair_log.append(
                "Adjusted communication intensity for hierarchy compliance"
            )

        return repaired, repair_log or ["Social repair not required"]

    def _convert_proposed_to_validated(
        self, proposed_action: "ProposedAction", validation_result: "ValidationResult"
    ) -> "ValidatedAction":
        """Convert proposed action to validated action."""
        return ValidatedAction(
            action_id=proposed_action.action_id,
            character_id=proposed_action.character_id,
            action_type=proposed_action.action_type,
            target=proposed_action.target,
            parameters=proposed_action.parameters,
            validation_result=validation_result,
            validation_details={},
            repairs_applied=[],
            estimated_effects={},
        )

    def _determine_overall_validation_result(
        self, violations: List["IronLawsViolation"]
    ) -> "ValidationResult":
        """Determine overall validation result from violations."""
        if not violations:
            return ValidationResult.VALID

        if any(v.severity == "critical" for v in violations):
            return ValidationResult.INVALID

        if any(v.severity == "error" for v in violations):
            return ValidationResult.REQUIRES_REPAIR

        return ValidationResult.VALID

    # Helper utilities -------------------------------------------------
    def _extract_character_data_from_agent(
        self, agent: "PersonaAgent"
    ) -> Optional["CharacterData"]:
        """Extract character data from agent for validation purposes."""
        if hasattr(agent, "character_data"):
            return agent.character_data
        if hasattr(agent, "model_dump"):
            return agent.model_dump()
        return None

    @staticmethod
    def _normalize_intensity(intensity: Any) -> str:
        if isinstance(intensity, ActionIntensity):
            return intensity.value
        if isinstance(intensity, str):
            return intensity.lower()
        return "normal"

    def _coerce_intensity(self, intensity: Any) -> ActionIntensity:
        if isinstance(intensity, ActionIntensity):
            return intensity
        normalized = self._normalize_intensity(intensity)
        for option in ActionIntensity:
            if option.value == normalized:
                return option
        return ActionIntensity.NORMAL

    @staticmethod
    def _get_position(source: Any) -> Optional[Position]:
        if source is None:
            return None
        position = getattr(source, "position", None)
        if position is None and isinstance(source, dict):
            position = source.get("position")
        return position

    @staticmethod
    def _get_resource_value(
        character_data: Optional[Any], resource_name: str
    ) -> Optional[ResourceValue]:
        if character_data is None:
            return None
        resources = getattr(character_data, "resources", None)
        if resources is None and isinstance(character_data, dict):
            resources = character_data.get("resources")
        if resources is None:
            return None
        value = getattr(resources, resource_name, None)
        if value is None and isinstance(resources, dict):
            value = resources.get(resource_name)
        return value

    def _ensure_proposed_action(
        self, action: Any, agent: "PersonaAgent"
    ) -> "ProposedAction":
        if isinstance(action, ProposedAction):
            return action

        action_type_value = getattr(action, "action_type", ActionType.MOVE)
        if not isinstance(action_type_value, ActionType):
            try:
                action_type_value = ActionType(action_type_value)
            except Exception:
                action_type_value = ActionType.MOVE

        character_id = getattr(
            action, "character_id", getattr(agent, "character_id", "unknown")
        )
        if not isinstance(character_id, str) or not character_id.strip():
            character_id = "unknown"
        reasoning_value = getattr(action, "reasoning", "Auto-generated reasoning")
        if not isinstance(reasoning_value, str) or not reasoning_value.strip():
            reasoning = "Auto-generated reasoning"
        else:
            reasoning = reasoning_value

        raw_params = getattr(action, "parameters", None)
        if isinstance(raw_params, ActionParameters):
            parameters = raw_params
        else:
            intensity = getattr(raw_params, "intensity", ActionIntensity.NORMAL)
            duration = getattr(raw_params, "duration", 1.0)
            range_value = getattr(raw_params, "range", 1.0)
            if not isinstance(intensity, ActionIntensity):
                try:
                    intensity = ActionIntensity(intensity)
                except Exception:
                    intensity = ActionIntensity.NORMAL
            try:
                duration = float(duration)
            except Exception:
                duration = 1.0
            try:
                range_value = float(range_value)
            except Exception:
                range_value = 1.0
            parameters = ActionParameters(
                intensity=intensity, duration=duration, range=range_value
            )

        target = getattr(action, "target", None)
        if target is not None and not isinstance(target, ActionTarget):
            entity_id = getattr(target, "entity_id", getattr(action, "target_id", None))
            if not isinstance(entity_id, str) or not entity_id.strip():
                entity_id = "auto_target"
            entity_type = getattr(target, "entity_type", EntityType.OBJECT)
            if not isinstance(entity_type, EntityType):
                try:
                    entity_type = EntityType(entity_type)
                except Exception:
                    entity_type = EntityType.OBJECT
            target = ActionTarget(
                entity_id=entity_id or "auto_target", entity_type=entity_type
            )

        payload: Dict[str, Any] = {
            "character_id": character_id,
            "action_type": action_type_value,
            "target": target,
            "parameters": parameters,
            "reasoning": reasoning,
        }
        action_identifier = getattr(action, "action_id", None)
        if action_identifier:
            payload["action_id"] = str(action_identifier)

        return ProposedAction(**payload)

    def _wrap_report(self, report: IronLawsReport, started_at: float) -> _ReportWrapper:
        return _ReportWrapper(report, processing_time=time.perf_counter() - started_at)

    def _build_failure_report(self, action_id: str, message: str) -> IronLawsReport:
        return IronLawsReport(
            action_id=action_id or "unknown",
            overall_result=ValidationResult.CATASTROPHIC_FAILURE,
            violations=[
                IronLawsViolation(
                    law_code="E000",
                    law_name="System_Error",
                    severity="critical",
                    description=message,
                    affected_entities=[str(action_id or "unknown")],
                    suggested_repair="Provide valid action input and character data",
                )
            ],
            checks_performed=[],
            repair_attempts=[message],
            final_action=None,
        )

    @staticmethod
    def _clone_action(action: Any) -> Any:
        if hasattr(action, "model_copy"):
            return action.model_copy()
        return deepcopy(action)



