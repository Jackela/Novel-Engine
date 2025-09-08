#!/usr/bin/env python3
"""
SQLAlchemy Character Repository Implementation

This module provides a concrete implementation of ICharacterRepository
using SQLAlchemy ORM for data persistence. It handles the mapping between
domain objects and database entities.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ...domain.aggregates.character import Character
from ...domain.repositories.character_repository import (
    ConcurrencyException,
    ICharacterRepository,
    RepositoryException,
)
from ...domain.value_objects.character_id import CharacterID
from ...domain.value_objects.character_profile import (
    Background,
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
    PersonalityTraits,
    PhysicalTraits,
)
from ...domain.value_objects.character_stats import (
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from ...domain.value_objects.skills import (
    ProficiencyLevel,
    Skill,
    SkillCategory,
    SkillGroup,
    Skills,
)
from ..persistence.character_models import (
    CharacterEventORM,
    CharacterORM,
    CharacterProfileORM,
    CharacterSkillsORM,
    CharacterStatsORM,
)

logger = logging.getLogger(__name__)


class SQLAlchemyCharacterRepository(ICharacterRepository):
    """
    SQLAlchemy-based implementation of the Character repository.

    This repository provides persistence capabilities for Character
    aggregates using SQLAlchemy ORM and relational database storage.
    """

    def __init__(self, session_factory: sessionmaker):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: SQLAlchemy session factory for database connections
        """
        self.session_factory = session_factory
        self.logger = logger.getChild(self.__class__.__name__)

    # ==================== Basic CRUD Operations ====================

    async def get_by_id(self, character_id: CharacterID) -> Optional[Character]:
        """Retrieve a character by their unique identifier."""
        try:
            with self.session_factory() as session:
                character_orm = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.character_id == character_id.value)
                    .first()
                )

                if not character_orm:
                    return None

                return self._map_orm_to_domain(character_orm)

        except SQLAlchemyError as e:
            self.logger.error(f"Error retrieving character {character_id}: {e}")
            raise RepositoryException(f"Failed to retrieve character: {e}")

    async def save(self, character: Character) -> None:
        """Save a character aggregate to the repository."""
        try:
            with self.session_factory() as session:
                # Check if character exists
                existing_orm = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.character_id == character.character_id.value)
                    .first()
                )

                if existing_orm:
                    # Update existing character
                    if existing_orm.version != character.version - 1:
                        raise ConcurrencyException(
                            f"Version conflict for character {character.character_id}",
                            character.version - 1,
                            existing_orm.version,
                        )

                    self._update_orm_from_domain(existing_orm, character, session)
                    existing_orm.version = character.version
                    existing_orm.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new character
                    character_orm = self._map_domain_to_orm(character)
                    session.add(character_orm)

                # Save any pending domain events
                if character.get_events():
                    for event in character.get_events():
                        event_orm = CharacterEventORM(
                            character_id=character.character_id.value,
                            event_type=event.__class__.__name__,
                            event_version=1,
                            event_data=event.to_dict(),
                            aggregate_version=character.version,
                            correlation_id=getattr(event, "correlation_id", None),
                            occurred_at=event.occurred_at,
                        )
                        session.add(event_orm)

                session.commit()
                character.clear_events()

        except ConcurrencyException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Error saving character {character.character_id}: {e}")
            raise RepositoryException(f"Failed to save character: {e}")

    async def delete(self, character_id: CharacterID) -> bool:
        """Delete a character from the repository."""
        try:
            with self.session_factory() as session:
                character_orm = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.character_id == character_id.value)
                    .first()
                )

                if not character_orm:
                    return False

                session.delete(character_orm)
                session.commit()
                return True

        except SQLAlchemyError as e:
            self.logger.error(f"Error deleting character {character_id}: {e}")
            raise RepositoryException(f"Failed to delete character: {e}")

    async def exists(self, character_id: CharacterID) -> bool:
        """Check if a character exists in the repository."""
        try:
            with self.session_factory() as session:
                exists = session.query(
                    session.query(CharacterORM)
                    .filter(CharacterORM.character_id == character_id.value)
                    .exists()
                ).scalar()

                return exists

        except SQLAlchemyError as e:
            self.logger.error(f"Error checking character existence {character_id}: {e}")
            raise RepositoryException(f"Failed to check character existence: {e}")

    # ==================== Query Operations ====================

    async def find_by_name(self, name: str) -> List[Character]:
        """Find characters by name (supports partial matching)."""
        try:
            with self.session_factory() as session:
                character_orms = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.name.ilike(f"%{name}%"))
                    .all()
                )

                return [self._map_orm_to_domain(orm) for orm in character_orms]

        except SQLAlchemyError as e:
            self.logger.error(f"Error finding characters by name '{name}': {e}")
            raise RepositoryException(f"Failed to find characters by name: {e}")

    async def find_by_class(self, character_class: CharacterClass) -> List[Character]:
        """Find all characters of a specific class."""
        try:
            with self.session_factory() as session:
                character_orms = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.character_class == character_class.value)
                    .all()
                )

                return [self._map_orm_to_domain(orm) for orm in character_orms]

        except SQLAlchemyError as e:
            self.logger.error(
                f"Error finding characters by class {character_class}: {e}"
            )
            raise RepositoryException(f"Failed to find characters by class: {e}")

    async def find_by_race(self, race: CharacterRace) -> List[Character]:
        """Find all characters of a specific race."""
        try:
            with self.session_factory() as session:
                character_orms = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.race == race.value)
                    .all()
                )

                return [self._map_orm_to_domain(orm) for orm in character_orms]

        except SQLAlchemyError as e:
            self.logger.error(f"Error finding characters by race {race}: {e}")
            raise RepositoryException(f"Failed to find characters by race: {e}")

    async def find_by_level_range(
        self, min_level: int, max_level: int
    ) -> List[Character]:
        """Find characters within a level range."""
        try:
            with self.session_factory() as session:
                character_orms = (
                    session.query(CharacterORM)
                    .filter(
                        and_(
                            CharacterORM.level >= min_level,
                            CharacterORM.level <= max_level,
                        )
                    )
                    .all()
                )

                return [self._map_orm_to_domain(orm) for orm in character_orms]

        except SQLAlchemyError as e:
            self.logger.error(
                f"Error finding characters by level range {min_level}-{max_level}: {e}"
            )
            raise RepositoryException(f"Failed to find characters by level range: {e}")

    async def find_alive_characters(self) -> List[Character]:
        """Find all characters that are currently alive."""
        try:
            with self.session_factory() as session:
                character_orms = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.is_alive is True)
                    .all()
                )

                return [self._map_orm_to_domain(orm) for orm in character_orms]

        except SQLAlchemyError as e:
            self.logger.error(f"Error finding alive characters: {e}")
            raise RepositoryException(f"Failed to find alive characters: {e}")

    async def find_by_created_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Character]:
        """Find characters created within a date range."""
        try:
            with self.session_factory() as session:
                character_orms = (
                    session.query(CharacterORM)
                    .filter(
                        and_(
                            CharacterORM.created_at >= start_date,
                            CharacterORM.created_at <= end_date,
                        )
                    )
                    .all()
                )

                return [self._map_orm_to_domain(orm) for orm in character_orms]

        except SQLAlchemyError as e:
            self.logger.error(f"Error finding characters by date range: {e}")
            raise RepositoryException(f"Failed to find characters by date range: {e}")

    # ==================== Advanced Query Operations ====================

    async def find_by_criteria(
        self, criteria: Dict[str, Any], limit: Optional[int] = None, offset: int = 0
    ) -> List[Character]:
        """Find characters matching multiple criteria."""
        try:
            with self.session_factory() as session:
                query = session.query(CharacterORM)

                # Apply criteria filters
                for field, value in criteria.items():
                    if hasattr(CharacterORM, field):
                        if isinstance(value, list):
                            query = query.filter(
                                getattr(CharacterORM, field).in_(value)
                            )
                        else:
                            query = query.filter(getattr(CharacterORM, field) == value)

                # Apply pagination
                if offset > 0:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)

                character_orms = query.all()
                return [self._map_orm_to_domain(orm) for orm in character_orms]

        except SQLAlchemyError as e:
            self.logger.error(f"Error finding characters by criteria: {e}")
            raise RepositoryException(f"Failed to find characters by criteria: {e}")

    async def count_by_criteria(self, criteria: Dict[str, Any]) -> int:
        """Count characters matching specific criteria."""
        try:
            with self.session_factory() as session:
                query = session.query(CharacterORM)

                # Apply criteria filters
                for field, value in criteria.items():
                    if hasattr(CharacterORM, field):
                        if isinstance(value, list):
                            query = query.filter(
                                getattr(CharacterORM, field).in_(value)
                            )
                        else:
                            query = query.filter(getattr(CharacterORM, field) == value)

                return query.count()

        except SQLAlchemyError as e:
            self.logger.error(f"Error counting characters by criteria: {e}")
            raise RepositoryException(f"Failed to count characters by criteria: {e}")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistical information about characters in the repository."""
        try:
            with self.session_factory() as session:
                # Total characters
                total_characters = session.query(CharacterORM).count()

                # Characters by class
                class_stats = (
                    session.query(
                        CharacterORM.character_class,
                        func.count(CharacterORM.character_id),
                    )
                    .group_by(CharacterORM.character_class)
                    .all()
                )

                # Characters by race
                race_stats = (
                    session.query(
                        CharacterORM.race, func.count(CharacterORM.character_id)
                    )
                    .group_by(CharacterORM.race)
                    .all()
                )

                # Level statistics
                avg_level = session.query(func.avg(CharacterORM.level)).scalar() or 0
                level_distribution = (
                    session.query(
                        CharacterORM.level, func.count(CharacterORM.character_id)
                    )
                    .group_by(CharacterORM.level)
                    .all()
                )

                # Alive characters
                alive_characters = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.is_alive is True)
                    .count()
                )

                return {
                    "total_characters": total_characters,
                    "characters_by_class": dict(class_stats),
                    "characters_by_race": dict(race_stats),
                    "average_level": float(avg_level),
                    "level_distribution": dict(level_distribution),
                    "alive_characters": alive_characters,
                }

        except SQLAlchemyError as e:
            self.logger.error(f"Error getting character statistics: {e}")
            raise RepositoryException(f"Failed to get character statistics: {e}")

    # ==================== Bulk Operations ====================

    async def save_multiple(self, characters: List[Character]) -> None:
        """Save multiple characters in a single transaction."""
        try:
            with self.session_factory() as session:
                for character in characters:
                    # Check concurrency for existing characters
                    existing_orm = (
                        session.query(CharacterORM)
                        .filter(
                            CharacterORM.character_id == character.character_id.value
                        )
                        .first()
                    )

                    if existing_orm:
                        if existing_orm.version != character.version - 1:
                            raise ConcurrencyException(
                                f"Version conflict for character {character.character_id}",
                                character.version - 1,
                                existing_orm.version,
                            )
                        self._update_orm_from_domain(existing_orm, character, session)
                        existing_orm.version = character.version
                        existing_orm.updated_at = datetime.now(timezone.utc)
                    else:
                        character_orm = self._map_domain_to_orm(character)
                        session.add(character_orm)

                session.commit()

                # Clear events from all characters
                for character in characters:
                    character.clear_events()

        except ConcurrencyException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Error saving multiple characters: {e}")
            raise RepositoryException(f"Failed to save multiple characters: {e}")

    async def delete_multiple(self, character_ids: List[CharacterID]) -> int:
        """Delete multiple characters in a single transaction."""
        try:
            with self.session_factory() as session:
                id_values = [char_id.value for char_id in character_ids]

                deleted_count = (
                    session.query(CharacterORM)
                    .filter(CharacterORM.character_id.in_(id_values))
                    .count()
                )

                session.query(CharacterORM).filter(
                    CharacterORM.character_id.in_(id_values)
                ).delete(synchronize_session=False)

                session.commit()
                return deleted_count

        except SQLAlchemyError as e:
            self.logger.error(f"Error deleting multiple characters: {e}")
            raise RepositoryException(f"Failed to delete multiple characters: {e}")

    # ==================== Version Control Operations ====================

    async def get_version(self, character_id: CharacterID) -> Optional[int]:
        """Get the current version of a character without loading the full aggregate."""
        try:
            with self.session_factory() as session:
                version = (
                    session.query(CharacterORM.version)
                    .filter(CharacterORM.character_id == character_id.value)
                    .scalar()
                )

                return version

        except SQLAlchemyError as e:
            self.logger.error(f"Error getting character version {character_id}: {e}")
            raise RepositoryException(f"Failed to get character version: {e}")

    async def get_character_history(
        self, character_id: CharacterID, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get the change history for a character."""
        try:
            with self.session_factory() as session:
                query = (
                    session.query(CharacterEventORM)
                    .filter(CharacterEventORM.character_id == character_id.value)
                    .order_by(CharacterEventORM.occurred_at.desc())
                )

                if limit:
                    query = query.limit(limit)

                events = query.all()

                return [
                    {
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "aggregate_version": event.aggregate_version,
                        "occurred_at": event.occurred_at.isoformat(),
                        "correlation_id": event.correlation_id,
                    }
                    for event in events
                ]

        except SQLAlchemyError as e:
            self.logger.error(f"Error getting character history {character_id}: {e}")
            raise RepositoryException(f"Failed to get character history: {e}")

    # ==================== Private Mapping Methods ====================

    def _map_domain_to_orm(self, character: Character) -> CharacterORM:
        """Map a domain Character to ORM model."""
        character_orm = CharacterORM(
            character_id=character.character_id.value,
            name=character.profile.name,
            gender=character.profile.gender.value,
            race=character.profile.race.value,
            character_class=character.profile.character_class.value,
            age=character.profile.age,
            level=character.profile.level,
            is_alive=character.is_alive(),
            version=character.version,
            created_at=character.created_at,
            updated_at=character.updated_at,
        )

        # Create profile ORM
        profile_orm = CharacterProfileORM(
            character_id=character.character_id.value,
            title=character.profile.title,
            affiliation=character.profile.affiliation,
            languages=character.profile.languages,
            height_cm=character.profile.physical_traits.height_cm,
            weight_kg=character.profile.physical_traits.weight_kg,
            hair_color=character.profile.physical_traits.hair_color,
            eye_color=character.profile.physical_traits.eye_color,
            skin_tone=character.profile.physical_traits.skin_tone,
            physical_description=character.profile.physical_traits.physical_description,
            personality_traits=character.profile.personality_traits.traits,
            backstory=character.profile.background.backstory,
            homeland=character.profile.background.homeland,
            education=character.profile.background.education,
        )

        # Create stats ORM
        stats_orm = CharacterStatsORM(
            character_id=character.character_id.value,
            strength=character.stats.core_abilities.strength,
            dexterity=character.stats.core_abilities.dexterity,
            constitution=character.stats.core_abilities.constitution,
            intelligence=character.stats.core_abilities.intelligence,
            wisdom=character.stats.core_abilities.wisdom,
            charisma=character.stats.core_abilities.charisma,
            max_health=character.stats.vital_stats.max_health,
            current_health=character.stats.vital_stats.current_health,
            max_mana=character.stats.vital_stats.max_mana,
            current_mana=character.stats.vital_stats.current_mana,
            max_stamina=character.stats.vital_stats.max_stamina,
            current_stamina=character.stats.vital_stats.current_stamina,
            armor_class=character.stats.vital_stats.armor_class,
            speed=character.stats.vital_stats.speed,
            base_attack_bonus=character.stats.combat_stats.base_attack_bonus,
            initiative_modifier=character.stats.combat_stats.initiative_modifier,
            damage_reduction=character.stats.combat_stats.damage_reduction,
            spell_resistance=character.stats.combat_stats.spell_resistance,
            critical_hit_chance=character.stats.combat_stats.critical_hit_chance,
            critical_damage_multiplier=character.stats.combat_stats.critical_damage_multiplier,
            experience_points=character.stats.experience_points,
            skill_points=character.stats.skill_points,
        )

        # Create skills ORM
        skill_groups_data = {}
        for category, skill_group in character.skills.skill_groups.items():
            skill_groups_data[category.value] = {
                skill_name: {
                    "proficiency_level": skill.proficiency_level.value,
                    "modifier": skill.modifier,
                    "description": skill.description,
                }
                for skill_name, skill in skill_group.skills.items()
            }

        skills_orm = CharacterSkillsORM(
            character_id=character.character_id.value,
            skill_groups=skill_groups_data,
            languages=character.skills.languages,
            specializations=character.skills.specializations,
        )

        # Set up relationships
        character_orm.profile = profile_orm
        character_orm.stats = stats_orm
        character_orm.skills = skills_orm

        return character_orm

    def _update_orm_from_domain(
        self, character_orm: CharacterORM, character: Character, session: Session
    ) -> None:
        """Update existing ORM model from domain object."""
        # Update main character fields
        character_orm.name = character.profile.name
        character_orm.gender = character.profile.gender.value
        character_orm.race = character.profile.race.value
        character_orm.character_class = character.profile.character_class.value
        character_orm.age = character.profile.age
        character_orm.level = character.profile.level
        character_orm.is_alive = character.is_alive()

        # Update profile if exists, create if not
        if not character_orm.profile:
            profile_orm = CharacterProfileORM(character_id=character.character_id.value)
            character_orm.profile = profile_orm

        profile = character_orm.profile
        profile.title = character.profile.title
        profile.affiliation = character.profile.affiliation
        profile.languages = character.profile.languages
        profile.height_cm = character.profile.physical_traits.height_cm
        profile.weight_kg = character.profile.physical_traits.weight_kg
        profile.hair_color = character.profile.physical_traits.hair_color
        profile.eye_color = character.profile.physical_traits.eye_color
        profile.skin_tone = character.profile.physical_traits.skin_tone
        profile.physical_description = (
            character.profile.physical_traits.physical_description
        )
        profile.personality_traits = character.profile.personality_traits.traits
        profile.backstory = character.profile.background.backstory
        profile.homeland = character.profile.background.homeland
        profile.education = character.profile.background.education

        # Update stats if exists, create if not
        if not character_orm.stats:
            stats_orm = CharacterStatsORM(character_id=character.character_id.value)
            character_orm.stats = stats_orm

        stats = character_orm.stats
        stats.strength = character.stats.core_abilities.strength
        stats.dexterity = character.stats.core_abilities.dexterity
        stats.constitution = character.stats.core_abilities.constitution
        stats.intelligence = character.stats.core_abilities.intelligence
        stats.wisdom = character.stats.core_abilities.wisdom
        stats.charisma = character.stats.core_abilities.charisma
        stats.max_health = character.stats.vital_stats.max_health
        stats.current_health = character.stats.vital_stats.current_health
        stats.max_mana = character.stats.vital_stats.max_mana
        stats.current_mana = character.stats.vital_stats.current_mana
        stats.max_stamina = character.stats.vital_stats.max_stamina
        stats.current_stamina = character.stats.vital_stats.current_stamina
        stats.armor_class = character.stats.vital_stats.armor_class
        stats.speed = character.stats.vital_stats.speed
        stats.base_attack_bonus = character.stats.combat_stats.base_attack_bonus
        stats.initiative_modifier = character.stats.combat_stats.initiative_modifier
        stats.damage_reduction = character.stats.combat_stats.damage_reduction
        stats.spell_resistance = character.stats.combat_stats.spell_resistance
        stats.critical_hit_chance = character.stats.combat_stats.critical_hit_chance
        stats.critical_damage_multiplier = (
            character.stats.combat_stats.critical_damage_multiplier
        )
        stats.experience_points = character.stats.experience_points
        stats.skill_points = character.stats.skill_points

        # Update skills if exists, create if not
        if not character_orm.skills:
            skills_orm = CharacterSkillsORM(character_id=character.character_id.value)
            character_orm.skills = skills_orm

        skill_groups_data = {}
        for category, skill_group in character.skills.skill_groups.items():
            skill_groups_data[category.value] = {
                skill_name: {
                    "proficiency_level": skill.proficiency_level.value,
                    "modifier": skill.modifier,
                    "description": skill.description,
                }
                for skill_name, skill in skill_group.skills.items()
            }

        skills = character_orm.skills
        skills.skill_groups = skill_groups_data
        skills.languages = character.skills.languages
        skills.specializations = character.skills.specializations

    def _map_orm_to_domain(self, character_orm: CharacterORM) -> Character:
        """Map an ORM model to domain Character."""
        # Map profile
        physical_traits = PhysicalTraits(
            height_cm=character_orm.profile.height_cm,
            weight_kg=character_orm.profile.weight_kg,
            hair_color=character_orm.profile.hair_color,
            eye_color=character_orm.profile.eye_color,
            skin_tone=character_orm.profile.skin_tone,
            physical_description=character_orm.profile.physical_description,
        )

        personality_traits = PersonalityTraits(
            traits=character_orm.profile.personality_traits or {}
        )

        background = Background(
            backstory=character_orm.profile.backstory,
            homeland=character_orm.profile.homeland,
            education=character_orm.profile.education,
        )

        profile = CharacterProfile(
            name=character_orm.name,
            gender=Gender(character_orm.gender),
            race=CharacterRace(character_orm.race),
            character_class=CharacterClass(character_orm.character_class),
            age=character_orm.age,
            level=character_orm.level,
            physical_traits=physical_traits,
            personality_traits=personality_traits,
            background=background,
            title=character_orm.profile.title,
            affiliation=character_orm.profile.affiliation,
            languages=character_orm.profile.languages or [],
        )

        # Map stats
        core_abilities = CoreAbilities(
            strength=character_orm.stats.strength,
            dexterity=character_orm.stats.dexterity,
            constitution=character_orm.stats.constitution,
            intelligence=character_orm.stats.intelligence,
            wisdom=character_orm.stats.wisdom,
            charisma=character_orm.stats.charisma,
        )

        vital_stats = VitalStats(
            max_health=character_orm.stats.max_health,
            current_health=character_orm.stats.current_health,
            max_mana=character_orm.stats.max_mana,
            current_mana=character_orm.stats.current_mana,
            max_stamina=character_orm.stats.max_stamina,
            current_stamina=character_orm.stats.current_stamina,
            armor_class=character_orm.stats.armor_class,
            speed=character_orm.stats.speed,
        )

        combat_stats = CombatStats(
            base_attack_bonus=character_orm.stats.base_attack_bonus,
            initiative_modifier=character_orm.stats.initiative_modifier,
            damage_reduction=character_orm.stats.damage_reduction,
            spell_resistance=character_orm.stats.spell_resistance,
            critical_hit_chance=character_orm.stats.critical_hit_chance,
            critical_damage_multiplier=character_orm.stats.critical_damage_multiplier,
        )

        stats = CharacterStats(
            core_abilities=core_abilities,
            vital_stats=vital_stats,
            combat_stats=combat_stats,
            experience_points=character_orm.stats.experience_points,
            skill_points=character_orm.stats.skill_points,
        )

        # Map skills
        skill_groups = {}
        if character_orm.skills.skill_groups:
            for category_name, skills_data in character_orm.skills.skill_groups.items():
                category = SkillCategory(category_name)
                skills_dict = {}

                for skill_name, skill_data in skills_data.items():
                    skill = Skill(
                        name=skill_name,
                        category=category,
                        proficiency_level=ProficiencyLevel(
                            skill_data["proficiency_level"]
                        ),
                        modifier=skill_data.get("modifier", 0),
                        description=skill_data.get("description"),
                    )
                    skills_dict[skill_name] = skill

                skill_group = SkillGroup(
                    name=f"{category.value.title()} Skills",
                    category=category,
                    base_modifier=0,
                    skills=skills_dict,
                )
                skill_groups[category] = skill_group

        skills = Skills(
            skill_groups=skill_groups,
            languages=character_orm.skills.languages or [],
            specializations=character_orm.skills.specializations or [],
        )

        # Create the character
        character = Character(
            character_id=CharacterID(character_orm.character_id),
            profile=profile,
            stats=stats,
            skills=skills,
            version=character_orm.version,
            created_at=character_orm.created_at,
            updated_at=character_orm.updated_at,
        )

        return character
