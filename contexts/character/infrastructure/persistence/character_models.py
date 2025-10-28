#!/usr/bin/env python3
"""
Character SQLAlchemy ORM Models

This module defines SQLAlchemy ORM models for persisting Character
aggregates and their associated value objects. The models provide
a relational database representation of the domain model.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship, validates


# Base class for all ORM models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class CharacterORM(Base):
    """
    Main Character ORM model representing the Character aggregate root.

    This model stores core character data and maintains relationships
    to other character-related data models.
    """

    __tablename__ = "characters"

    # Primary key and identity
    character_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic character information
    name = Column(String(100), nullable=False, index=True)
    gender = Column(String(20), nullable=False)
    race = Column(String(50), nullable=False)
    character_class = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)
    level = Column(Integer, nullable=False, default=1)

    # Character status
    is_alive = Column(Boolean, nullable=False, default=True)

    # Aggregate version for optimistic concurrency control
    version = Column(Integer, nullable=False, default=1)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Domain events (JSON storage for simplicity)
    pending_events = Column(JSON, nullable=True)

    # Relationships to other character data
    profile = relationship(
        "CharacterProfileORM",
        back_populates="character",
        uselist=False,
        cascade="all, delete-orphan",
    )
    stats = relationship(
        "CharacterStatsORM",
        back_populates="character",
        uselist=False,
        cascade="all, delete-orphan",
    )
    skills = relationship(
        "CharacterSkillsORM",
        back_populates="character",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<CharacterORM(id={self.character_id}, name='{self.name}', level={self.level})>"

    @validates("level")
    def validate_level(self, key, level):
        if level < 1:
            raise ValueError("Character level must be at least 1")
        return level

    @validates("age")
    def validate_age(self, key, age):
        if age < 0 or age > 10000:
            raise ValueError("Character age must be between 0 and 10000")
        return age


class CharacterProfileORM(Base):
    """
    Character Profile ORM model storing detailed character profile information.

    This includes physical traits, personality, background, and other
    character details beyond the core data.
    """

    __tablename__ = "character_profiles"

    # Primary key and foreign key
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(
        UUID(as_uuid=True),
        ForeignKey("characters.character_id"),
        nullable=False,
        unique=True,
    )

    # Profile information
    title = Column(String(100), nullable=True)
    affiliation = Column(String(200), nullable=True)
    languages = Column(JSON, nullable=True)  # List of languages

    # Physical traits
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Integer, nullable=True)
    hair_color = Column(String(50), nullable=True)
    eye_color = Column(String(50), nullable=True)
    skin_tone = Column(String(50), nullable=True)
    physical_description = Column(Text, nullable=True)

    # Personality traits (JSON storage for flexibility)
    personality_traits = Column(JSON, nullable=True)

    # Background information
    backstory = Column(Text, nullable=True)
    homeland = Column(String(200), nullable=True)
    education = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to character
    character = relationship("CharacterORM", back_populates="profile")

    def __repr__(self):
        return f"<CharacterProfileORM(character_id={self.character_id}, title='{self.title}')>"

    @validates("height_cm")
    def validate_height(self, key, height):
        if height is not None and (height < 30 or height > 300):
            raise ValueError("Height must be between 30 and 300 cm")
        return height

    @validates("weight_kg")
    def validate_weight(self, key, weight):
        if weight is not None and (weight < 1 or weight > 500):
            raise ValueError("Weight must be between 1 and 500 kg")
        return weight


class CharacterStatsORM(Base):
    """
    Character Statistics ORM model storing all character statistics.

    This includes core abilities, vital stats, combat stats, and
    experience/skill point tracking.
    """

    __tablename__ = "character_stats"

    # Primary key and foreign key
    stats_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(
        UUID(as_uuid=True),
        ForeignKey("characters.character_id"),
        nullable=False,
        unique=True,
    )

    # Core abilities (D&D-style)
    strength = Column(Integer, nullable=False, default=10)
    dexterity = Column(Integer, nullable=False, default=10)
    constitution = Column(Integer, nullable=False, default=10)
    intelligence = Column(Integer, nullable=False, default=10)
    wisdom = Column(Integer, nullable=False, default=10)
    charisma = Column(Integer, nullable=False, default=10)

    # Vital statistics
    max_health = Column(Integer, nullable=False, default=10)
    current_health = Column(Integer, nullable=False, default=10)
    max_mana = Column(Integer, nullable=False, default=0)
    current_mana = Column(Integer, nullable=False, default=0)
    max_stamina = Column(Integer, nullable=False, default=10)
    current_stamina = Column(Integer, nullable=False, default=10)

    # Combat statistics
    armor_class = Column(Integer, nullable=False, default=10)
    speed = Column(Integer, nullable=False, default=30)
    base_attack_bonus = Column(Integer, nullable=False, default=0)
    initiative_modifier = Column(Integer, nullable=False, default=0)
    damage_reduction = Column(Integer, nullable=False, default=0)
    spell_resistance = Column(Integer, nullable=False, default=0)
    critical_hit_chance = Column(Float, nullable=False, default=0.05)
    critical_damage_multiplier = Column(Float, nullable=False, default=2.0)

    # Experience and progression
    experience_points = Column(Integer, nullable=False, default=0)
    skill_points = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to character
    character = relationship("CharacterORM", back_populates="stats")

    def __repr__(self):
        return f"<CharacterStatsORM(character_id={self.character_id}, level={self.character.level if self.character else 'N/A'})>"

    @validates("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
    def validate_ability_score(self, key, score):
        if not 1 <= score <= 30:
            raise ValueError(f"Ability score {key} must be between 1 and 30")
        return score

    @validates("current_health", "current_mana", "current_stamina")
    def validate_current_stats(self, key, value):
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value

    @validates("max_health", "max_stamina")
    def validate_max_vital_stats(self, key, value):
        if value <= 0:
            raise ValueError(f"{key} must be positive")
        return value

    @validates("max_mana")
    def validate_max_mana(self, key, value):
        if value < 0:
            raise ValueError("Max mana cannot be negative")
        return value


class CharacterSkillsORM(Base):
    """
    Character Skills ORM model storing character skill proficiencies.

    This model stores skill groups, individual skills, and proficiency
    levels for each character.
    """

    __tablename__ = "character_skills"

    # Primary key and foreign key
    skills_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(
        UUID(as_uuid=True),
        ForeignKey("characters.character_id"),
        nullable=False,
        unique=True,
    )

    # Skills data (JSON storage for flexibility)
    # Structure: { "category": { "skill_name": { "proficiency_level": 1, "modifier": 0, "description": "..." } } }
    skill_groups = Column(JSON, nullable=True)

    # Languages known by the character
    languages = Column(JSON, nullable=True)  # List of language strings

    # Specializations and expertise
    specializations = Column(JSON, nullable=True)  # List of specialization strings

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to character
    character = relationship("CharacterORM", back_populates="skills")

    def __repr__(self):
        return f"<CharacterSkillsORM(character_id={self.character_id})>"

    def get_skill(self, category: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific skill from the skill groups."""
        if not self.skill_groups:
            return None

        category_skills = self.skill_groups.get(category, {})
        return category_skills.get(skill_name.lower())

    def set_skill(
        self,
        category: str,
        skill_name: str,
        proficiency_level: int,
        modifier: int = 0,
        description: str = None,
    ) -> None:
        """Set a specific skill in the skill groups."""
        if not self.skill_groups:
            self.skill_groups = {}

        if category not in self.skill_groups:
            self.skill_groups[category] = {}

        self.skill_groups[category][skill_name.lower()] = {
            "proficiency_level": proficiency_level,
            "modifier": modifier,
            "description": description,
        }

    def get_skills_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """Get all skills in a specific category."""
        if not self.skill_groups:
            return {}

        return self.skill_groups.get(category, {})


class CharacterEventORM(Base):
    """
    Character Domain Event ORM model for event sourcing.

    This model stores domain events related to character changes
    for audit trails and event sourcing patterns.
    """

    __tablename__ = "character_events"

    # Primary key
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event identification
    character_id = Column(
        UUID(as_uuid=True),
        ForeignKey("characters.character_id"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(100), nullable=False, index=True)
    event_version = Column(Integer, nullable=False)

    # Event data
    event_data = Column(JSON, nullable=False)

    # Event metadata
    aggregate_version = Column(Integer, nullable=False)
    correlation_id = Column(String(100), nullable=True, index=True)
    causation_id = Column(String(100), nullable=True)
    user_id = Column(String(100), nullable=True)

    # Timestamps
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<CharacterEventORM(event_id={self.event_id}, type='{self.event_type}', character_id={self.character_id})>"

    @validates("event_version")
    def validate_event_version(self, key, version):
        if version < 1:
            raise ValueError("Event version must be at least 1")
        return version

    @validates("aggregate_version")
    def validate_aggregate_version(self, key, version):
        if version < 1:
            raise ValueError("Aggregate version must be at least 1")
        return version
