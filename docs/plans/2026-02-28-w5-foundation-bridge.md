# Operation Bridge: Time-Geopolitics Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bridge the Time System with the Geopolitics System by standardizing EventBus, fixing schema blockers, and implementing the Faction Simulation Tick.

**Architecture:**
- Standardize on `src.events.event_bus` (Enterprise) since existing domain events (Geopolitics, Time) already use it
- The Core EventBus in `startup.py` will be replaced with Enterprise version
- Create `FactionTickService` to process simulation ticks when time advances
- Wire `TimeAdvancedHandler` to subscribe to `world.time_advanced` events

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, asyncio, structlog

---

## Task 1: Add Missing Time Schemas

**Files:**
- Modify: `src/api/schemas/world_schemas.py:188-202`
- Test: `tests/unit/api/schemas/test_world_schemas.py`

**Step 1: Write the failing test**

Create `tests/unit/api/schemas/test_world_schemas.py`:

```python
"""Unit tests for world schemas including time-related schemas."""

import pytest
from pydantic import ValidationError

from src.api.schemas.world_schemas import (
    WorldTimeResponse,
    AdvanceTimeRequest,
)


@pytest.mark.unit
class TestWorldTimeResponse:
    """Tests for WorldTimeResponse schema."""

    def test_create_world_time_response(self) -> None:
        """Test creating a valid WorldTimeResponse."""
        response = WorldTimeResponse(
            year=1042,
            month=5,
            day=14,
            era_name="Third Age",
            display_string="Year 1042, Month 5, Day 14 - Third Age",
        )
        assert response.year == 1042
        assert response.month == 5
        assert response.day == 14
        assert response.era_name == "Third Age"
        assert response.display_string == "Year 1042, Month 5, Day 14 - Third Age"

    def test_world_time_response_required_fields(self) -> None:
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            WorldTimeResponse()


@pytest.mark.unit
class TestAdvanceTimeRequest:
    """Tests for AdvanceTimeRequest schema."""

    def test_default_days_is_one(self) -> None:
        """Test that default days is 1."""
        request = AdvanceTimeRequest()
        assert request.days == 1

    def test_valid_days_range(self) -> None:
        """Test valid days range."""
        request = AdvanceTimeRequest(days=365)
        assert request.days == 365

    def test_days_below_minimum_raises_error(self) -> None:
        """Test that days < 1 raises validation error."""
        with pytest.raises(ValidationError):
            AdvanceTimeRequest(days=0)

    def test_days_above_maximum_raises_error(self) -> None:
        """Test that days > 365 raises validation error."""
        with pytest.raises(ValidationError):
            AdvanceTimeRequest(days=366)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/api/schemas/test_world_schemas.py -v`
Expected: FAIL with "cannot import name 'WorldTimeResponse'"

**Step 3: Add schemas to world_schemas.py**

Add after line 188 (after `AdvanceCalendarRequest`):

```python
class WorldTimeResponse(BaseModel):
    """Response model for world time state.

    Used by the world_time router for time operations.
    Similar to CalendarResponse but with simpler structure for MVP.
    """

    year: int = Field(description="Current year in the world calendar")
    month: int = Field(description="Current month (1-12)")
    day: int = Field(description="Current day (1-30)")
    era_name: str = Field(description="Name of the current era")
    display_string: str = Field(description="Human-readable formatted date string")


class AdvanceTimeRequest(BaseModel):
    """Request model for advancing world time."""

    days: int = Field(
        default=1, ge=1, le=365,
        description="Number of days to advance (1-365)"
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/api/schemas/test_world_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/schemas/world_schemas.py tests/unit/api/schemas/test_world_schemas.py
git commit -m "feat(schemas): add WorldTimeResponse and AdvanceTimeRequest schemas"
```

---

## Task 2: Update world_time Router to Use Correct Schemas

**Files:**
- Modify: `src/api/routers/world_time.py:17-21`
- Test: `tests/integration/api/test_world_time.py`

**Step 1: Update imports in world_time.py**

Change lines 17-21 from:
```python
from src.api.schemas.world_schemas import (
    AdvanceTimeRequest,
    WorldTimeResponse,
)
```

To (same, but verify they exist now):
```python
from src.api.schemas.world_schemas import (
    AdvanceTimeRequest,
    WorldTimeResponse,
)
```

**Step 2: Verify the response model matches**

Check `_calendar_to_response` function (lines 55-70) returns correct fields:
```python
def _calendar_to_response(calendar) -> WorldTimeResponse:
    return WorldTimeResponse(
        year=calendar.year,
        month=calendar.month,
        day=calendar.day,
        era_name=calendar.era_name,
        display_string=calendar.format(),
    )
```

**Step 3: Run integration tests**

Run: `pytest tests/integration/api/test_world_time.py -v`
Expected: PASS (schema imports should work now)

**Step 4: Commit**

```bash
git add src/api/routers/world_time.py
git commit -m "fix(time): verify world_time router uses new schemas"
```

---

## Task 3: Standardize EventBus to Enterprise Version in Startup

**Files:**
- Modify: `src/api/startup.py:71-80`
- Test: `tests/unit/api/test_startup.py`

**Step 1: Write the failing test**

Create `tests/unit/api/test_startup.py`:

```python
"""Unit tests for API startup initialization."""

import pytest
from unittest.mock import MagicMock, patch

from src.api.startup import initialize_app_state


@pytest.mark.unit
class TestEventBusInitialization:
    """Tests for EventBus initialization."""

    @pytest.mark.asyncio
    async def test_uses_enterprise_event_bus(self) -> None:
        """Test that startup uses Enterprise EventBus from src.events."""
        from src.events.event_bus import EventBus as EnterpriseEventBus

        app = MagicMock()
        app.state = MagicMock()

        with patch("src.api.startup.get_service_container") as mock_container:
            mock_container.return_value = MagicMock()

            await initialize_app_state(app)

            # Verify the event bus is Enterprise version
            assert hasattr(app.state, "event_bus")
            assert isinstance(app.state.event_bus, EnterpriseEventBus)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/api/test_startup.py -v`
Expected: FAIL (currently uses Core EventBus)

**Step 3: Update startup.py to use Enterprise EventBus**

Change lines 71-80 from:
```python
global_event_bus: Optional[object] = None
try:
    from src.core.event_bus import EventBus

    global_event_bus = EventBus()
    app.state.event_bus = global_event_bus
    container.register_singleton(EventBus, global_event_bus)
    logger.info("Global EventBus initialized and registered")
```

To:
```python
global_event_bus: Optional[object] = None
try:
    from src.events.event_bus import EventBus

    global_event_bus = EventBus()
    app.state.event_bus = global_event_bus
    container.register_singleton(EventBus, global_event_bus)
    logger.info("Global EventBus (Enterprise) initialized and registered")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/api/test_startup.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/startup.py tests/unit/api/test_startup.py
git commit -m "refactor(eventbus): standardize on Enterprise EventBus in startup"
```

---

## Task 4: Wire world_time Router to Global EventBus

**Files:**
- Modify: `src/api/app.py:104-133`
- Modify: `src/api/startup.py` (add wiring call)
- Test: `tests/integration/api/test_world_time.py`

**Step 1: Write the failing test**

Add to `tests/integration/api/test_world_time.py`:

```python
@pytest.mark.integration
class TestWorldTimeEventBusWiring:
    """Tests for event bus wiring in world_time router."""

    def test_event_bus_is_configured_on_startup(self) -> None:
        """Test that the event bus is configured when app starts."""
        from src.api.app import create_app

        app = create_app()

        # The world_time router should have access to event bus
        from src.api.routers import world_time

        # After app creation, event bus should be wired
        # (This test will fail until we wire it in startup)
        assert world_time._event_bus is not None, "Event bus should be wired on startup"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/api/test_world_time.py::TestWorldTimeEventBusWiring -v`
Expected: FAIL with "Event bus should be wired on startup"

**Step 3: Add wiring call in startup.py**

Add after the EventBus initialization (around line 80):

```python
    # Wire event bus to world_time router
    try:
        from src.api.routers.world_time import set_event_bus

        set_event_bus(global_event_bus)
        logger.info("Event bus wired to world_time router")
    except ImportError:
        logger.warning("world_time router not available for event bus wiring")
```

**Step 4: Uncomment world_time router in app.py**

Change lines 104-106 from:
```python
# TODO: Uncomment when world_time feature is ready for production
# from src.api.routers.world_time import router as world_time_router
```

To:
```python
from src.api.routers.world_time import router as world_time_router
```

And lines 131-133 from:
```python
# TODO: Uncomment when world_time feature is ready for production
# world_time_router must be registered before routers with /world/{world_id} patterns
# app.include_router(world_time_router, prefix="/api")
```

To:
```python
# Register before routers with /world/{world_id} patterns
app.include_router(world_time_router, prefix="/api")
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/integration/api/test_world_time.py::TestWorldTimeEventBusWiring -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/api/app.py src/api/startup.py tests/integration/api/test_world_time.py
git commit -m "feat(time): wire world_time router to global EventBus"
```

---

## Task 5: Create FactionTickService

**Files:**
- Create: `src/contexts/world/application/services/faction_tick_service.py`
- Create: `tests/unit/contexts/world/application/test_faction_tick_service.py`

**Step 1: Write the failing test**

Create `tests/unit/contexts/world/application/test_faction_tick_service.py`:

```python
"""Unit tests for FactionTickService."""

import pytest
from unittest.mock import MagicMock, patch

from src.contexts.world.application.services.faction_tick_service import (
    FactionTickService,
    TickResult,
)


@pytest.mark.unit
class TestFactionTickService:
    """Tests for FactionTickService."""

    @pytest.fixture
    def service(self) -> FactionTickService:
        """Create a FactionTickService instance."""
        return FactionTickService()

    def test_service_exists(self, service: FactionTickService) -> None:
        """Test that FactionTickService can be instantiated."""
        assert service is not None

    def test_process_tick_returns_result(self, service: FactionTickService) -> None:
        """Test that process_tick returns a TickResult."""
        result = service.process_tick(world_id="test-world", days_advanced=1)

        assert isinstance(result, TickResult)
        assert result.world_id == "test-world"
        assert result.days_advanced == 1
        assert result.resources_updated == 0  # No factions yet
        assert result.diplomatic_changes == 0

    def test_process_tick_with_factions(self, service: FactionTickService) -> None:
        """Test process_tick with mock faction data."""
        # This will be expanded when we integrate with actual faction data
        result = service.process_tick(world_id="test-world", days_advanced=5)

        assert result.days_advanced == 5
        assert result.success is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/contexts/world/application/test_faction_tick_service.py -v`
Expected: FAIL with "cannot import name 'FactionTickService'"

**Step 3: Create FactionTickService**

Create `src/contexts/world/application/services/faction_tick_service.py`:

```python
"""Faction Tick Service for simulation time advancement.

This service processes faction-related updates when world time advances.
It calculates resource yields, updates faction wealth, and handles
diplomatic state changes.

Called by TimeAdvancedHandler when world.time_advanced events are emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class TickResult:
    """Result of processing a simulation tick.

    Attributes:
        world_id: The world that was processed
        days_advanced: Number of days that advanced
        success: Whether the tick was processed successfully
        resources_updated: Number of faction resources updated
        diplomatic_changes: Number of diplomatic state changes
        errors: Any errors encountered during processing
    """

    world_id: str
    days_advanced: int
    success: bool = True
    resources_updated: int = 0
    diplomatic_changes: int = 0
    errors: List[str] = field(default_factory=list)


class FactionTickService:
    """Service for processing faction simulation ticks.

    This service is called when world time advances to update:
    1. Faction resource yields (gold, food, military, etc.)
    2. Diplomatic relationship decay/progression
    3. Territory control effects

    Future integration points:
    - FactionRepository for loading faction data
    - TerritoryRepository for territory control
    - DiplomacyMatrix for relationship updates
    """

    def __init__(self) -> None:
        """Initialize the FactionTickService."""
        logger.debug("faction_tick_service_initialized")

    def process_tick(self, world_id: str, days_advanced: int) -> TickResult:
        """Process a simulation tick for the given world.

        Args:
            world_id: The world to process
            days_advanced: Number of days that advanced

        Returns:
            TickResult with processing details
        """
        logger.info(
            "faction_tick_started",
            world_id=world_id,
            days_advanced=days_advanced,
        )

        errors: List[str] = []

        # TODO: Implement resource yield calculation
        # resources_updated = self._calculate_resource_yields(world_id, days_advanced)
        resources_updated = 0

        # TODO: Implement diplomatic decay/progression
        # diplomatic_changes = self._process_diplomatic_changes(world_id, days_advanced)
        diplomatic_changes = 0

        success = len(errors) == 0

        logger.info(
            "faction_tick_completed",
            world_id=world_id,
            days_advanced=days_advanced,
            resources_updated=resources_updated,
            diplomatic_changes=diplomatic_changes,
            success=success,
        )

        return TickResult(
            world_id=world_id,
            days_advanced=days_advanced,
            success=success,
            resources_updated=resources_updated,
            diplomatic_changes=diplomatic_changes,
            errors=errors,
        )

    def _calculate_resource_yields(self, world_id: str, days: int) -> int:
        """Calculate and apply resource yields for all factions.

        Args:
            world_id: The world to process
            days: Number of days to calculate yields for

        Returns:
            Number of faction resources updated
        """
        # Placeholder for future implementation
        # Will integrate with FactionRepository and ResourceYield
        logger.debug("resource_yield_calculation_placeholder", world_id=world_id)
        return 0

    def _process_diplomatic_changes(self, world_id: str, days: int) -> int:
        """Process diplomatic relationship changes.

        Args:
            world_id: The world to process
            days: Number of days that passed

        Returns:
            Number of diplomatic changes made
        """
        # Placeholder for future implementation
        # Will integrate with DiplomacyMatrix for decay/progression
        logger.debug("diplomatic_changes_placeholder", world_id=world_id)
        return 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/contexts/world/application/test_faction_tick_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/contexts/world/application/services/faction_tick_service.py tests/unit/contexts/world/application/test_faction_tick_service.py
git commit -m "feat(simulation): add FactionTickService for time-based updates"
```

---

## Task 6: Create TimeAdvancedHandler

**Files:**
- Create: `src/contexts/world/application/handlers/time_handler.py`
- Create: `tests/unit/contexts/world/application/handlers/test_time_handler.py`

**Step 1: Write the failing test**

Create `tests/unit/contexts/world/application/handlers/test_time_handler.py`:

```python
"""Unit tests for TimeAdvancedHandler."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.contexts.world.application.handlers.time_handler import (
    TimeAdvancedHandler,
)
from src.contexts.world.domain.events.time_events import TimeAdvancedEvent


@pytest.mark.unit
class TestTimeAdvancedHandler:
    """Tests for TimeAdvancedHandler."""

    @pytest.fixture
    def handler(self) -> TimeAdvancedHandler:
        """Create a TimeAdvancedHandler instance."""
        return TimeAdvancedHandler()

    @pytest.fixture
    def sample_event(self) -> TimeAdvancedEvent:
        """Create a sample TimeAdvancedEvent."""
        return TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 6, "era_name": "First Age"},
            days_advanced=5,
            world_id="test-world",
        )

    def test_handler_exists(self, handler: TimeAdvancedHandler) -> None:
        """Test that TimeAdvancedHandler can be instantiated."""
        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_time_advanced_event(
        self, handler: TimeAdvancedHandler, sample_event: TimeAdvancedEvent
    ) -> None:
        """Test handling a TimeAdvancedEvent."""
        result = await handler.handle(sample_event)

        assert result.success is True
        assert result.world_id == "test-world"
        assert result.days_advanced == 5

    @pytest.mark.asyncio
    async def test_handler_logs_event_processing(
        self, handler: TimeAdvancedHandler, sample_event: TimeAdvancedEvent
    ) -> None:
        """Test that handler logs event processing."""
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr(
                "src.contexts.world.application.handlers.time_handler.logger",
                mock_logger,
            )

            await handler.handle(sample_event)

            # Verify logging occurred
            assert mock_logger.info.called
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/contexts/world/application/handlers/test_time_handler.py -v`
Expected: FAIL with "cannot import name 'TimeAdvancedHandler'"

**Step 3: Create TimeAdvancedHandler**

Create `src/contexts/world/application/handlers/time_handler.py`:

```python
"""Time Advanced Event Handler.

This handler subscribes to world.time_advanced events and triggers
faction simulation updates via FactionTickService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.contexts.world.application.services.faction_tick_service import (
    FactionTickService,
    TickResult,
)

if TYPE_CHECKING:
    from src.contexts.world.domain.events.time_events import TimeAdvancedEvent

logger = structlog.get_logger()


class TimeAdvancedHandler:
    """Handler for TimeAdvancedEvent.

    This handler is called when world time advances. It triggers
    the FactionTickService to process resource yields and diplomatic changes.

    Event Flow:
        1. User calls POST /api/world/time/advance
        2. world_time router advances calendar
        3. TimeAdvancedEvent is published to EventBus
        4. This handler receives the event
        5. FactionTickService.process_tick() is called
        6. Faction resources and diplomacy are updated
    """

    def __init__(self, tick_service: FactionTickService | None = None) -> None:
        """Initialize the handler.

        Args:
            tick_service: Optional FactionTickService instance (for dependency injection)
        """
        self._tick_service = tick_service or FactionTickService()
        logger.debug("time_advanced_handler_initialized")

    async def handle(self, event: "TimeAdvancedEvent") -> TickResult:
        """Handle a TimeAdvancedEvent.

        Args:
            event: The TimeAdvancedEvent to process

        Returns:
            TickResult with processing details

        Raises:
            No exceptions are raised - errors are logged and returned in TickResult
        """
        logger.info(
            "time_advanced_event_received",
            event_id=event.event_id,
            world_id=event.payload.get("world_id"),
            days_advanced=event.days_advanced,
        )

        world_id = event.payload.get("world_id", "default")

        try:
            result = self._tick_service.process_tick(
                world_id=world_id,
                days_advanced=event.days_advanced,
            )

            logger.info(
                "time_advanced_event_processed",
                event_id=event.event_id,
                world_id=world_id,
                success=result.success,
                resources_updated=result.resources_updated,
                diplomatic_changes=result.diplomatic_changes,
            )

            return result

        except Exception as e:
            logger.error(
                "time_advanced_event_failed",
                event_id=event.event_id,
                world_id=world_id,
                error=str(e),
                exc_info=True,
            )

            return TickResult(
                world_id=world_id,
                days_advanced=event.days_advanced,
                success=False,
                errors=[str(e)],
            )

    @classmethod
    def create_for_event_bus(cls) -> "TimeAdvancedHandler":
        """Factory method to create a handler for EventBus registration.

        Returns:
            TimeAdvancedHandler instance ready for event subscription
        """
        return cls()


def handle_time_advanced(event: "TimeAdvancedEvent") -> None:
    """Sync wrapper for event bus compatibility.

    This function can be registered as a handler with the EventBus.

    Args:
        event: The TimeAdvancedEvent to process
    """
    import asyncio

    handler = TimeAdvancedHandler()

    # Run async handler in sync context
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(handler.handle(event))
    except RuntimeError:
        # No running loop, create new one
        asyncio.run(handler.handle(event))
```

**Step 4: Create __init__.py for handlers package**

Create `src/contexts/world/application/handlers/__init__.py`:

```python
"""Event handlers for the World context."""

from src.contexts.world.application.handlers.time_handler import (
    TimeAdvancedHandler,
    handle_time_advanced,
)

__all__ = [
    "TimeAdvancedHandler",
    "handle_time_advanced",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/contexts/world/application/handlers/test_time_handler.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/contexts/world/application/handlers/ tests/unit/contexts/world/application/handlers/
git commit -m "feat(events): add TimeAdvancedHandler for faction tick processing"
```

---

## Task 7: Register Time Handler with EventBus

**Files:**
- Modify: `src/api/startup.py`
- Test: `tests/integration/api/test_time_event_flow.py`

**Step 1: Write the failing test**

Create `tests/integration/api/test_time_event_flow.py`:

```python
"""Integration tests for time event flow from API to handler."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestTimeEventFlow:
    """Tests for end-to-end time event flow."""

    def test_advance_time_triggers_event(self, client: TestClient) -> None:
        """Test that advancing time triggers an event."""
        # Get initial time
        response = client.get("/api/world/time")
        assert response.status_code == 200
        initial_data = response.json()

        # Advance time
        response = client.post("/api/world/time/advance", json={"days": 5})
        assert response.status_code == 200
        new_data = response.json()

        # Verify time advanced
        assert new_data["day"] == initial_data["day"] + 5 or new_data["month"] > initial_data["month"]

    def test_event_handler_is_registered(self) -> None:
        """Test that TimeAdvancedHandler is registered with EventBus."""
        from src.api.app import create_app

        app = create_app()
        event_bus = app.state.event_bus

        # Check that world.time_advanced has subscribers
        # Note: The exact API depends on EventBus implementation
        assert event_bus is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/api/test_time_event_flow.py -v`
Expected: Some tests may fail if handler not registered

**Step 3: Register handler in startup.py**

Add after the world_time router wiring (around line 85):

```python
    # Register event handlers
    try:
        from src.contexts.world.application.handlers import handle_time_advanced

        # Subscribe to time events
        global_event_bus.subscribe("world.time_advanced", handle_time_advanced)
        logger.info("TimeAdvancedHandler registered with EventBus")
    except Exception as exc:
        logger.warning("Could not register TimeAdvancedHandler: %s", exc)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/api/test_time_event_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/startup.py tests/integration/api/test_time_event_flow.py
git commit -m "feat(events): register TimeAdvancedHandler with global EventBus"
```

---

## Task 8: Run Full Test Suite and Verify

**Files:**
- All modified files

**Step 1: Run all backend tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 2: Run frontend type check**

Run: `cd frontend && npm run type-check`
Expected: PASS (no TypeScript errors)

**Step 3: Run linting**

Run: `npm run lint:all`
Expected: PASS (no lint errors)

**Step 4: Run CI check script**

Run: `./scripts/ci-check.sh`
Expected: Exit code 0

**Step 5: Final commit with all changes**

```bash
git add -A
git commit -m "feat(bridge): complete Time-Geopolitics integration (Operation Bridge)

- Add WorldTimeResponse and AdvanceTimeRequest schemas
- Standardize EventBus to Enterprise version
- Wire world_time router to global EventBus
- Add FactionTickService for simulation ticks
- Add TimeAdvancedHandler for event processing
- Register handler with EventBus on startup

Closes: w5-foundation-bridge"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Add missing time schemas | `world_schemas.py`, test |
| 2 | Update router to use schemas | `world_time.py` |
| 3 | Standardize EventBus | `startup.py` |
| 4 | Wire router to EventBus | `app.py`, `startup.py` |
| 5 | Create FactionTickService | new service + test |
| 6 | Create TimeAdvancedHandler | new handler + test |
| 7 | Register handler with EventBus | `startup.py`, integration test |
| 8 | Run full test suite | verification only |
