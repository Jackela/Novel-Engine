#!/usr/bin/env python3
"""
Unit tests for Character Aggregate Root

Comprehensive test suite for the Character aggregate root business logic,
covering character management, stat updates, level progression, and domain events.
"""

# Mock problematic dependencies
import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

# Mock the aioredis dependency to avoid import errors

pytestmark = pytest.mark.unit

sys.modules["aioredis"] = MagicMock()

# Mock the event_bus module to avoid aioredis dependency
event_bus_mock = MagicMock()
event_mock = MagicMock()
event_mock.return_value = Mock()
event_bus_mock.Event = event_mock

# Save original module if it exists
_original_event_bus = sys.modules.get("src.events.event_bus")

sys.modules["src.events.event_bus"] = event_bus_mock

# Now import the actual modules we're testing
from src.contexts.character.domain.aggregates.character import Character
from src.contexts.character.domain.value_objects.character_id import CharacterID
from src.contexts.character.domain.value_objects.character_profile import (
    Background,
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
    PersonalityTraits,
    PhysicalTraits,
)
from src.contexts.character.domain.value_objects.character_stats import (
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from src.contexts.character.domain.value_objects.skills import (
    ProficiencyLevel,
    Skill,
    SkillCategory,
    Skills,
)

# Restore original module to avoid polluting other tests
if _original_event_bus is not None:
    sys.modules["src.events.event_bus"] = _original_event_bus
else:
    del sys.modules["src.events.event_bus"]


class TestCharacterAggregate:
    """Test suite for Character aggregate root."""

    @pytest.fixture
    def sample_core_abilities(self) -> CoreAbilities:
        """Create sample core abilities for testing."""
        return CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

    @pytest.fixture
    def sample_vital_stats(self) -> VitalStats:
        """Create sample vital stats for testing."""
        return VitalStats(
            max_health=36,  # 20 + 16 constitution
            current_health=36,
            max_mana=15,  # 10 + 5 for non-magic classes
            current_mana=15,
            max_stamina=31,  # 15 + 16 constitution
            current_stamina=31,
            armor_class=12,  # 10 + 2 dex modifier
            speed=30,
        )

    @pytest.fixture
    def sample_combat_stats(self) -> CombatStats:
        """Create sample combat stats for testing."""
        return CombatStats(
            base_attack_bonus=0,
            initiative_modifier=2,  # dex modifier
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        )

    @pytest.fixture
    def sample_character_stats(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ) -> CharacterStats:
        """Create sample character stats for testing."""
        return CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=sample_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=0,
            skill_points=5,
        )

    @pytest.fixture
    def sample_character_profile(self) -> CharacterProfile:
        """Create sample character profile for testing."""
        return CharacterProfile(
            name="Test Warrior",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=PhysicalTraits(
                height_cm=180, weight_kg=75, hair_color="brown", eye_color="blue"
            ),
            personality_traits=PersonalityTraits(
                traits={
                    "courage": 0.8,
                    "intelligence": 0.6,
                    "charisma": 0.5,
                    "loyalty": 0.9,
                }
            ),
            background=Background(),
        )

    @pytest.fixture
    def sample_skills(self) -> Skills:
        """Create sample skills for testing."""
        # Mock the Skills.create_basic_skills() method
        combat_skill = Skill(
            name="Melee Combat",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.NOVICE,
            modifier=0,
        )

        physical_skill = Skill(
            name="Athletics",
            category=SkillCategory.PHYSICAL,
            proficiency_level=ProficiencyLevel.APPRENTICE,
            modifier=1,
        )

        # Create a mock Skills object
        skills = Mock()
        skills.skill_groups = {
            SkillCategory.COMBAT: [combat_skill],
            SkillCategory.PHYSICAL: [physical_skill],
        }
        skills.get_skills_by_category = Mock(
            side_effect=lambda cat: skills.skill_groups.get(cat, [])
        )
        skills.get_skill_summary = Mock(
            return_value={"total_skills": 2, "trained_skills": 2}
        )

        return skills

    @pytest.fixture
    def sample_character(
        self, sample_character_profile, sample_character_stats, sample_skills
    ) -> Character:
        """Create a test Character instance."""
        return Character(
            character_id=CharacterID.generate(),
            profile=sample_character_profile,
            stats=sample_character_stats,
            skills=sample_skills,
        )

    # ==================== Initialization and Validation Tests ====================

    @pytest.mark.unit
    def test_character_initialization_success(
        self, sample_character_profile, sample_character_stats, sample_skills
    ):
        """Test successful character initialization."""
        character = Character(
            character_id=CharacterID.generate(),
            profile=sample_character_profile,
            stats=sample_character_stats,
            skills=sample_skills,
        )

        assert character.character_id is not None
        assert character.profile == sample_character_profile
        assert character.stats == sample_character_stats
        assert character.skills == sample_skills
        assert character.version == 1
        assert isinstance(character.created_at, datetime)
        assert isinstance(character.updated_at, datetime)
        assert len(character._events) == 1  # Creation event
        assert character._events[0].__class__.__name__ == "CharacterCreated"

    @pytest.mark.unit
    def test_character_validation_invalid_level(
        self, sample_character_profile, sample_character_stats, sample_skills
    ):
        """Test character validation with invalid level."""
        # Test that creating a profile with invalid level raises error immediately
        with pytest.raises(ValueError) as exc_info:
            CharacterProfile(
                name=sample_character_profile.name,
                gender=sample_character_profile.gender,
                race=sample_character_profile.race,
                character_class=sample_character_profile.character_class,
                age=sample_character_profile.age,
                level=0,  # Invalid level
                physical_traits=sample_character_profile.physical_traits,
                personality_traits=sample_character_profile.personality_traits,
                background=sample_character_profile.background,
            )
        assert "Level must be between 1 and 100" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_validation_insufficient_health(
        self, sample_character_profile, sample_character_stats, sample_skills
    ):
        """Test character validation with insufficient health for constitution and level."""
        # Create stats with too low health
        low_health_vital_stats = VitalStats(
            max_health=10,  # Too low for constitution 16 + level 1
            current_health=10,
            max_mana=15,
            current_mana=15,
            max_stamina=31,
            current_stamina=31,
            armor_class=12,
            speed=30,
        )

        low_health_stats = CharacterStats(
            core_abilities=sample_character_stats.core_abilities,
            vital_stats=low_health_vital_stats,
            combat_stats=sample_character_stats.combat_stats,
            experience_points=0,
            skill_points=5,
        )

        with pytest.raises(ValueError) as exc_info:
            Character(
                character_id=CharacterID.generate(),
                profile=sample_character_profile,
                stats=low_health_stats,
                skills=sample_skills,
            )
        assert "Character health too low" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_validation_racial_abilities(
        self, sample_character_stats, sample_skills
    ):
        """Test racial ability validation."""
        # Create a dwarf with too low constitution
        low_con_abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=10,  # Too low for dwarf
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

        dwarf_profile = CharacterProfile(
            name="Test Dwarf",
            gender=Gender.MALE,
            race=CharacterRace.DWARF,  # Requires constitution >= 12
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=PhysicalTraits(),
            personality_traits=PersonalityTraits(
                traits={"courage": 0.5, "determination": 0.6, "loyalty": 0.7}
            ),
            background=Background(),
        )

        dwarf_stats = CharacterStats(
            core_abilities=low_con_abilities,
            vital_stats=sample_character_stats.vital_stats,
            combat_stats=sample_character_stats.combat_stats,
            experience_points=0,
            skill_points=5,
        )

        with pytest.raises(ValueError) as exc_info:
            Character(
                character_id=CharacterID.generate(),
                profile=dwarf_profile,
                stats=dwarf_stats,
                skills=sample_skills,
            )
        assert "Dwarf should have constitution >= 12" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_validation_class_skills(
        self, sample_character_profile, sample_character_stats
    ):
        """Test class skill validation."""
        # Create skills without required categories for fighter
        invalid_skills = Mock()
        invalid_skills.skill_groups = {
            SkillCategory.MAGICAL: [Mock()]  # Fighter needs combat and physical
        }
        invalid_skills.get_skills_by_category = Mock(
            side_effect=lambda cat: invalid_skills.skill_groups.get(cat, [])
        )

        with pytest.raises(ValueError) as exc_info:
            Character(
                character_id=CharacterID.generate(),
                profile=sample_character_profile,
                stats=sample_character_stats,
                skills=invalid_skills,
            )
        assert "Fighter should have combat skills" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_validation_age_consistency(
        self, sample_character_stats, sample_skills
    ):
        """Test age consistency validation."""
        # Create high-level character with too young age
        high_level_profile = CharacterProfile(
            name="Test Veteran",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=15,  # Too young for high level
            level=20,  # High level character
            physical_traits=PhysicalTraits(),
            personality_traits=PersonalityTraits(
                traits={"courage": 0.5, "wisdom": 0.3, "experience": 0.8}
            ),
            background=Background(),
        )

        with pytest.raises(ValueError) as exc_info:
            Character(
                character_id=CharacterID.generate(),
                profile=high_level_profile,
                stats=sample_character_stats,
                skills=sample_skills,
            )
        assert "Character too young (15) for level 20" in str(exc_info.value)

    # ==================== Profile Management Tests ====================

    @pytest.mark.unit
    def test_update_profile_success(self, sample_character):
        """Test successful profile update."""
        initial_version = sample_character.version
        initial_events = len(sample_character._events)

        # Create new profile with updated name
        new_profile = CharacterProfile(
            name="Updated Warrior",
            gender=sample_character.profile.gender,
            race=sample_character.profile.race,
            character_class=sample_character.profile.character_class,
            age=sample_character.profile.age,
            level=sample_character.profile.level,
            physical_traits=sample_character.profile.physical_traits,
            personality_traits=sample_character.profile.personality_traits,
            background=sample_character.profile.background,
        )

        sample_character.update_profile(new_profile)

        assert sample_character.profile.name == "Updated Warrior"
        assert sample_character.version == initial_version + 1
        assert len(sample_character._events) == initial_events + 1
        assert sample_character._events[-1].__class__.__name__ == "CharacterUpdated"

    @pytest.mark.unit
    def test_update_profile_validation_failure_rollback(self, sample_character):
        """Test profile update rollback on validation failure."""
        initial_profile = sample_character.profile
        initial_version = sample_character.version

        # Create a valid profile individually, but one that would fail Character validation
        # due to age inconsistency (too young for high level)
        invalid_profile = CharacterProfile(
            name=sample_character.profile.name,
            gender=sample_character.profile.gender,
            race=sample_character.profile.race,
            character_class=sample_character.profile.character_class,
            age=15,  # Too young for level requirements
            level=20,  # High level character - violates age consistency
            physical_traits=sample_character.profile.physical_traits,
            personality_traits=sample_character.profile.personality_traits,
            background=sample_character.profile.background,
        )

        with pytest.raises(ValueError):
            sample_character.update_profile(invalid_profile)

        # Should rollback to original state
        assert sample_character.profile == initial_profile
        assert sample_character.version == initial_version

    # ==================== Statistics Management Tests ====================

    @pytest.mark.unit
    def test_update_stats_success(self, sample_character):
        """Test successful stats update."""
        initial_version = sample_character.version
        initial_health = sample_character.stats.vital_stats.current_health

        # Create new stats with updated health
        new_vital_stats = VitalStats(
            max_health=sample_character.stats.vital_stats.max_health,
            current_health=initial_health - 5,  # Lost some health
            max_mana=sample_character.stats.vital_stats.max_mana,
            current_mana=sample_character.stats.vital_stats.current_mana,
            max_stamina=sample_character.stats.vital_stats.max_stamina,
            current_stamina=sample_character.stats.vital_stats.current_stamina,
            armor_class=sample_character.stats.vital_stats.armor_class,
            speed=sample_character.stats.vital_stats.speed,
        )

        new_stats = CharacterStats(
            core_abilities=sample_character.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=sample_character.stats.combat_stats,
            experience_points=sample_character.stats.experience_points,
            skill_points=sample_character.stats.skill_points,
        )

        sample_character.update_stats(new_stats)

        assert sample_character.stats.vital_stats.current_health == initial_health - 5
        assert sample_character.version == initial_version + 1

    @pytest.mark.unit
    def test_update_stats_excessive_health_loss_fails(self, sample_character):
        """Test stats update fails when losing too much health at once."""
        initial_health = sample_character.stats.vital_stats.current_health

        # Try to lose more than half health in one update
        new_vital_stats = VitalStats(
            max_health=sample_character.stats.vital_stats.max_health,
            current_health=initial_health // 3,  # Lose more than half
            max_mana=sample_character.stats.vital_stats.max_mana,
            current_mana=sample_character.stats.vital_stats.current_mana,
            max_stamina=sample_character.stats.vital_stats.max_stamina,
            current_stamina=sample_character.stats.vital_stats.current_stamina,
            armor_class=sample_character.stats.vital_stats.armor_class,
            speed=sample_character.stats.vital_stats.speed,
        )

        new_stats = CharacterStats(
            core_abilities=sample_character.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=sample_character.stats.combat_stats,
            experience_points=sample_character.stats.experience_points,
            skill_points=sample_character.stats.skill_points,
        )

        with pytest.raises(ValueError) as exc_info:
            sample_character.update_stats(new_stats)
        assert "Cannot lose more than half health" in str(exc_info.value)

    @pytest.mark.unit
    def test_update_stats_exceed_maximum_values_fails(self, sample_character):
        """Test stats update fails when current values exceed maximums."""
        # Create valid vital stats first, then modify the object to bypass validation
        new_vital_stats = VitalStats(
            max_health=sample_character.stats.vital_stats.max_health,
            current_health=sample_character.stats.vital_stats.current_health,
            max_mana=sample_character.stats.vital_stats.max_mana,
            current_mana=sample_character.stats.vital_stats.current_mana,
            max_stamina=sample_character.stats.vital_stats.max_stamina,
            current_stamina=sample_character.stats.vital_stats.current_stamina,
            armor_class=sample_character.stats.vital_stats.armor_class,
            speed=sample_character.stats.vital_stats.speed,
        )

        # Bypass validation by modifying the object directly
        object.__setattr__(
            new_vital_stats, "current_health", new_vital_stats.max_health + 10
        )

        new_stats = CharacterStats(
            core_abilities=sample_character.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=sample_character.stats.combat_stats,
            experience_points=sample_character.stats.experience_points,
            skill_points=sample_character.stats.skill_points,
        )

        with pytest.raises(ValueError) as exc_info:
            sample_character.update_stats(new_stats)
        # Now the Character's validation should catch it
        assert "Current values cannot exceed maximum values" in str(exc_info.value)

    @pytest.mark.unit
    def test_update_stats_rollback_on_validation_failure(self, sample_character):
        """Test stats update rollback on validation failure."""
        initial_stats = sample_character.stats
        initial_version = sample_character.version

        # Create stats that will fail validation (health too low for constitution)
        invalid_vital_stats = VitalStats(
            max_health=5,  # Too low for constitution
            current_health=5,
            max_mana=sample_character.stats.vital_stats.max_mana,
            current_mana=sample_character.stats.vital_stats.current_mana,
            max_stamina=sample_character.stats.vital_stats.max_stamina,
            current_stamina=sample_character.stats.vital_stats.current_stamina,
            armor_class=sample_character.stats.vital_stats.armor_class,
            speed=sample_character.stats.vital_stats.speed,
        )

        invalid_stats = CharacterStats(
            core_abilities=sample_character.stats.core_abilities,
            vital_stats=invalid_vital_stats,
            combat_stats=sample_character.stats.combat_stats,
            experience_points=sample_character.stats.experience_points,
            skill_points=sample_character.stats.skill_points,
        )

        with pytest.raises(ValueError):
            sample_character.update_stats(invalid_stats)

        # Should rollback to original state
        assert sample_character.stats == initial_stats
        assert sample_character.version == initial_version

    # ==================== Character Operations Tests ====================

    @pytest.mark.unit
    def test_level_up_success(self, sample_character):
        """Test successful character level up."""
        initial_level = sample_character.profile.level
        initial_health = sample_character.stats.vital_stats.max_health
        initial_mana = sample_character.stats.vital_stats.max_mana
        initial_skill_points = sample_character.stats.skill_points
        initial_version = sample_character.version

        sample_character.level_up()

        assert sample_character.profile.level == initial_level + 1
        assert (
            sample_character.stats.vital_stats.max_health
            == initial_health + 10 + sample_character.stats.core_abilities.constitution
        )
        assert (
            sample_character.stats.vital_stats.max_mana
            == initial_mana + 5 + sample_character.stats.core_abilities.intelligence
        )
        assert sample_character.stats.skill_points == initial_skill_points + 5
        assert sample_character.version == initial_version + 1

    @pytest.mark.unit
    def test_level_up_at_maximum_level_fails(self, sample_character):
        """Test level up fails at maximum level."""
        # Set character to maximum level
        max_level_profile = CharacterProfile(
            name=sample_character.profile.name,
            gender=sample_character.profile.gender,
            race=sample_character.profile.race,
            character_class=sample_character.profile.character_class,
            age=sample_character.profile.age + 50,  # Appropriate age for level 100
            level=100,  # Maximum level
            physical_traits=sample_character.profile.physical_traits,
            personality_traits=sample_character.profile.personality_traits,
            background=sample_character.profile.background,
        )

        sample_character.profile = max_level_profile

        with pytest.raises(ValueError) as exc_info:
            sample_character.level_up()
        assert "Character is already at maximum level" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_heal_success(self, sample_character):
        """Test successful character healing."""
        # First damage the character
        sample_character.take_damage(10)
        damaged_health = sample_character.stats.vital_stats.current_health
        max_health = sample_character.stats.vital_stats.max_health
        initial_version = sample_character.version

        # Heal the character
        sample_character.heal(5)

        assert sample_character.stats.vital_stats.current_health == damaged_health + 5
        assert sample_character.stats.vital_stats.current_health <= max_health
        assert sample_character.version == initial_version + 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_heal_to_maximum_health(self, sample_character):
        """Test healing caps at maximum health."""
        # First damage the character
        sample_character.take_damage(5)
        max_health = sample_character.stats.vital_stats.max_health

        # Heal more than the damage taken
        sample_character.heal(100)  # Much more than needed

        assert sample_character.stats.vital_stats.current_health == max_health

    @pytest.mark.unit
    @pytest.mark.fast
    def test_heal_zero_amount_fails(self, sample_character):
        """Test healing with zero or negative amount fails."""
        with pytest.raises(ValueError) as exc_info:
            sample_character.heal(0)
        assert "Heal amount must be positive" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            sample_character.heal(-5)
        assert "Heal amount must be positive" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_heal_at_full_health_no_change(self, sample_character):
        """Test healing at full health makes no changes."""
        initial_health = sample_character.stats.vital_stats.current_health
        initial_version = sample_character.version

        sample_character.heal(10)

        # Should not change health or version if already at full health
        assert sample_character.stats.vital_stats.current_health == initial_health
        assert sample_character.version == initial_version

    @pytest.mark.unit
    def test_take_damage_success(self, sample_character):
        """Test successful damage application."""
        initial_health = sample_character.stats.vital_stats.current_health
        damage_reduction = sample_character.stats.combat_stats.damage_reduction
        initial_version = sample_character.version

        damage_amount = 15
        expected_damage = max(1, damage_amount - damage_reduction)

        sample_character.take_damage(damage_amount)

        assert (
            sample_character.stats.vital_stats.current_health
            == initial_health - expected_damage
        )
        assert sample_character.version == initial_version + 1

    @pytest.mark.unit
    def test_take_damage_with_reduction(self, sample_character):
        """Test damage application with damage reduction."""
        # Create new combat stats with damage reduction
        new_combat_stats = CombatStats(
            base_attack_bonus=sample_character.stats.combat_stats.base_attack_bonus,
            initiative_modifier=sample_character.stats.combat_stats.initiative_modifier,
            damage_reduction=5,  # Set damage reduction
            spell_resistance=sample_character.stats.combat_stats.spell_resistance,
            critical_hit_chance=sample_character.stats.combat_stats.critical_hit_chance,
            critical_damage_multiplier=sample_character.stats.combat_stats.critical_damage_multiplier,
        )

        new_stats = CharacterStats(
            core_abilities=sample_character.stats.core_abilities,
            vital_stats=sample_character.stats.vital_stats,
            combat_stats=new_combat_stats,
            experience_points=sample_character.stats.experience_points,
            skill_points=sample_character.stats.skill_points,
        )

        sample_character.update_stats(new_stats)
        initial_health = sample_character.stats.vital_stats.current_health

        # Apply damage that would be reduced
        sample_character.take_damage(8)  # Should be reduced to 3

        assert sample_character.stats.vital_stats.current_health == initial_health - 3

    @pytest.mark.unit
    def test_take_damage_minimum_one(self, sample_character):
        """Test damage always deals at least 1 point."""
        # Create new combat stats with very high damage reduction
        new_combat_stats = CombatStats(
            base_attack_bonus=sample_character.stats.combat_stats.base_attack_bonus,
            initiative_modifier=sample_character.stats.combat_stats.initiative_modifier,
            damage_reduction=50,  # Maximum damage reduction
            spell_resistance=sample_character.stats.combat_stats.spell_resistance,
            critical_hit_chance=sample_character.stats.combat_stats.critical_hit_chance,
            critical_damage_multiplier=sample_character.stats.combat_stats.critical_damage_multiplier,
        )

        new_stats = CharacterStats(
            core_abilities=sample_character.stats.core_abilities,
            vital_stats=sample_character.stats.vital_stats,
            combat_stats=new_combat_stats,
            experience_points=sample_character.stats.experience_points,
            skill_points=sample_character.stats.skill_points,
        )

        sample_character.update_stats(new_stats)
        initial_health = sample_character.stats.vital_stats.current_health

        sample_character.take_damage(5)

        assert sample_character.stats.vital_stats.current_health == initial_health - 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_take_damage_zero_amount_fails(self, sample_character):
        """Test taking zero or negative damage fails."""
        with pytest.raises(ValueError) as exc_info:
            sample_character.take_damage(0)
        assert "Damage amount must be positive" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            sample_character.take_damage(-5)
        assert "Damage amount must be positive" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_take_damage_to_zero_health(self, sample_character):
        """Test taking damage that reduces health to zero."""
        initial_health = sample_character.stats.vital_stats.current_health

        # Deal enough damage to reduce health to 0
        sample_character.take_damage(initial_health + 100)

        assert sample_character.stats.vital_stats.current_health == 0
        assert not sample_character.is_alive()

    # ==================== Query Methods Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_alive_when_alive(self, sample_character):
        """Test is_alive returns True when character has health."""
        assert sample_character.is_alive() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_alive_when_dead(self, sample_character):
        """Test is_alive returns False when character has no health."""
        # Reduce health to 0
        sample_character.take_damage(1000)
        assert sample_character.is_alive() is False

    @pytest.mark.unit
    def test_can_level_up_with_sufficient_xp(self, sample_character):
        """Test can_level_up with sufficient experience."""
        required_xp = 100

        # Set experience points to meet requirement
        new_stats = CharacterStats(
            core_abilities=sample_character.stats.core_abilities,
            vital_stats=sample_character.stats.vital_stats,
            combat_stats=sample_character.stats.combat_stats,
            experience_points=required_xp,
            skill_points=sample_character.stats.skill_points,
        )
        sample_character.stats = new_stats

        assert sample_character.can_level_up(required_xp) is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_can_level_up_insufficient_xp(self, sample_character):
        """Test can_level_up with insufficient experience."""
        required_xp = 100
        assert sample_character.can_level_up(required_xp) is False

    @pytest.mark.unit
    def test_can_level_up_at_max_level(self, sample_character):
        """Test can_level_up returns False at maximum level."""
        # Set to maximum level
        max_level_profile = CharacterProfile(
            name=sample_character.profile.name,
            gender=sample_character.profile.gender,
            race=sample_character.profile.race,
            character_class=sample_character.profile.character_class,
            age=sample_character.profile.age + 50,
            level=100,  # Maximum level
            physical_traits=sample_character.profile.physical_traits,
            personality_traits=sample_character.profile.personality_traits,
            background=sample_character.profile.background,
        )
        sample_character.profile = max_level_profile

        assert sample_character.can_level_up(0) is False

    @pytest.mark.unit
    def test_get_character_summary(self, sample_character):
        """Test character summary generation."""
        summary = sample_character.get_character_summary()

        assert "id" in summary
        assert "profile_summary" in summary
        assert "stats_summary" in summary
        assert "skills_summary" in summary
        assert "is_alive" in summary
        assert "level" in summary
        assert "class" in summary
        assert "race" in summary
        assert "created_at" in summary
        assert "updated_at" in summary
        assert "version" in summary

        assert summary["level"] == sample_character.profile.level
        assert summary["class"] == sample_character.profile.character_class.value
        assert summary["race"] == sample_character.profile.race.value
        assert summary["is_alive"] == sample_character.is_alive()

    # ==================== Factory Method Tests ====================

    @pytest.mark.unit
    def test_create_new_character_success(self):
        """Test successful character creation using factory method."""
        core_abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

        character = Character.create_new_character(
            name="New Hero",
            gender=Gender.FEMALE,
            race=CharacterRace.ELF,
            character_class=CharacterClass.RANGER,
            age=22,
            core_abilities=core_abilities,
        )

        assert character.profile.name == "New Hero"
        assert character.profile.gender == Gender.FEMALE
        assert character.profile.race == CharacterRace.ELF
        assert character.profile.character_class == CharacterClass.RANGER
        assert character.profile.age == 22
        assert character.profile.level == 1
        assert character.stats.core_abilities == core_abilities
        assert character.is_alive()
        assert len(character._events) == 1  # Creation event

    @pytest.mark.unit
    def test_create_new_character_appropriate_health_mana(self):
        """Test new character creation calculates appropriate health and mana."""
        core_abilities = CoreAbilities(
            strength=10,
            dexterity=10,
            constitution=14,
            intelligence=16,
            wisdom=10,
            charisma=10,
        )

        # Create wizard (magical class)
        wizard = Character.create_new_character(
            name="Test Wizard",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.WIZARD,
            age=25,
            core_abilities=core_abilities,
        )

        expected_health = 20 + 14  # base + constitution
        expected_mana = 10 + 16  # base + intelligence for magical classes

        assert wizard.stats.vital_stats.max_health == expected_health
        assert wizard.stats.vital_stats.max_mana == expected_mana
        assert wizard.stats.vital_stats.current_health == expected_health
        assert wizard.stats.vital_stats.current_mana == expected_mana

    # ==================== Domain Events Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_domain_events_creation(self, sample_character):
        """Test domain events are created properly."""
        assert len(sample_character._events) == 1
        creation_event = sample_character._events[0]
        assert creation_event.__class__.__name__ == "CharacterCreated"

    @pytest.mark.unit
    def test_domain_events_profile_update(self, sample_character):
        """Test domain events for profile updates."""
        initial_event_count = len(sample_character._events)

        new_profile = CharacterProfile(
            name="Updated Name",
            gender=sample_character.profile.gender,
            race=sample_character.profile.race,
            character_class=sample_character.profile.character_class,
            age=sample_character.profile.age,
            level=sample_character.profile.level,
            physical_traits=sample_character.profile.physical_traits,
            personality_traits=sample_character.profile.personality_traits,
            background=sample_character.profile.background,
        )

        sample_character.update_profile(new_profile)

        assert len(sample_character._events) == initial_event_count + 1
        update_event = sample_character._events[-1]
        assert update_event.__class__.__name__ == "CharacterUpdated"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_domain_events_stats_change(self, sample_character):
        """Test domain events for stats changes."""
        initial_event_count = len(sample_character._events)

        sample_character.take_damage(5)

        assert len(sample_character._events) == initial_event_count + 1
        stats_event = sample_character._events[-1]
        assert stats_event.__class__.__name__ == "CharacterStatsChanged"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_events(self, sample_character):
        """Test getting domain events."""
        events = sample_character.get_events()
        assert isinstance(events, list)
        assert len(events) >= 1
        # Should be a copy, not the original list
        assert events is not sample_character._events

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_clear_events(self, sample_character):
        """Test clearing domain events."""
        # Ensure there are events
        assert len(sample_character._events) > 0

        sample_character.clear_events()

        assert len(sample_character._events) == 0

    # ==================== Skills Management Tests ====================

    @pytest.mark.unit
    def test_update_skills_success(self, sample_character):
        """Test successful skills update."""
        initial_version = sample_character.version

        # Create new skills
        new_skills = Mock()
        new_skills.skill_groups = {
            SkillCategory.COMBAT: [Mock()],
            SkillCategory.PHYSICAL: [Mock()],
        }
        new_skills.get_skills_by_category = Mock(
            side_effect=lambda cat: new_skills.skill_groups.get(cat, [])
        )

        # Mock that skills are trained for validation
        trained_skill = Mock()
        trained_skill.is_trained.return_value = True
        new_skills.get_skills_by_category.return_value = [trained_skill]

        sample_character.update_skills(new_skills)

        assert sample_character.skills == new_skills
        assert sample_character.version == initial_version + 1

    @pytest.mark.unit
    def test_update_skills_validation_failure_rollback(self, sample_character):
        """Test skills update rollback on validation failure."""
        initial_skills = sample_character.skills
        initial_version = sample_character.version

        # Create invalid skills (missing required categories for fighter)
        invalid_skills = Mock()
        invalid_skills.skill_groups = {
            SkillCategory.MAGICAL: [Mock()]  # Fighter needs combat and physical
        }
        invalid_skills.get_skills_by_category = Mock(
            side_effect=lambda cat: invalid_skills.skill_groups.get(cat, [])
        )

        with pytest.raises(ValueError):
            sample_character.update_skills(invalid_skills)

        # Should rollback to original state
        assert sample_character.skills == initial_skills
        assert sample_character.version == initial_version

    # ==================== Edge Cases and Integration Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_character_version_consistency(self, sample_character):
        """Test version increments consistently across operations."""
        initial_version = sample_character.version

        # Each operation should increment version
        sample_character.take_damage(5)
        assert sample_character.version == initial_version + 1

        sample_character.heal(3)
        assert sample_character.version == initial_version + 2

        sample_character.level_up()
        assert sample_character.version == initial_version + 3

    @pytest.mark.unit
    def test_character_timestamp_updates(self, sample_character):
        """Test updated_at timestamp changes with operations."""
        initial_updated_at = sample_character.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.001)

        sample_character.take_damage(5)

        assert sample_character.updated_at > initial_updated_at

    @pytest.mark.unit
    def test_complete_character_lifecycle(self, sample_character):
        """Test complete character lifecycle from creation to high level."""
        # Start at level 1
        assert sample_character.profile.level == 1

        # Level up multiple times
        for _ in range(5):
            sample_character.level_up()

        assert sample_character.profile.level == 6

        # Take damage and heal
        initial_health = sample_character.stats.vital_stats.current_health
        sample_character.take_damage(20)
        damaged_health = sample_character.stats.vital_stats.current_health
        assert damaged_health < initial_health

        sample_character.heal(10)
        healed_health = sample_character.stats.vital_stats.current_health
        assert healed_health > damaged_health

        # Character should still be alive
        assert sample_character.is_alive()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_character_business_rules_consistency(self, sample_character):
        """Test business rules are maintained across operations."""
        # Level up should maintain health-constitution relationship
        original_constitution = sample_character.stats.core_abilities.constitution
        sample_character.level_up()

        # Health should still be appropriate for constitution and level
        min_expected_health = max(
            1, original_constitution + sample_character.profile.level
        )
        assert sample_character.stats.vital_stats.max_health >= min_expected_health

        # Character should still pass validation
        sample_character._validate_character_consistency()  # Should not raise exception


class TestCharacterMetadataSmartTags:
    """Tests for Character metadata and smart tags functionality."""

    @pytest.fixture
    def sample_core_abilities(self) -> CoreAbilities:
        """Create sample core abilities for testing."""
        return CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

    @pytest.fixture
    def sample_vital_stats(self) -> VitalStats:
        """Create sample vital stats for testing."""
        return VitalStats(
            max_health=36,
            current_health=36,
            max_mana=15,
            current_mana=15,
            max_stamina=31,
            current_stamina=31,
            armor_class=12,
            speed=30,
        )

    @pytest.fixture
    def sample_combat_stats(self) -> CombatStats:
        """Create sample combat stats for testing."""
        return CombatStats(
            base_attack_bonus=0,
            initiative_modifier=2,
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        )

    @pytest.fixture
    def sample_character_stats(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ) -> CharacterStats:
        """Create sample character stats for testing."""
        return CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=sample_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=0,
            skill_points=5,
        )

    @pytest.fixture
    def sample_character_profile(self) -> CharacterProfile:
        """Create sample character profile for testing."""
        return CharacterProfile(
            name="Test Warrior",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=PhysicalTraits(
                height_cm=180, weight_kg=75, hair_color="brown", eye_color="blue"
            ),
            personality_traits=PersonalityTraits(
                traits={
                    "courage": 0.8,
                    "intelligence": 0.6,
                    "charisma": 0.5,
                    "loyalty": 0.9,
                }
            ),
            background=Background(),
        )

    @pytest.fixture
    def sample_skills(self) -> Skills:
        """Create sample skills for testing."""
        combat_skill = Skill(
            name="Melee Combat",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.NOVICE,
            modifier=0,
        )

        physical_skill = Skill(
            name="Athletics",
            category=SkillCategory.PHYSICAL,
            proficiency_level=ProficiencyLevel.APPRENTICE,
            modifier=1,
        )

        skills = Mock()
        skills.skill_groups = {
            SkillCategory.COMBAT: [combat_skill],
            SkillCategory.PHYSICAL: [physical_skill],
        }
        skills.get_skills_by_category = Mock(
            side_effect=lambda cat: skills.skill_groups.get(cat, [])
        )
        skills.get_skill_summary = Mock(
            return_value={"total_skills": 2, "trained_skills": 2}
        )

        return skills

    @pytest.fixture
    def sample_character(
        self, sample_character_profile, sample_character_stats, sample_skills
    ) -> Character:
        """Create a test Character instance."""
        return Character(
            character_id=CharacterID.generate(),
            profile=sample_character_profile,
            stats=sample_character_stats,
            skills=sample_skills,
        )

    @pytest.fixture
    def character_with_metadata(self, sample_character):
        """Character with metadata for testing."""
        return sample_character

    @pytest.mark.unit
    def test_update_metadata_adds_key_value(self, character_with_metadata):
        """Test updating metadata with a key-value pair."""
        character_with_metadata.update_metadata("custom_field", "custom_value")

        assert character_with_metadata.get_metadata("custom_field") == "custom_value"
        assert character_with_metadata.version > 1

    @pytest.mark.unit
    def test_update_metadata_overwrites_existing(self, character_with_metadata):
        """Test that updating metadata overwrites existing values."""
        character_with_metadata.update_metadata("key", "value1")
        character_with_metadata.update_metadata("key", "value2")

        assert character_with_metadata.get_metadata("key") == "value2"

    @pytest.mark.unit
    def test_get_metadata_returns_default_for_missing_key(
        self, character_with_metadata
    ):
        """Test that get_metadata returns default for missing keys."""
        assert (
            character_with_metadata.get_metadata("nonexistent", "default") == "default"
        )
        assert character_with_metadata.get_metadata("nonexistent") is None

    @pytest.mark.unit
    def test_set_smart_tags_stores_tags(self, character_with_metadata):
        """Test storing smart tags in metadata."""
        tags = {
            "role": ["protagonist", "warrior"],
            "personality": ["brave", "impulsive"],
        }
        character_with_metadata.set_smart_tags(tags)

        assert character_with_metadata.get_smart_tags() == tags
        assert character_with_metadata.version > 1

    @pytest.mark.unit
    def test_get_smart_tags_empty_when_none_set(self, character_with_metadata):
        """Test that get_smart_tags returns empty dict when none set."""
        assert character_with_metadata.get_smart_tags() == {}

    @pytest.mark.unit
    def test_smart_tags_stored_alongside_other_metadata(self, character_with_metadata):
        """Test that smart tags coexist with other metadata."""
        character_with_metadata.update_metadata("other_key", "other_value")
        character_with_metadata.set_smart_tags({"role": ["protagonist"]})

        assert character_with_metadata.get_metadata("other_key") == "other_value"
        assert character_with_metadata.get_smart_tags() == {"role": ["protagonist"]}

    @pytest.mark.unit
    def test_metadata_triggers_domain_event(self, character_with_metadata):
        """Test that metadata update triggers a domain event."""
        initial_event_count = len(character_with_metadata.get_events())
        character_with_metadata.update_metadata("test", "value")

        # Metadata updates trigger CharacterUpdated event
        assert len(character_with_metadata.get_events()) > initial_event_count

    @pytest.mark.unit
    def test_smart_tags_trigger_domain_event(self, character_with_metadata):
        """Test that setting smart tags triggers a domain event."""
        initial_event_count = len(character_with_metadata.get_events())
        character_with_metadata.set_smart_tags({"role": ["protagonist"]})

        # Smart tag updates trigger CharacterUpdated event
        assert len(character_with_metadata.get_events()) > initial_event_count
