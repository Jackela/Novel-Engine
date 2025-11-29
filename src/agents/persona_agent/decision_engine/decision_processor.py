"""
Decision Processor
==================

Core decision-making engine for PersonaAgent character behavior.
Evaluates world state, character context, and personality traits to generate appropriate actions.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..protocols import (
    ThreatLevel,
    WorldEvent,
)

# Module-level LLM service instance (lazy loaded)
_llm_service_instance: Optional[Any] = None


def _get_llm_service() -> Any:
    """Get or create the LLM service singleton."""
    global _llm_service_instance
    if _llm_service_instance is None:
        from src.llm_service import UnifiedLLMService
        _llm_service_instance = UnifiedLLMService()
    return _llm_service_instance


async def _call_llm_for_score(prompt: str, requester: str) -> Optional[float]:
    """Call LLM to get a score. Returns None on failure."""
    try:
        from src.llm_service import LLMProvider, LLMRequest, ResponseFormat

        llm_service = _get_llm_service()
        if LLMProvider.GEMINI not in llm_service.providers:
            return None

        request = LLMRequest(
            prompt=prompt,
            provider=LLMProvider.GEMINI,
            response_format=ResponseFormat.ACTION_FORMAT,
            temperature=0.3,  # Lower for more consistent scoring
            max_tokens=200,
            cache_enabled=True,
            requester=requester,
        )

        response = await llm_service.generate(request)
        if "[LLM Error:" in response.content:
            return None

        # Extract numeric score from response
        score_match = re.search(r"SCORE:\s*([\d.]+)", response.content, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        return None
    except Exception as e:
        logging.getLogger(__name__).debug(f"LLM scoring failed: {e}")
        return None

# Import shared types with fallback
try:
    from shared_types import ActionPriority, CharacterAction
except ImportError:
    CharacterAction = Dict
    ActionPriority = str


class ActionCategory(Enum):
    """Categories of actions a character can take."""

    COMBAT = "combat"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    RESOURCE = "resource"
    SURVIVAL = "survival"
    TACTICAL = "tactical"
    DIPLOMATIC = "diplomatic"


@dataclass
class DecisionContext:
    """Context information for decision making."""

    world_state: Dict[str, Any]
    character_state: Dict[str, Any]
    recent_events: List[WorldEvent]
    active_goals: List[Dict[str, Any]]
    threat_level: ThreatLevel
    available_actions: List[str]
    time_pressure: float = 0.5  # 0.0 (no pressure) to 1.0 (extreme pressure)
    resource_constraints: Dict[str, float] = None

    def __post_init__(self):
        if self.resource_constraints is None:
            self.resource_constraints = {}


class DecisionProcessor:
    """
    Core decision processing engine for PersonaAgent.

    Responsibilities:
    - Evaluate world state and character context
    - Generate appropriate character actions
    - Consider personality traits and decision weights
    - Handle goal prioritization and action selection
    - Process threat assessments and defensive responses
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        # Decision-making weights (can be overridden by character data)
        self._default_decision_weights = {
            "self_preservation": 0.8,
            "faction_loyalty": 0.6,
            "personal_relationships": 0.5,
            "mission_success": 0.7,
            "moral_principles": 0.4,
            "resource_acquisition": 0.3,
            "knowledge_seeking": 0.5,
            "status_advancement": 0.4,
        }

        # Action evaluation cache
        self._action_cache = {}

        # Decision history for learning
        self._decision_history: List[Dict[str, Any]] = []

    async def make_decision(
        self, world_state: Dict[str, Any], character_context: Dict[str, Any]
    ) -> CharacterAction:
        """
        Make a decision based on current world state and character context.

        Args:
            world_state: Current state of the world
            character_context: Character-specific context and data

        Returns:
            CharacterAction: The selected action for the character
        """
        try:
            # Build decision context
            decision_context = await self._build_decision_context(
                world_state, character_context
            )

            # Evaluate all possible actions
            action_evaluations = await self._evaluate_all_actions(
                decision_context, character_context
            )

            # Select best action based on evaluations
            selected_action = await self._select_optimal_action(
                action_evaluations, decision_context
            )

            # Record decision for learning
            await self._record_decision(
                selected_action, decision_context, character_context
            )

            self.logger.info(
                f"Decision made: {selected_action.get('action_type', 'unknown')}"
            )
            return selected_action

        except Exception as e:
            self.logger.error(f"Decision making failed: {e}")
            # Return safe fallback action
            return await self._get_fallback_action(character_context)

    async def evaluate_threat(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> ThreatLevel:
        """
        Evaluate threat level of an event based on character perspective.

        Args:
            event: World event to evaluate
            character_data: Character's data and traits

        Returns:
            ThreatLevel: Assessment of threat level
        """
        try:
            threat_factors = await self._analyze_threat_factors(event, character_data)
            threat_level = await self._calculate_threat_level(threat_factors)

            self.logger.debug(
                f"Threat evaluation for event {event.event_id}: {threat_level}"
            )
            return threat_level

        except Exception as e:
            self.logger.error(f"Threat evaluation failed: {e}")
            return ThreatLevel.MODERATE  # Safe default

    async def prioritize_goals(
        self, goals: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize character goals based on current context.

        Args:
            goals: List of character goals
            context: Current context information

        Returns:
            List of goals sorted by priority
        """
        try:
            # Score each goal based on context
            scored_goals = []
            for goal in goals:
                score = await self._score_goal_priority(goal, context)
                scored_goals.append((goal, score))

            # Sort by score (highest first)
            scored_goals.sort(key=lambda x: x[1], reverse=True)

            # Return prioritized goals
            prioritized_goals = [goal for goal, score in scored_goals]

            self.logger.debug(f"Goals prioritized: {len(prioritized_goals)} goals")
            return prioritized_goals

        except Exception as e:
            self.logger.error(f"Goal prioritization failed: {e}")
            return goals  # Return original order on error

    async def _build_decision_context(
        self, world_state: Dict[str, Any], character_context: Dict[str, Any]
    ) -> DecisionContext:
        """Build comprehensive decision context."""
        try:
            # Extract relevant information
            character_state = character_context.get("state", {})
            recent_events = character_context.get("recent_events", [])
            active_goals = character_context.get("goals", [])
            available_actions = character_context.get("available_actions", [])

            # Assess overall threat level
            threat_level = await self._assess_overall_threat(
                world_state, recent_events, character_context
            )

            # Determine time pressure
            time_pressure = await self._calculate_time_pressure(
                world_state, character_state
            )

            # Extract resource constraints
            resource_constraints = character_state.get("resources", {})

            return DecisionContext(
                world_state=world_state,
                character_state=character_state,
                recent_events=recent_events,
                active_goals=active_goals,
                threat_level=threat_level,
                available_actions=available_actions,
                time_pressure=time_pressure,
                resource_constraints=resource_constraints,
            )

        except Exception as e:
            self.logger.error(f"Failed to build decision context: {e}")
            raise

    async def _evaluate_all_actions(
        self, context: DecisionContext, character_context: Dict[str, Any]
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Evaluate all available actions and return with scores."""
        try:
            evaluations = []
            decision_weights = character_context.get(
                "decision_weights", self._default_decision_weights
            )

            for action_type in context.available_actions:
                # Generate action details
                action = await self._generate_action_details(action_type, context)

                # Score the action
                score = await self._score_action(action, context, decision_weights)

                evaluations.append((action, score))

            # Sort by score for easier processing
            evaluations.sort(key=lambda x: x[1], reverse=True)

            return evaluations

        except Exception as e:
            self.logger.error(f"Action evaluation failed: {e}")
            return []

    async def _score_action(
        self,
        action: Dict[str, Any],
        context: DecisionContext,
        weights: Dict[str, float],
    ) -> float:
        """Score an action based on character weights and context."""
        try:
            base_score = 0.0

            # Factor in different decision criteria
            criteria_scores = {
                "self_preservation": await self._score_self_preservation(
                    action, context
                ),
                "faction_loyalty": await self._score_faction_loyalty(action, context),
                "personal_relationships": await self._score_personal_relationships(
                    action, context
                ),
                "mission_success": await self._score_mission_success(action, context),
                "moral_principles": await self._score_moral_principles(action, context),
                "resource_acquisition": await self._score_resource_acquisition(
                    action, context
                ),
                "knowledge_seeking": await self._score_knowledge_seeking(
                    action, context
                ),
                "status_advancement": await self._score_status_advancement(
                    action, context
                ),
            }

            # Calculate weighted score
            for criterion, score in criteria_scores.items():
                weight = weights.get(criterion, 0.5)
                base_score += score * weight

            # Apply threat level modifier
            threat_modifier = await self._get_threat_modifier(context.threat_level)
            final_score = base_score * threat_modifier

            # Apply time pressure modifier
            time_modifier = await self._get_time_pressure_modifier(
                context.time_pressure, action
            )
            final_score *= time_modifier

            return max(0.0, min(1.0, final_score))  # Clamp to [0, 1]

        except Exception as e:
            self.logger.error(f"Action scoring failed: {e}")
            return 0.5  # Neutral score on error

    async def _select_optimal_action(
        self, evaluations: List[Tuple[Dict[str, Any], float]], context: DecisionContext
    ) -> CharacterAction:
        """Select the optimal action from evaluations."""
        try:
            if not evaluations:
                return await self._get_fallback_action()

            # Get top candidates
            best_action, best_score = evaluations[0]

            # Add some randomness to prevent predictable behavior
            # Consider top 3 actions if they're close in score
            candidates = [best_action]
            for action, score in evaluations[1:3]:
                if score >= best_score * 0.85:  # Within 15% of best score
                    candidates.append(action)

            # Select from candidates with weighted randomness
            import random

            selected_action = random.choice(candidates)

            # Enhance action with additional context
            enhanced_action = await self._enhance_action_details(
                selected_action, context
            )

            return enhanced_action

        except Exception as e:
            self.logger.error(f"Action selection failed: {e}")
            return await self._get_fallback_action()

    async def _generate_action_details(
        self, action_type: str, context: DecisionContext
    ) -> Dict[str, Any]:
        """Generate detailed action structure from action type."""
        try:
            action = {
                "action_type": action_type,
                "priority": "medium",
                "category": await self._determine_action_category(action_type),
                "target": None,
                "parameters": {},
                "estimated_duration": 1.0,
                "resource_cost": {},
                "risks": [],
                "expected_outcomes": [],
            }

            # Add specific details based on action type
            if action_type == "attack":
                action["category"] = ActionCategory.COMBAT.value
                action["priority"] = "high"
                action["risks"] = ["injury", "death", "reputation_loss"]
                action["resource_cost"] = {"stamina": 0.3, "ammo": 0.1}

            elif action_type == "defend":
                action["category"] = ActionCategory.SURVIVAL.value
                action["priority"] = "high"
                action["resource_cost"] = {"stamina": 0.2}

            elif action_type == "negotiate":
                action["category"] = ActionCategory.DIPLOMATIC.value
                action["priority"] = "medium"
                action["resource_cost"] = {"influence": 0.1}

            elif action_type == "retreat":
                action["category"] = ActionCategory.SURVIVAL.value
                action["priority"] = "high"
                action["resource_cost"] = {"morale": 0.2}

            elif action_type == "explore":
                action["category"] = ActionCategory.EXPLORATION.value
                action["priority"] = "low"
                action["resource_cost"] = {"stamina": 0.4, "supplies": 0.1}
                action["expected_outcomes"] = ["discovery", "knowledge_gain"]

            elif action_type == "gather_intelligence":
                action["category"] = ActionCategory.TACTICAL.value
                action["priority"] = "medium"
                action["resource_cost"] = {"time": 0.3}
                action["expected_outcomes"] = ["information", "strategic_advantage"]

            return action

        except Exception as e:
            self.logger.error(f"Action detail generation failed: {e}")
            return {"action_type": action_type, "priority": "medium"}

    async def _score_self_preservation(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score action based on self-preservation concerns."""
        try:
            base_score = 0.5

            # High-risk actions score lower
            risks = action.get("risks", [])
            if "death" in risks:
                base_score -= 0.4
            elif "injury" in risks:
                base_score -= 0.2

            # Defensive actions score higher in dangerous situations
            if context.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                if action["action_type"] in ["defend", "retreat", "hide"]:
                    base_score += 0.3

            return max(0.0, min(1.0, base_score))

        except Exception as e:
            self.logger.debug(f"Self-preservation scoring failed: {e}")
            return 0.5

    async def _score_faction_loyalty(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score action based on faction loyalty."""
        try:
            base_score = 0.5

            # Actions that support faction goals score higher
            if action["action_type"] in [
                "defend_allies",
                "attack_enemies",
                "gather_intelligence",
            ]:
                base_score += 0.2

            # Actions that harm faction interests score lower
            if action["action_type"] in ["betray", "desert", "negotiate_with_enemies"]:
                base_score -= 0.3

            return max(0.0, min(1.0, base_score))

        except Exception as e:
            self.logger.debug(f"Faction loyalty scoring failed: {e}")
            return 0.5

    async def _score_mission_success(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score action based on mission success potential."""
        try:
            base_score = 0.5

            # Check if action aligns with active goals
            for goal in context.active_goals:
                if self._action_supports_goal(action, goal):
                    base_score += 0.2
                    break

            return max(0.0, min(1.0, base_score))

        except Exception as e:
            self.logger.debug(f"Mission success scoring failed: {e}")
            return 0.5

    def _action_supports_goal(
        self, action: Dict[str, Any], goal: Dict[str, Any]
    ) -> bool:
        """Check if an action supports achieving a goal."""
        goal_type = goal.get("type", "").lower()
        action_type = action.get("action_type", "").lower()

        # Simple keyword matching for now
        if "combat" in goal_type and action_type in ["attack", "defend"]:
            return True
        if "explore" in goal_type and action_type == "explore":
            return True
        if "diplomacy" in goal_type and action_type == "negotiate":
            return True

        return False

    async def _enhance_action_details(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> Dict[str, Any]:
        """Enhance action with additional context and details."""
        try:
            enhanced_action = action.copy()

            # Add timing information
            enhanced_action["timestamp"] = datetime.now().timestamp()
            enhanced_action["turn_context"] = {
                "threat_level": context.threat_level.value,
                "time_pressure": context.time_pressure,
                "available_resources": context.resource_constraints,
            }

            # Add reasoning
            enhanced_action["reasoning"] = await self._generate_action_reasoning(
                action, context
            )

            return enhanced_action

        except Exception as e:
            self.logger.error(f"Action enhancement failed: {e}")
            return action

    async def _generate_action_reasoning(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> str:
        """Generate reasoning text for the selected action."""
        try:
            action_type = action.get("action_type", "unknown")
            threat_level = context.threat_level.value

            reasoning_templates = {
                "attack": f"Initiating combat action due to {threat_level} threat level",
                "defend": f"Taking defensive position given {threat_level} threat assessment",
                "retreat": f"Strategic withdrawal recommended due to {threat_level} threat",
                "negotiate": f"Attempting diplomatic solution despite {threat_level} threat level",
                "explore": f"Continuing exploration mission with {threat_level} threat awareness",
                "gather_intelligence": f"Information gathering prioritized given {threat_level} situation",
            }

            return reasoning_templates.get(
                action_type, f"Action {action_type} selected based on current context"
            )

        except Exception as e:
            self.logger.debug(f"Reasoning generation failed: {e}")
            return "Action selected based on available information"

    async def _get_fallback_action(
        self, character_context: Optional[Dict[str, Any]] = None
    ) -> CharacterAction:
        """Get safe fallback action when decision making fails."""
        return {
            "action_type": "wait",
            "priority": "low",
            "category": "survival",
            "parameters": {},
            "reasoning": "Fallback action: observing situation",
        }

    # Additional helper methods for scoring criteria

    async def _score_personal_relationships(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score based on personal relationship impacts using LLM analysis."""
        action_type = action.get("type", action.get("action_type", "unknown"))
        target = action.get("target", "none")

        # Get character relationship data
        relationships = context.character_state.get("relationships", {})
        rel_summary = ", ".join([
            f"{k}: {v.get('trust', 0.5):.1f} trust"
            for k, v in list(relationships.items())[:5]
        ]) if relationships else "No established relationships"

        prompt = f"""Analyze how this action affects personal relationships.

ACTION: {action_type}
TARGET: {target}
CURRENT RELATIONSHIPS: {rel_summary}

Rate how this action impacts relationships on a 0-1 scale:
- 0.0: Severely damages relationships
- 0.5: Neutral impact
- 1.0: Greatly strengthens relationships

Respond in format:
SCORE: [0.0-1.0]
REASON: [brief explanation]"""

        score = await _call_llm_for_score(prompt, "relationship_score")
        return score if score is not None else 0.5

    async def _score_moral_principles(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score based on moral principles using LLM ethical evaluation."""
        action_type = action.get("type", action.get("action_type", "unknown"))
        target = action.get("target", "none")

        # Get character moral traits
        traits = context.character_state.get("traits", {})
        moral_traits = {k: v for k, v in traits.items()
                       if k in ["honor", "compassion", "justice", "loyalty", "honesty"]}
        traits_str = ", ".join([f"{k}: {v}" for k, v in moral_traits.items()]) or "standard ethics"

        prompt = f"""Evaluate this action's alignment with moral principles.

ACTION: {action_type}
TARGET: {target}
CHARACTER MORAL TRAITS: {traits_str}

Rate moral alignment on a 0-1 scale:
- 0.0: Severely unethical, violates core principles
- 0.5: Morally neutral
- 1.0: Highly ethical, upholds principles

Respond in format:
SCORE: [0.0-1.0]
REASON: [brief explanation]"""

        score = await _call_llm_for_score(prompt, "moral_score")
        return score if score is not None else 0.5

    async def _score_resource_acquisition(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score based on resource acquisition potential (algorithmic)."""
        action_type = action.get("type", action.get("action_type", "")).lower()
        score = 0.5

        # Actions that typically acquire resources
        resource_actions = {
            "loot": 0.9, "gather": 0.85, "trade": 0.7, "scavenge": 0.8,
            "search": 0.6, "explore": 0.5, "steal": 0.75, "harvest": 0.8
        }

        if action_type in resource_actions:
            score = resource_actions[action_type]

        # Adjust based on current resource constraints
        constraints = context.resource_constraints or {}
        if constraints:
            # Higher score if we're low on resources
            avg_constraint = sum(constraints.values()) / len(constraints)
            if avg_constraint < 0.3:  # Resource scarcity
                score = min(1.0, score + 0.2)

        return score

    async def _score_knowledge_seeking(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score based on knowledge seeking value (algorithmic)."""
        action_type = action.get("type", action.get("action_type", "")).lower()
        score = 0.5

        # Actions that acquire knowledge
        knowledge_actions = {
            "investigate": 0.9, "research": 0.95, "observe": 0.7, "explore": 0.75,
            "interrogate": 0.6, "search": 0.6, "study": 0.9, "scout": 0.7,
            "communicate": 0.5, "negotiate": 0.4
        }

        if action_type in knowledge_actions:
            score = knowledge_actions[action_type]

        # Adjust based on character curiosity trait
        traits = context.character_state.get("traits", {})
        curiosity = traits.get("curiosity", traits.get("inquisitive", 0.5))
        if isinstance(curiosity, (int, float)):
            score = score * 0.7 + curiosity * 0.3

        return score

    async def _score_status_advancement(
        self, action: Dict[str, Any], context: DecisionContext
    ) -> float:
        """Score based on status advancement potential (algorithmic)."""
        action_type = action.get("type", action.get("action_type", "")).lower()
        score = 0.5

        # Actions that improve social status
        status_actions = {
            "negotiate": 0.8, "persuade": 0.75, "lead": 0.9, "command": 0.85,
            "ally": 0.7, "impress": 0.8, "challenge": 0.6, "defend": 0.6,
            "help": 0.5, "communicate": 0.4
        }

        if action_type in status_actions:
            score = status_actions[action_type]

        # Adjust based on character ambition
        traits = context.character_state.get("traits", {})
        ambition = traits.get("ambition", traits.get("leadership", 0.5))
        if isinstance(ambition, (int, float)):
            score = score * 0.6 + ambition * 0.4

        return score

    async def _analyze_threat_factors(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Analyze threat factors from an event using LLM."""
        event_type = getattr(event, "event_type", "unknown")
        event_desc = getattr(event, "description", str(event))
        affected = getattr(event, "affected_entities", [])
        character_id = character_data.get("id", "unknown")

        prompt = f"""Analyze threat factors from this event for a character.

EVENT TYPE: {event_type}
EVENT DESCRIPTION: {event_desc[:200]}
AFFECTED ENTITIES: {affected[:5]}
CHARACTER ID: {character_id}

Rate each threat factor from 0.0 (no threat) to 1.0 (maximum threat):
Respond in format:
SCORE: [base_threat 0.0-1.0]
PHYSICAL_DANGER: [0.0-1.0]
RESOURCE_RISK: [0.0-1.0]
SOCIAL_THREAT: [0.0-1.0]"""

        score = await _call_llm_for_score(prompt, "threat_factors")
        base_threat = score if score is not None else 0.5

        return {
            "base_threat": base_threat,
            "physical_danger": base_threat * 0.8,
            "resource_risk": base_threat * 0.5,
            "social_threat": base_threat * 0.3,
        }

    async def _calculate_threat_level(
        self, threat_factors: Dict[str, float]
    ) -> ThreatLevel:
        """Calculate overall threat level from factors."""
        base_threat = threat_factors.get("base_threat", 0.5)
        if base_threat < 0.2:
            return ThreatLevel.NEGLIGIBLE
        elif base_threat < 0.4:
            return ThreatLevel.LOW
        elif base_threat < 0.6:
            return ThreatLevel.MODERATE
        elif base_threat < 0.8:
            return ThreatLevel.HIGH
        else:
            return ThreatLevel.CRITICAL

    async def _score_goal_priority(
        self, goal: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """Score a goal's priority based on context."""
        base_priority = goal.get("priority", 0.5)
        # Add context-based adjustments
        return base_priority

    async def _assess_overall_threat(
        self,
        world_state: Dict[str, Any],
        recent_events: List[WorldEvent],
        character_context: Dict[str, Any],
    ) -> ThreatLevel:
        """Assess overall threat level from world state and events using LLM."""
        # Summarize recent events
        event_summary = []
        for event in recent_events[:5]:
            event_type = getattr(event, "event_type", "unknown")
            desc = getattr(event, "description", "")[:100]
            event_summary.append(f"- {event_type}: {desc}")
        events_str = "\n".join(event_summary) if event_summary else "No recent events"

        # Get world state context
        location = world_state.get("current_location", "unknown")
        hostiles = world_state.get("hostile_entities", [])

        prompt = f"""Assess overall threat level for a character.

LOCATION: {location}
HOSTILE ENTITIES NEARBY: {len(hostiles)} ({hostiles[:3] if hostiles else 'none'})
RECENT EVENTS:
{events_str}

Rate the threat level on a 0-1 scale:
- 0.0-0.2: Negligible threat
- 0.2-0.4: Low threat
- 0.4-0.6: Moderate threat
- 0.6-0.8: High threat
- 0.8-1.0: Critical threat

Respond in format:
SCORE: [0.0-1.0]
REASON: [brief explanation]"""

        score = await _call_llm_for_score(prompt, "overall_threat")
        if score is None:
            score = 0.5

        # Map score to ThreatLevel
        if score < 0.2:
            return ThreatLevel.NEGLIGIBLE
        elif score < 0.4:
            return ThreatLevel.LOW
        elif score < 0.6:
            return ThreatLevel.MODERATE
        elif score < 0.8:
            return ThreatLevel.HIGH
        else:
            return ThreatLevel.CRITICAL

    async def _calculate_time_pressure(
        self, world_state: Dict[str, Any], character_state: Dict[str, Any]
    ) -> float:
        """Calculate time pressure factor (algorithmic)."""
        pressure = 0.5  # Base pressure

        # Check for urgent events
        if world_state.get("combat_active", False):
            pressure += 0.3
        if world_state.get("timer_active", False):
            pressure += 0.2

        # Check character conditions
        health = character_state.get("health", 1.0)
        if health < 0.3:
            pressure += 0.2  # Low health = high urgency

        stamina = character_state.get("stamina", 1.0)
        if stamina < 0.2:
            pressure += 0.1

        # Check for pursuit/danger
        if world_state.get("being_pursued", False):
            pressure += 0.25

        # Check deadline proximity
        deadline = world_state.get("mission_deadline", None)
        if deadline:
            # Assume deadline is a timestamp or turn count
            pressure += 0.15

        return min(1.0, max(0.0, pressure))

    async def _determine_action_category(self, action_type: str) -> str:
        """Determine category for an action type."""
        category_mapping = {
            "attack": ActionCategory.COMBAT.value,
            "defend": ActionCategory.SURVIVAL.value,
            "negotiate": ActionCategory.DIPLOMATIC.value,
            "explore": ActionCategory.EXPLORATION.value,
            "retreat": ActionCategory.SURVIVAL.value,
        }
        return category_mapping.get(action_type, ActionCategory.TACTICAL.value)

    async def _get_threat_modifier(self, threat_level: ThreatLevel) -> float:
        """Get threat level modifier for action scoring."""
        modifiers = {
            ThreatLevel.NEGLIGIBLE: 1.0,
            ThreatLevel.LOW: 1.1,
            ThreatLevel.MODERATE: 1.2,
            ThreatLevel.HIGH: 1.5,
            ThreatLevel.CRITICAL: 2.0,
        }
        return modifiers.get(threat_level, 1.0)

    async def _get_time_pressure_modifier(
        self, time_pressure: float, action: Dict[str, Any]
    ) -> float:
        """Get time pressure modifier for action scoring."""
        # Quick actions get bonus under time pressure
        estimated_duration = action.get("estimated_duration", 1.0)
        if time_pressure > 0.7 and estimated_duration < 0.5:
            return 1.3
        elif time_pressure > 0.5 and estimated_duration > 2.0:
            return 0.8
        return 1.0

    async def _record_decision(
        self,
        action: CharacterAction,
        context: DecisionContext,
        character_context: Dict[str, Any],
    ) -> None:
        """Record decision for learning and analysis."""
        try:
            decision_record = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "threat_level": context.threat_level.value,
                "time_pressure": context.time_pressure,
                "character_id": character_context.get("agent_id", "unknown"),
            }

            self._decision_history.append(decision_record)

            # Keep history limited
            if len(self._decision_history) > 100:
                self._decision_history = self._decision_history[-50:]

        except Exception as e:
            self.logger.debug(f"Decision recording failed: {e}")

    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent decision history."""
        return self._decision_history[-limit:] if self._decision_history else []
