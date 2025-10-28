#!/usr/bin/env python3
"""
Character Application Service

This module implements the main application service for the Character
bounded context. It serves as the primary interface for external systems
to interact with character operations.
"""

import logging
from typing import Any, Dict, List, Optional

from ...domain.aggregates.character import Character
from ...domain.repositories.character_repository import ICharacterRepository
from ...domain.value_objects.character_id import CharacterID
from ...domain.value_objects.character_profile import (
    CharacterClass,
    CharacterRace,
)
from ..commands.character_command_handlers import CharacterCommandHandlerRegistry
from ..commands.character_commands import (
    CreateCharacterCommand,
    DamageCharacterCommand,
    DeleteCharacterCommand,
    HealCharacterCommand,
    LevelUpCharacterCommand,
    UpdateCharacterSkillCommand,
    UpdateCharacterStatsCommand,
)

logger = logging.getLogger(__name__)


class CharacterApplicationService:
    """
    Main application service for character operations.

    This service coordinates character-related operations by handling
    commands, enforcing application-level business rules, and managing
    transactions across the domain and infrastructure layers.
    """

    def __init__(self, character_repository: ICharacterRepository):
        self.repository = character_repository
        self.command_handlers = CharacterCommandHandlerRegistry(character_repository)
        self.logger = logger.getChild(self.__class__.__name__)

    # ==================== Character Management Operations ====================

    async def create_character(
        self,
        character_name: str,
        gender: str,
        race: str,
        character_class: str,
        age: int,
        strength: int = 10,
        dexterity: int = 10,
        constitution: int = 10,
        intelligence: int = 10,
        wisdom: int = 10,
        charisma: int = 10,
        **optional_data,
    ) -> CharacterID:
        """
        Create a new character.

        Args:
            character_name: Name of the character
            gender: Character gender
            race: Character race
            character_class: Character class
            age: Character age
            strength: Strength ability score (1-30)
            dexterity: Dexterity ability score (1-30)
            constitution: Constitution ability score (1-30)
            intelligence: Intelligence ability score (1-30)
            wisdom: Wisdom ability score (1-30)
            charisma: Charisma ability score (1-30)
            **optional_data: Additional optional character data

        Returns:
            ID of the newly created character

        Raises:
            ValueError: If input data is invalid
            RepositoryException: If creation fails
        """
        self.logger.info(f"Creating character: {character_name}")

        try:
            # Check if character name is already taken
            existing_characters = await self.repository.find_by_name(character_name)
            if existing_characters:
                raise ValueError(f"Character name '{character_name}' is already taken")

            # Create command
            command = CreateCharacterCommand(
                character_name=character_name,
                gender=gender,
                race=race,
                character_class=character_class,
                age=age,
                strength=strength,
                dexterity=dexterity,
                constitution=constitution,
                intelligence=intelligence,
                wisdom=wisdom,
                charisma=charisma,
                **optional_data,
            )

            # Execute command
            character_id = await self.command_handlers.handle_command(command)

            self.logger.info(f"Character created successfully: {character_id}")
            return character_id

        except Exception as e:
            self.logger.error(f"Error creating character: {e}")
            raise

    async def get_character(self, character_id: str) -> Optional[Character]:
        """
        Get a character by ID.

        Args:
            character_id: The character ID

        Returns:
            Character if found, None otherwise

        Raises:
            ValueError: If character ID is invalid
            RepositoryException: If retrieval fails
        """
        try:
            char_id = CharacterID.from_string(character_id)
            character = await self.repository.get_by_id(char_id)
            return character

        except Exception as e:
            self.logger.error(f"Error getting character {character_id}: {e}")
            raise

    async def update_character_stats(self, character_id: str, **stat_updates) -> None:
        """
        Update character statistics.

        Args:
            character_id: The character ID
            **stat_updates: Stat values to update

        Raises:
            ValueError: If input data is invalid
            RepositoryException: If update fails
        """
        self.logger.info(f"Updating stats for character: {character_id}")

        try:
            command = UpdateCharacterStatsCommand(character_id=character_id, **stat_updates)

            await self.command_handlers.handle_command(command)

            self.logger.info(f"Character stats updated: {character_id}")

        except Exception as e:
            self.logger.error(f"Error updating character stats: {e}")
            raise

    async def update_character_skill(
        self,
        character_id: str,
        skill_name: str,
        skill_category: str,
        new_proficiency_level: str,
        modifier: int = 0,
        description: Optional[str] = None,
    ) -> None:
        """
        Update a character's skill proficiency.

        Args:
            character_id: The character ID
            skill_name: Name of the skill
            skill_category: Category of the skill
            new_proficiency_level: New proficiency level
            modifier: Skill modifier
            description: Optional skill description

        Raises:
            ValueError: If input data is invalid
            RepositoryException: If update fails
        """
        self.logger.info(f"Updating skill '{skill_name}' for character: {character_id}")

        try:
            command = UpdateCharacterSkillCommand(
                character_id=character_id,
                skill_name=skill_name,
                skill_category=skill_category,
                new_proficiency_level=new_proficiency_level,
                modifier=modifier,
                description=description,
            )

            await self.command_handlers.handle_command(command)

            self.logger.info(f"Character skill updated: {character_id}")

        except Exception as e:
            self.logger.error(f"Error updating character skill: {e}")
            raise

    async def level_up_character(
        self,
        character_id: str,
        ability_improvements: Optional[Dict[str, int]] = None,
        skill_improvements: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Level up a character.

        Args:
            character_id: The character ID
            ability_improvements: Optional ability score improvements
            skill_improvements: Optional skill improvements

        Raises:
            ValueError: If input data is invalid
            RepositoryException: If level up fails
        """
        self.logger.info(f"Leveling up character: {character_id}")

        try:
            command = LevelUpCharacterCommand(
                character_id=character_id,
                ability_score_improvements=ability_improvements or {},
                skill_improvements=skill_improvements or [],
            )

            await self.command_handlers.handle_command(command)

            self.logger.info(f"Character leveled up: {character_id}")

        except Exception as e:
            self.logger.error(f"Error leveling up character: {e}")
            raise

    async def heal_character(
        self,
        character_id: str,
        healing_amount: int,
        healing_type: str = "natural",
        reason: str = "Healing",
    ) -> None:
        """
        Heal a character.

        Args:
            character_id: The character ID
            healing_amount: Amount of healing
            healing_type: Type of healing
            reason: Reason for healing

        Raises:
            ValueError: If input data is invalid
            RepositoryException: If healing fails
        """
        self.logger.info(f"Healing character {character_id} for {healing_amount} points")

        try:
            command = HealCharacterCommand(
                character_id=character_id,
                healing_amount=healing_amount,
                healing_type=healing_type,
                reason=reason,
            )

            await self.command_handlers.handle_command(command)

            self.logger.info(f"Character healed: {character_id}")

        except Exception as e:
            self.logger.error(f"Error healing character: {e}")
            raise

    async def damage_character(
        self,
        character_id: str,
        damage_amount: int,
        damage_type: str = "physical",
        damage_source: Optional[str] = None,
        reason: str = "Damage taken",
    ) -> None:
        """
        Apply damage to a character.

        Args:
            character_id: The character ID
            damage_amount: Amount of damage
            damage_type: Type of damage
            damage_source: Source of damage
            reason: Reason for damage

        Raises:
            ValueError: If input data is invalid
            RepositoryException: If damage application fails
        """
        self.logger.info(
            f"Applying {damage_amount} {damage_type} damage to character {character_id}"
        )

        try:
            command = DamageCharacterCommand(
                character_id=character_id,
                damage_amount=damage_amount,
                damage_type=damage_type,
                damage_source=damage_source,
                reason=reason,
            )

            await self.command_handlers.handle_command(command)

            self.logger.info(f"Damage applied to character: {character_id}")

        except Exception as e:
            self.logger.error(f"Error applying damage to character: {e}")
            raise

    async def delete_character(self, character_id: str, reason: str) -> bool:
        """
        Delete a character.

        Args:
            character_id: The character ID
            reason: Reason for deletion

        Returns:
            True if character was deleted, False if not found

        Raises:
            ValueError: If input data is invalid
            RepositoryException: If deletion fails
        """
        self.logger.info(f"Deleting character: {character_id}")

        try:
            command = DeleteCharacterCommand(character_id=character_id, reason=reason)

            deleted = await self.command_handlers.handle_command(command)

            if deleted:
                self.logger.info(f"Character deleted: {character_id}")
            else:
                self.logger.info(f"Character not found for deletion: {character_id}")

            return deleted

        except Exception as e:
            self.logger.error(f"Error deleting character: {e}")
            raise

    # ==================== Character Query Operations ====================

    async def find_characters_by_name(self, name: str) -> List[Character]:
        """Find characters by name (supports partial matching)."""
        try:
            return await self.repository.find_by_name(name)
        except Exception as e:
            self.logger.error(f"Error finding characters by name '{name}': {e}")
            raise

    async def find_characters_by_class(self, character_class: str) -> List[Character]:
        """Find characters by class."""
        try:
            char_class = CharacterClass(character_class.lower())
            return await self.repository.find_by_class(char_class)
        except Exception as e:
            self.logger.error(f"Error finding characters by class '{character_class}': {e}")
            raise

    async def find_characters_by_race(self, race: str) -> List[Character]:
        """Find characters by race."""
        try:
            char_race = CharacterRace(race.lower())
            return await self.repository.find_by_race(char_race)
        except Exception as e:
            self.logger.error(f"Error finding characters by race '{race}': {e}")
            raise

    async def find_characters_by_level_range(
        self, min_level: int, max_level: int
    ) -> List[Character]:
        """Find characters within a level range."""
        try:
            return await self.repository.find_by_level_range(min_level, max_level)
        except Exception as e:
            self.logger.error(
                f"Error finding characters by level range {min_level}-{max_level}: {e}"
            )
            raise

    async def find_alive_characters(self) -> List[Character]:
        """Find all alive characters."""
        try:
            return await self.repository.find_alive_characters()
        except Exception as e:
            self.logger.error(f"Error finding alive characters: {e}")
            raise

    async def get_character_statistics(self) -> Dict[str, Any]:
        """Get character statistics from the repository."""
        try:
            return await self.repository.get_statistics()
        except Exception as e:
            self.logger.error(f"Error getting character statistics: {e}")
            raise

    async def search_characters(
        self, criteria: Dict[str, Any], limit: Optional[int] = None, offset: int = 0
    ) -> List[Character]:
        """Search characters by multiple criteria."""
        try:
            return await self.repository.find_by_criteria(criteria, limit, offset)
        except Exception as e:
            self.logger.error(f"Error searching characters: {e}")
            raise

    async def count_characters_by_criteria(self, criteria: Dict[str, Any]) -> int:
        """Count characters matching criteria."""
        try:
            return await self.repository.count_by_criteria(criteria)
        except Exception as e:
            self.logger.error(f"Error counting characters: {e}")
            raise

    # ==================== Character Utility Operations ====================

    async def character_exists(self, character_id: str) -> bool:
        """Check if a character exists."""
        try:
            char_id = CharacterID.from_string(character_id)
            return await self.repository.exists(char_id)
        except Exception as e:
            self.logger.error(f"Error checking character existence {character_id}: {e}")
            raise

    async def get_character_summary(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of character information."""
        try:
            character = await self.get_character(character_id)
            if not character:
                return None

            return character.get_character_summary()

        except Exception as e:
            self.logger.error(f"Error getting character summary {character_id}: {e}")
            raise

    async def validate_character_name_availability(self, name: str) -> bool:
        """Check if a character name is available."""
        try:
            existing_characters = await self.repository.find_by_name(name)
            return len(existing_characters) == 0
        except Exception as e:
            self.logger.error(f"Error validating character name '{name}': {e}")
            raise

    # ==================== Bulk Operations ====================

    async def create_multiple_characters(
        self, character_data_list: List[Dict[str, Any]]
    ) -> List[CharacterID]:
        """Create multiple characters in batch."""
        character_ids = []

        try:
            for character_data in character_data_list:
                character_id = await self.create_character(**character_data)
                character_ids.append(character_id)

            self.logger.info(f"Created {len(character_ids)} characters successfully")
            return character_ids

        except Exception as e:
            self.logger.error(f"Error creating multiple characters: {e}")
            # If we've created some characters, we might want to clean up
            # or return the partially successful results
            raise

    async def delete_multiple_characters(self, character_ids: List[str], reason: str) -> int:
        """Delete multiple characters."""
        deleted_count = 0

        try:
            for character_id in character_ids:
                if await self.delete_character(character_id, reason):
                    deleted_count += 1

            self.logger.info(f"Deleted {deleted_count} characters successfully")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error deleting multiple characters: {e}")
            raise
