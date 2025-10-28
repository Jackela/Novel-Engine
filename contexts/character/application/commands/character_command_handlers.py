#!/usr/bin/env python3
"""
Character Command Handlers

This module implements command handlers for the Character bounded context.
Command handlers execute the business logic for commands by coordinating
between the domain layer and infrastructure services.
"""

import logging
from typing import Any

from ...domain.aggregates.character import Character
from ...domain.repositories.character_repository import ICharacterRepository
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
from .character_commands import (
    CreateCharacterCommand,
    DamageCharacterCommand,
    DeleteCharacterCommand,
    HealCharacterCommand,
    LevelUpCharacterCommand,
    UpdateCharacterSkillCommand,
    UpdateCharacterStatsCommand,
)

logger = logging.getLogger(__name__)


class CreateCharacterCommandHandler:
    """Handler for creating new characters."""

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.logger = logger.getChild(self.__class__.__name__)

    async def handle(self, command: CreateCharacterCommand) -> CharacterID:
        """
        Handle character creation command.

        Args:
            command: The create character command

        Returns:
            The ID of the newly created character

        Raises:
            ValueError: If command data is invalid
            RepositoryException: If save operation fails
        """
        self.logger.info(f"Creating character: {command.character_name}")

        try:
            # Convert command data to domain objects
            core_abilities = CoreAbilities(
                strength=command.strength,
                dexterity=command.dexterity,
                constitution=command.constitution,
                intelligence=command.intelligence,
                wisdom=command.wisdom,
                charisma=command.charisma,
            )

            # Create character using aggregate factory method
            character = Character.create_new_character(
                name=command.character_name,
                gender=Gender(command.gender.lower()),
                race=CharacterRace(command.race.lower()),
                character_class=CharacterClass(command.character_class.lower()),
                age=command.age,
                core_abilities=core_abilities,
            )

            # Update optional profile data if provided
            if any(
                [
                    command.title,
                    command.affiliation,
                    command.languages,
                    command.height_cm,
                    command.weight_kg,
                    command.hair_color,
                    command.eye_color,
                    command.skin_tone,
                    command.physical_description,
                    command.backstory,
                    command.homeland,
                    command.education,
                ]
            ):
                # Create updated physical traits
                physical_traits = PhysicalTraits(
                    height_cm=command.height_cm,
                    weight_kg=command.weight_kg,
                    hair_color=command.hair_color,
                    eye_color=command.eye_color,
                    skin_tone=command.skin_tone,
                    physical_description=command.physical_description,
                )

                # Create updated personality traits
                personality_traits = PersonalityTraits(traits=command.personality_traits)

                # Create updated background
                background = Background(
                    backstory=command.backstory,
                    homeland=command.homeland,
                    education=command.education,
                )

                # Create updated profile
                updated_profile = CharacterProfile(
                    name=command.character_name,
                    gender=Gender(command.gender.lower()),
                    race=CharacterRace(command.race.lower()),
                    character_class=CharacterClass(command.character_class.lower()),
                    age=command.age,
                    level=1,
                    physical_traits=physical_traits,
                    personality_traits=personality_traits,
                    background=background,
                    title=command.title,
                    affiliation=command.affiliation,
                    languages=command.languages,
                )

                character.update_profile(updated_profile)

            # Save character to repository
            await self.repository.save(character)

            self.logger.info(f"Character created successfully: {character.character_id}")
            return character.character_id

        except Exception as e:
            self.logger.error(f"Error creating character: {e}")
            raise


class UpdateCharacterStatsCommandHandler:
    """Handler for updating character statistics."""

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.logger = logger.getChild(self.__class__.__name__)

    async def handle(self, command: UpdateCharacterStatsCommand) -> None:
        """
        Handle character stats update command.

        Args:
            command: The update stats command

        Raises:
            ValueError: If command data is invalid
            RepositoryException: If character not found or save fails
        """
        character_id = CharacterID.from_string(command.character_id)
        self.logger.info(f"Updating stats for character: {character_id}")

        try:
            # Load character from repository
            character = await self.repository.get_by_id(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")

            # Check version for optimistic concurrency control
            if command.expected_version and character.version != command.expected_version:
                raise ValueError(
                    f"Version conflict: expected {command.expected_version}, got {character.version}"
                )

            # Create updated vital stats
            current_vital_stats = character.stats.vital_stats
            new_vital_stats = VitalStats(
                max_health=command.max_health or current_vital_stats.max_health,
                current_health=(
                    command.current_health
                    if command.current_health is not None
                    else current_vital_stats.current_health
                ),
                max_mana=command.max_mana or current_vital_stats.max_mana,
                current_mana=(
                    command.current_mana
                    if command.current_mana is not None
                    else current_vital_stats.current_mana
                ),
                max_stamina=command.max_stamina or current_vital_stats.max_stamina,
                current_stamina=(
                    command.current_stamina
                    if command.current_stamina is not None
                    else current_vital_stats.current_stamina
                ),
                armor_class=command.armor_class or current_vital_stats.armor_class,
                speed=command.speed or current_vital_stats.speed,
            )

            # Create updated combat stats
            current_combat_stats = character.stats.combat_stats
            new_combat_stats = CombatStats(
                base_attack_bonus=command.base_attack_bonus
                or current_combat_stats.base_attack_bonus,
                initiative_modifier=command.initiative_modifier
                or current_combat_stats.initiative_modifier,
                damage_reduction=current_combat_stats.damage_reduction,
                spell_resistance=current_combat_stats.spell_resistance,
                critical_hit_chance=current_combat_stats.critical_hit_chance,
                critical_damage_multiplier=current_combat_stats.critical_damage_multiplier,
            )

            # Create updated character stats
            new_stats = CharacterStats(
                core_abilities=character.stats.core_abilities,
                vital_stats=new_vital_stats,
                combat_stats=new_combat_stats,
                experience_points=command.experience_points or character.stats.experience_points,
                skill_points=command.skill_points or character.stats.skill_points,
            )

            # Update character
            character.update_stats(new_stats)

            # Save character
            await self.repository.save(character)

            self.logger.info(f"Character stats updated successfully: {character_id}")

        except Exception as e:
            self.logger.error(f"Error updating character stats: {e}")
            raise


class UpdateCharacterSkillCommandHandler:
    """Handler for updating character skills."""

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.logger = logger.getChild(self.__class__.__name__)

    async def handle(self, command: UpdateCharacterSkillCommand) -> None:
        """
        Handle character skill update command.

        Args:
            command: The update skill command

        Raises:
            ValueError: If command data is invalid
            RepositoryException: If character not found or save fails
        """
        character_id = CharacterID.from_string(command.character_id)
        self.logger.info(f"Updating skill '{command.skill_name}' for character: {character_id}")

        try:
            # Load character from repository
            character = await self.repository.get_by_id(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")

            # Check version for optimistic concurrency control
            if command.expected_version and character.version != command.expected_version:
                raise ValueError(
                    f"Version conflict: expected {command.expected_version}, got {character.version}"
                )

            # Create new skill
            new_skill = Skill(
                name=command.skill_name,
                category=SkillCategory(command.skill_category.lower()),
                proficiency_level=ProficiencyLevel(int(command.new_proficiency_level)),
                modifier=command.modifier,
                description=command.description,
            )

            # Get current skills and update
            current_skills = character.skills
            category = SkillCategory(command.skill_category.lower())

            # Create updated skill group
            if category in current_skills.skill_groups:
                skill_group = current_skills.skill_groups[category]
                updated_skills = skill_group.skills.copy()
                updated_skills[command.skill_name.lower()] = new_skill

                updated_skill_group = SkillGroup(
                    name=skill_group.name,
                    category=category,
                    base_modifier=skill_group.base_modifier,
                    skills=updated_skills,
                )
            else:
                # Create new skill group
                updated_skill_group = SkillGroup(
                    name=f"{category.value.title()} Skills",
                    category=category,
                    base_modifier=0,
                    skills={command.skill_name.lower(): new_skill},
                )

            # Create updated skills
            updated_skill_groups = current_skills.skill_groups.copy()
            updated_skill_groups[category] = updated_skill_group

            new_skills = Skills(
                skill_groups=updated_skill_groups,
                languages=current_skills.languages,
                specializations=current_skills.specializations,
            )

            # Update character
            character.update_skills(new_skills)

            # Save character
            await self.repository.save(character)

            self.logger.info(f"Character skill updated successfully: {character_id}")

        except Exception as e:
            self.logger.error(f"Error updating character skill: {e}")
            raise


class LevelUpCharacterCommandHandler:
    """Handler for character level up operations."""

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.logger = logger.getChild(self.__class__.__name__)

    async def handle(self, command: LevelUpCharacterCommand) -> None:
        """
        Handle character level up command.

        Args:
            command: The level up command

        Raises:
            ValueError: If command data is invalid
            RepositoryException: If character not found or save fails
        """
        character_id = CharacterID.from_string(command.character_id)
        self.logger.info(f"Leveling up character: {character_id}")

        try:
            # Load character from repository
            character = await self.repository.get_by_id(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")

            # Check version for optimistic concurrency control
            if command.expected_version and character.version != command.expected_version:
                raise ValueError(
                    f"Version conflict: expected {command.expected_version}, got {character.version}"
                )

            # Perform level up
            character.level_up()

            # Apply ability score improvements if specified
            if command.ability_score_improvements:
                # This would require creating new CoreAbilities with improvements
                # For now, log the improvements
                self.logger.info(
                    f"Ability improvements requested: {command.ability_score_improvements}"
                )
                # TODO: Implement ability score improvements

            # Apply skill improvements if specified
            if command.skill_improvements:
                self.logger.info(f"Skill improvements requested: {command.skill_improvements}")
                # TODO: Implement skill improvements

            # Save character
            await self.repository.save(character)

            self.logger.info(f"Character leveled up successfully: {character_id}")

        except Exception as e:
            self.logger.error(f"Error leveling up character: {e}")
            raise


class DeleteCharacterCommandHandler:
    """Handler for character deletion."""

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.logger = logger.getChild(self.__class__.__name__)

    async def handle(self, command: DeleteCharacterCommand) -> bool:
        """
        Handle character deletion command.

        Args:
            command: The delete command

        Returns:
            True if character was deleted, False if not found

        Raises:
            RepositoryException: If deletion fails
        """
        character_id = CharacterID.from_string(command.character_id)
        self.logger.info(f"Deleting character: {character_id}, reason: {command.reason}")

        try:
            # Check if character exists first
            character = await self.repository.get_by_id(character_id)
            if not character:
                self.logger.warning(f"Character not found for deletion: {character_id}")
                return False

            # TODO: Raise CharacterDeleted domain event before deletion
            # This would require modifying the character to add the event first

            # Delete character
            deleted = await self.repository.delete(character_id)

            if deleted:
                self.logger.info(f"Character deleted successfully: {character_id}")
            else:
                self.logger.warning(f"Character deletion failed: {character_id}")

            return deleted

        except Exception as e:
            self.logger.error(f"Error deleting character: {e}")
            raise


class HealCharacterCommandHandler:
    """Handler for character healing operations."""

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.logger = logger.getChild(self.__class__.__name__)

    async def handle(self, command: HealCharacterCommand) -> None:
        """
        Handle character healing command.

        Args:
            command: The heal command

        Raises:
            ValueError: If command data is invalid
            RepositoryException: If character not found or save fails
        """
        character_id = CharacterID.from_string(command.character_id)
        self.logger.info(
            f"Healing character {character_id} for {command.healing_amount} points ({command.healing_type})"
        )

        try:
            # Load character from repository
            character = await self.repository.get_by_id(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")

            # Apply healing
            character.heal(command.healing_amount)

            # Save character
            await self.repository.save(character)

            self.logger.info(f"Character healed successfully: {character_id}")

        except Exception as e:
            self.logger.error(f"Error healing character: {e}")
            raise


class DamageCharacterCommandHandler:
    """Handler for character damage operations."""

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.logger = logger.getChild(self.__class__.__name__)

    async def handle(self, command: DamageCharacterCommand) -> None:
        """
        Handle character damage command.

        Args:
            command: The damage command

        Raises:
            ValueError: If command data is invalid
            RepositoryException: If character not found or save fails
        """
        character_id = CharacterID.from_string(command.character_id)
        self.logger.info(
            f"Applying {command.damage_amount} {command.damage_type} damage to character {character_id}"
        )

        try:
            # Load character from repository
            character = await self.repository.get_by_id(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")

            # Apply damage
            character.take_damage(command.damage_amount)

            # Save character
            await self.repository.save(character)

            self.logger.info(f"Damage applied successfully to character: {character_id}")

        except Exception as e:
            self.logger.error(f"Error applying damage to character: {e}")
            raise


class CharacterCommandHandlerRegistry:
    """Registry for character command handlers."""

    def __init__(self, character_repository: ICharacterRepository):
        self.handlers = {
            CreateCharacterCommand: CreateCharacterCommandHandler(character_repository),
            UpdateCharacterStatsCommand: UpdateCharacterStatsCommandHandler(character_repository),
            UpdateCharacterSkillCommand: UpdateCharacterSkillCommandHandler(character_repository),
            LevelUpCharacterCommand: LevelUpCharacterCommandHandler(character_repository),
            DeleteCharacterCommand: DeleteCharacterCommandHandler(character_repository),
            HealCharacterCommand: HealCharacterCommandHandler(character_repository),
            DamageCharacterCommand: DamageCharacterCommandHandler(character_repository),
        }

    async def handle_command(self, command) -> Any:
        """
        Handle a command by routing it to the appropriate handler.

        Args:
            command: The command to handle

        Returns:
            Result from the command handler

        Raises:
            ValueError: If no handler found for command type
        """
        command_type = type(command)
        handler = self.handlers.get(command_type)

        if not handler:
            raise ValueError(f"No handler registered for command type: {command_type}")

        return await handler.handle(command)
