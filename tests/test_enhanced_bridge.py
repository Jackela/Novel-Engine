#!/usr/bin/env python3
"""
Enhanced Multi-Agent Bridge Test Suite
======================================

Comprehensive unit and integration tests for the refactored Enhanced Multi-Agent Bridge.
Tests component coordination, dialogue management, and performance optimization.
"""

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest
from enhanced_multi_agent_bridge import (
    BridgeConfiguration,
    EnhancedMultiAgentBridge,
    create_enhanced_bridge,
)

from src.bridge.types import RequestPriority


class TestBridgeConfiguration:
    """Test BridgeConfiguration functionality."""

    def test_default_configuration(self):
        """Test default bridge configuration."""
        config = BridgeConfiguration()

        assert config.enable_advanced_coordination is True
        assert config.enable_smart_batching is True
        assert config.enable_dialogue_system is True
        assert config.enable_performance_monitoring is True
        assert config.max_concurrent_agents == 20
        assert config.turn_timeout_seconds == 30
        assert config.llm_coordination is not None

    def test_custom_configuration(self):
        """Test custom bridge configuration."""
        config = BridgeConfiguration(
            enable_advanced_coordination=False,
            max_concurrent_agents=10,
            turn_timeout_seconds=60,
        )

        assert config.enable_advanced_coordination is False
        assert config.max_concurrent_agents == 10
        assert config.turn_timeout_seconds == 60


class TestEnhancedMultiAgentBridge:
    """Test Enhanced Multi-Agent Bridge functionality."""

    @pytest.fixture
    def mock_director_agent(self):
        """Create mock DirectorAgent."""
        mock_director = Mock()
        mock_director.agents = []
        mock_director.world_state = {"time": "day", "location": "test_area"}
        return mock_director

    @pytest.fixture
    def bridge_config(self):
        """Create test bridge configuration."""
        return BridgeConfiguration(max_concurrent_agents=5, turn_timeout_seconds=10)

    @pytest.fixture
    def enhanced_bridge(self, mock_director_agent, bridge_config):
        """Create Enhanced Multi-Agent Bridge for testing."""
        return EnhancedMultiAgentBridge(mock_director_agent, bridge_config)

    def test_bridge_initialization(self, enhanced_bridge):
        """Test bridge initialization."""
        assert enhanced_bridge._initialized is False
        assert enhanced_bridge.dialogue_manager is None
        assert enhanced_bridge.llm_coordinator is None
        assert enhanced_bridge.ai_orchestrator is None
        assert enhanced_bridge.coordination_engine is None
        assert len(enhanced_bridge.turn_history) == 0

    @pytest.mark.asyncio
    async def test_bridge_component_initialization(self, enhanced_bridge):
        """Test bridge component initialization."""
        success = await enhanced_bridge.initialize()

        assert success is True
        assert enhanced_bridge._initialized is True

    @pytest.mark.asyncio
    async def test_enhanced_turn_execution_no_agents(self, enhanced_bridge):
        """Test enhanced turn with no agents."""
        # Initialize bridge first
        await enhanced_bridge.initialize()

        # Execute turn with no agents
        result = await enhanced_bridge.enhanced_run_turn()

        assert result["success"] is True
        assert result["enhanced"] is True
        assert "timestamp" in result
        assert "components_used" in result

    @pytest.mark.asyncio
    async def test_enhanced_turn_execution_with_agents(
        self, enhanced_bridge, mock_director_agent
    ):
        """Test enhanced turn with mock agents."""
        # Add mock agents
        mock_agent1 = Mock()
        mock_agent1.agent_id = "agent_001"
        mock_agent2 = Mock()
        mock_agent2.agent_id = "agent_002"

        mock_director_agent.agents = [mock_agent1, mock_agent2]

        # Initialize bridge
        await enhanced_bridge.initialize()

        # Execute enhanced turn
        result = await enhanced_bridge.enhanced_run_turn()

        assert result["success"] is True
        assert "agent_results" in result
        assert "coordination_results" in result

    def test_request_priority_determination(self, enhanced_bridge):
        """Test request priority determination logic."""
        # Mock agent with no special properties
        mock_agent = Mock()
        context = {"active_dialogues": 0}

        priority = enhanced_bridge._determine_request_priority(mock_agent, context)
        assert priority == RequestPriority.NORMAL

        # Agent with active dialogues should get high priority
        context_with_dialogues = {"active_dialogues": 2}
        priority = enhanced_bridge._determine_request_priority(
            mock_agent, context_with_dialogues
        )
        assert priority == RequestPriority.HIGH

        # Critical agent should get high priority
        mock_critical_agent = Mock()
        mock_critical_agent.is_critical = True
        priority = enhanced_bridge._determine_request_priority(
            mock_critical_agent, context
        )
        assert priority == RequestPriority.HIGH

    @pytest.mark.asyncio
    async def test_bridge_status(self, enhanced_bridge):
        """Test bridge status reporting."""
        status = await enhanced_bridge.get_bridge_status()

        assert "initialized" in status
        assert "components" in status
        assert "metrics" in status
        assert "configuration" in status

        # Check component status
        components = status["components"]
        assert "dialogue_manager" in components
        assert "llm_coordinator" in components
        assert "ai_orchestrator" in components
        assert "coordination_engine" in components

    def test_execution_time_calculation(self, enhanced_bridge):
        """Test average execution time calculation."""
        # Add some mock turn history
        enhanced_bridge.turn_history = [
            {"execution_time": 1.0},
            {"execution_time": 2.0},
            {"execution_time": 3.0},
        ]

        avg_time = enhanced_bridge._calculate_avg_execution_time()
        assert avg_time == 2.0  # (1+2+3)/3

        # Test with empty history
        enhanced_bridge.turn_history = []
        avg_time = enhanced_bridge._calculate_avg_execution_time()
        assert avg_time == 0.0

    @pytest.mark.asyncio
    async def test_bridge_shutdown(self, enhanced_bridge):
        """Test bridge shutdown process."""
        # Mock components
        enhanced_bridge.llm_coordinator = Mock()
        enhanced_bridge.llm_coordinator.shutdown = AsyncMock()

        enhanced_bridge.ai_orchestrator = Mock()
        enhanced_bridge.ai_orchestrator.shutdown = AsyncMock()

        enhanced_bridge.coordination_engine = Mock()
        enhanced_bridge.coordination_engine.shutdown = AsyncMock()

        # Test shutdown
        await enhanced_bridge.shutdown()

        assert enhanced_bridge._shutdown_requested is True
        enhanced_bridge.llm_coordinator.shutdown.assert_called_once()
        enhanced_bridge.ai_orchestrator.shutdown.assert_called_once()
        enhanced_bridge.coordination_engine.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_building(self, enhanced_bridge, mock_director_agent):
        """Test enhanced context building."""
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent"

        # Mock dialogue manager
        enhanced_bridge.dialogue_manager = Mock()
        enhanced_bridge.dialogue_manager.get_agent_dialogues = AsyncMock(
            return_value=[]
        )

        context = await enhanced_bridge._build_enhanced_context(mock_agent)

        assert "agent_id" in context
        assert "world_state" in context
        assert "current_time" in context
        assert "active_dialogues" in context
        assert context["agent_id"] == "test_agent"
        assert context["world_state"] == mock_director_agent.world_state


class TestBridgeFactory:
    """Test bridge factory functionality."""

    @pytest.mark.asyncio
    async def test_create_enhanced_bridge_success(self):
        """Test successful bridge creation."""
        mock_director = Mock()
        mock_director.agents = []
        mock_director.world_state = {}

        config = BridgeConfiguration()

        bridge = await create_enhanced_bridge(mock_director, config)

        assert isinstance(bridge, EnhancedMultiAgentBridge)
        assert bridge._initialized is True

    @pytest.mark.asyncio
    async def test_create_enhanced_bridge_failure(self):
        """Test bridge creation failure handling."""
        mock_director = Mock()

        # Mock bridge initialize to return False
        with patch.object(EnhancedMultiAgentBridge, 'initialize', return_value=False):
            with pytest.raises(RuntimeError, match="Failed to initialize"):
                await create_enhanced_bridge(mock_director)


class TestBridgeIntegration:
    """Integration tests for bridge components."""

    @pytest.mark.asyncio
    async def test_dialogue_manager_integration(self):
        """Test dialogue manager integration."""
        mock_director = Mock()
        mock_director.agents = []
        mock_director.world_state = {}

        config = BridgeConfiguration(enable_dialogue_system=True)
        bridge = EnhancedMultiAgentBridge(mock_director, config)

        await bridge.initialize()

        # Test dialogue processing
        result = await bridge._process_active_dialogues()

        assert result["status"] == "success"
        assert "dialogue_status" in result
        assert "cleaned_up_dialogues" in result

    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring integration."""
        mock_director = Mock()
        mock_director.agents = []
        mock_director.world_state = {}

        config = BridgeConfiguration(enable_performance_monitoring=True)
        bridge = EnhancedMultiAgentBridge(mock_director, config)

        start_time = time.time()
        metrics = await bridge._analyze_turn_performance(start_time)

        assert "execution_time_seconds" in metrics
        assert "components_active" in metrics
        assert "timestamp" in metrics
        assert metrics["execution_time_seconds"] > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
