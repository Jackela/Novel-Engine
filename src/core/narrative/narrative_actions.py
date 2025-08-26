#!/usr/bin/env python3
"""
Narrative Action Framework.

This module implements story-driven action types that extend beyond combat mechanics
to enable rich narrative interactions in the multi-agent simulator.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ..types.shared_types import CharacterAction, ActionPriority

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NarrativeActionType(Enum):
    """Enumeration of narrative action types for story-driven gameplay."""
    INVESTIGATE = "investigate"
    DIALOGUE = "dialogue"
    DIPLOMACY = "diplomacy"
    BETRAYAL = "betrayal"
    OBSERVE_ENVIRONMENT = "observe_environment"
    SEARCH_AREA = "search_area"
    ANALYZE_DATA = "analyze_data"
    COMMUNICATE_FACTION = "communicate_faction"


@dataclass
class NarrativeOutcome:
    """
    Represents the result of a narrative action execution.
    
    Contains both mechanical effects and story elements that advance
    the narrative and provide character development opportunities.
    """
    success: bool
    description: str
    character_impact: Dict[str, str]
    environmental_change: str
    story_advancement: List[str]
    relationship_changes: Dict[str, float]
    discovered_information: List[str]
    narrative_consequences: List[str]


class NarrativeActionResolver:
    """
    Handles resolution of narrative actions and generates story-appropriate outcomes.
    
    Provides context-aware resolution that considers character traits, faction
    relationships, and current narrative state to create meaningful story progression.
    """
    
    def __init__(self, campaign_brief=None):
        """Initializes the NarrativeActionResolver."""
        self.campaign_brief = campaign_brief
        self.logger = logging.getLogger(f"{__name__}.NarrativeActionResolver")
        self.investigation_counter = 0
        self.dialogue_history = []
        self.story_state = {}
    
    def resolve_investigate_action(self, action: CharacterAction, character_data: Dict, 
                                   world_state: Dict) -> NarrativeOutcome:
        """
        Resolves an investigation action to gather story information.

        Args:
            action: The investigation action being performed.
            character_data: The character performing the action.
            world_state: The current world state context.

        Returns:
            A NarrativeOutcome with the investigation results.
        """
        self.investigation_counter += 1
        character_name = character_data.get('name', 'Unknown')
        target = action.target or 'unknown_area'
        
        success_chance = self._calculate_investigation_success(character_data)
        success = random.random() < success_chance
        
        if success:
            discovered_info = self._generate_investigation_discovery(target, character_data)
            outcome = NarrativeOutcome(
                success=True,
                description=f"{character_name} carefully investigates {target} and makes a discovery.",
                character_impact={character_data.get('agent_id', 'unknown'): f"You uncover information about {target}."},
                environmental_change=f"The area around {target} shows signs of recent examination.",
                story_advancement=self._check_story_advancement('investigation'),
                relationship_changes={},
                discovered_information=discovered_info,
                narrative_consequences=[f"Knowledge of {target} may be useful later."]
            )
        else:
            outcome = NarrativeOutcome(
                success=False,
                description=f"{character_name} investigates {target} but finds nothing of note.",
                character_impact={character_data.get('agent_id', 'unknown'): f"Your investigation of {target} yields no results."},
                environmental_change=f"The area around {target} appears undisturbed.",
                story_advancement=[],
                relationship_changes={},
                discovered_information=[],
                narrative_consequences=["A more thorough search may be required."]
            )
        
        self.logger.info(f"Investigation action resolved - Success: {success}, Target: {target}")
        return outcome
    
    def resolve_dialogue_action(self, action: CharacterAction, character_data: Dict,
                                world_state: Dict) -> NarrativeOutcome:
        """
        Resolves a dialogue action for character interaction.

        Args:
            action: The dialogue action being performed.
            character_data: The character initiating the dialogue.
            world_state: The current world state context.

        Returns:
            A NarrativeOutcome with the dialogue results.
        """
        character_name = character_data.get('name', 'Unknown')
        target = action.target or 'a nearby entity'
        
        dialogue_entry = {'character': character_name, 'target': target, 'turn': world_state.get('current_turn', 0)}
        self.dialogue_history.append(dialogue_entry)
        
        success_chance = self._calculate_dialogue_success(character_data, target)
        success = random.random() < success_chance
        
        if success:
            outcome = NarrativeOutcome(
                success=True,
                description=f"{character_name} successfully communicates with {target}.",
                character_impact={character_data.get('agent_id', 'unknown'): f"You have a productive conversation with {target}."},
                environmental_change="",
                story_advancement=self._check_story_advancement('dialogue'),
                relationship_changes={target: 0.1},
                discovered_information=self._generate_dialogue_information(target),
                narrative_consequences=[f"Future interactions with {target} may be more fruitful."]
            )
        else:
            outcome = NarrativeOutcome(
                success=False,
                description=f"{character_name} attempts to communicate with {target} but is rebuffed.",
                character_impact={character_data.get('agent_id', 'unknown'): f"Your attempt to speak with {target} is unsuccessful."},
                environmental_change="",
                story_advancement=[],
                relationship_changes={},
                discovered_information=[],
                narrative_consequences=["Alternative communication methods may be necessary."]
            )
        
        self.logger.info(f"Dialogue action resolved - Success: {success}, Target: {target}")
        return outcome
    
    def _calculate_investigation_success(self, character_data: Dict) -> float:
        """Calculates the success probability for investigation actions."""
        base_chance = 0.6
        personality_traits = character_data.get('personality_traits', {})
        if personality_traits.get('cautious', 0) > 0.6:
            base_chance += 0.2
        return min(base_chance, 0.95)
    
    def _calculate_dialogue_success(self, character_data: Dict, target: str) -> float:
        """Calculates the success probability for dialogue actions."""
        base_chance = 0.5
        personality_traits = character_data.get('personality_traits', {})
        if personality_traits.get('charismatic', 0) > 0.6:
            base_chance += 0.2
        return min(base_chance, 0.9)
    
    def _generate_investigation_discovery(self, target: str, character_data: Dict) -> List[str]:
        """Generates information discovered through investigation."""
        return [f"You found a clue related to {target}."]
    
    def _generate_dialogue_information(self, target: str) -> List[str]:
        """Generates information learned through dialogue."""
        return [f"You learned something new from {target}."]
    
    def _check_story_advancement(self, action_type: str) -> List[str]:
        """Checks if this action triggers story progression markers."""
        advancement = []
        if self.campaign_brief:
            if action_type == 'investigation' and self.investigation_counter >= 3:
                advancement.append("Investigation milestone reached")
            if action_type == 'dialogue' and len(self.dialogue_history) >= 2:
                advancement.append("Dialogue milestone reached")
        return advancement