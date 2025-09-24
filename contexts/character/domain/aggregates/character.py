#!/usr/bin/env python3
"""
Character Aggregate Root

This module implements the Character aggregate root, which serves as the main
entry point for character-related domain operations and enforces business
invariants across all character data.

Follows P3 Sprint 3 patterns for type safety and validation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ...infrastructure.character_domain_types import (
        CharacterTypeGuards,
        ValueObjectFactory,
    )

from ..events.character_events import (
    CharacterCreated,
    CharacterEvent,
    CharacterStatsChanged,
    CharacterUpdated,
)
from ..value_objects.character_id import CharacterID
from ..value_objects.character_profile import (
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
)
from ..value_objects.character_stats import (
    AbilityScore,
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from ..value_objects.skills import SkillCategory, Skills


@dataclass
class Character:
    """
    Character Aggregate Root

    The Character aggregate is responsible for maintaining consistency across
    all character-related data and enforcing business rules. It coordinates
    between value objects and raises domain events when state changes occur.

    Following DDD principles, this is the only way external systems should
    interact with character data, ensuring all business invariants are maintained.
    """

    # Entity identity
    character_id: CharacterID

    # Value objects containing character data
    profile: CharacterProfile
    stats: CharacterStats
    skills: Skills

    # Entity state
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = field(default=1)

    # Domain events (not persisted)
    _events: List[CharacterEvent] = field(default_factory=list, init=False)

    def __post_init__(self):
        """Initialize aggregate and validate invariants."""
        self._validate_character_consistency()

        # Record creation event if this is a new character
        if self.version == 1 and not self._events:
            self._add_event(
                CharacterCreated.create(
                    character_id=self.character_id,
                    character_name=self.profile.name,
                    character_class=self.profile.character_class.value,
                    level=self.profile.level,
                    created_at=self.created_at,
                )
            )

    def _validate_character_consistency(self) -> None:
        """Validate business rules across all character data."""
        errors = []

        # Validate level consistency
        if self.profile.level < 1:
            errors.append("Character level must be at least 1")

        # Validate health makes sense for constitution and level
        expected_min_health = max(
            1, self.stats.core_abilities.constitution + self.profile.level
        )
        if self.stats.vital_stats.max_health < expected_min_health:
            errors.append(
                f"Character health too low for constitution and level (minimum: {expected_min_health})"
            )

        # Validate race-appropriate ability scores
        self._validate_racial_abilities(errors)

        # Validate class-appropriate skills
        self._validate_class_skills(errors)

        # Validate age appropriateness
        self._validate_age_consistency(errors)

        if errors:
            raise ValueError(
                f"Character validation failed: {'; '.join(errors)}"
            )

    def _validate_racial_abilities(self, errors: List[str]) -> None:
        """Validate ability scores are appropriate for character race."""
        # Basic racial ability expectations
        racial_minimums = {
            CharacterRace.DWARF: {"constitution": 12},
            CharacterRace.ELF: {"dexterity": 12},
            CharacterRace.HALFLING: {"dexterity": 12},
            CharacterRace.GNOME: {"intelligence": 12},
            CharacterRace.HALF_ORC: {"strength": 12},
            CharacterRace.DRAGONBORN: {"strength": 12, "charisma": 11},
        }

        minimums = racial_minimums.get(self.profile.race, {})
        for ability, min_score in minimums.items():
            if hasattr(self.stats.core_abilities, ability):
                actual_score = getattr(self.stats.core_abilities, ability)
                if actual_score < min_score:
                    errors.append(
                        f"{self.profile.race.value.title()} should have {ability} >= {min_score}"
                    )

    def _validate_class_skills(self, errors: List[str]) -> None:
        """Validate character has appropriate skills for their class."""
        class_skills = {
            CharacterClass.FIGHTER: [
                SkillCategory.COMBAT,
                SkillCategory.PHYSICAL,
            ],
            CharacterClass.WIZARD: [
                SkillCategory.INTELLECTUAL,
                SkillCategory.MAGICAL,
            ],
            CharacterClass.ROGUE: [
                SkillCategory.PHYSICAL,
                SkillCategory.SOCIAL,
            ],
            CharacterClass.CLERIC: [
                SkillCategory.MAGICAL,
                SkillCategory.SOCIAL,
            ],
            CharacterClass.RANGER: [
                SkillCategory.SURVIVAL,
                SkillCategory.COMBAT,
            ],
            CharacterClass.BARD: [
                SkillCategory.SOCIAL,
                SkillCategory.ARTISTIC,
            ],
            CharacterClass.PILOT: [
                SkillCategory.TECHNICAL,
                SkillCategory.PHYSICAL,
            ],
            CharacterClass.SCIENTIST: [
                SkillCategory.INTELLECTUAL,
                SkillCategory.TECHNICAL,
            ],
            CharacterClass.ENGINEER: [
                SkillCategory.TECHNICAL,
                SkillCategory.INTELLECTUAL,
            ],
        }

        expected_categories = class_skills.get(
            self.profile.character_class, []
        )
        for category in expected_categories:
            if category not in self.skills.skill_groups:
                errors.append(
                    f"{self.profile.character_class.value.title()} should have {category.value} skills"
                )
            elif not any(
                skill.is_trained()
                for skill in self.skills.get_skills_by_category(category)
            ):
                errors.append(
                    f"{self.profile.character_class.value.title()} should be trained in at least one {category.value} skill"
                )

    def _validate_age_consistency(self, errors: List[str]) -> None:
        """Validate character age makes sense for their experience."""
        min_age_by_level = {
            range(1, 6): 16,  # Levels 1-5: Young adult
            range(6, 11): 20,  # Levels 6-10: Adult
            range(11, 16): 25,  # Levels 11-15: Experienced
            range(16, 21): 30,  # Levels 16-20: Veteran
            range(21, 100): 35,  # Levels 21+: Master
        }

        for level_range, min_age in min_age_by_level.items():
            if (
                self.profile.level in level_range
                and self.profile.age < min_age
            ):
                errors.append(
                    f"Character too young ({self.profile.age}) for level {self.profile.level} (minimum age: {min_age})"
                )
                break

    def _add_event(self, event: CharacterEvent) -> None:
        """Add a domain event to the aggregate."""
        self._events.append(event)

    def get_events(self) -> List[CharacterEvent]:
        """Get all pending domain events."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear all pending domain events."""
        self._events.clear()

    # ==================== Character Operations ====================

    def update_profile(self, new_profile: CharacterProfile) -> None:
        """Update character profile, ensuring business rules are maintained."""
        old_profile = self.profile
        self.profile = new_profile
        self.updated_at = datetime.now()
        self.version += 1

        try:
            self._validate_character_consistency()
        except ValueError as e:
            # Rollback changes if validation fails
            self.profile = old_profile
            self.version -= 1
            raise e

        # Record update event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["profile"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def update_stats(self, new_stats: CharacterStats) -> None:
        """Update character statistics, validating health changes."""
        old_stats = self.stats

        # Business rule: Cannot lose more than half health in one update
        if (
            new_stats.vital_stats.current_health
            < old_stats.vital_stats.current_health
            and new_stats.vital_stats.current_health
            < old_stats.vital_stats.current_health / 2
        ):
            raise ValueError(
                "Cannot lose more than half health in a single update"
            )

        # Business rule: Cannot exceed maximum values
        if (
            new_stats.vital_stats.current_health
            > new_stats.vital_stats.max_health
            or new_stats.vital_stats.current_mana
            > new_stats.vital_stats.max_mana
            or new_stats.vital_stats.current_stamina
            > new_stats.vital_stats.max_stamina
        ):
            raise ValueError("Current values cannot exceed maximum values")

        self.stats = new_stats
        self.updated_at = datetime.now()
        self.version += 1

        try:
            self._validate_character_consistency()
        except ValueError as e:
            # Rollback changes if validation fails
            self.stats = old_stats
            self.version -= 1
            raise e

        # Record stats change event
        self._add_event(
            CharacterStatsChanged.create(
                character_id=self.character_id,
                old_health=old_stats.vital_stats.current_health,
                new_health=new_stats.vital_stats.current_health,
                old_mana=old_stats.vital_stats.current_mana,
                new_mana=new_stats.vital_stats.current_mana,
                changed_at=self.updated_at,
            )
        )

    def update_skills(self, new_skills: Skills) -> None:
        """Update character skills, ensuring class compatibility."""
        old_skills = self.skills
        self.skills = new_skills
        self.updated_at = datetime.now()
        self.version += 1

        try:
            self._validate_character_consistency()
        except ValueError as e:
            # Rollback changes if validation fails
            self.skills = old_skills
            self.version -= 1
            raise e

        # Record update event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["skills"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def level_up(self) -> None:
        """Level up the character, increasing stats appropriately."""
        if self.profile.level >= 100:
            raise ValueError("Character is already at maximum level")

        # Calculate stat increases
        new_health = (
            self.stats.vital_stats.max_health
            + 10
            + self.stats.core_abilities.constitution
        )
        new_mana = (
            self.stats.vital_stats.max_mana
            + 5
            + self.stats.core_abilities.intelligence
        )

        # Create updated profile
        from ..value_objects.character_profile import CharacterProfile

        new_profile = CharacterProfile(
            name=self.profile.name,
            gender=self.profile.gender,
            race=self.profile.race,
            character_class=self.profile.character_class,
            age=self.profile.age,
            level=self.profile.level + 1,
            physical_traits=self.profile.physical_traits,
            personality_traits=self.profile.personality_traits,
            background=self.profile.background,
            title=self.profile.title,
            affiliation=self.profile.affiliation,
            languages=self.profile.languages,
        )

        # Create updated vital stats
        new_vital_stats = VitalStats(
            max_health=new_health,
            current_health=min(
                self.stats.vital_stats.current_health + 10, new_health
            ),
            max_mana=new_mana,
            current_mana=min(
                self.stats.vital_stats.current_mana + 5, new_mana
            ),
            max_stamina=self.stats.vital_stats.max_stamina + 5,
            current_stamina=self.stats.vital_stats.max_stamina + 5,
            armor_class=self.stats.vital_stats.armor_class,
            speed=self.stats.vital_stats.speed,
        )

        new_stats = CharacterStats(
            core_abilities=self.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=self.stats.combat_stats,
            experience_points=self.stats.experience_points,
            skill_points=self.stats.skill_points + 5,
        )

        # Update character
        self.profile = new_profile
        self.stats = new_stats
        self.updated_at = datetime.now()
        self.version += 1

        # Record level up event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["level_up"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def heal(self, amount: int) -> None:
        """Heal the character by specified amount."""
        if amount <= 0:
            raise ValueError("Heal amount must be positive")

        new_health = min(
            self.stats.vital_stats.current_health + amount,
            self.stats.vital_stats.max_health,
        )

        if new_health == self.stats.vital_stats.current_health:
            return  # No healing needed

        new_vital_stats = VitalStats(
            max_health=self.stats.vital_stats.max_health,
            current_health=new_health,
            max_mana=self.stats.vital_stats.max_mana,
            current_mana=self.stats.vital_stats.current_mana,
            max_stamina=self.stats.vital_stats.max_stamina,
            current_stamina=self.stats.vital_stats.current_stamina,
            armor_class=self.stats.vital_stats.armor_class,
            speed=self.stats.vital_stats.speed,
        )

        old_health = self.stats.vital_stats.current_health

        self.stats = CharacterStats(
            core_abilities=self.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=self.stats.combat_stats,
            experience_points=self.stats.experience_points,
            skill_points=self.stats.skill_points,
        )

        self.updated_at = datetime.now()
        self.version += 1

        # Record healing event
        self._add_event(
            CharacterStatsChanged.create(
                character_id=self.character_id,
                old_health=old_health,
                new_health=new_health,
                old_mana=self.stats.vital_stats.current_mana,
                new_mana=self.stats.vital_stats.current_mana,
                changed_at=self.updated_at,
            )
        )

    def take_damage(self, amount: int) -> None:
        """Apply damage to the character."""
        if amount <= 0:
            raise ValueError("Damage amount must be positive")

        # Apply damage reduction
        actual_damage = max(
            1, amount - self.stats.combat_stats.damage_reduction
        )
        new_health = max(
            0, self.stats.vital_stats.current_health - actual_damage
        )

        new_vital_stats = VitalStats(
            max_health=self.stats.vital_stats.max_health,
            current_health=new_health,
            max_mana=self.stats.vital_stats.max_mana,
            current_mana=self.stats.vital_stats.current_mana,
            max_stamina=self.stats.vital_stats.max_stamina,
            current_stamina=self.stats.vital_stats.current_stamina,
            armor_class=self.stats.vital_stats.armor_class,
            speed=self.stats.vital_stats.speed,
        )

        old_health = self.stats.vital_stats.current_health

        self.stats = CharacterStats(
            core_abilities=self.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=self.stats.combat_stats,
            experience_points=self.stats.experience_points,
            skill_points=self.stats.skill_points,
        )

        self.updated_at = datetime.now()
        self.version += 1

        # Record damage event
        self._add_event(
            CharacterStatsChanged.create(
                character_id=self.character_id,
                old_health=old_health,
                new_health=new_health,
                old_mana=self.stats.vital_stats.current_mana,
                new_mana=self.stats.vital_stats.current_mana,
                changed_at=self.updated_at,
            )
        )

    # ==================== Query Methods ====================

    def is_alive(self) -> bool:
        """Check if character is alive."""
        return self.stats.vital_stats.is_alive()

    def can_level_up(self, required_xp: int) -> bool:
        """Check if character has enough experience to level up."""
        return (
            self.stats.experience_points >= required_xp
            and self.profile.level < 100
        )

    def get_character_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the character."""
        return {
            "id": str(self.character_id),
            "profile_summary": self.profile.get_character_summary(),
            "stats_summary": self.stats.get_stats_summary(),
            "skills_summary": self.skills.get_skill_summary(),
            "is_alive": self.is_alive(),
            "level": self.profile.level,
            "class": self.profile.character_class.value,
            "race": self.profile.race.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }

    @classmethod
    def create_new_character(
        cls,
        name: str,
        gender: Gender,
        race: CharacterRace,
        character_class: CharacterClass,
        age: int,
        core_abilities: CoreAbilities,
    ) -> "Character":
        """Factory method to create a new character with defaults."""
        from ..value_objects.character_profile import (
            Background,
            PersonalityTraits,
            PhysicalTraits,
        )

        # Create basic profile
        profile = CharacterProfile(
            name=name,
            gender=gender,
            race=race,
            character_class=character_class,
            age=age,
            level=1,
            physical_traits=PhysicalTraits(),
            personality_traits=PersonalityTraits(
                traits={
                    "courage": 0.5,
                    "intelligence": 0.5,
                    "charisma": 0.5,
                    "loyalty": 0.5,
                }
            ),
            background=Background(),
        )

        # Calculate starting health/mana based on class and constitution
        base_health = 20 + core_abilities.constitution
        base_mana = (
            10 + core_abilities.intelligence
            if character_class
            in [
                CharacterClass.WIZARD,
                CharacterClass.CLERIC,
                CharacterClass.SORCERER,
                CharacterClass.WARLOCK,
                CharacterClass.BARD,
                CharacterClass.DRUID,
            ]
            else 5
        )

        vital_stats = VitalStats(
            max_health=base_health,
            current_health=base_health,
            max_mana=base_mana,
            current_mana=base_mana,
            max_stamina=15 + core_abilities.constitution,
            current_stamina=15 + core_abilities.constitution,
            armor_class=10
            + core_abilities.get_ability_modifier(AbilityScore.DEXTERITY),
            speed=30,
        )

        combat_stats = CombatStats(
            base_attack_bonus=0,
            initiative_modifier=core_abilities.get_ability_modifier(
                AbilityScore.DEXTERITY
            ),
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        )

        stats = CharacterStats(
            core_abilities=core_abilities,
            vital_stats=vital_stats,
            combat_stats=combat_stats,
            experience_points=0,
            skill_points=5,
        )

        # Create basic skills appropriate for class
        skills = Skills.create_basic_skills()

        return cls(
            character_id=CharacterID.generate(),
            profile=profile,
            stats=stats,
            skills=skills,
        )
