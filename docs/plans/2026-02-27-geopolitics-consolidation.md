# Geopolitics Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate scattered geopolitics code into a unified, well-architected module with proper domain events, a dedicated service layer, and consistent API endpoints.

**Architecture:** Deep refactoring following Hexagonal Architecture. Create domain events for geopolitics actions, unify the DiplomacyMatrix and territory control under a GeopoliticsService, and consolidate duplicate API endpoints into a single `/geopolitics` router.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, dataclasses, structlog

---

## Overview

### Current Problems
1. **Duplicate diplomacy endpoints**: `world_state.py` and `diplomacy.py` both serve `/world/{id}/diplomacy`
2. **Inconsistent storage**: `world_store` dict vs `_diplomacy_matrices` dict
3. **Missing service layer**: No `GeopoliticsService`, logic scattered in routers
4. **Router not registered**: `world_state.py` not in `app.py`
5. **No domain events**: Diplomacy/territory changes don't emit events

### Target Architecture
```
API Layer:     geopolitics.py (NEW - unified router)
                    ↓
Service Layer: GeopoliticsService (NEW)
                    ↓
Domain Layer:  DiplomacyMatrix + GeopoliticsEvents (NEW)
                    ↓
Ports:         DiplomacyRepository, TerritoryRepository (NEW interfaces)
```

---

## Task 1: Create Geopolitics Domain Events

**Files:**
- Create: `src/contexts/world/domain/events/geopolitics_events.py`
- Test: `tests/unit/contexts/world/domain/events/test_geopolitics_events.py`

**Step 1: Write the failing test**

```python
# tests/unit/contexts/world/domain/events/test_geopolitics_events.py
"""Unit tests for geopolitics domain events."""

import pytest

from src.contexts.world.domain.events.geopolitics_events import (
    AllianceFormedEvent,
    PactType,
    TerritoryChangedEvent,
    WarDeclaredEvent,
)


class TestWarDeclaredEvent:
    """Tests for WarDeclaredEvent."""

    def test_create_war_declared_event(self) -> None:
        """Test creating a war declared event."""
        event = WarDeclaredEvent.create(
            aggressor_id="faction_a",
            defender_id="faction_b",
            reason="Territorial dispute",
            world_id="world_1",
        )

        assert event.aggressor_id == "faction_a"
        assert event.defender_id == "faction_b"
        assert event.reason == "Territorial dispute"
        assert event.event_type == "geopolitics.war_declared"
        assert "world:world_1" in event.tags

    def test_war_event_has_high_priority(self) -> None:
        """War events should have high priority."""
        from src.events.event_bus import EventPriority

        event = WarDeclaredEvent.create(
            aggressor_id="f1", defender_id="f2", reason="test"
        )
        assert event.priority == EventPriority.HIGH


class TestAllianceFormedEvent:
    """Tests for AllianceFormedEvent."""

    def test_create_alliance_event(self) -> None:
        """Test creating an alliance formed event."""
        event = AllianceFormedEvent.create(
            faction_a_id="faction_a",
            faction_b_id="faction_b",
            pact_type=PactType.DEFENSIVE_ALLIANCE,
            world_id="world_1",
        )

        assert event.faction_a_id == "faction_a"
        assert event.faction_b_id == "faction_b"
        assert event.pact_type == PactType.DEFENSIVE_ALLIANCE
        assert event.event_type == "geopolitics.alliance_formed"


class TestTerritoryChangedEvent:
    """Tests for TerritoryChangedEvent."""

    def test_create_territory_changed_event(self) -> None:
        """Test creating a territory changed event."""
        event = TerritoryChangedEvent.create(
            location_id="loc_1",
            previous_controller_id="faction_a",
            new_controller_id="faction_b",
            world_id="world_1",
            reason="Military conquest",
        )

        assert event.location_id == "loc_1"
        assert event.previous_controller_id == "faction_a"
        assert event.new_controller_id == "faction_b"
        assert event.reason == "Military conquest"
        assert event.event_type == "geopolitics.territory_changed"

    def test_territory_event_with_none_previous_controller(self) -> None:
        """Territory can be claimed from uncontrolled state."""
        event = TerritoryChangedEvent.create(
            location_id="loc_1",
            previous_controller_id=None,
            new_controller_id="faction_a",
            world_id="world_1",
        )

        assert event.previous_controller_id is None
        assert event.new_controller_id == "faction_a"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/contexts/world/domain/events/test_geopolitics_events.py -v`
Expected: FAIL with module import error

**Step 3: Write minimal implementation**

```python
# src/contexts/world/domain/events/geopolitics_events.py
#!/usr/bin/env python3
"""
Geopolitics Domain Events

Domain events for geopolitical actions including war declarations,
alliance formations, and territory transfers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog

from src.events.event_bus import Event, EventPriority

logger = structlog.get_logger()


class PactType(Enum):
    """Types of diplomatic pacts."""
    DEFENSIVE_ALLIANCE = "defensive_alliance"
    OFFENSIVE_ALLIANCE = "offensive_alliance"
    NON_AGGRESSION = "non_aggression"
    TRADE_AGREEMENT = "trade_agreement"
    RESEARCH_AGREEMENT = "research_agreement"


@dataclass
class WarDeclaredEvent(Event):
    """Domain event emitted when war is declared between factions."""

    event_type: str = field(default="geopolitics.war_declared", init=False)
    source: str = field(default="geopolitics_service", init=False)
    priority: EventPriority = field(default=EventPriority.HIGH, init=False)

    aggressor_id: str = ""
    defender_id: str = ""
    reason: str = ""
    world_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())
        if not self.event_id:
            object.__setattr__(self, 'event_id', str(uuid4()))

        self.tags.update({
            "context:world",
            "event:war_declared",
            f"aggressor:{self.aggressor_id}",
            f"defender:{self.defender_id}",
        })
        if self.world_id:
            self.tags.add(f"world:{self.world_id}")

        self.payload.update({
            "aggressor_id": self.aggressor_id,
            "defender_id": self.defender_id,
            "reason": self.reason,
            "world_id": self.world_id,
        })
        super().__post_init__()

    @classmethod
    def create(
        cls,
        aggressor_id: str,
        defender_id: str,
        reason: str,
        world_id: Optional[str] = None,
    ) -> "WarDeclaredEvent":
        return cls(
            aggressor_id=aggressor_id,
            defender_id=defender_id,
            reason=reason,
            world_id=world_id,
        )


@dataclass
class AllianceFormedEvent(Event):
    """Domain event emitted when an alliance is formed."""

    event_type: str = field(default="geopolitics.alliance_formed", init=False)
    source: str = field(default="geopolitics_service", init=False)
    priority: EventPriority = field(default=EventPriority.NORMAL, init=False)

    faction_a_id: str = ""
    faction_b_id: str = ""
    pact_type: PactType = PactType.DEFENSIVE_ALLIANCE
    world_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())
        if not self.event_id:
            object.__setattr__(self, 'event_id', str(uuid4()))

        self.tags.update({
            "context:world",
            "event:alliance_formed",
            f"faction_a:{self.faction_a_id}",
            f"faction_b:{self.faction_b_id}",
        })
        if self.world_id:
            self.tags.add(f"world:{self.world_id}")

        self.payload.update({
            "faction_a_id": self.faction_a_id,
            "faction_b_id": self.faction_b_id,
            "pact_type": self.pact_type.value,
            "world_id": self.world_id,
        })
        super().__post_init__()

    @classmethod
    def create(
        cls,
        faction_a_id: str,
        faction_b_id: str,
        pact_type: PactType,
        world_id: Optional[str] = None,
    ) -> "AllianceFormedEvent":
        return cls(
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            pact_type=pact_type,
            world_id=world_id,
        )


@dataclass
class TerritoryChangedEvent(Event):
    """Domain event emitted when territory control changes."""

    event_type: str = field(default="geopolitics.territory_changed", init=False)
    source: str = field(default="geopolitics_service", init=False)
    priority: EventPriority = field(default=EventPriority.NORMAL, init=False)

    location_id: str = ""
    previous_controller_id: Optional[str] = None
    new_controller_id: Optional[str] = None
    reason: str = ""
    world_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())
        if not self.event_id:
            object.__setattr__(self, 'event_id', str(uuid4()))

        self.tags.update({
            "context:world",
            "event:territory_changed",
            f"location:{self.location_id}",
        })
        if self.world_id:
            self.tags.add(f"world:{self.world_id}")

        self.payload.update({
            "location_id": self.location_id,
            "previous_controller_id": self.previous_controller_id,
            "new_controller_id": self.new_controller_id,
            "reason": self.reason,
            "world_id": self.world_id,
        })
        super().__post_init__()

    @classmethod
    def create(
        cls,
        location_id: str,
        previous_controller_id: Optional[str],
        new_controller_id: Optional[str],
        world_id: Optional[str] = None,
        reason: str = "",
    ) -> "TerritoryChangedEvent":
        return cls(
            location_id=location_id,
            previous_controller_id=previous_controller_id,
            new_controller_id=new_controller_id,
            world_id=world_id,
            reason=reason,
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/contexts/world/domain/events/test_geopolitics_events.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/contexts/world/domain/events/geopolitics_events.py tests/unit/contexts/world/domain/events/test_geopolitics_events.py
git commit -m "feat(geopolitics): add domain events for war, alliance, and territory changes"
```

---

## Task 2: Create Geopolitics Service

**Files:**
- Create: `src/contexts/world/application/services/geopolitics_service.py`
- Test: `tests/unit/contexts/world/application/test_geopolitics_service.py`

**Step 1: Write the failing test**

```python
# tests/unit/contexts/world/application/test_geopolitics_service.py
"""Unit tests for GeopoliticsService."""

import pytest
from unittest.mock import MagicMock, patch

from src.contexts.world.application.services.geopolitics_service import GeopoliticsService
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus


class TestGeopoliticsService:
    """Tests for GeopoliticsService."""

    @pytest.fixture
    def service(self) -> GeopoliticsService:
        """Create a GeopoliticsService instance."""
        return GeopoliticsService()

    @pytest.fixture
    def diplomacy_matrix(self) -> DiplomacyMatrix:
        """Create a sample diplomacy matrix."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")
        return matrix

    def test_declare_war_success(self, service: GeopoliticsService) -> None:
        """Test declaring war between factions."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")

        result = service.declare_war(
            matrix=matrix,
            aggressor_id="faction_a",
            defender_id="faction_b",
            reason="Territorial dispute",
        )

        assert result.is_ok
        status = matrix.get_status("faction_a", "faction_b")
        assert status == DiplomaticStatus.AT_WAR

    def test_declare_war_emits_event(self, service: GeopoliticsService) -> None:
        """Test that declaring war emits a WarDeclaredEvent."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")

        with patch.object(service, '_emit_event') as mock_emit:
            service.declare_war(
                matrix=matrix,
                aggressor_id="faction_a",
                defender_id="faction_b",
                reason="Test war",
            )
            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "geopolitics.war_declared"

    def test_form_alliance_success(self, service: GeopoliticsService) -> None:
        """Test forming an alliance between factions."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")

        result = service.form_alliance(
            matrix=matrix,
            faction_a_id="faction_a",
            faction_b_id="faction_b",
        )

        assert result.is_ok
        status = matrix.get_status("faction_a", "faction_b")
        assert status == DiplomaticStatus.ALLIED

    def test_cannot_ally_while_at_war(self, service: GeopoliticsService) -> None:
        """Test that factions at war cannot form alliance directly."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")
        matrix.set_status("faction_a", "faction_b", DiplomaticStatus.AT_WAR)

        result = service.form_alliance(
            matrix=matrix,
            faction_a_id="faction_a",
            faction_b_id="faction_b",
        )

        assert result.is_error
        assert "at war" in str(result.error).lower()

    def test_transfer_territory(self, service: GeopoliticsService) -> None:
        """Test transferring territory between factions."""
        from src.contexts.world.domain.entities.location import Location

        location = Location(
            id="loc_1",
            name="Test Territory",
            description="A test territory",
            location_type="province",
            controlling_faction_id="faction_a",
        )

        result = service.transfer_territory(
            location=location,
            new_controller_id="faction_b",
            reason="Military conquest",
        )

        assert result.is_ok
        assert location.controlling_faction_id == "faction_b"

    def test_transfer_territory_emits_event(self, service: GeopoliticsService) -> None:
        """Test that territory transfer emits TerritoryChangedEvent."""
        from src.contexts.world.domain.entities.location import Location

        location = Location(
            id="loc_1",
            name="Test Territory",
            description="A test territory",
            location_type="province",
            controlling_faction_id="faction_a",
        )

        with patch.object(service, '_emit_event') as mock_emit:
            service.transfer_territory(
                location=location,
                new_controller_id="faction_b",
                reason="Test transfer",
            )
            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "geopolitics.territory_changed"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/contexts/world/application/test_geopolitics_service.py -v`
Expected: FAIL with module import error

**Step 3: Write minimal implementation**

```python
# src/contexts/world/application/services/geopolitics_service.py
#!/usr/bin/env python3
"""
Geopolitics Service

Application service for managing geopolitical actions including
diplomatic relations, territory control, and resource tracking.
"""

from typing import List, Optional

import structlog

from src.core.result import Err, Ok, Result
from src.events.event_bus import EventBus

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.entities.location import Location
from src.contexts.world.domain.events.geopolitics_events import (
    AllianceFormedEvent,
    PactType,
    TerritoryChangedEvent,
    WarDeclaredEvent,
)
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus

logger = structlog.get_logger()


class GeopoliticsService:
    """
    Application service for geopolitical operations.

    Provides a unified interface for:
    - Declaring wars and forming alliances
    - Transferring territory control
    - Querying geopolitical state

    All operations emit appropriate domain events.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize the geopolitics service."""
        self._event_bus = event_bus or EventBus.get_instance()

    def _emit_event(self, event) -> None:
        """Emit a domain event."""
        self._event_bus.publish(event)
        logger.info(
            "geopolitics_event_emitted",
            event_type=event.event_type,
            event_id=event.event_id,
        )

    def declare_war(
        self,
        matrix: DiplomacyMatrix,
        aggressor_id: str,
        defender_id: str,
        reason: str,
        world_id: Optional[str] = None,
    ) -> Result[None, ValueError]:
        """
        Declare war between two factions.

        Args:
            matrix: The diplomacy matrix to modify
            aggressor_id: ID of the faction declaring war
            defender_id: ID of the faction being attacked
            reason: Reason for the war declaration
            world_id: Optional world ID for event context

        Returns:
            Ok(None) on success, Err(ValueError) on failure
        """
        # Set diplomatic status to AT_WAR
        result = matrix.set_status(aggressor_id, defender_id, DiplomaticStatus.AT_WAR)
        if result.is_error:
            return result

        # Emit war declared event
        event = WarDeclaredEvent.create(
            aggressor_id=aggressor_id,
            defender_id=defender_id,
            reason=reason,
            world_id=world_id or matrix.world_id,
        )
        self._emit_event(event)

        logger.info(
            "war_declared",
            aggressor=aggressor_id,
            defender=defender_id,
            reason=reason,
        )

        return Ok(None)

    def form_alliance(
        self,
        matrix: DiplomacyMatrix,
        faction_a_id: str,
        faction_b_id: str,
        pact_type: PactType = PactType.DEFENSIVE_ALLIANCE,
        world_id: Optional[str] = None,
    ) -> Result[None, ValueError]:
        """
        Form an alliance between two factions.

        Args:
            matrix: The diplomacy matrix to modify
            faction_a_id: ID of the first faction
            faction_b_id: ID of the second faction
            pact_type: Type of alliance (default: defensive)
            world_id: Optional world ID for event context

        Returns:
            Ok(None) on success, Err(ValueError) on failure
        """
        # Check if factions are at war
        current_status = matrix.get_status(faction_a_id, faction_b_id)
        if current_status == DiplomaticStatus.AT_WAR:
            return Err(
                ValueError(
                    f"Cannot form alliance: factions {faction_a_id} and {faction_b_id} are at war"
                )
            )

        # Set diplomatic status to ALLIED
        result = matrix.set_status(faction_a_id, faction_b_id, DiplomaticStatus.ALLIED)
        if result.is_error:
            return result

        # Emit alliance formed event
        event = AllianceFormedEvent.create(
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            pact_type=pact_type,
            world_id=world_id or matrix.world_id,
        )
        self._emit_event(event)

        logger.info(
            "alliance_formed",
            faction_a=faction_a_id,
            faction_b=faction_b_id,
            pact_type=pact_type.value,
        )

        return Ok(None)

    def transfer_territory(
        self,
        location: Location,
        new_controller_id: Optional[str],
        reason: str = "",
        world_id: Optional[str] = None,
    ) -> Result[None, ValueError]:
        """
        Transfer territory control to a new faction.

        Args:
            location: The location to transfer
            new_controller_id: ID of the new controlling faction (None for uncontrolled)
            reason: Reason for the transfer
            world_id: Optional world ID for event context

        Returns:
            Ok(None) on success, Err(ValueError) on failure
        """
        previous_controller_id = location.controlling_faction_id

        # Use the location's transfer_control method if available
        if hasattr(location, 'transfer_control'):
            location.transfer_control(new_controller_id)
        else:
            location.controlling_faction_id = new_controller_id
            location.touch()

        # Emit territory changed event
        event = TerritoryChangedEvent.create(
            location_id=location.id,
            previous_controller_id=previous_controller_id,
            new_controller_id=new_controller_id,
            world_id=world_id,
            reason=reason,
        )
        self._emit_event(event)

        logger.info(
            "territory_transferred",
            location_id=location.id,
            previous_controller=previous_controller_id,
            new_controller=new_controller_id,
            reason=reason,
        )

        return Ok(None)

    def get_diplomacy_summary(
        self,
        matrix: DiplomacyMatrix,
        faction_id: str,
    ) -> dict:
        """
        Get a summary of diplomatic relations for a faction.

        Args:
            matrix: The diplomacy matrix to query
            faction_id: ID of the faction to summarize

        Returns:
            Dictionary with allies, enemies, and neutral factions
        """
        return {
            "faction_id": faction_id,
            "allies": matrix.get_allies(faction_id),
            "enemies": matrix.get_enemies(faction_id),
            "neutral": matrix.get_neutral(faction_id),
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/contexts/world/application/test_geopolitics_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/contexts/world/application/services/geopolitics_service.py tests/unit/contexts/world/application/test_geopolitics_service.py
git commit -m "feat(geopolitics): add GeopoliticsService with war/alliance/territory operations"
```

---

## Task 3: Create Unified Geopolitics Router

**Files:**
- Create: `src/api/routers/geopolitics.py`
- Modify: `src/api/app.py` (add router registration)
- Test: `tests/integration/api/test_geopolitics_api.py`

**Step 1: Write the failing test**

```python
# tests/integration/api/test_geopolitics_api.py
"""Integration tests for Geopolitics API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    app = create_app()
    return TestClient(app)


class TestGeopoliticsEndpoints:
    """Tests for geopolitics API endpoints."""

    def test_get_diplomacy_matrix(self, client: TestClient) -> None:
        """Test GET /api/geopolitics/world/{world_id}/diplomacy."""
        response = client.get("/api/geopolitics/world/test-world/diplomacy")

        assert response.status_code == 200
        data = response.json()
        assert "matrix" in data
        assert "factions" in data

    def test_get_territories(self, client: TestClient) -> None:
        """Test GET /api/geopolitics/world/{world_id}/territories."""
        response = client.get("/api/geopolitics/world/test-world/territories")

        assert response.status_code in [200, 404]  # 404 if world doesn't exist

    def test_get_resources(self, client: TestClient) -> None:
        """Test GET /api/geopolitics/world/{world_id}/resources."""
        response = client.get("/api/geopolitics/world/test-world/resources")

        assert response.status_code in [200, 404]

    def test_declare_war_endpoint_exists(self, client: TestClient) -> None:
        """Test POST /api/geopolitics/world/{world_id}/war exists."""
        response = client.post(
            "/api/geopolitics/world/test-world/war",
            json={
                "aggressor_id": "faction_a",
                "defender_id": "faction_b",
                "reason": "Test war",
            },
        )

        # Should not return 404 (method might exist even if world doesn't)
        assert response.status_code != 404

    def test_form_alliance_endpoint_exists(self, client: TestClient) -> None:
        """Test POST /api/geopolitics/world/{world_id}/alliance exists."""
        response = client.post(
            "/api/geopolitics/world/test-world/alliance",
            json={
                "faction_a_id": "faction_a",
                "faction_b_id": "faction_b",
            },
        )

        assert response.status_code != 404

    def test_transfer_territory_endpoint_exists(self, client: TestClient) -> None:
        """Test POST /api/geopolitics/world/{world_id}/territory/transfer exists."""
        response = client.post(
            "/api/geopolitics/world/test-world/territory/transfer",
            json={
                "location_id": "loc_1",
                "new_controller_id": "faction_b",
                "reason": "Military conquest",
            },
        )

        assert response.status_code != 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/api/test_geopolitics_api.py -v`
Expected: FAIL with 404 errors

**Step 3: Write minimal implementation**

```python
# src/api/routers/geopolitics.py
"""
Geopolitics API Router

Unified API endpoints for geopolitical operations including
diplomacy, territory control, and resources.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas.world_schemas import (
    DiplomacyMatrixDetailResponse,
    FactionResourceSummary,
    PactSummary,
    TerritoriesResponse,
    TerritorySummary,
    WorldResourcesResponse,
)
from src.core.result import Err, Ok
from src.contexts.world.application.services.geopolitics_service import GeopoliticsService
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geopolitics", tags=["geopolitics"])


# === Request Schemas ===

from pydantic import BaseModel


class DeclareWarRequest(BaseModel):
    """Request body for declaring war."""
    aggressor_id: str
    defender_id: str
    reason: str


class FormAllianceRequest(BaseModel):
    """Request body for forming alliance."""
    faction_a_id: str
    faction_b_id: str
    pact_type: str = "defensive_alliance"


class TransferTerritoryRequest(BaseModel):
    """Request body for transferring territory."""
    location_id: str
    new_controller_id: Optional[str]
    reason: str = ""


# === Storage Helpers ===

def _get_world_store(request: Request) -> Dict[str, Dict[str, Any]]:
    """Get the world store from app state."""
    store = getattr(request.app.state, "world_store", None)
    if store is None:
        store = {}
        request.app.state.world_store = store
    return store


def _get_or_create_diplomacy_matrix(
    world_store: Dict[str, Dict[str, Any]],
    world_id: str,
) -> DiplomacyMatrix:
    """Get or create a diplomacy matrix for a world."""
    world_data = world_store.get(world_id, {})

    if "diplomacy_matrix" in world_data:
        matrix_data = world_data["diplomacy_matrix"]
        return DiplomacyMatrix.from_dict(matrix_data)

    matrix = DiplomacyMatrix(world_id=world_id)

    # Register factions from world data
    factions = world_data.get("factions", [])
    for faction in factions:
        if isinstance(faction, dict) and "id" in faction:
            matrix.register_faction(faction["id"])

    return matrix


def _save_diplomacy_matrix(
    world_store: Dict[str, Dict[str, Any]],
    world_id: str,
    matrix: DiplomacyMatrix,
) -> None:
    """Save diplomacy matrix back to world store."""
    if world_id not in world_store:
        world_store[world_id] = {}

    world_store[world_id]["diplomacy_matrix"] = matrix.to_dict()


# === Service Instance ===

def _get_geopolitics_service() -> GeopoliticsService:
    """Get a GeopoliticsService instance."""
    return GeopoliticsService()


# === Endpoints ===

@router.get(
    "/world/{world_id}/diplomacy",
    response_model=DiplomacyMatrixDetailResponse,
    summary="Get diplomacy matrix",
)
async def get_diplomacy(
    world_id: str,
    request: Request,
) -> DiplomacyMatrixDetailResponse:
    """Get the full diplomacy matrix with active pacts."""
    world_store = _get_world_store(request)
    matrix = _get_or_create_diplomacy_matrix(world_store, world_id)

    # Build active pacts list
    active_pacts = [
        PactSummary(
            pact_id=pact.id,
            faction_a_id=pact.faction_a_id,
            faction_b_id=pact.faction_b_id,
            pact_type=pact.pact_type.value if hasattr(pact.pact_type, 'value') else str(pact.pact_type),
            signed_date=str(pact.signed_date) if hasattr(pact, 'signed_date') else None,
            expires_date=str(pact.expires_date) if hasattr(pact, 'expires_date') else None,
            is_active=pact.is_active() if hasattr(pact, 'is_active') else True,
        )
        for pact in matrix.active_pacts
    ]

    return DiplomacyMatrixDetailResponse(
        world_id=world_id,
        matrix=matrix.to_matrix(),
        factions=sorted(list(matrix.faction_ids)),
        active_pacts=active_pacts,
    )


@router.get(
    "/world/{world_id}/territories",
    response_model=TerritoriesResponse,
    summary="Get world territories",
)
async def get_territories(
    world_id: str,
    request: Request,
) -> TerritoriesResponse:
    """Get territories with control information."""
    world_store = _get_world_store(request)
    world_data = world_store.get(world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    locations = world_data.get("locations", [])
    territories = []
    controlled_count = 0
    contested_count = 0

    for loc in locations:
        if not isinstance(loc, dict):
            continue

        controlling_faction = loc.get("controlling_faction_id")
        contested_by = loc.get("contested_by", [])
        resource_yields = loc.get("resource_yields", [])

        territory = TerritorySummary(
            location_id=loc.get("id", ""),
            name=loc.get("name", "Unknown"),
            location_type=loc.get("location_type", "unknown"),
            controlling_faction_id=controlling_faction,
            contested_by=contested_by if isinstance(contested_by, list) else [],
            territory_value=loc.get("territory_value", 0),
            infrastructure_level=loc.get("infrastructure_level", 0),
            population=loc.get("population", 0),
            resource_types=[
                ry.get("resource_type", "")
                for ry in resource_yields
                if isinstance(ry, dict) and ry.get("resource_type")
            ],
        )
        territories.append(territory)

        if controlling_faction:
            controlled_count += 1
        if contested_by and len(contested_by) > 0:
            contested_count += 1

    return TerritoriesResponse(
        world_id=world_id,
        territories=territories,
        total_count=len(territories),
        controlled_count=controlled_count,
        contested_count=contested_count,
    )


@router.get(
    "/world/{world_id}/resources",
    response_model=WorldResourcesResponse,
    summary="Get world resources",
)
async def get_resources(
    world_id: str,
    request: Request,
) -> WorldResourcesResponse:
    """Get faction resource summary."""
    world_store = _get_world_store(request)
    world_data = world_store.get(world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    factions_data = world_data.get("factions", [])
    locations = world_data.get("locations", [])

    faction_summaries = []
    total_resources: Dict[str, int] = {}

    for faction in factions_data:
        if not isinstance(faction, dict):
            continue

        faction_id = faction.get("id", "")
        faction_name = faction.get("name", "Unknown")

        controlled_locations = [
            loc for loc in locations
            if isinstance(loc, dict) and loc.get("controlling_faction_id") == faction_id
        ]

        resources: Dict[str, int] = {}
        total_population = 0

        for loc in controlled_locations:
            total_population += loc.get("population", 0)
            for ry in loc.get("resource_yields", []):
                if isinstance(ry, dict):
                    resource_type = ry.get("resource_type", "")
                    if resource_type:
                        amount = ry.get("current_stock", 0)
                        resources[resource_type] = resources.get(resource_type, 0) + amount

        faction_resources = faction.get("resources", {})
        if isinstance(faction_resources, dict):
            for res_type, amount in faction_resources.items():
                resources[res_type] = resources.get(res_type, 0) + amount

        for res_type, amount in resources.items():
            total_resources[res_type] = total_resources.get(res_type, 0) + amount

        faction_summaries.append(
            FactionResourceSummary(
                faction_id=faction_id,
                faction_name=faction_name,
                resources=resources,
                total_territories=len(controlled_locations),
                total_population=total_population,
            )
        )

    return WorldResourcesResponse(
        world_id=world_id,
        factions=faction_summaries,
        total_resources=total_resources,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.post(
    "/world/{world_id}/war",
    summary="Declare war",
)
async def declare_war(
    world_id: str,
    request_body: DeclareWarRequest,
    request: Request,
) -> Dict[str, Any]:
    """Declare war between two factions."""
    world_store = _get_world_store(request)
    matrix = _get_or_create_diplomacy_matrix(world_store, world_id)
    service = _get_geopolitics_service()

    result = service.declare_war(
        matrix=matrix,
        aggressor_id=request_body.aggressor_id,
        defender_id=request_body.defender_id,
        reason=request_body.reason,
        world_id=world_id,
    )

    if result.is_error:
        raise HTTPException(
            status_code=400,
            detail=str(result.error),
        )

    _save_diplomacy_matrix(world_store, world_id, matrix)

    return {
        "status": "war_declared",
        "aggressor_id": request_body.aggressor_id,
        "defender_id": request_body.defender_id,
    }


@router.post(
    "/world/{world_id}/alliance",
    summary="Form alliance",
)
async def form_alliance(
    world_id: str,
    request_body: FormAllianceRequest,
    request: Request,
) -> Dict[str, Any]:
    """Form an alliance between two factions."""
    from src.contexts.world.domain.events.geopolitics_events import PactType

    world_store = _get_world_store(request)
    matrix = _get_or_create_diplomacy_matrix(world_store, world_id)
    service = _get_geopolitics_service()

    pact_type = PactType.DEFENSIVE_ALLIANCE
    try:
        pact_type = PactType(request_body.pact_type)
    except ValueError:
        pass

    result = service.form_alliance(
        matrix=matrix,
        faction_a_id=request_body.faction_a_id,
        faction_b_id=request_body.faction_b_id,
        pact_type=pact_type,
        world_id=world_id,
    )

    if result.is_error:
        raise HTTPException(
            status_code=400,
            detail=str(result.error),
        )

    _save_diplomacy_matrix(world_store, world_id, matrix)

    return {
        "status": "alliance_formed",
        "faction_a_id": request_body.faction_a_id,
        "faction_b_id": request_body.faction_b_id,
    }


@router.post(
    "/world/{world_id}/territory/transfer",
    summary="Transfer territory",
)
async def transfer_territory(
    world_id: str,
    request_body: TransferTerritoryRequest,
    request: Request,
) -> Dict[str, Any]:
    """Transfer territory control to another faction."""
    world_store = _get_world_store(request)
    world_data = world_store.get(world_id)

    if world_data is None:
        raise HTTPException(status_code=404, detail=f"World {world_id} not found")

    locations = world_data.get("locations", [])
    location = None
    location_idx = None

    for idx, loc in enumerate(locations):
        if isinstance(loc, dict) and loc.get("id") == request_body.location_id:
            location = loc
            location_idx = idx
            break

    if location is None:
        raise HTTPException(
            status_code=404,
            detail=f"Location {request_body.location_id} not found",
        )

    previous_controller = location.get("controlling_faction_id")
    location["controlling_faction_id"] = request_body.new_controller_id
    locations[location_idx] = location

    # Emit event via service
    service = _get_geopolitics_service()
    from src.contexts.world.domain.events.geopolitics_events import TerritoryChangedEvent
    event = TerritoryChangedEvent.create(
        location_id=request_body.location_id,
        previous_controller_id=previous_controller,
        new_controller_id=request_body.new_controller_id,
        world_id=world_id,
        reason=request_body.reason,
    )
    service._emit_event(event)

    return {
        "status": "territory_transferred",
        "location_id": request_body.location_id,
        "previous_controller_id": previous_controller,
        "new_controller_id": request_body.new_controller_id,
    }
```

**Step 4: Update app.py to register the router**

Add to `src/api/app.py` after line 104:

```python
    from src.api.routers.geopolitics import router as geopolitics_router
```

And add after line 134:

```python
    app.include_router(geopolitics_router, prefix="/api")
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/integration/api/test_geopolitics_api.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/api/routers/geopolitics.py src/api/app.py tests/integration/api/test_geopolitics_api.py
git commit -m "feat(geopolitics): add unified geopolitics router with diplomacy/territory/resources endpoints"
```

---

## Task 4: Deprecate Old Diplomacy Router

**Files:**
- Modify: `src/api/routers/diplomacy.py` (add deprecation warning)
- Modify: `src/api/routers/world_state.py` (add deprecation warning)

**Step 1: Add deprecation notice to old routers**

Add this comment block at the top of `src/api/routers/diplomacy.py`:

```python
"""
DEPRECATED: This router is deprecated in favor of src.api.routers.geopolitics

The /world/{world_id}/diplomacy endpoint is now served by the unified
geopolitics router at /api/geopolitics/world/{world_id}/diplomacy

This file will be removed in a future version.
"""
import warnings
warnings.warn(
    "diplomacy router is deprecated. Use geopolitics router instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

**Step 2: Add deprecation notice to world_state.py**

Add similar deprecation notice to `src/api/routers/world_state.py`:

```python
"""
DEPRECATED: This router is deprecated in favor of src.api.routers.geopolitics

The /world/{world_id}/* endpoints are now served by the unified
geopolitics router at /api/geopolitics/world/{world_id}/*

This file will be removed in a future version.
"""
import warnings
warnings.warn(
    "world_state router is deprecated. Use geopolitics router instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

**Step 3: Run tests to ensure nothing broke**

Run: `pytest tests/ -v -k "diplomacy or geopolitics or world_state" --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add src/api/routers/diplomacy.py src/api/routers/world_state.py
git commit -m "deprecate(diplomacy): mark old routers as deprecated in favor of geopolitics"
```

---

## Task 5: Update Frontend API Hooks

**Files:**
- Create: `frontend/src/features/world/api/geopoliticsApi.ts`
- Modify: `frontend/src/types/schemas.ts` (add geopolitics types)

**Step 1: Add geopolitics types to schemas.ts**

Add these types to `frontend/src/types/schemas.ts`:

```typescript
// Geopolitics types

export const DeclareWarRequestSchema = z.object({
  aggressor_id: z.string(),
  defender_id: z.string(),
  reason: z.string(),
});

export const FormAllianceRequestSchema = z.object({
  faction_a_id: z.string(),
  faction_b_id: z.string(),
  pact_type: z.string().optional().default('defensive_alliance'),
});

export const TransferTerritoryRequestSchema = z.object({
  location_id: z.string(),
  new_controller_id: z.string().nullable(),
  reason: z.string().optional().default(''),
});

export const WarResponseSchema = z.object({
  status: z.literal('war_declared'),
  aggressor_id: z.string(),
  defender_id: z.string(),
});

export const AllianceResponseSchema = z.object({
  status: z.literal('alliance_formed'),
  faction_a_id: z.string(),
  faction_b_id: z.string(),
});

export const TerritoryTransferResponseSchema = z.object({
  status: z.literal('territory_transferred'),
  location_id: z.string(),
  previous_controller_id: z.string().nullable(),
  new_controller_id: z.string().nullable(),
});

export type DeclareWarRequest = z.infer<typeof DeclareWarRequestSchema>;
export type FormAllianceRequest = z.infer<typeof FormAllianceRequestSchema>;
export type TransferTerritoryRequest = z.infer<typeof TransferTerritoryRequestSchema>;
export type WarResponse = z.infer<typeof WarResponseSchema>;
export type AllianceResponse = z.infer<typeof AllianceResponseSchema>;
export type TerritoryTransferResponse = z.infer<typeof TerritoryTransferResponseSchema>;
```

**Step 2: Create geopolitics API hooks**

Create `frontend/src/features/world/api/geopoliticsApi.ts`:

```typescript
/**
 * Geopolitics API hooks
 *
 * Unified API hooks for geopolitics operations including diplomacy,
 * territory control, and resources.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import {
  DiplomacyMatrixDetailResponseSchema,
  TerritoriesResponseSchema,
  WorldResourcesResponseSchema,
  DeclareWarRequest,
  FormAllianceRequest,
  TransferTerritoryRequest,
  WarResponseSchema,
  AllianceResponseSchema,
  TerritoryTransferResponseSchema,
} from '@/types/schemas';

const API_BASE = '/api/geopolitics';

// Query keys
export const geopoliticsKeys = {
  all: ['geopolitics'] as const,
  world: (worldId: string) => [...geopoliticsKeys.all, worldId] as const,
  diplomacy: (worldId: string) => [...geopoliticsKeys.world(worldId), 'diplomacy'] as const,
  territories: (worldId: string) => [...geopoliticsKeys.world(worldId), 'territories'] as const,
  resources: (worldId: string) => [...geopoliticsKeys.world(worldId), 'resources'] as const,
};

// Error parsing helper
async function parseErrorResponse(response: Response, operation: string): Promise<Error> {
  try {
    const data = await response.json();
    const message = data?.detail || data?.message || `Failed to ${operation}`;
    return new Error(message);
  } catch {
    return new Error(`Failed to ${operation}: HTTP ${response.status}`);
  }
}

// === Query Hooks ===

export function useDiplomacy(worldId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: geopoliticsKeys.diplomacy(worldId),
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/world/${worldId}/diplomacy`);
      if (!response.ok) throw await parseErrorResponse(response, 'fetch diplomacy');
      const data = await response.json();
      return DiplomacyMatrixDetailResponseSchema.parse(data);
    },
    enabled: options?.enabled ?? true,
  });
}

export function useTerritories(worldId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: geopoliticsKeys.territories(worldId),
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/world/${worldId}/territories`);
      if (!response.ok) {
        if (response.status === 404) return null;
        throw await parseErrorResponse(response, 'fetch territories');
      }
      const data = await response.json();
      return TerritoriesResponseSchema.parse(data);
    },
    enabled: options?.enabled ?? true,
  });
}

export function useResources(worldId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: geopoliticsKeys.resources(worldId),
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/world/${worldId}/resources`);
      if (!response.ok) {
        if (response.status === 404) return null;
        throw await parseErrorResponse(response, 'fetch resources');
      }
      const data = await response.json();
      return WorldResourcesResponseSchema.parse(data);
    },
    enabled: options?.enabled ?? true,
  });
}

// === Mutation Hooks ===

export function useDeclareWar(worldId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: DeclareWarRequest) => {
      const response = await fetch(`${API_BASE}/world/${worldId}/war`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!response.ok) throw await parseErrorResponse(response, 'declare war');
      const data = await response.json();
      return WarResponseSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.diplomacy(worldId) });
    },
  });
}

export function useFormAlliance(worldId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: FormAllianceRequest) => {
      const response = await fetch(`${API_BASE}/world/${worldId}/alliance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!response.ok) throw await parseErrorResponse(response, 'form alliance');
      const data = await response.json();
      return AllianceResponseSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.diplomacy(worldId) });
    },
  });
}

export function useTransferTerritory(worldId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: TransferTerritoryRequest) => {
      const response = await fetch(`${API_BASE}/world/${worldId}/territory/transfer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!response.ok) throw await parseErrorResponse(response, 'transfer territory');
      const data = await response.json();
      return TerritoryTransferResponseSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.territories(worldId) });
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.resources(worldId) });
    },
  });
}
```

**Step 3: Run frontend type check**

Run: `cd frontend && npm run type-check`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/types/schemas.ts frontend/src/features/world/api/geopoliticsApi.ts
git commit -m "feat(frontend): add unified geopolitics API hooks with TanStack Query"
```

---

## Task 6: Run Full Test Suite and Verify

**Step 1: Run all backend tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Run frontend checks**

Run: `cd frontend && npm run type-check && npm run lint`
Expected: PASS

**Step 3: Run CI check script**

Run: `./scripts/ci-check.sh`
Expected: Exit code 0

**Step 4: Final commit with summary**

```bash
git add -A
git commit -m "feat(geopolitics): complete deep refactoring with unified service and events

- Add Geopolitics domain events (WarDeclaredEvent, AllianceFormedEvent, TerritoryChangedEvent)
- Create GeopoliticsService for unified diplomacy/territory operations
- Add unified /api/geopolitics router consolidating world_state and diplomacy
- Deprecate old diplomacy.py and world_state.py routers
- Add frontend geopoliticsApi.ts with TanStack Query hooks
- All tests passing, CI validated"
```

---

## Summary

This plan consolidates the scattered geopolitics code into a unified, well-architected module:

1. **Domain Events** - Proper event emission for war, alliance, and territory changes
2. **Service Layer** - `GeopoliticsService` provides unified interface
3. **API Layer** - Single `/api/geopolitics` router replaces duplicate endpoints
4. **Frontend** - New API hooks with proper caching and invalidation
5. **Deprecation** - Old routers marked for future removal
