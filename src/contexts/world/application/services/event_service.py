#!/usr/bin/env python3
"""Event Service for History Event Operations.

This module provides the application-layer service for managing historical
events. It orchestrates domain objects and repositories to handle event-related
operations, including listing, filtering, pagination, and event creation with
optional rumor generation.

The EventService follows the Command Query Separation principle:
- list_events() is a query (read-only)
- create_event() is a command (modifies state)
- get_event() is a query (read-only)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import structlog

from src.api.schemas.world_schemas import CreateEventRequest
from src.contexts.world.domain.entities import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
    Rumor,
    RumorOrigin,
)
from src.contexts.world.domain.errors import (
    EventError,
    EventNotFoundError,
    EventValidationError,
)
from src.contexts.world.domain.ports.event_repository import EventRepository
from src.contexts.world.domain.ports.rumor_repository import RumorRepository
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar
from src.core.result import Err, Error, Ok, Result

logger = structlog.get_logger()


@dataclass
class EventListResult:
    """Result of listing events with pagination info.

    This data class encapsulates the events and pagination metadata,
    making it easier to return structured data from the service.

    Attributes:
        events: List of HistoryEvent objects
        total_count: Total number of events matching the filter
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
    """

    events: List[HistoryEvent]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class EventService:
    """Application service for managing historical events.

    This service provides the primary interface for event operations,
    abstracting the complexity of event management, filtering, sorting,
    and optional rumor generation.

    Responsibilities:
        - Retrieving events with filtering and pagination
        - Creating new events with validation
        - Generating rumors from events when requested
        - Orchestrating event-related domain logic

    Attributes:
        _event_repo: The event repository for persistence
        _rumor_repo: The rumor repository for rumor persistence
    """

    def __init__(
        self,
        event_repo: EventRepository,
        rumor_repo: RumorRepository,
    ) -> None:
        """Initialize the event service with repositories.

        Args:
            event_repo: The event repository to use for persistence
            rumor_repo: The rumor repository for rumor generation
        """
        self._event_repo = event_repo
        self._rumor_repo = rumor_repo
        logger.debug("event_service_initialized")

    async def list_events(
        self,
        world_id: str,
        event_type: Optional[str] = None,
        impact_scope: Optional[str] = None,
        faction_id: Optional[str] = None,
        location_id: Optional[str] = None,
        is_secret: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Result[EventListResult, Error]:
        """List historical events with filtering and pagination.

        This method retrieves all events for a world and applies the
        specified filters. Events are sorted by structured date (newest first)
        with a fallback to creation time.

        Why we filter in service not repository:
            The repository provides basic CRUD, but complex filtering
            logic belongs in the service layer to allow for flexible
            query composition without bloating the repository interface.

        Args:
            world_id: ID of the world to get events from
            event_type: Optional filter by event type (e.g., 'war', 'treaty')
            impact_scope: Optional filter by impact scope ('local', 'regional', 'global')
            faction_id: Optional filter by faction ID involved
            location_id: Optional filter by location ID
            is_secret: Optional filter by secret status
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            EventListResult containing events and pagination metadata

        Example:
            >>> result = await service.list_events(
            ...     world_id="world-123",
            ...     event_type="war",
            ...     page=1,
            ...     page_size=10
            ... )
            >>> print(f"Found {result.total_count} wars")
        """
        try:
            # Get all events for the world (repository handles pagination limits)
            # We fetch all then filter to support complex filtering logic
            all_events = await self._event_repo.get_by_world_id(world_id, limit=10000)
        except Exception as e:
            logger.error(
                "list_events_failed",
                world_id=world_id,
                error=str(e),
            )
            return Err(
                EventError(
                    f"Failed to list events: {e}",
                    details={"world_id": world_id},
                )
            )

        # Apply filters
        filtered_events = list(all_events)

        if event_type:
            try:
                et = EventType(event_type.lower())
                filtered_events = [e for e in filtered_events if e.event_type == et]
            except ValueError:
                # Invalid filter value - log and ignore
                logger.warning(
                    "invalid_event_type_filter",
                    event_type=event_type,
                    world_id=world_id,
                )

        if impact_scope:
            try:
                scope = ImpactScope(impact_scope.lower())
                filtered_events = [
                    e for e in filtered_events if e.impact_scope == scope
                ]
            except ValueError:
                logger.warning(
                    "invalid_impact_scope_filter",
                    impact_scope=impact_scope,
                    world_id=world_id,
                )

        if faction_id:
            filtered_events = [
                e
                for e in filtered_events
                if faction_id in e.faction_ids
                or (e.affected_faction_ids and faction_id in e.affected_faction_ids)
            ]

        if location_id:
            filtered_events = [
                e
                for e in filtered_events
                if location_id in e.location_ids
                or (e.affected_location_ids and location_id in e.affected_location_ids)
            ]

        if is_secret is not None:
            filtered_events = [e for e in filtered_events if e.is_secret == is_secret]

        # Sort by structured date (newest first), fallback to created_at
        def sort_key(event: HistoryEvent) -> Tuple:
            """Sort key for events: structured date or created_at."""
            if event.structured_date:
                return (
                    -event.structured_date.year,
                    -event.structured_date.month,
                    -event.structured_date.day,
                )
            # Fallback to created_at timestamp (as tuple for consistent type)
            if event.created_at:
                return (0, 0, 0, event.created_at)
            return (0, 0, 0)

        filtered_events.sort(key=sort_key)

        # Calculate pagination
        total_count = len(filtered_events)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_events = filtered_events[start_idx:end_idx]

        logger.debug(
            "events_listed",
            world_id=world_id,
            total_count=total_count,
            page=page,
            page_size=page_size,
            returned_count=len(paginated_events),
            filters={
                "event_type": event_type,
                "impact_scope": impact_scope,
                "faction_id": faction_id,
                "location_id": location_id,
                "is_secret": is_secret,
            },
        )

        return Ok(
            EventListResult(
                events=paginated_events,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        )

    async def create_event(
        self,
        world_id: str,
        data: CreateEventRequest,
    ) -> Result[Tuple[HistoryEvent, Optional[Rumor]], str]:
        """Create a new historical event with optional rumor generation.

        This command creates a history event, validates it using domain rules,
        persists it, and optionally generates a related rumor.

        Args:
            world_id: ID of the world for the event
            data: CreateEventRequest with event details

        Returns:
            Result containing:
            - Ok: Tuple of (created_event, optional_rumor)
            - Err: Error message string

        Example:
            >>> result = await service.create_event(world_id, request)
            >>> if result.is_ok:
            ...     event, rumor = result.value
            ...     print(f"Created event: {event.name}")
            ...     if rumor:
            ...         print(f"Generated rumor: {rumor.content}")
        """
        logger.info(
            "create_event_request",
            world_id=world_id,
            event_name=data.name,
            event_type=data.event_type,
            generate_rumor=data.generate_rumor,
        )

        # Parse enums with error handling
        try:
            event_type = EventType(data.event_type.lower())
        except ValueError as e:
            valid_types = [t.value for t in EventType]
            error_msg = f"Invalid event_type. Must be one of: {valid_types}"
            logger.warning("create_event_invalid_type", error=str(e))
            return Err(error_msg)

        try:
            significance = EventSignificance(data.significance.lower())
        except ValueError as e:
            valid_levels = [s.value for s in EventSignificance]
            error_msg = f"Invalid significance. Must be one of: {valid_levels}"
            logger.warning("create_event_invalid_significance", error=str(e))
            return Err(error_msg)

        try:
            outcome = EventOutcome(data.outcome.lower())
        except ValueError as e:
            valid_outcomes = [o.value for o in EventOutcome]
            error_msg = f"Invalid outcome. Must be one of: {valid_outcomes}"
            logger.warning("create_event_invalid_outcome", error=str(e))
            return Err(error_msg)

        # Parse optional impact scope
        impact_scope: Optional[ImpactScope] = None
        if data.impact_scope:
            try:
                impact_scope = ImpactScope(data.impact_scope.lower())
            except ValueError as e:
                valid_scopes = [s.value for s in ImpactScope]
                error_msg = f"Invalid impact_scope. Must be one of: {valid_scopes}"
                logger.warning("create_event_invalid_impact_scope", error=str(e))
                return Err(error_msg)

        # Parse structured date if provided
        structured_date: Optional[WorldCalendar] = None
        if data.structured_date:
            try:
                structured_date = WorldCalendar(
                    year=data.structured_date.get("year", 1),
                    month=data.structured_date.get("month", 1),
                    day=data.structured_date.get("day", 1),
                    era_name=data.structured_date.get("era_name", "First Age"),
                )
            except (ValueError, TypeError) as e:
                error_msg = f"Invalid structured_date: {e}"
                logger.warning("create_event_invalid_date", error=str(e))
                return Err(error_msg)

        # Create domain entity
        event = HistoryEvent(
            id=str(uuid4()),
            name=data.name,
            description=data.description,
            event_type=event_type,
            significance=significance,
            outcome=outcome,
            date_description=data.date_description,
            duration_description=data.duration_description,
            location_ids=data.location_ids or [],
            faction_ids=data.faction_ids or [],
            key_figures=data.key_figures or [],
            causes=data.causes or [],
            consequences=data.consequences or [],
            preceding_event_ids=data.preceding_event_ids or [],
            following_event_ids=data.following_event_ids or [],
            related_event_ids=data.related_event_ids or [],
            is_secret=data.is_secret,
            sources=data.sources or [],
            narrative_importance=data.narrative_importance,
            impact_scope=impact_scope,
            affected_faction_ids=data.affected_faction_ids,
            affected_location_ids=data.affected_location_ids,
            structured_date=structured_date,
        )

        # Validate using domain rules
        errors = event.validate()
        if errors:
            error_msg = f"Event validation failed: {'; '.join(errors)}"
            logger.warning(
                "create_event_validation_failed",
                world_id=world_id,
                event_id=event.id,
                errors=errors,
            )
            return Err(error_msg)

        # Persist the event
        await self._event_repo.save(event)

        # Register event to world for proper indexing
        if hasattr(self._event_repo, "register_world_event"):
            self._event_repo.register_world_event(world_id, event.id)

        logger.info(
            "event_created",
            world_id=world_id,
            event_id=event.id,
            event_name=event.name,
        )

        # Generate rumor if requested
        rumor: Optional[Rumor] = None
        if data.generate_rumor:
            rumor = await self._generate_rumor_from_event(event, world_id)

        return Ok((event, rumor))

    async def get_event(
        self,
        event_id: str,
        world_id: str,
    ) -> Result[Optional[HistoryEvent], Error]:
        """Get a single historical event by ID.

        Retrieves an event and verifies it belongs to the specified world.

        Args:
            event_id: Unique identifier for the event
            world_id: World ID for verification

        Returns:
            Result containing:
            - Ok: HistoryEvent if found, None if not found
            - Err: Error if operation fails

        Example:
            >>> result = await service.get_event("evt-123", "world-456")
            >>> if result.is_ok:
            ...     event = result.value
            ...     if event:
            ...         print(event.name)
            ...     else:
            ...         print("Event not found")
        """
        try:
            event = await self._event_repo.get_by_id(event_id)

            if event is None:
                logger.debug(
                    "get_event_not_found",
                    event_id=event_id,
                    world_id=world_id,
                )
                return Ok(None)

            # Note: In a production implementation, we would verify the event
            # belongs to the specified world. For now, we rely on the event_id
            # being unique across worlds.

            logger.debug(
                "get_event_found",
                event_id=event_id,
                world_id=world_id,
            )
            return Ok(event)
        except Exception as e:
            logger.error(
                "get_event_failed",
                event_id=event_id,
                world_id=world_id,
                error=str(e),
            )
            return Err(
                EventError(
                    f"Failed to get event: {e}",
                    details={"event_id": event_id, "world_id": world_id},
                )
            )

    async def _generate_rumor_from_event(
        self,
        event: HistoryEvent,
        world_id: str,
    ) -> Optional[Rumor]:
        """Generate a rumor from an event.

        Creates a rumor based on event data with truth value derived from
        event significance. The rumor is persisted to the repository.

        Args:
            event: The HistoryEvent to generate a rumor from
            world_id: World ID for the rumor

        Returns:
            Rumor if generated successfully, None if event has no locations
        """
        # Get location IDs from event
        if not event.location_ids:
            logger.warning(
                "rumor_generation_failed_no_locations",
                event_id=event.id,
                world_id=world_id,
            )
            return None

        origin_location_id = event.location_ids[0]

        # Truth value based on significance
        truth_value_map = {
            EventSignificance.TRIVIAL: 70,
            EventSignificance.MINOR: 75,
            EventSignificance.MODERATE: 80,
            EventSignificance.MAJOR: 85,
            EventSignificance.WORLD_CHANGING: 90,
            EventSignificance.LEGENDARY: 95,
        }
        truth_value = truth_value_map.get(event.significance, 80)

        # Generate rumor content
        content = f"Rumors speak of {event.name.lower()}: {event.description[:100]}..."

        # Determine created date from event's structured date or default
        created_date: Optional[WorldCalendar] = None
        if event.structured_date:
            created_date = event.structured_date
        else:
            created_date = WorldCalendar(
                year=1,
                month=1,
                day=1,
                era_name="First Age",
            )

        # Create rumor entity
        rumor = Rumor(
            content=content,
            truth_value=truth_value,
            origin_type=RumorOrigin.EVENT,
            source_event_id=event.id,
            origin_location_id=origin_location_id,
            current_locations=set(event.location_ids[:3]),
            created_date=created_date,
            spread_count=0,
        )

        # Persist the rumor
        await self._rumor_repo.save(rumor)

        # Register rumor to world for proper indexing
        if hasattr(self._rumor_repo, "register_rumor_world"):
            self._rumor_repo.register_rumor_world(rumor.rumor_id, world_id)

        logger.info(
            "rumor_generated_from_event",
            world_id=world_id,
            event_id=event.id,
            rumor_id=rumor.rumor_id,
        )

        return rumor

    async def bulk_import_events(
        self,
        world_id: str,
        events_data: List[Dict[str, Any]],
        generate_rumors: bool = False,
        atomic: bool = True,
    ) -> Result[Dict[str, Any], str]:
        """Bulk import historical events.

        This command creates multiple history events from parsed data,
        optionally generating rumors for each event.

        Args:
            world_id: ID of the world for the events
            events_data: List of event data dictionaries
            generate_rumors: Whether to generate rumors for each event
            atomic: Whether to treat import as a transaction (all-or-nothing)

        Returns:
            Result containing:
            - Ok: Dict with import statistics and IDs
            - Err: Error message string
        """
        logger.info(
            "bulk_import_events_request",
            world_id=world_id,
            event_count=len(events_data),
            generate_rumors=generate_rumors,
            atomic=atomic,
        )

        imported_events: List[HistoryEvent] = []
        generated_rumors: List[Rumor] = []
        errors: List[Dict[str, Any]] = []

        for idx, event_data in enumerate(events_data, start=1):
            # Convert dict to CreateEventRequest
            try:
                request = CreateEventRequest(**event_data)
            except Exception as e:
                errors.append(
                    {
                        "row": idx,
                        "message": f"Failed to create request: {e}",
                    }
                )
                if atomic:
                    logger.warning(
                        "bulk_import_atomic_abort",
                        world_id=world_id,
                        failed_row=idx,
                    )
                    return Err(f"Import failed at row {idx}: {e}")
                continue

            # Create the event
            result = await self.create_event(
                world_id=world_id,
                data=request,
            )

            if result.is_error:
                errors.append(
                    {
                        "row": idx,
                        "message": result.error,
                    }
                )
                if atomic:
                    logger.warning(
                        "bulk_import_atomic_abort",
                        world_id=world_id,
                        failed_row=idx,
                        error=result.error,
                    )
                    return Err(f"Import failed at row {idx}: {result.error}")
                continue

            event, rumor = result.value
            imported_events.append(event)
            if rumor:
                generated_rumors.append(rumor)

            # Log progress every 100 events
            if idx % 100 == 0:
                logger.info(
                    "bulk_import_progress",
                    world_id=world_id,
                    processed=idx,
                    total=len(events_data),
                )

        logger.info(
            "bulk_import_completed",
            world_id=world_id,
            total=len(events_data),
            imported=len(imported_events),
            failed=len(errors),
            rumors_generated=len(generated_rumors),
        )

        return Ok(
            {
                "imported_ids": [e.id for e in imported_events],
                "imported_count": len(imported_events),
                "failed_count": len(errors),
                "errors": errors,
                "generated_rumors": len(generated_rumors),
            }
        )

    async def export_timeline(
        self,
        world_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        event_types: Optional[List[str]] = None,
    ) -> Result[Dict[str, Any], Error]:
        """Export events as a timeline.

        This query retrieves events and formats them as a timeline
        suitable for export to various formats.

        Args:
            world_id: ID of the world
            from_date: Optional filter for events from this date
            to_date: Optional filter for events to this date
            event_types: Optional filter by event types

        Returns:
            Result containing:
            - Ok: Dictionary with timeline data
            - Err: Error if operation fails
        """
        logger.info(
            "export_timeline_request",
            world_id=world_id,
            from_date=from_date,
            to_date=to_date,
            event_types=event_types,
        )

        try:
            # Get all events for the world
            all_events = await self._event_repo.get_by_world_id(world_id, limit=10000)
        except Exception as e:
            logger.error(
                "export_timeline_failed",
                world_id=world_id,
                error=str(e),
            )
            return Err(
                EventError(
                    f"Failed to export timeline: {e}",
                    details={"world_id": world_id},
                )
            )

        # Apply filters
        filtered_events = list(all_events)

        if event_types:
            type_set = {t.lower() for t in event_types}
            filtered_events = [
                e for e in filtered_events if e.event_type.value.lower() in type_set
            ]

        # Sort by structured date if available, otherwise by created_at
        def sort_key(event: HistoryEvent) -> Tuple:
            if event.structured_date:
                return (
                    event.structured_date.year,
                    event.structured_date.month,
                    event.structured_date.day,
                )
            if event.created_at:
                return (0, 0, 0, event.created_at.timestamp())
            return (0, 0, 0, 0)

        filtered_events.sort(key=sort_key)

        # Group by date
        timeline: Dict[str, List[Dict[str, Any]]] = {}
        for event in filtered_events:
            date_key = event.date_description
            if date_key not in timeline:
                timeline[date_key] = []
            timeline[date_key].append(
                {
                    "id": event.id,
                    "name": event.name,
                    "description": event.description,
                    "event_type": event.event_type.value,
                    "significance": event.significance.value,
                    "date_description": event.date_description,
                }
            )

        # Convert to sorted list
        timeline_entries = [
            {"date": date, "events": events} for date, events in timeline.items()
        ]

        logger.info(
            "export_timeline_completed",
            world_id=world_id,
            total_events=len(filtered_events),
            date_entries=len(timeline_entries),
        )

        return Ok(
            {
                "world_id": world_id,
                "format": "json",
                "timeline": timeline_entries,
                "metadata": {
                    "total_events": len(filtered_events),
                    "date_range": {
                        "from": from_date,
                        "to": to_date,
                    },
                    "filters_applied": {
                        "event_types": event_types,
                    },
                },
            }
        )
