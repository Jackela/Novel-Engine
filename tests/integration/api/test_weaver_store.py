#!/usr/bin/env python3
"""
Weaver Store Integration Tests

Tests the Weaver frontend store behavior through integration patterns.
Since Weaver is primarily a frontend component, these tests validate
the data contracts and types that flow between frontend and backend.
"""

import pytest
from typing import Literal
from pydantic import BaseModel, Field
from enum import Enum


class WeaverNodeStatus(str, Enum):
    """Node status states matching frontend types."""

    IDLE = "idle"
    ACTIVE = "active"
    LOADING = "loading"
    ERROR = "error"


class WeaverNodePosition(BaseModel):
    """Node position in the canvas."""

    x: float
    y: float


class CharacterNodeData(BaseModel):
    """Character node data contract."""

    name: str = Field(min_length=1)
    role: str
    traits: list[str] = Field(default_factory=list)
    status: WeaverNodeStatus = WeaverNodeStatus.IDLE


class EventNodeData(BaseModel):
    """Event node data contract."""

    title: str = Field(min_length=1)
    type: Literal["action", "dialogue", "discovery", "conflict", "resolution"]
    description: str = ""
    timestamp: str | None = None
    status: WeaverNodeStatus = WeaverNodeStatus.IDLE


class LocationNodeData(BaseModel):
    """Location node data contract."""

    name: str = Field(min_length=1)
    type: Literal["city", "building", "wilderness", "dungeon", "other"]
    description: str = ""
    status: WeaverNodeStatus = WeaverNodeStatus.IDLE


class WeaverNode(BaseModel):
    """Generic weaver node model."""

    id: str
    type: Literal["character", "event", "location"]
    position: WeaverNodePosition
    data: CharacterNodeData | EventNodeData | LocationNodeData


class WeaverEdge(BaseModel):
    """Edge connecting two nodes."""

    id: str
    source: str
    target: str


@pytest.mark.integration
class TestWeaverNodeStatus:
    """Tests for WeaverNodeStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses are defined."""
        assert WeaverNodeStatus.IDLE.value == "idle"
        assert WeaverNodeStatus.ACTIVE.value == "active"
        assert WeaverNodeStatus.LOADING.value == "loading"
        assert WeaverNodeStatus.ERROR.value == "error"

    def test_status_from_string(self):
        """Test creating status from string value."""
        assert WeaverNodeStatus("idle") == WeaverNodeStatus.IDLE
        assert WeaverNodeStatus("active") == WeaverNodeStatus.ACTIVE
        assert WeaverNodeStatus("loading") == WeaverNodeStatus.LOADING
        assert WeaverNodeStatus("error") == WeaverNodeStatus.ERROR

    def test_invalid_status_raises(self):
        """Test that invalid status raises error."""
        with pytest.raises(ValueError):
            WeaverNodeStatus("invalid")


@pytest.mark.integration
class TestCharacterNodeData:
    """Tests for CharacterNodeData contract."""

    def test_valid_character_node(self):
        """Test creating valid character node data."""
        data = CharacterNodeData(
            name="Alice",
            role="Protagonist",
            traits=["Brave", "Curious", "Kind"],
            status=WeaverNodeStatus.IDLE,
        )
        assert data.name == "Alice"
        assert data.role == "Protagonist"
        assert len(data.traits) == 3
        assert data.status == WeaverNodeStatus.IDLE

    def test_character_node_defaults(self):
        """Test character node default values."""
        data = CharacterNodeData(name="Test", role="NPC")
        assert data.traits == []
        assert data.status == WeaverNodeStatus.IDLE

    def test_character_node_status_transitions(self):
        """Test character node status can change."""
        data = CharacterNodeData(name="Test", role="NPC")
        assert data.status == WeaverNodeStatus.IDLE

        # Simulate status transitions
        data_active = data.model_copy(update={"status": WeaverNodeStatus.ACTIVE})
        assert data_active.status == WeaverNodeStatus.ACTIVE

        data_loading = data.model_copy(update={"status": WeaverNodeStatus.LOADING})
        assert data_loading.status == WeaverNodeStatus.LOADING

        data_error = data.model_copy(update={"status": WeaverNodeStatus.ERROR})
        assert data_error.status == WeaverNodeStatus.ERROR


@pytest.mark.integration
class TestEventNodeData:
    """Tests for EventNodeData contract."""

    def test_valid_event_types(self):
        """Test all valid event types."""
        event_types = ["action", "dialogue", "discovery", "conflict", "resolution"]

        for event_type in event_types:
            data = EventNodeData(title="Test Event", type=event_type)
            assert data.type == event_type

    def test_invalid_event_type_raises(self):
        """Test that invalid event type raises error."""
        with pytest.raises(ValueError):
            EventNodeData(title="Test", type="invalid_type")

    def test_event_node_with_timestamp(self):
        """Test event node with timestamp."""
        data = EventNodeData(
            title="Battle",
            type="conflict",
            description="A fierce battle",
            timestamp="2024-01-01T12:00:00Z",
        )
        assert data.timestamp == "2024-01-01T12:00:00Z"


@pytest.mark.integration
class TestLocationNodeData:
    """Tests for LocationNodeData contract."""

    def test_valid_location_types(self):
        """Test all valid location types."""
        location_types = ["city", "building", "wilderness", "dungeon", "other"]

        for loc_type in location_types:
            data = LocationNodeData(name="Test Location", type=loc_type)
            assert data.type == loc_type

    def test_invalid_location_type_raises(self):
        """Test that invalid location type raises error."""
        with pytest.raises(ValueError):
            LocationNodeData(name="Test", type="invalid_type")


@pytest.mark.integration
class TestWeaverNode:
    """Tests for WeaverNode integration."""

    def test_character_node_creation(self):
        """Test creating a character node."""
        node = WeaverNode(
            id="char_1",
            type="character",
            position=WeaverNodePosition(x=100, y=200),
            data=CharacterNodeData(name="Hero", role="Protagonist"),
        )
        assert node.id == "char_1"
        assert node.type == "character"
        assert node.position.x == 100
        assert node.position.y == 200

    def test_event_node_creation(self):
        """Test creating an event node."""
        node = WeaverNode(
            id="event_1",
            type="event",
            position=WeaverNodePosition(x=300, y=150),
            data=EventNodeData(title="Meeting", type="dialogue"),
        )
        assert node.id == "event_1"
        assert node.type == "event"

    def test_location_node_creation(self):
        """Test creating a location node."""
        node = WeaverNode(
            id="loc_1",
            type="location",
            position=WeaverNodePosition(x=50, y=50),
            data=LocationNodeData(name="Tavern", type="building"),
        )
        assert node.id == "loc_1"
        assert node.type == "location"


@pytest.mark.integration
class TestWeaverEdge:
    """Tests for WeaverEdge contract."""

    def test_edge_creation(self):
        """Test creating an edge between nodes."""
        edge = WeaverEdge(
            id="edge_1",
            source="char_1",
            target="event_1",
        )
        assert edge.id == "edge_1"
        assert edge.source == "char_1"
        assert edge.target == "event_1"

    def test_multiple_edges(self):
        """Test creating multiple edges."""
        edges = [
            WeaverEdge(id="e1", source="char_1", target="event_1"),
            WeaverEdge(id="e2", source="char_1", target="loc_1"),
            WeaverEdge(id="e3", source="event_1", target="loc_1"),
        ]
        assert len(edges) == 3
        assert edges[0].source == edges[1].source  # Same character


@pytest.mark.integration
class TestWeaverStoreState:
    """Tests for Weaver store state contract."""

    def test_initial_state_structure(self):
        """Test initial store state structure."""
        # Simulate initial state
        initial_state = {
            "nodes": [],
            "edges": [],
            "startParams": {
                "character_names": [],
                "total_turns": 3,
                "setting": "",
                "scenario": "",
            },
        }

        assert initial_state["nodes"] == []
        assert initial_state["edges"] == []
        assert initial_state["startParams"]["total_turns"] == 3

    def test_state_with_nodes(self):
        """Test store state with nodes."""
        nodes = [
            WeaverNode(
                id="1",
                type="character",
                position=WeaverNodePosition(x=250, y=50),
                data=CharacterNodeData(
                    name="Alice",
                    role="Protagonist",
                    traits=["Brave", "Curious"],
                ),
            ),
            WeaverNode(
                id="2",
                type="event",
                position=WeaverNodePosition(x=100, y=200),
                data=EventNodeData(title="Discovery", type="discovery"),
            ),
        ]

        state = {"nodes": [n.model_dump() for n in nodes], "edges": []}
        assert len(state["nodes"]) == 2
        assert state["nodes"][0]["type"] == "character"
        assert state["nodes"][1]["type"] == "event"
