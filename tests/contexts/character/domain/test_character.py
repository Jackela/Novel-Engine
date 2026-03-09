"""
Tests for Character Domain Aggregate Module

Coverage targets:
- Inventory management
- Skill updates
- Relationship management
- State transitions
"""

from datetime import datetime

import pytest

from src.contexts.character.domain.aggregates.character import Character
from src.contexts.character.domain.events.character_events import (
    CharacterCreated,
)
from src.contexts.character.domain.value_objects.character_goal import (
    CharacterGoal,
    GoalStatus,
    GoalUrgency,
)
from src.contexts.character.domain.value_objects.character_id import CharacterID
from src.contexts.character.domain.value_objects.character_memory import CharacterMemory

# Note: Using MemoryType from context_models instead of core.data_models
from src.contexts.character.domain.value_objects.character_profile import (
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
)
from src.contexts.character.domain.value_objects.character_stats import (
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from src.contexts.character.domain.value_objects.skills import (
    Skills,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def character_id():
    """Create a test character ID."""
    return CharacterID.generate()


@pytest.fixture
def character_profile():
    """Create a test character profile."""
    return CharacterProfile.create_default(
        name="Test Character",
        gender=Gender.MALE,
        race=CharacterRace.HUMAN,
        character_class=CharacterClass.FIGHTER,
        age=25,
    )


@pytest.fixture
def character_stats():
    """Create test character stats."""
    core_abilities = CoreAbilities(
        strength=14,
        dexterity=12,
        constitution=13,
        intelligence=10,
        wisdom=11,
        charisma=10,
    )

    vital_stats = VitalStats(
        max_health=30,
        current_health=30,
        max_mana=10,
        current_mana=10,
        max_stamina=20,
        current_stamina=20,
        armor_class=15,
        speed=30,
    )

    combat_stats = CombatStats(
        base_attack_bonus=2,
        initiative_modifier=1,
        damage_reduction=0,
        spell_resistance=0,
        critical_hit_chance=0.05,
        critical_damage_multiplier=2.0,
    )

    return CharacterStats(
        core_abilities=core_abilities,
        vital_stats=vital_stats,
        combat_stats=combat_stats,
        experience_points=0,
        skill_points=5,
    )


@pytest.fixture
def character_skills():
    """Create test character skills."""
    return Skills.create_basic_skills()


@pytest.fixture
def character(character_id, character_profile, character_stats, character_skills):
    """Create a test character."""
    return Character(
        character_id=character_id,
        profile=character_profile,
        stats=character_stats,
        skills=character_skills,
    )


class TestCharacterCreation:
    """Tests for character creation."""

    def test_character_creation_success(self, character):
        """Test successful character creation."""
        assert character.character_id is not None
        assert character.profile.name == "Test Character"
        assert character.profile.level == 1
        assert character.stats.vital_stats.current_health == 30
        assert character.version == 1
        assert character.is_deceased is False

    def test_character_creation_event(self, character):
        """Test character creation generates event."""
        events = character.get_events()

        # Should have CharacterCreated event
        created_events = [e for e in events if isinstance(e, CharacterCreated)]
        assert len(created_events) == 1
        assert created_events[0].character_name == "Test Character"

    def test_character_validation_level(self):
        """Test CharacterProfile validation for level < 1."""
        # CharacterProfile validates level in __post_init__
        from src.contexts.character.domain.value_objects.character_profile import (
            Background,
            PersonalityTraits,
            PhysicalTraits,
        )

        # Cannot create a CharacterProfile with level 0
        with pytest.raises(ValueError, match="Level must be between 1 and 100"):
            CharacterProfile(
                name="Invalid",
                gender=Gender.MALE,
                race=CharacterRace.HUMAN,
                character_class=CharacterClass.FIGHTER,
                age=25,
                level=0,  # Invalid level
                physical_traits=PhysicalTraits(),
                personality_traits=PersonalityTraits(traits={"neutral": 0.5}),
                background=Background(),
            )


class TestCharacterEvents:
    """Tests for character events."""

    def test_get_events(self, character):
        """Test getting events."""
        events = character.get_events()
        assert isinstance(events, list)
        assert len(events) > 0

    def test_clear_events(self, character):
        """Test clearing events."""
        assert len(character.get_events()) > 0

        character.clear_events()

        assert len(character.get_events()) == 0


class TestCharacterStatsOperations:
    """Tests for stats operations."""

    def test_update_stats_success(self, character):
        """Test successful stats update."""
        new_vital = VitalStats(
            max_health=35,
            current_health=35,
            max_mana=12,
            current_mana=12,
            max_stamina=22,
            current_stamina=22,
            armor_class=16,
            speed=30,
        )

        new_stats = CharacterStats(
            core_abilities=character.stats.core_abilities,
            vital_stats=new_vital,
            combat_stats=character.stats.combat_stats,
            experience_points=100,
            skill_points=5,
        )

        character.update_stats(new_stats)

        assert character.stats.vital_stats.max_health == 35
        assert character.version == 2

    def test_update_stats_health_limit(self, character):
        """Test stats update enforces health change limit."""
        # Try to lose more than half health
        new_vital = VitalStats(
            max_health=30,
            current_health=5,  # Losing 25 of 30 health (>50%)
            max_mana=10,
            current_mana=10,
            max_stamina=20,
            current_stamina=20,
            armor_class=15,
            speed=30,
        )

        new_stats = CharacterStats(
            core_abilities=character.stats.core_abilities,
            vital_stats=new_vital,
            combat_stats=character.stats.combat_stats,
            experience_points=0,
            skill_points=5,
        )

        with pytest.raises(ValueError, match="Cannot lose more than half health"):
            character.update_stats(new_stats)

    def test_heal(self, character):
        """Test healing character."""
        # First damage the character by creating damaged stats
        from src.contexts.character.domain.value_objects.character_stats import (
            CharacterStats,
            VitalStats,
        )

        damaged_vital = VitalStats(
            max_health=character.stats.vital_stats.max_health,
            current_health=15,  # Damaged
            max_mana=character.stats.vital_stats.max_mana,
            current_mana=character.stats.vital_stats.current_mana,
            max_stamina=character.stats.vital_stats.max_stamina,
            current_stamina=character.stats.vital_stats.current_stamina,
            armor_class=character.stats.vital_stats.armor_class,
            speed=character.stats.vital_stats.speed,
        )

        damaged_stats = CharacterStats(
            core_abilities=character.stats.core_abilities,
            vital_stats=damaged_vital,
            combat_stats=character.stats.combat_stats,
            experience_points=character.stats.experience_points,
            skill_points=character.stats.skill_points,
        )

        character.stats = damaged_stats

        character.heal(10)

        assert character.stats.vital_stats.current_health == 25

    def test_heal_max_cap(self, character):
        """Test healing doesn't exceed max health."""
        # Character starts with full health in fixture, damage first then heal
        character.take_damage(10)  # Now at 20

        character.heal(20)  # Would exceed max of 30

        assert character.stats.vital_stats.current_health == 30

    def test_take_damage(self, character):
        """Test taking damage."""
        character.take_damage(10)

        assert character.stats.vital_stats.current_health == 20


class TestCharacterSkillOperations:
    """Tests for skill operations."""

    def test_update_skills_success(self, character, character_skills):
        """Test successful skills update."""
        new_skills = character_skills  # Use same skills for simplicity

        character.update_skills(new_skills)

        assert character.version == 2


class TestCharacterMemoryOperations:
    """Tests for memory operations."""

    def test_add_memory(self, character):
        """Test adding memory."""
        memory = CharacterMemory(
            memory_id="mem123",
            content="Test memory",
            importance=5,
            tags=("test", "memory"),
            timestamp=datetime.now(),
        )

        character.add_memory(memory)

        assert len(character.memories) == 1
        assert character.memories[0].content == "Test memory"

    def test_add_memory_invalid_type(self, character):
        """Test adding non-memory raises error."""
        with pytest.raises(TypeError):
            character.add_memory("not a memory")

    def test_get_core_memories(self, character):
        """Test getting core memories."""
        memory1 = CharacterMemory(
            memory_id="mem1",
            content="Memory 1",
            importance=5,
            tags=("foundational",),
            timestamp=datetime.now(),
        )
        memory2 = CharacterMemory(
            memory_id="mem2",
            content="Memory 2",
            importance=9,  # Core memory (> 8)
            tags=("achievement",),
            timestamp=datetime.now(),
        )

        character.add_memory(memory1)
        character.add_memory(memory2)

        core_memories = character.get_core_memories()
        assert len(core_memories) == 1
        assert core_memories[0].memory_id == "mem2"


class TestCharacterGoalOperations:
    """Tests for goal operations."""

    def test_add_goal(self, character):
        """Test adding goal."""
        goal = CharacterGoal(
            goal_id="goal1",
            description="Defeat the dragon - Kill the red dragon",
            urgency=GoalUrgency.HIGH,
            status=GoalStatus.ACTIVE,
        )

        character.add_goal(goal)

        assert len(character.goals) == 1
        assert "Defeat the dragon" in character.goals[0].description
        assert character.goals[0].is_urgent() is True

    def test_add_goal_duplicate(self, character):
        """Test adding duplicate goal raises error."""
        goal = CharacterGoal(
            goal_id="goal1",
            description="Goal - Description",
        )

        character.add_goal(goal)

        with pytest.raises(ValueError, match="already exists"):
            character.add_goal(goal)

    def test_complete_goal(self, character):
        """Test completing goal."""
        goal = CharacterGoal(
            goal_id="goal1",
            description="Goal - Description",
            status=GoalStatus.ACTIVE,
        )

        character.add_goal(goal)
        completed = character.complete_goal("goal1")

        assert completed.is_completed() is True

    def test_get_urgent_goals(self, character):
        """Test getting urgent goals."""
        urgent_goal = CharacterGoal(
            goal_id="goal1",
            description="Urgent goal",
            urgency=GoalUrgency.CRITICAL,
            status=GoalStatus.ACTIVE,
        )
        normal_goal = CharacterGoal(
            goal_id="goal2",
            description="Normal goal",
            urgency=GoalUrgency.LOW,
            status=GoalStatus.ACTIVE,
        )

        character.add_goal(urgent_goal)
        character.add_goal(normal_goal)

        urgent = character.get_urgent_goals()
        assert len(urgent) == 1
        assert urgent[0].goal_id == "goal1"


class TestCharacterInventoryOperations:
    """Tests for inventory operations."""

    def test_give_item(self, character):
        """Test giving item to character."""
        character.give_item("sword_001")

        assert "sword_001" in character.inventory
        assert character.get_inventory_count() == 1

    def test_give_item_duplicate(self, character):
        """Test giving duplicate item raises error."""
        character.give_item("sword_001")

        with pytest.raises(ValueError, match="already in inventory"):
            character.give_item("sword_001")

    def test_remove_item(self, character):
        """Test removing item from inventory."""
        character.give_item("sword_001")
        result = character.remove_item("sword_001")

        assert result is True
        assert "sword_001" not in character.inventory

    def test_has_item(self, character):
        """Test checking if character has item."""
        character.give_item("sword_001")

        assert character.has_item("sword_001") is True
        assert character.has_item("shield_001") is False


class TestCharacterFactionOperations:
    """Tests for faction operations."""

    def test_join_faction(self, character):
        """Test joining faction."""
        character.join_faction("faction_001")

        assert character.faction_id == "faction_001"
        assert character.is_in_faction() is True

    def test_leave_faction(self, character):
        """Test leaving faction."""
        character.join_faction("faction_001")
        result = character.leave_faction()

        assert result is True
        assert character.faction_id is None


class TestCharacterLifecycle:
    """Tests for character lifecycle."""

    def test_is_alive(self, character):
        """Test checking if character is alive."""
        assert character.is_alive() is True

        # Apply damage to reduce health to 0
        character.take_damage(character.stats.vital_stats.max_health)
        assert character.is_alive() is False

    def test_mark_deceased(self, character):
        """Test marking character as deceased."""
        from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

        death_date = WorldCalendar(year=1000, month=1, day=1, era_name="Third Age")
        character.mark_deceased(death_date)

        assert character.is_deceased is True
        assert character.death_date == death_date


class TestCharacterFactory:
    """Tests for character factory method."""

    def test_create_new_character(self):
        """Test creating new character with defaults."""
        core_abilities = CoreAbilities(
            strength=14,
            dexterity=12,
            constitution=13,
            intelligence=10,
            wisdom=11,
            charisma=10,
        )

        character = Character.create_new_character(
            name="New Character",
            gender=Gender.FEMALE,
            race=CharacterRace.ELF,
            character_class=CharacterClass.WIZARD,
            age=120,
            core_abilities=core_abilities,
        )

        assert character.profile.name == "New Character"
        assert character.profile.level == 1
