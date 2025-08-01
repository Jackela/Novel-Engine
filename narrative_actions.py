#!/usr/bin/env python3
"""
Narrative Action Framework
=========================

This module implements story-driven action types that extend beyond combat mechanics
to enable rich narrative interactions in the Warhammer 40k Multi-Agent Simulator.

The narrative action system provides:
1. Investigation actions for exploring story elements
2. Dialogue actions for character interactions
3. Diplomacy actions for negotiation and alliance building
4. Betrayal actions for dramatic relationship changes
5. Resolution logic for non-combat scenarios

Architecture Reference: Story 1.1 - Narrative Engine Foundation
Development Phase: Phase 1 - Narrative Action Framework
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Import shared type definitions
from shared_types import CharacterAction, ActionPriority

# Configure narrative action logging
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
    character_impact: Dict[str, str]  # Impact on specific characters
    environmental_change: str
    story_advancement: List[str]  # Story progression markers triggered
    relationship_changes: Dict[str, float]  # Relationship modifications
    discovered_information: List[str]  # New information revealed
    narrative_consequences: List[str]  # Future story implications


class NarrativeActionResolver:
    """
    Handles resolution of narrative actions and generates story-appropriate outcomes.
    
    Provides context-aware resolution that considers character traits, faction
    relationships, and current narrative state to create meaningful story progression.
    """
    
    def __init__(self, campaign_brief=None):
        self.campaign_brief = campaign_brief
        self.logger = logging.getLogger(f"{__name__}.NarrativeActionResolver")
        self.investigation_counter = 0
        self.dialogue_history = []
        self.story_state = {}
    
    def resolve_investigate_action(self, action: CharacterAction, character_data: Dict, 
                                   world_state: Dict) -> NarrativeOutcome:
        """
        Resolve an investigation action to gather story information.
        
        Args:
            action: The investigation action being performed
            character_data: Character performing the action
            world_state: Current world state context
            
        Returns:
            NarrativeOutcome with investigation results
        """
        self.investigation_counter += 1
        character_name = character_data.get('name', 'Unknown')
        target = action.target or 'unknown_area'
        
        # Determine investigation success based on character traits
        success_chance = self._calculate_investigation_success(character_data)
        success = random.random() < success_chance
        
        if success:
            # Generate successful investigation outcome
            discovered_info = self._generate_investigation_discovery(target, character_data)
            
            outcome = NarrativeOutcome(
                success=True,
                description=f"{character_name} carefully investigates {target} and makes significant discoveries.",
                character_impact={
                    character_data.get('agent_id', 'unknown'): f"You uncover valuable information about {target}."
                },
                environmental_change=f"Investigation site at {target} shows signs of recent examination.",
                story_advancement=self._check_story_advancement('investigation'),
                relationship_changes={},
                discovered_information=discovered_info,
                narrative_consequences=[f"Knowledge of {target} may prove crucial later."]
            )
        else:
            # Generate failed investigation outcome
            outcome = NarrativeOutcome(
                success=False,
                description=f"{character_name} investigates {target} but finds little of immediate value.",
                character_impact={
                    character_data.get('agent_id', 'unknown'): f"Your investigation of {target} yields minimal results."
                },
                environmental_change=f"Investigation site at {target} shows signs of disturbance.",
                story_advancement=[],
                relationship_changes={},
                discovered_information=["The area appears disturbed but reveals no obvious secrets."],
                narrative_consequences=["A more thorough approach might yield better results."]
            )
        
        self.logger.info(f"Investigation action resolved - Success: {success}, Target: {target}")
        return outcome
    
    def resolve_dialogue_action(self, action: CharacterAction, character_data: Dict,
                                world_state: Dict) -> NarrativeOutcome:
        """
        Resolve a dialogue action for character interaction.
        
        Args:
            action: The dialogue action being performed
            character_data: Character initiating dialogue
            world_state: Current world state context
            
        Returns:
            NarrativeOutcome with dialogue results
        """
        character_name = character_data.get('name', 'Unknown')
        target = action.target or 'environmental_systems'
        
        # Record dialogue attempt
        dialogue_entry = {
            'character': character_name,
            'target': target,
            'turn': world_state.get('current_turn', 0),
            'timestamp': datetime.now().isoformat()
        }
        self.dialogue_history.append(dialogue_entry)
        
        # Determine dialogue success based on character traits and faction
        success_chance = self._calculate_dialogue_success(character_data, target)
        success = random.random() < success_chance
        
        if success:
            # Generate successful dialogue outcome
            outcome = NarrativeOutcome(
                success=True,
                description=f"{character_name} successfully establishes communication with {target}.",
                character_impact={
                    character_data.get('agent_id', 'unknown'): f"Your words find their mark with {target}."
                },
                environmental_change=f"Communication channels with {target} are now open.",
                story_advancement=self._check_story_advancement('dialogue'),
                relationship_changes={target: 0.1},  # Slight positive relationship boost
                discovered_information=self._generate_dialogue_information(target),
                narrative_consequences=[f"Future interactions with {target} may be more favorable."]
            )
        else:
            # Generate failed dialogue outcome
            outcome = NarrativeOutcome(
                success=False,
                description=f"{character_name} attempts to communicate with {target} but receives no clear response.",
                character_impact={
                    character_data.get('agent_id', 'unknown'): f"Your attempts to reach {target} meet with silence."
                },
                environmental_change=f"No response detected from {target}.",
                story_advancement=[],
                relationship_changes={},
                discovered_information=["The silence itself may be significant."],
                narrative_consequences=["Alternative approaches to communication may be needed."]
            )
        
        self.logger.info(f"Dialogue action resolved - Success: {success}, Target: {target}")
        return outcome
    
    def resolve_diplomacy_action(self, action: CharacterAction, character_data: Dict,
                                 world_state: Dict) -> NarrativeOutcome:
        """
        Resolve a diplomacy action for negotiation or alliance building.
        
        Args:
            action: The diplomacy action being performed
            character_data: Character attempting diplomacy
            world_state: Current world state context
            
        Returns:
            NarrativeOutcome with diplomacy results
        """
        character_name = character_data.get('name', 'Unknown')
        target = action.target or 'other_agents'
        
        # Diplomacy requires high faction loyalty and communication skills
        success_chance = self._calculate_diplomacy_success(character_data)
        success = random.random() < success_chance
        
        if success:
            outcome = NarrativeOutcome(
                success=True,
                description=f"{character_name} successfully negotiates with {target}, finding common ground.",
                character_impact={
                    character_data.get('agent_id', 'unknown'): f"Your diplomatic efforts with {target} bear fruit."
                },
                environmental_change=f"Diplomatic relations with {target} improve noticeably.",
                story_advancement=self._check_story_advancement('diplomacy'),
                relationship_changes={target: 0.2},  # Significant positive relationship boost
                discovered_information=[f"You learn about {target}'s motivations and concerns."],
                narrative_consequences=[f"This alliance with {target} may prove crucial in future challenges."]
            )
        else:
            outcome = NarrativeOutcome(
                success=False,
                description=f"{character_name} attempts diplomacy with {target} but negotiations stall.",
                character_impact={
                    character_data.get('agent_id', 'unknown'): f"Your diplomatic overtures to {target} are met with suspicion."
                },
                environmental_change=f"Tension remains high between you and {target}.",
                story_advancement=[],
                relationship_changes={target: -0.05},  # Slight negative impact
                discovered_information=["Diplomatic solutions may not be viable at this time."],
                narrative_consequences=["Failed diplomacy may limit future cooperation opportunities."]
            )
        
        self.logger.info(f"Diplomacy action resolved - Success: {success}, Target: {target}")
        return outcome
    
    def resolve_betrayal_action(self, action: CharacterAction, character_data: Dict,
                               world_state: Dict) -> NarrativeOutcome:
        """
        Resolve a betrayal action that dramatically alters relationships.
        
        Args:
            action: The betrayal action being performed
            character_data: Character committing betrayal
            world_state: Current world state context
            
        Returns:
            NarrativeOutcome with betrayal results
        """
        character_name = character_data.get('name', 'Unknown')
        target = action.target or 'trusted_ally'
        
        # Betrayal always succeeds but has significant consequences
        outcome = NarrativeOutcome(
            success=True,
            description=f"{character_name} betrays the trust of {target} in a shocking turn of events.",
            character_impact={
                character_data.get('agent_id', 'unknown'): f"You have betrayed {target} - there is no turning back."
            },
            environmental_change=f"The atmosphere grows tense as {character_name}'s betrayal becomes apparent.",
            story_advancement=self._check_story_advancement('betrayal'),
            relationship_changes={
                target: -0.8,  # Massive negative impact
                'all_others': -0.2  # Others lose some trust
            },
            discovered_information=[f"You learn {target}'s weaknesses through your betrayal."],
            narrative_consequences=[
                f"Your betrayal of {target} will have lasting consequences.",
                "Other characters may be less likely to trust you.",
                "New conflict opportunities may arise from this betrayal."
            ]
        )
        
        self.logger.warning(f"Betrayal action resolved - Character: {character_name}, Target: {target}")
        return outcome
    
    def _calculate_investigation_success(self, character_data: Dict) -> float:
        """Calculate success probability for investigation actions."""
        base_chance = 0.6
        
        # Character traits that help with investigation
        personality_traits = character_data.get('personality_traits', {})
        
        # Cautious characters are better investigators
        if personality_traits.get('cautious', 0) > 0.6:
            base_chance += 0.2
        
        # Technical knowledge helps
        if 'tech' in character_data.get('name', '').lower():
            base_chance += 0.15
        
        # Space Marines have enhanced senses
        if 'space marine' in character_data.get('faction', '').lower():
            base_chance += 0.1
        
        return min(base_chance, 0.95)  # Cap at 95%
    
    def _calculate_dialogue_success(self, character_data: Dict, target: str) -> float:
        """Calculate success probability for dialogue actions."""
        base_chance = 0.5
        
        # Character traits that help with dialogue
        personality_traits = character_data.get('personality_traits', {})
        
        # Charismatic characters are better at dialogue
        if personality_traits.get('charismatic', 0) > 0.6:
            base_chance += 0.2
        
        # Faction compatibility
        character_faction = character_data.get('faction', '').lower()
        if 'imperial' in character_faction and 'system' in target.lower():
            base_chance += 0.15  # Imperial characters work well with Imperial systems
        
        return min(base_chance, 0.9)  # Cap at 90%
    
    def _calculate_diplomacy_success(self, character_data: Dict) -> float:
        """Calculate success probability for diplomacy actions."""
        base_chance = 0.4  # Diplomacy is challenging
        
        # High faction loyalty helps with diplomacy
        decision_weights = character_data.get('decision_weights', {})
        faction_loyalty = decision_weights.get('faction_loyalty', 0.5)
        
        if faction_loyalty > 0.8:
            base_chance += 0.2
        
        # Personal relationships matter
        personal_relationships = decision_weights.get('personal_relationships', 0.5)
        if personal_relationships > 0.6:
            base_chance += 0.15
        
        return min(base_chance, 0.8)  # Cap at 80%
    
    def _generate_investigation_discovery(self, target: str, character_data: Dict) -> List[str]:
        """Generate information discovered through investigation."""
        discoveries = [
            f"Signs of recent activity at {target}.",
            f"Hidden compartments or passages near {target}.",
            f"Data logs or personal effects left at {target}.",
            f"Environmental clues about what happened at {target}."
        ]
        
        # Character-specific discoveries
        character_faction = character_data.get('faction', '').lower()
        if 'mechanicus' in character_faction:
            discoveries.append(f"Technical analysis reveals machine spirit anomalies at {target}.")
        elif 'space marine' in character_faction:
            discoveries.append(f"Enhanced senses detect subtle threats near {target}.")
        
        return random.sample(discoveries, min(2, len(discoveries)))
    
    def _generate_dialogue_information(self, target: str) -> List[str]:
        """Generate information learned through dialogue."""
        information = [
            f"{target} provides cryptic responses about recent events.",
            f"Communication with {target} reveals underlying concerns.",
            f"{target} shares fragmentary data about the current situation.",
            f"Partial cooperation from {target} yields useful insights."
        ]
        
        return [random.choice(information)]
    
    def _check_story_advancement(self, action_type: str) -> List[str]:
        """Check if this action triggers story progression markers."""
        advancement = []
        
        if self.campaign_brief:
            # Check campaign-specific advancement triggers
            if action_type == 'investigation' and self.investigation_counter >= 3:
                advancement.append("Multiple investigations completed")
            
            if action_type == 'dialogue' and len(self.dialogue_history) >= 2:
                advancement.append("Communication patterns established")
            
            if action_type == 'diplomacy':
                advancement.append("Diplomatic channels opened")
            
            if action_type == 'betrayal':
                advancement.append("Trust networks disrupted")
        
        return advancement