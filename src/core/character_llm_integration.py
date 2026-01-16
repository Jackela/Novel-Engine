#!/usr/bin/env python3
"""
Character LLM Integration Module
===============================

Handles LLM integration and prompt construction for PersonaAgent characters.
Separated from the main PersonaAgent to follow Single Responsibility Principle.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.types.shared_types import ActionPriority, CharacterAction

# Module-level LLM service instance (lazy loaded)
_llm_service_instance: Optional[Any] = None


def _get_llm_service() -> Any:
    """Get or create the LLM service singleton."""
    global _llm_service_instance
    if _llm_service_instance is None:
        from src.core.llm_service import UnifiedLLMService

        _llm_service_instance = UnifiedLLMService()
    return _llm_service_instance


logger = logging.getLogger(__name__)


class LLMIntegration:
    """
    Handles LLM integration for character agents.

    This class encapsulates all LLM-related operations that were previously
    part of the PersonaAgent class, improving maintainability and testability.
    """

    def __init__(self, agent_id: str):
        """
        Initialize the LLM integration.

        Args:
            agent_id: Identifier for the agent
        """
        self.agent_id = agent_id
        self.prompt_history: List[str] = []
        self.response_history: List[str] = []

    def enhanced_decision_making(
        self,
        world_state_update: Dict[str, Any],
        situation_assessment: Dict[str, Any],
        available_actions: List[Dict[str, Any]],
        character_data: Dict[str, Any],
        personality_traits: Dict[str, float],
        decision_weights: Dict[str, float],
        subjective_worldview: Dict[str, Any],
        current_status: str,
        morale_level: float,
        current_location: Optional[str],
        relationships: Dict[str, float],
    ) -> Optional[CharacterAction]:
        """
        Enhanced decision-making using LLM integration.

        Returns:
            CharacterAction object based on LLM guidance, or None if LLM suggests waiting
        """
        try:
            logger.debug(
                f"Agent {self.agent_id} beginning LLM-enhanced decision making"
            )

            # Construct dynamic, character-specific prompt
            prompt = self._construct_character_prompt(
                world_state_update,
                situation_assessment,
                available_actions,
                character_data,
                personality_traits,
                decision_weights,
                subjective_worldview,
                current_status,
                morale_level,
                current_location,
                relationships,
            )

            # Call LLM with constructed prompt
            llm_response = self._call_llm(prompt)

            # Parse LLM response into structured action
            parsed_action = self._parse_llm_response(llm_response, available_actions)

            if parsed_action:
                logger.debug(
                    f"Agent {self.agent_id} successfully processed LLM response into action: {parsed_action.action_type}"
                )
                return parsed_action
            else:
                logger.debug(
                    f"Agent {self.agent_id} LLM response parsed as 'wait/observe' action"
                )
                return None

        except Exception as e:
            logger.error(
                f"LLM-enhanced decision making failed for agent {self.agent_id}: {str(e)}"
            )
            raise  # Re-raise for fallback handling

    def _construct_character_prompt(
        self,
        world_state_update: Dict[str, Any],
        situation_assessment: Dict[str, Any],
        available_actions: List[Dict[str, Any]],
        character_data: Dict[str, Any],
        personality_traits: Dict[str, float],
        decision_weights: Dict[str, float],
        subjective_worldview: Dict[str, Any],
        current_status: str,
        morale_level: float,
        current_location: Optional[str],
        relationships: Dict[str, float],
    ) -> str:
        """Construct character-specific prompt for LLM decision-making."""
        character_name = character_data.get("name", "Unknown Character")
        primary_faction = subjective_worldview.get("primary_faction", "Unknown Faction")

        # Build all prompt sections using helper methods
        character_background = self._build_character_background_section(
            character_name,
            primary_faction,
            character_data,
            current_status,
            morale_level,
        )
        personality_section = self._build_personality_section(personality_traits)
        decision_weights_section = self._build_decision_weights_section(
            decision_weights
        )
        situation_section = self._build_situation_section(
            world_state_update,
            situation_assessment,
            current_location,
            subjective_worldview,
        )
        world_state_section = self._build_world_state_section(world_state_update)
        narrative_section = self._build_narrative_section(subjective_worldview)
        action_history_section = self._build_action_history_section(
            world_state_update, morale_level
        )
        relationships_section = self._build_relationships_section(relationships)
        actions_section = self._build_actions_section(available_actions)
        decision_request = self._build_decision_request_section(
            character_name, primary_faction
        )

        # Construct final prompt
        prompt = f"""{character_background}

{personality_section}
{decision_weights_section}
{situation_section}

{world_state_section}
{narrative_section}
{action_history_section}
{relationships_section}
{actions_section}
{decision_request}"""

        # Store in history
        self.prompt_history.append(prompt)
        if len(self.prompt_history) > 100:  # Limit history size
            self.prompt_history = self.prompt_history[-100:]

        logger.debug(
            f"Agent {self.agent_id} constructed prompt of {len(prompt)} characters"
        )
        return prompt

    def _build_character_background_section(
        self,
        character_name: str,
        primary_faction: str,
        character_data: Dict[str, Any],
        current_status: str,
        morale_level: float,
    ) -> str:
        """Build the character identity section of the prompt."""
        return f"""CHARACTER IDENTITY:
Name: {character_name}
Faction: {primary_faction}
Rank/Role: {character_data.get('rank_role', 'Unknown')}
Current Status: {current_status}
Morale Level: {morale_level:.2f} (-1.0 to 1.0 scale)"""

    def _build_personality_section(self, personality_traits: Dict[str, float]) -> str:
        """Build the personality traits section of the prompt."""
        section = "PERSONALITY TRAITS:\\n"
        for trait, value in personality_traits.items():
            section += f"- {trait.replace('_', ' ').title()}: {value:.2f} (strength on 0.0-1.0 scale)\\n"
        return section

    def _build_decision_weights_section(
        self, decision_weights: Dict[str, float]
    ) -> str:
        """Build the decision-making priorities section of the prompt."""
        section = "DECISION-MAKING PRIORITIES:\\n"
        for weight, value in decision_weights.items():
            section += f"- {weight.replace('_', ' ').title()}: {value:.2f} (importance on 0.0-1.0 scale)\\n"
        return section

    def _build_situation_section(
        self,
        world_state_update: Dict[str, Any],
        situation_assessment: Dict[str, Any],
        current_location: Optional[str],
        subjective_worldview: Dict[str, Any],
    ) -> str:
        """Build the current situation section of the prompt."""
        # Determine threat level from situation assessment
        threat_level = situation_assessment.get("threat_level", "low")
        if hasattr(threat_level, "value"):
            threat_level = threat_level.value

        current_goals = situation_assessment.get("current_goals", [])
        current_turn = world_state_update.get("current_turn", "Unknown")
        simulation_time = world_state_update.get("simulation_time", "Unknown")

        return f"""CURRENT SITUATION:
Turn Number: {current_turn}
Simulation Time: {simulation_time}
Threat Level: {threat_level}
Location: {current_location or 'Unknown'}
Active Goals: {len(current_goals)} mission objectives
Known Entities: {len(subjective_worldview.get('known_entities', {}))}
Recent Events: {len(subjective_worldview.get('recent_events', []))}"""

    def _build_world_state_section(self, world_state_update: Dict[str, Any]) -> str:
        """Build the world state update section of the prompt."""
        section = "WORLD STATE UPDATE:\\n"

        # Add recent events
        recent_events = world_state_update.get("recent_events", [])
        if recent_events:
            section += "Recent Events:\\n"
            for event in recent_events[-3:]:  # Last 3 events
                section += f"- {event.get('type', 'unknown')}: {event.get('description', 'No description')}\\n"
        else:
            section += "No significant recent events reported.\\n"

        # Add location updates
        location_updates = world_state_update.get("location_updates", {})
        if location_updates:
            section += "Location Updates:\\n"
            for location, info in location_updates.items():
                section += f"- {location}: {info}\\n"

        return section

    def _build_narrative_section(self, subjective_worldview: Dict[str, Any]) -> str:
        """Build the narrative context section of the prompt."""
        narrative_state = subjective_worldview.get("narrative_state", {})
        if not narrative_state:
            return ""

        section = "NARRATIVE CONTEXT:\\n"

        narrative_elements = [
            ("current_campaign", "Campaign"),
            ("story_setting", "Setting"),
            ("current_atmosphere", "Atmosphere"),
            ("current_narrative_prompt", "Character Situation"),
            ("faction_narrative_prompt", "Faction Context"),
        ]

        for key, label in narrative_elements:
            value = narrative_state.get(key, "")
            if value:
                section += f"{label}: {value}\\n"

        story_markers = narrative_state.get("story_markers", [])
        if story_markers:
            section += f"Story Progress: {', '.join(story_markers[-3:])}\\n"

        return section + "\\n"

    def _build_action_history_section(
        self, world_state_update: Dict[str, Any], morale_level: float
    ) -> str:
        """Build the action history section of the prompt."""
        current_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        current_turn = world_state_update.get("current_turn", "Unknown")

        section = f"""ACTION HISTORY:
Current Time: {current_timestamp}
Turn Context: This is turn {current_turn} of the simulation.
Previous Action: This is my first decision in the simulation.
Agent State: Active and operational with current morale {morale_level:.2f}
"""
        return section

    def _build_relationships_section(self, relationships: Dict[str, float]) -> str:
        """Build the key relationships section of the prompt."""
        section = "KEY RELATIONSHIPS:\\n"
        important_relationships = {
            k: v for k, v in relationships.items() if abs(v) > 0.3
        }

        if important_relationships:
            for entity, strength in important_relationships.items():
                relationship_type = self._get_relationship_type(strength)
                section += f"- {entity}: {relationship_type} ({strength:.2f})\\n"
        else:
            section += "No significant relationships recorded.\\n"

        return section

    def _get_relationship_type(self, strength: float) -> str:
        """Determine relationship type based on strength."""
        if strength > 0.7:
            return "Strong Ally"
        elif strength > 0.3:
            return "Ally"
        elif strength < -0.3:
            return "Enemy" if strength > -0.7 else "Strong Enemy"
        else:
            return "Neutral"

    def _build_actions_section(self, available_actions: List[Dict[str, Any]]) -> str:
        """Build the available actions section of the prompt."""
        section = "AVAILABLE ACTIONS:\\n"
        for i, action in enumerate(available_actions, 1):
            action_desc = action.get("description", "No description")
            if "narrative_type" in action:
                action_desc += f" (Story Action: {action['narrative_type']})"
            section += f"{i}. {action.get('type', 'unknown')}: {action_desc}\\n"
        return section

    def _build_decision_request_section(
        self, character_name: str, primary_faction: str
    ) -> str:
        """Build the decision request section of the prompt."""
        return (
            "DECISION REQUEST:\n"
            f"As {character_name}, a {primary_faction} character with the personality "
            "and priorities described above, what action would you take in this situation? "
            "Consider your character's traits, faction loyalty, current goals, and the "
            "recent events.\n\n"
            "Please respond in the following format:\n"
            "ACTION: [choose one of the numbered available actions or 'wait_observe']\n"
            "TARGET: [specify target if applicable, or 'none']\n"
            "REASONING: [explain your decision from the character's perspective in 1-2 "
            "sentences]\n\n"
            "Example response:\n"
            "ACTION: 3\n"
            "TARGET: hostile_entity_alpha\n"
            "REASONING: As a dedicated envoy of the Founders' Council, my duty requires me "
            "to engage threats to protect innocent civilians. My decisive nature and high "
            "mission success priority compel me to take direct action."
        )

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with the constructed prompt using UnifiedLLMService."""
        fallback_response = "ACTION: observe\nTARGET: none\nREASONING: Assessing situation before taking action."

        try:
            from src.core.llm_service import LLMProvider, LLMRequest, ResponseFormat

            llm_service = _get_llm_service()

            if LLMProvider.GEMINI not in llm_service.providers:
                logger.warning(
                    f"Agent {self.agent_id}: Gemini not configured, using fallback"
                )
                response = fallback_response
            else:
                request = LLMRequest(
                    prompt=prompt,
                    provider=LLMProvider.GEMINI,
                    response_format=ResponseFormat.ACTION_FORMAT,
                    temperature=0.7,
                    max_tokens=1500,
                    cache_enabled=True,
                    requester=f"character_llm_{self.agent_id}",
                )

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                llm_response = loop.run_until_complete(llm_service.generate(request))

                if "[LLM Error:" in llm_response.content:
                    logger.warning(f"Agent {self.agent_id}: LLM error, using fallback")
                    response = fallback_response
                else:
                    logger.info(
                        f"Agent {self.agent_id}: LLM call successful ({llm_response.tokens_used} tokens)"
                    )
                    response = llm_response.content

        except Exception as e:
            logger.warning(
                f"Agent {self.agent_id}: LLM call failed ({e}), using fallback"
            )
            response = fallback_response

        # Store in history
        self.response_history.append(response)
        if len(self.response_history) > 100:  # Limit history size
            self.response_history = self.response_history[-100:]

        return response

    def _parse_llm_response(
        self, llm_response: str, available_actions: List[Dict[str, Any]]
    ) -> Optional[CharacterAction]:
        """Parse LLM response into structured action."""
        try:
            # Validate response format
            if not self._is_valid_llm_response_format(llm_response):
                logger.warning(
                    f"Agent {self.agent_id} received invalid LLM response format"
                )
                return None

            # Extract components using regex
            action_match = re.search(r"ACTION:\s*(.+)", llm_response, re.IGNORECASE)
            target_match = re.search(r"TARGET:\s*(.+)", llm_response, re.IGNORECASE)
            reasoning_match = re.search(
                r"REASONING:\s*(.+)", llm_response, re.IGNORECASE | re.DOTALL
            )

            if not action_match:
                logger.warning(
                    f"Agent {self.agent_id} LLM response missing ACTION field"
                )
                return None

            action_text = action_match.group(1).strip()
            target_text = target_match.group(1).strip() if target_match else "none"
            reasoning_text = (
                reasoning_match.group(1).strip()
                if reasoning_match
                else "No reasoning provided"
            )

            # Handle wait/observe actions
            if action_text.lower() in ["wait", "observe", "wait_observe"]:
                return None

            # Map action number to action type
            action_type = None
            if action_text.isdigit():
                action_index = int(action_text) - 1  # Convert to 0-based index
                if 0 <= action_index < len(available_actions):
                    action_type = available_actions[action_index].get("type", "unknown")
            else:
                # Direct action type specified
                action_type = action_text.lower()

            if not action_type:
                logger.warning(
                    f"Agent {self.agent_id} could not determine action type from: {action_text}"
                )
                return None

            # Determine priority based on action type and reasoning
            priority = self._determine_llm_action_priority(action_type, reasoning_text)

            return CharacterAction(
                agent_id=self.agent_id,
                action_type=action_type,
                target=target_text if target_text.lower() != "none" else None,
                reasoning=reasoning_text,
                priority=priority,
            )

        except Exception as e:
            logger.error(f"Failed to parse LLM response for agent {self.agent_id}: {e}")
            return None

    def _is_valid_llm_response_format(self, response: str) -> bool:
        """Validate LLM response format."""
        required_fields = ["ACTION:", "TARGET:", "REASONING:"]
        return all(field in response.upper() for field in required_fields)

    def _determine_llm_action_priority(
        self, action_type: str, reasoning: str
    ) -> ActionPriority:
        """Determine action priority based on action type and reasoning."""
        reasoning_lower = reasoning.lower()

        # High priority indicators
        if any(
            keyword in reasoning_lower
            for keyword in ["urgent", "critical", "emergency", "immediate"]
        ):
            return ActionPriority.CRITICAL

        if any(
            keyword in reasoning_lower
            for keyword in ["important", "must", "duty", "loyalty"]
        ):
            return ActionPriority.HIGH

        # Action type priorities
        if action_type in ["attack", "defend", "heal", "rescue"]:
            return ActionPriority.HIGH
        elif action_type in ["communicate", "investigate", "support"]:
            return ActionPriority.MEDIUM
        else:
            return ActionPriority.LOW

