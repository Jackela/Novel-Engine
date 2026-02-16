"""
Tests for KnowledgeEventSubscriber

Unit tests for the event subscriber that bridges domain events
to the knowledge sync handler.

Warzone 4: AI Brain - BRAIN-005
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from src.contexts.knowledge.application.event_handlers.knowledge_event_subscriber import (
    KnowledgeEventSubscriber,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestKnowledgeEventSubscriber:
    """Tests for KnowledgeEventSubscriber."""

    @pytest.fixture
    def mock_event_bus(self) -> Mock:
        """Create a mock event bus."""
        bus = Mock()
        bus.subscribe = Mock()
        bus.unsubscribe = Mock()
        bus.emit = Mock()
        return bus

    @pytest.fixture
    def mock_sync_handler(self) -> Mock:
        """Create a mock sync handler."""
        handler = Mock()
        handler.queue_ingestion = AsyncMock(return_value=True)
        return handler

    @pytest.fixture
    def subscriber(
        self,
        mock_event_bus: Mock,
        mock_sync_handler: Mock,
    ) -> KnowledgeEventSubscriber:
        """Create a subscriber instance for testing."""
        return KnowledgeEventSubscriber(
            event_bus=mock_event_bus,
            sync_handler=mock_sync_handler,
        )

    def test_subscriber_initialization(
        self,
        mock_event_bus: Mock,
        mock_sync_handler: Mock,
    ) -> None:
        """Test subscriber initializes correctly."""
        subscriber = KnowledgeEventSubscriber(
            event_bus=mock_event_bus,
            sync_handler=mock_sync_handler,
        )

        assert subscriber._event_bus is mock_event_bus
        assert subscriber._sync_handler is mock_sync_handler
        assert subscriber._subscribed is False

    def test_subscribe_to_all(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_event_bus: Mock,
    ) -> None:
        """Test subscribing to all events."""
        import asyncio

        async def run_test():
            await subscriber.subscribe_to_all()

            # Verify all subscriptions were made
            assert mock_event_bus.subscribe.call_count == 6

            # Check specific event types
            subscribed_events = [
                call[0][0] for call in mock_event_bus.subscribe.call_args_list
            ]
            assert "character.created" in subscribed_events
            assert "character.updated" in subscribed_events
            assert "lore.created" in subscribed_events
            assert "lore.updated" in subscribed_events
            assert "scene.created" in subscribed_events
            assert "scene.updated" in subscribed_events

            assert subscriber._subscribed is True

        asyncio.run(run_test())

    def test_subscribe_when_already_subscribed(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_event_bus: Mock,
    ) -> None:
        """Test subscribing when already subscribed doesn't duplicate."""
        import asyncio

        async def run_test():
            await subscriber.subscribe_to_all()
            first_count = mock_event_bus.subscribe.call_count

            await subscriber.subscribe_to_all()
            second_count = mock_event_bus.subscribe.call_count

            # Should not subscribe again
            assert first_count == second_count

        asyncio.run(run_test())

    def test_unsubscribe_all(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_event_bus: Mock,
    ) -> None:
        """Test unsubscribing from all events."""
        import asyncio

        async def run_test():
            # First subscribe
            await subscriber.subscribe_to_all()
            assert subscriber._subscribed is True

            # Then unsubscribe
            await subscriber.unsubscribe_all()

            # Verify all unsubscriptions were made
            assert mock_event_bus.unsubscribe.call_count == 6

            # Check specific event types
            unsubscribed_events = [
                call[0][0] for call in mock_event_bus.unsubscribe.call_args_list
            ]
            assert "character.created" in unsubscribed_events
            assert "character.updated" in unsubscribed_events
            assert "lore.created" in unsubscribed_events
            assert "lore.updated" in unsubscribed_events
            assert "scene.created" in unsubscribed_events
            assert "scene.updated" in unsubscribed_events

            assert subscriber._subscribed is False

        asyncio.run(run_test())

    def test_unsubscribe_when_not_subscribed(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_event_bus: Mock,
    ) -> None:
        """Test unsubscribing when not subscribed is safe."""
        import asyncio

        async def run_test():
            await subscriber.unsubscribe_all()

            # Should not call unsubscribe
            assert mock_event_bus.unsubscribe.call_count == 0

        asyncio.run(run_test())

    # Character event handler tests

    @pytest.mark.asyncio
    async def test_on_character_created(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test handling CharacterCreated event."""
        subscriber._on_character_created(
            character_id="char_001",
            character_name="Alice",
            description="A brave warrior",
            traits=["brave", "kind"],
            backstory="Born in a village",
        )

        # Verify queue_ingestion was called
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert call_kwargs["source_id"] == "char_001"
        assert call_kwargs["source_type"] == SourceType.CHARACTER
        assert "Alice" in call_kwargs["content"]
        assert "brave, kind" in call_kwargs["content"]
        assert "Born in a village" in call_kwargs["content"]

    @pytest.mark.asyncio
    async def test_on_character_created_missing_data(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test CharacterCreated with missing data is handled safely."""
        # Missing character_id
        subscriber._on_character_created(character_name="Alice")

        # Should not queue ingestion
        mock_sync_handler.queue_ingestion.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_character_updated(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test handling CharacterUpdated event."""
        subscriber._on_character_updated(
            character_id="char_001",
            character_name="Alice",
            description="Updated description",
            updated_fields=["description", "backstory"],
        )

        # Verify queue_ingestion was called
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert call_kwargs["source_id"] == "char_001"
        assert call_kwargs["source_type"] == SourceType.CHARACTER
        # Updated content should include "updated" tag
        assert "updated" in call_kwargs["tags"]

    # Lore event handler tests

    @pytest.mark.asyncio
    async def test_on_lore_created(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test handling LoreCreated event."""
        subscriber._on_lore_created(
            lore_id="lore_001",
            title="The Great War",
            content="War in 1234",
            category="HISTORY",
            tags=["war", "history"],
        )

        # Verify queue_ingestion was called
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert call_kwargs["source_id"] == "lore_001"
        assert call_kwargs["source_type"] == SourceType.LORE
        assert "The Great War" in call_kwargs["content"]
        assert "War in 1234" in call_kwargs["content"]

    @pytest.mark.asyncio
    async def test_on_lore_created_missing_content(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test LoreCreated without content uses summary."""
        subscriber._on_lore_created(
            lore_id="lore_001",
            title="The Great War",
            summary="A great war happened",
        )

        # Verify queue_ingestion was called
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert "A great war happened" in call_kwargs["content"]

    @pytest.mark.asyncio
    async def test_on_lore_updated(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test handling LoreUpdated event."""
        subscriber._on_lore_updated(
            lore_id="lore_001",
            title="The Great War",
            content="Updated content",
            category="HISTORY",
        )

        # Verify queue_ingestion was called with updated tag
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert call_kwargs["source_id"] == "lore_001"
        assert call_kwargs["source_type"] == SourceType.LORE
        assert "updated" in call_kwargs["tags"]

    # Scene event handler tests

    @pytest.mark.asyncio
    async def test_on_scene_created(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test handling SceneCreated event."""
        subscriber._on_scene_created(
            scene_id="scene_001",
            title="The Encounter",
            summary="Alice meets Bob",
            location="Forest",
            chapter_id="chapter_001",
        )

        # Verify queue_ingestion was called
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert call_kwargs["source_id"] == "scene_001"
        assert call_kwargs["source_type"] == SourceType.SCENE
        assert "The Encounter" in call_kwargs["content"]
        assert "Alice meets Bob" in call_kwargs["content"]
        assert "Location: Forest" in call_kwargs["content"]
        assert call_kwargs["extra_metadata"]["chapter_id"] == "chapter_001"

    @pytest.mark.asyncio
    async def test_on_scene_created_with_beats(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test SceneCreated with beats includes beat content."""
        subscriber._on_scene_created(
            scene_id="scene_001",
            title="The Encounter",
            beats=[
                {"content": "They meet"},
                {"content": "They fight"},
            ],
        )

        # Verify queue_ingestion was called
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert "They meet" in call_kwargs["content"]
        assert "They fight" in call_kwargs["content"]
        assert "Beat 1" in call_kwargs["content"]
        assert "Beat 2" in call_kwargs["content"]

    @pytest.mark.asyncio
    async def test_on_scene_updated(
        self,
        subscriber: KnowledgeEventSubscriber,
        mock_sync_handler: Mock,
    ) -> None:
        """Test handling SceneUpdated event."""
        subscriber._on_scene_updated(
            scene_id="scene_001",
            title="The Encounter",
            summary="Updated summary",
        )

        # Verify queue_ingestion was called with updated tag
        mock_sync_handler.queue_ingestion.assert_called_once()
        call_kwargs = mock_sync_handler.queue_ingestion.call_args[1]

        assert call_kwargs["source_id"] == "scene_001"
        assert call_kwargs["source_type"] == SourceType.SCENE
        assert "updated" in call_kwargs["tags"]
        assert "Updated summary" in call_kwargs["content"]
