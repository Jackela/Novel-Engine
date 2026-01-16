#!/usr/bin/env python3
"""
Enhanced Decision Engine
=======================

Enhanced version of DecisionEngine that utilizes structured character context
from ContextLoaderService for more sophisticated decision-making. This engine
extends the base DecisionEngine with context-driven modifiers while maintaining
backward compatibility.

Features:
- Objective alignment scoring
- Behavioral trigger processing
- Relationship context evaluation
- Emotional drive modifiers
- Memory-based decision influences
"""

import logging
from typing import Any, Dict

# Import base decision engine
from src.agents.decision_engine import DecisionEngine
from src.agents.persona_agent.core import PersonaAgentCore

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedDecisionEngine(DecisionEngine):
    """
    Enhanced DecisionEngine with context-driven decision making.

    Extends the base DecisionEngine to utilize structured character context
    for more nuanced and personality-driven decision making while maintaining
    full backward compatibility with existing agent behavior.
    """

    def __init__(self, agent_core: PersonaAgentCore):
        """Initialize the enhanced decision engine."""
        super().__init__(agent_core)
        self.context_modifier_enabled = True
        self.modifier_weights = {
            "objective_alignment": 0.3,
            "behavioral_trigger": 0.25,
            "relationship_context": 0.2,
            "emotional_drive": 0.15,
            "memory_influence": 0.1,
        }
        logger.debug("Enhanced DecisionEngine initialized")

    def _evaluate_action_option(
        self, action: Dict[str, Any], situation: Dict[str, Any]
    ) -> float:
        """Enhanced action evaluation with context modifiers."""
        # Base evaluation (existing logic unchanged)
        base_score = super()._evaluate_action_option(action, situation)

        # Apply context-driven modifiers if available
        if (
            self.context_modifier_enabled
            and hasattr(self.core, "character_data")
            and "enhanced_context" in self.core.character_data
        ):
            context_score = self._apply_context_modifiers(base_score, action, situation)
            logger.debug(
                f"Action {action.get('action_type', 'unknown')} enhanced: {base_score:.2f} → {context_score:.2f}"
            )
            return context_score

        return base_score

    def _apply_context_modifiers(
        self, base_score: float, action: Dict, situation: Dict
    ) -> float:
        """Apply enhanced context modifiers to action evaluation."""
        try:
            character_data = self.core.character_data
            enhanced_context = character_data.get("enhanced_context")

            if not enhanced_context:
                return base_score

            score = base_score

            # Apply objective alignment modifiers
            if "active_objectives" in character_data:
                objective_modifier = self._get_objective_alignment_modifier(
                    action, character_data["active_objectives"]
                )
                score *= (
                    1.0
                    + (objective_modifier - 1.0)
                    * self.modifier_weights["objective_alignment"]
                )

            # Apply behavioral trigger modifiers
            if "behavioral_triggers" in character_data:
                trigger_modifier = self._get_behavioral_trigger_modifier(
                    action, situation, character_data["behavioral_triggers"]
                )
                score *= (
                    1.0
                    + (trigger_modifier - 1.0)
                    * self.modifier_weights["behavioral_trigger"]
                )

            # Apply relationship context modifiers
            if (
                "enhanced_relationships" in character_data
                and "target_character" in action
            ):
                relationship_modifier = self._get_relationship_modifier(
                    action, character_data["enhanced_relationships"]
                )
                score *= (
                    1.0
                    + (relationship_modifier - 1.0)
                    * self.modifier_weights["relationship_context"]
                )

            # Apply emotional drive modifiers
            if "emotional_drives" in character_data:
                emotion_modifier = self._get_emotional_drive_modifier(
                    action, character_data["emotional_drives"]
                )
                score *= (
                    1.0
                    + (emotion_modifier - 1.0)
                    * self.modifier_weights["emotional_drive"]
                )

            # Apply memory influence modifiers
            if "formative_events" in character_data:
                memory_modifier = self._get_memory_influence_modifier(
                    action, situation, character_data["formative_events"]
                )
                score *= (
                    1.0
                    + (memory_modifier - 1.0)
                    * self.modifier_weights["memory_influence"]
                )

            return max(0.1, min(3.0, score))  # Clamp to reasonable range

        except Exception as e:
            logger.warning(f"Error applying context modifiers: {e}")
            return base_score

    def _get_objective_alignment_modifier(
        self, action: Dict, objectives: Dict
    ) -> float:
        """Calculate modifier based on alignment with active objectives."""
        try:
            action_type = action.get("action_type", "").lower()
            alignment_score = 1.0

            for obj_name, obj_data in objectives.items():
                # Simple keyword matching for objective alignment
                obj_keywords = obj_name.lower().split()
                if any(keyword in action_type for keyword in obj_keywords):
                    # Calculate priority-based modifier
                    priority_modifier = 1.0 + (
                        obj_data["priority"] / 20.0
                    )  # Up to 50% bonus for priority 10

                    # Apply tier-based multiplier
                    tier_multiplier = {
                        "core": 1.4,
                        "strategic": 1.3,
                        "tactical": 1.2,
                    }.get(obj_data["tier"], 1.0)

                    alignment_score *= priority_modifier * tier_multiplier

            return min(1.6, alignment_score)  # Cap at 60% bonus

        except Exception as e:
            logger.warning(f"Error calculating objective alignment: {e}")
            return 1.0

    def _get_behavioral_trigger_modifier(
        self, action: Dict, situation: Dict, triggers: Dict
    ) -> float:
        """Calculate modifier based on behavioral triggers from memory."""
        try:
            modifier = 1.0

            for trigger_name, trigger_data in triggers.items():
                # Check if any trigger conditions are met in current situation
                for condition in trigger_data["conditions"]:
                    if self._condition_matches_situation(condition, situation):
                        response = trigger_data["response"].lower()
                        action_type = action.get("action_type", "").lower()

                        # Apply behavioral response influence
                        if "aggressive" in response and any(
                            keyword in action_type
                            for keyword in ["attack", "combat", "fight"]
                        ):
                            modifier *= 1.3
                        elif "cautious" in response and any(
                            keyword in action_type
                            for keyword in ["wait", "observe", "retreat"]
                        ):
                            modifier *= 1.4
                        elif "social" in response and any(
                            keyword in action_type
                            for keyword in ["interact", "communicate", "negotiate"]
                        ):
                            modifier *= 1.3
                        elif "defensive" in response and any(
                            keyword in action_type
                            for keyword in ["defend", "protect", "guard"]
                        ):
                            modifier *= 1.3

            return max(0.7, min(1.5, modifier))  # 30% penalty to 50% bonus

        except Exception as e:
            logger.warning(f"Error calculating behavioral trigger modifier: {e}")
            return 1.0

    def _get_relationship_modifier(self, action: Dict, relationships: Dict) -> float:
        """Calculate modifier based on relationship context."""
        try:
            target = action.get("target_character", "")
            if not target or target not in relationships:
                return 1.0

            relationship = relationships[target]
            trust_level = relationship["trust_level"]
            action_type = action.get("action_type", "").lower()

            # High trust encourages cooperation, low trust encourages caution
            if any(
                keyword in action_type
                for keyword in ["cooperate", "help", "assist", "support"]
            ):
                return 1.0 + (
                    trust_level / 250.0
                )  # Up to 40% bonus for trust level 100
            elif any(
                keyword in action_type
                for keyword in ["attack", "betray", "harm", "oppose"]
            ):
                return 1.0 + (
                    (100 - trust_level) / 250.0
                )  # Up to 40% bonus for low trust
            elif any(
                keyword in action_type for keyword in ["negotiate", "trade", "discuss"]
            ):
                # Moderate trust levels favor negotiation
                trust_factor = (
                    1.0 - abs(trust_level - 50) / 100.0
                )  # Peak at trust level 50
                return 1.0 + (trust_factor * 0.2)  # Up to 20% bonus

            return 1.0

        except Exception as e:
            logger.warning(f"Error calculating relationship modifier: {e}")
            return 1.0

    def _get_emotional_drive_modifier(self, action: Dict, drives: Dict) -> float:
        """Calculate modifier based on emotional drives."""
        try:
            modifier = 1.0
            action_type = action.get("action_type", "").lower()

            for drive_name, drive_data in drives.items():
                weight = drive_data["weight"]
                drive_name_lower = drive_name.lower()

                # Match drives to action types
                if "security" in drive_name_lower or "safety" in drive_name_lower:
                    if any(
                        keyword in action_type
                        for keyword in ["defend", "prepare", "fortify", "retreat"]
                    ):
                        modifier *= 1.0 + (
                            weight * 0.4
                        )  # Up to 40% bonus for dominant drives
                elif (
                    "connection" in drive_name_lower or "belonging" in drive_name_lower
                ):
                    if any(
                        keyword in action_type
                        for keyword in ["interact", "help", "communicate", "join"]
                    ):
                        modifier *= 1.0 + (weight * 0.4)
                elif "purpose" in drive_name_lower or "achievement" in drive_name_lower:
                    if any(
                        keyword in action_type
                        for keyword in ["objective", "mission", "accomplish", "achieve"]
                    ):
                        modifier *= 1.0 + (weight * 0.4)
                elif "autonomy" in drive_name_lower or "control" in drive_name_lower:
                    if any(
                        keyword in action_type
                        for keyword in ["lead", "command", "decide", "independent"]
                    ):
                        modifier *= 1.0 + (weight * 0.4)

            return max(0.8, min(1.4, modifier))  # 20% penalty to 40% bonus

        except Exception as e:
            logger.warning(f"Error calculating emotional drive modifier: {e}")
            return 1.0

    def _get_memory_influence_modifier(
        self, action: Dict, situation: Dict, events: Dict
    ) -> float:
        """Calculate modifier based on formative memory events."""
        try:
            modifier = 1.0
            action_type = action.get("action_type", "").lower()

            for event_name, event_data in events.items():
                # Check if any trigger phrases from memories match current situation
                for trigger_phrase in event_data.get("trigger_phrases", []):
                    if self._phrase_matches_context(trigger_phrase, action, situation):
                        decision_influence = event_data.get(
                            "decision_influence", ""
                        ).lower()

                        # Apply memory-based decision influence
                        if (
                            "encourages" in decision_influence
                            and "caution" in decision_influence
                        ):
                            if any(
                                keyword in action_type
                                for keyword in ["wait", "observe", "retreat"]
                            ):
                                modifier *= 1.25
                        elif (
                            "promotes" in decision_influence
                            and "aggressive" in decision_influence
                        ):
                            if any(
                                keyword in action_type
                                for keyword in ["attack", "confront", "challenge"]
                            ):
                                modifier *= 1.25
                        elif (
                            "increases" in decision_influence
                            and "trust" in decision_influence
                        ):
                            if any(
                                keyword in action_type
                                for keyword in ["cooperate", "help", "trust"]
                            ):
                                modifier *= 1.25

            return max(0.8, min(1.3, modifier))  # 20% penalty to 30% bonus

        except Exception as e:
            logger.warning(f"Error calculating memory influence modifier: {e}")
            return 1.0

    def _condition_matches_situation(self, condition: str, situation: Dict) -> bool:
        """Check if a behavioral trigger condition matches the current situation."""
        try:
            condition_lower = condition.lower()

            # Simple keyword matching against situation data
            situation_text = " ".join(
                str(v).lower() for v in situation.values() if isinstance(v, str)
            )

            return any(
                keyword.strip() in situation_text
                for keyword in condition_lower.split(",")
            )

        except Exception as e:
            logger.warning(f"Error matching condition to situation: {e}")
            return False

    def _phrase_matches_context(
        self, phrase: str, action: Dict, situation: Dict
    ) -> bool:
        """Check if a trigger phrase matches the current action/situation context."""
        try:
            phrase_lower = phrase.lower()

            # Check action context
            action_text = " ".join(
                str(v).lower() for v in action.values() if isinstance(v, str)
            )

            # Check situation context
            situation_text = " ".join(
                str(v).lower() for v in situation.values() if isinstance(v, str)
            )

            combined_context = f"{action_text} {situation_text}"

            # Simple keyword matching
            return any(
                keyword.strip() in combined_context
                for keyword in phrase_lower.split(",")
            )

        except Exception as e:
            logger.warning(f"Error matching phrase to context: {e}")
            return False

    def get_context_decision_summary(
        self, action: Dict, situation: Dict
    ) -> Dict[str, Any]:
        """Get summary of context-driven decision factors."""
        try:
            if (
                not hasattr(self.agent_core, "character_data")
                or "enhanced_context" not in self.agent_core.character_data
            ):
                return {"context_available": False}

            character_data = self.agent_core.character_data

            summary = {
                "context_available": True,
                "modifiers_applied": {},
                "active_objectives_count": len(
                    character_data.get("active_objectives", {})
                ),
                "behavioral_triggers_count": len(
                    character_data.get("behavioral_triggers", {})
                ),
                "enhanced_relationships_count": len(
                    character_data.get("enhanced_relationships", {})
                ),
                "emotional_drives_count": len(
                    character_data.get("emotional_drives", {})
                ),
                "formative_events_count": len(
                    character_data.get("formative_events", {})
                ),
            }

            # Calculate individual modifiers for transparency
            if "active_objectives" in character_data:
                summary["modifiers_applied"]["objective_alignment"] = (
                    self._get_objective_alignment_modifier(
                        action, character_data["active_objectives"]
                    )
                )

            if "behavioral_triggers" in character_data:
                summary["modifiers_applied"]["behavioral_trigger"] = (
                    self._get_behavioral_trigger_modifier(
                        action, situation, character_data["behavioral_triggers"]
                    )
                )

            if (
                "enhanced_relationships" in character_data
                and "target_character" in action
            ):
                summary["modifiers_applied"]["relationship_context"] = (
                    self._get_relationship_modifier(
                        action, character_data["enhanced_relationships"]
                    )
                )

            if "emotional_drives" in character_data:
                summary["modifiers_applied"]["emotional_drive"] = (
                    self._get_emotional_drive_modifier(
                        action, character_data["emotional_drives"]
                    )
                )

            if "formative_events" in character_data:
                summary["modifiers_applied"]["memory_influence"] = (
                    self._get_memory_influence_modifier(
                        action, situation, character_data["formative_events"]
                    )
                )

            return summary

        except Exception as e:
            logger.error(f"Error generating context decision summary: {e}")
            return {"context_available": False, "error": str(e)}





