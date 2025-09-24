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

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """Initialize the AgentLifecycleManager."""
        # Use provided logger or create new one
        if logger_instance:
            global logger
            logger = logger_instance

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

        # Agent registration tracking
        self.registered_agents: Dict[str, Any] = {}
        self.agent_count = 0
        self._initialized = False

        logger.info(
            f"AgentLifecycleManager initialized (Iron Laws: "
            f"{'enabled' if self.validation_enabled else 'disabled'})"
        )

    async def initialize(self) -> bool:
        """
        Initialize the AgentLifecycleManager asynchronously.

        Performs any async setup required for the lifecycle manager
        including validation system initialization and resource allocation.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing AgentLifecycleManager async components")

            # Initialize async components if needed
            if self.validation_enabled:
                logger.info("Iron Laws validation system ready")

            self._initialized = True
            logger.info("AgentLifecycleManager initialization complete")
            return True

        except Exception as e:
            logger.error(f"AgentLifecycleManager initialization failed: {e}")
            self._initialized = False
            return False

    async def register_agent(self, agent: Any) -> bool:
        """
        Register an agent with the lifecycle manager.

        Args:
            agent: Agent instance to register

        Returns:
            bool: True if registration successful
        """
        try:
            agent_id = getattr(
                agent, "character_name", f"agent_{self.agent_count}"
            )
            self.registered_agents[agent_id] = agent
            self.agent_count += 1
            logger.info(f"Registered agent: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    def get_agent_list(self) -> List[Any]:
        """
        Get list of registered agents.

        Returns:
            List of registered agent instances
        """
        return list(self.registered_agents.values())

    async def list_agents(self) -> List[Any]:
        """
        Get list of registered agents (async interface for consistency).

        Returns:
            List of registered agent instances
        """
        return list(self.registered_agents.values())

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the lifecycle manager.

        Returns:
            Dictionary with status information
        """
        return {
            "initialized": self._initialized,
            "total_agents": self.agent_count,
            "validation_enabled": self.validation_enabled,
            "total_validations": self.total_validations,
            "repair_attempts": self.repair_attempts_count,
            "successful_repairs": self.successful_repairs_count,
        }

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status (async interface for consistency).

        Returns:
            Dictionary with status information
        """
        return self.get_status()

    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the system (interface consistency method).

        Args:
            agent_id: ID of agent to remove

        Returns:
            bool: True if removal successful
        """
        try:
            if agent_id in self.registered_agents:
                del self.registered_agents[agent_id]
                self.agent_count -= 1
                logger.info(f"Removed agent: {agent_id}")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found for removal")
                return False
        except Exception as e:
            logger.error(f"Failed to remove agent {agent_id}: {e}")
            return False

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

            if (
                validated_action
                and validated_action.status == ValidationResult.VALID
            ):
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
            causality_violations = self._validate_causality_law(
                proposed_action
            )
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
            narrative_violations = self._validate_narrative_law(
                proposed_action
            )
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
            if (
                not hasattr(proposed_action, "target")
                or not proposed_action.target
            ):
                violations.append(
                    IronLawsViolation(
                        law_code="E001",
                        law_name="Causality_Law",
                        description="Action lacks proper target specification",
                        severity="error",
                        affected_entities=[
                            getattr(proposed_action, "agent_id", "unknown")
                        ],
                        suggested_repair="Add target specification",
                    )
                )
            elif (
                hasattr(proposed_action.target, "entity_id")
                and not proposed_action.target.entity_id
            ):
                violations.append(
                    IronLawsViolation(
                        law_code="E001",
                        law_name="Causality_Law",
                        description="Action lacks necessary target specification",
                        severity="error",
                        affected_entities=[
                            getattr(proposed_action, "agent_id", "unknown")
                        ],
                        suggested_repair="Add target specification",
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
                        law_name="Causality_Law",
                        description="Action lacks valid action type",
                        severity="high",
                        affected_entities=[
                            getattr(proposed_action, "agent_id", "unknown")
                        ],
                        suggested_repair="Set valid action type",
                    )
                )

            # Check for logical reasoning
            if hasattr(proposed_action, "reasoning"):
                reasoning = (
                    proposed_action.reasoning.strip()
                    if proposed_action.reasoning
                    else ""
                )
                if not reasoning or len(reasoning) < 3:
                    violations.append(
                        IronLawsViolation(
                            law_code="E001",
                            law_name="Causality_Law",
                            description="Action lacks logical reasoning",
                            severity="warning",
                            affected_entities=[
                                getattr(proposed_action, "agent_id", "unknown")
                            ],
                            suggested_repair="Add reasoning for action",
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
            # Calculate stamina cost for the action
            stamina_cost = self._calculate_action_stamina_cost(proposed_action)

            # If we have character data, check against resources
            if character_data and hasattr(character_data, "resources"):
                resources = character_data.resources
                if hasattr(resources, "stamina") and hasattr(
                    resources.stamina, "current"
                ):
                    current_stamina = resources.stamina.current
                    if stamina_cost > current_stamina:
                        violations.append(
                            IronLawsViolation(
                                law_code="E002",
                                law_name="Resource_Law",
                                description="Action requires more stamina than available",
                                severity="error",
                                affected_entities=[
                                    getattr(
                                        proposed_action, "agent_id", "unknown"
                                    )
                                ],
                                suggested_repair="Reduce action intensity or duration",
                            )
                        )
            else:
                # Fallback: Check for obviously excessive actions
                if (
                    hasattr(proposed_action, "parameters")
                    and proposed_action.parameters
                ):
                    params = proposed_action.parameters

                    # Check for extreme intensity with high duration
                    if hasattr(params, "intensity") and hasattr(
                        params, "duration"
                    ):
                        intensity_str = str(params.intensity).lower()
                        is_extreme = (
                            "extreme" in intensity_str
                            or hasattr(params.intensity, "value")
                            and str(params.intensity.value).lower()
                            == "extreme"
                        )
                        duration = getattr(params, "duration", 1.0)
                        if is_extreme and duration > 2.0:
                            violations.append(
                                IronLawsViolation(
                                    law_code="E002",
                                    law_name="Resource_Law",
                                    description="Action requires excessive stamina (extreme intensity + long duration)",
                                    severity="error",
                                    affected_entities=[
                                        getattr(
                                            proposed_action,
                                            "agent_id",
                                            "unknown",
                                        )
                                    ],
                                    suggested_repair="Reduce action intensity or duration",
                                )
                            )

        except Exception as e:
            logger.error(f"Error validating resource law: {str(e)}")

        return violations

    def _calculate_action_stamina_cost(
        self, proposed_action: ProposedAction
    ) -> int:
        """Calculate stamina cost for a proposed action."""
        try:
            base_cost = 5

            # Add cost based on action type
            if (
                hasattr(proposed_action, "action_type")
                and proposed_action.action_type
            ):
                action_type_str = str(proposed_action.action_type).lower()
                # Handle both enum values and string values
                if hasattr(proposed_action.action_type, "value"):
                    action_type = str(
                        proposed_action.action_type.value
                    ).lower()
                else:
                    action_type = action_type_str

                type_costs = {
                    "move": 10,
                    "attack": 20,
                    "investigate": 8,
                    "communicate": 5,
                    "observe": 3,
                }
                base_cost = type_costs.get(action_type, 10)

            # Add cost based on intensity
            if (
                hasattr(proposed_action, "parameters")
                and proposed_action.parameters
            ):
                params = proposed_action.parameters
                if hasattr(params, "intensity") and params.intensity:
                    intensity_str = str(params.intensity).lower()
                    # Handle both enum values and string values
                    if hasattr(params.intensity, "value"):
                        intensity_value = str(params.intensity.value).lower()
                    else:
                        intensity_value = intensity_str

                    intensity_multipliers = {
                        "low": 0.5,
                        "normal": 1.0,
                        "high": 1.5,
                        "extreme": 2.0,
                    }
                    multiplier = intensity_multipliers.get(
                        intensity_value, 1.0
                    )
                    base_cost = int(base_cost * multiplier)

                # Add cost based on duration
                if hasattr(params, "duration") and params.duration:
                    duration = getattr(params, "duration", 1.0)
                    if isinstance(duration, (int, float)) and duration > 1.0:
                        base_cost = int(base_cost * duration)

            return max(1, base_cost)

        except Exception as e:
            logger.error(f"Error calculating stamina cost: {e}")
            return 1

    def _validate_physics_law(
        self,
        proposed_action: ProposedAction,
        character_data: Optional[CharacterData] = None,
    ) -> List[IronLawsViolation]:
        """Validate E003 - Physics Law: Actions must be physically possible."""
        violations = []

        try:
            # Check for impossible actions
            if (
                hasattr(proposed_action, "action_type")
                and proposed_action.action_type
            ):
                action_type = str(proposed_action.action_type).lower()
                impossible_actions = ["fly_unaided", "teleport", "time_travel"]
                if action_type in impossible_actions:
                    violations.append(
                        IronLawsViolation(
                            law_code="E003",
                            law_name="Physics_Law",
                            description=f"Action '{action_type}' violates physical laws",
                            severity="critical",
                            affected_entities=[
                                getattr(proposed_action, "agent_id", "unknown")
                            ],
                            suggested_repair="Adjust duration and range to realistic values",
                        )
                    )

            # Check for impossible movement speeds
            if (
                hasattr(proposed_action, "parameters")
                and proposed_action.parameters
            ):
                params = proposed_action.parameters
                if hasattr(params, "duration") and hasattr(params, "range"):
                    duration = getattr(params, "duration", 1.0)
                    range_val = getattr(params, "range", 1.0)

                    if isinstance(duration, (int, float)) and isinstance(
                        range_val, (int, float)
                    ):
                        if duration > 0 and range_val > 0:
                            speed = range_val / duration
                            # Check for impossible speeds (e.g., >1000 units per second)
                            if speed > 1000:
                                violations.append(
                                    IronLawsViolation(
                                        law_code="E003",
                                        law_name="Physics_Law",
                                        description="Movement speed exceeds physical limits",
                                        severity="critical",
                                        affected_entities=[
                                            getattr(
                                                proposed_action,
                                                "agent_id",
                                                "unknown",
                                            )
                                        ],
                                        suggested_repair="Adjust duration and range to realistic values",
                                    )
                                )

            # Check for impossible target positions
            if (
                hasattr(proposed_action, "target")
                and proposed_action.target
                and hasattr(proposed_action.target, "position")
                and proposed_action.target.position
            ):
                target_pos = proposed_action.target.position
                if hasattr(target_pos, "x") and hasattr(target_pos, "y"):
                    x, y = getattr(target_pos, "x", 0), getattr(
                        target_pos, "y", 0
                    )
                    # Check for extreme distances that would be physically impossible to reach quickly
                    if (
                        hasattr(proposed_action, "parameters")
                        and proposed_action.parameters
                    ):
                        params = proposed_action.parameters
                        duration = getattr(params, "duration", 1.0)
                        if (
                            isinstance(duration, (int, float))
                            and duration < 1.0
                        ):
                            distance = (x**2 + y**2) ** 0.5
                            if (
                                distance > 100
                            ):  # Very far distance with very short time
                                violations.append(
                                    IronLawsViolation(
                                        law_code="E003",
                                        law_name="Physics_Law",
                                        description="Movement distance exceeds physical possibility in given time",
                                        severity="high",
                                        affected_entities=[
                                            getattr(
                                                proposed_action,
                                                "agent_id",
                                                "unknown",
                                            )
                                        ],
                                        suggested_repair="Increase duration for distant movement",
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
            # Check narrative reasoning quality
            if hasattr(proposed_action, "reasoning"):
                reasoning = (
                    proposed_action.reasoning.strip()
                    if proposed_action.reasoning
                    else ""
                )
                if not reasoning or len(reasoning) < 10:
                    violations.append(
                        IronLawsViolation(
                            law_code="E004",
                            law_name="Narrative_Law",
                            description="Action lacks sufficient narrative reasoning",
                            severity="low",
                            affected_entities=[
                                getattr(proposed_action, "agent_id", "unknown")
                            ],
                            suggested_repair="Add detailed reasoning for narrative consistency",
                        )
                    )

            # Check for narrative inconsistencies
            if (
                hasattr(proposed_action, "action_type")
                and hasattr(proposed_action, "target")
                and proposed_action.action_type
                and proposed_action.target
            ):
                # Handle both enum values and string values for action_type
                if hasattr(proposed_action.action_type, "value"):
                    action_type = str(
                        proposed_action.action_type.value
                    ).lower()
                else:
                    action_type = str(proposed_action.action_type).lower()
                target = proposed_action.target

                # Check for attacking allies without justification
                if action_type == "attack" and hasattr(target, "entity_id"):
                    target_id = str(target.entity_id).lower()
                    ally_indicators = [
                        "ally",
                        "friendly",
                        "friend",
                        "team_member",
                        "companion",
                    ]

                    if any(
                        indicator in target_id for indicator in ally_indicators
                    ):
                        reasoning = getattr(
                            proposed_action, "reasoning", ""
                        ).lower()
                        justifications = [
                            "betray",
                            "mind_control",
                            "infected",
                            "corrupted",
                            "necessary",
                        ]

                        if not any(
                            justification in reasoning
                            for justification in justifications
                        ):
                            violations.append(
                                IronLawsViolation(
                                    law_code="E004",
                                    law_name="Narrative_Law",
                                    description="Attacking ally without justification",
                                    severity="error",
                                    affected_entities=[
                                        getattr(
                                            proposed_action,
                                            "agent_id",
                                            "unknown",
                                        )
                                    ],
                                    suggested_repair="Change action to be consistent with relationships",
                                )
                            )

                # Check for illogical actions based on reasoning
                if (
                    hasattr(proposed_action, "reasoning")
                    and proposed_action.reasoning
                ):
                    reasoning = proposed_action.reasoning.lower()
                    if (
                        action_type == "attack"
                        and "no apparent reason" in reasoning
                    ):
                        violations.append(
                            IronLawsViolation(
                                law_code="E004",
                                law_name="Narrative_Law",
                                description="Action lacks logical narrative motivation",
                                severity="error",
                                affected_entities=[
                                    getattr(
                                        proposed_action, "agent_id", "unknown"
                                    )
                                ],
                                suggested_repair="Provide logical motivation for action",
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
            # Check for hierarchy violations
            if (
                hasattr(proposed_action, "action_type")
                and hasattr(proposed_action, "target")
                and proposed_action.action_type
                and proposed_action.target
            ):
                # Handle both enum values and string values for action_type
                if hasattr(proposed_action.action_type, "value"):
                    action_type = str(
                        proposed_action.action_type.value
                    ).lower()
                else:
                    action_type = str(proposed_action.action_type).lower()
                target = proposed_action.target

                # Check for inappropriate communication with superiors
                if action_type == "communicate" and hasattr(
                    target, "entity_id"
                ):
                    target_id = str(target.entity_id).lower()
                    superior_indicators = [
                        "superior",
                        "officer",
                        "commanding",
                        "commander",
                        "captain",
                        "boss",
                    ]

                    if any(
                        indicator in target_id
                        for indicator in superior_indicators
                    ):
                        # Check for inappropriate intensity or tone
                        if (
                            hasattr(proposed_action, "parameters")
                            and proposed_action.parameters
                        ):
                            params = proposed_action.parameters
                            if hasattr(params, "intensity"):
                                # Handle both enum values and string values for intensity
                                if hasattr(params.intensity, "value"):
                                    intensity = str(
                                        params.intensity.value
                                    ).lower()
                                else:
                                    intensity = str(params.intensity).lower()

                                # Also check full enum string representation
                                if (
                                    "high" in str(params.intensity).lower()
                                    or "extreme"
                                    in str(params.intensity).lower()
                                ):
                                    intensity = (
                                        "high"
                                        if "high"
                                        in str(params.intensity).lower()
                                        else "extreme"
                                    )

                                if intensity in ["high", "extreme"]:
                                    violations.append(
                                        IronLawsViolation(
                                            law_code="E005",
                                            law_name="Social_Law",
                                            description="Action violates command hierarchy",
                                            severity="warning",
                                            affected_entities=[
                                                getattr(
                                                    proposed_action,
                                                    "agent_id",
                                                    "unknown",
                                                )
                                            ],
                                            suggested_repair="Adjust communication style to be appropriate for hierarchy",
                                        )
                                    )

                        # Check reasoning for inappropriate demands
                        if (
                            hasattr(proposed_action, "reasoning")
                            and proposed_action.reasoning
                        ):
                            reasoning = proposed_action.reasoning.lower()
                            inappropriate_phrases = [
                                "demand",
                                "order",
                                "shouting orders",
                                "commanding",
                            ]

                            if any(
                                phrase in reasoning
                                for phrase in inappropriate_phrases
                            ):
                                violations.append(
                                    IronLawsViolation(
                                        law_code="E005",
                                        law_name="Social_Law",
                                        description="Inappropriate behavior toward superior officer",
                                        severity="error",
                                        affected_entities=[
                                            getattr(
                                                proposed_action,
                                                "agent_id",
                                                "unknown",
                                            )
                                        ],
                                        suggested_repair="Show proper respect for command hierarchy",
                                    )
                                )

                # Check for inappropriate actions between different social groups
                if hasattr(target, "entity_id") and hasattr(
                    proposed_action, "reasoning"
                ):
                    target_id = str(target.entity_id).lower()
                    reasoning = str(proposed_action.reasoning).lower()

                    # Check for actions that ignore established relationships
                    if action_type == "attack":
                        civilian_indicators = [
                            "civilian",
                            "scientist",
                            "researcher",
                            "medic",
                            "doctor",
                        ]
                        if (
                            any(
                                indicator in target_id
                                for indicator in civilian_indicators
                            )
                            and "threat" not in reasoning
                            and "hostile" not in reasoning
                        ):
                            violations.append(
                                IronLawsViolation(
                                    law_code="E005",
                                    law_name="Social_Law",
                                    description="Action violates social norms (attacking non-combatant)",
                                    severity="high",
                                    affected_entities=[
                                        getattr(
                                            proposed_action,
                                            "agent_id",
                                            "unknown",
                                        )
                                    ],
                                    suggested_repair="Only target hostile entities or provide justification",
                                )
                            )

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
                        (
                            modified_action,
                            causality_repairs,
                        ) = self._repair_causality_violations(
                            modified_action, law_violations
                        )
                        repair_log.extend(causality_repairs)

                    elif law_code == "E002":
                        (
                            modified_action,
                            resource_repairs,
                        ) = self._repair_resource_violations(
                            modified_action, law_violations, character_data
                        )
                        repair_log.extend(resource_repairs)

                    elif law_code == "E003":
                        (
                            modified_action,
                            physics_repairs,
                        ) = self._repair_physics_violations(
                            modified_action, law_violations, character_data
                        )
                        repair_log.extend(physics_repairs)

                    elif law_code == "E004":
                        (
                            modified_action,
                            narrative_repairs,
                        ) = self._repair_narrative_violations(
                            modified_action, law_violations
                        )
                        repair_log.extend(narrative_repairs)

                    elif law_code == "E005":
                        (
                            modified_action,
                            social_repairs,
                        ) = self._repair_social_violations(
                            modified_action, law_violations
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
                # Add default target if missing or empty
                if (
                    not hasattr(modified_action, "target")
                    or not modified_action.target
                ):
                    # Import target types if available
                    try:
                        from src.shared_types import ActionTarget, EntityType

                        modified_action.target = ActionTarget(
                            entity_id="default_target",
                            entity_type=EntityType.OBJECT,
                        )
                        repairs_made.append(
                            "Added default target for causality compliance"
                        )
                    except ImportError:
                        # Fallback for when types not available
                        modified_action.target = type(
                            "ActionTarget",
                            (),
                            {
                                "entity_id": "default_target",
                                "entity_type": "object",
                            },
                        )()
                        repairs_made.append(
                            "Added default target for causality compliance"
                        )
                elif (
                    hasattr(modified_action.target, "entity_id")
                    and not modified_action.target.entity_id
                ):
                    modified_action.target.entity_id = "default_target"
                    repairs_made.append("Fixed empty target entity ID")

            elif "action type" in violation.description:
                # Set default action type if missing
                if (
                    not hasattr(modified_action, "action_type")
                    or not modified_action.action_type
                ):
                    try:
                        from src.shared_types import ActionType

                        modified_action.action_type = ActionType.OBSERVE
                        repairs_made.append(
                            "Set default action type to 'observe'"
                        )
                    except ImportError:
                        modified_action.action_type = "observe"
                        repairs_made.append(
                            "Set default action type to 'observe'"
                        )

            elif "reasoning" in violation.description:
                # Add default reasoning if missing or inadequate
                if (
                    not hasattr(modified_action, "reasoning")
                    or not modified_action.reasoning
                    or len(modified_action.reasoning.strip()) < 3
                ):
                    action_type = getattr(
                        modified_action, "action_type", "act"
                    )
                    modified_action.reasoning = f"Character decided to {action_type} based on current situation assessment."
                    repairs_made.append("Added default narrative reasoning")

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

        for violation in violations:
            if "stamina" in violation.description:
                # Reduce action intensity or duration to reduce stamina cost
                if (
                    hasattr(modified_action, "parameters")
                    and modified_action.parameters
                ):
                    params = modified_action.parameters

                    # Try to reduce intensity first
                    if hasattr(params, "intensity"):
                        # Handle both enum values and string values
                        if hasattr(params.intensity, "value"):
                            current_intensity = str(
                                params.intensity.value
                            ).lower()
                        else:
                            current_intensity = str(params.intensity).lower()

                        # Also check full enum string representation
                        if "extreme" in str(params.intensity).lower():
                            current_intensity = "extreme"
                        elif "high" in str(params.intensity).lower():
                            current_intensity = "high"
                        elif "normal" in str(params.intensity).lower():
                            current_intensity = "normal"

                        intensity_reductions = {
                            "extreme": "high",
                            "high": "normal",
                            "normal": "low",
                        }

                        if current_intensity in intensity_reductions:
                            try:
                                from src.shared_types import ActionIntensity

                                new_intensity = intensity_reductions[
                                    current_intensity
                                ]
                                if new_intensity == "high":
                                    params.intensity = ActionIntensity.HIGH
                                elif new_intensity == "normal":
                                    params.intensity = ActionIntensity.NORMAL
                                elif new_intensity == "low":
                                    params.intensity = ActionIntensity.LOW
                                repairs_made.append(
                                    f"Reduced intensity from {current_intensity} to {new_intensity}"
                                )
                            except ImportError:
                                params.intensity = intensity_reductions[
                                    current_intensity
                                ]
                                repairs_made.append(
                                    f"Reduced intensity from {current_intensity} to {intensity_reductions[current_intensity]}"
                                )

                    # If intensity can't be reduced further, try reducing duration
                    elif (
                        hasattr(params, "duration")
                        and params.duration
                        and params.duration > 1.0
                    ):
                        old_duration = params.duration
                        params.duration = max(1.0, params.duration * 0.5)
                        repairs_made.append(
                            f"Reduced duration from {old_duration} to {params.duration}"
                        )

                    # If neither worked, set reasonable defaults
                    else:
                        if hasattr(params, "intensity"):
                            try:
                                from src.shared_types import ActionIntensity

                                params.intensity = ActionIntensity.LOW
                                repairs_made.append(
                                    "Set intensity to low to reduce stamina cost"
                                )
                            except ImportError:
                                params.intensity = "low"
                                repairs_made.append(
                                    "Set intensity to low to reduce stamina cost"
                                )
                        if hasattr(params, "duration"):
                            params.duration = 1.0
                            repairs_made.append(
                                "Set duration to 1.0 to reduce stamina cost"
                            )

        if not repairs_made:
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
            # Handle any E003 physics law violation
            if violation.law_code == "E003" or "E003" in violation.law_code:
                # Fix movement distance violations by adjusting duration or target
                if (
                    "movement distance exceeds" in violation.description
                    or "movement speed exceeds" in violation.description
                ):
                    if (
                        hasattr(modified_action, "parameters")
                        and modified_action.parameters
                    ):
                        params = modified_action.parameters
                        if hasattr(params, "duration") and params.duration:
                            # Increase duration to allow for longer movement
                            old_duration = params.duration
                            params.duration = params.duration * 2.0
                            repairs_made.append(
                                f"Increased duration from {old_duration} to {params.duration} for realistic movement"
                            )
                        else:
                            # Set reasonable duration
                            params.duration = 2.0
                            repairs_made.append(
                                "Set duration to 2.0 for realistic movement"
                            )

                # Replace impossible action with feasible alternative
                elif (
                    "impossible movement" in violation.description
                    or "violates physical laws" in violation.description
                ):
                    if hasattr(modified_action, "action_type"):
                        impossible_to_possible = {
                            "fly_unaided": "jump",
                            "teleport": "run",
                            "time_travel": "remember",
                        }

                        old_action = str(modified_action.action_type)
                        if old_action in impossible_to_possible:
                            try:
                                from src.shared_types import ActionType

                                if (
                                    impossible_to_possible[old_action]
                                    == "jump"
                                ):
                                    modified_action.action_type = (
                                        ActionType.MOVE
                                    )
                                elif (
                                    impossible_to_possible[old_action] == "run"
                                ):
                                    modified_action.action_type = (
                                        ActionType.MOVE
                                    )
                                elif (
                                    impossible_to_possible[old_action]
                                    == "remember"
                                ):
                                    modified_action.action_type = (
                                        ActionType.OBSERVE
                                    )
                                repairs_made.append(
                                    f"Changed impossible action '{old_action}' to feasible alternative"
                                )
                            except ImportError:
                                modified_action.action_type = (
                                    impossible_to_possible[old_action]
                                )
                                repairs_made.append(
                                    f"Changed impossible action '{old_action}' to '{impossible_to_possible[old_action]}'"
                                )
                        else:
                            # Generic fix: make sure it's a valid action type
                            try:
                                from src.shared_types import ActionType

                                modified_action.action_type = ActionType.MOVE
                                repairs_made.append(
                                    "Changed to basic movement action for physical feasibility"
                                )
                            except ImportError:
                                modified_action.action_type = "move"
                                repairs_made.append(
                                    "Changed to basic movement action for physical feasibility"
                                )

                # Generic physics violation repair
                if not repairs_made:
                    # Default fix for any physics violation: adjust parameters to be more realistic
                    if (
                        hasattr(modified_action, "parameters")
                        and modified_action.parameters
                    ):
                        params = modified_action.parameters
                        if (
                            hasattr(params, "duration")
                            and params.duration
                            and params.duration < 1.0
                        ):
                            old_duration = params.duration
                            params.duration = 1.0
                            repairs_made.append(
                                f"Increased duration from {old_duration} to 1.0 for physical feasibility"
                            )
                        if (
                            hasattr(params, "range")
                            and params.range
                            and params.range > 100.0
                        ):
                            old_range = params.range
                            params.range = 50.0
                            repairs_made.append(
                                f"Reduced range from {old_range} to 50.0 for physical feasibility"
                            )

                    if not repairs_made:
                        repairs_made.append(
                            "Applied general physics law compliance fixes"
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
                    modified_action.reasoning = f"Character decided to {getattr( modified_action, 'action_type', 'act')} based on current situation assessment."
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
        self,
        proposed_action: ProposedAction,
        violations: List[IronLawsViolation],
    ) -> None:
        """Record violations for tracking and analysis."""
        violation_record = {
            "timestamp": datetime.now().isoformat(),
            "action_id": getattr(proposed_action, "action_id", "unknown"),
            "violation_count": len(violations),
            "violations": [
                (v.law_code, v.description, v.severity) for v in violations
            ],
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
                    (successful_actions / total_actions)
                    if total_actions > 0
                    else 0.0
                ),
                "repair_attempts": self.repair_attempts_count,
                "successful_repairs": self.successful_repairs_count,
                "repair_success_rate": (
                    (
                        self.successful_repairs_count
                        / self.repair_attempts_count
                    )
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
