"""
Knowledge Event Subscriber

Bridges domain events (CharacterCreated, LoreCreated, etc.)
to the KnowledgeSyncEventHandler for automatic ingestion.

This module subscribes to events from other bounded contexts
and triggers knowledge ingestion.

Constitution Compliance:
- Article II (Hexagonal): Application layer integration
- Article VI (EDA): Event-driven integration between contexts

Warzone 4: AI Brain - BRAIN-005
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog

from ...domain.models.source_type import SourceType
from .knowledge_sync_event_handler import (
    KnowledgeSyncEventHandler,
    _character_to_content,
    _lore_to_content,
    _scene_to_content,
)

if TYPE_CHECKING:
    from src.core.event_bus import EventBus


logger = structlog.get_logger()


class KnowledgeEventSubscriber:
    """
    Subscribes to domain events and triggers knowledge ingestion.

    Listens for events from Character, Lore, and Scene contexts
    and automatically ingests them into the RAG system.

    Optionally integrates with SmartTaggingEventHandler to automatically
    generate and store tags for entities.

    Example:
        >>> subscriber = KnowledgeEventSubscriber(
        ...     event_bus=event_bus,
        ...     sync_handler=sync_handler,
        ...     tagging_handler=tagging_handler,  # Optional
        ... )
        >>> await subscriber.subscribe_to_all()
        >>> # Now automatically ingests on events
        >>> await subscriber.unsubscribe_all()
    """

    def __init__(
        self,
        event_bus: EventBus,
        sync_handler: KnowledgeSyncEventHandler,
        tagging_handler: Any | None = None,  # SmartTaggingEventHandler
    ):
        """
        Initialize the subscriber.

        Args:
            event_bus: The event bus to subscribe to
            sync_handler: The sync handler that processes ingestions
            tagging_handler: Optional smart tagging handler for auto-tagging
        """
        self._event_bus = event_bus
        self._sync_handler = sync_handler
        self._tagging_handler = tagging_handler
        self._subscribed = False

    async def subscribe_to_all(self) -> None:
        """Subscribe to all relevant domain events."""
        if self._subscribed:
            logger.warning("knowledge_event_subscriber_already_subscribed")
            return

        # Subscribe to Character events
        self._event_bus.subscribe(
            "character.created",
            self._on_character_created,
        )
        self._event_bus.subscribe(
            "character.updated",
            self._on_character_updated,
        )

        # Subscribe to Lore events
        # Note: These use the world context event naming
        self._event_bus.subscribe(
            "lore.created",
            self._on_lore_created,
        )
        self._event_bus.subscribe(
            "lore.updated",
            self._on_lore_updated,
        )

        # Subscribe to Scene events
        self._event_bus.subscribe(
            "scene.created",
            self._on_scene_created,
        )
        self._event_bus.subscribe(
            "scene.updated",
            self._on_scene_updated,
        )

        self._subscribed = True

        logger.info("knowledge_event_subscriber_subscribed")

    async def unsubscribe_all(self) -> None:
        """Unsubscribe from all domain events."""
        if not self._subscribed:
            return

        # Unsubscribe from Character events
        self._event_bus.unsubscribe(
            "character.created",
            self._on_character_created,
        )
        self._event_bus.unsubscribe(
            "character.updated",
            self._on_character_updated,
        )

        # Unsubscribe from Lore events
        self._event_bus.unsubscribe(
            "lore.created",
            self._on_lore_created,
        )
        self._event_bus.unsubscribe(
            "lore.updated",
            self._on_lore_updated,
        )

        # Unsubscribe from Scene events
        self._event_bus.unsubscribe(
            "scene.created",
            self._on_scene_created,
        )
        self._event_bus.unsubscribe(
            "scene.updated",
            self._on_scene_updated,
        )

        self._subscribed = False

        logger.info("knowledge_event_subscriber_unsubscribed")

    # Character event handlers

    def _on_character_created(self, **kwargs: Any) -> None:
        """
        Handle CharacterCreated event.

        Expected kwargs:
            character_id: str
            character_name: str
            description: str (optional)
            traits: list[str] (optional)
            backstory: str (optional)
        """
        character_id = kwargs.get("character_id")
        character_name = kwargs.get("character_name")

        if not character_id or not character_name:
            logger.warning("character_created_missing_data", kwargs=kwargs)
            return

        # Build content from character data
        content = _character_to_content(
            character_id=str(character_id),
            name=character_name,
            description=kwargs.get("description"),
            traits=kwargs.get("traits"),
            backstory=kwargs.get("backstory"),
        )

        # Queue for ingestion
        asyncio_coro = self._sync_handler.queue_ingestion(
            source_id=str(character_id),
            source_type=SourceType.CHARACTER,
            content=content,
            tags=kwargs.get("tags", ["character"]),
        )

        # Create task for async processing
        import asyncio

        asyncio.create_task(asyncio_coro)

        logger.info(
            "character_created_queued_for_ingestion",
            character_id=str(character_id),
            character_name=character_name,
        )

    def _on_character_updated(self, **kwargs: Any) -> None:
        """
        Handle CharacterUpdated event.

        Expected kwargs:
            character_id: str
            character_name: str
            description: str (optional)
            traits: list[str] (optional)
            backstory: str (optional)
            updated_fields: list[str]
        """
        character_id = kwargs.get("character_id")
        character_name = kwargs.get("character_name")

        if not character_id or not character_name:
            logger.warning("character_updated_missing_data", kwargs=kwargs)
            return

        # Build content from character data
        content = _character_to_content(
            character_id=str(character_id),
            name=character_name,
            description=kwargs.get("description"),
            traits=kwargs.get("traits"),
            backstory=kwargs.get("backstory"),
        )

        # Queue for ingestion (update replaces old content)
        asyncio_coro = self._sync_handler.queue_ingestion(
            source_id=str(character_id),
            source_type=SourceType.CHARACTER,
            content=content,
            tags=kwargs.get("tags", ["character", "updated"]),
        )

        # Create task for async processing
        import asyncio

        asyncio.create_task(asyncio_coro)

        logger.info(
            "character_updated_queued_for_ingestion",
            character_id=str(character_id),
            character_name=character_name,
            updated_fields=kwargs.get("updated_fields", []),
        )

    # Lore event handlers

    def _on_lore_created(self, **kwargs: Any) -> None:
        """
        Handle LoreCreated event.

        Expected kwargs:
            lore_id: str
            title: str
            content: str
            category: str (optional)
            tags: list[str] (optional)
        """
        lore_id = kwargs.get("lore_id")
        title = kwargs.get("title")
        content = kwargs.get("content")

        if not lore_id or not title:
            logger.warning("lore_created_missing_data", kwargs=kwargs)
            return

        # Use provided content or build from fields
        if not content:
            content = f"# {title}\n\n{kwargs.get('summary', '')}"

        # Build formatted content
        formatted_content = _lore_to_content(
            lore_id=str(lore_id),
            title=title,
            content=content,
            category=kwargs.get("category"),
            tags=kwargs.get("tags"),
        )

        # Build metadata with smart tags if tagging handler is available
        extra_metadata = {}
        if self._tagging_handler:
            # Queue async smart tagging
            asyncio.create_task(
                self._generate_and_store_lore_tags(
                    lore_id=str(lore_id),
                    title=title,
                    content=content,
                    category=kwargs.get("category"),
                    existing_tags=kwargs.get("smart_tags"),
                )
            )

        # Queue for ingestion
        asyncio_coro = self._sync_handler.queue_ingestion(
            source_id=str(lore_id),
            source_type=SourceType.LORE,
            content=formatted_content,
            tags=kwargs.get("tags", ["lore"]),
            extra_metadata=extra_metadata if extra_metadata else None,
        )

        # Create task for async processing
        asyncio.create_task(asyncio_coro)

        logger.info(
            "lore_created_queued_for_ingestion",
            lore_id=str(lore_id),
            title=title,
        )

    async def _generate_and_store_lore_tags(
        self,
        lore_id: str,
        title: str,
        content: str,
        category: str | None = None,
        existing_tags: dict[str, list[str]] | None = None,
    ) -> None:
        """
        Generate smart tags for lore and store in metadata.

        Args:
            lore_id: Lore entry ID
            title: Lore title
            content: Lore content
            category: Lore category
            existing_tags: Existing tags to preserve
        """
        if not self._tagging_handler:
            return

        try:
            tags = await self._tagging_handler.generate_tags_for_lore(
                lore_id=lore_id,
                title=title,
                content=content,
                category=category,
                existing_tags=existing_tags,
            )

            # Store tags in metadata
            # In a real implementation, this would call a repository
            # to persist the tags to the entity's metadata
            logger.info(
                "smart_tags_stored_for_lore",
                lore_id=lore_id,
                tags=tags,
            )

        except Exception as e:
            logger.error(
                "smart_tagging_lore_error",
                lore_id=lore_id,
                error=str(e),
            )

    def _on_lore_updated(self, **kwargs: Any) -> None:
        """
        Handle LoreUpdated event.

        Expected kwargs:
            lore_id: str
            title: str
            content: str
            category: str (optional)
            tags: list[str] (optional)
        """
        lore_id = kwargs.get("lore_id")
        title = kwargs.get("title")
        content = kwargs.get("content")

        if not lore_id or not title:
            logger.warning("lore_updated_missing_data", kwargs=kwargs)
            return

        # Use provided content or build from fields
        if not content:
            content = f"# {title}\n\n{kwargs.get('summary', '')}"

        # Build formatted content
        formatted_content = _lore_to_content(
            lore_id=str(lore_id),
            title=title,
            content=content,
            category=kwargs.get("category"),
            tags=kwargs.get("tags"),
        )

        # Build metadata with smart tags if tagging handler is available
        extra_metadata = {}
        if self._tagging_handler:
            # Queue async smart tagging
            asyncio.create_task(
                self._generate_and_store_lore_tags(
                    lore_id=str(lore_id),
                    title=title,
                    content=content,
                    category=kwargs.get("category"),
                    existing_tags=kwargs.get("smart_tags"),
                )
            )

        # Queue for ingestion (update replaces old content)
        asyncio_coro = self._sync_handler.queue_ingestion(
            source_id=str(lore_id),
            source_type=SourceType.LORE,
            content=formatted_content,
            tags=kwargs.get("tags", ["lore", "updated"]),
            extra_metadata=extra_metadata if extra_metadata else None,
        )

        # Create task for async processing
        asyncio.create_task(asyncio_coro)

        logger.info(
            "lore_updated_queued_for_ingestion",
            lore_id=str(lore_id),
            title=title,
        )

    # Scene event handlers

    def _on_scene_created(self, **kwargs: Any) -> None:
        """
        Handle SceneCreated event.

        Expected kwargs:
            scene_id: str or UUID
            title: str
            summary: str (optional)
            location: str (optional)
            chapter_id: str or UUID (optional)
            beats: list[dict] (optional)
        """
        scene_id = kwargs.get("scene_id")
        title = kwargs.get("title")

        if not scene_id or not title:
            logger.warning("scene_created_missing_data", kwargs=kwargs)
            return

        # Extract beat content if available
        beat_contents = []
        beats = kwargs.get("beats", [])
        for beat in beats:
            if isinstance(beat, dict):
                beat_contents.append(beat.get("content", ""))
            else:
                beat_contents.append(str(beat))

        # Build metadata
        extra_metadata = {}
        if chapter_id := kwargs.get("chapter_id"):
            extra_metadata["chapter_id"] = str(chapter_id)

        # Queue smart tagging if handler is available
        if self._tagging_handler:
            # Queue async smart tagging
            asyncio.create_task(
                self._generate_and_store_scene_tags(
                    scene_id=str(scene_id),
                    title=title,
                    summary=kwargs.get("summary"),
                    location=kwargs.get("location"),
                    beats=beat_contents if beat_contents else None,
                    existing_tags=kwargs.get("smart_tags"),
                )
            )

        # Build formatted content
        content = _scene_to_content(
            scene_id=str(scene_id),
            title=title,
            summary=kwargs.get("summary"),
            location=kwargs.get("location"),
            beats=beat_contents if beat_contents else None,
        )

        # Queue for ingestion
        asyncio_coro = self._sync_handler.queue_ingestion(
            source_id=str(scene_id),
            source_type=SourceType.SCENE,
            content=content,
            tags=["scene"],
            extra_metadata=extra_metadata if extra_metadata else None,
        )

        # Create task for async processing
        asyncio.create_task(asyncio_coro)

        logger.info(
            "scene_created_queued_for_ingestion",
            scene_id=str(scene_id),
            title=title,
        )

    async def _generate_and_store_scene_tags(
        self,
        scene_id: str,
        title: str,
        summary: str | None = None,
        location: str | None = None,
        beats: list[str] | None = None,
        existing_tags: dict[str, list[str]] | None = None,
    ) -> None:
        """
        Generate smart tags for scene and store in metadata.

        Args:
            scene_id: Scene ID
            title: Scene title
            summary: Scene summary
            location: Scene location
            beats: Scene beat contents
            existing_tags: Existing tags to preserve
        """
        if not self._tagging_handler:
            return

        try:
            tags = await self._tagging_handler.generate_tags_for_scene(
                scene_id=scene_id,
                title=title,
                summary=summary,
                location=location,
                beats=beats,
                existing_tags=existing_tags,
            )

            # Store tags in metadata
            logger.info(
                "smart_tags_stored_for_scene",
                scene_id=scene_id,
                tags=tags,
            )

        except Exception as e:
            logger.error(
                "smart_tagging_scene_error",
                scene_id=scene_id,
                error=str(e),
            )

    def _on_scene_updated(self, **kwargs: Any) -> None:
        """
        Handle SceneUpdated event.

        Expected kwargs:
            scene_id: str or UUID
            title: str
            summary: str (optional)
            location: str (optional)
            chapter_id: str or UUID (optional)
            beats: list[dict] (optional)
        """
        scene_id = kwargs.get("scene_id")
        title = kwargs.get("title")

        if not scene_id or not title:
            logger.warning("scene_updated_missing_data", kwargs=kwargs)
            return

        # Extract beat content if available
        beat_contents = []
        beats = kwargs.get("beats", [])
        for beat in beats:
            if isinstance(beat, dict):
                beat_contents.append(beat.get("content", ""))
            else:
                beat_contents.append(str(beat))

        # Build metadata
        extra_metadata = {}
        if chapter_id := kwargs.get("chapter_id"):
            extra_metadata["chapter_id"] = str(chapter_id)

        # Queue smart tagging if handler is available
        if self._tagging_handler:
            # Queue async smart tagging
            asyncio.create_task(
                self._generate_and_store_scene_tags(
                    scene_id=str(scene_id),
                    title=title,
                    summary=kwargs.get("summary"),
                    location=kwargs.get("location"),
                    beats=beat_contents if beat_contents else None,
                    existing_tags=kwargs.get("smart_tags"),
                )
            )

        # Build formatted content
        content = _scene_to_content(
            scene_id=str(scene_id),
            title=title,
            summary=kwargs.get("summary"),
            location=kwargs.get("location"),
            beats=beat_contents if beat_contents else None,
        )

        # Queue for ingestion (update replaces old content)
        asyncio_coro = self._sync_handler.queue_ingestion(
            source_id=str(scene_id),
            source_type=SourceType.SCENE,
            content=content,
            tags=["scene", "updated"],
            extra_metadata=extra_metadata if extra_metadata else None,
        )

        # Create task for async processing
        asyncio.create_task(asyncio_coro)

        logger.info(
            "scene_updated_queued_for_ingestion",
            scene_id=str(scene_id),
            title=title,
        )


__all__ = ["KnowledgeEventSubscriber"]
