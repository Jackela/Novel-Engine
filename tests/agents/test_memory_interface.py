#!/usr/bin/env python3
"""
Test suite for MemoryInterface module.

Tests memory management, experience processing, and relationship updates.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.agents.memory_interface import MemoryInterface


class TestMemoryInterfaceInitialization:
    """Test MemoryInterface initialization."""

    @pytest.fixture
    def mock_agent_core(self):
        """Create a mock agent core."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = []
        core.long_term_memory = []
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        return core

    def test_initialization(self, mock_agent_core):
        """Test basic initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            interface = MemoryInterface(mock_agent_core, tmpdir)

            assert interface.agent_core == mock_agent_core
            assert interface.character_directory_path == tmpdir
            assert interface.short_term_memory_limit == 20
            assert interface.long_term_memory_limit == 200
            assert interface.significance_threshold == 0.6

    def test_initialization_creates_memory_log_path(self, mock_agent_core):
        """Test that memory log path is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            interface = MemoryInterface(mock_agent_core, tmpdir)

            expected_path = os.path.join(tmpdir, "memory.log")
            assert interface.memory_log_path == expected_path


class TestMemoryInterfaceUpdateInternal:
    """Test internal memory update methods."""

    @pytest.fixture
    def memory_interface(self):
        """Create a MemoryInterface with mock core."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = []
        core.long_term_memory = []
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            yield MemoryInterface(core, tmpdir)

    def test_update_internal_memory_valid(self, memory_interface):
        """Test updating internal memory with valid log."""
        new_log = {
            "event_type": "combat",
            "description": "Fought an enemy",
            "participants": ["enemy1"],
            "outcome": "victory",
            "significance": 0.8,
            "emotional_impact": "triumph",
        }

        memory_interface.update_internal_memory(new_log)

        assert len(memory_interface.agent_core.short_term_memory) == 1
        assert memory_interface.experiences_processed == 1

    def test_update_internal_memory_invalid(self, memory_interface):
        """Test updating internal memory with invalid log."""
        memory_interface.update_internal_memory("invalid string")

        assert len(memory_interface.agent_core.short_term_memory) == 0

    def test_update_internal_memory_high_significance(self, memory_interface):
        """Test memory update with high significance event."""
        new_log = {
            "event_type": "combat",
            "description": "Major battle",
            "participants": ["enemy1"],
            "outcome": "victory",
            "significance": 0.9,
            "emotional_impact": "triumph",
        }

        memory_interface.update_internal_memory(new_log)

        # Should be in long-term memory
        assert len(memory_interface.agent_core.long_term_memory) == 1
        assert memory_interface.significant_experiences == 1


class TestMemoryInterfacePersistent:
    """Test persistent memory methods."""

    @pytest.fixture
    def memory_interface(self):
        """Create a MemoryInterface with mock core."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = []
        core.long_term_memory = []
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            yield MemoryInterface(core, tmpdir)

    def test_update_memory(self, memory_interface):
        """Test updating persistent memory."""
        memory_interface.update_memory("Test event occurred")

        # Check file was created and written
        assert os.path.exists(memory_interface.memory_log_path)
        with open(memory_interface.memory_log_path) as f:
            content = f.read()
            assert "Test event occurred" in content

    def test_update_memory_multiple(self, memory_interface):
        """Test multiple memory updates."""
        memory_interface.update_memory("Event 1")
        memory_interface.update_memory("Event 2")

        with open(memory_interface.memory_log_path) as f:
            content = f.read()
            assert "Event 1" in content
            assert "Event 2" in content

    def test_load_persistent_memories(self, memory_interface):
        """Test loading persistent memories."""
        # Create some memories
        memory_interface.update_memory("Memory 1")
        memory_interface.update_memory("Memory 2")

        memories = memory_interface.load_persistent_memories()

        assert len(memories) == 2
        assert any("Memory 1" in m for m in memories)

    def test_load_persistent_memories_empty(self, memory_interface):
        """Test loading when no memory file exists."""
        memories = memory_interface.load_persistent_memories()

        assert memories == []


class TestMemoryInterfaceRetrieval:
    """Test memory retrieval methods."""

    @pytest.fixture
    def memory_interface_with_data(self):
        """Create MemoryInterface with test data."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8

        # Pre-populate memories
        core.short_term_memory = [
            {
                "timestamp": 1.0,
                "event_type": "combat",
                "description": "Fought enemy",
                "significance": 0.7,
            },
            {
                "timestamp": 2.0,
                "event_type": "dialogue",
                "description": "Spoke with ally",
                "significance": 0.3,
            },
        ]
        core.long_term_memory = [
            {
                "timestamp": 0.5,
                "event_type": "betrayal",
                "description": "Major betrayal event",
                "significance": 0.9,
            },
        ]
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            yield MemoryInterface(core, tmpdir)

    def test_get_recent_memories(self, memory_interface_with_data):
        """Test getting recent memories."""
        memories = memory_interface_with_data.get_recent_memories(2)

        assert len(memories) == 2
        # Most recent first
        assert memories[0]["event_type"] == "dialogue"

    def test_get_recent_memories_count(self, memory_interface_with_data):
        """Test getting limited recent memories."""
        memories = memory_interface_with_data.get_recent_memories(1)

        assert len(memories) == 1

    def test_get_significant_memories(self, memory_interface_with_data):
        """Test getting significant memories."""
        memories = memory_interface_with_data.get_significant_memories(5)

        assert len(memories) == 1
        assert memories[0]["event_type"] == "betrayal"

    def test_search_memories(self, memory_interface_with_data):
        """Test searching memories."""
        memories = memory_interface_with_data.search_memories("combat")

        assert len(memories) >= 1
        assert any(m["event_type"] == "combat" for m in memories)

    def test_search_memories_long_term(self, memory_interface_with_data):
        """Test searching long-term memories."""
        memories = memory_interface_with_data.search_memories(
            "betrayal", memory_type="long_term"
        )

        assert len(memories) == 1

    def test_search_memories_no_match(self, memory_interface_with_data):
        """Test searching with no matches."""
        memories = memory_interface_with_data.search_memories("nonexistent")

        assert len(memories) == 0


class TestMemoryInterfaceCapacity:
    """Test memory capacity management."""

    @pytest.fixture
    def memory_interface(self):
        """Create MemoryInterface with small limits."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = []
        core.long_term_memory = []
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            interface = MemoryInterface(core, tmpdir)
            interface.short_term_memory_limit = 3  # Small for testing
            yield interface

    def test_short_term_memory_capacity(self, memory_interface):
        """Test short-term memory capacity limit."""
        # Add more memories than limit
        for i in range(5):
            memory_interface.agent_core.short_term_memory.append(
                {"event_type": f"event_{i}"}
            )

        memory_interface._manage_short_term_memory_capacity()

        assert len(memory_interface.agent_core.short_term_memory) == 3

    def test_long_term_memory_capacity(self, memory_interface):
        """Test long-term memory capacity management."""
        memory_interface.long_term_memory_limit = 3

        # Add memories with varying significance
        for i in range(5):
            memory_interface.agent_core.long_term_memory.append(
                {"event_type": f"event_{i}", "significance": i * 0.2}
            )

        memory_interface._manage_long_term_memory_capacity()

        assert len(memory_interface.agent_core.long_term_memory) == 3

    def test_consolidate_memories(self, memory_interface):
        """Test memory consolidation."""
        # Add qualifying short-term memories
        memory_interface.agent_core.short_term_memory = [
            {"event_type": "combat", "significance": 0.7},
            {"event_type": "wait", "significance": 0.3},
        ]

        count = memory_interface.consolidate_memories()

        assert count == 1  # Only combat should be consolidated
        assert len(memory_interface.agent_core.long_term_memory) == 1


class TestMemoryInterfaceRelationshipUpdates:
    """Test relationship update methods."""

    @pytest.fixture
    def memory_interface(self):
        """Create MemoryInterface."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = []
        core.long_term_memory = []
        core.relationships = {"ally": 0.5}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = max(-1.0, min(1.0, strength))

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            yield MemoryInterface(core, tmpdir)

    def test_update_relationships_from_combat(self, memory_interface):
        """Test relationship update from combat."""
        experience = {
            "event_type": "combat",
            "participants": ["ally"],
            "outcome": "victory",
            "emotional_impact": "positive",
        }

        memory_interface._update_relationships_from_experience(experience)

        assert memory_interface.agent_core.relationships["ally"] > 0.5

    def test_update_relationships_from_betrayal(self, memory_interface):
        """Test relationship update from betrayal."""
        experience = {
            "event_type": "betrayal",
            "participants": ["traitor"],
            "outcome": "failure",
        }

        memory_interface._update_relationships_from_experience(experience)

        assert memory_interface.agent_core.relationships["traitor"] < 0

    def test_update_relationships_from_dialogue(self, memory_interface):
        """Test relationship update from dialogue."""
        experience = {
            "event_type": "dialogue",
            "participants": ["ally"],
            "emotional_impact": "positive",
        }

        memory_interface._update_relationships_from_experience(experience)

        assert memory_interface.agent_core.relationships["ally"] > 0.5


class TestMemoryInterfaceWorldview:
    """Test worldview update methods."""

    @pytest.fixture
    def memory_interface(self):
        """Create MemoryInterface."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = []
        core.long_term_memory = []
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            yield MemoryInterface(core, tmpdir)

    def test_update_worldview_location(self, memory_interface):
        """Test worldview update with location."""
        experience = {
            "event_type": "exploration",
            "location": "Cave",
            "outcome": "discovery",
        }

        memory_interface._update_worldview_from_experience(experience)

        assert "location_knowledge" in memory_interface.agent_core.subjective_worldview

    def test_update_worldview_threat(self, memory_interface):
        """Test worldview update with threat."""
        experience = {
            "event_type": "combat",
            "location": "Forest",
            "participants": ["bandit"],
            "significance": 0.7,
        }

        memory_interface._update_worldview_from_experience(experience)

        assert "active_threats" in memory_interface.agent_core.subjective_worldview


class TestMemoryInterfaceMetrics:
    """Test metrics methods."""

    @pytest.fixture
    def memory_interface(self):
        """Create MemoryInterface."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = [{}, {}, {}]
        core.long_term_memory = [{}]
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            interface = MemoryInterface(core, tmpdir)
            interface.experiences_processed = 10
            interface.significant_experiences = 5
            yield interface

    def test_get_memory_metrics(self, memory_interface):
        """Test getting memory metrics."""
        metrics = memory_interface.get_memory_metrics()

        assert metrics["short_term_memory_count"] == 3
        assert metrics["long_term_memory_count"] == 1
        assert metrics["experiences_processed"] == 10
        assert metrics["significant_experiences"] == 5


class TestMemoryInterfaceClearing:
    """Test memory clearing methods."""

    @pytest.fixture
    def memory_interface(self):
        """Create MemoryInterface."""
        core = Mock()
        core.agent_id = "test_agent"
        core.short_term_memory = [{}, {}, {}]
        core.long_term_memory = [{}]

        with tempfile.TemporaryDirectory() as tmpdir:
            yield MemoryInterface(core, tmpdir)

    def test_clear_short_term_memory(self, memory_interface):
        """Test clearing short-term memory."""
        memory_interface.clear_short_term_memory()

        assert len(memory_interface.agent_core.short_term_memory) == 0


class TestMemoryInterfaceIntegration:
    """Integration tests."""

    def test_full_memory_flow(self):
        """Test full memory processing flow."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_name = "Test Character"
        core.faction = "Alliance"
        core.morale_level = 0.8
        core.short_term_memory = []
        core.long_term_memory = []
        core.relationships = {}
        core.behavioral_modifiers = {}
        core.subjective_worldview = {}

        def get_relationship_strength(entity):
            return core.relationships.get(entity, 0.0)

        def add_relationship(entity, strength):
            core.relationships[entity] = strength

        def add_to_subjective_worldview(category, key, value):
            if category not in core.subjective_worldview:
                core.subjective_worldview[category] = {}
            core.subjective_worldview[category][key] = value

        core.get_relationship_strength = get_relationship_strength
        core.add_relationship = add_relationship
        core.add_to_subjective_worldview = add_to_subjective_worldview

        with tempfile.TemporaryDirectory() as tmpdir:
            interface = MemoryInterface(core, tmpdir)

            # Process experiences
            for i in range(5):
                interface.update_internal_memory(
                    {
                        "event_type": "combat",
                        "description": f"Battle {i}",
                        "significance": 0.5 + i * 0.1,
                        "participants": [f"enemy_{i}"],
                    }
                )

            # Verify state
            assert interface.experiences_processed == 5
            assert len(core.short_term_memory) == 5

            # Consolidate
            consolidated = interface.consolidate_memories()
            assert consolidated > 0

            # Check metrics
            metrics = interface.get_memory_metrics()
            assert metrics["experiences_processed"] == 5
