"""Unit tests for the EventService.

Tests the EventService application layer, verifying:
- Event listing with filtering and pagination
- Event creation with validation
- Rumor generation from events
- Proper use of repository pattern
"""

import pytest

from src.api.schemas.world_schemas import CreateEventRequest
from src.contexts.world.application.services.event_service import EventService
from src.contexts.world.domain.entities import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    RumorOrigin,
)
from src.contexts.world.infrastructure.persistence.in_memory_event_repository import (
    InMemoryEventRepository,
)
from src.contexts.world.infrastructure.persistence.in_memory_rumor_repository import (
    InMemoryRumorRepository,
)


@pytest.fixture
def event_repo():
    """Create a fresh event repository for each test."""
    return InMemoryEventRepository()


@pytest.fixture
def rumor_repo():
    """Create a fresh rumor repository for each test."""
    return InMemoryRumorRepository()


@pytest.fixture
def service(event_repo, rumor_repo):
    """Create an EventService with fresh repositories."""
    return EventService(event_repo, rumor_repo)


@pytest.mark.unit
class TestEventServiceList:
    """Tests for EventService.list_events method."""

    async def test_list_empty_world(self, service):
        """Listing events for empty world returns empty result."""
        result = await service.list_events(world_id="test-world")

        assert result.events == []
        assert result.total_count == 0
        assert result.total_pages == 0

    async def test_list_with_events(self, service, event_repo):
        """Listing events returns all events for the world."""
        # Create an event
        event = HistoryEvent(
            id="evt-1",
            name="Test Event",
            description="A test event",
            event_type=EventType.POLITICAL,
            significance=EventSignificance.MODERATE,
            outcome=EventOutcome.NEUTRAL,
            date_description="Year 1000",
        )
        await event_repo.save(event)
        event_repo.register_world_event("test-world", event.id)

        result = await service.list_events(world_id="test-world")

        assert len(result.events) == 1
        assert result.events[0].name == "Test Event"
        assert result.total_count == 1

    async def test_list_with_filter_by_type(self, service, event_repo):
        """Filtering by event type returns only matching events."""
        # Create events of different types
        war_event = HistoryEvent(
            id="evt-war",
            name="War Event",
            description="A war",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.NEGATIVE,
            date_description="Year 1000",
        )
        treaty_event = HistoryEvent(
            id="evt-treaty",
            name="Treaty Event",
            description="A treaty",
            event_type=EventType.TREATY,
            significance=EventSignificance.MODERATE,
            outcome=EventOutcome.POSITIVE,
            date_description="Year 1001",
        )
        await event_repo.save(war_event)
        await event_repo.save(treaty_event)
        event_repo.register_world_event("test-world", war_event.id)
        event_repo.register_world_event("test-world", treaty_event.id)

        result = await service.list_events(
            world_id="test-world",
            event_type="war",
        )

        assert len(result.events) == 1
        assert result.events[0].event_type == EventType.WAR

    async def test_list_pagination(self, service, event_repo):
        """Pagination works correctly."""
        # Create 5 events
        for i in range(5):
            event = HistoryEvent(
                id=f"evt-{i}",
                name=f"Event {i}",
                description=f"Description {i}",
                event_type=EventType.POLITICAL,
                significance=EventSignificance.MODERATE,
                outcome=EventOutcome.NEUTRAL,
                date_description=f"Year {1000 + i}",
            )
            await event_repo.save(event)
            event_repo.register_world_event("test-world", event.id)

        # Get page 1 with page_size 2
        result = await service.list_events(
            world_id="test-world",
            page=1,
            page_size=2,
        )

        assert len(result.events) == 2
        assert result.total_count == 5
        assert result.total_pages == 3
        assert result.page == 1


@pytest.mark.unit
class TestEventServiceCreate:
    """Tests for EventService.create_event method."""

    async def test_create_event_success(self, service):
        """Creating an event succeeds with valid data."""
        request = CreateEventRequest(
            name="The Great War",
            description="A devastating conflict",
            event_type="war",
            significance="major",
            outcome="negative",
            date_description="Year 1042",
        )

        result = await service.create_event(
            world_id="test-world",
            data=request,
        )

        assert result.is_ok
        event, rumor = result.value
        assert event.name == "The Great War"
        assert event.event_type == EventType.WAR
        assert rumor is None  # generate_rumor defaults to False

    async def test_create_event_with_rumor_generation(self, service, rumor_repo):
        """Creating an event with generate_rumor=True creates a rumor."""
        request = CreateEventRequest(
            name="Dragon Sighting",
            description="A dragon was seen in the mountains",
            event_type="disaster",
            significance="major",
            outcome="negative",
            date_description="Year 1042",
            location_ids=["loc-mountains"],
            generate_rumor=True,
        )

        result = await service.create_event(
            world_id="test-world",
            data=request,
        )

        assert result.is_ok
        event, rumor = result.value
        assert rumor is not None
        assert rumor.origin_type == RumorOrigin.EVENT
        assert rumor.source_event_id == event.id
        assert "loc-mountains" in rumor.current_locations

    async def test_create_event_no_locations_no_rumor(self, service):
        """Creating an event with generate_rumor=True but no locations skips rumor."""
        request = CreateEventRequest(
            name="Secret Meeting",
            description="A secret meeting occurred",
            event_type="political",
            significance="minor",
            outcome="neutral",
            date_description="Year 1042",
            location_ids=[],  # No locations
            generate_rumor=True,
        )

        result = await service.create_event(
            world_id="test-world",
            data=request,
        )

        assert result.is_ok
        event, rumor = result.value
        assert rumor is None  # No locations, so no rumor generated

    async def test_create_event_invalid_type(self, service):
        """Creating an event with invalid type returns error."""
        request = CreateEventRequest(
            name="Invalid Event",
            description="Bad type",
            event_type="invalid_type",
            date_description="Year 1000",
        )

        result = await service.create_event(
            world_id="test-world",
            data=request,
        )

        assert result.is_error
        assert "Invalid event_type" in result.error

    async def test_create_event_invalid_significance(self, service):
        """Creating an event with invalid significance returns error."""
        request = CreateEventRequest(
            name="Invalid Event",
            description="Bad significance",
            event_type="war",
            significance="ultra_epic",
            date_description="Year 1000",
        )

        result = await service.create_event(
            world_id="test-world",
            data=request,
        )

        assert result.is_error
        assert "Invalid significance" in result.error


@pytest.mark.unit
class TestEventServiceGet:
    """Tests for EventService.get_event method."""

    async def test_get_event_success(self, service, event_repo):
        """Getting an existing event returns the event."""
        event = HistoryEvent(
            id="evt-123",
            name="Found Event",
            description="This event exists",
            event_type=EventType.FOUNDING,
            significance=EventSignificance.MODERATE,
            outcome=EventOutcome.POSITIVE,
            date_description="Year 1",
        )
        await event_repo.save(event)

        result = await service.get_event(
            event_id="evt-123",
            world_id="test-world",
        )

        assert result is not None
        assert result.name == "Found Event"

    async def test_get_event_not_found(self, service):
        """Getting a non-existent event returns None."""
        result = await service.get_event(
            event_id="nonexistent",
            world_id="test-world",
        )

        assert result is None
