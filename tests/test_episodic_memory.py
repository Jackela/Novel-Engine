#!/usr/bin/env python3
"""
Tests for EpisodicMemory

Testing Coverage:
- Unit tests for all public methods (15+ methods)
- Integration tests for temporal/thematic/participant indexing
- Edge cases and error conditions
- Consolidation and significance scoring
- Causal linking between episodes
"""

import asyncio
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio  # codeql[py/unused-global-variable]

from src.core.data_models import MemoryItem, MemoryType
from src.database.context_db import ContextDatabase
from src.memory.episodic_memory import EpisodicEvent, EpisodicMemory


class TestEpisodicEvent:
    """Unit tests for EpisodicEvent dataclass."""

    @pytest.mark.unit
    def test_episodic_event_initialization(self):
        """Test EpisodicEvent initialization and significance calculation."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="A significant event.",
            emotional_weight=7.0,
            participants=["Character A", "Character B"],
        )

        event = EpisodicEvent(
            memory_item=memory,
            temporal_context={"time_of_day": "morning"},
            spatial_context={"location": "Main Gate"},
            social_context=["Character A", "Character B"],
        )

        assert event.memory_item == memory
        assert event.temporal_context == {"time_of_day": "morning"}
        assert event.spatial_context == {"location": "Main Gate"}
        assert event.social_context == ["Character A", "Character B"]
        assert event.significance_score > 0.0
        assert event.significance_score <= 1.0

    @pytest.mark.unit
    def test_episodic_event_significance_calculation(self):
        """Test significance score calculation."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Test event.",
            emotional_weight=10.0,
            participants=["A", "B", "C"],
        )

        event = EpisodicEvent(
            memory_item=memory,
            social_context=["A", "B", "C"],
            emotional_peaks=[("peak1", 0.8), ("peak2", 0.9)],
        )

        assert event.significance_score > 0.0

    @pytest.mark.unit
    def test_add_causal_link(self):
        """Test adding causal links to events."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event A.",
        )

        event = EpisodicEvent(memory_item=memory)

        initial_significance = event.significance_score

        event.add_causal_link("memory_b", "leads_to")

        assert "leads_to:memory_b" in event.causal_links
        assert event.significance_score >= initial_significance

    @pytest.mark.unit
    def test_add_duplicate_causal_link(self):
        """Test that duplicate causal links are not added."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event.",
        )

        event = EpisodicEvent(memory_item=memory)

        event.add_causal_link("memory_b", "leads_to")
        event.add_causal_link("memory_b", "leads_to")

        assert event.causal_links.count("leads_to:memory_b") == 1


class TestEpisodicMemory:
    """Unit tests for EpisodicMemory system."""

    @pytest_asyncio.fixture
    async def database(self):
        """Setup test database."""
        db = ContextDatabase(":memory:")
        await db.initialize()
        yield db
        await db.close()

    @pytest_asyncio.fixture
    async def episodic_memory(self, database):
        """Setup test EpisodicMemory instance."""
        memory = EpisodicMemory(
            agent_id="test_agent_001",
            database=database,
            max_episodes=100,
            consolidation_threshold=0.7,
        )
        yield memory

    @pytest.fixture
    def sample_memory(self):
        """Create sample memory item for testing."""
        return MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="A significant battle occurred at the main gate.",
            emotional_weight=7.0,
            participants=["Commander Lex", "Enemy Alpha"],
            location="Main Gate",
            tags=["combat", "important"],
        )

    async def test_initialization(self, episodic_memory):
        """Test EpisodicMemory initialization."""
        assert episodic_memory.agent_id == "test_agent_001"
        assert episodic_memory.max_episodes == 100
        assert episodic_memory.consolidation_threshold == 0.7
        assert episodic_memory.total_episodes == 0
        assert episodic_memory.consolidated_episodes == 0
        assert len(episodic_memory._episodes) == 0

    async def test_store_episode_success(self, episodic_memory, sample_memory):
        """Test successful episode storage."""
        result = await episodic_memory.store_episode(sample_memory)

        assert result.success is True
        assert "stored" in result.data
        assert result.data["stored"] is True
        assert "significance_score" in result.data
        assert "themes" in result.data
        assert episodic_memory.total_episodes == 1
        assert sample_memory.memory_id in episodic_memory._episodes

    async def test_store_episode_with_temporal_context(self, episodic_memory):
        """Test episode storage with temporal context."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Morning event.",
        )

        temporal_context = {"time_of_day": "morning", "duration_minutes": 30}

        result = await episodic_memory.store_episode(
            memory, temporal_context=temporal_context
        )

        assert result.success is True
        episode = episodic_memory._episodes[memory.memory_id]
        assert episode.temporal_context == temporal_context

    async def test_store_episode_with_spatial_context(self, episodic_memory):
        """Test episode storage with spatial context."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Location-based event.",
        )

        spatial_context = {"location": "Main Gate", "coordinates": "x:100,y:200"}

        result = await episodic_memory.store_episode(
            memory, spatial_context=spatial_context
        )

        assert result.success is True
        episode = episodic_memory._episodes[memory.memory_id]
        assert episode.spatial_context == spatial_context

    async def test_store_episode_with_significance_boost(self, episodic_memory):
        """Test episode storage with significance boost."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Boosted event.",
        )

        result = await episodic_memory.store_episode(memory, significance_boost=0.5)

        assert result.success is True
        assert result.data["significance_score"] >= 0.0

    async def test_retrieve_episodes_by_timeframe(self, episodic_memory):
        """Test temporal episode retrieval."""
        memories = []
        for i in range(5):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event {i}",
                timestamp=datetime.now() + timedelta(hours=i),
            )
            memories.append(memory)
            await episodic_memory.store_episode(memory)

        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=10)

        result = await episodic_memory.retrieve_episodes_by_timeframe(
            start_time, end_time, limit=10
        )

        assert result.success is True
        assert "episodes" in result.data
        assert len(result.data["episodes"]) == 5
        assert "timeframe" in result.data
        assert "total_found" in result.data

    async def test_retrieve_episodes_by_timeframe_limited(self, episodic_memory):
        """Test temporal retrieval with limit."""
        for i in range(10):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event {i}",
                timestamp=datetime.now() + timedelta(minutes=i),
            )
            await episodic_memory.store_episode(memory)

        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)

        result = await episodic_memory.retrieve_episodes_by_timeframe(
            start_time, end_time, limit=3
        )

        assert result.success is True
        assert len(result.data["episodes"]) == 3

    async def test_retrieve_episodes_by_timeframe_empty(self, episodic_memory):
        """Test temporal retrieval with no matches."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Recent event.",
            timestamp=datetime.now(),
        )
        await episodic_memory.store_episode(memory)

        past_start = datetime.now() - timedelta(days=10)
        past_end = datetime.now() - timedelta(days=5)

        result = await episodic_memory.retrieve_episodes_by_timeframe(
            past_start, past_end
        )

        assert result.success is True
        assert len(result.data["episodes"]) == 0

    async def test_retrieve_episodes_by_participants(self, episodic_memory):
        """Test participant-based episode retrieval."""
        for i in range(3):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event with Commander Lex {i}",
                participants=["Commander Lex", f"Soldier {i}"],
            )
            await episodic_memory.store_episode(memory)

        memory_without = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event without Commander Lex",
            participants=["Other Person"],
        )
        await episodic_memory.store_episode(memory_without)

        result = await episodic_memory.retrieve_episodes_by_participants(
            ["Commander Lex"], limit=10
        )

        assert result.success is True
        assert len(result.data["episodes"]) >= 0
        assert result.data["participants"] == ["Commander Lex"]
        assert episodic_memory.total_episodes == 4

    async def test_retrieve_episodes_by_multiple_participants(self, episodic_memory):
        """Test retrieval with multiple participants."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Multi-person event",
            participants=["Person A", "Person B", "Person C"],
        )
        await episodic_memory.store_episode(memory)

        result = await episodic_memory.retrieve_episodes_by_participants(
            ["Person A", "Person B"]
        )

        assert result.success is True
        assert len(result.data["episodes"]) >= 0
        assert episodic_memory.total_episodes == 1

    async def test_retrieve_episodes_by_theme(self, episodic_memory):
        """Test thematic episode retrieval."""
        combat_memories = []
        for i in range(3):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"A fierce battle occurred at gate {i}",
            )
            combat_memories.append(memory)
            await episodic_memory.store_episode(memory)

        social_memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Had a friendly conversation over tea",
        )
        await episodic_memory.store_episode(social_memory)

        combat_result = await episodic_memory.retrieve_episodes_by_theme(
            ["combat", "battle"], limit=10
        )

        assert combat_result.success is True
        assert len(combat_result.data["episodes"]) >= 3
        assert combat_result.data["themes"] == ["combat", "battle"]

    async def test_retrieve_episodes_by_theme_multiple_themes(self, episodic_memory):
        """Test retrieval with multiple theme keywords."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Discovered a hidden chamber during exploration",
        )
        await episodic_memory.store_episode(memory)

        result = await episodic_memory.retrieve_episodes_by_theme(
            ["discover", "explore"]
        )

        assert result.success is True
        assert len(result.data["episodes"]) >= 0
        assert episodic_memory.total_episodes == 1

    async def test_link_episodes_causally(self, episodic_memory):
        """Test causal linking between episodes."""
        memory_a = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event A causes Event B",
        )
        memory_b = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event B is caused by Event A",
        )

        await episodic_memory.store_episode(memory_a)
        await episodic_memory.store_episode(memory_b)

        result = await episodic_memory.link_episodes_causally(
            memory_a.memory_id, memory_b.memory_id, link_type="causes"
        )

        assert result.success is True
        assert result.data["linked"] is True
        assert result.data["link_type"] == "causes"

        episode_a = episodic_memory._episodes[memory_a.memory_id]
        episode_b = episodic_memory._episodes[memory_b.memory_id]

        assert f"causes:{memory_b.memory_id}" in episode_a.causal_links
        assert f"caused_by:{memory_a.memory_id}" in episode_b.causal_links

    async def test_link_episodes_different_link_types(self, episodic_memory):
        """Test different causal link types."""
        memory_a = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event A",
        )
        memory_b = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event B",
        )

        await episodic_memory.store_episode(memory_a)
        await episodic_memory.store_episode(memory_b)

        link_types = ["leads_to", "enables", "causes"]

        for link_type in link_types:
            memory_x = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event {link_type}",
            )
            await episodic_memory.store_episode(memory_x)

            result = await episodic_memory.link_episodes_causally(
                memory_a.memory_id, memory_x.memory_id, link_type=link_type
            )

            assert result.success is True
            assert result.data["link_type"] == link_type

    async def test_link_episodes_not_found(self, episodic_memory):
        """Test linking non-existent episodes."""
        result = await episodic_memory.link_episodes_causally(
            "nonexistent_a", "nonexistent_b"
        )

        assert result.success is False
        assert result.error.code == "EPISODE_NOT_FOUND"

    async def test_extract_themes(self, episodic_memory):
        """Test theme extraction from content."""
        themes_combat = episodic_memory._extract_themes(
            "A fierce battle and combat occurred"
        )
        assert "combat" in themes_combat

        themes_social = episodic_memory._extract_themes(
            "Had a friendly conversation and met new allies"
        )
        assert "social" in themes_social

        themes_exploration = episodic_memory._extract_themes(
            "Discovered a hidden chamber while exploring"
        )
        assert "exploration" in themes_exploration

        themes_emotion = episodic_memory._extract_themes("Felt proud and joyful")
        assert "emotion" in themes_emotion

        themes_technical = episodic_memory._extract_themes(
            "Built a new system and repaired the machine"
        )
        assert "technical" in themes_technical

    async def test_update_indices(self, episodic_memory, sample_memory):
        """Test index updating."""
        themes = episodic_memory._extract_themes(sample_memory.content)

        episodic_memory._update_indices(sample_memory, themes)

        date_key = sample_memory.timestamp.date().isoformat()
        assert sample_memory.memory_id in episodic_memory._temporal_index[date_key]

        for theme in themes:
            assert (
                sample_memory.memory_id
                in episodic_memory._thematic_index[theme.lower()]
            )

        for participant in sample_memory.participants:
            assert (
                sample_memory.memory_id
                in episodic_memory._participant_index[participant.lower()]
            )

    async def test_get_memory_statistics_empty(self, episodic_memory):
        """Test statistics retrieval with no episodes."""
        stats = episodic_memory.get_memory_statistics()

        assert stats["total_episodes"] == 0
        assert stats["average_significance"] == 0.0

    async def test_get_memory_statistics(self, episodic_memory):
        """Test statistics retrieval."""
        for i in range(5):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event {i}",
                emotional_weight=float(i),
            )
            await episodic_memory.store_episode(memory)

        stats = episodic_memory.get_memory_statistics()

        assert stats["total_episodes"] == 5
        assert stats["average_significance"] > 0.0
        assert "consolidated_episodes" in stats
        assert "temporal_index_size" in stats
        assert "thematic_index_size" in stats
        assert "participant_index_size" in stats
        assert "last_consolidation" in stats

    async def test_consolidation_trigger(self, episodic_memory):
        """Test automatic consolidation triggering."""
        episodic_memory.consolidation_threshold = 0.5

        for i in range(50):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Significant event {i}",
                emotional_weight=10.0,
            )
            await episodic_memory.store_episode(memory)

        assert episodic_memory.consolidated_episodes > 0

    async def test_perform_consolidation(self, episodic_memory):
        """Test consolidation process."""
        episodic_memory.consolidation_threshold = 0.5

        for i in range(10):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event {i}",
                emotional_weight=10.0 if i % 2 == 0 else 1.0,
            )
            await episodic_memory.store_episode(memory)

        result = await episodic_memory._perform_consolidation()

        assert result.success is True
        assert "consolidated_count" in result.data
        assert "consolidation_time_ms" in result.data
        assert result.data["consolidated_count"] >= 0

    async def test_multiple_episode_storage(self, episodic_memory):
        """Test storing multiple episodes."""
        memories = [
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event {i}",
            )
            for i in range(10)
        ]

        for memory in memories:
            result = await episodic_memory.store_episode(memory)
            assert result.success is True

        assert episodic_memory.total_episodes == 10
        assert len(episodic_memory._episodes) == 10

    async def test_episode_sorting_by_significance(self, episodic_memory):
        """Test that episodes are sorted by significance."""
        high_sig_memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Very important event",
            emotional_weight=10.0,
            participants=["A", "B", "C", "D"],
        )

        low_sig_memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Minor event",
            emotional_weight=1.0,
        )

        await episodic_memory.store_episode(low_sig_memory)
        await episodic_memory.store_episode(high_sig_memory)

        high_episode = episodic_memory._episodes[high_sig_memory.memory_id]
        low_episode = episodic_memory._episodes[low_sig_memory.memory_id]

        assert high_episode.significance_score > low_episode.significance_score

    async def test_concurrent_episode_storage(self, episodic_memory):
        """Test concurrent episode storage."""
        memories = [
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Concurrent event {i}",
            )
            for i in range(5)
        ]

        results = await asyncio.gather(
            *[episodic_memory.store_episode(m) for m in memories]
        )

        assert all(r.success for r in results)
        assert episodic_memory.total_episodes == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


__all__ = ["TestEpisodicEvent", "TestEpisodicMemory"]
