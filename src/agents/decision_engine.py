#!/usr/bin/env python3
"""
Decision Engine
===============

Core decision-making logic extracted from PersonaAgent.
Handles action selection, evaluation, and reasoning.

Part of Wave 6.2 PersonaAgent Decomposition Strategy.
"""

import logging
import random
import time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

# Import shared types  
from src.core.types.shared_types import CharacterAction, ActionPriority

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Enumeration for threat assessment levels used in character decision-making."""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SituationAssessment:
    """Assessment of current situation for decision making."""
    current_location: Optional[str]
    threat_level: ThreatLevel
    available_resources: Dict[str, Any]
    active_goals: List[Dict[str, Any]]
    social_obligations: List[Dict[str, Any]]
    environmental_factors: Dict[str, Any]
    mission_status: Dict[str, Any]


@dataclass
class ActionEvaluation:
    """Evaluation result for a potential action."""
    action: Dict[str, Any]
    base_score: float
    modified_score: float
    reasoning: str
    priority: ActionPriority


class DecisionEngine:
    """
    Core decision-making engine for PersonaAgent.
    
    Responsibilities:
    - Situation assessment and analysis
    - Action identification and evaluation
    - Decision scoring and selection
    - Reasoning generation
    """
    
    def __init__(self, core: 'PersonaCore', context_manager: 'CharacterContextManager'):
        """
        Initialize decision engine.
        
        Args:
            core: PersonaCore instance
            context_manager: Character context manager
        """
        self.core = core
        self.context_manager = context_manager
        self.logger = logging.getLogger(f"{__name__}.{core.agent_id}")
        
        # Decision-making configuration
        self.action_threshold = 0.3  # Minimum score for action consideration
        self.decision_weights = {}   # Will be loaded from character data
        
    def make_decision(self, world_state_update: Dict[str, Any]) -> Optional[CharacterAction]:
        """
        Make a decision based on current world state.
        
        Args:
            world_state_update: Current world state information
            
        Returns:
            Optional[CharacterAction]: Selected action or None if no suitable action
        """
        try:
            self.logger.debug(f"Making decision for agent {self.core.agent_id}")
            
            # Update decision weights from character data
            self._update_decision_weights()
            
            # Assess current situation
            situation = self._assess_current_situation(world_state_update)
            
            # Identify available actions
            available_actions = self._identify_available_actions(situation)
            
            if not available_actions:
                self.logger.debug("No available actions found")
                return None
            
            # Evaluate each action
            action_evaluations = []
            for action in available_actions:
                evaluation = self._evaluate_action(action, situation)
                if evaluation.modified_score >= self.action_threshold:
                    action_evaluations.append(evaluation)
            
            if not action_evaluations:
                self.logger.debug("No actions meet minimum threshold")
                return None
            
            # Select best action
            best_evaluation = self._select_best_action(action_evaluations)
            
            if best_evaluation:
                return self._create_character_action(best_evaluation)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Decision making failed: {e}")
            return None
    
    def _assess_current_situation(self, world_state_update: Dict[str, Any]) -> SituationAssessment:
        """
        Assess the current situation for decision making.
        
        Args:
            world_state_update: World state information
            
        Returns:
            SituationAssessment: Current situation analysis
        """
        # Extract location information
        current_location = world_state_update.get("current_location") or self.core.state.current_location
        
        # Assess threat level
        threat_level = self._assess_threat_level(world_state_update)
        
        # Assess available resources
        available_resources = self._assess_available_resources(world_state_update)
        
        # Get current goals
        active_goals = self._get_current_goals()
        
        # Assess social obligations
        social_obligations = self._assess_social_obligations(world_state_update)
        
        # Environmental factors
        environmental_factors = self._assess_environmental_factors(world_state_update)
        
        # Mission status
        mission_status = self._assess_mission_status(world_state_update)
        
        return SituationAssessment(
            current_location=current_location,
            threat_level=threat_level,
            available_resources=available_resources,
            active_goals=active_goals,
            social_obligations=social_obligations,
            environmental_factors=environmental_factors,
            mission_status=mission_status
        )
    
    def _identify_available_actions(self, situation: SituationAssessment) -> List[Dict[str, Any]]:
        """
        Identify actions available in the current situation.
        
        Args:
            situation: Current situation assessment
            
        Returns:
            List[Dict]: Available actions
        """
        available_actions = []
        
        # Basic actions always available
        basic_actions = [
            {
                "type": "observe",
                "description": "Observe surroundings and gather information",
                "requirements": [],
                "outcomes": ["knowledge_gain", "situational_awareness"]
            },
            {
                "type": "wait", 
                "description": "Wait and assess the situation",
                "requirements": [],
                "outcomes": ["time_passage", "patience"]
            }
        ]
        available_actions.extend(basic_actions)
        
        # Location-based actions
        if situation.current_location:
            location_actions = self._get_location_actions(situation.current_location)
            available_actions.extend(location_actions)
        
        # Goal-based actions
        for goal in situation.active_goals:
            goal_actions = self._get_goal_actions(goal, situation)
            available_actions.extend(goal_actions)
        
        # Profession-based actions
        profession_actions = self._get_profession_actions()
        available_actions.extend(profession_actions)
        
        # Social actions
        social_actions = self._get_social_actions(situation)
        available_actions.extend(social_actions)
        
        # Remove duplicates based on action type
        unique_actions = {}
        for action in available_actions:
            action_key = action.get("type", "unknown")
            if action_key not in unique_actions:
                unique_actions[action_key] = action
        
        return list(unique_actions.values())
    
    def _evaluate_action(self, action: Dict[str, Any], situation: SituationAssessment) -> ActionEvaluation:
        """
        Evaluate a potential action.
        
        Args:
            action: Action to evaluate
            situation: Current situation
            
        Returns:
            ActionEvaluation: Action evaluation result
        """
        # Calculate base score
        base_score = self._calculate_base_score(action, situation)
        
        # Apply personality modifiers
        modified_score = self._apply_personality_modifiers(base_score, action)
        
        # Apply situational modifiers
        modified_score = self._apply_situational_modifiers(modified_score, action, situation)
        
        # Generate reasoning
        reasoning = self._generate_action_reasoning(action, base_score, modified_score)
        
        # Determine priority
        priority = self._determine_action_priority(action, modified_score)
        
        return ActionEvaluation(
            action=action,
            base_score=base_score,
            modified_score=modified_score,
            reasoning=reasoning,
            priority=priority
        )
    
    def _calculate_base_score(self, action: Dict[str, Any], situation: SituationAssessment) -> float:
        """Calculate base score for an action."""
        base_score = 0.5  # Neutral base
        
        action_type = action.get("type", "")
        
        # Score based on current goals alignment
        for goal in situation.active_goals:
            goal_type = goal.get("type", "")
            if action_type in goal.get("related_actions", []):
                base_score += 0.3
        
        # Score based on threat level
        if situation.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            if action_type in ["combat", "escape", "hide", "defend"]:
                base_score += 0.4
        
        # Score based on social obligations
        for obligation in situation.social_obligations:
            if action_type in obligation.get("required_actions", []):
                base_score += 0.2
        
        return min(1.0, max(0.0, base_score))
    
    def _apply_personality_modifiers(self, base_score: float, action: Dict[str, Any]) -> float:
        """Apply personality-based modifiers to action score."""
        modified_score = base_score
        
        # Get personality traits
        personality = self.core.character_data.get("psychological", {}).get("personality_traits", {})
        action_type = action.get("type", "")
        
        # Apply trait modifiers
        trait_modifiers = {
            "aggressive": {"combat": 0.3, "intimidate": 0.2, "wait": -0.2},
            "cautious": {"observe": 0.3, "wait": 0.2, "combat": -0.3},
            "loyal": {"help_ally": 0.4, "betray": -0.5},
            "pragmatic": {"efficient": 0.2, "idealistic": -0.2},
            "social": {"communicate": 0.3, "negotiate": 0.2, "isolate": -0.2}
        }
        
        for trait, strength in personality.items():
            if trait in trait_modifiers and action_type in trait_modifiers[trait]:
                modifier = trait_modifiers[trait][action_type] * strength
                modified_score += modifier
        
        return min(1.0, max(0.0, modified_score))
    
    def _apply_situational_modifiers(self, base_score: float, action: Dict[str, Any], situation: SituationAssessment) -> float:
        """Apply situation-specific modifiers."""
        modified_score = base_score
        action_type = action.get("type", "")
        
        # Threat-based modifiers
        if situation.threat_level == ThreatLevel.CRITICAL:
            if action_type in ["combat", "escape"]:
                modified_score += 0.3
            elif action_type in ["wait", "observe"]:
                modified_score -= 0.2
        
        # Resource-based modifiers
        if "combat" in action_type:
            combat_resources = situation.available_resources.get("combat_capability", 0.0)
            if combat_resources < 0.3:
                modified_score -= 0.4  # Poor combat capability
        
        # Location-based modifiers
        if situation.current_location:
            location_modifiers = self._get_location_modifiers(situation.current_location, action_type)
            modified_score += location_modifiers
        
        return min(1.0, max(0.0, modified_score))
    
    def _select_best_action(self, evaluations: List[ActionEvaluation]) -> Optional[ActionEvaluation]:
        """Select the best action from evaluations."""
        if not evaluations:
            return None
        
        # Sort by modified score (descending)
        evaluations.sort(key=lambda e: e.modified_score, reverse=True)
        
        # Add some randomness to prevent predictable behavior
        top_actions = [e for e in evaluations[:3] if e.modified_score >= evaluations[0].modified_score * 0.8]
        
        if len(top_actions) > 1:
            # Weighted random selection from top actions
            weights = [e.modified_score for e in top_actions]
            selected = random.choices(top_actions, weights=weights)[0]
        else:
            selected = top_actions[0]
        
        return selected
    
    def _create_character_action(self, evaluation: ActionEvaluation) -> CharacterAction:
        """Create CharacterAction from evaluation."""
        return CharacterAction(
            action_type=evaluation.action["type"],
            target=evaluation.action.get("target"),
            priority=evaluation.priority,
            reasoning=evaluation.reasoning,
            parameters=evaluation.action.get("parameters", {})
        )
    
    # Helper methods for action identification
    
    def _get_location_actions(self, location: str) -> List[Dict[str, Any]]:
        """Get actions specific to current location."""
        # This would be enhanced with actual location data
        return [
            {
                "type": "explore",
                "description": f"Explore {location}",
                "requirements": [],
                "outcomes": ["discovery", "knowledge_gain"]
            }
        ]
    
    def _get_goal_actions(self, goal: Dict[str, Any], situation: SituationAssessment) -> List[Dict[str, Any]]:
        """Get actions related to a specific goal."""
        goal_type = goal.get("type", "")
        
        goal_action_map = {
            "combat": [{"type": "combat", "description": "Engage in combat"}],
            "investigation": [{"type": "investigate", "description": "Investigate something"}],
            "social": [{"type": "communicate", "description": "Communicate with others"}]
        }
        
        return goal_action_map.get(goal_type, [])
    
    def _get_profession_actions(self) -> List[Dict[str, Any]]:
        """Get profession-specific actions."""
        profession = self.core.character_data.get("identity", {}).get("profession", "")
        
        profession_actions = {
            "warrior": [{"type": "combat", "description": "Use combat skills"}],
            "scholar": [{"type": "research", "description": "Research information"}],
            "diplomat": [{"type": "negotiate", "description": "Negotiate agreements"}]
        }
        
        return profession_actions.get(profession.lower(), [])
    
    def _get_social_actions(self, situation: SituationAssessment) -> List[Dict[str, Any]]:
        """Get social interaction actions."""
        return [
            {
                "type": "communicate",
                "description": "Communicate with nearby entities",
                "requirements": [],
                "outcomes": ["information_exchange", "relationship_change"]
            }
        ]
    
    # Helper methods for situation assessment
    
    def _assess_threat_level(self, world_state: Dict[str, Any]) -> ThreatLevel:
        """Assess current threat level."""
        # This would analyze world state for threats
        threat_indicators = world_state.get("threat_indicators", [])
        
        if len(threat_indicators) >= 3:
            return ThreatLevel.CRITICAL
        elif len(threat_indicators) >= 2:
            return ThreatLevel.HIGH
        elif len(threat_indicators) >= 1:
            return ThreatLevel.MODERATE
        else:
            return ThreatLevel.LOW
    
    def _assess_available_resources(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess available resources."""
        return {
            "combat_capability": 0.7,  # Would be calculated from character stats
            "social_influence": 0.5,
            "knowledge_base": 0.6,
            "equipment": world_state.get("available_equipment", [])
        }
    
    def _get_current_goals(self) -> List[Dict[str, Any]]:
        """Get character's current goals."""
        # This would be enhanced with actual goal tracking
        return [
            {
                "type": "survival",
                "priority": "high",
                "related_actions": ["observe", "hide", "escape"]
            }
        ]
    
    def _assess_social_obligations(self, world_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess current social obligations."""
        return []  # Would be enhanced with relationship tracking
    
    def _assess_environmental_factors(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess environmental factors."""
        return world_state.get("environmental_factors", {})
    
    def _assess_mission_status(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess mission status."""
        return world_state.get("mission_status", {})
    
    def _get_location_modifiers(self, location: str, action_type: str) -> float:
        """Get location-based action modifiers."""
        return 0.0  # Would be enhanced with location data
    
    def _generate_action_reasoning(self, action: Dict[str, Any], base_score: float, modified_score: float) -> str:
        """Generate reasoning for action selection."""
        return f"Selected {action['type']}: base score {base_score:.2f}, final score {modified_score:.2f}"
    
    def _determine_action_priority(self, action: Dict[str, Any], score: float) -> ActionPriority:
        """Determine action priority based on score."""
        if score >= 0.8:
            return ActionPriority.HIGH
        elif score >= 0.6:
            return ActionPriority.NORMAL
        else:
            return ActionPriority.LOW
    
    def _update_decision_weights(self) -> None:
        """Update decision weights from character data."""
        behavioral_data = self.core.character_data.get("behavioral", {})
        self.decision_weights = behavioral_data.get("decision_weights", {})