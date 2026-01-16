#!/usr/bin/env python3
"""
Narrative Processing Module for Novel Engine.

This module handles all narrative-related functionality including campaign brief loading,
narrative context generation, story state management, and narrative action processing.
Extracted from DirectorAgent for better modularity and maintainability.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from campaign_brief import CampaignBrief, CampaignBriefLoader
from narrative_actions import NarrativeActionResolver, NarrativeOutcome

from src.core.types.shared_types import CharacterAction
from src.agents.persona_agent.agent import PersonaAgent

logger = logging.getLogger(__name__)


class NarrativeProcessor:
    """
    Manages narrative processing and story-driven simulation features.

    Responsibilities:
    - Campaign brief loading and management
    - Narrative context generation for agents
    - Story state tracking and updates
    - Narrative action processing and outcomes
    - Event trigger management
    """

    def __init__(self, campaign_brief_path: Optional[str] = None):
        """
        Initialize the Narrative Processor.

        Args:
            campaign_brief_path: Optional path to campaign brief file
        """
        self.campaign_brief_path = campaign_brief_path
        self.campaign_brief: Optional[CampaignBrief] = None
        self.narrative_resolver: Optional[NarrativeActionResolver] = None

        # Initialize story state
        self.story_state = {
            "current_phase": "initialization",
            "investigation_count": 0,
            "dialogue_count": 0,
            "story_progression": [],
            "character_relationships": {},
            "triggered_events": [],
            "environment_discoveries": [],
            "faction_status": {},
        }

        # Load campaign brief if provided
        self._load_campaign_brief()

    def _load_campaign_brief(self) -> None:
        """
        Load campaign brief file to define narrative context for story-driven simulation.

        Campaign briefs transform the simulation from basic combat mechanics to rich
        story-driven character interactions. If no brief is provided, simulation
        runs in traditional combat-focused mode.

        Raises:
            ValueError: If campaign brief file exists but contains invalid data
            OSError: If file operations fail
        """
        if self.campaign_brief_path is None:
            logger.info("No campaign brief specified - running in combat mode")
            self.narrative_resolver = NarrativeActionResolver(None)
            return

        try:
            campaign_brief_path = Path(self.campaign_brief_path)

            if not campaign_brief_path.exists():
                logger.warning(
                    f"Campaign brief file not found: {self.campaign_brief_path}"
                )
                logger.info("Running in combat mode without narrative context")
                self.narrative_resolver = NarrativeActionResolver(None)
                return

            # Load campaign brief
            logger.info(f"Loading campaign brief from: {self.campaign_brief_path}")

            brief_loader = CampaignBriefLoader()
            self.campaign_brief = brief_loader.load_from_file(campaign_brief_path)

            if self.campaign_brief:
                logger.info(f"Campaign brief loaded: {self.campaign_brief.title}")
                logger.info(f"Narrative context: {self.campaign_brief.setting}")

                # Initialize narrative action resolver with campaign context
                self.narrative_resolver = NarrativeActionResolver(self.campaign_brief)

                # Initialize story state phase from campaign brief
                if hasattr(self.campaign_brief, "initial_phase"):
                    self.story_state["current_phase"] = (
                        self.campaign_brief.initial_phase
                    )
                else:
                    self.story_state["current_phase"] = "investigation"

                logger.info(
                    f"Story initialized in '{self.story_state['current_phase']}' phase"
                )
            else:
                logger.warning("Failed to load campaign brief data")
                self.narrative_resolver = NarrativeActionResolver(None)

        except Exception as e:
            logger.error(f"Error loading campaign brief: {str(e)}")
            logger.info("Falling back to combat mode")
            self.narrative_resolver = NarrativeActionResolver(None)

    def trigger_initial_narrative_events(self, log_event_callback) -> None:
        """
        Trigger initial narrative events marked for simulation start.

        Processes campaign brief events with 'simulation_start' trigger condition
        to establish the initial story context for all agents.

        Args:
            log_event_callback: Callback function for logging events
        """
        if not self.campaign_brief:
            return

        for event in self.campaign_brief.key_events:
            if event.trigger_condition == "simulation_start":
                logger.info(f"Triggering initial narrative event: {event.description}")

                # Add event to story state
                self.story_state["triggered_events"].append(
                    {
                        "event": event,
                        "turn_triggered": 0,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                # Log narrative event
                event_description = f"**NARRATIVE EVENT:** {event.description}"
                log_event_callback(event_description)

    def generate_narrative_context(
        self,
        agent_id: str,
        registered_agents: List[PersonaAgent],
        current_turn_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate narrative context for a specific agent based on current story state.

        Creates rich story elements that transform basic simulation updates into
        compelling narrative situations. Character-specific context is tailored
        to their faction, personality, and relationship to the ongoing story.

        Args:
            agent_id: ID of the agent to generate context for
            registered_agents: List of all registered agents
            current_turn_number: Current simulation turn number

        Returns:
            Dict containing narrative context or None if no campaign brief loaded
        """
        if not self.campaign_brief:
            return None

        try:
            # Find the target agent to get character data
            target_agent = None
            for agent in registered_agents:
                if agent.agent_id == agent_id:
                    target_agent = agent
                    break

            if not target_agent:
                logger.warning(
                    f"Could not find agent {agent_id} for narrative context generation"
                )
                return None

            # Basic narrative context structure
            narrative_context = {
                "story_setting": self.campaign_brief.setting,
                "current_phase": self.story_state["current_phase"],
                "character_context": self._generate_character_specific_context(
                    target_agent
                ),
                "active_events": self._check_narrative_event_triggers(
                    target_agent, current_turn_number
                ),
                "available_actions": self._identify_available_narrative_actions(
                    target_agent, registered_agents
                ),
                "relationship_status": self._get_agent_relationships(target_agent),
                "story_progress": self.story_state["story_progression"][
                    -3:
                ],  # Last 3 progressions
            }

            return narrative_context

        except Exception as e:
            logger.error(f"Error generating narrative context for {agent_id}: {str(e)}")
            return None

    def _generate_character_specific_context(self, agent: PersonaAgent) -> str:
        """
        Generate character-specific narrative context based on their faction and traits.

        Args:
            agent: PersonaAgent to generate context for

        Returns:
            String containing personalized narrative context
        """
        character_name = agent.character_data.get("name", "Unknown")
        faction = agent.subjective_worldview.get("primary_faction", "Unknown")

        # Basic character context description
        base_context = f"As {character_name} of {faction}, you find yourself in this unfolding story."

        # Add faction-specific narrative perspective
        faction_lower = faction.lower()
        if any(
            keyword in faction_lower for keyword in ("alliance network", "coalition")
        ):
            alliance_context = " Your duty to the Founders' Council guides your perception of these events."
            base_context += alliance_context
        elif "freewind" in faction_lower:
            freewind_context = " Your freewind instincts tell you there's a decisive opportunity emerging here."
            base_context += freewind_context
        elif "engineering collective" in faction_lower:
            engineering_context = " Your engineered senses detect deeper mysteries in the system processes here."
            base_context += engineering_context

        # Add context based on the current story phase
        if self.story_state["current_phase"] == "investigation":
            base_context += " The mysteries here call for careful investigation."
        elif self.story_state["current_phase"] == "revelation":
            base_context += " Critical information is coming to light."
        elif self.story_state["current_phase"] == "confrontation":
            base_context += " The tension is building toward a decisive moment."

        return base_context

    def _check_narrative_event_triggers(
        self, agent: PersonaAgent, current_turn_number: int
    ) -> List[Dict[str, Any]]:
        """
        Check which narrative events should trigger for the current turn and agent.

        Args:
            agent: Agent to check event triggers for
            current_turn_number: Current simulation turn number

        Returns:
            List of active narrative events
        """
        active_events = []

        if not self.campaign_brief:
            return active_events

        for event in self.campaign_brief.key_events:
            should_trigger = False

            # Check for turn-based triggers
            if "turn >=" in event.trigger_condition:
                try:
                    required_turn = int(event.trigger_condition.split(">=")[1].strip())
                    if current_turn_number >= required_turn:
                        should_trigger = True
                except ValueError:
                    logger.warning(
                        f"Invalid turn trigger condition: {event.trigger_condition}"
                    )

            # Check for investigation count-based triggers
            elif "investigation_count >=" in event.trigger_condition:
                try:
                    required_count = int(event.trigger_condition.split(">=")[1].strip())
                    if self.story_state["investigation_count"] >= required_count:
                        should_trigger = True
                except ValueError:
                    logger.warning(
                        f"Invalid investigation trigger condition: {event.trigger_condition}"
                    )

            if should_trigger:
                active_events.append(
                    {
                        "event": event,
                        "description": event.description,
                        "impact": getattr(event, "impact", "minor"),
                    }
                )

        return active_events

    def _identify_available_narrative_actions(
        self, agent: PersonaAgent, registered_agents: List[PersonaAgent]
    ) -> List[str]:
        """
        Identify narrative actions available to the character in current context.

        Args:
            agent: Agent to identify actions for
            registered_agents: List of all registered agents

        Returns:
            List of available narrative action names
        """
        available_actions = ["investigate", "observe_environment"]  # Always available

        # Add actions based on story state
        if self.story_state["investigation_count"] > 0:
            available_actions.append("analyze_data")

        if len(registered_agents) > 1:
            available_actions.extend(["dialogue", "communicate_faction"])

        # Add actions based on character traits
        personality_traits = agent.personality_traits
        decision_weights = agent.decision_weights

        if decision_weights.get("personal_relationships", 0) > 0.6:
            available_actions.append("diplomacy")

        if (
            personality_traits.get("aggressive", 0) < 0.3
            and personality_traits.get("cautious", 0) > 0.6
        ):
            available_actions.append("search_area")

        # Remove duplicates and return
        return list(set(available_actions))

    def _get_agent_relationships(self, agent: PersonaAgent) -> Dict[str, float]:
        """
        Get relationship status for the agent with other characters.

        Args:
            agent: Agent to get relationships for

        Returns:
            Dict mapping character names to relationship values
        """
        agent_name = agent.character_data.get("name", agent.agent_id)
        return self.story_state["character_relationships"].get(agent_name, {})

    def process_narrative_action(
        self, action: CharacterAction, agent: PersonaAgent
    ) -> Optional[NarrativeOutcome]:
        """
        Process narrative actions and generate story-driven outcomes.

        This method handles story actions like investigation, dialogue, diplomacy, and betrayal
        by using the narrative action resolver to create meaningful story consequences.

        Args:
            action: The character action to process
            agent: The agent who performed the action

        Returns:
            NarrativeOutcome if the action is narrative-based, None otherwise
        """
        if not hasattr(action, "action_type"):
            return None

        # Check if this is a narrative action
        narrative_action_types = [
            "investigate",
            "dialogue",
            "diplomacy",
            "betrayal",
            "observe_environment",
            "communicate_faction",
        ]

        if action.action_type not in narrative_action_types:
            return None

        logger.info(
            f"Processing narrative action: {action.action_type} by {agent.agent_id}"
        )

        # Get character data for narrative processing
        character_data = {
            "agent_id": agent.agent_id,
            "name": agent.character_data.get("name", "Unknown"),
            "faction": agent.character_data.get("faction", "Unknown"),
            "personality": agent.personality_traits,
            "decision_weights": agent.decision_weights,
        }

        # Process action through narrative resolver
        if self.narrative_resolver:
            narrative_outcome = self.narrative_resolver.resolve_action(
                action_type=action.action_type,
                character_data=character_data,
                story_context=self.story_state,
                action_parameters=getattr(action, "parameters", {}),
            )

            if narrative_outcome:
                # Update story state based on outcome
                self._update_story_state(narrative_outcome)
                return narrative_outcome

        return None

    def _update_story_state(self, narrative_outcome: NarrativeOutcome) -> None:
        """
        Update the story state based on narrative action outcomes.

        This method processes the consequences of narrative actions and updates
        the ongoing story progression markers and character relationships.

        Args:
            narrative_outcome: The outcome of a narrative action to process
        """
        try:
            # Update story progression markers
            for advancement in narrative_outcome.story_advancement:
                if advancement not in self.story_state["story_progression"]:
                    self.story_state["story_progression"].append(advancement)
                    logger.info(f"Story advancement: {advancement}")

            # Update character relationships
            for character, change in narrative_outcome.relationship_changes.items():
                if character not in self.story_state["character_relationships"]:
                    self.story_state["character_relationships"][character] = 0.0

                self.story_state["character_relationships"][character] += change
                logger.info(
                    f"Relationship change: {character} {change:+.2f} (now {self.story_state['character_relationships'][character]:.2f})"
                )

            # Track investigation count for event triggers
            if "investigation" in str(narrative_outcome.description).lower():
                self.story_state["investigation_count"] += 1

            # Track dialogue count for event triggers
            if (
                "dialogue" in str(narrative_outcome.description).lower()
                or "communication" in str(narrative_outcome.description).lower()
            ):
                self.story_state["dialogue_count"] += 1

            # Update current phase if specified in outcome
            if (
                hasattr(narrative_outcome, "phase_change")
                and narrative_outcome.phase_change
            ):
                self.story_state["current_phase"] = narrative_outcome.phase_change
                logger.info(f"Story phase changed to: {narrative_outcome.phase_change}")

        except Exception as e:
            logger.error(f"Error updating story state: {str(e)}")

    def get_story_state(self) -> Dict[str, Any]:
        """Get the current story state."""
        return self.story_state.copy()

    def has_campaign_brief(self) -> bool:
        """Check if a campaign brief is loaded."""
        return self.campaign_brief is not None



