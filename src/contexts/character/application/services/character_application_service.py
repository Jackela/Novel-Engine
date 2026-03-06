#!/usr/bin/env python3
"""
Character Application Service

This module implements the main application service for the Character
bounded context. It serves as the primary interface for external systems
to interact with character operations.
"""

import structlog
from typing import Any, Dict, List, Optional

from .....core.result import ConflictError, Err, Error, NotFoundError, Ok, Result, SaveError, ValidationError
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

logger = structlog.get_logger(__name__)


class CharacterApplicationService:
    """
    Main application service for character operations.

    This service coordinates character-related operations by handling
    commands, enforcing application-level business rules, and managing
    transactions across the domain and infrastructure layers.
    """

    def __init__(self, character_repository: ICharacterRepository) -> None:
        self.repository = character_repository
        self.command_handlers = CharacterCommandHandlerRegistry(character_repository)
        self.logger = logger.bind(component=self.__class__.__name__)

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
    ) -> Result[CharacterID, Error]:
        """
        Create a new character.

        Why Result pattern:
            Explicitly signals potential failures (name conflict) without
            raising exceptions, allowing routers to handle errors gracefully.

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
            Result with CharacterID on success, Error if name already taken
        """
        self.logger.info("creating_character", character_name=character_name)

        try:
            # Check if character name is already taken
            existing_characters = await self.repository.find_by_name(character_name)
            if existing_characters:
                return Err(
                    ConflictError(
                        message=f"Character name '{character_name}' is already taken",
                        details={"character_name": character_name},
                    )
                )

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

            self.logger.info("character_created", character_id=str(character_id))
            return Ok(character_id)

        except Exception as e:
            self.logger.error("character_creation_failed", error=str(e))
            return Err(
                Error(
                    code="CREATION_FAILED",
                    message=f"Failed to create character: {e}",
                    recoverable=False,
                )
            )

    async def get_character(self, character_id: str) -> Result[Character, Error]:
        """
        Get a character by ID.

        Why Result pattern:
            Explicitly signals when a character is not found, allowing
            routers to return 404 instead of 500.

        Args:
            character_id: The character ID

        Returns:
            Result with Character on success, NotFoundError if not found
        """
        try:
            char_id = CharacterID.from_string(character_id)
            character = await self.repository.get_by_id(char_id)

            if character is None:
                return Err(
                    NotFoundError(
                        message=f"Character with ID '{character_id}' not found",
                        details={"character_id": character_id},
                    )
                )

            return Ok(character)

        except ValueError as e:
            self.logger.error("invalid_character_id", character_id=character_id, error=str(e))
            return Err(
                Error(
                    code="INVALID_ID",
                    message=f"Invalid character ID format: {e}",
                    recoverable=False,
                )
            )
        except Exception as e:
            self.logger.error("character_retrieval_failed", character_id=character_id, error=str(e))
            return Err(
                Error(
                    code="RETRIEVAL_FAILED",
                    message=f"Failed to retrieve character: {e}",
                    recoverable=False,
                )
            )

    async def update_character_stats(
        self, character_id: str, **stat_updates
    ) -> Result[None, Error]:
        """
        Update character statistics.

        Why Result pattern:
            Explicit error handling without exceptions allows routers to
            return appropriate HTTP status codes and handle failures gracefully.

        Args:
            character_id: The character ID
            **stat_updates: Stat values to update

        Returns:
            Result with None on success, Error on failure
        """
        self.logger.info("updating_character_stats", character_id=character_id)

        try:
            command = UpdateCharacterStatsCommand(
                character_id=character_id, **stat_updates
            )

            await self.command_handlers.handle_command(command)

            self.logger.info("character_stats_updated", character_id=character_id)
            return Ok(None)

        except ValueError as e:
            self.logger.error("character_stats_validation_failed", error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid stat update data: {e}",
                    details={"character_id": character_id, "updates": stat_updates},
                )
            )
        except Exception as e:
            self.logger.error("character_stats_update_failed", error=str(e))
            return Err(
                SaveError(
                    message=f"Failed to update character stats: {e}",
                    entity_type="Character",
                    details={"character_id": character_id},
                )
            )

    async def update_character_skill(
        self,
        character_id: str,
        skill_name: str,
        skill_category: str,
        new_proficiency_level: str,
        modifier: int = 0,
        description: Optional[str] = None,
    ) -> Result[None, Error]:
        """
        Update a character's skill proficiency.

        Why Result pattern:
            Explicit error handling without exceptions allows routers to
            return appropriate HTTP status codes and handle failures gracefully.

        Args:
            character_id: The character ID
            skill_name: Name of the skill
            skill_category: Category of the skill
            new_proficiency_level: New proficiency level
            modifier: Skill modifier
            description: Optional skill description

        Returns:
            Result with None on success, Error on failure
        """
        self.logger.info("updating_character_skill", skill_name=skill_name, character_id=character_id)

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

            self.logger.info("character_skill_updated", character_id=character_id)
            return Ok(None)

        except ValueError as e:
            self.logger.error("character_skill_validation_failed", error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid skill update data: {e}",
                    field="skill",
                    details={"character_id": character_id, "skill_name": skill_name},
                )
            )
        except Exception as e:
            self.logger.error("character_skill_update_failed", error=str(e))
            return Err(
                SaveError(
                    message=f"Failed to update character skill: {e}",
                    entity_type="Character",
                    details={"character_id": character_id, "skill_name": skill_name},
                )
            )

    async def level_up_character(
        self,
        character_id: str,
        ability_improvements: Optional[Dict[str, int]] = None,
        skill_improvements: Optional[List[Dict[str, Any]]] = None,
    ) -> Result[None, Error]:
        """
        Level up a character.

        Why Result pattern:
            Explicit error handling without exceptions allows routers to
            return appropriate HTTP status codes and handle failures gracefully.

        Args:
            character_id: The character ID
            ability_improvements: Optional ability score improvements
            skill_improvements: Optional skill improvements

        Returns:
            Result with None on success, Error on failure
        """
        self.logger.info("leveling_up_character", character_id=character_id)

        try:
            command = LevelUpCharacterCommand(
                character_id=character_id,
                ability_score_improvements=ability_improvements or {},
                skill_improvements=skill_improvements or [],
            )

            await self.command_handlers.handle_command(command)

            self.logger.info("character_leveled_up", character_id=character_id)
            return Ok(None)

        except ValueError as e:
            self.logger.error("character_level_up_validation_failed", error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid level up data: {e}",
                    details={"character_id": character_id},
                )
            )
        except Exception as e:
            self.logger.error("character_level_up_failed", error=str(e))
            return Err(
                SaveError(
                    message=f"Failed to level up character: {e}",
                    entity_type="Character",
                    details={"character_id": character_id},
                )
            )

    async def heal_character(
        self,
        character_id: str,
        healing_amount: int,
        healing_type: str = "natural",
        reason: str = "Healing",
    ) -> Result[None, Error]:
        """
        Heal a character.

        Why Result pattern:
            Explicit error handling without exceptions allows routers to
            return appropriate HTTP status codes and handle failures gracefully.

        Args:
            character_id: The character ID
            healing_amount: Amount of healing
            healing_type: Type of healing
            reason: Reason for healing

        Returns:
            Result with None on success, Error on failure
        """
        self.logger.info(
            "healing_character",
            character_id=character_id,
            healing_amount=healing_amount
        )

        try:
            command = HealCharacterCommand(
                character_id=character_id,
                healing_amount=healing_amount,
                healing_type=healing_type,
                reason=reason,
            )

            await self.command_handlers.handle_command(command)

            self.logger.info("character_healed", character_id=character_id)
            return Ok(None)

        except ValueError as e:
            self.logger.error("character_healing_validation_failed", error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid healing data: {e}",
                    details={"character_id": character_id, "amount": healing_amount},
                )
            )
        except Exception as e:
            self.logger.error("character_healing_failed", error=str(e))
            return Err(
                SaveError(
                    message=f"Failed to heal character: {e}",
                    entity_type="Character",
                    details={"character_id": character_id},
                )
            )

    async def damage_character(
        self,
        character_id: str,
        damage_amount: int,
        damage_type: str = "physical",
        damage_source: Optional[str] = None,
        reason: str = "Damage taken",
    ) -> Result[None, Error]:
        """
        Apply damage to a character.

        Why Result pattern:
            Explicit error handling without exceptions allows routers to
            return appropriate HTTP status codes and handle failures gracefully.

        Args:
            character_id: The character ID
            damage_amount: Amount of damage
            damage_type: Type of damage
            damage_source: Source of damage
            reason: Reason for damage

        Returns:
            Result with None on success, Error on failure
        """
        self.logger.info(
            "applying_damage",
            character_id=character_id,
            damage_amount=damage_amount,
            damage_type=damage_type
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

            self.logger.info("damage_applied", character_id=character_id)
            return Ok(None)

        except ValueError as e:
            self.logger.error("damage_validation_failed", error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid damage data: {e}",
                    details={"character_id": character_id, "amount": damage_amount},
                )
            )
        except Exception as e:
            self.logger.error("damage_application_failed", error=str(e))
            return Err(
                SaveError(
                    message=f"Failed to apply damage: {e}",
                    entity_type="Character",
                    details={"character_id": character_id},
                )
            )

    async def delete_character(self, character_id: str, reason: str) -> Result[bool, Error]:
        """
        Delete a character.

        Why Result pattern:
            Explicit error handling without exceptions allows routers to
            return appropriate HTTP status codes and handle failures gracefully.

        Args:
            character_id: The character ID
            reason: Reason for deletion

        Returns:
            Result with True if deleted, False if not found, Error on failure
        """
        self.logger.info("deleting_character", character_id=character_id)

        try:
            command = DeleteCharacterCommand(character_id=character_id, reason=reason)

            deleted = await self.command_handlers.handle_command(command)

            if deleted:
                self.logger.info("character_deleted", character_id=character_id)
            else:
                self.logger.info("character_not_found_for_deletion", character_id=character_id)

            return Ok(deleted)

        except ValueError as e:
            self.logger.error("character_deletion_validation_failed", error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid deletion request: {e}",
                    details={"character_id": character_id},
                )
            )
        except Exception as e:
            self.logger.error("character_deletion_failed", error=str(e))
            return Err(
                SaveError(
                    message=f"Failed to delete character: {e}",
                    entity_type="Character",
                    details={"character_id": character_id},
                )
            )

    # ==================== Character Query Operations ====================

    async def find_characters_by_name(self, name: str) -> Result[List[Character], Error]:
        """
        Find characters by name (supports partial matching).

        Why Result pattern:
            Explicit error handling for repository failures.

        Returns:
            Result with list of characters on success, Error on failure
        """
        try:
            characters = await self.repository.find_by_name(name)
            return Ok(characters)
        except Exception as e:
            self.logger.error("find_characters_by_name_failed", name=name, error=str(e))
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to find characters by name: {e}",
                    recoverable=True,
                    details={"name": name},
                )
            )

    async def find_characters_by_class(self, character_class: str) -> Result[List[Character], Error]:
        """
        Find characters by class.

        Why Result pattern:
            Explicit error handling for validation and repository failures.

        Returns:
            Result with list of characters on success, Error on failure
        """
        try:
            char_class = CharacterClass(character_class.lower())
            characters = await self.repository.find_by_class(char_class)
            return Ok(characters)
        except ValueError as e:
            self.logger.error("find_characters_by_class_validation_failed", character_class=character_class, error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid character class: {e}",
                    field="character_class",
                    details={"character_class": character_class},
                )
            )
        except Exception as e:
            self.logger.error(
                "find_characters_by_class_failed", character_class=character_class, error=str(e)
            )
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to find characters by class: {e}",
                    recoverable=True,
                    details={"character_class": character_class},
                )
            )

    async def find_characters_by_race(self, race: str) -> Result[List[Character], Error]:
        """
        Find characters by race.

        Why Result pattern:
            Explicit error handling for validation and repository failures.

        Returns:
            Result with list of characters on success, Error on failure
        """
        try:
            char_race = CharacterRace(race.lower())
            characters = await self.repository.find_by_race(char_race)
            return Ok(characters)
        except ValueError as e:
            self.logger.error("find_characters_by_race_validation_failed", race=race, error=str(e))
            return Err(
                ValidationError(
                    message=f"Invalid character race: {e}",
                    field="race",
                    details={"race": race},
                )
            )
        except Exception as e:
            self.logger.error("find_characters_by_race_failed", race=race, error=str(e))
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to find characters by race: {e}",
                    recoverable=True,
                    details={"race": race},
                )
            )

    async def find_characters_by_level_range(
        self, min_level: int, max_level: int
    ) -> Result[List[Character], Error]:
        """
        Find characters within a level range.

        Why Result pattern:
            Explicit error handling for repository failures and validation.

        Returns:
            Result with list of characters on success, Error on failure
        """
        try:
            if min_level < 0 or max_level < 0:
                return Err(
                    ValidationError(
                        message="Level values must be non-negative",
                        details={"min_level": min_level, "max_level": max_level},
                    )
                )
            if min_level > max_level:
                return Err(
                    ValidationError(
                        message="min_level cannot be greater than max_level",
                        details={"min_level": min_level, "max_level": max_level},
                    )
                )

            characters = await self.repository.find_by_level_range(min_level, max_level)
            return Ok(characters)
        except Exception as e:
            self.logger.error(
                "find_characters_by_level_range_failed",
                min_level=min_level,
                max_level=max_level,
                error=str(e)
            )
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to find characters by level range: {e}",
                    recoverable=True,
                    details={"min_level": min_level, "max_level": max_level},
                )
            )

    async def find_alive_characters(self) -> Result[List[Character], Error]:
        """
        Find all alive characters.

        Why Result pattern:
            Explicit error handling for repository failures.

        Returns:
            Result with list of characters on success, Error on failure
        """
        try:
            characters = await self.repository.find_alive_characters()
            return Ok(characters)
        except Exception as e:
            self.logger.error("find_alive_characters_failed", error=str(e))
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to find alive characters: {e}",
                    recoverable=True,
                )
            )

    async def get_character_statistics(self) -> Result[Dict[str, Any], Error]:
        """
        Get character statistics from the repository.

        Why Result pattern:
            Explicit error handling for repository failures.

        Returns:
            Result with statistics dict on success, Error on failure
        """
        try:
            stats = await self.repository.get_statistics()
            return Ok(stats)
        except Exception as e:
            self.logger.error("get_character_statistics_failed", error=str(e))
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to get character statistics: {e}",
                    recoverable=True,
                )
            )

    async def search_characters(
        self, criteria: Dict[str, Any], limit: Optional[int] = None, offset: int = 0
    ) -> Result[List[Character], Error]:
        """
        Search characters by multiple criteria.

        Why Result pattern:
            Explicit error handling for repository failures.

        Returns:
            Result with list of characters on success, Error on failure
        """
        try:
            characters = await self.repository.find_by_criteria(criteria, limit, offset)
            return Ok(characters)
        except Exception as e:
            self.logger.error("search_characters_failed", error=str(e))
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to search characters: {e}",
                    recoverable=True,
                    details={"criteria": criteria},
                )
            )

    async def count_characters_by_criteria(
        self, criteria: Dict[str, Any]
    ) -> Result[int, Error]:
        """
        Count characters matching criteria.

        Why Result pattern:
            Explicit error handling for repository failures.

        Returns:
            Result with count on success, Error on failure
        """
        try:
            if not isinstance(criteria, dict):
                return Err(
                    ValidationError(
                        message="Criteria must be a dictionary",
                        field="criteria",
                    )
                )

            count = await self.repository.count_by_criteria(criteria)
            return Ok(count)
        except Exception as e:
            self.logger.error("count_characters_failed", error=str(e), criteria=criteria)
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to count characters: {e}",
                    recoverable=True,
                    details={"criteria": criteria},
                )
            )

    # ==================== Character Utility Operations ====================

    async def character_exists(self, character_id: str) -> Result[bool, Error]:
        """
        Check if a character exists.

        Why Result pattern:
            Explicit error handling for invalid ID format and repository failures.

        Returns:
            Result with True/False on success, Error on failure
        """
        try:
            char_id = CharacterID.from_string(character_id)
            exists = await self.repository.exists(char_id)
            return Ok(exists)
        except ValueError as e:
            self.logger.error(
                "invalid_character_id_format",
                character_id=character_id,
                error=str(e)
            )
            return Err(
                ValidationError(
                    message=f"Invalid character ID format: {e}",
                    field="character_id",
                    details={"character_id": character_id},
                )
            )
        except Exception as e:
            self.logger.error(
                "check_character_existence_failed",
                character_id=character_id,
                error=str(e)
            )
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to check character existence: {e}",
                    recoverable=True,
                    details={"character_id": character_id},
                )
            )

    async def get_character_summary(
        self, character_id: str
    ) -> Result[Optional[Dict[str, Any]], Error]:
        """
        Get a summary of character information.

        Why Result pattern:
            Explicit error handling for retrieval failures.

        Returns:
            Result with character summary on success, Error on failure
        """
        try:
            character_result = await self.get_character(character_id)
            if character_result.is_error:
                return character_result

            character = character_result.value
            if character is None:
                return Ok(None)

            return Ok(character.get_character_summary())

        except Exception as e:
            self.logger.error("get_character_summary_failed", character_id=character_id, error=str(e))
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to get character summary: {e}",
                    recoverable=True,
                    details={"character_id": character_id},
                )
            )

    async def validate_character_name_availability(self, name: str) -> Result[bool, Error]:
        """
        Check if a character name is available.

        Why Result pattern:
            Explicit error handling for validation and repository failures.

        Returns:
            Result with True if available, False if taken, Error on failure
        """
        try:
            if not name or not name.strip():
                return Err(
                    ValidationError(
                        message="Character name cannot be empty",
                        field="name",
                    )
                )

            existing_characters = await self.repository.find_by_name(name)
            is_available = len(existing_characters) == 0
            return Ok(is_available)
        except Exception as e:
            self.logger.error("validate_character_name_failed", name=name, error=str(e))
            return Err(
                Error(
                    code="QUERY_FAILED",
                    message=f"Failed to validate character name availability: {e}",
                    recoverable=True,
                    details={"name": name},
                )
            )

    # ==================== Bulk Operations ====================

    async def create_multiple_characters(
        self, character_data_list: List[Dict[str, Any]]
    ) -> Result[List[CharacterID], Error]:
        """
        Create multiple characters in batch.

        Why Result pattern:
            Explicit error handling for partial failures.

        Returns:
            Result with list of character IDs on success, Error on failure
        """
        character_ids: List[CharacterID] = []
        try:
            for character_data in character_data_list:
                result = await self.create_character(**character_data)
                if result.is_error:
                    return Err(
                        Error(
                            code="BATCH_CREATION_FAILED",
                            message=f"Failed to create character in batch: {result.error}",
                            recoverable=False,
                            details={"created_so_far": len(character_ids)},
                        )
                    )
                character_ids.append(result.value)

            self.logger.info("multiple_characters_created", count=len(character_ids))
            return Ok(character_ids)

        except Exception as e:
            self.logger.error("create_multiple_characters_failed", error=str(e))
            return Err(
                Error(
                    code="BATCH_CREATION_FAILED",
                    message=f"Failed to create multiple characters: {e}",
                    recoverable=False,
                    details={"created_so_far": len(character_ids)},
                )
            )

    async def delete_multiple_characters(
        self, character_ids: List[str], reason: str
    ) -> Result[int, Error]:
        """
        Delete multiple characters.

        Why Result pattern:
            Explicit error handling for partial failures.

        Returns:
            Result with count of deleted characters on success, Error on failure
        """
        deleted_count = 0

        try:
            for character_id in character_ids:
                result = await self.delete_character(character_id, reason)
                if result.is_error:
                    return Err(
                        Error(
                            code="BATCH_DELETION_FAILED",
                            message=f"Failed to delete character in batch: {result.error}",
                            recoverable=False,
                            details={"deleted_so_far": deleted_count},
                        )
                    )
                if result.value:
                    deleted_count += 1

            self.logger.info("multiple_characters_deleted", count=deleted_count)
            return Ok(deleted_count)

        except Exception as e:
            self.logger.error("delete_multiple_characters_failed", error=str(e))
            return Err(
                Error(
                    code="BATCH_DELETION_FAILED",
                    message=f"Failed to delete multiple characters: {e}",
                    recoverable=False,
                    details={"deleted_so_far": deleted_count},
                )
            )
