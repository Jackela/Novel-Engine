#!/usr/bin/env python3
"""
Character Application Commands

This module implements command objects for the Character bounded context.
Commands represent user intentions to change character state and follow
the Command pattern for request encapsulation.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...domain.value_objects.character_id import CharacterID
from ...domain.value_objects.character_profile import (
    CharacterClass,
    CharacterRace,
    Gender,
)
from ...domain.value_objects.character_stats import AbilityScore
from ...domain.value_objects.skills import ProficiencyLevel, SkillCategory


@dataclass
class CreateCharacterCommand:
    """
    Command to create a new character.

    This command encapsulates all the data needed to create a new
    character aggregate with proper validation and defaults.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Required character data
    character_name: str = ""
    gender: str = ""  # Will be converted to Gender enum
    race: str = ""  # Will be converted to CharacterRace enum
    character_class: str = ""  # Will be converted to CharacterClass enum
    age: int = 0

    # Core abilities
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Optional character data
    title: Optional[str] = None
    affiliation: Optional[str] = None
    languages: Optional[List[str]] = None

    # Physical traits
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    physical_description: Optional[str] = None

    # Personality traits (trait_name -> score 0.0-1.0)
    personality_traits: Dict[str, float] = field(
        default_factory=lambda: {
            "courage": 0.5,
            "intelligence": 0.5,
            "charisma": 0.5,
            "loyalty": 0.5,
        }
    )

    # Background information
    backstory: Optional[str] = None
    homeland: Optional[str] = None
    education: Optional[str] = None

    # Command metadata
    user_id: Optional[str] = None
    source: str = "character_application"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Validate command data after initialization."""
        errors = []

        # Validate required fields
        if not self.character_name or not self.character_name.strip():
            errors.append("Character name is required")

        if not self.gender:
            errors.append("Gender is required")

        if not self.race:
            errors.append("Race is required")

        if not self.character_class:
            errors.append("Character class is required")

        if self.age < 0 or self.age > 10000:
            errors.append("Age must be between 0 and 10000")

        # Validate ability scores
        abilities = [
            self.strength,
            self.dexterity,
            self.constitution,
            self.intelligence,
            self.wisdom,
            self.charisma,
        ]
        for ability in abilities:
            if not 1 <= ability <= 30:
                errors.append("Ability scores must be between 1 and 30")

        # Validate personality traits
        for trait, score in self.personality_traits.items():
            if not 0.0 <= score <= 1.0:
                errors.append(
                    f"Personality trait '{trait}' score must be between 0.0 and 1.0"
                )

        # Validate enum values
        try:
            Gender(self.gender.lower())
        except ValueError:
            errors.append(f"Invalid gender: {self.gender}")

        try:
            CharacterRace(self.race.lower())
        except ValueError:
            errors.append(f"Invalid race: {self.race}")

        try:
            CharacterClass(self.character_class.lower())
        except ValueError:
            errors.append(f"Invalid character class: {self.character_class}")

        if errors:
            raise ValueError(
                f"CreateCharacterCommand validation failed: {'; '.join(errors)}"
            )

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())


@dataclass
class UpdateCharacterStatsCommand:
    """
    Command to update character statistics.

    This command allows updating vital statistics like health, mana,
    and stamina while enforcing business rules.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    character_id: str = ""
    expected_version: Optional[int] = None

    # Vital stats updates (None means no change)
    current_health: Optional[int] = None
    current_mana: Optional[int] = None
    current_stamina: Optional[int] = None
    max_health: Optional[int] = None
    max_mana: Optional[int] = None
    max_stamina: Optional[int] = None

    # Combat stats updates
    armor_class: Optional[int] = None
    speed: Optional[int] = None
    base_attack_bonus: Optional[int] = None
    initiative_modifier: Optional[int] = None

    # Experience and skill points
    experience_points: Optional[int] = None
    skill_points: Optional[int] = None

    # Command metadata
    user_id: Optional[str] = None
    reason: str = "Stats update"
    source: str = "character_application"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Validate command data."""
        errors = []

        # Validate required fields
        if not self.character_id:
            errors.append("Character ID is required")

        try:
            CharacterID.from_string(self.character_id)
        except ValueError:
            errors.append("Character ID must be a valid UUID")

        if not self.reason or not self.reason.strip():
            errors.append("Reason for stats update is required")

        # Validate stat values
        if self.current_health is not None and self.current_health < 0:
            errors.append("Current health cannot be negative")

        if self.current_mana is not None and self.current_mana < 0:
            errors.append("Current mana cannot be negative")

        if self.current_stamina is not None and self.current_stamina < 0:
            errors.append("Current stamina cannot be negative")

        if self.max_health is not None and self.max_health <= 0:
            errors.append("Max health must be positive")

        if self.max_mana is not None and self.max_mana < 0:
            errors.append("Max mana cannot be negative")

        if self.max_stamina is not None and self.max_stamina < 0:
            errors.append("Max stamina cannot be negative")

        if self.armor_class is not None and not 0 <= self.armor_class <= 50:
            errors.append("Armor class must be between 0 and 50")

        if self.speed is not None and not 0 <= self.speed <= 200:
            errors.append("Speed must be between 0 and 200")

        if self.experience_points is not None and self.experience_points < 0:
            errors.append("Experience points cannot be negative")

        if self.skill_points is not None and self.skill_points < 0:
            errors.append("Skill points cannot be negative")

        if errors:
            raise ValueError(
                f"UpdateCharacterStatsCommand validation failed: {'; '.join(errors)}"
            )

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())


@dataclass
class UpdateCharacterSkillCommand:
    """
    Command to update a character's skill proficiency.

    This command allows adding new skills or updating existing
    skill proficiency levels and modifiers.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    character_id: str = ""
    expected_version: Optional[int] = None

    skill_name: str = ""
    skill_category: str = ""  # Will be converted to SkillCategory enum
    new_proficiency_level: str = ""  # Will be converted to ProficiencyLevel enum
    modifier: int = 0
    description: Optional[str] = None

    # Command metadata
    user_id: Optional[str] = None
    reason: str = "Skill update"
    source: str = "character_application"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Validate command data."""
        errors = []

        # Validate required fields
        if not self.character_id:
            errors.append("Character ID is required")

        if not self.skill_name or not self.skill_name.strip():
            errors.append("Skill name is required")

        if not self.skill_category:
            errors.append("Skill category is required")

        if not self.new_proficiency_level:
            errors.append("Proficiency level is required")

        # Validate character ID format
        try:
            CharacterID.from_string(self.character_id)
        except ValueError:
            errors.append("Character ID must be a valid UUID")

        # Validate enums
        try:
            SkillCategory(self.skill_category.lower())
        except ValueError:
            errors.append(f"Invalid skill category: {self.skill_category}")

        try:
            ProficiencyLevel(int(self.new_proficiency_level))
        except ValueError:
            errors.append(f"Invalid proficiency level: {self.new_proficiency_level}")

        # Validate modifier
        if not -10 <= self.modifier <= 20:
            errors.append("Skill modifier must be between -10 and 20")

        # Validate description length
        if self.description and len(self.description) > 500:
            errors.append("Skill description cannot exceed 500 characters")

        if errors:
            raise ValueError(
                f"UpdateCharacterSkillCommand validation failed: {'; '.join(errors)}"
            )

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())


@dataclass
class LevelUpCharacterCommand:
    """
    Command to level up a character.

    This command handles character level progression including
    stat increases and skill point allocation.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    character_id: str = ""
    expected_version: Optional[int] = None

    # Optional ability score improvements
    ability_score_improvements: Dict[str, int] = field(default_factory=dict)

    # Optional new skills to add/improve
    skill_improvements: List[Dict[str, Any]] = field(default_factory=list)

    # Command metadata
    user_id: Optional[str] = None
    reason: str = "Level up"
    source: str = "character_application"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Validate command data."""
        errors = []

        # Validate required fields
        if not self.character_id:
            errors.append("Character ID is required")

        try:
            CharacterID.from_string(self.character_id)
        except ValueError:
            errors.append("Character ID must be a valid UUID")

        # Validate ability score improvements
        for ability, improvement in self.ability_score_improvements.items():
            if not hasattr(AbilityScore, ability.upper()):
                errors.append(f"Invalid ability score: {ability}")

            if not 0 <= improvement <= 3:
                errors.append(
                    f"Ability improvement must be 0-3 points, got {improvement} for {ability}"
                )

        # Validate skill improvements
        for skill_data in self.skill_improvements:
            if not isinstance(skill_data, dict):
                errors.append("Skill improvements must be dictionaries")
                continue

            if "skill_name" not in skill_data or not skill_data["skill_name"]:
                errors.append("Skill improvement must include skill_name")

            if "improvement" in skill_data:
                improvement = skill_data["improvement"]
                if not 0 <= improvement <= 2:
                    errors.append(
                        f"Skill improvement must be 0-2 levels, got {improvement}"
                    )

        if errors:
            raise ValueError(
                f"LevelUpCharacterCommand validation failed: {'; '.join(errors)}"
            )

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())


@dataclass
class DeleteCharacterCommand:
    """
    Command to delete a character.

    This command handles character deletion with proper
    reason tracking for audit purposes.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    character_id: str = ""
    reason: str = ""

    # Command metadata
    user_id: Optional[str] = None
    source: str = "character_application"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Validate command data."""
        errors = []

        # Validate required fields
        if not self.character_id:
            errors.append("Character ID is required")

        if not self.reason or not self.reason.strip():
            errors.append("Deletion reason is required")

        try:
            CharacterID.from_string(self.character_id)
        except ValueError:
            errors.append("Character ID must be a valid UUID")

        if len(self.reason.strip()) > 500:
            errors.append("Deletion reason cannot exceed 500 characters")

        if errors:
            raise ValueError(
                f"DeleteCharacterCommand validation failed: {'; '.join(errors)}"
            )

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())


@dataclass
class HealCharacterCommand:
    """
    Command to heal a character.

    This command handles healing operations with
    validation and amount limits.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    character_id: str = ""
    healing_amount: int = 0
    healing_type: str = "natural"  # natural, magical, potion, etc.

    # Command metadata
    user_id: Optional[str] = None
    reason: str = "Healing"
    source: str = "character_application"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Validate command data."""
        errors = []

        # Validate required fields
        if not self.character_id:
            errors.append("Character ID is required")

        if self.healing_amount <= 0:
            errors.append("Healing amount must be positive")

        if self.healing_amount > 1000:
            errors.append("Healing amount cannot exceed 1000")

        try:
            CharacterID.from_string(self.character_id)
        except ValueError:
            errors.append("Character ID must be a valid UUID")

        valid_healing_types = [
            "natural",
            "magical",
            "potion",
            "spell",
            "ability",
            "other",
        ]
        if self.healing_type not in valid_healing_types:
            errors.append(f"Invalid healing type: {self.healing_type}")

        if errors:
            raise ValueError(
                f"HealCharacterCommand validation failed: {'; '.join(errors)}"
            )

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())


@dataclass
class DamageCharacterCommand:
    """
    Command to apply damage to a character.

    This command handles damage application with
    damage type and source tracking.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    character_id: str = ""
    damage_amount: int = 0
    damage_type: str = "physical"  # physical, magical, poison, fire, etc.
    damage_source: Optional[str] = None

    # Command metadata
    user_id: Optional[str] = None
    reason: str = "Damage taken"
    source: str = "character_application"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    def __post_init__(self):
        """Validate command data."""
        errors = []

        # Validate required fields
        if not self.character_id:
            errors.append("Character ID is required")

        if self.damage_amount <= 0:
            errors.append("Damage amount must be positive")

        if self.damage_amount > 10000:
            errors.append("Damage amount cannot exceed 10000")

        try:
            CharacterID.from_string(self.character_id)
        except ValueError:
            errors.append("Character ID must be a valid UUID")

        valid_damage_types = [
            "physical",
            "magical",
            "poison",
            "fire",
            "cold",
            "acid",
            "lightning",
            "psychic",
            "necrotic",
            "radiant",
            "other",
        ]
        if self.damage_type not in valid_damage_types:
            errors.append(f"Invalid damage type: {self.damage_type}")

        if self.damage_source and len(self.damage_source) > 100:
            errors.append("Damage source cannot exceed 100 characters")

        if errors:
            raise ValueError(
                f"DamageCharacterCommand validation failed: {'; '.join(errors)}"
            )

        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())
