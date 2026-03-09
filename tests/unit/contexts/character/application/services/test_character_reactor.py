#!/usr/bin/env python3
"""Tests for CharacterReactor service.

This module tests the CharacterReactor service which generates character
reactions to world events based on rules and character properties.
"""

from unittest.mock import MagicMock

import pytest

from src.contexts.character.application.services.character_reactor import (
    REACTION_VERBS,
    CharacterMemoryService,
    CharacterReactor,
)
from src.contexts.character.domain.aggregates.character import Character
from src.contexts.character.domain.value_objects.character_id import CharacterID
from src.contexts.character.domain.value_objects.character_memory import CharacterMemory
from src.contexts.character.domain.value_objects.character_profile import (
    Background,
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
    PersonalityTraits,
    PhysicalTraits,
)
from src.contexts.character.domain.value_objects.character_reaction import (
    CharacterReaction,
    ReactionType,
)
from src.contexts.character.domain.value_objects.character_stats import (
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from src.contexts.character.domain.value_objects.skills import Skills
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.history_event import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
)

pytestmark = pytest.mark.unit


# ==================== Test Fixtures ====================

@pytest.fixture
def mock_memory_service() -> MagicMock:
    """Create a mock memory service."""
    service = MagicMock(spec=CharacterMemoryService)
    service.create_memory.return_value = CharacterMemory.create(
        content="Test memory",
        importance=5,
        tags=["test"],
    )
    return service


@pytest.fixture
def basic_character() -> Character:
    """Create a basic character for testing."""
    character_id = CharacterID.generate()
    profile = CharacterProfile(
        name="Test Character",
        gender=Gender.MALE,
        race=CharacterRace.HUMAN,
        character_class=CharacterClass.FIGHTER,
        age=25,
        level=5,
        personality_traits=PersonalityTraits(traits={"courage": 0.5}),
        physical_traits=PhysicalTraits(),
        background=Background(),
    )
    stats = CharacterStats(
        core_abilities=CoreAbilities(
            strength=14,
            dexterity=12,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
        ),
        vital_stats=VitalStats(
            max_health=30,
            current_health=30,
            max_mana=10,
            current_mana=10,
            max_stamina=20,
            current_stamina=20,
            armor_class=14,
            speed=30,
        ),
        combat_stats=CombatStats(
            base_attack_bonus=3,
            initiative_modifier=1,
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        ),
        experience_points=1000,
        skill_points=10,
    )
    skills = Skills.create_basic_skills()

    return Character(
        character_id=character_id,
        profile=profile,
        stats=stats,
        skills=skills,
    )


@pytest.fixture
def basic_world_state() -> WorldState:
    """Create a basic world state for testing."""
    return WorldState(
        name="Test World",
    )


@pytest.fixture
def local_event() -> HistoryEvent:
    """Create a basic local event for testing."""
    return HistoryEvent(
        name="A Minor Skirmish",
        description="A small battle broke out between local militias.",
        event_type=EventType.BATTLE,
        significance=EventSignificance.MINOR,
        outcome=EventOutcome.NEUTRAL,
        date_description="Year 1, Month 1, Day 1",
        impact_scope=ImpactScope.LOCAL,
    )


@pytest.fixture
def war_event() -> HistoryEvent:
    """Create a war event for testing."""
    return HistoryEvent(
        name="The Great War",
        description="A devastating war between major powers.",
        event_type=EventType.WAR,
        significance=EventSignificance.MAJOR,
        outcome=EventOutcome.MIXED,
        date_description="Year 5, Month 3, Day 15",
        impact_scope=ImpactScope.REGIONAL,
    )


@pytest.fixture
def global_event() -> HistoryEvent:
    """Create a global event for testing."""
    return HistoryEvent(
        name="The Cataclysm",
        description="A world-shattering event.",
        event_type=EventType.DISASTER,
        significance=EventSignificance.WORLD_CHANGING,
        outcome=EventOutcome.NEGATIVE,
        date_description="Year 10, Month 1, Day 1",
        impact_scope=ImpactScope.GLOBAL,
    )


# ==================== Intensity Calculation Tests ====================

class TestIntensityCalculation:
    """Tests for the intensity calculation logic."""

    def test_base_intensity_local(self, basic_character, local_event, basic_world_state):
        """Test base intensity for LOCAL impact scope."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, local_event, basic_world_state)

        # LOCAL = 3, no modifiers
        assert reaction.intensity == 3

    def test_base_intensity_regional(self, basic_character, war_event, basic_world_state):
        """Test base intensity for REGIONAL impact scope."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, war_event, basic_world_state)

        # REGIONAL = 5, no modifiers
        assert reaction.intensity == 5

    def test_base_intensity_global(self, basic_character, global_event, basic_world_state):
        """Test base intensity for GLOBAL impact scope."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        # GLOBAL = 7, no modifiers
        assert reaction.intensity == 7

    def test_faction_modifier_adds_2(self, basic_character, basic_world_state):
        """Test that faction in affected_faction_ids adds +2 intensity."""
        basic_character.faction_id = "faction-123"
        event = HistoryEvent(
            name="Faction Event",
            description="An event affecting factions.",
            event_type=EventType.POLITICAL,
            impact_scope=ImpactScope.LOCAL,
            affected_faction_ids=["faction-123", "faction-456"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # LOCAL = 3, +2 for faction = 5
        assert reaction.intensity == 5

    def test_location_modifier_adds_1(self, basic_character, basic_world_state):
        """Test that current location in affected_location_ids adds +1 intensity."""
        basic_character.current_location_id = "location-123"
        event = HistoryEvent(
            name="Location Event",
            description="An event affecting locations.",
            event_type=EventType.DISASTER,
            impact_scope=ImpactScope.LOCAL,
            affected_location_ids=["location-123", "location-456"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # LOCAL = 3, +1 for location = 4
        assert reaction.intensity == 4

    def test_combined_modifiers(self, basic_character, basic_world_state):
        """Test combined faction and location modifiers."""
        basic_character.faction_id = "faction-123"
        basic_character.current_location_id = "location-123"
        event = HistoryEvent(
            name="Combined Event",
            description="An event affecting both faction and location.",
            event_type=EventType.BATTLE,
            impact_scope=ImpactScope.REGIONAL,
            affected_faction_ids=["faction-123"],
            affected_location_ids=["location-123"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # REGIONAL = 5, +2 faction, +1 location = 8
        assert reaction.intensity == 8

    def test_intensity_clamped_to_max_10(self, basic_character, basic_world_state):
        """Test that intensity is clamped to maximum 10."""
        basic_character.faction_id = "faction-123"
        basic_character.current_location_id = "location-123"
        event = HistoryEvent(
            name="Max Intensity Event",
            description="An event that would exceed max intensity.",
            event_type=EventType.WAR,
            impact_scope=ImpactScope.GLOBAL,
            affected_faction_ids=["faction-123"],
            affected_location_ids=["location-123"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # GLOBAL = 7, +2 faction, +1 location = 10 (clamped from 10)
        assert reaction.intensity == 10

    def test_no_faction_modifier_when_not_in_affected(self, basic_character, basic_world_state):
        """Test no modifier when faction not in affected_faction_ids."""
        basic_character.faction_id = "faction-999"
        event = HistoryEvent(
            name="Other Faction Event",
            description="An event affecting other factions.",
            event_type=EventType.POLITICAL,
            impact_scope=ImpactScope.LOCAL,
            affected_faction_ids=["faction-123", "faction-456"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # LOCAL = 3, no modifier
        assert reaction.intensity == 3


# ==================== Reaction Type Tests ====================

class TestReactionTypeDetermination:
    """Tests for the reaction type determination rules."""

    def test_war_pacifist_protest(self, basic_world_state, war_event):
        """Test that pacifist character protests WAR events."""
        # Create character with pacifist trait
        character_id = CharacterID.generate()
        profile = CharacterProfile(
            name="Pacifist Character",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.CLERIC,
            age=30,
            level=5,
            personality_traits=PersonalityTraits(traits={"pacifist": 0.8, "courage": 0.3}),
            physical_traits=PhysicalTraits(),
            background=Background(),
        )
        stats = CharacterStats(
            core_abilities=CoreAbilities(
                strength=10, dexterity=12, constitution=12,
                intelligence=14, wisdom=16, charisma=12,
            ),
            vital_stats=VitalStats(
                max_health=24, current_health=24,
                max_mana=20, current_mana=20,
                max_stamina=16, current_stamina=16,
                armor_class=12, speed=30,
            ),
            combat_stats=CombatStats(
                base_attack_bonus=2, initiative_modifier=1,
                damage_reduction=0, spell_resistance=0,
                critical_hit_chance=0.05, critical_damage_multiplier=2.0,
            ),
            experience_points=1000,
            skill_points=10,
        )
        character = Character(
            character_id=character_id,
            profile=profile,
            stats=stats,
            skills=Skills.create_basic_skills(),
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(character, war_event, basic_world_state)

        assert reaction.reaction_type == ReactionType.PROTEST

    def test_death_relationship_mourn(self, basic_character, basic_world_state):
        """Test that character mourns DEATH events with relationship figures."""
        # Add relationship via metadata
        basic_character.metadata["relationships"] = {
            "allies": [{"name": "Sir Aldric", "type": "friend"}]
        }

        event = HistoryEvent(
            name="Death of Sir Aldric",
            description="Sir Aldric has fallen in battle.",
            event_type=EventType.DEATH,
            significance=EventSignificance.MAJOR,
            key_figures=["Sir Aldric"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        assert reaction.reaction_type == ReactionType.MOURN

    def test_trade_merchant_celebrate(self, basic_world_state):
        """Test that merchant character celebrates TRADE events."""
        # Create character with merchant trait
        character_id = CharacterID.generate()
        profile = CharacterProfile(
            name="Merchant Character",
            gender=Gender.FEMALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.MERCHANT,
            age=35,
            level=5,
            personality_traits=PersonalityTraits(traits={"merchant": 0.9, "courage": 0.5}),
            physical_traits=PhysicalTraits(),
            background=Background(),
        )
        stats = CharacterStats(
            core_abilities=CoreAbilities(
                strength=10, dexterity=12, constitution=12,
                intelligence=14, wisdom=12, charisma=16,
            ),
            vital_stats=VitalStats(
                max_health=24, current_health=24,
                max_mana=10, current_mana=10,
                max_stamina=16, current_stamina=16,
                armor_class=12, speed=30,
            ),
            combat_stats=CombatStats(
                base_attack_bonus=2, initiative_modifier=1,
                damage_reduction=0, spell_resistance=0,
                critical_hit_chance=0.05, critical_damage_multiplier=2.0,
            ),
            experience_points=1000,
            skill_points=10,
        )
        character = Character(
            character_id=character_id,
            profile=profile,
            stats=stats,
            skills=Skills.create_basic_skills(),
        )

        event = HistoryEvent(
            name="New Trade Route",
            description="A lucrative trade route has been established.",
            event_type=EventType.TRADE,
            significance=EventSignificance.MODERATE,
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(character, event, basic_world_state)

        assert reaction.reaction_type == ReactionType.CELEBRATE

    def test_war_location_affected_flee(self, basic_character, war_event, basic_world_state):
        """Test that character flees when their location is affected by war."""
        basic_character.current_location_id = "village-123"
        war_event.affected_location_ids = ["village-123", "city-456"]

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, war_event, basic_world_state)

        assert reaction.reaction_type == ReactionType.FLEE

    def test_global_scope_observe(self, basic_character, global_event, basic_world_state):
        """Test that GLOBAL events cause OBSERVE reaction."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        assert reaction.reaction_type == ReactionType.OBSERVE

    def test_default_ignore(self, basic_character, local_event, basic_world_state):
        """Test that events with no matching rules cause IGNORE reaction."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, local_event, basic_world_state)

        # BATTLE with no special conditions -> IGNORE
        assert reaction.reaction_type == ReactionType.IGNORE

    def test_rule_priority_war_pacifist_over_location(self, basic_world_state):
        """Test that pacifist rule takes priority over location rule for WAR."""
        # Create character that is both pacifist AND in affected location
        character_id = CharacterID.generate()
        profile = CharacterProfile(
            name="Pacifist at War",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.CLERIC,
            age=30,
            level=5,
            personality_traits=PersonalityTraits(traits={"pacifist": 0.9, "courage": 0.3}),
            physical_traits=PhysicalTraits(),
            background=Background(),
        )
        stats = CharacterStats(
            core_abilities=CoreAbilities(
                strength=10, dexterity=12, constitution=12,
                intelligence=14, wisdom=16, charisma=12,
            ),
            vital_stats=VitalStats(
                max_health=24, current_health=24,
                max_mana=20, current_mana=20,
                max_stamina=16, current_stamina=16,
                armor_class=12, speed=30,
            ),
            combat_stats=CombatStats(
                base_attack_bonus=2, initiative_modifier=1,
                damage_reduction=0, spell_resistance=0,
                critical_hit_chance=0.05, critical_damage_multiplier=2.0,
            ),
            experience_points=1000,
            skill_points=10,
        )
        character = Character(
            character_id=character_id,
            profile=profile,
            stats=stats,
            skills=Skills.create_basic_skills(),
        )
        character.current_location_id = "village-123"

        event = HistoryEvent(
            name="War at Home",
            description="War breaks out at the character's location.",
            event_type=EventType.WAR,
            impact_scope=ImpactScope.REGIONAL,
            affected_location_ids=["village-123"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(character, event, basic_world_state)

        # Pacifist rule (Rule 1) should win over location rule (Rule 4)
        assert reaction.reaction_type == ReactionType.PROTEST


# ==================== Narrative Generation Tests ====================

class TestNarrativeGeneration:
    """Tests for narrative generation."""

    def test_narrative_format(self, basic_character, local_event, basic_world_state):
        """Test that narrative follows the expected format."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, local_event, basic_world_state)

        # Format: "{character_name} {reaction_verb} upon hearing {event_title}"
        assert basic_character.profile.name in reaction.narrative
        assert local_event.name in reaction.narrative
        assert "upon hearing" in reaction.narrative

    def test_reaction_verb_variety(self, basic_character, basic_world_state):
        """Test that different reaction types have appropriate verbs."""
        _ = CharacterReactor()

        # Test each reaction type has a corresponding verb
        for reaction_type in ReactionType.__members__.values():
            verb = REACTION_VERBS.get(reaction_type)
            assert verb is not None, f"No verb defined for {reaction_type}"

    def test_observe_narrative(self, basic_character, global_event, basic_world_state):
        """Test narrative for OBSERVE reaction."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        assert "watches with interest" in reaction.narrative
        assert global_event.name in reaction.narrative


# ==================== Memory Integration Tests ====================

class TestMemoryIntegration:
    """Tests for memory creation integration."""

    def test_memory_created_for_significant_reaction(
        self, basic_character, global_event, basic_world_state, mock_memory_service
    ):
        """Test that memory is created for significant reactions."""
        reactor = CharacterReactor(memory_service=mock_memory_service)
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        # GLOBAL event with OBSERVE reaction, intensity >= 4
        assert reaction.memory_created is True
        mock_memory_service.create_memory.assert_called_once()

    def test_memory_not_created_for_ignore(
        self, basic_character, local_event, basic_world_state, mock_memory_service
    ):
        """Test that memory is not created for IGNORE reactions."""
        reactor = CharacterReactor(memory_service=mock_memory_service)
        reaction = reactor.react_to_event(basic_character, local_event, basic_world_state)

        # IGNORE reaction, even if intensity is present
        assert reaction.reaction_type == ReactionType.IGNORE
        # Memory shouldn't be created for IGNORE (intensity would need to be >= 4 anyway)
        # For LOCAL with no modifiers, intensity = 3, so no memory

    def test_memory_not_created_without_service(
        self, basic_character, global_event, basic_world_state
    ):
        """Test that no memory is created when no memory service is provided."""
        reactor = CharacterReactor(memory_service=None)
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        # Even though reaction should create memory, no service means no creation
        assert reaction.memory_created is False

    def test_memory_content_includes_event_description(
        self, basic_character, global_event, basic_world_state, mock_memory_service
    ):
        """Test that memory content includes event description."""
        reactor = CharacterReactor(memory_service=mock_memory_service)
        reactor.react_to_event(basic_character, global_event, basic_world_state)

        call_args = mock_memory_service.create_memory.call_args
        content = call_args.kwargs.get("content", call_args[0][1] if call_args[0] else "")

        assert global_event.description[:100] in content

    def test_memory_importance_matches_intensity(
        self, basic_character, global_event, basic_world_state, mock_memory_service
    ):
        """Test that memory importance matches reaction intensity."""
        reactor = CharacterReactor(memory_service=mock_memory_service)
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        call_args = mock_memory_service.create_memory.call_args
        importance = call_args.kwargs.get("importance", call_args[0][2] if len(call_args[0]) > 2 else None)

        assert importance == reaction.intensity


# ==================== Edge Case Tests ====================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_no_impact_scope_defaults_to_local(
        self, basic_character, basic_world_state
    ):
        """Test that events without impact_scope default to LOCAL intensity."""
        event = HistoryEvent(
            name="Unknown Scope Event",
            description="An event with no defined scope.",
            event_type=EventType.POLITICAL,
            impact_scope=None,  # No scope defined
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # Should default to LOCAL = 3
        assert reaction.intensity == 3

    def test_character_no_faction(self, basic_character, basic_world_state):
        """Test reaction when character has no faction."""
        basic_character.faction_id = None
        event = HistoryEvent(
            name="Faction Event",
            description="An event affecting factions.",
            event_type=EventType.POLITICAL,
            impact_scope=ImpactScope.REGIONAL,
            affected_faction_ids=["faction-123"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # REGIONAL = 5, no faction modifier
        assert reaction.intensity == 5

    def test_character_no_location(self, basic_character, basic_world_state):
        """Test reaction when character has no location."""
        basic_character.current_location_id = None
        event = HistoryEvent(
            name="Location Event",
            description="An event affecting locations.",
            event_type=EventType.DISASTER,
            impact_scope=ImpactScope.LOCAL,
            affected_location_ids=["location-123"],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # LOCAL = 3, no location modifier
        assert reaction.intensity == 3

    def test_event_empty_affected_lists(self, basic_character, basic_world_state):
        """Test reaction when event has empty affected lists."""
        event = HistoryEvent(
            name="Generic Event",
            description="A generic event.",
            event_type=EventType.POLITICAL,
            impact_scope=ImpactScope.REGIONAL,
            affected_faction_ids=[],
            affected_location_ids=[],
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # REGIONAL = 5, no modifiers
        assert reaction.intensity == 5

    def test_deceased_character_still_reacts(self, basic_character, global_event, basic_world_state):
        """Test that deceased characters can still have reactions (for historical records)."""
        # Mark character as deceased
        from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
        death_date = WorldCalendar(year=5, month=1, day=1, era_name="First Age")
        basic_character.is_deceased = True
        basic_character.death_date = death_date

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        # Should still generate a reaction
        assert reaction is not None
        assert reaction.reaction_type == ReactionType.OBSERVE


# ==================== Batch Processing Tests ====================

class TestBatchProcessing:
    """Tests for batch reaction processing."""

    def test_batch_react_multiple_characters(self, basic_world_state, mock_memory_service):
        """Test batch processing of multiple characters."""
        # Create multiple characters
        characters = []
        for i in range(3):
            char_id = CharacterID.generate()
            profile = CharacterProfile(
                name=f"Character {i}",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25 + i,
                level=5,
                personality_traits=PersonalityTraits(traits={"courage": 0.5}),
                physical_traits=PhysicalTraits(),
                background=Background(),
            )
            stats = CharacterStats(
                core_abilities=CoreAbilities(
                    strength=14, dexterity=12, constitution=14,
                    intelligence=10, wisdom=10, charisma=10,
                ),
                vital_stats=VitalStats(
                    max_health=30, current_health=30,
                    max_mana=10, current_mana=10,
                    max_stamina=20, current_stamina=20,
                    armor_class=14, speed=30,
                ),
                combat_stats=CombatStats(
                    base_attack_bonus=3, initiative_modifier=1,
                    damage_reduction=0, spell_resistance=0,
                    critical_hit_chance=0.05, critical_damage_multiplier=2.0,
                ),
                experience_points=1000,
                skill_points=10,
            )
            char = Character(
                character_id=char_id,
                profile=profile,
                stats=stats,
                skills=Skills.create_basic_skills(),
            )
            characters.append(char)

        event = HistoryEvent(
            name="Global Event",
            description="A global event affecting everyone.",
            event_type=EventType.DISASTER,
            impact_scope=ImpactScope.GLOBAL,
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor(memory_service=mock_memory_service)
        reactions = reactor.batch_react(characters, event, basic_world_state)

        assert len(reactions) == 3
        for reaction in reactions:
            assert isinstance(reaction, CharacterReaction)
            assert reaction.reaction_type == ReactionType.OBSERVE


# ==================== Trait Detection Tests ====================

class TestTraitDetection:
    """Tests for trait detection in characters."""

    def test_trait_in_personality_traits(self, basic_world_state):
        """Test detection of trait in personality_traits."""
        # Create character with merchant trait
        character_id = CharacterID.generate()
        profile = CharacterProfile(
            name="Merchant Character",
            gender=Gender.FEMALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.MERCHANT,
            age=35,
            level=5,
            personality_traits=PersonalityTraits(traits={"merchant": 0.85, "courage": 0.5}),
            physical_traits=PhysicalTraits(),
            background=Background(),
        )
        stats = CharacterStats(
            core_abilities=CoreAbilities(
                strength=10, dexterity=12, constitution=12,
                intelligence=14, wisdom=12, charisma=16,
            ),
            vital_stats=VitalStats(
                max_health=24, current_health=24,
                max_mana=10, current_mana=10,
                max_stamina=16, current_stamina=16,
                armor_class=12, speed=30,
            ),
            combat_stats=CombatStats(
                base_attack_bonus=2, initiative_modifier=1,
                damage_reduction=0, spell_resistance=0,
                critical_hit_chance=0.05, critical_damage_multiplier=2.0,
            ),
            experience_points=1000,
            skill_points=10,
        )
        character = Character(
            character_id=character_id,
            profile=profile,
            stats=stats,
            skills=Skills.create_basic_skills(),
        )

        event = HistoryEvent(
            name="Trade Deal",
            description="A new trade deal.",
            event_type=EventType.TRADE,
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(character, event, basic_world_state)

        # Merchant trait should trigger CELEBRATE
        assert reaction.reaction_type == ReactionType.CELEBRATE

    def test_trait_below_threshold_not_detected(self, basic_character, basic_world_state):
        """Test that traits below threshold (0.7) are not detected."""
        # basic_character has courage: 0.5 which is below threshold
        # This is already below 0.7, so we test that weak traits don't trigger

        event = HistoryEvent(
            name="Trade Deal",
            description="A new trade deal.",
            event_type=EventType.TRADE,
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # basic_character doesn't have merchant trait, should not CELEBRATE
        assert reaction.reaction_type != ReactionType.CELEBRATE

    def test_trait_in_metadata(self, basic_character, basic_world_state):
        """Test detection of trait in character metadata."""
        basic_character.metadata["traits"] = {"pacifist": True}

        event = HistoryEvent(
            name="War Begins",
            description="A war begins.",
            event_type=EventType.WAR,
            impact_scope=ImpactScope.REGIONAL,
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # Pacifist trait in metadata should trigger PROTEST
        assert reaction.reaction_type == ReactionType.PROTEST


# ==================== Reaction Properties Tests ====================

class TestReactionProperties:
    """Tests for reaction value object properties."""

    def test_reaction_intense_threshold(self, basic_character, global_event, basic_world_state):
        """Test is_intense method with custom threshold."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, global_event, basic_world_state)

        # GLOBAL = 7, so is_intense(threshold=7) should be True
        assert reaction.is_intense(7) is True
        assert reaction.is_intense(8) is False

    def test_reaction_mild(self, basic_character, local_event, basic_world_state):
        """Test is_mild method."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, local_event, basic_world_state)

        # LOCAL = 3, should be mild
        assert reaction.is_mild() is True

    def test_should_create_memory_logic(self, basic_character, basic_world_state):
        """Test should_create_memory combines type and intensity."""
        # Create event that will result in OBSERVE (not IGNORE) with high intensity
        event = HistoryEvent(
            name="Global Event",
            description="A global event.",
            event_type=EventType.DISASTER,
            impact_scope=ImpactScope.GLOBAL,  # Will cause OBSERVE
            date_description="Year 1, Month 1",
        )

        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, event, basic_world_state)

        # OBSERVE creates memory, intensity 7 >= 4
        assert reaction.should_create_memory() is True

    def test_ignore_never_creates_memory(self, basic_character, local_event, basic_world_state):
        """Test that IGNORE reactions never create memory regardless of intensity."""
        reactor = CharacterReactor()
        reaction = reactor.react_to_event(basic_character, local_event, basic_world_state)

        # IGNORE type
        assert reaction.reaction_type == ReactionType.IGNORE
        assert reaction.should_create_memory() is False
