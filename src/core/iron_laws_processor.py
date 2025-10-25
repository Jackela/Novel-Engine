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
        ActionIntensity,
        ActionParameters,
        ActionTarget,
        ActionType,
        EntityType,
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
            return IronLawsReport(
                action_id=getattr(proposed_action, "action_id", "unknown"),
                overall_result=ValidationResult.VALID,
                checks_performed=["validation_disabled"],
                violations=[],
                repair_attempts=["Iron Laws validation disabled"],
                final_action=None,
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
            if all_violations and validation_result != ValidationResult.INVALID:
                repaired_action, repair_log = self._attempt_action_repairs(
                    proposed_action, all_violations, character_data
                )

            # Create comprehensive report
            checks_performed = [
                "E001_Causality_Law",
                "E002_Resource_Law",
                "E003_Physics_Law",
                "E004_Narrative_Law",
                "E005_Social_Law",
            ]
            report = IronLawsReport(
                action_id=proposed_action.action_id,
                overall_result=validation_result,
                checks_performed=checks_performed,
                violations=all_violations,
                repair_attempts=repair_log,
                final_action=repaired_action,
            )

            return report

        except Exception as e:
            logger.error(f"Error during Iron Laws validation: {str(e)}")
            # Return rejection on unexpected errors
            # Safely extract action_id and character_id (handle Mock objects and None)
            try:
                action_id = str(getattr(proposed_action, "action_id", "unknown")) if proposed_action else "unknown"
                if action_id == "None":
                    action_id = "unknown"
            except:
                action_id = "unknown"
            
            try:
                char_id = str(getattr(proposed_action, "character_id", "unknown")) if proposed_action else "unknown"
                if char_id == "None":
                    char_id = "unknown"
            except:
                char_id = "unknown"
            
            return IronLawsReport(
                action_id=action_id,
                overall_result=ValidationResult.CATASTROPHIC_FAILURE,
                checks_performed=["system_error"],
                violations=[
                    IronLawsViolation(
                        law_code="E000",
                        law_name="System_Error",
                        severity="critical",
                        description=f"Validation system error: {str(e)}",
                        affected_entities=[char_id],
                        suggested_repair="Check system logs and action format",
                    )
                ],
                repair_attempts=[f"System error: {str(e)}"],
                final_action=None,
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
        
        # Handle both dict and object character_data
        if isinstance(character_data, dict):
            resources = character_data.get("resources", {})
            # Resources can be either a CharacterResources object or a dict
            if hasattr(resources, "stamina"):
                current_stamina = resources.stamina
            else:
                current_stamina = resources.get("stamina", ResourceValue(current=100, maximum=100))
        else:
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
        if action.action_type == ActionType.COMMUNICATE and action.target:
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

        # Attempt repairs for each law (grouped by law_code now)
        for law_code, law_violations in grouped_violations.items():
            law_repair_log = []
            
            if law_code == "E001":  # Causality Law
                modified_action, law_repair_log = self._repair_causality_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E002":  # Resource Law
                modified_action, law_repair_log = self._repair_resource_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E003":  # Physics Law
                modified_action, law_repair_log = self._repair_physics_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E004":  # Narrative Law
                modified_action, law_repair_log = self._repair_narrative_violations(
                    modified_action, law_violations, character_data
                )
            elif law_code == "E005":  # Social Law
                modified_action, law_repair_log = self._repair_social_violations(
                    modified_action, law_violations, character_data
                )

            if law_repair_log:
                repair_log.extend(law_repair_log)

        # Convert to validated action if repairs were successful
        if modified_action != proposed_action or repair_log:
            validation_result = ValidationResult.REQUIRES_REPAIR
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
        """Calculate stamina cost for an action based on type and intensity."""
        # Handle missing or None parameters
        if not hasattr(action, "parameters") or action.parameters is None:
            return 10  # Default cost
        
        # Base cost by action type
        base_costs = {
            ActionType.MOVE: 10,
            ActionType.INVESTIGATE: 8,
            ActionType.COMMUNICATE: 5,
            ActionType.ATTACK: 15,
            ActionType.DEFEND: 12,
            ActionType.SPECIAL_ABILITY: 14,
            ActionType.USE_ITEM: 6,
        }
        base_cost = base_costs.get(action.action_type, 10)
        
        # Intensity multipliers
        intensity_multipliers = {
            ActionIntensity.LOW: 0.5,
            ActionIntensity.NORMAL: 1.0,
            ActionIntensity.HIGH: 1.5,
            ActionIntensity.EXTREME: 3.0,
        }
        
        # Safely get intensity and duration with defaults
        try:
            intensity = getattr(action.parameters, "intensity", ActionIntensity.NORMAL)
            multiplier = intensity_multipliers.get(intensity, 1.0)
        except:
            multiplier = 1.0
        
        try:
            duration = getattr(action.parameters, "duration", 1.0)
            duration_factor = 1.0 + max(0, duration - 1.0) * 0.2
        except:
            duration_factor = 1.0
        
        total_cost = int(base_cost * multiplier * duration_factor)
        return max(1, total_cost)  # Minimum 1 stamina

    def _get_action_equipment_requirements(self, action: "ProposedAction") -> List[str]:
        """Get equipment requirements for an action."""
        return []  # Placeholder

    def _character_has_equipment(
        self, character_data: "CharacterData", equipment: str
    ) -> bool:
        """Check if character has required equipment."""
        return True  # Placeholder

    def _calculate_distance(self, pos1: "Position", pos2: "Position") -> float:
        """Calculate Euclidean distance between two positions."""
        if not pos1 or not pos2:
            return 0.0
        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        dz = pos2.z - pos1.z
        return (dx*dx + dy*dy + dz*dz) ** 0.5

    def _calculate_max_movement_distance(self, character_data) -> float:
        """Calculate maximum movement distance based on character stats and stamina."""
        # Base movement is 10 units per action
        base_movement = 10.0
        
        # Extract dexterity stat for movement bonus
        if isinstance(character_data, dict):
            stats = character_data.get("stats")
            if stats:
                dexterity = getattr(stats, "dexterity", 5) if hasattr(stats, "dexterity") else stats.get("dexterity", 5)
                # Higher dexterity = faster movement (up to 2x at dex 10)
                movement_multiplier = 1.0 + (dexterity - 5) * 0.1
                base_movement *= max(0.5, min(2.0, movement_multiplier))
        else:
            if hasattr(character_data, "stats") and character_data.stats:
                dexterity = getattr(character_data.stats, "dexterity", 5)
                movement_multiplier = 1.0 + (dexterity - 5) * 0.1
                base_movement *= max(0.5, min(2.0, movement_multiplier))
        
        return base_movement

    def _check_line_of_sight(
        self, from_pos: "Position", target, world_context: Dict[str, Any]
    ) -> bool:
        """Check if there's line of sight to target."""
        # For now, simple distance-based check
        # In production, would check for obstacles in world_context
        if not from_pos or not target:
            return False
        
        if hasattr(target, "position") and target.position:
            distance = self._calculate_distance(from_pos, target.position)
            # Line of sight up to 50 units
            return distance <= 50.0
        
        return True  # Allow if no position data

    def _action_contradicts_personality(
        self, action: "ProposedAction", personality_traits: Dict[str, Any]
    ) -> bool:
        """Check if action contradicts personality traits."""
        return False  # Placeholder

    def _get_character_rank(
        self, character_id: str, world_context: Dict[str, Any]
    ) -> str:
        """Get character's military rank from context or infer from ID."""
        # Check world_context for rank data
        if world_context and "characters" in world_context:
            char_data = world_context.get("characters", {}).get(character_id, {})
            if "rank" in char_data:
                return char_data["rank"]
        
        # Infer from character_id keywords
        character_id_lower = character_id.lower()
        if any(keyword in character_id_lower for keyword in ["general", "commander"]):
            return "general"
        elif any(keyword in character_id_lower for keyword in ["colonel"]):
            return "colonel"
        elif any(keyword in character_id_lower for keyword in ["captain", "officer", "superior"]):
            return "captain"
        elif any(keyword in character_id_lower for keyword in ["lieutenant"]):
            return "lieutenant"
        elif any(keyword in character_id_lower for keyword in ["sergeant"]):
            return "sergeant"
        
        return "private"  # Default

    def _is_insubordinate_communication(
        self, action: "ProposedAction", agent_rank: str, target_rank: str
    ) -> bool:
        """Check if communication violates military hierarchy."""
        # Rank hierarchy (higher number = higher rank)
        rank_hierarchy = {
            "private": 1,
            "corporal": 2,
            "sergeant": 3,
            "lieutenant": 4,
            "captain": 5,
            "major": 6,
            "colonel": 7,
            "general": 8,
        }
        
        agent_rank_value = rank_hierarchy.get(agent_rank.lower(), 1)
        target_rank_value = rank_hierarchy.get(target_rank.lower(), 1)
        
        # HIGH intensity communication to superior is insubordinate
        if action.parameters.intensity == ActionIntensity.HIGH and target_rank_value > agent_rank_value:
            return True
        
        # Shouting/ordering superiors
        if "shout" in action.reasoning.lower() or "order" in action.reasoning.lower():
            if target_rank_value > agent_rank_value:
                return True
        
        return False

    def _group_violations_by_law(
        self, violations: List["IronLawsViolation"]
    ) -> Dict[str, List["IronLawsViolation"]]:
        """Group violations by law code."""
        grouped = {}
        for violation in violations:
            if violation.law_code not in grouped:
                grouped[violation.law_code] = []
            grouped[violation.law_code].append(violation)
        return grouped

    def _repair_causality_violations(
        self, action, violations, character_data=None
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair causality law violations by fixing missing targets and reasoning."""
        repairs_made = []
        updates = {}
        
        for violation in violations:
            description = violation.description.lower()
            
            # Fix missing or empty target
            if "target" in description and (not action.target or not action.target.entity_id):
                # Create a generic target based on action type
                if action.action_type == ActionType.ATTACK:
                    target_id = "nearby_enemy"
                    entity_type = EntityType.CHARACTER
                elif action.action_type == ActionType.MOVE:
                    target_id = "destination"
                    entity_type = EntityType.LOCATION
                else:
                    target_id = "target_object"
                    entity_type = EntityType.OBJECT
                
                updates["target"] = ActionTarget(
                    entity_id=target_id,
                    entity_type=entity_type
                )
                repairs_made.append(f"Added {entity_type.value} target: {target_id}")
            
            # Fix minimal or missing reasoning
            if "reasoning" in description and len(action.reasoning.strip()) <= 1:
                updates["reasoning"] = f"Performing {action.action_type.value} action to achieve tactical objective"
                repairs_made.append("Added logical reasoning for action")
        
        # Apply repairs if any were made
        if updates:
            repaired_action = action.model_copy(update=updates)
            return repaired_action, repairs_made
        
        return action, repairs_made if repairs_made else ["No repairs needed"]

    def _repair_resource_violations(
        self, action, violations, character_data=None
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair resource law violations by reducing action intensity or duration."""
        repairs_made = []
        updates = {}
        
        for violation in violations:
            description = violation.description.lower()
            
            # Reduce intensity if stamina insufficient
            if "stamina" in description or "resource" in description:
                current_intensity = action.parameters.intensity
                
                # Step down intensity
                intensity_steps = {
                    ActionIntensity.EXTREME: ActionIntensity.HIGH,
                    ActionIntensity.HIGH: ActionIntensity.NORMAL,
                    ActionIntensity.NORMAL: ActionIntensity.LOW,
                }
                
                if current_intensity in intensity_steps:
                    new_intensity = intensity_steps[current_intensity]
                    new_params = action.parameters.model_copy(
                        update={"intensity": new_intensity}
                    )
                    updates["parameters"] = new_params
                    repairs_made.append(
                        f"Reduced intensity from {current_intensity.value} to {new_intensity.value} to conserve stamina"
                    )
        
        # Apply repairs if any were made
        if updates:
            repaired_action = action.model_copy(update=updates)
            return repaired_action, repairs_made
        
        return action, repairs_made if repairs_made else ["No repairs possible"]

    def _repair_physics_violations(
        self, action, violations, character_data=None
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair physics law violations by adjusting duration and range."""
        repairs_made = []
        param_updates = {}
        
        for violation in violations:
            description = violation.description.lower()
            
            # Fix unrealistic movement speed/distance
            if "distance" in description or "movement" in description or "speed" in description:
                current_duration = action.parameters.duration
                current_range = action.parameters.range
                
                # Increase duration to realistic value
                if current_duration < 1.0:
                    param_updates["duration"] = max(1.0, current_duration * 10)
                    repairs_made.append(
                        f"Increased duration from {current_duration}s to {param_updates['duration']}s"
                    )
                
                # Reduce range to achievable distance
                if current_range > 100.0:
                    param_updates["range"] = min(100.0, current_range * 0.1)
                    repairs_made.append(
                        f"Reduced range from {current_range} to {param_updates['range']} for realistic movement"
                    )
                
                if repairs_made:
                    repairs_made.append("Adjusted movement parameters to be physically realistic")
        
        # Apply repairs if any were made
        if param_updates:
            new_params = action.parameters.model_copy(update=param_updates)
            repaired_action = action.model_copy(update={"parameters": new_params})
            return repaired_action, repairs_made
        
        return action, repairs_made if repairs_made else ["No repairs possible"]

    def _repair_narrative_violations(
        self, action, violations, character_data=None
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair narrative law violations by changing target or adding justification."""
        repairs_made = []
        updates = {}
        
        for violation in violations:
            description = violation.description.lower()
            
            # Change target if attacking allies
            if "ally" in description or "friend" in description:
                if action.target and "ally" in action.target.entity_id.lower():
                    updates["target"] = ActionTarget(
                        entity_id="hostile_enemy",
                        entity_type=EntityType.CHARACTER
                    )
                    repairs_made.append("Changed target from ally to enemy")
            
            # Add narrative justification if personality conflict
            if "personality" in description:
                current_reasoning = action.reasoning
                updates["reasoning"] = f"{current_reasoning} (Acting under duress or compelling circumstances)"
                repairs_made.append("Added narrative justification for out-of-character action")
        
        # Apply repairs if any were made
        if updates:
            repaired_action = action.model_copy(update=updates)
            return repaired_action, repairs_made
        
        return action, repairs_made if repairs_made else ["No repairs possible"]

    def _repair_social_violations(
        self, action, violations, character_data=None
    ) -> Tuple["ProposedAction", List[str]]:
        """Repair social law violations by adjusting intensity or communication style."""
        repairs_made = []
        updates = {}
        
        for violation in violations:
            description = violation.description.lower()
            
            # Reduce intensity if violating hierarchy
            if "hierarchy" in description or "insubordinate" in description:
                if action.parameters.intensity == ActionIntensity.HIGH:
                    new_params = action.parameters.model_copy(
                        update={"intensity": ActionIntensity.NORMAL}
                    )
                    updates["parameters"] = new_params
                    repairs_made.append("Adjusted communication intensity to respect hierarchy")
                
                # Fix reasoning to be more respectful
                if "demand" in action.reasoning.lower() or "shout" in action.reasoning.lower() or "order" in action.reasoning.lower():
                    updates["reasoning"] = "Respectfully communicating with superior officer following proper protocol"
                    repairs_made.append("Adjusted communication style to follow proper chain of command")
        
        # Apply repairs if any were made
        if updates:
            repaired_action = action.model_copy(update=updates)
            return repaired_action, repairs_made
        
        return action, repairs_made if repairs_made else ["No repairs possible"]

    def _convert_proposed_to_validated(
        self, proposed_action: "ProposedAction", validation_result: "ValidationResult"
    ) -> "ValidatedAction":
        """Convert proposed action to validated action."""
        from src.shared_types import ValidatedAction
        
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

        # Check for critical violations
        critical_violations = [v for v in violations if v.severity == "critical"]
        if critical_violations:
            return ValidationResult.INVALID

        # Check for error violations
        error_violations = [v for v in violations if v.severity == "error"]
        if error_violations:
            return ValidationResult.REQUIRES_REPAIR

        # Only warnings remain
        return ValidationResult.VALID
