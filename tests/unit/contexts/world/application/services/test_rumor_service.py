"""Unit tests for the RumorService.

Tests the RumorService application layer, verifying:
- Rumor retrieval for locations
- Rumor retrieval by ID
- Sorting and filtering logic
- Veracity label calculation
"""

import pytest

from src.api.schemas.world_schemas import SortByEnum
from src.contexts.world.application.services.rumor_service import RumorService
from src.contexts.world.domain.entities import Rumor, RumorOrigin
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.contexts.world.infrastructure.persistence.in_memory_rumor_repository import (
    InMemoryRumorRepository,
)


@pytest.fixture
def rumor_repo():
    """Create a fresh rumor repository for each test."""
    return InMemoryRumorRepository()


@pytest.fixture
def service(rumor_repo):
    """Create a RumorService with fresh repository."""
    return RumorService(rumor_repo)


@pytest.mark.unit
class TestRumorServiceLocationRumors:
    """Tests for RumorService.get_location_rumors method."""

    async def test_get_location_rumors_empty(self, service):
        """Getting rumors for empty location returns empty list."""
        result = await service.get_location_rumors(
            location_id="loc-empty",
            world_id="test-world",
        )

        assert result == []

    async def test_get_location_rumors_with_data(self, service, rumor_repo):
        """Getting rumors returns only rumors at that location."""
        # Create rumors at different locations
        rumor_at_capital = Rumor(
            rumor_id="rumor-1",
            content="Rumor at capital",
            truth_value=80,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-capital",
            current_locations={"loc-capital", "loc-market"},
        )
        rumor_only_market = Rumor(
            rumor_id="rumor-2",
            content="Rumor only at market",
            truth_value=60,
            origin_type=RumorOrigin.NPC,
            origin_location_id="loc-market",
            current_locations={"loc-market"},
        )
        await rumor_repo.save(rumor_at_capital)
        await rumor_repo.save(rumor_only_market)
        # Register to world
        rumor_repo.register_rumor_world("rumor-1", "test-world")
        rumor_repo.register_rumor_world("rumor-2", "test-world")

        result = await service.get_location_rumors(
            location_id="loc-capital",
            world_id="test-world",
        )

        assert len(result) == 1
        assert result[0].rumor_id == "rumor-1"

    async def test_get_location_rumors_sorted_by_recent(self, service, rumor_repo):
        """Rumors are sorted by date when sort_by=RECENT."""
        # Create rumors with different dates
        old_rumor = Rumor(
            rumor_id="rumor-old",
            content="Old rumor",
            truth_value=50,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-test",
            current_locations={"loc-test"},
            created_date=WorldCalendar(year=1000, month=1, day=1, era_name="First Age"),
        )
        new_rumor = Rumor(
            rumor_id="rumor-new",
            content="New rumor",
            truth_value=50,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-test",
            current_locations={"loc-test"},
            created_date=WorldCalendar(year=1001, month=1, day=1, era_name="First Age"),
        )
        await rumor_repo.save(old_rumor)
        await rumor_repo.save(new_rumor)
        rumor_repo.register_rumor_world("rumor-old", "test-world")
        rumor_repo.register_rumor_world("rumor-new", "test-world")

        result = await service.get_location_rumors(
            location_id="loc-test",
            world_id="test-world",
            sort_by=SortByEnum.RECENT,
        )

        assert len(result) == 2
        assert result[0].rumor_id == "rumor-new"  # Newer first
        assert result[1].rumor_id == "rumor-old"


@pytest.mark.unit
class TestRumorServiceWorldRumors:
    """Tests for RumorService.get_world_rumors method."""

    async def test_get_world_rumors_empty(self, service):
        """Getting rumors for empty world returns empty list."""
        result = await service.get_world_rumors(world_id="empty-world")

        assert result == []

    async def test_get_world_rumors_all(self, service, rumor_repo):
        """Getting all rumors for a world."""
        rumor = Rumor(
            rumor_id="rumor-1",
            content="Test rumor",
            truth_value=70,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
            current_locations={"loc-1"},
        )
        await rumor_repo.save(rumor)
        rumor_repo.register_rumor_world("rumor-1", "test-world")

        result = await service.get_world_rumors(world_id="test-world")

        assert len(result) == 1
        assert result[0].rumor_id == "rumor-1"

    async def test_get_world_rumors_sorted_by_reliable(self, service, rumor_repo):
        """Rumors sorted by truth_value when sort_by=RELIABLE."""
        low_truth = Rumor(
            rumor_id="rumor-low",
            content="Low truth",
            truth_value=30,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
            current_locations={"loc-1"},
        )
        high_truth = Rumor(
            rumor_id="rumor-high",
            content="High truth",
            truth_value=90,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
            current_locations={"loc-1"},
        )
        await rumor_repo.save(low_truth)
        await rumor_repo.save(high_truth)
        rumor_repo.register_rumor_world("rumor-low", "test-world")
        rumor_repo.register_rumor_world("rumor-high", "test-world")

        result = await service.get_world_rumors(
            world_id="test-world",
            sort_by=SortByEnum.RELIABLE,
        )

        assert len(result) == 2
        assert result[0].rumor_id == "rumor-high"  # Higher truth first
        assert result[1].rumor_id == "rumor-low"

    async def test_get_world_rumors_sorted_by_spread(self, service, rumor_repo):
        """Rumors sorted by spread_count when sort_by=SPREAD."""
        low_spread = Rumor(
            rumor_id="rumor-low",
            content="Low spread",
            truth_value=50,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
            current_locations={"loc-1"},
            spread_count=1,
        )
        high_spread = Rumor(
            rumor_id="rumor-high",
            content="High spread",
            truth_value=50,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
            current_locations={"loc-1", "loc-2", "loc-3"},
            spread_count=5,
        )
        await rumor_repo.save(low_spread)
        await rumor_repo.save(high_spread)
        rumor_repo.register_rumor_world("rumor-low", "test-world")
        rumor_repo.register_rumor_world("rumor-high", "test-world")

        result = await service.get_world_rumors(
            world_id="test-world",
            sort_by=SortByEnum.SPREAD,
        )

        assert len(result) == 2
        assert result[0].rumor_id == "rumor-high"  # Higher spread first
        assert result[1].rumor_id == "rumor-low"

    async def test_get_world_rumors_with_limit(self, service, rumor_repo):
        """Limit parameter restricts number of results."""
        # Create 5 rumors
        for i in range(5):
            rumor = Rumor(
                rumor_id=f"rumor-{i}",
                content=f"Rumor {i}",
                truth_value=50,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc-1",
                current_locations={"loc-1"},
            )
            await rumor_repo.save(rumor)
            rumor_repo.register_rumor_world(f"rumor-{i}", "test-world")

        result = await service.get_world_rumors(
            world_id="test-world",
            limit=3,
        )

        assert len(result) == 3


@pytest.mark.unit
class TestRumorServiceGet:
    """Tests for RumorService.get_rumor method."""

    async def test_get_rumor_success(self, service, rumor_repo):
        """Getting an existing rumor returns the rumor."""
        rumor = Rumor(
            rumor_id="rumor-123",
            content="Found rumor",
            truth_value=75,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
            current_locations={"loc-1"},
        )
        await rumor_repo.save(rumor)

        result = await service.get_rumor(
            rumor_id="rumor-123",
            world_id="test-world",
        )

        assert result is not None
        assert result.rumor_id == "rumor-123"
        assert result.content == "Found rumor"

    async def test_get_rumor_not_found(self, service):
        """Getting a non-existent rumor returns None."""
        result = await service.get_rumor(
            rumor_id="nonexistent",
            world_id="test-world",
        )

        assert result is None


@pytest.mark.unit
class TestRumorServiceVeracityLabel:
    """Tests for RumorService.get_veracity_label static method."""

    def test_veracity_label_confirmed(self):
        """Truth value >= 80 returns 'Confirmed'."""
        assert RumorService.get_veracity_label(80) == "Confirmed"
        assert RumorService.get_veracity_label(95) == "Confirmed"

    def test_veracity_label_likely_true(self):
        """Truth value 60-79 returns 'Likely True'."""
        assert RumorService.get_veracity_label(60) == "Likely True"
        assert RumorService.get_veracity_label(79) == "Likely True"

    def test_veracity_label_uncertain(self):
        """Truth value 40-59 returns 'Uncertain'."""
        assert RumorService.get_veracity_label(40) == "Uncertain"
        assert RumorService.get_veracity_label(59) == "Uncertain"

    def test_veracity_label_likely_false(self):
        """Truth value 20-39 returns 'Likely False'."""
        assert RumorService.get_veracity_label(20) == "Likely False"
        assert RumorService.get_veracity_label(39) == "Likely False"

    def test_veracity_label_false(self):
        """Truth value < 20 returns 'False'."""
        assert RumorService.get_veracity_label(0) == "False"
        assert RumorService.get_veracity_label(19) == "False"
