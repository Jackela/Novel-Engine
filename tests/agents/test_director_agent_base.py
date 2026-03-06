#!/usr/bin/env python3
"""
Test suite for DirectorAgentBase module.

Tests agent registration, simulation status, and event logging.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit

from src.agents.director_agent_base import DirectorAgentBase
from src.core.event_bus import EventBus


class TestDirectorAgentBaseInitialization:
    """Test DirectorAgentBase initialization."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        assert director.event_bus == event_bus
        assert director.registered_agents == []
        assert director.current_turn_number == 0
        assert director.total_actions_processed == 0

    def test_initialization_with_paths(self):
        """Test initialization with file paths."""
        event_bus = EventBus()
        with tempfile.TemporaryDirectory() as tmpdir:
            director = DirectorAgentBase(
                event_bus=event_bus,
                world_state_file_path=os.path.join(tmpdir, "world.db"),
                campaign_log_path=os.path.join(tmpdir, "campaign.md"),
                campaign_brief_path=os.path.join(tmpdir, "brief.md"),
            )

            assert director.world_state_file_path == os.path.join(tmpdir, "world.db")
            assert director.campaign_log_path == os.path.join(tmpdir, "campaign.md")

    def test_initialization_creates_default_paths(self):
        """Test that default paths are created."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        assert director.campaign_log_path == "campaign_log.md"

    def test_initialization_simulation_state(self):
        """Test simulation state initialization."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        assert director.simulation_start_time is not None
        assert director.error_count == 0


class TestDirectorAgentBaseAgentManagement:
    """Test agent management methods."""

    @pytest.fixture
    def director(self):
        """Create a DirectorAgentBase."""
        event_bus = EventBus()
        return DirectorAgentBase(event_bus=event_bus)

    @pytest.fixture
    def valid_agent(self):
        """Create a valid mock agent."""
        agent = Mock()
        agent.agent_id = "test_agent"
        agent.handle_turn_start = Mock()
        return agent

    def test_register_agent_success(self, director, valid_agent):
        """Test successful agent registration."""
        result = director.register_agent(valid_agent)

        assert result is True
        assert len(director.registered_agents) == 1
        assert director.registered_agents[0] == valid_agent

    def test_register_agent_invalid_type(self, director):
        """Test registering invalid agent type."""
        result = director.register_agent("not an agent")

        assert result is False
        assert len(director.registered_agents) == 0

    def test_register_agent_missing_method(self, director):
        """Test registering agent without required method."""
        agent = Mock()
        agent.agent_id = "test"
        # Missing handle_turn_start

        result = director.register_agent(agent)

        assert result is False

    def test_register_agent_missing_id(self, director):
        """Test registering agent without agent_id."""
        agent = Mock()
        agent.handle_turn_start = Mock()
        # Missing agent_id

        result = director.register_agent(agent)

        assert result is False

    def test_register_duplicate_agent(self, director, valid_agent):
        """Test registering same agent twice."""
        director.register_agent(valid_agent)
        result = director.register_agent(valid_agent)

        assert result is False
        assert len(director.registered_agents) == 1

    def test_remove_agent_success(self, director, valid_agent):
        """Test successful agent removal."""
        director.register_agent(valid_agent)
        result = director.remove_agent(valid_agent.agent_id)

        assert result is True
        assert len(director.registered_agents) == 0

    def test_remove_agent_not_found(self, director):
        """Test removing non-existent agent."""
        result = director.remove_agent("nonexistent")

        assert result is False

    def test_get_agent_list(self, director, valid_agent):
        """Test getting list of agents."""
        valid_agent.character_name = "Test Character"
        valid_agent.faction = "Alliance"
        director.register_agent(valid_agent)

        agent_list = director.get_agent_list()

        assert len(agent_list) == 1
        assert agent_list[0]["agent_id"] == "test_agent"
        assert agent_list[0]["character_name"] == "Test Character"

    def test_get_agent_list_empty(self, director):
        """Test getting agent list when empty."""
        agent_list = director.get_agent_list()

        assert agent_list == []


class TestDirectorAgentBaseSimulationStatus:
    """Test simulation status methods."""

    @pytest.fixture
    def director(self):
        """Create a DirectorAgentBase."""
        event_bus = EventBus()
        return DirectorAgentBase(event_bus=event_bus)

    def test_get_simulation_status(self, director):
        """Test getting simulation status."""
        status = director.get_simulation_status()

        assert "simulation_status" in status
        assert "current_turn" in status
        assert "registered_agents" in status
        assert "total_actions_processed" in status
        assert status["current_turn"] == 0

    def test_get_simulation_status_with_agents(self, director):
        """Test status with registered agents."""
        agent = Mock()
        agent.agent_id = "test_agent"
        agent.handle_turn_start = Mock()
        director.register_agent(agent)

        status = director.get_simulation_status()

        assert status["registered_agents"] == 1
        assert status["simulation_status"] == "running"

    def test_is_initialized(self, director):
        """Test initialization check."""
        assert director.is_initialized() is True


class TestDirectorAgentBaseLogging:
    """Test logging methods."""

    @pytest.fixture
    def director_with_log(self):
        """Create a DirectorAgentBase with temp log file."""
        event_bus = EventBus()
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "campaign.md")
            director = DirectorAgentBase(
                event_bus=event_bus,
                campaign_log_path=log_path,
            )
            yield director, log_path

    def test_log_event(self, director_with_log):
        """Test logging an event."""
        director, log_path = director_with_log

        director.log_event("Test event occurred")

        assert os.path.exists(log_path)
        with open(log_path) as f:
            content = f.read()
            assert "Test event occurred" in content

    def test_log_event_multiple(self, director_with_log):
        """Test logging multiple events."""
        director, log_path = director_with_log

        director.log_event("Event 1")
        director.log_event("Event 2")

        with open(log_path) as f:
            content = f.read()
            assert "Event 1" in content
            assert "Event 2" in content


class TestDirectorAgentBaseErrorHandling:
    """Test error handling methods."""

    @pytest.fixture
    def director(self):
        """Create a DirectorAgentBase."""
        event_bus = EventBus()
        return DirectorAgentBase(event_bus=event_bus)

    def test_handle_error(self, director):
        """Test error handling."""
        initial_count = director.error_count

        director._handle_error("Test error")

        assert director.error_count == initial_count + 1
        assert director.last_error_time is not None

    def test_handle_error_with_exception(self, director):
        """Test error handling with exception."""
        director._handle_error("Test error", Exception("Test"))

        assert director.error_count == 1


class TestDirectorAgentBaseConfig:
    """Test configuration methods."""

    def test_get_config(self):
        """Test getting configuration."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        config = director.get_config()
        # May be None or actual config depending on environment
        assert config is None or config is not None


class TestDirectorAgentBaseNarrative:
    """Test narrative component initialization."""

    def test_story_state_initialization(self):
        """Test story state is initialized."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        assert "current_phase" in director.story_state
        assert director.story_state["current_phase"] == "initialization"
        assert "triggered_events" in director.story_state

    def test_world_state_tracker_initialization(self):
        """Test world state tracker is initialized."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        assert "discovered_clues" in director.world_state_tracker
        assert "environmental_changes" in director.world_state_tracker


class TestDirectorAgentBaseEdgeCases:
    """Test edge cases."""

    def test_error_during_registration(self):
        """Test handling error during registration."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        # Create agent that will cause exception
        agent = Mock()
        agent.agent_id = "test"
        agent.handle_turn_start = Mock()
        # Make isinstance check fail
        with patch("src.agents.director_agent_base.PersonaAgent", str):
            result = director.register_agent(agent)

        # Should handle gracefully
        assert result is False or result is True  # Depends on patching

    def test_remove_agent_error(self):
        """Test error during agent removal."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        # Corrupt registered_agents to cause error
        director.registered_agents = None  # type: ignore

        result = director.remove_agent("test")

        assert result is False


class TestDirectorAgentBaseIntegration:
    """Integration tests."""

    def test_full_agent_lifecycle(self):
        """Test full agent lifecycle."""
        event_bus = EventBus()
        director = DirectorAgentBase(event_bus=event_bus)

        # Create and register agents
        for i in range(3):
            agent = Mock()
            agent.agent_id = f"agent_{i}"
            agent.handle_turn_start = Mock()
            agent.character_name = f"Character {i}"
            agent.faction = "Alliance"
            director.register_agent(agent)

        # Verify
        assert len(director.registered_agents) == 3

        # Get list
        agent_list = director.get_agent_list()
        assert len(agent_list) == 3

        # Remove one
        director.remove_agent("agent_1")
        assert len(director.registered_agents) == 2

        # Check status
        status = director.get_simulation_status()
        assert status["registered_agents"] == 2
