#!/usr/bin/env python3
"""
Character Infrastructure SQLAlchemy Type Pattern Solutions

This module provides specialized type patterns to resolve Column[T] vs T type conflicts
and other SQLAlchemy integration issues with MyPy static analysis for character domain.

P3 Sprint 3 Character-Specific ORM Type Patterns:
1. Character Model Base Pattern: Properly typed base class for character models
2. Character Value Object Converters: Type-safe character value object mapping
3. Character Repository Pattern: SQLAlchemy method compatibility fixes
4. Character Domain Mapping: Enhanced converter type hints for character data
"""

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

# SQLAlchemy imports with proper type annotations
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreUUID
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause

# Import core platform patterns
from ....core_platform.persistence.sqlalchemy_types import (
    RepositoryHelpers,
    SQLAlchemyTyping,
    TimestampMixin,
    VersionMixin,
    ensure_not_none,
    safe_column_access,
)

# Type variables for generic patterns
T = TypeVar("T")
CharacterModelType = TypeVar("CharacterModelType", bound="CharacterModelBase")

# P3 Sprint 3 Pattern 1: Character Model Base Pattern
# Resolves: Character-specific SQLAlchemy model typing issues

# Properly typed base class for character models using TYPE_CHECKING guard
if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

    CharacterModelBase = DeclarativeBase
else:
    CharacterModelBase = declarative_base()

# P3 Sprint 3 Pattern: Column Mapping Mixin
# Resolves: Type-safe column mapping for character models


class ColumnMappingMixin:
    """Mixin providing type-safe column mapping methods."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        result = {}
        if hasattr(self, "__table__") and hasattr(self.__table__, "columns"):
            for column in self.__table__.columns:
                result[column.name] = getattr(self, column.name)
        return result

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model instance from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


# P3 Sprint 3 Pattern 2: Character Value Object Converters
# Resolves: Type-safe character value object to/from SQLAlchemy conversion


class CharacterValueObjectConverters:
    """Character-specific value object converters with type safety."""

    @staticmethod
    def character_profile_to_dict(profile: Any) -> Optional[Dict[str, Any]]:
        """Convert CharacterProfile to dictionary for storage."""
        if profile is None:
            return None

        try:
            return {
                "name": profile.name,
                "gender": profile.gender.value
                if hasattr(profile.gender, "value")
                else str(profile.gender),
                "race": profile.race.value
                if hasattr(profile.race, "value")
                else str(profile.race),
                "character_class": profile.character_class.value
                if hasattr(profile.character_class, "value")
                else str(profile.character_class),
                "age": profile.age,
                "level": profile.level,
                "title": profile.title,
                "affiliation": profile.affiliation,
                "languages": profile.languages,
                "physical_traits": CharacterValueObjectConverters._physical_traits_to_dict(
                    profile.physical_traits
                ),
                "personality_traits": CharacterValueObjectConverters._personality_traits_to_dict(
                    profile.personality_traits
                ),
                "background": CharacterValueObjectConverters._background_to_dict(
                    profile.background
                ),
            }
        except Exception:
            return None

    @staticmethod
    def dict_to_character_profile(data: Optional[Dict[str, Any]]) -> Any:
        """Convert dictionary to CharacterProfile."""
        if data is None:
            return None

        try:
            from ..infrastructure.character_domain_types import (
                ValueObjectFactory,
            )

            return ValueObjectFactory.create_character_profile_with_validation(
                name=data.get("name", ""),
                gender=data.get("gender", "unspecified"),
                race=data.get("race", "human"),
                character_class=data.get("character_class", "other"),
                age=data.get("age", 18),
                level=data.get("level", 1),
                title=data.get("title"),
                affiliation=data.get("affiliation"),
                languages=data.get("languages", []),
                physical_traits=data.get("physical_traits", {}),
                personality_traits=data.get("personality_traits", {}),
                background=data.get("background", {}),
            )
        except Exception:
            return None

    @staticmethod
    def character_stats_to_dict(stats: Any) -> Optional[Dict[str, Any]]:
        """Convert CharacterStats to dictionary for storage."""
        if stats is None:
            return None

        try:
            return {
                "core_abilities": {
                    "strength": stats.core_abilities.strength,
                    "dexterity": stats.core_abilities.dexterity,
                    "constitution": stats.core_abilities.constitution,
                    "intelligence": stats.core_abilities.intelligence,
                    "wisdom": stats.core_abilities.wisdom,
                    "charisma": stats.core_abilities.charisma,
                },
                "vital_stats": {
                    "max_health": stats.vital_stats.max_health,
                    "current_health": stats.vital_stats.current_health,
                    "max_mana": stats.vital_stats.max_mana,
                    "current_mana": stats.vital_stats.current_mana,
                    "max_stamina": stats.vital_stats.max_stamina,
                    "current_stamina": stats.vital_stats.current_stamina,
                    "armor_class": stats.vital_stats.armor_class,
                    "speed": stats.vital_stats.speed,
                },
                "combat_stats": {
                    "base_attack_bonus": stats.combat_stats.base_attack_bonus,
                    "initiative_modifier": stats.combat_stats.initiative_modifier,
                    "damage_reduction": stats.combat_stats.damage_reduction,
                    "spell_resistance": stats.combat_stats.spell_resistance,
                    "critical_hit_chance": float(
                        stats.combat_stats.critical_hit_chance
                    ),
                    "critical_damage_multiplier": float(
                        stats.combat_stats.critical_damage_multiplier
                    ),
                },
                "experience_points": stats.experience_points,
                "skill_points": stats.skill_points,
            }
        except Exception:
            return None

    @staticmethod
    def dict_to_character_stats(data: Optional[Dict[str, Any]]) -> Any:
        """Convert dictionary to CharacterStats."""
        if data is None:
            return None

        try:
            from ..infrastructure.character_domain_types import (
                ValueObjectFactory,
            )

            # Extract core abilities
            core_abilities = data.get("core_abilities", {})

            return ValueObjectFactory.create_character_stats_with_validation(
                strength=core_abilities.get("strength", 10),
                dexterity=core_abilities.get("dexterity", 10),
                constitution=core_abilities.get("constitution", 10),
                intelligence=core_abilities.get("intelligence", 10),
                wisdom=core_abilities.get("wisdom", 10),
                charisma=core_abilities.get("charisma", 10),
                vital_stats=data.get("vital_stats", {}),
                combat_stats=data.get("combat_stats", {}),
                experience_points=data.get("experience_points", 0),
                skill_points=data.get("skill_points", 5),
            )
        except Exception:
            return None

    @staticmethod
    def skills_to_dict(skills: Any) -> Optional[Dict[str, Any]]:
        """Convert Skills to dictionary for storage."""
        if skills is None:
            return None

        try:
            skill_groups_dict = {}
            for category, skill_list in skills.skill_groups.items():
                category_name = (
                    category.value
                    if hasattr(category, "value")
                    else str(category)
                )
                skill_groups_dict[category_name] = [
                    {
                        "name": skill.name,
                        "proficiency_level": skill.proficiency_level,
                        "base_value": skill.base_value,
                        "experience": skill.experience,
                        "description": skill.description,
                    }
                    for skill in skill_list
                ]

            return {
                "skill_groups": skill_groups_dict,
                "total_skill_points": getattr(skills, "total_skill_points", 0),
            }
        except Exception:
            return None

    @staticmethod
    def dict_to_skills(data: Optional[Dict[str, Any]]) -> Any:
        """Convert dictionary to Skills."""
        if data is None:
            return None

        try:
            from ..infrastructure.character_domain_types import (
                ValueObjectFactory,
            )

            return ValueObjectFactory.create_skills_with_validation(
                skill_groups=data.get("skill_groups", {})
            )
        except Exception:
            return None

    # Helper methods for nested objects
    @staticmethod
    def _physical_traits_to_dict(traits: Any) -> Dict[str, Any]:
        """Convert PhysicalTraits to dictionary."""
        if traits is None:
            return {}

        return {
            "height_cm": traits.height_cm,
            "weight_kg": traits.weight_kg,
            "hair_color": traits.hair_color,
            "eye_color": traits.eye_color,
            "skin_tone": traits.skin_tone,
            "distinguishing_marks": traits.distinguishing_marks,
            "physical_description": traits.physical_description,
        }

    @staticmethod
    def _personality_traits_to_dict(traits: Any) -> Dict[str, Any]:
        """Convert PersonalityTraits to dictionary."""
        if traits is None:
            return {}

        return {
            "traits": traits.traits,
            "alignment": traits.alignment,
            "motivations": traits.motivations,
            "fears": traits.fears,
            "quirks": traits.quirks,
            "ideals": traits.ideals,
            "bonds": traits.bonds,
            "flaws": traits.flaws,
        }

    @staticmethod
    def _background_to_dict(background: Any) -> Dict[str, Any]:
        """Convert Background to dictionary."""
        if background is None:
            return {}

        return {
            "backstory": background.backstory,
            "homeland": background.homeland,
            "family": background.family,
            "education": background.education,
            "previous_occupations": background.previous_occupations,
            "significant_events": background.significant_events,
            "reputation": background.reputation,
        }


# P3 Sprint 3 Pattern 3: Character Repository Pattern Extensions
# Resolves: Character-specific repository method typing issues


class CharacterRepositoryHelpers(RepositoryHelpers):
    """Character-specific repository helpers extending base patterns."""

    @staticmethod
    def safe_character_query_with_filters(
        session: Any,
        model_class: Type[CharacterModelType],
        filters: Dict[str, Any],
    ) -> Any:
        """Type-safe character query with filters."""
        query = session.query(model_class)

        for field, value in filters.items():
            if value is not None:
                if hasattr(model_class, field):
                    column = getattr(model_class, field)
                    query = query.filter(column == value)

        return query

    @staticmethod
    def safe_character_aggregate_query(
        session: Any,
        model_class: Type[CharacterModelType],
        group_by_field: str,
    ) -> Dict[str, int]:
        """Type-safe character aggregate query."""
        try:
            if hasattr(model_class, group_by_field):
                column = getattr(model_class, group_by_field)
                query = session.query(
                    column, session.query.func.count()
                ).group_by(column)
                rows = query.all()
                return dict(rows)
        except Exception:
            pass
        return {}


# P3 Sprint 3 Pattern 4: Character Model Update Pattern
# Resolves: Character-specific model update method typing


class CharacterModelUpdatePattern:
    """Character-specific model update patterns."""

    @staticmethod
    def update_character_model_from_aggregate(
        model_instance: Any, character_aggregate: Any
    ) -> None:
        """Type-safe character model update from domain aggregate."""
        field_mappings = {
            "character_id": "character_id.value"
            if hasattr(character_aggregate.character_id, "value")
            else "character_id",
            "profile_data": "profile",
            "stats_data": "stats",
            "skills_data": "skills",
            "created_at": "created_at",
            "updated_at": "updated_at",
            "version": "version",
        }

        # Handle complex value object conversions
        conversions = {}

        # Convert profile to JSON
        if hasattr(character_aggregate, "profile"):
            conversions[
                "profile_data"
            ] = CharacterValueObjectConverters.character_profile_to_dict(
                character_aggregate.profile
            )

        # Convert stats to JSON
        if hasattr(character_aggregate, "stats"):
            conversions[
                "stats_data"
            ] = CharacterValueObjectConverters.character_stats_to_dict(
                character_aggregate.stats
            )

        # Convert skills to JSON
        if hasattr(character_aggregate, "skills"):
            conversions[
                "skills_data"
            ] = CharacterValueObjectConverters.skills_to_dict(
                character_aggregate.skills
            )

        # Apply standard field mappings
        for model_field, aggregate_field in field_mappings.items():
            if hasattr(character_aggregate, aggregate_field.split(".")[0]):
                # Handle nested field access
                value = character_aggregate
                for field_part in aggregate_field.split("."):
                    value = getattr(value, field_part, None)
                    if value is None:
                        break

                if value is not None and hasattr(model_instance, model_field):
                    object.__setattr__(model_instance, model_field, value)

        # Apply complex conversions
        for field, value in conversions.items():
            if hasattr(model_instance, field):
                object.__setattr__(model_instance, field, value)


# P3 Sprint 3 Pattern 5: Character Query Builder Pattern
# Resolves: Character-specific query construction with proper typing


class CharacterQueryBuilderPattern:
    """Character-specific query building with proper type safety."""

    @staticmethod
    def build_character_search_filters(
        search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build character search filters from parameters."""
        filters = {}

        # Handle character-specific search parameters
        if "name" in search_params and search_params["name"]:
            filters["name_like"] = f"%{search_params['name']}%"

        if "level_min" in search_params and search_params["level_min"]:
            filters["level_gte"] = search_params["level_min"]

        if "level_max" in search_params and search_params["level_max"]:
            filters["level_lte"] = search_params["level_max"]

        if "race" in search_params and search_params["race"]:
            filters["race"] = search_params["race"]

        if (
            "character_class" in search_params
            and search_params["character_class"]
        ):
            filters["character_class"] = search_params["character_class"]

        if "is_alive" in search_params:
            filters["is_alive"] = search_params["is_alive"]

        return filters

    @staticmethod
    def build_character_stats_query(
        stats_filters: Dict[str, Any]
    ) -> List[str]:
        """Build WHERE clause for character stats queries."""
        clauses = []

        for stat_name, criteria in stats_filters.items():
            if isinstance(criteria, dict):
                if "min" in criteria:
                    clauses.append(
                        f"JSON_EXTRACT(stats_data, '$.core_abilities.{stat_name}') >= :{stat_name}_min"
                    )
                if "max" in criteria:
                    clauses.append(
                        f"JSON_EXTRACT(stats_data, '$.core_abilities.{stat_name}') <= :{stat_name}_max"
                    )
            else:
                clauses.append(
                    f"JSON_EXTRACT(stats_data, '$.core_abilities.{stat_name}') = :{stat_name}"
                )

        return clauses


# Export the character-specific patterns
__all__ = [
    "CharacterModelBase",
    "ColumnMappingMixin",
    "CharacterValueObjectConverters",
    "CharacterRepositoryHelpers",
    "CharacterModelUpdatePattern",
    "CharacterQueryBuilderPattern",
]
