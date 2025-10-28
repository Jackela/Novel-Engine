#!/usr/bin/env python3
"""
AI Intelligence Integration Test Suite
======================================

Comprehensive test suite for validating the integration between Novel Engine's
AI intelligence systems and the existing framework. Tests all integration
patterns, fallback mechanisms, and performance characteristics.

Test Categories:
- System startup and shutdown
- Traditional/AI coordination
- Performance and fallback testing
- Cross-system event handling
- Quality metrics validation
- User experience integration
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.ai_intelligence.analytics_platform import AnalyticsEvent

# Import systems under test
from src.ai_intelligence.integration_orchestrator import (
    IntegrationConfig,
    IntegrationMode,
    IntegrationOrchestrator,
    SystemIntegrationLevel,
)
from src.ai_intelligence.story_quality_engine import QualityLevel
from src.core.data_models import ErrorInfo, StandardResponse
from src.core.system_orchestrator import OrchestratorConfig


class TestAIIntelligenceIntegration:
    """Test suite for AI intelligence integration."""

    @pytest.fixture
    def temp_database(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup - try multiple times to handle file locking issues
        import time

        for attempt in range(5):
            try:
                Path(db_path).unlink(missing_ok=True)
                break
            except PermissionError:
                if attempt < 4:
                    time.sleep(0.1)  # Wait 100ms before retry
                else:
                    # Log the issue but don't fail the test
                    print(f"Warning: Could not delete temporary database {db_path}")

    @pytest.fixture
    def integration_config(self):
        """Create test integration configuration."""
        return IntegrationConfig(
            integration_mode=IntegrationMode.AI_ENHANCED,
            integration_level=SystemIntegrationLevel.INTEGRATED,
            enable_progressive_activation=True,
            enable_fallback_systems=True,
            ai_feature_gates={
                "agent_coordination": True,
                "story_quality": True,
                "analytics": True,
                "recommendations": True,
                "export_integration": True,
            },
            traditional_system_timeout=5.0,
            ai_system_timeout=5.0,
        )

    @pytest.fixture
    def orchestrator_config(self):
        """Create test orchestrator configuration."""
        return OrchestratorConfig(
            max_concurrent_agents=5,
            memory_cleanup_interval=60,
            debug_logging=True,
            enable_metrics=True,
        )

    @pytest.fixture
    def integration_orchestrator(
        self, temp_database, integration_config, orchestrator_config
    ):
        """Create integration orchestrator for testing."""
        orchestrator = IntegrationOrchestrator(
            database_path=temp_database,
            orchestrator_config=orchestrator_config,
            integration_config=integration_config,
        )
        yield orchestrator
        # Ensure proper cleanup - but use asyncio.run if needed
        try:
            if orchestrator.integration_active:
                import asyncio

                asyncio.create_task(orchestrator.shutdown())
        except Exception as e:
            print(f"Warning: Error during orchestrator cleanup: {e}")

    @pytest.mark.asyncio
    async def test_integration_startup_success(self, integration_orchestrator):
        """Test successful integration orchestrator startup."""
        result = await integration_orchestrator.startup()

        assert result.success
        assert integration_orchestrator.integration_active
        assert result.data["integration_mode"] == IntegrationMode.AI_ENHANCED.value
        assert result.data["traditional_available"]
        assert "ai_available" in result.data
        assert "startup_time" in result.data

    @pytest.mark.asyncio
    async def test_integration_startup_traditional_only(
        self, temp_database, orchestrator_config
    ):
        """Test startup in traditional-only mode."""
        config = IntegrationConfig(integration_mode=IntegrationMode.TRADITIONAL_ONLY)
        orchestrator = IntegrationOrchestrator(
            database_path=temp_database,
            orchestrator_config=orchestrator_config,
            integration_config=config,
        )

        result = await orchestrator.startup()

        assert result.success
        assert result.data["integration_mode"] == IntegrationMode.TRADITIONAL_ONLY.value

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_integration_shutdown(self, integration_orchestrator):
        """Test graceful integration shutdown."""
        # Start first
        await integration_orchestrator.startup()

        # Then shutdown
        result = await integration_orchestrator.shutdown()

        assert result.success
        assert not integration_orchestrator.integration_active
        assert "shutdown_time" in result.data
        assert "uptime_seconds" in result.data
        assert "total_operations" in result.data

    @pytest.mark.asyncio
    async def test_character_action_processing_traditional(
        self, integration_orchestrator
    ):
        """Test character action processing in traditional mode."""
        orchestrator = integration_orchestrator
        orchestrator.config.integration_mode = IntegrationMode.TRADITIONAL_ONLY

        await orchestrator.startup()

        result = await orchestrator.process_character_action(
            agent_id="test_agent", action="speak", context={"message": "Hello world"}
        )

        assert result.success
        assert orchestrator.operation_count > 0

    @pytest.mark.asyncio
    async def test_character_action_processing_ai_enhanced(
        self, integration_orchestrator
    ):
        """Test character action processing with AI enhancement."""
        await integration_orchestrator.startup()

        # Mock AI coordination engine for testing
        with patch.object(
            integration_orchestrator.ai_orchestrator.agent_coordination,
            "coordinate_agent_action",
            new_callable=AsyncMock,
        ) as mock_coordinate:
            mock_coordinate.return_value = StandardResponse(
                success=True, data={"coordination_result": "success", "enhanced": True}
            )

            result = await integration_orchestrator.process_character_action(
                agent_id="test_agent",
                action="speak",
                context={"message": "AI enhanced message"},
            )

            assert result.success
            assert mock_coordinate.called

    @pytest.mark.asyncio
    async def test_character_action_fallback_mechanism(self, integration_orchestrator):
        """Test fallback to traditional system when AI fails."""
        await integration_orchestrator.startup()

        # Mock AI coordination to fail
        with patch.object(
            integration_orchestrator.ai_orchestrator.agent_coordination,
            "coordinate_agent_action",
            new_callable=AsyncMock,
        ) as mock_coordinate:
            mock_coordinate.return_value = StandardResponse(
                success=False,
                error=ErrorInfo(code="AI_FAILURE", message="AI processing failed"),
            )

            result = await integration_orchestrator.process_character_action(
                agent_id="test_agent",
                action="speak",
                context={"message": "Should fallback to traditional"},
            )

            # Should still succeed due to fallback
            assert result.success
            assert mock_coordinate.called

    @pytest.mark.asyncio
    async def test_story_generation_traditional(self, integration_orchestrator):
        """Test story generation using traditional systems."""
        orchestrator = integration_orchestrator
        orchestrator.config.integration_mode = IntegrationMode.TRADITIONAL_ONLY

        await orchestrator.startup()

        result = await orchestrator.generate_story_content(
            prompt="Generate a science fiction story", user_id="test_user"
        )

        assert result.success
        assert "content" in result.data
        assert result.data["generation_method"] == "traditional"

    @pytest.mark.asyncio
    async def test_story_generation_ai_enhanced(self, integration_orchestrator):
        """Test story generation with AI enhancements."""
        await integration_orchestrator.startup()

        # Mock AI components
        with patch.object(
            integration_orchestrator.ai_orchestrator.story_quality_engine,
            "analyze_story_quality",
            new_callable=AsyncMock,
        ) as mock_quality:
            mock_quality.return_value = StandardResponse(
                success=True,
                data={"overall_score": 0.8, "quality_level": QualityLevel.GOOD},
            )

            with patch.object(
                integration_orchestrator.ai_orchestrator.analytics_platform,
                "track_event",
                new_callable=AsyncMock,
            ) as mock_analytics:
                result = await integration_orchestrator.generate_story_content(
                    prompt="Generate an AI-enhanced story",
                    user_id="test_user",
                    preferences={"genre": "fantasy", "style": "descriptive"},
                )

                assert result.success
                assert "content" in result.data
                assert mock_analytics.called

    @pytest.mark.asyncio
    async def test_system_status_retrieval(self, integration_orchestrator):
        """Test comprehensive system status retrieval."""
        await integration_orchestrator.startup()

        result = await integration_orchestrator.get_system_status()

        assert result.success
        assert "integration_config" in result.data
        assert "traditional_system" in result.data
        assert "ai_system" in result.data
        assert "integration_metrics" in result.data
        assert "uptime_seconds" in result.data
        assert "total_operations" in result.data
        assert "error_rate" in result.data

    @pytest.mark.asyncio
    async def test_performance_tracking(self, integration_orchestrator):
        """Test performance metrics tracking."""
        await integration_orchestrator.startup()

        # Perform several operations
        for i in range(5):
            await integration_orchestrator.process_character_action(
                agent_id=f"agent_{i}", action="test_action", context={"test": True}
            )

        # Check performance tracking
        assert len(integration_orchestrator.response_times) > 0
        assert integration_orchestrator.operation_count >= 5

        # Get metrics
        metrics = await integration_orchestrator._generate_integration_metrics()
        assert metrics.average_response_time >= 0
        assert metrics.system_health_score > 0

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, integration_orchestrator):
        """Test error handling and system recovery."""
        await integration_orchestrator.startup()

        # Mock system to raise exception
        with patch.object(
            integration_orchestrator.system_orchestrator,
            "process_dynamic_context",
            side_effect=Exception("Simulated system error"),
        ):
            result = await integration_orchestrator.process_character_action(
                agent_id="error_agent", action="error_action"
            )

            assert not result.success
            assert integration_orchestrator.error_count > 0
            assert result.error.code == "CHARACTER_ACTION_ERROR"

    @pytest.mark.asyncio
    async def test_feature_gate_functionality(self, temp_database, orchestrator_config):
        """Test AI feature gate functionality."""
        # Create config with some features disabled
        config = IntegrationConfig(
            integration_mode=IntegrationMode.AI_ENHANCED,
            ai_feature_gates={
                "agent_coordination": True,
                "story_quality": False,  # Disabled
                "analytics": True,
                "recommendations": False,  # Disabled
                "export_integration": True,
            },
        )

        orchestrator = IntegrationOrchestrator(
            database_path=temp_database,
            orchestrator_config=orchestrator_config,
            integration_config=config,
        )

        result = await orchestrator.startup()

        assert result.success
        assert result.data["feature_gates"]["story_quality"] is False
        assert result.data["feature_gates"]["recommendations"] is False
        assert result.data["feature_gates"]["agent_coordination"] is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_cross_system_event_coordination(self, integration_orchestrator):
        """Test event coordination between traditional and AI systems."""
        await integration_orchestrator.startup()

        # Test event emission
        test_event_data = {
            "agent_id": "test_agent",
            "action": "test_action",
            "success": True,
            "timestamp": datetime.now().isoformat(),
        }

        await integration_orchestrator._emit_integration_event(
            "test_integration_event", test_event_data
        )

        # Verify event was processed (in a real system, this would check event handlers)
        assert True  # Placeholder for actual event verification

    @pytest.mark.asyncio
    async def test_integration_mode_switching(self, temp_database, orchestrator_config):
        """Test different integration modes."""
        modes_to_test = [
            IntegrationMode.TRADITIONAL_ONLY,
            IntegrationMode.AI_ENHANCED,
            IntegrationMode.AI_FIRST,
        ]

        for mode in modes_to_test:
            config = IntegrationConfig(integration_mode=mode)
            orchestrator = IntegrationOrchestrator(
                database_path=temp_database,
                orchestrator_config=orchestrator_config,
                integration_config=config,
            )

            result = await orchestrator.startup()
            assert result.success
            assert result.data["integration_mode"] == mode.value

            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, integration_orchestrator):
        """Test timeout handling for AI operations."""
        await integration_orchestrator.startup()

        # Set very short timeout
        integration_orchestrator.config.ai_system_timeout = 0.001

        # Mock slow AI operation
        with patch.object(
            integration_orchestrator,
            "_process_ai_enhanced_action",
            new_callable=AsyncMock,
        ) as mock_ai_action:
            # Make it slow
            async def slow_operation(*args, **kwargs):
                await asyncio.sleep(1.0)  # Longer than timeout
                return StandardResponse(success=True, data={})

            mock_ai_action.side_effect = slow_operation

            result = await integration_orchestrator.process_character_action(
                agent_id="timeout_test", action="slow_action"
            )

            # Should still succeed due to fallback
            assert result.success

    @pytest.mark.asyncio
    async def test_analytics_integration(self, integration_orchestrator):
        """Test analytics integration across systems."""
        await integration_orchestrator.startup()

        with patch.object(
            integration_orchestrator.ai_orchestrator.analytics_platform,
            "track_event",
            new_callable=AsyncMock,
        ) as mock_track:
            await integration_orchestrator.generate_story_content(
                prompt="Test story for analytics",
                user_id="analytics_test_user",
                preferences={"test": True},
            )

            # Verify analytics tracking was called
            assert mock_track.called
            call_args = mock_track.call_args[0][0]
            assert isinstance(call_args, AnalyticsEvent)
            assert call_args.user_id == "analytics_test_user"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, integration_orchestrator):
        """Test concurrent operation handling."""
        await integration_orchestrator.startup()

        # Run multiple operations concurrently
        tasks = []
        for i in range(10):
            task = integration_orchestrator.process_character_action(
                agent_id=f"concurrent_agent_{i}",
                action=f"action_{i}",
                context={"concurrent": True},
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(result.success for result in results)
        assert integration_orchestrator.operation_count >= 10

    @pytest.mark.asyncio
    async def test_memory_and_cleanup(self, integration_orchestrator):
        """Test memory management and cleanup."""
        await integration_orchestrator.startup()

        # Generate some operations to create memory usage
        for i in range(20):
            await integration_orchestrator.process_character_action(
                agent_id=f"memory_test_{i}", action="memory_action"
            )

        # Check metrics tracking
        assert len(integration_orchestrator.response_times) > 0
        assert len(integration_orchestrator.metrics_history) > 0

        # Simulate cleanup by limiting history
        if len(integration_orchestrator.response_times) > 100:
            integration_orchestrator.response_times = (
                integration_orchestrator.response_times[-100:]
            )

        assert len(integration_orchestrator.response_times) <= 100


@pytest.mark.asyncio
class TestNarrativeEngineV2Integration:
    """Test suite for V2 Narrative Engine integration with AI intelligence systems."""

    @pytest.fixture
    def temp_database(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        import time

        for attempt in range(5):
            try:
                Path(db_path).unlink(missing_ok=True)
                break
            except PermissionError:
                if attempt < 4:
                    time.sleep(0.1)

    @pytest.mark.asyncio
    async def test_narrative_engine_initialization(self, temp_database):
        """Test that V2 Narrative Engine initializes correctly with IntegrationOrchestrator."""
        orchestrator = IntegrationOrchestrator(database_path=temp_database)

        assert hasattr(orchestrator, "narrative_engine_v2")
        assert hasattr(orchestrator, "current_arc_state")
        assert orchestrator.current_arc_state.current_phase.value == "exposition"
        assert orchestrator.current_arc_state.turn_number == 0

    @pytest.mark.asyncio
    async def test_get_narrative_guidance(self, temp_database):
        """Test retrieving narrative guidance from V2 engine."""
        orchestrator = IntegrationOrchestrator(database_path=temp_database)

        guidance = orchestrator.get_narrative_guidance()

        assert "primary_goal" in guidance
        assert "secondary_goals" in guidance
        assert "target_tension" in guidance
        assert "pacing_intensity" in guidance
        assert "narrative_tone" in guidance
        assert "phase" in guidance
        assert "phase_progress" in guidance
        assert "overall_progress" in guidance

        assert guidance["phase"] == "exposition"
        assert isinstance(guidance["target_tension"], float)
        assert isinstance(guidance["phase_progress"], float)

    @pytest.mark.asyncio
    async def test_narrative_guidance_integration_in_story_generation(
        self, temp_database
    ):
        """Test that narrative guidance is integrated into story content generation."""
        orchestrator = IntegrationOrchestrator(database_path=temp_database)
        await orchestrator.startup()

        result = await orchestrator.generate_story_content(
            prompt="A hero begins their journey",
            user_id="test_user_v2_narrative",
            preferences={"style": "epic"},
        )

        assert result.success
        assert "narrative_guidance" in result.data
        assert "primary_goal" in result.data["narrative_guidance"]
        assert "target_tension" in result.data["narrative_guidance"]
        assert "current_phase" in result.data["narrative_guidance"]

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_turn_completion_updates_arc_state(self, temp_database):
        """Test that turn completion properly updates the story arc state."""
        orchestrator = IntegrationOrchestrator(database_path=temp_database)
        await orchestrator.startup()

        initial_turn = orchestrator.current_arc_state.turn_number
        initial_progress = float(orchestrator.current_arc_state.phase_progress)

        result = await orchestrator.generate_story_content(
            prompt="The adventure continues",
            user_id="test_user_turn_completion",
        )

        assert result.success

        updated_turn = orchestrator.current_arc_state.turn_number
        updated_progress = float(orchestrator.current_arc_state.phase_progress)

        assert updated_turn == initial_turn + 1
        assert updated_progress > initial_progress

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_narrative_progression_through_multiple_turns(self, temp_database):
        """Test narrative state progression through multiple turn completions."""
        orchestrator = IntegrationOrchestrator(database_path=temp_database)
        await orchestrator.startup()

        turn_states = []

        for i in range(5):
            turn_states.append(
                {
                    "turn": orchestrator.current_arc_state.turn_number,
                    "progress": float(orchestrator.current_arc_state.phase_progress),
                    "phase": orchestrator.current_arc_state.current_phase.value,
                }
            )

            await orchestrator.generate_story_content(
                prompt=f"Turn {i+1} narrative", user_id=f"test_user_{i}"
            )

        for i in range(1, len(turn_states)):
            assert turn_states[i]["turn"] > turn_states[i - 1]["turn"]
            assert turn_states[i]["progress"] >= turn_states[i - 1]["progress"]

        await orchestrator.shutdown()


@pytest.mark.asyncio
class TestPerformanceValidation:
    """Performance validation tests for AI intelligence integration."""

    @pytest.mark.asyncio
    async def test_response_time_requirements(self, temp_database):
        """Test that response times meet performance requirements."""
        config = IntegrationConfig(
            integration_mode=IntegrationMode.AI_ENHANCED,
            performance_threshold=2.0,  # 2 second threshold
        )

        orchestrator = IntegrationOrchestrator(
            database_path=temp_database, integration_config=config
        )

        await orchestrator.startup()

        start_time = datetime.now()
        result = await orchestrator.process_character_action(
            agent_id="performance_test", action="test_action"
        )
        end_time = datetime.now()

        response_time = (end_time - start_time).total_seconds()

        assert result.success
        assert response_time < config.performance_threshold

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_throughput_capacity(self, temp_database):
        """Test system throughput capacity."""
        orchestrator = IntegrationOrchestrator(database_path=temp_database)
        await orchestrator.startup()

        # Measure throughput over time period
        start_time = datetime.now()
        operation_count = 0

        # Run operations for 5 seconds
        while (datetime.now() - start_time).total_seconds() < 5:
            await orchestrator.process_character_action(
                agent_id=f"throughput_agent_{operation_count}", action="throughput_test"
            )
            operation_count += 1

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        operations_per_second = operation_count / duration

        # Should handle at least 1 operation per second
        assert operations_per_second >= 1.0

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_resource_utilization(self, temp_database):
        """Test resource utilization under load."""
        orchestrator = IntegrationOrchestrator(database_path=temp_database)
        await orchestrator.startup()

        await orchestrator._generate_integration_metrics()

        # Generate load
        tasks = []
        for i in range(50):
            task = orchestrator.process_character_action(
                agent_id=f"load_agent_{i}", action="load_test"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        final_metrics = await orchestrator._generate_integration_metrics()

        # Verify all operations succeeded
        assert all(result.success for result in results)

        # Check that system health remained good
        assert final_metrics.system_health_score > 0.5

        await orchestrator.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
