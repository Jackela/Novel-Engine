#!/usr/bin/env python3
"""
Character Decision Maker Module
==============================

Handles decision-making logic for PersonaAgent characters.
Separated from the main PersonaAgent to follow Single Responsibility Principle.
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.types.shared_types import ActionPriority, CharacterAction


# Define ThreatLevel locally to avoid circular import
class ThreatLevel(Enum):
    """Enumeration for threat assessment levels used in character decision-making."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


logger = logging.getLogger(__name__)


class DecisionMaker:
    """
    Handles decision-making logic for character agents.

    This class encapsulates all decision-making algorithms that were previously
    part of the PersonaAgent class, improving maintainability and testability.
    """

    def __init__(self, agent_id: str):
        """
        Initialize the decision maker.

        Args:
            agent_id: Identifier for the agent
        """
        self.agent_id = agent_id
        self.decision_history: List[Dict[str, Any]] = []

    def make_decision(
        self,
        world_state_update: Dict[str, Any],
        character_data: Dict[str, Any],
        personality_traits: Dict[str, float],
        decision_weights: Dict[str, float],
        subjective_worldview: Dict[str, Any],
    ) -> Optional[CharacterAction]:
        """
        Make a character decision based on current world state and character attributes.

        Args:
            world_state_update: Current world state information
            character_data: Character information
            personality_traits: Character personality traits
            decision_weights: Character decision-making weights
            subjective_worldview: Character's subjective interpretation of the world

        Returns:
            CharacterAction object or None if no action should be taken
        """
        # Assess current situation
        situation_assessment = self._assess_current_situation(
            world_state_update, character_data, subjective_worldview
        )

        # Identify available actions
        available_actions = self._identify_available_actions(
            situation_assessment, character_data, subjective_worldview
        )

        if not available_actions:
            logger.debug(f"Agent {self.agent_id} found no available actions")
            return None

        # Evaluate each action
        action_evaluations = []
        for action in available_actions:
            score = self._evaluate_action_option(
                action,
                situation_assessment,
                personality_traits,
                decision_weights,
                subjective_worldview,
            )
            action_evaluations.append((action, score))

        # Select best action
        return self._select_best_action(action_evaluations, character_data)

    def _assess_current_situation(
        self,
        world_state_update: Dict[str, Any],
        character_data: Dict[str, Any],
        subjective_worldview: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assess the current situation for decision-making."""
        assessment = {
            "threat_level": self._assess_overall_threat_level(
                world_state_update, subjective_worldview
            ),
            "current_goals": self._get_current_goals(
                character_data, subjective_worldview
            ),
            "available_resources": self._assess_available_resources(
                character_data, subjective_worldview
            ),
            "social_obligations": self._assess_social_obligations(subjective_worldview),
            "mission_status": self._assess_mission_status(subjective_worldview),
            "environmental_factors": self._assess_environmental_factors(
                world_state_update
            ),
        }

        logger.debug(
            f"Agent {self.agent_id} situation assessment: {assessment['threat_level']}"
        )
        return assessment

    def _identify_available_actions(
        self,
        situation_assessment: Dict[str, Any],
        character_data: Dict[str, Any],
        subjective_worldview: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Identify actions available to the character in current situation."""
        available_actions = []

        # Basic actions always available
        basic_actions = [
            {
                "type": "observe",
                "description": "Observe surroundings and gather information",
            },
            {"type": "wait", "description": "Wait and assess the situation"},
            {"type": "move", "description": "Move to a different location"},
        ]
        available_actions.extend(basic_actions)

        # Combat actions if character has combat capability
        if self._character_has_combat_capability(character_data):
            combat_actions = [
                {"type": "attack", "description": "Engage hostile targets"},
                {"type": "defend", "description": "Take defensive position"},
                {"type": "retreat", "description": "Withdraw from combat"},
            ]
            available_actions.extend(combat_actions)

        # Social actions if other entities are present
        known_entities = subjective_worldview.get("known_entities", {})
        if known_entities:
            social_actions = [
                {
                    "type": "communicate",
                    "description": "Attempt communication with nearby entities",
                },
                {"type": "negotiate", "description": "Engage in negotiation"},
                {"type": "assist", "description": "Offer assistance to allies"},
            ]
            available_actions.extend(social_actions)

        # Professional actions based on character role
        profession_actions = self._get_profession_actions(character_data)
        available_actions.extend(profession_actions)

        return available_actions

    def _evaluate_action_option(
        self,
        action: Dict[str, Any],
        situation: Dict[str, Any],
        personality_traits: Dict[str, float],
        decision_weights: Dict[str, float],
        subjective_worldview: Dict[str, Any],
    ) -> float:
        """Evaluate an action option and return a score."""
        base_score = 0.5  # Neutral starting score

        action_type = action.get("type", "unknown")

        # Apply personality modifiers
        personality_score = self._apply_personality_modifiers(
            base_score, action_type, personality_traits
        )

        # Apply situational modifiers
        situational_score = self._apply_situational_modifiers(
            personality_score, action, situation, decision_weights
        )

        # Apply profession modifiers
        final_score = self._apply_profession_modifiers(
            situational_score, action_type, subjective_worldview
        )

        return max(0.0, min(1.0, final_score))  # Clamp to 0-1 range

    def _select_best_action(
        self,
        action_evaluations: List[Tuple[Dict[str, Any], float]],
        character_data: Dict[str, Any],
    ) -> Optional[CharacterAction]:
        """Select the best action from evaluated options."""
        if not action_evaluations:
            return None

        # Sort by score (highest first)
        action_evaluations.sort(key=lambda x: x[1], reverse=True)

        # Get action threshold for this character
        action_threshold = self._get_character_action_threshold(character_data)

        # Check if best action meets threshold
        best_action, best_score = action_evaluations[0]

        if best_score < action_threshold:
            logger.debug(
                f"Agent {self.agent_id} best action score {best_score:.2f} below threshold {action_threshold:.2f}"
            )
            return None

        # Generate reasoning and priority
        reasoning = self._generate_action_reasoning(best_action, best_score)
        priority = self._determine_action_priority(best_action, best_score)

        # Record decision in history
        self.decision_history.append(
            {
                "action": best_action,
                "score": best_score,
                "reasoning": reasoning,
                "timestamp": time.time(),
            }
        )

        return CharacterAction(
            agent_id=self.agent_id,
            action_type=best_action["type"],
            target=best_action.get("target"),
            reasoning=reasoning,
            priority=priority,
        )

    def _assess_overall_threat_level(
        self, world_state_update: Dict[str, Any], subjective_worldview: Dict[str, Any]
    ) -> ThreatLevel:
        """Assess overall threat level in current situation."""
        # Check for explicit threats in world state
        recent_events = world_state_update.get("recent_events", [])
        threat_indicators = 0

        for event in recent_events:
            event_description = event.get("description", "").lower()
            if any(
                keyword in event_description
                for keyword in ["threat", "danger", "attack", "hostile"]
            ):
                threat_indicators += 1

        # Check subjective worldview for threats
        known_entities = subjective_worldview.get("known_entities", {})
        hostile_entities = sum(
            1
            for entity_data in known_entities.values()
            if entity_data.get("disposition", "neutral") == "hostile"
        )

        # Calculate overall threat level
        if threat_indicators > 2 or hostile_entities > 3:
            return ThreatLevel.CRITICAL
        elif threat_indicators > 1 or hostile_entities > 1:
            return ThreatLevel.HIGH
        elif threat_indicators > 0 or hostile_entities > 0:
            return ThreatLevel.MODERATE
        else:
            return ThreatLevel.LOW

    def _get_current_goals(
        self, character_data: Dict[str, Any], subjective_worldview: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get current character goals."""
        goals = []

        # Primary mission goals
        mission_data = subjective_worldview.get("current_mission", {})
        if mission_data:
            goals.append(
                {
                    "type": "mission",
                    "description": mission_data.get(
                        "description", "Complete current mission"
                    ),
                    "priority": "high",
                }
            )

        # Faction goals
        faction = character_data.get("faction", "")
        if faction:
            goals.append(
                {
                    "type": "faction",
                    "description": f"Serve {faction} interests",
                    "priority": "medium",
                }
            )

        # Personal goals
        personal_motivations = character_data.get("psychological", {}).get(
            "motivations", {}
        )
        for motivation, weight in personal_motivations.items():
            if weight > 0.6:  # High priority personal goals
                goals.append(
                    {
                        "type": "personal",
                        "description": f"Pursue {motivation}",
                        "priority": "medium",
                    }
                )

        return goals

    def _assess_available_resources(
        self, character_data: Dict[str, Any], subjective_worldview: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess resources available to the character."""
        return {
            "equipment": subjective_worldview.get("equipment", []),
            "allies": subjective_worldview.get("known_allies", []),
            "capabilities": character_data.get("capabilities", {}),
            "knowledge": character_data.get("knowledge", {}),
        }

    def _assess_social_obligations(
        self, subjective_worldview: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Assess social obligations and relationships."""
        obligations = []
        relationships = subjective_worldview.get("relationships", {})

        for entity, relationship_data in relationships.items():
            strength = relationship_data.get("strength", 0.0)
            if strength > 0.5:  # Strong positive relationship
                obligations.append(
                    {"entity": entity, "type": "support", "strength": strength}
                )

        return obligations

    def _assess_mission_status(
        self, subjective_worldview: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess current mission status."""
        mission = subjective_worldview.get("current_mission", {})
        return {
            "active": bool(mission),
            "progress": mission.get("progress", 0.0),
            "time_remaining": mission.get("time_remaining"),
            "success_probability": mission.get("success_probability", 0.5),
        }

    def _assess_environmental_factors(
        self, world_state_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess environmental factors affecting decisions."""
        return {
            "location": world_state_update.get("current_location"),
            "time_of_day": world_state_update.get("time_of_day"),
            "weather": world_state_update.get("weather"),
            "visibility": world_state_update.get("visibility", "normal"),
        }

    def _character_has_combat_capability(self, character_data: Dict[str, Any]) -> bool:
        """Check if character has combat capabilities."""
        capabilities = character_data.get("capabilities", {})
        combat_skills = ["combat", "weapons", "tactics", "martial_arts"]

        return any(skill in capabilities for skill in combat_skills)

    def _get_profession_actions(
        self, character_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get actions specific to character's profession."""
        profession = character_data.get("rank_role", "").lower()
        profession_actions = []

        if "tech" in profession or "engineer" in profession:
            profession_actions.extend(
                [
                    {"type": "repair", "description": "Repair damaged equipment"},
                    {"type": "analyze", "description": "Analyze technical systems"},
                ]
            )
        elif "medic" in profession or "apothecary" in profession:
            profession_actions.extend(
                [
                    {"type": "heal", "description": "Provide medical assistance"},
                    {"type": "diagnose", "description": "Diagnose medical conditions"},
                ]
            )
        elif "scout" in profession or "ranger" in profession:
            profession_actions.extend(
                [
                    {"type": "scout", "description": "Scout ahead for threats"},
                    {"type": "track", "description": "Track enemy movements"},
                ]
            )

        return profession_actions

    def _apply_personality_modifiers(
        self, base_score: float, action_type: str, personality_traits: Dict[str, float]
    ) -> float:
        """Apply personality trait modifiers to action score."""
        modifier = 0.0

        # Aggressive trait affects combat actions
        if action_type in ["attack", "charge", "assault"]:
            modifier += personality_traits.get("aggressive", 0.5) - 0.5

        # Cautious trait affects risky actions
        if action_type in ["retreat", "observe", "wait"]:
            modifier += personality_traits.get("cautious", 0.5) - 0.5
        elif action_type in ["attack", "charge"]:
            modifier -= personality_traits.get("cautious", 0.5) - 0.5

        # Loyal trait affects faction-related actions
        if action_type in ["assist", "protect", "support"]:
            modifier += personality_traits.get("loyal", 0.5) - 0.5

        return base_score + (modifier * 0.3)  # Cap personality influence at 30%

    def _apply_situational_modifiers(
        self,
        base_score: float,
        action: Dict[str, Any],
        situation: Dict[str, Any],
        decision_weights: Dict[str, float],
    ) -> float:
        """Apply situational modifiers to action score."""
        modifier = 0.0
        action_type = action.get("type", "")

        # Threat level affects action preferences
        threat_level = situation.get("threat_level", ThreatLevel.LOW)
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            if action_type in ["attack", "defend"]:
                modifier += 0.2
            elif action_type in ["wait", "observe"]:
                modifier -= 0.1

        # Mission priority affects action selection
        mission_priority = decision_weights.get("mission_success", 0.5)
        if action_type in ["complete_objective", "advance_mission"]:
            modifier += (mission_priority - 0.5) * 0.4

        return base_score + modifier

    def _apply_profession_modifiers(
        self, base_score: float, action_type: str, subjective_worldview: Dict[str, Any]
    ) -> float:
        """Apply profession-specific modifiers to action score."""
        # This would be expanded based on specific profession logic
        return base_score

    def _get_character_action_threshold(self, character_data: Dict[str, Any]) -> float:
        """Get the action threshold for this character."""
        # More decisive characters have lower thresholds
        decisiveness = (
            character_data.get("psychological", {})
            .get("traits", {})
            .get("decisive", 0.5)
        )
        return 0.6 - (decisiveness * 0.2)  # Range: 0.4 to 0.6

    def _generate_action_reasoning(self, action: Dict[str, Any], score: float) -> str:
        """Generate reasoning for the selected action."""
        action_type = action.get("type", "unknown")
        return f"Selected {action_type} with confidence {score:.2f} based on current situation assessment."

    def _determine_action_priority(
        self, action: Dict[str, Any], score: float
    ) -> ActionPriority:
        """Determine action priority based on action and score."""
        if score > 0.8:
            return ActionPriority.CRITICAL
        elif score > 0.6:
            return ActionPriority.HIGH
        elif score > 0.4:
            return ActionPriority.MEDIUM
        else:
            return ActionPriority.LOW
