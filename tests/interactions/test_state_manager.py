"""
Test suite for State Manager module.

Tests state transitions, persistence, and recovery for interaction engine.
"""

import pytest

pytestmark = pytest.mark.unit

from unittest.mock import Mock
from datetime import datetime

from src.interactions.interaction_engine_system.state_management.state_manager import (
    StateManager,
    StateUpdate,
    MemoryUpdate,
)
from src.interactions.interaction_engine_system.core.types import (
    InteractionContext,
    InteractionType,
    InteractionPriority,
    InteractionEngineConfig,
)


class TestStateUpdate:
    """Test StateUpdate dataclass."""

    def test_state_update_creation(self):
        """Test creating a state update."""
        update = StateUpdate(
            agent_id="agent1",
            state_type="mood",
            old_value=50,
            new_value=60,
            change_amount=10.0,
            change_reason="Test interaction",
        )
        
        assert update.agent_id == "agent1"
        assert update.state_type == "mood"
        assert update.old_value == 50
        assert update.new_value == 60
        assert update.change_amount == 10.0
        assert isinstance(update.timestamp, datetime)


class TestMemoryUpdate:
    """Test MemoryUpdate dataclass."""

    def test_memory_update_creation(self):
        """Test creating a memory update."""
        memory_item = {"memory_id": "mem1", "content": "Test memory"}
        update = MemoryUpdate(
            agent_id="agent1",
            memory_item=memory_item,
            memory_type="episodic",
            significance=0.8,
        )
        
        assert update.agent_id == "agent1"
        assert update.memory_item == memory_item
        assert update.memory_type == "episodic"
        assert update.significance == 0.8


class TestStateManager:
    """Test StateManager implementation."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return InteractionEngineConfig(
            memory_significance_threshold=0.5,
            memory_integration_enabled=True,
            auto_generate_memories=True,
        )

    @pytest.fixture
    def state_manager(self, config):
        """Create a fresh state manager."""
        return StateManager(config)

    def test_initialization(self, config):
        """Test state manager initialization."""
        sm = StateManager(config)
        
        assert sm.config == config
        assert sm.memory_manager is None
        assert sm.character_manager is None
        assert sm.pending_state_updates == {}
        assert sm.pending_memory_updates == {}

    def test_get_pending_updates_empty(self, state_manager):
        """Test getting pending updates when none exist."""
        updates = state_manager.get_pending_updates()
        
        assert updates["all_state_updates"] == {}
        assert updates["all_memory_updates"] == {}
        assert updates["relationship_changes"] == {}

    def test_get_state_statistics(self, state_manager):
        """Test getting state statistics."""
        # Add some stats
        state_manager.state_update_stats["total_updates"] = 10
        state_manager.state_update_stats["successful_updates"] = 8
        
        stats = state_manager.get_state_statistics()
        
        assert stats["total_updates"] == 10
        assert stats["successful_updates"] == 8


class TestStateManagerCalculations:
    """Test calculation methods."""

    @pytest.fixture
    def config(self):
        return InteractionEngineConfig()

    @pytest.fixture
    def state_manager(self, config):
        return StateManager(config)

    def test_calculate_interaction_significance(self, state_manager):
        """Test significance calculation."""
        context = InteractionContext(
            interaction_id="test",
            interaction_type=InteractionType.COMBAT,
            priority=InteractionPriority.CRITICAL,
            participants=["agent1", "agent2", "agent3"],
            location="arena",
        )
        
        significance = state_manager._calculate_interaction_significance(
            context, {"success": True}
        )
        
        assert 0 <= significance <= 1.0

    def test_calculate_base_relationship_change(self, state_manager):
        """Test base relationship change calculation."""
        combat_change = state_manager._calculate_base_relationship_change(
            InteractionType.COMBAT, {"success": True}
        )
        
        cooperation_change = state_manager._calculate_base_relationship_change(
            InteractionType.COOPERATION, {"success": True}
        )
        
        assert isinstance(combat_change, float)
        assert isinstance(cooperation_change, float)

    def test_calculate_base_relationship_change_failed(self, state_manager):
        """Test relationship change for failed interactions."""
        change = state_manager._calculate_base_relationship_change(
            InteractionType.COOPERATION, {"success": False}
        )
        
        assert isinstance(change, float)


class TestStateManagerEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def config(self):
        return InteractionEngineConfig()

    @pytest.fixture
    def state_manager(self, config):
        return StateManager(config)

    def test_state_update_with_metadata(self):
        """Test state update with metadata."""
        update = StateUpdate(
            agent_id="agent1",
            state_type="mood",
            old_value=50,
            new_value=60,
            change_amount=10.0,
            change_reason="Test",
            metadata={"source": "test", "version": 1},
        )
        
        assert update.metadata["source"] == "test"
        assert update.metadata["version"] == 1
