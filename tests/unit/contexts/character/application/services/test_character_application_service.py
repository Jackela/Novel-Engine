#!/usr/bin/env python3
"""
Unit Tests for CharacterApplicationService

Comprehensive test suite covering:
- Character creation, retrieval, updates
- Query operations (find by name, class, race, level)
- Bulk operations
- Error handling paths
- Result pattern assertions
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.contexts.character.application.services.character_application_service import (
    CharacterApplicationService,
)
from src.contexts.character.domain.aggregates.character import Character
from src.contexts.character.domain.repositories.character_repository import (
    ICharacterRepository,
)
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
from src.contexts.character.domain.value_objects.skills import Skills
from src.core.result import ConflictError, NotFoundError, ValidationError


# Helper to get valid UUID string
def valid_uuid() -> str:
    return str(uuid4())

pytestmark = pytest.mark.unit


# ==================== Test Fixtures ====================


@pytest.fixture
def mock_repository() -> Mock:
    """Create a mock character repository."""
    repo = Mock(spec=ICharacterRepository)
    return repo


@pytest.fixture
def service(mock_repository: Mock) -> CharacterApplicationService:
    """Create a CharacterApplicationService with mock repository."""
    return CharacterApplicationService(character_repository=mock_repository)


@pytest.fixture
def sample_character() -> Character:
    """Create a sample character for testing."""
    character_id = CharacterID.generate()
    profile = CharacterProfile(
        name="Test Character",
        gender=Gender.MALE,
        race=CharacterRace.HUMAN,
        character_class=CharacterClass.FIGHTER,
        age=25,
        level=5,
        personality_traits=PersonalityTraits(traits={"courage": 0.7}),
        physical_traits=PhysicalTraits(),
        background=Background(),
    )
    stats = CharacterStats(
        core_abilities=CoreAbilities(
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
        ),
        vital_stats=VitalStats(
            max_health=50,
            current_health=50,
            max_mana=10,
            current_mana=10,
            max_stamina=30,
            current_stamina=30,
            armor_class=16,
            speed=30,
        ),
        combat_stats=CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        ),
        experience_points=5000,
        skill_points=10,
    )
    skills = Skills.create_basic_skills()

    return Character(
        character_id=character_id,
        profile=profile,
        stats=stats,
        skills=skills,
    )


# ==================== Character Creation Tests ====================


class TestCharacterCreation:
    """Tests for character creation operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_character_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test successful character creation."""
        # Setup
        mock_repository.find_by_name = AsyncMock(return_value=[])
        mock_repository.save = AsyncMock()

        # Execute
        result = await service.create_character(
            character_name="New Hero",
            gender="male",
            race="human",
            character_class="fighter",
            age=25,
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
        )

        # Verify
        assert result.is_ok
        assert isinstance(result.value, CharacterID)
        mock_repository.find_by_name.assert_called_once_with("New Hero")
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_character_duplicate_name(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test character creation with duplicate name returns ConflictError."""
        # Setup
        mock_repository.find_by_name = AsyncMock(return_value=[sample_character])

        # Execute
        result = await service.create_character(
            character_name="Test Character",
            gender="male",
            race="human",
            character_class="fighter",
            age=25,
        )

        # Verify
        assert result.is_error
        assert isinstance(result.error, ConflictError)
        assert "already taken" in result.error.message.lower()
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_character_repository_error(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test character creation handles repository errors."""
        # Setup
        mock_repository.find_by_name = AsyncMock(return_value=[])
        mock_repository.save = AsyncMock(side_effect=Exception("Database connection failed"))

        # Execute
        result = await service.create_character(
            character_name="New Hero",
            gender="male",
            race="human",
            character_class="fighter",
            age=25,
        )

        # Verify
        assert result.is_error
        assert result.error.code == "CREATION_FAILED"


# ==================== Character Retrieval Tests ====================


class TestCharacterRetrieval:
    """Tests for character retrieval operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_character_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test successful character retrieval."""
        # Setup
        char_id_str = str(sample_character.character_id)
        mock_repository.get_by_id = AsyncMock(return_value=sample_character)

        # Execute
        result = await service.get_character(char_id_str)

        # Verify
        assert result.is_ok
        assert result.value == sample_character

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_character_not_found(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test retrieval of non-existent character returns NotFoundError."""
        # Setup
        mock_repository.get_by_id = AsyncMock(return_value=None)

        # Execute
        result = await service.get_character(valid_uuid())

        # Verify
        assert result.is_error
        assert isinstance(result.error, NotFoundError)
        assert "not found" in result.error.message.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_character_invalid_id_format(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test retrieval with invalid ID format returns error."""
        # Execute
        result = await service.get_character("invalid-id-format!!!")

        # Verify
        assert result.is_error
        assert result.error.code == "INVALID_ID"


# ==================== Character Update Tests ====================


class TestCharacterUpdates:
    """Tests for character update operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_character_stats_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test successful character stats update."""
        # Setup - patch the command handler to avoid validation issues
        with patch.object(service.command_handlers, 'handle_command', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = None

            # Execute - use valid vital stats parameters
            result = await service.update_character_stats(
                character_id=valid_uuid(),
                current_health=45,
                max_health=50,
                armor_class=18,
            )

            # Verify
            assert result.is_ok
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_update_character_skill_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test successful character skill update."""
        # Setup - patch the command handler at the module level to bypass validation
        with patch(
            'src.contexts.character.application.services.character_application_service.UpdateCharacterSkillCommand'
        ) as mock_cmd_class:
            mock_cmd = Mock()
            mock_cmd_class.return_value = mock_cmd
            
            with patch.object(service.command_handlers, 'handle_command', new_callable=AsyncMock) as mock_handle:
                mock_handle.return_value = None

                # Execute
                result = await service.update_character_skill(
                    character_id=valid_uuid(),
                    skill_name="Acrobatics",
                    skill_category="Physical",
                    new_proficiency_level="expert",
                    modifier=4,
                )

                # Verify
                assert result.is_ok
                mock_handle.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_level_up_character_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test successful character level up."""
        # Setup - patch the command handler
        with patch.object(service.command_handlers, 'handle_command', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = None
            ability_improvements = {"strength": 1, "constitution": 1}

            # Execute
            result = await service.level_up_character(
                character_id=valid_uuid(),
                ability_improvements=ability_improvements,
            )

            # Verify
            assert result.is_ok
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_heal_character_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test successful character healing."""
        # Setup - patch the command handler
        with patch.object(service.command_handlers, 'handle_command', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = None

            # Execute
            result = await service.heal_character(
                character_id=valid_uuid(),
                healing_amount=10,
                healing_type="magical",
                reason="Potion of Healing",
            )

            # Verify
            assert result.is_ok
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_damage_character_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test successful damage application."""
        # Setup - patch the command handler
        with patch.object(service.command_handlers, 'handle_command', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = None

            # Execute - use valid damage type from enum
            result = await service.damage_character(
                character_id=valid_uuid(),
                damage_amount=15,
                damage_type="physical",  # Use valid type
                damage_source="Goblin Warrior",
            )

            # Verify
            assert result.is_ok
            mock_handle.assert_called_once()


# ==================== Character Deletion Tests ====================


class TestCharacterDeletion:
    """Tests for character deletion operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_character_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test successful character deletion."""
        # Setup - patch the command handler
        with patch.object(service.command_handlers, 'handle_command', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = True  # Character was deleted

            # Execute
            result = await service.delete_character(
                character_id=valid_uuid(),
                reason="Player request",
            )

            # Verify
            assert result.is_ok
            assert result.value is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_character_not_found(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test deletion of non-existent character."""
        # Setup - patch the command handler
        with patch.object(service.command_handlers, 'handle_command', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = False  # Character not found

            # Execute
            result = await service.delete_character(
                character_id=valid_uuid(),
                reason="Cleanup",
            )

            # Verify
            assert result.is_ok
            assert result.value is False


# ==================== Query Operations Tests ====================


class TestCharacterQueries:
    """Tests for character query operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_characters_by_name_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test finding characters by name."""
        # Setup
        mock_repository.find_by_name = AsyncMock(return_value=[sample_character])

        # Execute
        result = await service.find_characters_by_name("Test")

        # Verify
        assert result.is_ok
        assert len(result.value) == 1
        assert result.value[0].profile.name == "Test Character"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_characters_by_class_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test finding characters by class."""
        # Setup
        mock_repository.find_by_class = AsyncMock(return_value=[sample_character])

        # Execute
        result = await service.find_characters_by_class("fighter")

        # Verify
        assert result.is_ok
        assert len(result.value) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_characters_by_class_invalid(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test finding characters with invalid class returns validation error."""
        # Execute
        result = await service.find_characters_by_class("invalid_class")

        # Verify
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_characters_by_race_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test finding characters by race."""
        # Setup
        mock_repository.find_by_race = AsyncMock(return_value=[sample_character])

        # Execute
        result = await service.find_characters_by_race("human")

        # Verify
        assert result.is_ok
        assert len(result.value) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_characters_by_level_range_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test finding characters by level range."""
        # Setup
        mock_repository.find_by_level_range = AsyncMock(return_value=[sample_character])

        # Execute
        result = await service.find_characters_by_level_range(min_level=1, max_level=10)

        # Verify
        assert result.is_ok
        assert len(result.value) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_characters_by_level_range_invalid(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test finding characters with invalid level range."""
        # Execute with negative level
        result = await service.find_characters_by_level_range(min_level=-1, max_level=10)

        # Verify
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_characters_by_level_range_inverted(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test finding characters with min > max level."""
        # Execute with inverted range
        result = await service.find_characters_by_level_range(min_level=10, max_level=1)

        # Verify
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_alive_characters_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test finding alive characters."""
        # Setup
        mock_repository.find_alive_characters = AsyncMock(return_value=[sample_character])

        # Execute
        result = await service.find_alive_characters()

        # Verify
        assert result.is_ok
        assert len(result.value) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_character_statistics_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test getting character statistics."""
        # Setup
        stats = {"total": 100, "by_class": {"fighter": 30}, "by_race": {"human": 50}}
        mock_repository.get_statistics = AsyncMock(return_value=stats)

        # Execute
        result = await service.get_character_statistics()

        # Verify
        assert result.is_ok
        assert result.value["total"] == 100

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_characters_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test searching characters with criteria."""
        # Setup
        mock_repository.find_by_criteria = AsyncMock(return_value=[sample_character])

        # Execute
        criteria = {"name": "Test", "level_min": 1}
        result = await service.search_characters(criteria=criteria, limit=10, offset=0)

        # Verify
        assert result.is_ok
        assert len(result.value) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_count_characters_by_criteria_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test counting characters by criteria."""
        # Setup
        mock_repository.count_by_criteria = AsyncMock(return_value=42)

        # Execute
        result = await service.count_characters_by_criteria({"is_alive": True})

        # Verify
        assert result.is_ok
        assert result.value == 42

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_count_characters_invalid_criteria(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test counting characters with invalid criteria type."""
        # Execute with non-dict criteria
        result = await service.count_characters_by_criteria("invalid_criteria")

        # Verify
        assert result.is_error
        assert isinstance(result.error, ValidationError)


# ==================== Utility Operations Tests ====================


class TestUtilityOperations:
    """Tests for utility operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_character_exists_true(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test checking existence of existing character."""
        # Setup
        mock_repository.exists = AsyncMock(return_value=True)

        # Execute
        result = await service.character_exists(valid_uuid())

        # Verify
        assert result.is_ok
        assert result.value is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_character_exists_false(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test checking existence of non-existent character."""
        # Setup
        mock_repository.exists = AsyncMock(return_value=False)

        # Execute
        result = await service.character_exists(valid_uuid())

        # Verify
        assert result.is_ok
        assert result.value is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_character_exists_invalid_id(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test checking existence with invalid ID format."""
        # Execute
        result = await service.character_exists("invalid!!!")

        # Verify
        assert result.is_error
        assert isinstance(result.error, ValidationError)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_character_summary_success(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test getting character summary."""
        # Setup
        mock_repository.get_by_id = AsyncMock(return_value=sample_character)

        # Execute
        result = await service.get_character_summary(str(sample_character.character_id))

        # Verify
        assert result.is_ok
        assert result.value is not None
        assert "name" in result.value

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_character_name_available(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test validating available character name."""
        # Setup
        mock_repository.find_by_name = AsyncMock(return_value=[])

        # Execute
        result = await service.validate_character_name_availability("Unique Name")

        # Verify
        assert result.is_ok
        assert result.value is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_character_name_taken(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test validating taken character name."""
        # Setup
        mock_repository.find_by_name = AsyncMock(return_value=[sample_character])

        # Execute
        result = await service.validate_character_name_availability("Test Character")

        # Verify
        assert result.is_ok
        assert result.value is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_validate_character_name_empty(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test validating empty character name."""
        # Execute
        result = await service.validate_character_name_availability("")

        # Verify
        assert result.is_error
        assert isinstance(result.error, ValidationError)


# ==================== Bulk Operations Tests ====================


class TestBulkOperations:
    """Tests for bulk operations."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_multiple_characters_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test creating multiple characters."""
        # Setup - patch create_character to bypass validation
        with patch.object(service, 'create_character', new_callable=AsyncMock) as mock_create:
            from src.contexts.character.domain.value_objects.character_id import (
                CharacterID,
            )
            from src.core.result import Ok
            mock_create.side_effect = [
                Ok(CharacterID.generate()),
                Ok(CharacterID.generate()),
            ]

            # Execute
            character_data_list = [
                {"character_name": "Hero 1", "gender": "male", "race": "human", "character_class": "fighter", "age": 20},
                {"character_name": "Hero 2", "gender": "female", "race": "elf", "character_class": "wizard", "age": 120},
            ]
            result = await service.create_multiple_characters(character_data_list)

            # Verify
            assert result.is_ok
            assert len(result.value) == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_multiple_characters_partial_failure(self, service: CharacterApplicationService, mock_repository: Mock, sample_character: Character):
        """Test batch creation stops on first failure."""
        # Setup - first call returns empty (success), second returns existing character (failure)
        mock_repository.find_by_name = AsyncMock(side_effect=[[], [sample_character]])

        # Execute
        character_data_list = [
            {"character_name": "New Hero", "gender": "male", "race": "human", "character_class": "fighter", "age": 20},
            {"character_name": "Test Character", "gender": "female", "race": "elf", "character_class": "wizard", "age": 120},
        ]
        result = await service.create_multiple_characters(character_data_list)

        # Verify
        assert result.is_error
        assert "BATCH_CREATION_FAILED" in result.error.code

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_multiple_characters_success(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test deleting multiple characters."""
        # Setup - patch delete_character to bypass validation
        with patch.object(service, 'delete_character', new_callable=AsyncMock) as mock_delete:
            from src.core.result import Ok
            mock_delete.return_value = Ok(True)

            # Execute
            character_ids = [valid_uuid(), valid_uuid(), valid_uuid()]
            result = await service.delete_multiple_characters(character_ids, "Cleanup")

            # Verify
            assert result.is_ok
            assert result.value == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_delete_multiple_characters_partial(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test deleting multiple characters with partial success."""
        # Setup - patch delete_character
        with patch.object(service, 'delete_character', new_callable=AsyncMock) as mock_delete:
            from src.core.result import Ok
            mock_delete.side_effect = [Ok(True), Ok(False), Ok(True)]

            # Execute
            character_ids = [valid_uuid(), valid_uuid(), valid_uuid()]
            result = await service.delete_multiple_characters(character_ids, "Cleanup")

            # Verify
            assert result.is_ok
            assert result.value == 2  # 2 out of 3 deleted


# ==================== Error Handling Tests ====================


class TestErrorHandling:
    """Tests for error handling paths."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_by_name_repository_error(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test find_by_name handles repository errors."""
        # Setup
        mock_repository.find_by_name = AsyncMock(side_effect=Exception("Database error"))

        # Execute
        result = await service.find_characters_by_name("Test")

        # Verify
        assert result.is_error
        assert result.error.code == "QUERY_FAILED"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_by_class_repository_error(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test find_by_class handles repository errors."""
        # Setup
        mock_repository.find_by_class = AsyncMock(side_effect=Exception("Database error"))

        # Execute
        result = await service.find_characters_by_class("fighter")

        # Verify
        assert result.is_error
        assert result.error.code == "QUERY_FAILED"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_alive_characters_repository_error(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test find_alive_characters handles repository errors."""
        # Setup
        mock_repository.find_alive_characters = AsyncMock(side_effect=Exception("Database error"))

        # Execute
        result = await service.find_alive_characters()

        # Verify
        assert result.is_error
        assert result.error.code == "QUERY_FAILED"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_statistics_repository_error(self, service: CharacterApplicationService, mock_repository: Mock):
        """Test get_statistics handles repository errors."""
        # Setup
        mock_repository.get_statistics = AsyncMock(side_effect=Exception("Database error"))

        # Execute
        result = await service.get_character_statistics()

        # Verify
        assert result.is_error
        assert result.error.code == "QUERY_FAILED"
