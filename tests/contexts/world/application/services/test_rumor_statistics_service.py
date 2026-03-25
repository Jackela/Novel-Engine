"""Test suite for RumorStatisticsService.

Tests the calculation of rumor statistics.
"""

import pytest

from src.contexts.world.application.services.rumor_statistics_service import (
    RumorStatisticsService,
)
from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin


class TestRumorStatisticsService:
    """Test cases for RumorStatisticsService."""

    @pytest.fixture
    def service(self) -> RumorStatisticsService:
        """Create a RumorStatisticsService instance."""
        return RumorStatisticsService()

    @pytest.fixture
    def sample_rumors(self) -> list[Rumor]:
        """Create sample rumors for testing."""
        return [
            Rumor(
                content="Rumor 1",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc1",
                spread_count=10,
            ),
            Rumor(
                content="Rumor 2",
                truth_value=50,
                origin_type=RumorOrigin.NPC,
                origin_location_id="loc2",
                spread_count=5,
            ),
            Rumor(
                content="Rumor 3",
                truth_value=0,
                origin_type=RumorOrigin.PLAYER,
                origin_location_id="loc3",
                spread_count=20,
            ),
        ]

    def test_calculate_statistics(
        self, service: RumorStatisticsService, sample_rumors: list[Rumor]
    ) -> None:
        """Test statistics calculation."""
        result = service.calculate_statistics(sample_rumors)

        assert result.is_ok
        stats = result.value
        assert stats.total_rumors == 3
        assert stats.active_rumors == 2
        assert stats.dead_rumors == 1
        assert stats.avg_truth == 75.0  # (100 + 50) / 2

    def test_calculate_statistics_empty_list(
        self, service: RumorStatisticsService
    ) -> None:
        """Test statistics calculation with empty list."""
        result = service.calculate_statistics([])

        assert result.is_ok
        stats = result.value
        assert stats.total_rumors == 0
        assert stats.active_rumors == 0
        assert stats.avg_truth == 0.0
        assert stats.most_spread is None

    def test_get_most_spread(
        self, service: RumorStatisticsService, sample_rumors: list[Rumor]
    ) -> None:
        """Test getting most spread rumor."""
        most_spread = service.get_most_spread(sample_rumors)

        assert most_spread is not None
        assert most_spread.spread_count == 20  # The dead rumor with highest spread

    def test_get_most_spread_empty(self, service: RumorStatisticsService) -> None:
        """Test getting most spread rumor from empty list."""
        most_spread = service.get_most_spread([])

        assert most_spread is None

    def test_get_average_truth(
        self, service: RumorStatisticsService, sample_rumors: list[Rumor]
    ) -> None:
        """Test calculating average truth."""
        avg_truth = service.get_average_truth(sample_rumors)

        assert avg_truth == 75.0  # (100 + 50) / 2

    def test_get_average_truth_empty(self, service: RumorStatisticsService) -> None:
        """Test calculating average truth with empty list."""
        avg_truth = service.get_average_truth([])

        assert avg_truth == 0.0

    def test_get_average_truth_all_dead(self, service: RumorStatisticsService) -> None:
        """Test calculating average truth with all dead rumors."""
        dead_rumors = [
            Rumor(
                content="Dead 1",
                truth_value=0,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc1",
            ),
            Rumor(
                content="Dead 2",
                truth_value=0,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc2",
            ),
        ]

        avg_truth = service.get_average_truth(dead_rumors)

        assert avg_truth == 0.0

    def test_count_active(
        self, service: RumorStatisticsService, sample_rumors: list[Rumor]
    ) -> None:
        """Test counting active rumors."""
        count = service.count_active(sample_rumors)

        assert count == 2

    def test_count_dead(
        self, service: RumorStatisticsService, sample_rumors: list[Rumor]
    ) -> None:
        """Test counting dead rumors."""
        count = service.count_dead(sample_rumors)

        assert count == 1

    def test_truth_distribution(self, service: RumorStatisticsService) -> None:
        """Test truth value distribution."""
        rumors = [
            Rumor(
                content="Dead",
                truth_value=0,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc1",
            ),
            Rumor(
                content="Low",
                truth_value=20,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc2",
            ),
            Rumor(
                content="Medium",
                truth_value=50,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc3",
            ),
            Rumor(
                content="High",
                truth_value=80,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc4",
            ),
            Rumor(
                content="Perfect",
                truth_value=95,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc5",
            ),
        ]

        distribution = service.get_truth_distribution(rumors)

        assert distribution["dead (0)"] == 1
        assert distribution["low (1-30)"] == 1
        assert distribution["medium (31-60)"] == 1
        assert distribution["high (61-90)"] == 1
        assert distribution["perfect (91-100)"] == 1

    def test_spread_distribution(self, service: RumorStatisticsService) -> None:
        """Test spread count distribution."""
        rumors = [
            Rumor(
                content="None",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc1",
                spread_count=0,
            ),
            Rumor(
                content="Low",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc2",
                spread_count=3,
            ),
            Rumor(
                content="Medium",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc3",
                spread_count=10,
            ),
            Rumor(
                content="High",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc4",
                spread_count=25,
            ),
            Rumor(
                content="Viral",
                truth_value=100,
                origin_type=RumorOrigin.EVENT,
                origin_location_id="loc5",
                spread_count=50,
            ),
        ]

        distribution = service.get_spread_distribution(rumors)

        assert distribution["none (0)"] == 1
        assert distribution["low (1-5)"] == 1
        assert distribution["medium (6-15)"] == 1
        assert distribution["high (16-30)"] == 1
        assert distribution["viral (31+)"] == 1
