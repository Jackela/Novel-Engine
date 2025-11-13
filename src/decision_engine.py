#!/usr/bin/env python3
"""
Decision Engine
===============

Handles agent decision-making logic including:
- Core decision-making processes
- Situation assessment and analysis
- Action evaluation and selection
- LLM integration for enhanced decisions

This component manages the cognitive processes that drive agent behavior
while maintaining separation from character data and memory management.
"""

import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Import shared types
try:
    from src.core.types.shared_types import ActionPriority, CharacterAction
except ImportError:
    # Fallback for basic functionality
    CharacterAction = dict

    class ActionPriority:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"


# Import LLM integration
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Handles agent decision-making processes and action selection.

    Responsibilities:
    - Core decision-making logic and flow
    - Situation assessment and threat analysis
    - Action option evaluation and ranking
    - LLM integration for enhanced decision-making
    - Action selection based on character priorities
    """

    def __init__(self, agent_core: Any):
        """
        Initialize the DecisionEngine.

        Args:
            agent_core: Reference to the PersonaAgentCore instance
        """
        self.agent_core = agent_core
        self.last_action_taken = None
        self.decision_history: List[Dict[str, Any]] = []

        # LLM integration setup
        self.llm_available = LLM_AVAILABLE
        self._setup_llm_session()

        logger.info(f"DecisionEngine initialized for agent {self.agent_core.agent_id}")

    def _setup_llm_session(self) -> None:
        """Set up LLM session with retry strategy if available."""
        if not self.llm_available:
            logger.info(
                "LLM integration not available - using algorithmic decision-making only"
            )
            return

        try:
            # Set up requests session with retry strategy for LLM calls
            self.llm_session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.llm_session.mount("http://", adapter)
            self.llm_session.mount("https://", adapter)

            logger.info("LLM session configured with retry strategy")
        except Exception as e:
            logger.warning(f"Failed to setup LLM session: {e}")
            self.llm_available = False

    def make_decision(
        self, world_state_update: Dict[str, Any]
    ) -> Optional[CharacterAction]:
        """
        Core decision-making logic that processes world state and returns character action.

        This method orchestrates the complete decision-making process:
        1. Situational assessment and threat analysis
        2. Available action identification
        3. LLM-enhanced decision-making (if available)
        4. Fallback algorithmic decision-making
        5. Action selection and validation

        Args:
            world_state_update: Current world state information

        Returns:
            CharacterAction object or None if character chooses to wait
        """
        try:
            agent_id = self.agent_core.agent_id
            logger.info(f"Agent {agent_id} processing decision-making cycle")

            # Step 1: Update understanding of world state
            self._process_world_state_update(world_state_update)

            # Step 2: Assess current situation and identify options
            situation_assessment = self._assess_current_situation()
            available_actions = self._identify_available_actions(situation_assessment)

            # Step 3: Attempt LLM-enhanced decision-making
            if self.llm_available:
                try:
                    llm_action = self._llm_enhanced_decision_making(
                        world_state_update, situation_assessment, available_actions
                    )
                    if llm_action:
                        self._record_decision(llm_action, "llm_enhanced")
                        return llm_action
                except Exception as llm_error:
                    logger.warning(
                        f"LLM decision-making failed for {agent_id}: {str(llm_error)}"
                    )

            # Step 4: Fallback to algorithmic decision-making
            logger.info(f"Agent {agent_id} using algorithmic decision-making")

            # Evaluate each available action
            action_evaluations = []
            for action in available_actions:
                evaluation_score = self._evaluate_action_option(
                    action, situation_assessment
                )
                action_evaluations.append((action, evaluation_score))

            # Select best action based on character priorities
            selected_action = self._select_best_action(action_evaluations)

            # Record and return decision
            self._record_decision(selected_action, "algorithmic")
            return selected_action

        except Exception as e:
            logger.error(
                f"Error in decision-making for agent {self.agent_core.agent_id}: {str(e)}"
            )
            return None

    def _process_world_state_update(self, world_state_update: Dict[str, Any]) -> None:
        """
        Process incoming world state information through character's subjective lens.

        Args:
            world_state_update: World state information to process
        """
        try:
            # Extract relevant information for this character
            location_info = world_state_update.get("location_updates", {})
            world_state_update.get("entity_updates", {})
            faction_info = world_state_update.get("faction_updates", {})
            events = world_state_update.get("recent_events", [])

            # Process narrative context if available
            narrative_context = world_state_update.get("narrative_context", {})
            if narrative_context:
                self._process_narrative_situation_update(narrative_context)

            # Update character's subjective worldview
            if location_info:
                self.agent_core.add_to_subjective_worldview(
                    "location_knowledge", "current_area", location_info
                )

            if faction_info:
                for faction, status in faction_info.items():
                    self.agent_core.add_to_subjective_worldview(
                        "faction_relationships", faction, status
                    )

            # Process events for memory and relationship updates
            for event in events[-3:]:  # Process last 3 events
                self._process_event_for_relationships(event)

            logger.debug(
                f"Agent {self.agent_core.agent_id} processed world state update"
            )

        except Exception as e:
            logger.error(f"Error processing world state update: {str(e)}")

    def _assess_current_situation(self) -> Dict[str, Any]:
        """
        Assess the current situation from the character's perspective.

        Returns:
            Dictionary containing situation assessment
        """
        try:
            situation = {
                "threat_level": self._assess_threat_level(),
                "opportunity_level": self._assess_opportunity_level(),
                "resource_status": self._assess_resource_status(),
                "social_context": self._assess_social_context(),
                "narrative_urgency": self._assess_narrative_urgency(),
                "character_state": {
                    "morale": self.agent_core.morale_level,
                    "status": self.agent_core.current_status,
                    "location": self.agent_core.current_location,
                },
            }

            logger.debug(
                f"Agent {self.agent_core.agent_id} situation assessment: threat={situation['threat_level']}, opportunity={situation['opportunity_level']}"
            )

            return situation

        except Exception as e:
            logger.error(f"Error assessing situation: {str(e)}")
            return {
                "threat_level": "unknown",
                "opportunity_level": "unknown",
                "resource_status": "unknown",
                "social_context": {},
                "narrative_urgency": "low",
                "character_state": {},
            }

    def _assess_threat_level(self) -> str:
        """Assess current threat level from character's perspective."""
        try:
            active_threats = self.agent_core.subjective_worldview.get(
                "active_threats", {}
            )
            threat_count = len(active_threats)

            if threat_count == 0:
                return "low"
            elif threat_count <= 2:
                return "moderate"
            else:
                return "high"

        except Exception:
            return "unknown"

    def _assess_opportunity_level(self) -> str:
        """Assess current opportunity level from character's perspective."""
        try:
            current_goals = self.agent_core.subjective_worldview.get(
                "current_goals", []
            )
            known_entities = self.agent_core.subjective_worldview.get(
                "known_entities", {}
            )

            # Simple heuristic: opportunities based on goals and known entities
            opportunity_score = len(current_goals) + len(known_entities) * 0.1

            if opportunity_score < 1:
                return "low"
            elif opportunity_score <= 3:
                return "moderate"
            else:
                return "high"

        except Exception:
            return "unknown"

    def _assess_resource_status(self) -> str:
        """Assess current resource status from character's perspective."""
        # Simplified resource assessment based on morale and status
        if (
            self.agent_core.morale_level > 0.5
            and self.agent_core.current_status == "active"
        ):
            return "good"
        elif (
            self.agent_core.morale_level > 0
            and self.agent_core.current_status == "active"
        ):
            return "adequate"
        else:
            return "poor"

    def _assess_social_context(self) -> Dict[str, Any]:
        """Assess social context and relationships."""
        try:
            positive_relationships = sum(
                1 for strength in self.agent_core.relationships.values() if strength > 0
            )
            negative_relationships = sum(
                1 for strength in self.agent_core.relationships.values() if strength < 0
            )

            return {
                "allies_present": positive_relationships,
                "enemies_present": negative_relationships,
                "social_standing": "neutral",  # Could be expanded
            }
        except Exception:
            return {
                "allies_present": 0,
                "enemies_present": 0,
                "social_standing": "unknown",
            }

    def _assess_narrative_urgency(self) -> str:
        """Assess narrative urgency based on recent events."""
        try:
            recent_events = self.agent_core.subjective_worldview.get(
                "recent_events", []
            )
            if len(recent_events) > 5:
                return "high"
            elif len(recent_events) > 2:
                return "moderate"
            else:
                return "low"
        except Exception:
            return "low"

    def _identify_available_actions(
        self, situation_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify available actions based on situation assessment.

        Args:
            situation_assessment: Current situation analysis

        Returns:
            List of available action dictionaries
        """
        try:
            actions = []

            # Basic actions always available
            actions.extend(
                [
                    {"action_type": "observe", "priority": "low", "risk": "none"},
                    {"action_type": "investigate", "priority": "medium", "risk": "low"},
                    {"action_type": "communicate", "priority": "medium", "risk": "low"},
                ]
            )

            # Context-dependent actions
            threat_level = situation_assessment.get("threat_level", "unknown")

            if threat_level in ["moderate", "high"]:
                actions.extend(
                    [
                        {
                            "action_type": "defensive_action",
                            "priority": "high",
                            "risk": "medium",
                        },
                        {"action_type": "retreat", "priority": "medium", "risk": "low"},
                    ]
                )

            opportunity_level = situation_assessment.get("opportunity_level", "unknown")
            if opportunity_level in ["moderate", "high"]:
                actions.extend(
                    [
                        {
                            "action_type": "advance",
                            "priority": "medium",
                            "risk": "medium",
                        },
                        {
                            "action_type": "exploit_opportunity",
                            "priority": "high",
                            "risk": "high",
                        },
                    ]
                )

            # Social actions if allies present
            social_context = situation_assessment.get("social_context", {})
            if social_context.get("allies_present", 0) > 0:
                actions.append(
                    {"action_type": "coordinate", "priority": "medium", "risk": "low"}
                )

            return actions

        except Exception as e:
            logger.error(f"Error identifying available actions: {str(e)}")
            return [{"action_type": "observe", "priority": "low", "risk": "none"}]

    def _evaluate_action_option(
        self, action: Dict[str, Any], situation: Dict[str, Any]
    ) -> float:
        """
        Evaluate an action option based on character priorities and situation.

        Args:
            action: Action dictionary to evaluate
            situation: Current situation assessment

        Returns:
            float: Evaluation score (higher is better)
        """
        try:
            score = 0.0

            # Base score from action priority
            priority_scores = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
            score += priority_scores.get(action.get("priority", "low"), 0.2)

            # Adjust for risk tolerance based on character state
            risk_penalty = {"none": 0.0, "low": 0.1, "medium": 0.3, "high": 0.5}
            risk = action.get("risk", "none")

            # Characters with low morale are more risk-averse
            risk_multiplier = 1.0 + (1.0 - self.agent_core.morale_level) * 0.5
            score -= risk_penalty.get(risk, 0.0) * risk_multiplier

            # Apply character decision weights
            action_type = action.get("action_type", "")
            if action_type in ["retreat", "defensive_action"]:
                score *= self.agent_core.decision_weights.get("self_preservation", 0.5)
            elif action_type in ["communicate", "coordinate"]:
                score *= self.agent_core.decision_weights.get(
                    "personal_relationships", 0.6
                )
            elif action_type in ["advance", "exploit_opportunity"]:
                score *= self.agent_core.decision_weights.get("mission_success", 0.8)

            # Situation-based modifiers
            threat_level = situation.get("threat_level", "unknown")
            if threat_level == "high" and action_type in [
                "retreat",
                "defensive_action",
            ]:
                score *= 1.5  # Boost defensive actions in high threat

            return max(0.0, score)  # Ensure non-negative score

        except Exception as e:
            logger.error(f"Error evaluating action: {str(e)}")
            return 0.1  # Minimal fallback score

    def _select_best_action(
        self, action_evaluations: List[Tuple[Dict[str, Any], float]]
    ) -> Optional[CharacterAction]:
        """
        Select the best action from evaluated options.

        Args:
            action_evaluations: List of (action, score) tuples

        Returns:
            CharacterAction object or None for waiting
        """
        try:
            if not action_evaluations:
                return None

            # Sort by evaluation score (highest first)
            action_evaluations.sort(key=lambda x: x[1], reverse=True)

            # Select best action with some randomness for variety
            best_actions = [
                action
                for action, score in action_evaluations
                if score >= action_evaluations[0][1] * 0.8
            ]

            if not best_actions:
                return None

            # Add some randomness to prevent completely predictable behavior
            selected = random.choice(best_actions)

            # Convert to CharacterAction format
            action_id = (
                f"{self.agent_core.agent_id}_action_{datetime.now().strftime('%H%M%S')}"
            )

            character_action = CharacterAction(
                action_type=selected.get("action_type", "observe"),
                target=selected.get("target"),
                priority=selected.get("priority", ActionPriority.NORMAL),
                reasoning=self._generate_action_reasoning(selected),
                parameters={
                    "agent_id": self.agent_core.agent_id,
                    "action_id": action_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return character_action

        except Exception as e:
            logger.error(f"Error selecting best action: {str(e)}")
            return None

    def _generate_action_reasoning(self, action: Dict[str, Any]) -> str:
        """
        Generate reasoning explanation for the selected action.

        Args:
            action: Selected action dictionary

        Returns:
            str: Reasoning explanation
        """
        try:
            action_type = action.get("action_type", "observe")
            character_name = self.agent_core.character_name

            reasoning_templates = {
                "observe": f"{character_name} carefully observes the situation to gather more information.",
                "investigate": f"{character_name} decides to investigate further to uncover important details.",
                "communicate": f"{character_name} attempts to establish communication with others.",
                "defensive_action": f"{character_name} takes defensive measures to protect against threats.",
                "retreat": f"{character_name} strategically withdraws to a safer position.",
                "advance": f"{character_name} moves forward to gain a tactical advantage.",
                "coordinate": f"{character_name} coordinates with allies to improve effectiveness.",
                "exploit_opportunity": f"{character_name} seizes the opportunity to advance their objectives.",
            }

            base_reasoning = reasoning_templates.get(
                action_type,
                f"{character_name} decides to {action_type} based on the current situation.",
            )

            # Add character-specific context
            morale_context = ""
            if self.agent_core.morale_level > 0.7:
                morale_context = " Their high morale drives them to act decisively."
            elif self.agent_core.morale_level < 0.3:
                morale_context = (
                    " Their low morale makes them cautious in their approach."
                )

            return base_reasoning + morale_context

        except Exception as e:
            logger.error(f"Error generating action reasoning: {str(e)}")
            return "Character decides to act based on current assessment."

    def _llm_enhanced_decision_making(
        self,
        world_state_update: Dict[str, Any],
        situation_assessment: Dict[str, Any],
        available_actions: List[Dict[str, Any]],
    ) -> Optional[CharacterAction]:
        """
        Use LLM to enhance decision-making with character-specific insights.

        Args:
            world_state_update: Current world state
            situation_assessment: Situation analysis
            available_actions: Available action options

        Returns:
            CharacterAction from LLM guidance or None
        """
        # Placeholder for LLM integration
        # This would construct a character-specific prompt and call the LLM API
        # For now, return None to fall back to algorithmic decision-making
        return None

    def _process_narrative_situation_update(
        self, narrative_context: Dict[str, Any]
    ) -> None:
        """Process narrative context updates."""
        try:
            # Extract story elements and update character's narrative understanding
            story_phase = narrative_context.get("current_phase", "unknown")
            events = narrative_context.get("triggered_events", [])

            # Update character's goals based on narrative context
            if story_phase and story_phase != "unknown":
                self.agent_core.add_to_subjective_worldview(
                    "current_goals", "narrative_phase", story_phase
                )

            # Process narrative events
            for event in events:
                self.agent_core.add_to_subjective_worldview(
                    "recent_events", event, datetime.now().isoformat()
                )

        except Exception as e:
            logger.error(f"Error processing narrative situation update: {str(e)}")

    def _process_event_for_relationships(self, event: Dict[str, Any]) -> None:
        """Process events for relationship and social context updates."""
        try:
            # Basic event processing for relationship updates
            # This would be expanded with more sophisticated relationship modeling
            event_type = event.get("type", "unknown")
            participants = event.get("participants", [])

            # Simple relationship adjustment based on event type
            if event_type in ["cooperation", "alliance"]:
                for participant in participants:
                    if participant != self.agent_core.agent_id:
                        current_strength = self.agent_core.get_relationship_strength(
                            participant
                        )
                        self.agent_core.add_relationship(
                            participant, min(1.0, current_strength + 0.1)
                        )
            elif event_type in ["conflict", "betrayal"]:
                for participant in participants:
                    if participant != self.agent_core.agent_id:
                        current_strength = self.agent_core.get_relationship_strength(
                            participant
                        )
                        self.agent_core.add_relationship(
                            participant, max(-1.0, current_strength - 0.2)
                        )

        except Exception as e:
            logger.error(f"Error processing event for relationships: {str(e)}")

    def _record_decision(
        self, action: Optional[CharacterAction], decision_type: str
    ) -> None:
        """Record decision for analysis and debugging."""
        try:
            if action and hasattr(action, "__dict__"):
                action_payload = action.__dict__
            else:
                action_payload = action or {}

            decision_record = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.agent_core.agent_id,
                "action_type": action_payload.get("action_type", "wait"),
                "decision_type": decision_type,
                "reasoning": action_payload.get(
                    "reasoning", "Chose to wait and observe"
                ),
                "morale_at_decision": self.agent_core.morale_level,
            }

            self.decision_history.append(decision_record)

            # Keep history manageable
            if len(self.decision_history) > 100:
                self.decision_history = self.decision_history[-50:]

        except Exception as e:
            logger.error(f"Error recording decision: {str(e)}")

    def get_decision_metrics(self) -> Dict[str, Any]:
        """
        Get decision-making performance metrics.

        Returns:
            Dictionary containing decision metrics and analysis
        """
        try:
            if not self.decision_history:
                return {"decisions_made": 0, "error": "No decision history available"}

            recent_decisions = self.decision_history[-10:]  # Last 10 decisions

            action_types = {}
            decision_types = {}

            for decision in recent_decisions:
                action_type = decision.get("action_type", "unknown")
                decision_type = decision.get("decision_type", "unknown")

                action_types[action_type] = action_types.get(action_type, 0) + 1
                decision_types[decision_type] = decision_types.get(decision_type, 0) + 1

            return {
                "total_decisions": len(self.decision_history),
                "recent_decisions": len(recent_decisions),
                "action_type_distribution": action_types,
                "decision_type_distribution": decision_types,
                "llm_available": self.llm_available,
                "last_action": self.last_action_taken,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating decision metrics: {str(e)}")
            return {"error": str(e)}
