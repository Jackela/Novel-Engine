"""End-to-end workflow tests."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from uuid import uuid4

import pytest


@pytest.mark.integration
@pytest.mark.e2e
class TestCompleteStoryCreationWorkflow:
    """Test complete workflow from story creation to character interaction."""

    async def test_create_user_world_story_character(self, memory_event_bus):
        """Test complete user, world, story, character creation flow."""
        events_recorded: List[Dict[str, Any]] = []

        async def record_event(event) -> None:
            events_recorded.append({"type": event.event_type, "payload": event.payload})

        # Subscribe to all relevant events
        await memory_event_bus.subscribe("UserCreated", record_event)
        await memory_event_bus.subscribe("WorldCreated", record_event)
        await memory_event_bus.subscribe("StoryCreated", record_event)
        await memory_event_bus.subscribe("CharacterCreated", record_event)

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        # 1. Create user
        user_id = str(uuid4())
        await memory_event_bus.publish(
            DomainEvent(
                event_type="UserCreated",
                payload={"user_id": user_id, "username": "test_user"},
                aggregate_id=user_id,
            )
        )

        # 2. Create world
        world_id = str(uuid4())
        await memory_event_bus.publish(
            DomainEvent(
                event_type="WorldCreated",
                payload={
                    "world_id": world_id,
                    "name": "Fantasy Realm",
                    "owner_id": user_id,
                },
                aggregate_id=world_id,
            )
        )

        # 3. Create story
        story_id = str(uuid4())
        await memory_event_bus.publish(
            DomainEvent(
                event_type="StoryCreated",
                payload={
                    "story_id": story_id,
                    "title": "Epic Journey",
                    "world_id": world_id,
                    "owner_id": user_id,
                },
                aggregate_id=story_id,
            )
        )

        # 4. Create character
        character_id = str(uuid4())
        await memory_event_bus.publish(
            DomainEvent(
                event_type="CharacterCreated",
                payload={
                    "character_id": character_id,
                    "name": "Hero",
                    "story_id": story_id,
                    "owner_id": user_id,
                },
                aggregate_id=character_id,
            )
        )

        await asyncio.sleep(0.1)

        # Verify all events were recorded
        assert len(events_recorded) == 4
        assert any(e["type"] == "UserCreated" for e in events_recorded)
        assert any(e["type"] == "WorldCreated" for e in events_recorded)
        assert any(e["type"] == "StoryCreated" for e in events_recorded)
        assert any(e["type"] == "CharacterCreated" for e in events_recorded)

    async def test_character_interaction_with_story(self, memory_event_bus):
        """Test character interaction events in story context."""
        interactions: List[Dict[str, Any]] = []

        async def record_interaction(event) -> None:
            if event.event_type in ["CharacterAction", "StoryProgressed"]:
                interactions.append(event.payload)

        await memory_event_bus.subscribe("CharacterAction", record_interaction)
        await memory_event_bus.subscribe("StoryProgressed", record_interaction)

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        story_id = str(uuid4())
        character_id = str(uuid4())

        # Character takes action
        await memory_event_bus.publish(
            DomainEvent(
                event_type="CharacterAction",
                payload={
                    "character_id": character_id,
                    "story_id": story_id,
                    "action": "explore",
                    "location": "dark_cave",
                },
                aggregate_id=character_id,
            )
        )

        # Story progresses
        await memory_event_bus.publish(
            DomainEvent(
                event_type="StoryProgressed",
                payload={
                    "story_id": story_id,
                    "chapter": 1,
                    "event": "character_explored",
                },
                aggregate_id=story_id,
            )
        )

        await asyncio.sleep(0.1)

        assert len(interactions) == 2


@pytest.mark.integration
@pytest.mark.e2e
class TestRumorPropagationWorkflow:
    """Test rumor creation and propagation workflow."""

    async def test_rumor_creation_and_propagation(self, memory_event_bus):
        """Test rumor creation and propagation through event system."""
        rumor_events: List[Dict[str, Any]] = []

        async def record_rumor(event) -> None:
            if "Rumor" in event.event_type:
                rumor_events.append({"type": event.event_type, "data": event.payload})

        await memory_event_bus.subscribe("RumorCreated", record_rumor)
        await memory_event_bus.subscribe("RumorPropagated", record_rumor)
        await memory_event_bus.subscribe("RumorHeard", record_rumor)

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        world_id = str(uuid4())
        location_id = str(uuid4())

        # 1. Create rumor at location
        rumor_id = str(uuid4())
        await memory_event_bus.publish(
            DomainEvent(
                event_type="RumorCreated",
                payload={
                    "rumor_id": rumor_id,
                    "world_id": world_id,
                    "location_id": location_id,
                    "content": "A dragon has been seen in the mountains",
                    "severity": "high",
                },
                aggregate_id=rumor_id,
            )
        )

        # 2. Propagate rumor to nearby locations
        target_location_id = str(uuid4())
        await memory_event_bus.publish(
            DomainEvent(
                event_type="RumorPropagated",
                payload={
                    "rumor_id": rumor_id,
                    "from_location": location_id,
                    "to_location": target_location_id,
                    "method": "word_of_mouth",
                },
                aggregate_id=rumor_id,
            )
        )

        # 3. Characters hear the rumor
        character_id = str(uuid4())
        await memory_event_bus.publish(
            DomainEvent(
                event_type="RumorHeard",
                payload={
                    "rumor_id": rumor_id,
                    "character_id": character_id,
                    "location_id": target_location_id,
                    "credibility": 0.8,
                },
                aggregate_id=character_id,
            )
        )

        await asyncio.sleep(0.1)

        # Verify rumor propagation chain
        assert len(rumor_events) == 3
        assert any(e["type"] == "RumorCreated" for e in rumor_events)
        assert any(e["type"] == "RumorPropagated" for e in rumor_events)
        assert any(e["type"] == "RumorHeard" for e in rumor_events)

    async def test_rumor_modification_as_it_spreads(self, memory_event_bus):
        """Test how rumors change as they propagate."""
        rumor_versions: List[Dict[str, Any]] = []

        async def record_version(event) -> None:
            if event.event_type == "RumorModified":
                rumor_versions.append(event.payload)

        await memory_event_bus.subscribe("RumorModified", record_version)

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        rumor_id = str(uuid4())

        # Original rumor
        await memory_event_bus.publish(
            DomainEvent(
                event_type="RumorModified",
                payload={
                    "rumor_id": rumor_id,
                    "version": 1,
                    "content": "A dragon was seen",
                    "accuracy": 1.0,
                },
                aggregate_id=rumor_id,
            )
        )

        # Modified version
        await memory_event_bus.publish(
            DomainEvent(
                event_type="RumorModified",
                payload={
                    "rumor_id": rumor_id,
                    "version": 2,
                    "content": "A huge dragon attacked the village",
                    "accuracy": 0.6,
                },
                aggregate_id=rumor_id,
            )
        )

        await asyncio.sleep(0.1)

        assert len(rumor_versions) == 2
        assert rumor_versions[1]["accuracy"] < rumor_versions[0]["accuracy"]


@pytest.mark.integration
@pytest.mark.e2e
class TestMemoryAndStoryIntegration:
    """Test memory system integration with story progression."""

    async def test_character_memory_integration(self, memory_event_bus):
        """Test character memories persist through story events."""
        memory_events: List[Dict[str, Any]] = []

        async def record_memory(event) -> None:
            if "Memory" in event.event_type:
                memory_events.append(event.payload)

        await memory_event_bus.subscribe("CharacterMemoryStored", record_memory)
        await memory_event_bus.subscribe("CharacterMemoryRecalled", record_memory)

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        character_id = str(uuid4())
        story_id = str(uuid4())

        # Store memory during story event
        await memory_event_bus.publish(
            DomainEvent(
                event_type="CharacterMemoryStored",
                payload={
                    "character_id": character_id,
                    "story_id": story_id,
                    "content": "Saved the princess from the tower",
                    "significance": "major",
                    "emotional_impact": 0.9,
                },
                aggregate_id=character_id,
            )
        )

        # Recall memory during later story event
        await memory_event_bus.publish(
            DomainEvent(
                event_type="CharacterMemoryRecalled",
                payload={
                    "character_id": character_id,
                    "story_id": story_id,
                    "memory_content": "Saved the princess from the tower",
                    "trigger": "seeing a tower",
                },
                aggregate_id=character_id,
            )
        )

        await asyncio.sleep(0.1)

        assert len(memory_events) == 2


@pytest.mark.integration
@pytest.mark.e2e
class TestMultiCharacterInteraction:
    """Test interactions between multiple characters."""

    async def test_character_dialogue_workflow(self, memory_event_bus):
        """Test dialogue between multiple characters."""
        dialogue_events: List[Dict[str, Any]] = []

        async def record_dialogue(event) -> None:
            if event.event_type in ["CharacterSpoke", "CharacterHeard"]:
                dialogue_events.append(event.payload)

        await memory_event_bus.subscribe("CharacterSpoke", record_dialogue)
        await memory_event_bus.subscribe("CharacterHeard", record_dialogue)

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        char1_id = str(uuid4())
        char2_id = str(uuid4())
        story_id = str(uuid4())

        # Character 1 speaks
        await memory_event_bus.publish(
            DomainEvent(
                event_type="CharacterSpoke",
                payload={
                    "character_id": char1_id,
                    "story_id": story_id,
                    "message": "Have you heard the news?",
                    "tone": "curious",
                },
                aggregate_id=char1_id,
            )
        )

        # Character 2 hears
        await memory_event_bus.publish(
            DomainEvent(
                event_type="CharacterHeard",
                payload={
                    "character_id": char2_id,
                    "story_id": story_id,
                    "speaker_id": char1_id,
                    "message": "Have you heard the news?",
                    "understanding": 0.95,
                },
                aggregate_id=char2_id,
            )
        )

        await asyncio.sleep(0.1)

        assert len(dialogue_events) == 2

    async def test_character_relationship_updates(self, memory_event_bus):
        """Test character relationship changes through interactions."""
        relationship_events: List[Dict[str, Any]] = []

        async def record_relationship(event) -> None:
            if event.event_type == "CharacterRelationshipUpdated":
                relationship_events.append(event.payload)

        await memory_event_bus.subscribe(
            "CharacterRelationshipUpdated", record_relationship
        )

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        char1_id = str(uuid4())
        char2_id = str(uuid4())

        # Positive interaction improves relationship
        await memory_event_bus.publish(
            DomainEvent(
                event_type="CharacterRelationshipUpdated",
                payload={
                    "character1_id": char1_id,
                    "character2_id": char2_id,
                    "change": +0.2,
                    "reason": "helped in combat",
                    "new_value": 0.7,
                },
                aggregate_id=char1_id,
            )
        )

        await asyncio.sleep(0.1)

        assert len(relationship_events) == 1
        assert relationship_events[0]["new_value"] == 0.7


@pytest.mark.integration
@pytest.mark.e2e
class TestWorldStateWorkflows:
    """Test world state management workflows."""

    async def test_world_state_snapshot_workflow(self, memory_event_bus):
        """Test world state snapshot creation."""
        snapshot_events: List[Dict[str, Any]] = []

        async def record_snapshot(event) -> None:
            if event.event_type == "WorldStateSnapshotCreated":
                snapshot_events.append(event.payload)

        await memory_event_bus.subscribe("WorldStateSnapshotCreated", record_snapshot)

        from src.shared.infrastructure.messaging.event_bus import DomainEvent

        world_id = str(uuid4())

        await memory_event_bus.publish(
            DomainEvent(
                event_type="WorldStateSnapshotCreated",
                payload={
                    "world_id": world_id,
                    "snapshot_id": str(uuid4()),
                    "turn": 1,
                    "state": {
                        "weather": "sunny",
                        "time": "morning",
                        "active_quests": ["quest_1"],
                    },
                },
                aggregate_id=world_id,
            )
        )

        await asyncio.sleep(0.1)

        assert len(snapshot_events) == 1
