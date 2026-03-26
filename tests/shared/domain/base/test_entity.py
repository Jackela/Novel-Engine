"""Tests for the Entity base class.

This module contains comprehensive tests for the Entity class,
ensuring proper identity-based equality, domain event handling,
and abstract method enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import override
from uuid import UUID, uuid4

import pytest

from src.shared.domain.base.entity import Entity
from src.shared.domain.base.event import DomainEvent


@dataclass(eq=False)
class MockEntity(Entity[UUID]):
    """Concrete entity implementation for testing."""

    name: str = ""
    age: int = 0

    @override
    def validate(self) -> None:
        """Validate the entity."""
        if self.age < 0:
            raise ValueError("Age cannot be negative")


@dataclass(frozen=True)
class MockEvent(DomainEvent):
    """Mock domain event for testing."""

    event_type: str = "mock.event"


class TestEntity:
    """Test cases for Entity base class."""

    def test_entity_creation_with_default_id(self) -> None:
        """Test that entity can be created with auto-generated UUID."""
        entity = MockEntity(name="John", age=25)

        assert isinstance(entity.id, UUID)
        assert entity.name == "John"
        assert entity.age == 25
        assert isinstance(entity.created_at, datetime)
        assert isinstance(entity.updated_at, datetime)

    def test_entity_creation_with_custom_id(self) -> None:
        """Test that entity can be created with custom UUID."""
        custom_id = uuid4()
        entity = MockEntity(id=custom_id, name="Jane", age=30)

        assert entity.id == custom_id

    def test_entity_equality_based_on_id(self) -> None:
        """Test that entities are equal only if they have the same ID."""
        entity_id = uuid4()
        entity1 = MockEntity(id=entity_id, name="John", age=25)
        entity2 = MockEntity(id=entity_id, name="Jane", age=30)
        entity3 = MockEntity(name="John", age=25)  # Different ID

        assert entity1 == entity2  # Same ID
        assert entity1 != entity3  # Different ID
        assert entity1 != "not an entity"
        assert entity1 is not None

    def test_entity_hash_based_on_id(self) -> None:
        """Test that entity hash is based on ID and type."""
        entity_id = uuid4()
        entity1 = MockEntity(id=entity_id, name="John", age=25)
        entity2 = MockEntity(id=entity_id, name="Jane", age=30)

        assert hash(entity1) == hash(entity2)

    def test_entity_events_list_initialized(self) -> None:
        """Test that domain events list is initialized."""
        entity = MockEntity()

        assert entity.get_events() == []

    def test_add_event(self) -> None:
        """Test adding domain events to entity."""
        entity = MockEntity()
        event = MockEvent(aggregate_id=str(entity.id))

        entity.add_event(event)

        assert len(entity.get_events()) == 1
        assert entity.get_events()[0] == event

    def test_clear_events(self) -> None:
        """Test clearing all domain events."""
        entity = MockEntity()
        event = MockEvent(aggregate_id=str(entity.id))
        entity.add_event(event)

        entity.clear_events()

        assert entity.get_events() == []

    def test_get_events_returns_copy(self) -> None:
        """Test that get_events returns a copy, not the original list."""
        entity = MockEntity()
        event = MockEvent(aggregate_id=str(entity.id))
        entity.add_event(event)

        events = entity.get_events()
        events.clear()

        assert len(entity.get_events()) == 1  # Original list unchanged

    def test_validate_raises_on_invalid_state(self) -> None:
        """Test that validate raises error for invalid state."""
        with pytest.raises(ValueError, match="Age cannot be negative"):
            MockEntity(name="Invalid", age=-1)

    def test_next_id_returns_uuid(self) -> None:
        """Test that next_id class method returns a UUID."""
        new_id = MockEntity.next_id()

        assert isinstance(new_id, UUID)

    def test_post_init_ensures_events_list(self) -> None:
        """Test that __post_init__ ensures events list exists."""
        entity = object.__new__(MockEntity)
        object.__setattr__(entity, "id", uuid4())
        object.__setattr__(entity, "created_at", datetime.utcnow())
        object.__setattr__(entity, "updated_at", datetime.utcnow())
        object.__setattr__(entity, "name", "Test")
        object.__setattr__(entity, "age", 0)
        object.__setattr__(entity, "_domain_events", None)

        entity.__post_init__()

        assert entity._domain_events is not None
        assert entity._domain_events == []

    def test_equality_with_different_types(self) -> None:
        """Test that entities of different types are not equal."""

        @dataclass
        class OtherEntity(Entity[UUID]):
            value: str = ""

            @override
            def validate(self) -> None:
                pass

        entity_id = uuid4()
        entity1 = MockEntity(id=entity_id, name="Test")
        entity2 = OtherEntity(id=entity_id, value="Test")

        assert entity1 != entity2


class TestAbstractEntity:
    """Test cases for abstract Entity behavior."""

    def test_cannot_instantiate_abstract_entity(self) -> None:
        """Test that Entity cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Entity()  # type: ignore[abstract]
