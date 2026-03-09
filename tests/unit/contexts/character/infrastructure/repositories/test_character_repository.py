"""Unit tests for SQLAlchemyCharacterRepository.

Tests cover CRUD operations, query operations, bulk operations,
and error handling for the SQLAlchemy-based character repository.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.contexts.character.domain.aggregates.character import Character
from src.contexts.character.domain.repositories.character_repository import (
    ConcurrencyException,
    RepositoryException,
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
from src.contexts.character.infrastructure.repositories.character_repository import (
    SQLAlchemyCharacterRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session_factory():
    """Create a mock session factory."""
    mock_session = MagicMock(spec=Session)
    mock_factory = Mock(return_value=mock_session)
    mock_factory.return_value.__enter__ = Mock(return_value=mock_session)
    mock_factory.return_value.__exit__ = Mock(return_value=False)
    return mock_factory, mock_session


@pytest.fixture
def character_repository(mock_session_factory):
    """Create a character repository with mocked session factory."""
    factory, _ = mock_session_factory
    return SQLAlchemyCharacterRepository(session_factory=factory)


@pytest.fixture
def sample_character_id():
    """Create a sample character ID."""
    return CharacterID("12345678-1234-1234-1234-123456789abc")


@pytest.fixture
def sample_character(sample_character_id):
    """Create a sample character for testing."""
    profile = CharacterProfile(
        name="Test Character",
        gender=Gender.MALE,
        race=CharacterRace.HUMAN,
        character_class=CharacterClass.WARRIOR,
        age=25,
        level=5,
        physical_traits=PhysicalTraits(
            height_cm=180,
            weight_kg=75,
            hair_color="brown",
            eye_color="blue",
            skin_tone="fair",
        ),
        personality_traits=PersonalityTraits(traits={"brave": 0.8, "honest": 0.7}),
        background=Background(
            backstory="A brave warrior from the north.",
            homeland="Northlands",
            education="Military academy",
        ),
    )

    stats = CharacterStats(
        core_abilities=CoreAbilities(
            strength=15,
            dexterity=12,
            constitution=14,
            intelligence=10,
            wisdom=11,
            charisma=13,
        ),
        vital_stats=VitalStats(
            max_health=100,
            current_health=100,
            max_mana=50,
            current_mana=50,
            max_stamina=80,
            current_stamina=80,
            armor_class=15,
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
        experience_points=0,
        skill_points=0,
    )

    # Create a proper skill group for the sample character
    from src.contexts.character.domain.value_objects.skills import (
        ProficiencyLevel,
        Skill,
        SkillCategory,
        SkillGroup,
    )

    combat_skill = Skill(
        name="sword",
        category=SkillCategory.COMBAT,
        proficiency_level=ProficiencyLevel.APPRENTICE,
        modifier=2,
    )
    combat_group = SkillGroup(
        name="Combat Skills",
        category=SkillCategory.COMBAT,
        base_modifier=0,
        skills={"sword": combat_skill},
    )
    skills = Skills(
        skill_groups={SkillCategory.COMBAT: combat_group},
        languages={"Common"},
        specializations={},
    )

    return Character(
        character_id=sample_character_id,
        profile=profile,
        stats=stats,
        skills=skills,
    )


class TestCharacterRepositoryGetById:
    """Tests for get_by_id method."""

    async def test_get_by_id_returns_character_when_found(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """get_by_id returns character when found in database."""
        _, mock_session = mock_session_factory

        # Setup mock ORM result
        mock_orm = Mock()
        mock_orm.character_id = sample_character_id.value
        mock_orm.name = "Test Character"
        mock_orm.gender = "male"
        mock_orm.race = "human"
        mock_orm.character_class = "warrior"
        mock_orm.age = 25
        mock_orm.level = 5
        mock_orm.is_alive = True
        mock_orm.version = 1
        mock_orm.created_at = datetime.now(UTC)
        mock_orm.updated_at = datetime.now(UTC)

        # Setup related ORM objects
        mock_orm.profile = Mock(
            title="Warrior",
            affiliation="Northern Guild",
            languages=["Common"],
            height_cm=180,
            weight_kg=75,
            hair_color="brown",
            eye_color="blue",
            skin_tone="fair",
            physical_description="Tall and strong",
            personality_traits={"brave": 0.8},
            backstory="Warrior from north",
            homeland="Northlands",
            education="Military",
        )
        mock_orm.stats = Mock(
            strength=15,
            dexterity=12,
            constitution=14,
            intelligence=10,
            wisdom=11,
            charisma=13,
            max_health=100,
            current_health=100,
            max_mana=50,
            current_mana=50,
            max_stamina=80,
            current_stamina=80,
            armor_class=15,
            speed=30,
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
            experience_points=0,
            skill_points=0,
        )
        mock_orm.skills = Mock(
            skill_groups={
                "combat": {
                    "sword": {
                        "proficiency_level": 2,
                        "modifier": 2,
                        "description": None,
                    }
                }
            },
            languages=["Common"],
            specializations={"sword_mastery": 2},
        )

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_orm
        mock_session.query.return_value = mock_query

        result = await character_repository.get_by_id(sample_character_id)

        assert result is not None
        assert result.character_id.value == sample_character_id.value
        assert result.profile.name == "Test Character"

    async def test_get_by_id_returns_none_when_not_found(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """get_by_id returns None when character not found."""
        _, mock_session = mock_session_factory

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_session.query.return_value = mock_query

        result = await character_repository.get_by_id(sample_character_id)

        assert result is None

    async def test_get_by_id_raises_repository_exception_on_db_error(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """get_by_id raises RepositoryException on database error."""
        _, mock_session = mock_session_factory
        mock_session.query.side_effect = SQLAlchemyError("Database connection failed")

        with pytest.raises(RepositoryException) as exc_info:
            await character_repository.get_by_id(sample_character_id)

        assert "Failed to retrieve character" in str(exc_info.value)


class TestCharacterRepositorySave:
    """Tests for save method."""

    async def test_save_creates_new_character(
        self, character_repository, mock_session_factory, sample_character
    ):
        """save creates new character when not exists."""
        _, mock_session = mock_session_factory

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_session.query.return_value = mock_query

        await character_repository.save(sample_character)

        # Verify session.add was called for new character
        assert mock_session.add.called
        assert mock_session.commit.called

    async def test_save_updates_existing_character(
        self, character_repository, mock_session_factory, sample_character
    ):
        """save updates existing character when found."""
        _, mock_session = mock_session_factory

        sample_character.version = 2  # Character modified from version 1

        mock_existing = Mock()
        mock_existing.version = 1  # Database has version 1
        mock_existing.profile = Mock()
        mock_existing.stats = Mock()
        mock_existing.skills = Mock()

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_existing
        mock_session.query.return_value = mock_query

        await character_repository.save(sample_character)

        # Verify no add for existing character
        mock_session.commit.assert_called_once()

    async def test_save_raises_concurrency_exception_on_version_mismatch(
        self, character_repository, mock_session_factory, sample_character
    ):
        """save raises ConcurrencyException when version mismatch."""
        _, mock_session = mock_session_factory

        sample_character.version = 3  # Expecting to update from version 2

        mock_existing = Mock()
        mock_existing.version = 5  # Database has version 5 (ahead!)

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_existing
        mock_session.query.return_value = mock_query

        with pytest.raises(ConcurrencyException) as exc_info:
            await character_repository.save(sample_character)

        assert "Version conflict" in str(exc_info.value)

    async def test_save_raises_repository_exception_on_db_error(
        self, character_repository, mock_session_factory, sample_character
    ):
        """save raises RepositoryException on database error."""
        _, mock_session = mock_session_factory
        mock_session.query.side_effect = SQLAlchemyError("Insert failed")

        with pytest.raises(RepositoryException) as exc_info:
            await character_repository.save(sample_character)

        assert "Failed to save character" in str(exc_info.value)


class TestCharacterRepositoryDelete:
    """Tests for delete method."""

    async def test_delete_returns_true_when_character_deleted(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """delete returns True when character is deleted."""
        _, mock_session = mock_session_factory

        mock_orm = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_orm
        mock_session.query.return_value = mock_query

        result = await character_repository.delete(sample_character_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_orm)
        mock_session.commit.assert_called_once()

    async def test_delete_returns_false_when_character_not_found(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """delete returns False when character not found."""
        _, mock_session = mock_session_factory

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_session.query.return_value = mock_query

        result = await character_repository.delete(sample_character_id)

        assert result is False

    async def test_delete_raises_repository_exception_on_db_error(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """delete raises RepositoryException on database error."""
        _, mock_session = mock_session_factory
        mock_session.query.side_effect = SQLAlchemyError("Delete failed")

        with pytest.raises(RepositoryException) as exc_info:
            await character_repository.delete(sample_character_id)

        assert "Failed to delete character" in str(exc_info.value)


class TestCharacterRepositoryExists:
    """Tests for exists method."""

    async def test_exists_returns_true_when_character_exists(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """exists returns True when character exists."""
        _, mock_session = mock_session_factory

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.exists.return_value = True
        mock_session.query.return_value = mock_query

        # For scalar() result
        mock_scalar_query = Mock()
        mock_scalar_query.scalar.return_value = True
        mock_session.query.side_effect = [mock_query, mock_scalar_query]

        result = await character_repository.exists(sample_character_id)

        assert result is True

    async def test_exists_returns_false_when_character_not_found(
        self, character_repository, mock_session_factory, sample_character_id
    ):
        """exists returns False when character not found."""
        _, mock_session = mock_session_factory

        mock_exists_query = Mock()
        mock_exists_query.filter.return_value = mock_exists_query
        mock_exists_query.exists.return_value = False

        mock_scalar_query = Mock()
        mock_scalar_query.scalar.return_value = False

        mock_session.query.side_effect = [mock_exists_query, mock_scalar_query]

        result = await character_repository.exists(sample_character_id)

        assert result is False


class TestCharacterRepositoryFindByName:
    """Tests for find_by_name method."""

    async def test_find_by_name_returns_matching_characters(
        self, character_repository, mock_session_factory
    ):
        """find_by_name returns characters matching name pattern."""
        _, mock_session = mock_session_factory

        mock_orm1 = Mock()
        mock_orm1.character_id = "char-001"
        mock_orm1.profile = Mock()
        mock_orm1.stats = Mock()
        mock_orm1.skills = Mock()

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_orm1]
        mock_session.query.return_value = mock_query

        with patch.object(
            character_repository,
            "_map_orm_to_domain",
            return_value=Mock(spec=Character),
        ):
            result = await character_repository.find_by_name("Test")

            assert len(result) == 1

    async def test_find_by_name_raises_repository_exception_on_error(
        self, character_repository, mock_session_factory
    ):
        """find_by_name raises RepositoryException on database error."""
        _, mock_session = mock_session_factory
        mock_session.query.side_effect = SQLAlchemyError("Query failed")

        with pytest.raises(RepositoryException):
            await character_repository.find_by_name("Test")


class TestCharacterRepositoryBulkOperations:
    """Tests for bulk operations."""

    async def test_save_multiple_saves_all_characters(
        self, character_repository, mock_session_factory, sample_character
    ):
        """save_multiple saves all characters in batch."""
        _, mock_session = mock_session_factory

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_session.query.return_value = mock_query

        await character_repository.save_multiple([sample_character, sample_character])

        assert mock_session.commit.called

    async def test_delete_multiple_deletes_all_characters(
        self, character_repository, mock_session_factory
    ):
        """delete_multiple deletes all characters in batch."""
        _, mock_session = mock_session_factory

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_session.query.return_value = mock_query

        char_ids = [
            CharacterID("12345678-1234-1234-1234-123456789001"),
            CharacterID("12345678-1234-1234-1234-123456789002"),
        ]
        result = await character_repository.delete_multiple(char_ids)

        assert result == 2
        mock_session.commit.assert_called_once()


class TestCharacterRepositoryNotSupportedOperations:
    """Tests for operations that are not supported."""

    async def test_find_by_smart_tag_raises_not_supported(self, character_repository):
        """find_by_smart_tag raises NotSupportedException."""
        from src.contexts.character.domain.repositories.character_repository import (
            NotSupportedException,
        )

        with pytest.raises(NotSupportedException):
            await character_repository.find_by_smart_tag("category", "tag")

    async def test_find_by_smart_tags_raises_not_supported(self, character_repository):
        """find_by_smart_tags raises NotSupportedException."""
        from src.contexts.character.domain.repositories.character_repository import (
            NotSupportedException,
        )

        with pytest.raises(NotSupportedException):
            await character_repository.find_by_smart_tags({"category": ["tag"]})

    async def test_find_by_metadata_raises_not_supported(self, character_repository):
        """find_by_metadata raises NotSupportedException."""
        from src.contexts.character.domain.repositories.character_repository import (
            NotSupportedException,
        )

        with pytest.raises(NotSupportedException):
            await character_repository.find_by_metadata("key", "value")


class TestCharacterRepositoryGetStatistics:
    """Tests for get_statistics method."""

    async def test_get_statistics_returns_correct_data(
        self, character_repository, mock_session_factory
    ):
        """get_statistics returns aggregated character statistics."""
        _, mock_session = mock_session_factory

        mock_session.query.return_value.count.return_value = 10

        # Setup mock for group_by queries
        mock_class_result = [("warrior", 5), ("mage", 5)]
        mock_race_result = [("human", 8), ("elf", 2)]
        mock_level_result = [(1, 3), (5, 7)]

        mock_query = Mock()
        mock_query.group_by.return_value = mock_query
        mock_query.all.side_effect = [
            mock_class_result,
            mock_race_result,
            mock_level_result,
        ]
        mock_query.scalar.return_value = 3.5
        mock_session.query.return_value = mock_query

        result = await character_repository.get_statistics()

        assert "total_characters" in result
        assert "characters_by_class" in result
        assert "characters_by_race" in result

    async def test_get_statistics_raises_repository_exception_on_error(
        self, character_repository, mock_session_factory
    ):
        """get_statistics raises RepositoryException on database error."""
        _, mock_session = mock_session_factory
        mock_session.query.side_effect = SQLAlchemyError("Query failed")

        with pytest.raises(RepositoryException):
            await character_repository.get_statistics()
