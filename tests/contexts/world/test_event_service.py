"""
Tests for Event Service Module

Coverage targets:
- Event creation
- Timeline management
- Rumor generation
- Event queries
"""

import pytest
import pytest_asyncio
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

from src.contexts.world.application.services.event_service import (
    EventListResult,
    EventService,
)
from src.contexts.world.domain.entities import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
    Rumor,
    RumorOrigin,
)
from src.contexts.world.domain.ports.event_repository import EventRepository
from src.contexts.world.domain.ports.rumor_repository import RumorRepository
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.api.schemas.world_schemas import CreateEventRequest
from src.core.result import Ok, Err


class TestEventListResult:
    """Tests for EventListResult dataclass."""

    def test_result_creation(self):
        """Test result creation."""
        events = []
        result = EventListResult(
            events=events,
            total_count=100,
            page=1,
            page_size=20,
            total_pages=5,
        )
        
        assert result.events == events
        assert result.total_count == 100
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 5


@pytest.mark.asyncio
class TestEventService:
    """Tests for EventService class."""

    @pytest_asyncio.fixture
    async def mock_event_repo(self):
        """Create a mock event repository."""
        repo = AsyncMock(spec=EventRepository)
        return repo

    @pytest_asyncio.fixture
    async def mock_rumor_repo(self):
        """Create a mock rumor repository."""
        repo = AsyncMock(spec=RumorRepository)
        return repo

    @pytest_asyncio.fixture
    async def event_service(self, mock_event_repo, mock_rumor_repo):
        """Create an EventService instance."""
        service = EventService(
            event_repo=mock_event_repo,
            rumor_repo=mock_rumor_repo,
        )
        return service

    def test_initialization(self, mock_event_repo, mock_rumor_repo):
        """Test service initialization."""
        service = EventService(
            event_repo=mock_event_repo,
            rumor_repo=mock_rumor_repo,
        )
        
        assert service._event_repo == mock_event_repo
        assert service._rumor_repo == mock_rumor_repo

    async def test_list_events_basic(self, event_service, mock_event_repo):
        """Test basic event listing."""
        # Create mock events
        event1 = HistoryEvent(
            id="evt1",
            name="Event 1",
            description="Description 1",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
        )
        event2 = HistoryEvent(
            id="evt2",
            name="Event 2",
            description="Description 2",
            event_type=EventType.TREATY,
            significance=EventSignificance.MINOR,
            outcome=EventOutcome.PARTIAL_SUCCESS,
        )
        
        mock_event_repo.get_by_world_id = AsyncMock(return_value=[event1, event2])
        
        result = await event_service.list_events(world_id="world_001")
        
        assert isinstance(result, EventListResult)
        assert len(result.events) == 2
        assert result.total_count == 2
        assert result.page == 1

    async def test_list_events_with_filters(self, event_service, mock_event_repo):
        """Test event listing with filters."""
        event1 = HistoryEvent(
            id="evt1",
            name="War Event",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
            is_secret=False,
        )
        event2 = HistoryEvent(
            id="evt2",
            name="Secret Event",
            description="Description",
            event_type=EventType.TREATY,
            significance=EventSignificance.MINOR,
            outcome=EventOutcome.SUCCESS,
            is_secret=True,
        )
        
        mock_event_repo.get_by_world_id = AsyncMock(return_value=[event1, event2])
        
        # Filter by event_type
        result = await event_service.list_events(
            world_id="world_001",
            event_type="war",
        )
        
        assert len(result.events) == 1
        assert result.events[0].name == "War Event"

    async def test_list_events_with_secret_filter(self, event_service, mock_event_repo):
        """Test event listing with secret filter."""
        public_event = HistoryEvent(
            id="evt1",
            name="Public Event",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
            is_secret=False,
        )
        secret_event = HistoryEvent(
            id="evt2",
            name="Secret Event",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
            is_secret=True,
        )
        
        mock_event_repo.get_by_world_id = AsyncMock(
            return_value=[public_event, secret_event]
        )
        
        result = await event_service.list_events(
            world_id="world_001",
            is_secret=False,
        )
        
        assert len(result.events) == 1
        assert result.events[0].is_secret is False

    async def test_list_events_pagination(self, event_service, mock_event_repo):
        """Test event listing pagination."""
        events = []
        for i in range(25):
            events.append(HistoryEvent(
                id=f"evt{i}",
                name=f"Event {i}",
                description="Description",
                event_type=EventType.WAR,
                significance=EventSignificance.MINOR,
                outcome=EventOutcome.SUCCESS,
            ))
        
        mock_event_repo.get_by_world_id = AsyncMock(return_value=events)
        
        result = await event_service.list_events(
            world_id="world_001",
            page=2,
            page_size=10,
        )
        
        assert result.page == 2
        assert result.page_size == 10
        assert result.total_count == 25
        assert result.total_pages == 3
        assert len(result.events) == 10

    async def test_list_events_invalid_event_type(self, event_service, mock_event_repo):
        """Test event listing with invalid event type filter."""
        event = HistoryEvent(
            id="evt1",
            name="Event",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MINOR,
            outcome=EventOutcome.SUCCESS,
        )
        
        mock_event_repo.get_by_world_id = AsyncMock(return_value=[event])
        
        # Invalid filter should be ignored
        result = await event_service.list_events(
            world_id="world_001",
            event_type="invalid_type",
        )
        
        # Should return all events (filter ignored)
        assert len(result.events) == 1

    async def test_create_event_success(self, event_service, mock_event_repo, mock_rumor_repo):
        """Test successful event creation."""
        request = CreateEventRequest(
            name="Great War",
            description="A major conflict",
            event_type="war",
            significance="major",
            outcome="success",
            generate_rumor=False,
        )
        
        mock_event_repo.save = AsyncMock()
        
        result = await event_service.create_event(
            world_id="world_001",
            data=request,
        )
        
        assert result.is_ok is True
        event, rumor = result.value
        assert isinstance(event, HistoryEvent)
        assert event.name == "Great War"
        assert event.event_type == EventType.WAR
        assert rumor is None
        
        mock_event_repo.save.assert_called_once()

    async def test_create_event_with_rumor(self, event_service, mock_event_repo, mock_rumor_repo):
        """Test event creation with rumor generation."""
        request = CreateEventRequest(
            name="Secret Treaty",
            description="A secret agreement",
            event_type="treaty",
            significance="major",
            outcome="success",
            generate_rumor=True,
            location_ids=["loc_001"],
        )
        
        mock_event_repo.save = AsyncMock()
        mock_rumor_repo.save = AsyncMock()
        
        result = await event_service.create_event(
            world_id="world_001",
            data=request,
        )
        
        assert result.is_ok is True
        event, rumor = result.value
        assert isinstance(event, HistoryEvent)
        assert isinstance(rumor, Rumor)
        assert rumor.content is not None
        
        mock_event_repo.save.assert_called_once()
        mock_rumor_repo.save.assert_called_once()

    async def test_create_event_invalid_type(self, event_service):
        """Test event creation with invalid event type."""
        request = CreateEventRequest(
            name="Test Event",
            description="Description",
            event_type="invalid_type",
            significance="major",
            outcome="success",
        )
        
        result = await event_service.create_event(
            world_id="world_001",
            data=request,
        )
        
        assert result.is_error is True
        assert "Invalid event_type" in result.error

    async def test_create_event_invalid_significance(self, event_service):
        """Test event creation with invalid significance."""
        request = CreateEventRequest(
            name="Test Event",
            description="Description",
            event_type="war",
            significance="invalid",
            outcome="success",
        )
        
        result = await event_service.create_event(
            world_id="world_001",
            data=request,
        )
        
        assert result.is_error is True
        assert "Invalid significance" in result.error

    async def test_create_event_validation_failure(self, event_service, mock_event_repo):
        """Test event creation with validation failure."""
        request = CreateEventRequest(
            name="",  # Empty name should fail validation
            description="Description",
            event_type="war",
            significance="major",
            outcome="success",
        )
        
        result = await event_service.create_event(
            world_id="world_001",
            data=request,
        )
        
        assert result.is_error is True

    async def test_get_event_found(self, event_service, mock_event_repo):
        """Test getting existing event."""
        event = HistoryEvent(
            id="evt_001",
            name="Test Event",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
        )
        
        mock_event_repo.get_by_id = AsyncMock(return_value=event)
        
        result = await event_service.get_event(
            event_id="evt_001",
            world_id="world_001",
        )
        
        assert result is not None
        assert result.id == "evt_001"

    async def test_get_event_not_found(self, event_service, mock_event_repo):
        """Test getting non-existent event."""
        mock_event_repo.get_by_id = AsyncMock(return_value=None)
        
        result = await event_service.get_event(
            event_id="nonexistent",
            world_id="world_001",
        )
        
        assert result is None

    async def test_bulk_import_events_success(self, event_service, mock_event_repo):
        """Test successful bulk import."""
        events_data = [
            {
                "name": "Event 1",
                "description": "Description 1",
                "event_type": "war",
                "significance": "major",
                "outcome": "success",
            },
            {
                "name": "Event 2",
                "description": "Description 2",
                "event_type": "treaty",
                "significance": "minor",
                "outcome": "success",
            },
        ]
        
        mock_event_repo.save = AsyncMock()
        
        result = await event_service.bulk_import_events(
            world_id="world_001",
            events_data=events_data,
        )
        
        assert result.is_ok is True
        assert result.value["imported_count"] == 2
        assert result.value["failed_count"] == 0
        assert len(result.value["imported_ids"]) == 2

    async def test_bulk_import_events_partial_failure(self, event_service):
        """Test bulk import with partial failures."""
        events_data = [
            {
                "name": "Valid Event",
                "description": "Description",
                "event_type": "war",
                "significance": "major",
                "outcome": "success",
            },
            {
                "name": "",  # Invalid - empty name
                "description": "Description",
                "event_type": "war",
                "significance": "major",
                "outcome": "success",
            },
        ]
        
        result = await event_service.bulk_import_events(
            world_id="world_001",
            events_data=events_data,
            atomic=False,  # Non-atomic, should continue on failure
        )
        
        assert result.is_ok is True  # Overall success (atomic=False)
        assert result.value["imported_count"] == 1
        assert result.value["failed_count"] == 1

    async def test_bulk_import_events_atomic_failure(self, event_service):
        """Test bulk import with atomic transaction failure."""
        events_data = [
            {
                "name": "Valid Event",
                "description": "Description",
                "event_type": "war",
                "significance": "major",
                "outcome": "success",
            },
            {
                "name": "",  # Invalid
                "description": "Description",
                "event_type": "war",
                "significance": "major",
                "outcome": "success",
            },
        ]
        
        result = await event_service.bulk_import_events(
            world_id="world_001",
            events_data=events_data,
            atomic=True,  # Atomic, should abort on failure
        )
        
        assert result.is_error is True

    async def test_export_timeline(self, event_service, mock_event_repo):
        """Test timeline export."""
        event1 = HistoryEvent(
            id="evt1",
            name="Ancient War",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
            date_description="Year 100",
            structured_date=WorldCalendar(year=100, month=1, day=1),
        )
        event2 = HistoryEvent(
            id="evt2",
            name="Modern Treaty",
            description="Description",
            event_type=EventType.TREATY,
            significance=EventSignificance.MINOR,
            outcome=EventOutcome.SUCCESS,
            date_description="Year 200",
            structured_date=WorldCalendar(year=200, month=1, day=1),
        )
        
        mock_event_repo.get_by_world_id = AsyncMock(return_value=[event2, event1])
        
        result = await event_service.export_timeline(world_id="world_001")
        
        assert result["world_id"] == "world_001"
        assert result["format"] == "json"
        assert "timeline" in result
        assert result["metadata"]["total_events"] == 2

    async def test_export_timeline_with_filters(self, event_service, mock_event_repo):
        """Test timeline export with filters."""
        event1 = HistoryEvent(
            id="evt1",
            name="War Event",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
        )
        event2 = HistoryEvent(
            id="evt2",
            name="Treaty Event",
            description="Description",
            event_type=EventType.TREATY,
            significance=EventSignificance.MINOR,
            outcome=EventOutcome.SUCCESS,
        )
        
        mock_event_repo.get_by_world_id = AsyncMock(return_value=[event1, event2])
        
        result = await event_service.export_timeline(
            world_id="world_001",
            event_types=["war"],
        )
        
        # Only war events should be in timeline
        all_events = []
        for entry in result["timeline"]:
            all_events.extend(entry["events"])
        
        assert len(all_events) == 1
        assert all_events[0]["event_type"] == "war"

    async def test_generate_rumor_from_event(self, event_service, mock_rumor_repo):
        """Test rumor generation from event."""
        event = HistoryEvent(
            id="evt_001",
            name="Battle of Kings",
            description="A great battle between kingdoms",
            event_type=EventType.WAR,
            significance=EventSignificance.LEGENDARY,
            outcome=EventOutcome.SUCCESS,
            location_ids=["loc_001", "loc_002"],
        )
        
        mock_rumor_repo.save = AsyncMock()
        
        rumor = await event_service._generate_rumor_from_event(
            event=event,
            world_id="world_001",
        )
        
        assert isinstance(rumor, Rumor)
        assert rumor.origin_type == RumorOrigin.EVENT
        assert rumor.source_event_id == "evt_001"
        assert rumor.truth_value == 95  # Legendary significance
        assert "Battle of Kings" in rumor.content

    async def test_generate_rumor_no_locations(self, event_service):
        """Test rumor generation fails without locations."""
        event = HistoryEvent(
            id="evt_001",
            name="Battle",
            description="Description",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.SUCCESS,
            location_ids=[],  # No locations
        )
        
        rumor = await event_service._generate_rumor_from_event(
            event=event,
            world_id="world_001",
        )
        
        assert rumor is None
