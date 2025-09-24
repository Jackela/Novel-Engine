#!/usr/bin/env python3
"""
Character Domain Type Safety Patterns

This module provides type safety utilities and patterns for the character domain,
following P3 Sprint 2 architectural patterns for systematic type safety.
"""

from datetime import datetime
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from ..domain.aggregates.character import Character
    from ..domain.value_objects.character_id import CharacterID

T = TypeVar("T")
ValueObjectType = TypeVar("ValueObjectType")


# Type Guards for Runtime Safety
def ensure_not_none(value: Optional[T]) -> T:
    """Type guard to ensure value is not None."""
    if value is None:
        raise ValueError("Expected non-None value")
    return value


def ensure_uuid(value: Union[str, UUID]) -> UUID:
    """Type guard to ensure value is a UUID."""
    if isinstance(value, str):
        return UUID(value)
    return value


def ensure_decimal(value: Union[str, int, float, Decimal]) -> Decimal:
    """Type guard to ensure value is a Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def ensure_int(value: Union[str, int, float]) -> int:
    """Type guard to ensure value is an integer."""
    if isinstance(value, int):
        return value
    if isinstance(value, (str, float)):
        return int(value)
    raise TypeError(f"Cannot convert {type(value)} to int")


def ensure_float(value: Union[str, int, float]) -> float:
    """Type guard to ensure value is a float."""
    if isinstance(value, float):
        return value
    if isinstance(value, (str, int)):
        return float(value)
    raise TypeError(f"Cannot convert {type(value)} to float")


# Character Domain Type Safety Patterns
class CharacterDomainTyping:
    """Type safety utilities for character domain operations."""

    @staticmethod
    def safe_enum_conversion(enum_class: Type[T], value: Union[str, T]) -> T:
        """Type-safe enum conversion with fallback."""
        if isinstance(value, enum_class):
            return value
        if isinstance(value, str):
            try:
                return enum_class(value)  # type: ignore[call-arg]
            except ValueError:
                # Try by name if value lookup fails
                try:
                    return getattr(enum_class, value.upper())
                except (AttributeError, KeyError):
                    raise ValueError(
                        f"Invalid {enum_class.__name__} value: {value}"
                    )
        raise TypeError(
            f"Cannot convert {type(value)} to {enum_class.__name__}"
        )

    @staticmethod
    def safe_uuid_conversion(value: Union[str, UUID, None]) -> Optional[UUID]:
        """Type-safe UUID conversion."""
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {value}")
        raise TypeError(f"Cannot convert {type(value)} to UUID")

    @staticmethod
    def safe_list_conversion(
        items: Optional[List[Any]], converter_func
    ) -> List[Any]:
        """Type-safe list conversion with element transformation."""
        if items is None:
            return []
        return [converter_func(item) for item in items]

    @staticmethod
    def safe_dict_conversion(
        items: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Type-safe dictionary conversion."""
        if items is None:
            return {}
        return dict(items)

    @staticmethod
    def safe_set_conversion(items: Optional[Union[List[Any], set]]) -> set:
        """Type-safe set conversion."""
        if items is None:
            return set()
        if isinstance(items, set):
            return items
        return set(items)


# Value Object Factory Patterns
class ValueObjectFactory:
    """Factory for creating character value objects with type safety."""

    @staticmethod
    def create_character_profile_with_validation(
        name: str,
        gender: str,
        race: str,
        character_class: str,
        age: Union[int, str],
        level: Union[int, str],
        **kwargs,
    ):
        """Create CharacterProfile with type validation and conversion."""
        from ..domain.value_objects.character_profile import (
            Background,
            CharacterClass,
            CharacterProfile,
            CharacterRace,
            Gender,
            PersonalityTraits,
            PhysicalTraits,
        )

        # Type-safe enum conversions
        safe_gender = CharacterDomainTyping.safe_enum_conversion(
            Gender, gender
        )
        safe_race = CharacterDomainTyping.safe_enum_conversion(
            CharacterRace, race
        )
        safe_class = CharacterDomainTyping.safe_enum_conversion(
            CharacterClass, character_class
        )

        # Convert numeric fields
        safe_age = ensure_int(age)
        safe_level = ensure_int(level)

        # Extract optional parameters with defaults
        title = kwargs.get("title")
        affiliation = kwargs.get("affiliation")
        languages = kwargs.get("languages", [])
        if languages and not isinstance(languages, list):
            languages = (
                [languages] if isinstance(languages, str) else list(languages)
            )

        # Create physical traits
        physical_traits_data = kwargs.get("physical_traits", {})
        if isinstance(physical_traits_data, dict):
            physical_traits = PhysicalTraits(
                height_cm=physical_traits_data.get("height_cm"),
                weight_kg=physical_traits_data.get("weight_kg"),
                hair_color=physical_traits_data.get("hair_color"),
                eye_color=physical_traits_data.get("eye_color"),
                skin_tone=physical_traits_data.get("skin_tone"),
                distinguishing_marks=physical_traits_data.get(
                    "distinguishing_marks"
                ),
                physical_description=physical_traits_data.get(
                    "physical_description"
                ),
            )
        else:
            physical_traits = (
                physical_traits_data
                if physical_traits_data
                else PhysicalTraits()
            )

        # Create personality traits
        personality_traits_data = kwargs.get("personality_traits", {})
        if isinstance(personality_traits_data, dict):
            traits_dict = personality_traits_data.get(
                "traits",
                {
                    "courage": 0.5,
                    "intelligence": 0.5,
                    "charisma": 0.5,
                    "loyalty": 0.5,
                },
            )
            # Ensure trait scores are floats
            safe_traits = {k: ensure_float(v) for k, v in traits_dict.items()}

            personality_traits = PersonalityTraits(
                traits=safe_traits,
                alignment=personality_traits_data.get("alignment"),
                motivations=personality_traits_data.get("motivations"),
                fears=personality_traits_data.get("fears"),
                quirks=personality_traits_data.get("quirks"),
                ideals=personality_traits_data.get("ideals"),
                bonds=personality_traits_data.get("bonds"),
                flaws=personality_traits_data.get("flaws"),
            )
        else:
            personality_traits = (
                personality_traits_data
                if personality_traits_data
                else PersonalityTraits(
                    traits={
                        "courage": 0.5,
                        "intelligence": 0.5,
                        "charisma": 0.5,
                        "loyalty": 0.5,
                    }
                )
            )

        # Create background
        background_data = kwargs.get("background", {})
        if isinstance(background_data, dict):
            background = Background(
                backstory=background_data.get("backstory"),
                homeland=background_data.get("homeland"),
                family=background_data.get("family"),
                education=background_data.get("education"),
                previous_occupations=background_data.get(
                    "previous_occupations"
                ),
                significant_events=background_data.get("significant_events"),
                reputation=background_data.get("reputation"),
            )
        else:
            background = background_data if background_data else Background()

        return CharacterProfile(
            name=name,
            gender=safe_gender,
            race=safe_race,
            character_class=safe_class,
            age=safe_age,
            level=safe_level,
            physical_traits=physical_traits,
            personality_traits=personality_traits,
            background=background,
            title=title,
            affiliation=affiliation,
            languages=languages,
        )

    @staticmethod
    def create_character_stats_with_validation(
        strength: Union[int, str],
        dexterity: Union[int, str],
        constitution: Union[int, str],
        intelligence: Union[int, str],
        wisdom: Union[int, str],
        charisma: Union[int, str],
        **kwargs,
    ):
        """Create CharacterStats with type validation and conversion."""
        from ..domain.value_objects.character_stats import (
            CharacterStats,
            CombatStats,
            CoreAbilities,
            VitalStats,
        )

        # Convert core abilities
        core_abilities = CoreAbilities(
            strength=ensure_int(strength),
            dexterity=ensure_int(dexterity),
            constitution=ensure_int(constitution),
            intelligence=ensure_int(intelligence),
            wisdom=ensure_int(wisdom),
            charisma=ensure_int(charisma),
        )

        # Extract vital stats parameters
        vital_stats_data = kwargs.get("vital_stats", {})
        if isinstance(vital_stats_data, dict):
            vital_stats = VitalStats(
                max_health=ensure_int(vital_stats_data.get("max_health", 20)),
                current_health=ensure_int(
                    vital_stats_data.get("current_health", 20)
                ),
                max_mana=ensure_int(vital_stats_data.get("max_mana", 10)),
                current_mana=ensure_int(
                    vital_stats_data.get("current_mana", 10)
                ),
                max_stamina=ensure_int(
                    vital_stats_data.get("max_stamina", 15)
                ),
                current_stamina=ensure_int(
                    vital_stats_data.get("current_stamina", 15)
                ),
                armor_class=ensure_int(
                    vital_stats_data.get("armor_class", 10)
                ),
                speed=ensure_int(vital_stats_data.get("speed", 30)),
            )
        else:
            vital_stats = (
                vital_stats_data
                if vital_stats_data
                else VitalStats(
                    max_health=20,
                    current_health=20,
                    max_mana=10,
                    current_mana=10,
                    max_stamina=15,
                    current_stamina=15,
                    armor_class=10,
                    speed=30,
                )
            )

        # Extract combat stats parameters
        combat_stats_data = kwargs.get("combat_stats", {})
        if isinstance(combat_stats_data, dict):
            combat_stats = CombatStats(
                base_attack_bonus=ensure_int(
                    combat_stats_data.get("base_attack_bonus", 0)
                ),
                initiative_modifier=ensure_int(
                    combat_stats_data.get("initiative_modifier", 0)
                ),
                damage_reduction=ensure_int(
                    combat_stats_data.get("damage_reduction", 0)
                ),
                spell_resistance=ensure_int(
                    combat_stats_data.get("spell_resistance", 0)
                ),
                critical_hit_chance=ensure_float(
                    combat_stats_data.get("critical_hit_chance", 0.05)
                ),
                critical_damage_multiplier=ensure_float(
                    combat_stats_data.get("critical_damage_multiplier", 2.0)
                ),
            )
        else:
            combat_stats = (
                combat_stats_data
                if combat_stats_data
                else CombatStats(
                    base_attack_bonus=0,
                    initiative_modifier=0,
                    damage_reduction=0,
                    spell_resistance=0,
                    critical_hit_chance=0.05,
                    critical_damage_multiplier=2.0,
                )
            )

        return CharacterStats(
            core_abilities=core_abilities,
            vital_stats=vital_stats,
            combat_stats=combat_stats,
            experience_points=ensure_int(kwargs.get("experience_points", 0)),
            skill_points=ensure_int(kwargs.get("skill_points", 5)),
        )

    @staticmethod
    def create_skills_with_validation(
        skill_groups: Optional[Dict[Union[str, Any], Any]] = None, **kwargs
    ):
        """Create Skills with type validation and conversion."""
        from ..domain.value_objects.skills import SkillCategory, Skills

        if skill_groups is None:
            return Skills.create_basic_skills()

        # For now, return basic skills if conversion is complex
        # TODO: Implement proper skill group conversion from dict
        return Skills.create_basic_skills()


# Repository Type Safety Patterns (following P3 Sprint 2)
class RepositoryHelpers:
    """Type-safe helpers for repository operations."""

    @staticmethod
    def safe_entity_conversion(entity_data: Any, target_type: Type[T]) -> T:
        """Type-safe entity conversion with validation."""
        if entity_data is None:
            raise ValueError(f"Cannot convert None to {target_type.__name__}")

        if isinstance(entity_data, target_type):
            return entity_data

        # Apply type conversion based on target type
        return cast(T, entity_data)

    @staticmethod
    def safe_session_operation(
        session: "Session", operation_func, *args, **kwargs
    ):
        """Type-safe session operation with error handling."""
        try:
            result = operation_func(*args, **kwargs)
            return result
        except Exception as e:
            session.rollback()
            raise


# Domain Mapper Protocol (following P3 Sprint 2 patterns)
class DomainMapper(Protocol):
    """Protocol for type-safe domain mapping operations."""

    def entity_to_aggregate(self, entity: Any) -> "Character":
        """Convert entity to domain aggregate."""
        ...

    def aggregate_to_entity(self, aggregate: "Character") -> Any:
        """Convert domain aggregate to entity."""
        ...


# Character-specific Type Guards
class CharacterTypeGuards:
    """Character-specific type guards and validation."""

    @staticmethod
    def is_valid_character_name(name: Any) -> bool:
        """Check if name is valid for character."""
        return isinstance(name, str) and 1 <= len(name.strip()) <= 100

    @staticmethod
    def is_valid_age(age: Any) -> bool:
        """Check if age is valid for character."""
        try:
            age_int = ensure_int(age)
            return 0 <= age_int <= 10000
        except (TypeError, ValueError):
            return False

    @staticmethod
    def is_valid_level(level: Any) -> bool:
        """Check if level is valid for character."""
        try:
            level_int = ensure_int(level)
            return 1 <= level_int <= 100
        except (TypeError, ValueError):
            return False

    @staticmethod
    def is_valid_ability_score(score: Any) -> bool:
        """Check if ability score is valid."""
        try:
            score_int = ensure_int(score)
            return 1 <= score_int <= 30
        except (TypeError, ValueError):
            return False

    @staticmethod
    def is_valid_health(health: Any) -> bool:
        """Check if health value is valid."""
        try:
            health_int = ensure_int(health)
            return health_int >= 0
        except (TypeError, ValueError):
            return False


# Export all patterns
__all__ = [
    "ensure_not_none",
    "ensure_uuid",
    "ensure_decimal",
    "ensure_int",
    "ensure_float",
    "CharacterDomainTyping",
    "ValueObjectFactory",
    "RepositoryHelpers",
    "DomainMapper",
    "CharacterTypeGuards",
]
