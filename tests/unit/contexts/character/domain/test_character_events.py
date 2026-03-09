#!/usr/bin/env python3
"""
Unit tests for Character Domain Events

Comprehensive test suite for character domain events including:
- TravelRecord
- CharacterCreated
- CharacterUpdated
- CharacterStatsChanged
- CharacterLeveledUp
- CharacterDeleted
- CharacterLocationChanged
"""

import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies before importing
sys.modules["aioredis"] = MagicMock()
event_bus_mock = MagicMock()
event_mock = MagicMock()
event_mock.return_value = Mock()
event_bus_mock.Event = event_mock
sys.modules["src.events.event_bus"] = event_bus_mock

from src.contexts.character.domain.events.character_events import (
    CharacterCreated,
    CharacterDeleted,
    CharacterLeveledUp,
    CharacterLocationChanged,
    CharacterStatsChanged,
    CharacterUpdated,
    TravelRecord,
)
from src.contexts.character.domain.value_objects.character_id import CharacterID


class TestTravelRecord:
    """Test suite for TravelRecord value object."""

    @pytest.fixture
    def mock_calendar(self):
        """Create a mock WorldCalendar for testing."""
        calendar = Mock()
        calendar.year = 1025
        calendar.month = 6
        calendar.day = 15
        calendar.to_dict = Mock(
            return_value={"year": 1025, "month": 6, "day": 15, "era_name": "Third Age"}
        )
        return calendar

    @pytest.fixture
    def sample_travel_record(self, mock_calendar):
        """Create a sample travel record."""
        return TravelRecord(
            location_id="loc_123",
            arrived_date=mock_calendar,
            departed_date=None,
        )

    def test_travel_record_creation_success(self, mock_calendar):
        """Test successful travel record creation."""
        record = TravelRecord(
            location_id="loc_123",
            arrived_date=mock_calendar,
        )

        assert record.location_id == "loc_123"
        assert record.arrived_date == mock_calendar
        assert record.departed_date is None

    def test_travel_record_creation_with_departure(self, mock_calendar):
        """Test travel record creation with departure date."""
        departure_date = Mock()
        departure_date.year = 1025
        departure_date.month = 7
        departure_date.day = 1

        record = TravelRecord(
            location_id="loc_123",
            arrived_date=mock_calendar,
            departed_date=departure_date,
        )

        assert record.departed_date == departure_date

    def test_travel_record_empty_location_raises_error(self, mock_calendar):
        """Test that empty location_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TravelRecord(
                location_id="",
                arrived_date=mock_calendar,
            )
        assert "Location ID cannot be empty" in str(exc_info.value)

    def test_travel_record_whitespace_location_raises_error(self, mock_calendar):
        """Test that whitespace-only location_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TravelRecord(
                location_id="   ",
                arrived_date=mock_calendar,
            )
        assert "Location ID cannot be empty" in str(exc_info.value)

    def test_travel_record_depart_success(self, sample_travel_record, mock_calendar):
        """Test successful departure from location."""
        departure_date = Mock()
        departure_date.year = 1025
        departure_date.month = 7
        departure_date.day = 1

        sample_travel_record.depart(departure_date)

        assert sample_travel_record.departed_date == departure_date

    def test_travel_record_depart_already_departed_raises_error(
        self, sample_travel_record, mock_calendar
    ):
        """Test that departing twice raises ValueError."""
        departure_date = Mock()
        sample_travel_record.depart(departure_date)

        with pytest.raises(ValueError) as exc_info:
            sample_travel_record.depart(departure_date)
        assert "already departed" in str(exc_info.value)

    def test_travel_record_is_current_when_no_departure(self, sample_travel_record):
        """Test is_current returns True when no departure date."""
        assert sample_travel_record.is_current() is True

    def test_travel_record_is_current_after_departure(self, sample_travel_record):
        """Test is_current returns False after departure."""
        departure_date = Mock()
        sample_travel_record.depart(departure_date)
        assert sample_travel_record.is_current() is False

    def test_travel_record_to_dict(self, sample_travel_record, mock_calendar):
        """Test dictionary serialization."""
        result = sample_travel_record.to_dict()

        assert result["location_id"] == "loc_123"
        assert result["arrived_date"] is not None
        assert result["departed_date"] is None
        assert result["is_current"] is True

    def test_travel_record_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "location_id": "loc_456",
            "arrived_date": None,
            "departed_date": None,
        }

        record = TravelRecord.from_dict(data)

        assert record.location_id == "loc_456"


class TestCharacterCreated:
    """Test suite for CharacterCreated event."""

    @pytest.fixture
    def sample_character_id(self):
        """Create a sample character ID."""
        return CharacterID.generate()

    @pytest.fixture
    def valid_creation_data(self, sample_character_id):
        """Create valid data for CharacterCreated event."""
        return {
            "character_id": sample_character_id,
            "character_name": "Test Hero",
            "character_class": "fighter",
            "level": 5,
            "created_at": datetime.now(),
        }

    def test_character_created_success(self, valid_creation_data):
        """Test successful CharacterCreated event creation."""
        event = CharacterCreated.create(**valid_creation_data)

        assert event.character_name == "Test Hero"
        assert event.character_class == "fighter"
        assert event.level == 5
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_character_created_empty_name_raises_error(self, sample_character_id):
        """Test that empty character name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterCreated.create(
                character_id=sample_character_id,
                character_name="",
                character_class="fighter",
                level=5,
                created_at=datetime.now(),
            )
        assert "Character name cannot be empty" in str(exc_info.value)

    def test_character_created_empty_class_raises_error(self, sample_character_id):
        """Test that empty character class raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterCreated.create(
                character_id=sample_character_id,
                character_name="Test Hero",
                character_class="",
                level=5,
                created_at=datetime.now(),
            )
        assert "Character class cannot be empty" in str(exc_info.value)

    def test_character_created_invalid_level_raises_error(self, sample_character_id):
        """Test that level < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterCreated.create(
                character_id=sample_character_id,
                character_name="Test Hero",
                character_class="fighter",
                level=0,
                created_at=datetime.now(),
            )
        assert "Character level must be at least 1" in str(exc_info.value)

    def test_character_created_get_event_type(self, valid_creation_data):
        """Test get_event_type returns correct value."""
        event = CharacterCreated.create(**valid_creation_data)
        assert event.get_event_type() == "character.created"

    def test_character_created_to_dict(self, valid_creation_data):
        """Test dictionary serialization."""
        event = CharacterCreated.create(**valid_creation_data)
        result = event.to_dict()

        assert result["event_type"] == "character.created"
        assert result["character_name"] == "Test Hero"
        assert result["character_class"] == "fighter"
        assert result["level"] == 5
        assert "event_id" in result
        assert "occurred_at" in result


class TestCharacterUpdated:
    """Test suite for CharacterUpdated event."""

    @pytest.fixture
    def sample_character_id(self):
        """Create a sample character ID."""
        return CharacterID.generate()

    @pytest.fixture
    def valid_update_data(self, sample_character_id):
        """Create valid data for CharacterUpdated event."""
        return {
            "character_id": sample_character_id,
            "updated_fields": ["profile", "stats"],
            "old_version": 1,
            "new_version": 2,
            "updated_at": datetime.now(),
        }

    def test_character_updated_success(self, valid_update_data):
        """Test successful CharacterUpdated event creation."""
        event = CharacterUpdated.create(**valid_update_data)

        assert event.updated_fields == ["profile", "stats"]
        assert event.old_version == 1
        assert event.new_version == 2

    def test_character_updated_empty_fields_raises_error(self, sample_character_id):
        """Test that empty updated_fields raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterUpdated.create(
                character_id=sample_character_id,
                updated_fields=[],
                old_version=1,
                new_version=2,
                updated_at=datetime.now(),
            )
        assert "Updated fields cannot be empty" in str(exc_info.value)

    def test_character_updated_invalid_old_version_raises_error(self, sample_character_id):
        """Test that old_version < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterUpdated.create(
                character_id=sample_character_id,
                updated_fields=["profile"],
                old_version=0,
                new_version=1,
                updated_at=datetime.now(),
            )
        assert "Old version must be at least 1" in str(exc_info.value)

    def test_character_updated_same_version_raises_error(self, sample_character_id):
        """Test that new_version <= old_version raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterUpdated.create(
                character_id=sample_character_id,
                updated_fields=["profile"],
                old_version=2,
                new_version=2,
                updated_at=datetime.now(),
            )
        assert "New version must be greater than old version" in str(exc_info.value)

    def test_character_updated_get_event_type(self, valid_update_data):
        """Test get_event_type returns correct value."""
        event = CharacterUpdated.create(**valid_update_data)
        assert event.get_event_type() == "character.updated"

    def test_character_updated_to_dict(self, valid_update_data):
        """Test dictionary serialization."""
        event = CharacterUpdated.create(**valid_update_data)
        result = event.to_dict()

        assert result["event_type"] == "character.updated"
        assert result["updated_fields"] == ["profile", "stats"]
        assert result["old_version"] == 1
        assert result["new_version"] == 2


class TestCharacterStatsChanged:
    """Test suite for CharacterStatsChanged event."""

    @pytest.fixture
    def sample_character_id(self):
        """Create a sample character ID."""
        return CharacterID.generate()

    @pytest.fixture
    def valid_stats_data(self, sample_character_id):
        """Create valid data for CharacterStatsChanged event."""
        return {
            "character_id": sample_character_id,
            "old_health": 100,
            "new_health": 80,
            "old_mana": 50,
            "new_mana": 50,
            "changed_at": datetime.now(),
        }

    def test_character_stats_changed_success(self, valid_stats_data):
        """Test successful CharacterStatsChanged event creation."""
        event = CharacterStatsChanged.create(**valid_stats_data)

        assert event.old_health == 100
        assert event.new_health == 80
        assert event.old_mana == 50
        assert event.new_mana == 50

    def test_character_stats_changed_negative_health_raises_error(self, sample_character_id):
        """Test that negative health raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterStatsChanged.create(
                character_id=sample_character_id,
                old_health=-10,
                new_health=80,
                old_mana=50,
                new_mana=50,
                changed_at=datetime.now(),
            )
        assert "Health values cannot be negative" in str(exc_info.value)

    def test_character_stats_changed_negative_mana_raises_error(self, sample_character_id):
        """Test that negative mana raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterStatsChanged.create(
                character_id=sample_character_id,
                old_health=100,
                new_health=80,
                old_mana=-5,
                new_mana=50,
                changed_at=datetime.now(),
            )
        assert "Mana values cannot be negative" in str(exc_info.value)

    def test_character_stats_changed_is_damage_taken(self, valid_stats_data):
        """Test is_damage_taken returns True when health decreases."""
        event = CharacterStatsChanged.create(**valid_stats_data)
        assert event.is_damage_taken() is True

    def test_character_stats_changed_is_healing(self, sample_character_id):
        """Test is_healing returns True when health increases."""
        event = CharacterStatsChanged.create(
            character_id=sample_character_id,
            old_health=80,
            new_health=100,
            old_mana=50,
            new_mana=50,
            changed_at=datetime.now(),
        )
        assert event.is_healing() is True

    def test_character_stats_changed_is_mana_consumed(self, valid_stats_data, sample_character_id):
        """Test is_mana_consumed returns appropriate value."""
        # Mana unchanged in valid_stats_data
        event = CharacterStatsChanged.create(**valid_stats_data)
        assert event.is_mana_consumed() is False

        event_mana_used = CharacterStatsChanged.create(
            character_id=sample_character_id,
            old_health=100,
            new_health=100,
            old_mana=50,
            new_mana=30,
            changed_at=datetime.now(),
        )
        assert event_mana_used.is_mana_consumed() is True

    def test_character_stats_changed_is_mana_restored(self, sample_character_id):
        """Test is_mana_restored returns True when mana increases."""
        event = CharacterStatsChanged.create(
            character_id=sample_character_id,
            old_health=100,
            new_health=100,
            old_mana=30,
            new_mana=50,
            changed_at=datetime.now(),
        )
        assert event.is_mana_restored() is True

    def test_character_stats_changed_get_damage_amount(self, valid_stats_data):
        """Test get_damage_amount returns correct value."""
        event = CharacterStatsChanged.create(**valid_stats_data)
        assert event.get_damage_amount() == 20

    def test_character_stats_changed_get_damage_amount_no_damage(self, sample_character_id):
        """Test get_damage_amount returns 0 when no damage."""
        event = CharacterStatsChanged.create(
            character_id=sample_character_id,
            old_health=100,
            new_health=100,
            old_mana=50,
            new_mana=50,
            changed_at=datetime.now(),
        )
        assert event.get_damage_amount() == 0

    def test_character_stats_changed_get_healing_amount(self, sample_character_id):
        """Test get_healing_amount returns correct value."""
        event = CharacterStatsChanged.create(
            character_id=sample_character_id,
            old_health=80,
            new_health=100,
            old_mana=50,
            new_mana=50,
            changed_at=datetime.now(),
        )
        assert event.get_healing_amount() == 20

    def test_character_stats_changed_to_dict(self, valid_stats_data):
        """Test dictionary serialization includes calculated fields."""
        event = CharacterStatsChanged.create(**valid_stats_data)
        result = event.to_dict()

        assert result["event_type"] == "character.stats_changed"
        assert result["old_health"] == 100
        assert result["new_health"] == 80
        assert result["health_changed"] is True
        assert result["mana_changed"] is False
        assert result["health_delta"] == -20
        assert result["mana_delta"] == 0


class TestCharacterLeveledUp:
    """Test suite for CharacterLeveledUp event."""

    @pytest.fixture
    def sample_character_id(self):
        """Create a sample character ID."""
        return CharacterID.generate()

    @pytest.fixture
    def valid_levelup_data(self, sample_character_id):
        """Create valid data for CharacterLeveledUp event."""
        return {
            "character_id": sample_character_id,
            "old_level": 5,
            "new_level": 6,
            "new_health": 120,
            "new_mana": 60,
            "skill_points_gained": 5,
            "leveled_up_at": datetime.now(),
        }

    def test_character_leveled_up_success(self, valid_levelup_data):
        """Test successful CharacterLeveledUp event creation."""
        event = CharacterLeveledUp.create(**valid_levelup_data)

        assert event.old_level == 5
        assert event.new_level == 6
        assert event.new_health == 120
        assert event.new_mana == 60
        assert event.skill_points_gained == 5

    def test_character_leveled_up_invalid_level_raises_error(self, sample_character_id):
        """Test that level < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterLeveledUp.create(
                character_id=sample_character_id,
                old_level=0,
                new_level=1,
                new_health=100,
                new_mana=50,
                skill_points_gained=5,
                leveled_up_at=datetime.now(),
            )
        assert "Levels must be at least 1" in str(exc_info.value)

    def test_character_leveled_up_same_level_raises_error(self, sample_character_id):
        """Test that new_level <= old_level raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterLeveledUp.create(
                character_id=sample_character_id,
                old_level=5,
                new_level=5,
                new_health=100,
                new_mana=50,
                skill_points_gained=5,
                leveled_up_at=datetime.now(),
            )
        assert "New level must be greater than old level" in str(exc_info.value)

    def test_character_leveled_up_negative_skill_points_raises_error(self, sample_character_id):
        """Test that negative skill_points_gained raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterLeveledUp.create(
                character_id=sample_character_id,
                old_level=5,
                new_level=6,
                new_health=100,
                new_mana=50,
                skill_points_gained=-1,
                leveled_up_at=datetime.now(),
            )
        assert "Skill points gained cannot be negative" in str(exc_info.value)

    def test_character_leveled_up_get_levels_gained(self, valid_levelup_data):
        """Test get_levels_gained returns correct value."""
        event = CharacterLeveledUp.create(**valid_levelup_data)
        assert event.get_levels_gained() == 1

    def test_character_leveled_up_get_event_type(self, valid_levelup_data):
        """Test get_event_type returns correct value."""
        event = CharacterLeveledUp.create(**valid_levelup_data)
        assert event.get_event_type() == "character.leveled_up"

    def test_character_leveled_up_to_dict(self, valid_levelup_data):
        """Test dictionary serialization includes levels_gained."""
        event = CharacterLeveledUp.create(**valid_levelup_data)
        result = event.to_dict()

        assert result["event_type"] == "character.leveled_up"
        assert result["levels_gained"] == 1
        assert result["old_level"] == 5
        assert result["new_level"] == 6


class TestCharacterDeleted:
    """Test suite for CharacterDeleted event."""

    @pytest.fixture
    def sample_character_id(self):
        """Create a sample character ID."""
        return CharacterID.generate()

    @pytest.fixture
    def valid_deletion_data(self, sample_character_id):
        """Create valid data for CharacterDeleted event."""
        return {
            "character_id": sample_character_id,
            "character_name": "Test Hero",
            "final_level": 10,
            "reason": "User requested deletion",
            "deleted_at": datetime.now(),
        }

    def test_character_deleted_success(self, valid_deletion_data):
        """Test successful CharacterDeleted event creation."""
        event = CharacterDeleted.create(**valid_deletion_data)

        assert event.character_name == "Test Hero"
        assert event.final_level == 10
        assert event.reason == "User requested deletion"

    def test_character_deleted_empty_name_raises_error(self, sample_character_id):
        """Test that empty character name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterDeleted.create(
                character_id=sample_character_id,
                character_name="",
                final_level=10,
                reason="User requested deletion",
                deleted_at=datetime.now(),
            )
        assert "Character name cannot be empty" in str(exc_info.value)

    def test_character_deleted_invalid_level_raises_error(self, sample_character_id):
        """Test that final_level < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterDeleted.create(
                character_id=sample_character_id,
                character_name="Test Hero",
                final_level=0,
                reason="User requested deletion",
                deleted_at=datetime.now(),
            )
        assert "Final level must be at least 1" in str(exc_info.value)

    def test_character_deleted_empty_reason_raises_error(self, sample_character_id):
        """Test that empty reason raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterDeleted.create(
                character_id=sample_character_id,
                character_name="Test Hero",
                final_level=10,
                reason="",
                deleted_at=datetime.now(),
            )
        assert "Deletion reason cannot be empty" in str(exc_info.value)

    def test_character_deleted_get_event_type(self, valid_deletion_data):
        """Test get_event_type returns correct value."""
        event = CharacterDeleted.create(**valid_deletion_data)
        assert event.get_event_type() == "character.deleted"

    def test_character_deleted_to_dict(self, valid_deletion_data):
        """Test dictionary serialization."""
        event = CharacterDeleted.create(**valid_deletion_data)
        result = event.to_dict()

        assert result["event_type"] == "character.deleted"
        assert result["character_name"] == "Test Hero"
        assert result["reason"] == "User requested deletion"


class TestCharacterLocationChanged:
    """Test suite for CharacterLocationChanged event."""

    @pytest.fixture
    def sample_character_id(self):
        """Create a sample character ID."""
        return CharacterID.generate()

    @pytest.fixture
    def valid_location_data(self, sample_character_id):
        """Create valid data for CharacterLocationChanged event."""
        return {
            "character_id": sample_character_id,
            "location_id_before": "loc_123",
            "location_id_after": "loc_456",
            "moved_at": datetime.now(),
        }

    def test_character_location_changed_success(self, valid_location_data):
        """Test successful CharacterLocationChanged event creation."""
        event = CharacterLocationChanged.create(**valid_location_data)

        assert event.location_id_before == "loc_123"
        assert event.location_id_after == "loc_456"

    def test_character_location_changed_initial_placement(self, sample_character_id):
        """Test event creation for initial placement (no previous location)."""
        event = CharacterLocationChanged.create(
            character_id=sample_character_id,
            location_id_before=None,
            location_id_after="loc_456",
            moved_at=datetime.now(),
        )

        assert event.location_id_before is None
        assert event.location_id_after == "loc_456"

    def test_character_location_changed_empty_new_location_raises_error(self, sample_character_id):
        """Test that empty new location raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterLocationChanged.create(
                character_id=sample_character_id,
                location_id_before="loc_123",
                location_id_after="",
                moved_at=datetime.now(),
            )
        assert "New location ID cannot be empty" in str(exc_info.value)

    def test_character_location_changed_is_initial_placement(self, valid_location_data):
        """Test is_initial_placement returns False when there was a previous location."""
        event = CharacterLocationChanged.create(**valid_location_data)
        assert event.is_initial_placement() is False

    def test_character_location_changed_is_initial_placement_true(self, sample_character_id):
        """Test is_initial_placement returns True for initial placement."""
        event = CharacterLocationChanged.create(
            character_id=sample_character_id,
            location_id_before=None,
            location_id_after="loc_456",
            moved_at=datetime.now(),
        )
        assert event.is_initial_placement() is True

    def test_character_location_changed_get_event_type(self, valid_location_data):
        """Test get_event_type returns correct value."""
        event = CharacterLocationChanged.create(**valid_location_data)
        assert event.get_event_type() == "character.location_changed"

    def test_character_location_changed_to_dict(self, valid_location_data):
        """Test dictionary serialization."""
        event = CharacterLocationChanged.create(**valid_location_data)
        result = event.to_dict()

        assert result["event_type"] == "character.location_changed"
        assert result["location_id_before"] == "loc_123"
        assert result["location_id_after"] == "loc_456"
