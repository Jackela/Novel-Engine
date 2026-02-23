#!/usr/bin/env python3
"""
Character Reactor Application Service

This module provides the CharacterReactor service, which determines how characters
react to world events. Reactions are generated based on rules considering:
- Event type and impact scope
- Character traits and personality
- Character's faction membership and location
- Character's relationships with affected parties

Why this matters:
    Character reactions bring the world to life. When a war breaks out, a pacifist
    should protest. When a trade route opens, a merchant should celebrate. These
    reactions create emergent narrative and make events feel personal to each
    character.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Protocol

from src.contexts.character.domain.aggregates.character import Character
from src.contexts.character.domain.value_objects.character_memory import CharacterMemory
from src.contexts.character.domain.value_objects.character_reaction import (
    CharacterReaction,
    ReactionType,
)
from src.contexts.world.domain.entities.history_event import EventType, HistoryEvent, ImpactScope

if TYPE_CHECKING:
    from src.contexts.world.domain.aggregates.world_state import WorldState


class CharacterMemoryService(Protocol):
    """Protocol for the character memory service dependency.

    This allows dependency injection without requiring a concrete implementation.
    """

    def create_memory(
        self,
        character_id: str,
        content: str,
        importance: int,
        tags: Optional[List[str]] = None,
    ) -> CharacterMemory:
        """Create a memory for a character.

        Args:
            character_id: ID of the character
            content: The memory content
            importance: Importance score (1-10)
            tags: Optional list of tags

        Returns:
            The created CharacterMemory
        """
        ...


# Reaction type verbs for narrative generation
REACTION_VERBS: dict[ReactionType, str] = {
    ReactionType.OBSERVE: "watches with interest",
    ReactionType.FLEE: "flees in fear",
    ReactionType.INVESTIGATE: "investigates curiously",
    ReactionType.IGNORE: "pays no heed",
    ReactionType.CELEBRATE: "celebrates joyfully",
    ReactionType.MOURN: "mourns deeply",
    ReactionType.PROTEST: "protests vehemently",
}

# Base intensity by impact scope
BASE_INTENSITY_BY_SCOPE: dict[ImpactScope, int] = {
    ImpactScope.LOCAL: 3,
    ImpactScope.REGIONAL: 5,
    ImpactScope.GLOBAL: 7,
}


class CharacterReactor:
    """Service for generating character reactions to world events.

    The reactor uses rule-based logic to determine how a character would respond
    to an event. Rules are evaluated in order, with the first match winning.

    Example:
        >>> reactor = CharacterReactor(memory_service)
        >>> reaction = reactor.react_to_event(character, war_event, world)
        >>> print(reaction.narrative)
        "Sir Aldric protests vehemently upon hearing The Great War"
    """

    def __init__(self, memory_service: Optional[CharacterMemoryService] = None):
        """Initialize the reactor.

        Args:
            memory_service: Optional service for creating character memories.
                           If None, memories won't be automatically created.
        """
        self._memory_service = memory_service

    def react_to_event(
        self,
        character: Character,
        event: HistoryEvent,
        world: "WorldState",
    ) -> CharacterReaction:
        """Generate a character's reaction to a world event.

        Evaluates reaction rules in order and creates a CharacterReaction with
        the appropriate type, intensity, and narrative.

        Args:
            character: The character reacting to the event
            event: The historical event being reacted to
            world: The current world state

        Returns:
            A CharacterReaction value object describing the reaction
        """
        # Calculate intensity
        intensity = self._calculate_intensity(character, event)

        # Determine reaction type (first match wins)
        reaction_type = self._determine_reaction_type(character, event)

        # Generate narrative
        narrative = self._generate_narrative(character, event, reaction_type)

        # Create the reaction
        reaction = CharacterReaction.create(
            character_id=str(character.character_id),
            event_id=event.id,
            reaction_type=reaction_type,
            intensity=intensity,
            narrative=narrative,
        )

        # Create memory if appropriate (not IGNORE and intensity >= 4)
        if reaction.should_create_memory() and self._memory_service:
            self._create_memory_for_reaction(character, event, reaction)

        # Return reaction with memory_created flag if memory was created
        if reaction.should_create_memory() and self._memory_service:
            return reaction.with_memory_created()
        return reaction

    def _calculate_intensity(self, character: Character, event: HistoryEvent) -> int:
        """Calculate the reaction intensity.

        Formula: base_intensity + modifiers (clamped to 1-10)

        Base intensity determined by impact_scope:
        - LOCAL: 3
        - REGIONAL: 5
        - GLOBAL: 7

        Modifiers:
        - +2 if character.faction_id in event.affected_faction_ids
        - +1 if character's current location in event.affected_location_ids

        Args:
            character: The character reacting
            event: The event being reacted to

        Returns:
            Intensity score (1-10)
        """
        # Default to LOCAL scope if not set
        impact_scope = event.impact_scope or ImpactScope.LOCAL
        base_intensity = BASE_INTENSITY_BY_SCOPE.get(impact_scope, 3)

        intensity = base_intensity

        # +2 if character's faction is affected
        if character.faction_id and event.affected_faction_ids:
            if character.faction_id in event.affected_faction_ids:
                intensity += 2

        # +1 if character's current location is affected
        if character.current_location_id and event.affected_location_ids:
            if character.current_location_id in event.affected_location_ids:
                intensity += 1

        # Clamp to valid range
        return max(1, min(10, intensity))

    def _determine_reaction_type(
        self, character: Character, event: HistoryEvent
    ) -> ReactionType:
        """Determine the reaction type based on rules.

        Rules are evaluated in order; first match wins:
        1. WAR + 'pacifist' trait -> PROTEST
        2. DEATH + affected character in relationships -> MOURN
        3. TRADE + 'merchant' trait -> CELEBRATE
        4. WAR + current location affected -> FLEE
        5. GLOBAL impact scope -> OBSERVE
        6. Default -> IGNORE

        Args:
            character: The character reacting
            event: The event being reacted to

        Returns:
            The appropriate ReactionType
        """
        # Rule 1: WAR + pacifist trait -> PROTEST
        if event.event_type == EventType.WAR:
            if self._has_trait(character, "pacifist"):
                return ReactionType.PROTEST

        # Rule 2: DEATH + relationship -> MOURN
        if event.event_type == EventType.DEATH:
            if self._has_relationship_to_event_figures(character, event):
                return ReactionType.MOURN

        # Rule 3: TRADE + merchant trait -> CELEBRATE
        if event.event_type == EventType.TRADE:
            if self._has_trait(character, "merchant"):
                return ReactionType.CELEBRATE

        # Rule 4: WAR + location affected -> FLEE
        if event.event_type == EventType.WAR:
            if self._is_character_location_affected(character, event):
                return ReactionType.FLEE

        # Rule 5: GLOBAL impact -> OBSERVE
        if event.impact_scope == ImpactScope.GLOBAL:
            return ReactionType.OBSERVE

        # Rule 6: Default -> IGNORE
        return ReactionType.IGNORE

    def _has_trait(self, character: Character, trait_name: str) -> bool:
        """Check if character has a specific personality trait.

        Checks both personality_traits (in profile) and psychology (Big Five).
        For personality_traits, any score >= 0.7 indicates the trait.
        For psychology, checks dominant traits.

        Args:
            character: The character to check
            trait_name: The trait name to look for (case-insensitive)

        Returns:
            True if the character has this trait
        """
        trait_lower = trait_name.lower()

        # Check personality traits in profile
        if hasattr(character.profile, "personality_traits"):
            try:
                trait_score = character.profile.personality_traits.get_trait_score(trait_lower)
                if trait_score >= 0.7:
                    return True
            except (AttributeError, KeyError):
                pass

        # Check psychology dominant traits
        if character.psychology:
            try:
                dominant_traits = character.psychology.get_dominant_traits()
                if trait_lower in [t.lower() for t in dominant_traits]:
                    return True
            except (AttributeError, TypeError):
                pass

        # Check metadata for custom traits
        traits_meta = character.metadata.get("traits", {})
        if isinstance(traits_meta, dict):
            if trait_lower in [k.lower() for k in traits_meta.keys()]:
                return True

        return False

    def _has_relationship_to_event_figures(
        self, character: Character, event: HistoryEvent
    ) -> bool:
        """Check if character has a relationship with figures in the event.

        Args:
            character: The character to check
            event: The event containing affected figures

        Returns:
            True if character has a relationship with event figures
        """
        # Get relationships from metadata (common pattern in this codebase)
        relationships = character.metadata.get("relationships", {})
        if not isinstance(relationships, dict):
            return False

        # Check if any key figures are in the relationships
        for figure in event.key_figures:
            # key_figures are names, relationships dict keys are character IDs
            # For simplicity, check if any relationship entry mentions the figure
            for rel_list in relationships.values():
                if isinstance(rel_list, list):
                    for rel in rel_list:
                        if isinstance(rel, dict):
                            if figure in str(rel):
                                return True

        # Also check affected_faction_ids if character shares faction
        if event.affected_faction_ids and character.faction_id:
            if character.faction_id in event.affected_faction_ids:
                return True

        return False

    def _is_character_location_affected(
        self, character: Character, event: HistoryEvent
    ) -> bool:
        """Check if character's current location is affected by the event.

        Args:
            character: The character to check
            event: The event with affected locations

        Returns:
            True if character's location is in the affected locations
        """
        if not character.current_location_id:
            return False

        if not event.affected_location_ids:
            return False

        return character.current_location_id in event.affected_location_ids

    def _generate_narrative(
        self,
        character: Character,
        event: HistoryEvent,
        reaction_type: ReactionType,
    ) -> str:
        """Generate a narrative description of the reaction.

        Template: "{character_name} {reaction_verb} upon hearing {event_title}"

        Args:
            character: The character reacting
            event: The event being reacted to
            reaction_type: The type of reaction

        Returns:
            A narrative string describing the reaction
        """
        character_name = character.profile.name
        reaction_verb = REACTION_VERBS.get(reaction_type, "reacts to")
        event_title = event.name

        return f"{character_name} {reaction_verb} upon hearing {event_title}"

    def _create_memory_for_reaction(
        self,
        character: Character,
        event: HistoryEvent,
        reaction: CharacterReaction,
    ) -> None:
        """Create a memory for the character about this event.

        Args:
            character: The character to create a memory for
            event: The event that triggered the reaction
            reaction: The reaction that was generated
        """
        if not self._memory_service:
            return

        # Create memory content combining event and reaction
        memory_content = f"{reaction.narrative}. {event.description[:200]}"

        # Create tags based on event type and reaction type
        tags = [
            event.event_type.value,
            reaction.reaction_type.value.lower(),
            "event_reaction",
        ]
        if event.impact_scope:
            tags.append(event.impact_scope.value)

        self._memory_service.create_memory(
            character_id=str(character.character_id),
            content=memory_content,
            importance=reaction.intensity,
            tags=tags,
        )

    def batch_react(
        self,
        characters: List[Character],
        event: HistoryEvent,
        world: "WorldState",
    ) -> List[CharacterReaction]:
        """Generate reactions for multiple characters.

        This is an optimization for processing many characters at once,
        useful for simulation ticks.

        Args:
            characters: List of characters to generate reactions for
            event: The event being reacted to
            world: The current world state

        Returns:
            List of CharacterReaction objects (one per character)
        """
        return [
            self.react_to_event(character, event, world)
            for character in characters
        ]
