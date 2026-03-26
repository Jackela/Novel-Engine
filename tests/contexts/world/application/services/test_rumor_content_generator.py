"""Test suite for RumorContentGenerator.

Tests the generation of rumor content from historical events.
"""

import pytest

from src.contexts.world.application.services.rumor_content_generator import (
    RumorContentGenerator,
)
from src.contexts.world.domain.entities.history_event import (
    EventType,
    HistoryEvent,
)


class TestRumorContentGenerator:
    """Test cases for RumorContentGenerator."""

    @pytest.fixture
    def generator(self) -> RumorContentGenerator:
        """Create a RumorContentGenerator instance."""
        return RumorContentGenerator()

    def test_generate_war_content(self, generator: RumorContentGenerator) -> None:
        """Test content generation for war events."""
        event = HistoryEvent(
            name="The Great War",
            event_type=EventType.WAR,
            faction_ids=["faction1", "faction2"],
            location_ids=["loc1"],
        )

        content = generator.generate_content(event)

        assert "conflict" in content.lower()
        assert "Great War" in content

    def test_generate_battle_content(self, generator: RumorContentGenerator) -> None:
        """Test content generation for battle events."""
        event = HistoryEvent(
            name="Battle of Hill 42",
            event_type=EventType.BATTLE,
            location_ids=["battlefield"],
        )

        content = generator.generate_content(event)

        assert "battle" in content.lower()

    def test_generate_death_content_with_figures(
        self, generator: RumorContentGenerator
    ) -> None:
        """Test content generation for death events with figures."""
        event = HistoryEvent(
            name="Death of the King",
            event_type=EventType.DEATH,
            key_figures=["King Arthur"],
            location_ids=["castle"],
        )

        content = generator.generate_content(event)

        assert "King Arthur" in content
        assert "passing" in content.lower()

    def test_generate_death_content_without_figures(
        self, generator: RumorContentGenerator
    ) -> None:
        """Test content generation for death events without figures."""
        event = HistoryEvent(
            name="Mysterious Death",
            event_type=EventType.DEATH,
            location_ids=["village"],
        )

        content = generator.generate_content(event)

        assert "notable figure" in content.lower()

    def test_generate_marriage_content(self, generator: RumorContentGenerator) -> None:
        """Test content generation for marriage events."""
        event = HistoryEvent(
            name="Royal Wedding",
            event_type=EventType.MARRIAGE,
            key_figures=["Prince", "Princess"],
            location_ids=["palace"],
        )

        content = generator.generate_content(event)

        assert "union" in content.lower()

    def test_generate_trade_content(self, generator: RumorContentGenerator) -> None:
        """Test content generation for trade events."""
        event = HistoryEvent(
            name="Trade Agreement",
            event_type=EventType.TRADE,
            location_ids=["market"],
        )

        content = generator.generate_content(event)

        assert "trade" in content.lower()
        assert "merchants" in content.lower()

    def test_format_faction_list_single(self, generator: RumorContentGenerator) -> None:
        """Test faction list formatting with single faction."""
        event = HistoryEvent(
            name="Event",
            event_type=EventType.WAR,
            faction_ids=["faction1"],
        )

        result = generator._format_faction_list(event)

        assert result == "an unknown faction"

    def test_format_faction_list_double(self, generator: RumorContentGenerator) -> None:
        """Test faction list formatting with two factions."""
        event = HistoryEvent(
            name="Event",
            event_type=EventType.WAR,
            faction_ids=["faction1", "faction2"],
        )

        result = generator._format_faction_list(event)

        assert result == "two great powers"

    def test_format_faction_list_multiple(
        self, generator: RumorContentGenerator
    ) -> None:
        """Test faction list formatting with multiple factions."""
        event = HistoryEvent(
            name="Event",
            event_type=EventType.WAR,
            faction_ids=["f1", "f2", "f3", "f4"],
        )

        result = generator._format_faction_list(event)

        assert result == "4 factions"

    def test_format_faction_list_empty(self, generator: RumorContentGenerator) -> None:
        """Test faction list formatting with no factions."""
        event = HistoryEvent(
            name="Event",
            event_type=EventType.WAR,
        )

        result = generator._format_faction_list(event)

        assert result == "unknown parties"

    def test_format_location_list_single(
        self, generator: RumorContentGenerator
    ) -> None:
        """Test location list formatting with single location."""
        event = HistoryEvent(
            name="Event",
            event_type=EventType.BATTLE,
            location_ids=["loc1"],
        )

        result = generator._format_location_list(event)

        assert result == "a distant land"

    def test_format_location_list_multiple(
        self, generator: RumorContentGenerator
    ) -> None:
        """Test location list formatting with multiple locations."""
        event = HistoryEvent(
            name="Event",
            event_type=EventType.BATTLE,
            location_ids=["loc1", "loc2", "loc3"],
        )

        result = generator._format_location_list(event)

        assert result == "several locations"

    def test_format_location_list_empty(self, generator: RumorContentGenerator) -> None:
        """Test location list formatting with no locations."""
        event = HistoryEvent(
            name="Event",
            event_type=EventType.BATTLE,
        )

        result = generator._format_location_list(event)

        assert result == "an unknown location"

    def test_all_event_types(self, generator: RumorContentGenerator) -> None:
        """Test that all event types have content generators."""
        for event_type in EventType:
            event = HistoryEvent(
                name=f"Test {event_type.name}",
                event_type=event_type,
                location_ids=["test_loc"],
            )

            content = generator.generate_content(event)

            assert content is not None
            assert len(content) > 0
