#!/usr/bin/env python3
"""Tests for WorldSnapshot Entity.

Unit tests covering:
- WorldSnapshot creation and validation
- to_dict and from_dict serialization
- restore method for WorldState reconstruction
- size_bytes property
- Factory methods create() and create_from_world()
"""

import json
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Mock aioredis before any imports that might use it
sys.modules["aioredis"] = MagicMock()

from src.contexts.world.domain.entities.world_snapshot import WorldSnapshot
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def calendar() -> WorldCalendar:
    """Create a test calendar."""
    return WorldCalendar(
        year=1042,
        month=3,
        day=15,
        era_name="Third Age",
    )


@pytest.fixture
def sample_state_dict() -> dict:
    """Create sample WorldState dict for testing."""
    return {
        "id": "world-123",
        "name": "Test World",
        "status": "active",
        "calendar": {
            "year": 1042,
            "month": 3,
            "day": 15,
            "era_name": "Third Age",
            "days_per_month": 30,
            "months_per_year": 12,
        },
        "entities": [],
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "version": 1,
    }


@pytest.fixture
def sample_state_json(sample_state_dict: dict) -> str:
    """Create sample state JSON string."""
    return json.dumps(sample_state_dict)


@pytest.fixture
def snapshot(calendar: WorldCalendar, sample_state_json: str) -> WorldSnapshot:
    """Create a basic snapshot for testing."""
    return WorldSnapshot(
        snapshot_id="snapshot-001",
        world_id="world-123",
        calendar=calendar,
        state_json=sample_state_json,
        tick_number=5,
        description="Test snapshot",
    )


# ============================================================================
# Test WorldSnapshot Creation
# ============================================================================


class TestWorldSnapshotCreation:
    """Tests for WorldSnapshot creation and validation."""

    def test_create_snapshot(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Should create snapshot with all fields."""
        snapshot = WorldSnapshot(
            snapshot_id="snapshot-001",
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
            description="Test snapshot",
        )

        assert snapshot.snapshot_id == "snapshot-001"
        assert snapshot.world_id == "world-123"
        assert snapshot.calendar == calendar
        assert snapshot.state_json == sample_state_json
        assert snapshot.tick_number == 5
        assert snapshot.description == "Test snapshot"
        assert isinstance(snapshot.created_at, datetime)

    def test_auto_generate_snapshot_id(self, sample_state_json: str) -> None:
        """Should auto-generate snapshot_id if not provided."""
        snapshot = WorldSnapshot(
            world_id="world-123",
            state_json=sample_state_json,
        )

        assert snapshot.snapshot_id  # Should have a UUID
        assert len(snapshot.snapshot_id) == 36  # UUID format

    def test_auto_generate_created_at(self, sample_state_json: str) -> None:
        """Should auto-generate created_at if not provided."""
        before = datetime.now()
        snapshot = WorldSnapshot(
            world_id="world-123",
            state_json=sample_state_json,
        )
        after = datetime.now()

        assert before <= snapshot.created_at <= after

    def test_validation_empty_snapshot_id(self, sample_state_json: str) -> None:
        """Should reject empty snapshot_id."""
        with pytest.raises(ValueError, match="Snapshot ID cannot be empty"):
            WorldSnapshot(
                snapshot_id="",
                world_id="world-123",
                state_json=sample_state_json,
            )

    def test_validation_empty_world_id(self, sample_state_json: str) -> None:
        """Should reject empty world_id."""
        with pytest.raises(ValueError, match="World ID cannot be empty"):
            WorldSnapshot(
                snapshot_id="snapshot-001",
                world_id="",
                state_json=sample_state_json,
            )

    def test_validation_negative_tick_number(self, sample_state_json: str) -> None:
        """Should reject negative tick_number."""
        with pytest.raises(ValueError, match="Tick number cannot be negative"):
            WorldSnapshot(
                snapshot_id="snapshot-001",
                world_id="world-123",
                state_json=sample_state_json,
                tick_number=-1,
            )

    def test_validation_empty_state_json(self) -> None:
        """Should reject empty state_json."""
        with pytest.raises(ValueError, match="State JSON cannot be empty"):
            WorldSnapshot(
                snapshot_id="snapshot-001",
                world_id="world-123",
                state_json="",
            )

    def test_zero_tick_number_allowed(self, sample_state_json: str) -> None:
        """Should allow tick_number=0 for initial state."""
        snapshot = WorldSnapshot(
            snapshot_id="snapshot-001",
            world_id="world-123",
            state_json=sample_state_json,
            tick_number=0,
        )

        assert snapshot.tick_number == 0


# ============================================================================
# Test size_bytes Property
# ============================================================================


class TestSizeBytes:
    """Tests for size_bytes property."""

    def test_size_bytes_small_json(self) -> None:
        """Should calculate size for small JSON."""
        small_json = '{"key": "value"}'
        snapshot = WorldSnapshot(
            world_id="world-123",
            state_json=small_json,
        )

        assert snapshot.size_bytes == len(small_json.encode("utf-8"))

    def test_size_bytes_large_json(self, sample_state_dict: dict) -> None:
        """Should calculate size for larger JSON."""
        # Make a larger state
        large_state = sample_state_dict.copy()
        large_state["entities"] = [{"id": f"entity-{i}"} for i in range(100)]
        large_json = json.dumps(large_state)

        snapshot = WorldSnapshot(
            world_id="world-123",
            state_json=large_json,
        )

        assert snapshot.size_bytes == len(large_json.encode("utf-8"))
        assert snapshot.size_bytes > 1000  # Should be substantial

    def test_size_bytes_unicode(self) -> None:
        """Should correctly calculate size for unicode content."""
        unicode_json = '{"name": "世界"}'  # Chinese characters
        snapshot = WorldSnapshot(
            world_id="world-123",
            state_json=unicode_json,
        )

        assert snapshot.size_bytes == len(unicode_json.encode("utf-8"))


# ============================================================================
# Test to_dict
# ============================================================================


class TestToDict:
    """Tests for to_dict method."""

    def test_to_dict_basic(self, snapshot: WorldSnapshot) -> None:
        """Should convert snapshot to dictionary."""
        result = snapshot.to_dict()

        assert result["snapshot_id"] == snapshot.snapshot_id
        assert result["world_id"] == snapshot.world_id
        assert result["tick_number"] == snapshot.tick_number
        assert result["description"] == snapshot.description
        assert result["state_json"] == snapshot.state_json
        assert "created_at" in result
        assert "size_bytes" in result

    def test_to_dict_includes_calendar(self, snapshot: WorldSnapshot) -> None:
        """Should include calendar in dict."""
        result = snapshot.to_dict()

        assert result["calendar"] is not None
        assert result["calendar"]["year"] == 1042
        assert result["calendar"]["month"] == 3
        assert result["calendar"]["day"] == 15

    def test_to_dict_null_calendar(self, sample_state_json: str) -> None:
        """Should handle null calendar."""
        snapshot = WorldSnapshot(
            snapshot_id="snapshot-001",
            world_id="world-123",
            calendar=None,
            state_json=sample_state_json,
        )

        result = snapshot.to_dict()

        assert result["calendar"] is None

    def test_to_dict_includes_size_bytes(self, snapshot: WorldSnapshot) -> None:
        """Should include size_bytes in dict."""
        result = snapshot.to_dict()

        assert result["size_bytes"] == snapshot.size_bytes


# ============================================================================
# Test from_dict
# ============================================================================


class TestFromDict:
    """Tests for from_dict class method."""

    def test_from_dict_basic(self, snapshot: WorldSnapshot) -> None:
        """Should create snapshot from dictionary."""
        data = snapshot.to_dict()

        result = WorldSnapshot.from_dict(data)

        assert result.snapshot_id == snapshot.snapshot_id
        assert result.world_id == snapshot.world_id
        assert result.tick_number == snapshot.tick_number
        assert result.description == snapshot.description
        assert result.state_json == snapshot.state_json

    def test_from_dict_with_calendar(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Should parse calendar from dict."""
        data = {
            "snapshot_id": "snapshot-001",
            "world_id": "world-123",
            "calendar": calendar.to_dict(),
            "state_json": sample_state_json,
            "tick_number": 5,
        }

        result = WorldSnapshot.from_dict(data)

        assert result.calendar is not None
        assert result.calendar.year == 1042
        assert result.calendar.month == 3

    def test_from_dict_null_calendar(self, sample_state_json: str) -> None:
        """Should handle null calendar in dict."""
        data = {
            "snapshot_id": "snapshot-001",
            "world_id": "world-123",
            "calendar": None,
            "state_json": sample_state_json,
            "tick_number": 5,
        }

        result = WorldSnapshot.from_dict(data)

        assert result.calendar is None

    def test_from_dict_string_created_at(
        self,
        sample_state_json: str,
    ) -> None:
        """Should parse created_at from ISO string."""
        created_str = "2024-06-15T10:30:00"
        data = {
            "snapshot_id": "snapshot-001",
            "world_id": "world-123",
            "state_json": sample_state_json,
            "created_at": created_str,
        }

        result = WorldSnapshot.from_dict(data)

        assert result.created_at == datetime.fromisoformat(created_str)

    def test_from_dict_datetime_created_at(
        self,
        sample_state_json: str,
    ) -> None:
        """Should accept datetime object for created_at."""
        created = datetime(2024, 6, 15, 10, 30, 0)
        data = {
            "snapshot_id": "snapshot-001",
            "world_id": "world-123",
            "state_json": sample_state_json,
            "created_at": created,
        }

        result = WorldSnapshot.from_dict(data)

        assert result.created_at == created

    def test_from_dict_defaults(self, sample_state_json: str) -> None:
        """Should use defaults for missing optional fields."""
        data = {
            "world_id": "world-123",
            "state_json": sample_state_json,
        }

        result = WorldSnapshot.from_dict(data)

        assert result.snapshot_id  # Auto-generated
        assert result.tick_number == 0
        assert result.description == ""
        assert result.calendar is None


# ============================================================================
# Test restore
# ============================================================================


class TestRestore:
    """Tests for restore method."""

    def test_restore_valid_json(self, snapshot: WorldSnapshot) -> None:
        """Should restore WorldState from valid JSON."""
        # Mock WorldState.from_dict to avoid full deserialization complexity
        with patch(
            "src.contexts.world.domain.aggregates.world_state.WorldState.from_dict"
        ) as mock_from_dict:
            mock_instance = MagicMock()
            mock_from_dict.return_value = mock_instance

            result = snapshot.restore()

            mock_from_dict.assert_called_once()
            assert result == mock_instance

    def test_restore_invalid_json(self, sample_state_json: str) -> None:
        """Should raise ValueError for invalid JSON."""
        snapshot = WorldSnapshot(
            snapshot_id="snapshot-001",
            world_id="world-123",
            state_json="not valid json {",
        )

        with pytest.raises(ValueError, match="Invalid state_json"):
            snapshot.restore()


# ============================================================================
# Test Factory Methods
# ============================================================================


class TestFactoryMethods:
    """Tests for factory methods."""

    def test_create_auto_description(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Should auto-generate description from tick and calendar."""
        snapshot = WorldSnapshot.create(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

        assert "Tick 5" in snapshot.description
        assert "1042" in snapshot.description  # Year from calendar

    def test_create_custom_description(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Should use provided description."""
        snapshot = WorldSnapshot.create(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
            description="Before the great battle",
        )

        assert snapshot.description == "Before the great battle"

    def test_create_generates_id(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Should auto-generate snapshot_id."""
        snapshot = WorldSnapshot.create(
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

        assert snapshot.snapshot_id
        assert len(snapshot.snapshot_id) == 36  # UUID format

    def test_create_from_world(self, calendar: WorldCalendar) -> None:
        """Should create snapshot from WorldState."""
        # Mock WorldState
        mock_world = MagicMock()
        mock_world.id = "world-123"
        mock_world.calendar = calendar
        mock_world.to_dict.return_value = {"id": "world-123", "test": "data"}

        snapshot = WorldSnapshot.create_from_world(
            world=mock_world,
            tick_number=10,
        )

        assert snapshot.world_id == "world-123"
        assert snapshot.calendar == calendar
        assert snapshot.tick_number == 10
        assert "world-123" in snapshot.state_json

    def test_create_from_world_custom_description(
        self,
        calendar: WorldCalendar,
    ) -> None:
        """Should accept custom description in create_from_world."""
        mock_world = MagicMock()
        mock_world.id = "world-123"
        mock_world.calendar = calendar
        mock_world.to_dict.return_value = {"id": "world-123"}

        snapshot = WorldSnapshot.create_from_world(
            world=mock_world,
            tick_number=10,
            description="Custom description",
        )

        assert snapshot.description == "Custom description"


# ============================================================================
# Test String Representations
# ============================================================================


class TestStringRepresentations:
    """Tests for __str__ and __repr__ methods."""

    def test_str(self, snapshot: WorldSnapshot) -> None:
        """Should return readable string representation."""
        result = str(snapshot)

        assert "WorldSnapshot" in result
        assert "tick=5" in result
        assert "1042" in result  # Year

    def test_str_null_calendar(self, sample_state_json: str) -> None:
        """Should handle null calendar in str."""
        snapshot = WorldSnapshot(
            snapshot_id="snapshot-001",
            world_id="world-123",
            calendar=None,
            state_json=sample_state_json,
            tick_number=5,
        )

        result = str(snapshot)

        assert "Unknown" in result

    def test_repr(self, snapshot: WorldSnapshot) -> None:
        """Should return detailed string representation."""
        result = repr(snapshot)

        assert "WorldSnapshot" in result
        assert "tick_number=5" in result


# ============================================================================
# Test Serialization Round-trip
# ============================================================================


class TestSerializationRoundTrip:
    """Tests for serialize/deserialize round-trip."""

    def test_round_trip_basic(self, snapshot: WorldSnapshot) -> None:
        """Should survive to_dict -> from_dict round-trip."""
        data = snapshot.to_dict()
        restored = WorldSnapshot.from_dict(data)

        assert restored.snapshot_id == snapshot.snapshot_id
        assert restored.world_id == snapshot.world_id
        assert restored.tick_number == snapshot.tick_number
        assert restored.description == snapshot.description
        assert restored.state_json == snapshot.state_json

    def test_round_trip_with_calendar(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Should preserve calendar through round-trip."""
        original = WorldSnapshot(
            snapshot_id="snapshot-001",
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

        data = original.to_dict()
        restored = WorldSnapshot.from_dict(data)

        assert restored.calendar is not None
        assert restored.calendar.year == calendar.year
        assert restored.calendar.month == calendar.month
        assert restored.calendar.day == calendar.day
        assert restored.calendar.era_name == calendar.era_name

    def test_round_trip_preserves_size(
        self,
        calendar: WorldCalendar,
        sample_state_json: str,
    ) -> None:
        """Should preserve size through round-trip."""
        original = WorldSnapshot(
            snapshot_id="snapshot-001",
            world_id="world-123",
            calendar=calendar,
            state_json=sample_state_json,
            tick_number=5,
        )

        data = original.to_dict()
        restored = WorldSnapshot.from_dict(data)

        assert restored.size_bytes == original.size_bytes
