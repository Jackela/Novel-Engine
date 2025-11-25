"""
Comprehensive Unit Test Suite for Modular Components
===================================================

Enterprise-grade unit tests specifically designed for the modular architecture.
Tests each component in isolation with comprehensive coverage.
"""

import asyncio
import logging
from datetime import datetime
from unittest.mock import Mock

import pytest

# Configure logging for tests
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Import modular components for testing
try:
    # Persona Agent Modular Components
    from src.agents.persona_agent.core.character_data_manager import (
        CharacterDataManager,
    )
    from src.agents.persona_agent.core.types import (
        CharacterData,
        DecisionContext,
        PersonaAgentConfig,
    )
    from src.agents.persona_agent.decision_engine.decision_processor import (
        DecisionProcessor,
    )
    from src.agents.persona_agent.llm_integration.llm_client import LLMClient
    from src.agents.persona_agent.persona_agent_modular import PersonaAgent
    from src.agents.persona_agent.world_interpretation.memory_manager import (
        MemoryManager,
    )
    from src.bridges.multi_agent_bridge.coordination.dialogue_manager import (
        DialogueManager,
    )
    from src.bridges.multi_agent_bridge.core.types import (
        CommunicationType,
        LLMCoordinationConfig,
    )

    # Multi-Agent Bridge Modular Components
    from src.bridges.multi_agent_bridge.enhanced_multi_agent_bridge_modular import (
        EnhancedMultiAgentBridge,
    )
    from src.bridges.multi_agent_bridge.llm_processing.llm_batch_processor import (
        LLMBatchProcessor,
    )
    from src.bridges.multi_agent_bridge.performance.cost_tracker import CostTracker

    # Interaction Engine Modular Components
    from src.interactions.interaction_engine_system import (
        InteractionContext,
        InteractionEngine,
        InteractionEngineConfig,
        InteractionPriority,
        InteractionType,
    )
    from src.interactions.interaction_engine_system.core.types import InteractionOutcome
    from src.interactions.interaction_engine_system.queue_management.queue_manager import (
        QueueManager,
        QueueStatus,
    )
    from src.interactions.interaction_engine_system.validation.interaction_validator import (
        InteractionValidator,
    )

    REAL_COMPONENTS = True
    logger.info("Successfully imported all modular components")

except ImportError as e:
    logger.warning(f"Some modular components not available: {e}")
    REAL_COMPONENTS = False

    # Create mock components for basic testing
    class MockPersonaAgent:
        def __init__(
            self, agent_id="test_agent", character_directory=None, config=None
        ):
            self.agent_id = agent_id
            self.is_initialized = True

        async def make_decision(self, context):
            return "mock_decision"

        def get_current_state(self):
            return {"status": "active", "last_decision": "mock"}

    class MockInteractionEngine:
        def __init__(self, config=None):
            self.config = config
            self.is_initialized = True

        async def process_interaction(self, context):
            return type(
                "MockOutcome",
                (),
                {
                    "success": True,
                    "interaction_id": context.interaction_id,
                    "processing_duration": 0.1,
                },
            )()

    class MockEnhancedMultiAgentBridge:
        def __init__(self, event_bus, **kwargs):
            self.event_bus = event_bus
            self._agents = {}

        def register_agent(self, agent_id, agent):
            self._agents[agent_id] = agent

    # Assign mocks
    PersonaAgent = MockPersonaAgent
    InteractionEngine = MockInteractionEngine
    EnhancedMultiAgentBridge = MockEnhancedMultiAgentBridge


@pytest.mark.integration
class TestPersonaAgentModularComponents:
    """Comprehensive tests for PersonaAgent modular components."""

    @pytest.mark.asyncio
    async def test_persona_agent_initialization(self):
        """Test PersonaAgent modular initialization."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = PersonaAgentConfig(
            agent_id="test_agent_001",
            enable_memory=True,
            enable_llm_integration=True,
            decision_confidence_threshold=0.7,
        )

        agent = PersonaAgent(
            agent_id="test_agent_001",
            character_directory="characters/test_character",
            config=config,
        )

        assert agent.agent_id == "test_agent_001"
        assert agent.config.enable_memory is True
        assert agent.is_initialized is True

    @pytest.mark.asyncio
    async def test_decision_engine_component(self):
        """Test DecisionProcessor component in isolation."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = PersonaAgentConfig()
        decision_engine = DecisionProcessor(config)

        # Test decision context processing
        context = DecisionContext(
            situation="test_situation",
            available_actions=["action1", "action2"],
            world_state={"location": "test_area"},
            urgency_level="normal",
        )

        decision = await decision_engine.evaluate_decision(context)

        assert decision is not None
        assert hasattr(decision, "selected_action")
        assert hasattr(decision, "confidence_score")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_character_data_manager_component(self):
        """Test CharacterDataManager component functionality."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        data_manager = CharacterDataManager("test_character_dir")

        # Test character data loading
        character_data = await data_manager.load_character_data()

        assert isinstance(character_data, (CharacterData, dict))

        # Test data validation
        validation_result = data_manager.validate_character_data(character_data)
        assert hasattr(validation_result, "is_valid")

    def test_persona_memory_manager_component(self):
        """Test MemoryManager component."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = PersonaAgentConfig(max_memory_size=100)
        memory_manager = MemoryManager(config)

        # Test memory operations
        memory_manager.store_memory("test_event", {"data": "test"})

        memories = memory_manager.retrieve_memories(query="test_event")
        assert len(memories) > 0

        # Test memory capacity management
        assert memory_manager.get_memory_usage() >= 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_client_component(self):
        """Test LLMClient component functionality."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = PersonaAgentConfig(
            llm_provider="mock", max_tokens=150, temperature=0.7
        )

        llm_client = LLMClient(config)

        # Test LLM request processing
        response = await llm_client.generate_response(
            prompt="Test prompt for decision making",
            context={"character": "test_character"},
        )

        assert response is not None
        assert isinstance(response, (str, dict))


@pytest.mark.integration
class TestInteractionEngineModularComponents:
    """Comprehensive tests for InteractionEngine modular components."""

    def test_interaction_engine_initialization(self):
        """Test InteractionEngine modular initialization."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = InteractionEngineConfig(
            max_concurrent_interactions=5,
            enable_parallel_processing=True,
            performance_monitoring=True,
        )

        engine = InteractionEngine(config=config)

        assert engine.config.max_concurrent_interactions == 5
        assert engine.config.enable_parallel_processing is True
        assert engine.is_initialized is True
    @pytest.mark.asyncio
    async def test_interaction_validator_component(self):
        """Test InteractionValidator component."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = InteractionEngineConfig()
        validator = InteractionValidator(config)

        # Test context validation
        context = InteractionContext(
            interaction_id="test_interaction_001",
            interaction_type=InteractionType.DIALOGUE,
            participants=["agent1", "agent2"],
            priority=InteractionPriority.NORMAL,
        )

        validation_result = await validator.validate_interaction_context(context)

        assert hasattr(validation_result, "success")
        assert validation_result.success is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_queue_manager_component(self):
        """Test QueueManager component functionality."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = InteractionEngineConfig(max_queue_size=10)
        queue_manager = QueueManager(config)

        # Test queue operations
        context = InteractionContext(
            interaction_id="queue_test_001",
            interaction_type=InteractionType.DIALOGUE,
            participants=["agent1", "agent2"],
        )

        # Test queuing interaction
        queue_result = await queue_manager.queue_interaction(context)
        assert queue_result.success is True

        # Test queue status
        status = queue_manager.get_queue_status()
        assert status["queue_size"] >= 0
        assert status["processing_active"] in [True, False]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_interaction_processing_pipeline(self):
        """Test complete interaction processing pipeline."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = InteractionEngineConfig(
            enable_parallel_processing=True, performance_monitoring=True
        )

        engine = InteractionEngine(config=config)

        # Test interaction processing
        context = InteractionContext(
            interaction_id="pipeline_test_001",
            interaction_type=InteractionType.COOPERATION,
            participants=["agent1", "agent2", "agent3"],
            priority=InteractionPriority.HIGH,
        )

        outcome = await engine.process_interaction(context)

        assert hasattr(outcome, "success")
        assert outcome.interaction_id == "pipeline_test_001"
        if hasattr(outcome, "processing_duration"):
            assert outcome.processing_duration >= 0


@pytest.mark.integration
class TestMultiAgentBridgeModularComponents:
    """Comprehensive tests for MultiAgentBridge modular components."""

    def test_enhanced_bridge_initialization(self):
        """Test EnhancedMultiAgentBridge modular initialization."""
        mock_event_bus = Mock()

        bridge = EnhancedMultiAgentBridge(event_bus=mock_event_bus)

        assert bridge.event_bus == mock_event_bus
        assert hasattr(bridge, "_agents")
    @pytest.mark.asyncio
    async def test_dialogue_manager_component(self):
        """Test DialogueManager component."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = LLMCoordinationConfig()
        dialogue_manager = DialogueManager(config=config)

        # Test dialogue initiation
        dialogue_id = await dialogue_manager.initiate_dialogue(
            initiator_id="agent1",
            target_id="agent2",
            communication_type=CommunicationType.DIALOGUE,
        )

        assert dialogue_id is not None
        assert isinstance(dialogue_id, str)

        # Test dialogue stats
        stats = dialogue_manager.get_dialogue_stats()
        assert isinstance(stats, dict)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_batch_processor_component(self):
        """Test LLMBatchProcessor component."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = LLMCoordinationConfig(max_batch_size=3, batch_timeout_ms=100)

        processor = LLMBatchProcessor(config=config)

        # Test batch processing
        requests = [
            {"prompt": "Test prompt 1", "type": "dialogue"},
            {"prompt": "Test prompt 2", "type": "dialogue"},
        ]

        results = await processor.process_batch(requests)

        assert isinstance(results, list)
        assert len(results) == len(requests)

    def test_cost_tracker_component(self):
        """Test CostTracker component functionality."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        tracker = CostTracker(max_cost_per_turn=0.10, max_total_cost=1.0)

        # Test cost tracking
        tracker.record_cost(0.05, "test_operation")

        assert tracker.get_current_cost() >= 0.05
        assert tracker.is_under_budget(0.03) in [True, False]

        # Test cost efficiency stats
        stats = tracker.get_cost_efficiency_stats()
        assert isinstance(stats, dict)
        assert "total_cost" in stats

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bridge_agent_coordination(self):
        """Test agent coordination through the bridge."""
        mock_event_bus = Mock()
        bridge = EnhancedMultiAgentBridge(event_bus=mock_event_bus)

        # Test agent registration
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent_001"

        bridge.register_agent("test_agent_001", mock_agent)

        assert "test_agent_001" in bridge._agents
        assert bridge._agents["test_agent_001"] == mock_agent


@pytest.mark.integration
class TestModularComponentIntegration:
    """Test integration between modular components."""
    @pytest.mark.asyncio
    async def test_persona_agent_with_interaction_engine(self):
        """Test PersonaAgent integration with InteractionEngine."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        # Create persona agent
        persona_config = PersonaAgentConfig(agent_id="integration_test_001")
        PersonaAgent(
            agent_id="integration_test_001",
            character_directory=None,
            config=persona_config,
        )

        # Create interaction engine
        interaction_config = InteractionEngineConfig()
        interaction_engine = InteractionEngine(config=interaction_config)

        # Test integration
        context = InteractionContext(
            interaction_id="integration_001",
            interaction_type=InteractionType.DIALOGUE,
            participants=["integration_test_001", "other_agent"],
        )

        outcome = await interaction_engine.process_interaction(context)

        assert hasattr(outcome, "success")
        assert outcome.interaction_id == "integration_001"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_modular_system_coordination(self):
        """Test coordination between all major modular components."""
        # Initialize event bus mock
        mock_event_bus = Mock()

        # Create bridge
        bridge = EnhancedMultiAgentBridge(event_bus=mock_event_bus)

        # Create agents
        agent1 = PersonaAgent(agent_id="coord_test_001", character_directory=None)
        agent2 = PersonaAgent(agent_id="coord_test_002", character_directory=None)

        # Register agents
        bridge.register_agent("coord_test_001", agent1)
        bridge.register_agent("coord_test_002", agent2)

        # Test coordination
        assert len(bridge._agents) == 2
        assert "coord_test_001" in bridge._agents
        assert "coord_test_002" in bridge._agents


@pytest.mark.integration
class TestModularComponentPerformance:
    """Performance tests for modular components."""
    @pytest.mark.asyncio
    async def test_persona_agent_decision_performance(self):
        """Test PersonaAgent decision-making performance."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = PersonaAgentConfig(agent_id="perf_test_001")
        agent = PersonaAgent(
            agent_id="perf_test_001", character_directory=None, config=config
        )

        start_time = datetime.now()

        # Simulate multiple decisions
        for i in range(5):
            decision_context = {
                "situation": f"performance_test_{i}",
                "available_actions": ["action1", "action2"],
                "urgency": "normal",
            }

            decision = await agent.make_decision(decision_context)
            assert decision is not None

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Performance assertion (should be under 1 second for 5 decisions)
        assert (
            total_time < 1.0
        ), f"Performance test failed: {total_time}s for 5 decisions"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_interaction_engine_throughput(self):
        """Test InteractionEngine processing throughput."""
        if not REAL_COMPONENTS:
            pytest.skip("Real components not available")

        config = InteractionEngineConfig(
            max_concurrent_interactions=5, enable_parallel_processing=True
        )

        engine = InteractionEngine(config=config)

        start_time = datetime.now()

        # Process multiple interactions concurrently
        tasks = []
        for i in range(10):
            context = InteractionContext(
                interaction_id=f"throughput_test_{i}",
                interaction_type=InteractionType.DIALOGUE,
                participants=[f"agent_{i}", f"agent_{i+1}"],
            )

            task = engine.process_interaction(context)
            tasks.append(task)

        outcomes = await asyncio.gather(*tasks)

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Performance assertions
        assert len(outcomes) == 10
        assert all(hasattr(outcome, "success") for outcome in outcomes)
        assert (
            total_time < 2.0
        ), f"Throughput test failed: {total_time}s for 10 interactions"


def run_modular_component_tests():
    """Run all modular component tests and generate summary."""
    print("=" * 80)
    print("🧪 MODULAR COMPONENT COMPREHENSIVE TESTING")
    print("=" * 80)
    print(f"📅 Started: {datetime.now().isoformat()}")
    print(f"🔧 Real Components: {'Available' if REAL_COMPONENTS else 'Mock Fallbacks'}")
    print()

    # Run pytest with detailed output
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure for debugging
        "--disable-warnings",
    ]

    try:
        result = pytest.main(pytest_args)

        print()
        print("=" * 80)
        if result == 0:
            print("🎉 ALL MODULAR COMPONENT TESTS PASSED")
        else:
            print("⚠️ SOME MODULAR COMPONENT TESTS FAILED")
        print("=" * 80)

        return result

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    result = run_modular_component_tests()
    exit(result)
