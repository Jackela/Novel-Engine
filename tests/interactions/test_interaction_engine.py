"""
Tests for Interaction Engine Module

Coverage targets:
- Phase processing
- Validation logic
- State management
- Error handling
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

pytestmark = pytest.mark.unit

# Import InteractionEngine from the actual module
try:
    from src.interactions.interaction_engine_system import (
        InteractionEngine,
        create_interaction_engine,
        create_performance_optimized_config,
    )
    from src.interactions.interaction_engine_system.core.types import (
        InteractionEngineConfig,
        InteractionOutcome,
        InteractionContext,
        InteractionType,
        InteractionPriority,
    )
    REAL_IMPORTS_AVAILABLE = True
except ImportError as e:
    REAL_IMPORTS_AVAILABLE = False
    print(f"Warning: Could not import real types: {e}")


# Tests for InteractionEngineConfig
@pytest.mark.skipif(not REAL_IMPORTS_AVAILABLE, reason="Real imports not available")
class TestInteractionEngineConfig:
    """Tests for InteractionEngineConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = InteractionEngineConfig()
        
        assert config.max_concurrent_interactions == 5  # Real default is 5
        assert config.default_timeout_seconds == 300.0
        assert config.enable_parallel_processing is True
        assert config.memory_integration_enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = InteractionEngineConfig(
            max_concurrent_interactions=3,
            default_timeout_seconds=180.0,
            enable_parallel_processing=False,
        )
        
        assert config.max_concurrent_interactions == 3
        assert config.default_timeout_seconds == 180.0
        assert config.enable_parallel_processing is False


# Tests for InteractionOutcome
@pytest.mark.skipif(not REAL_IMPORTS_AVAILABLE, reason="Real imports not available")
class TestInteractionOutcome:
    """Tests for InteractionOutcome."""

    def test_success_outcome(self):
        """Test successful outcome."""
        context = InteractionContext(
            interaction_id="int_001",
            interaction_type=InteractionType.DIALOGUE,
        )
        outcome = InteractionOutcome(
            interaction_id="int_001",
            context=context,
            success=True,
            processing_duration=1.5,
            completed_phases=["validation", "processing"],
        )
        
        assert outcome.success is True
        assert outcome.processing_duration == 1.5
        assert len(outcome.completed_phases) == 2

    def test_failure_outcome(self):
        """Test failure outcome."""
        context = InteractionContext(
            interaction_id="int_001",
            interaction_type=InteractionType.COMBAT,
        )
        outcome = InteractionOutcome(
            interaction_id="int_001",
            context=context,
            success=False,
            errors=["Validation failed"],
            processing_duration=0.5,
        )
        
        assert outcome.success is False
        assert len(outcome.errors) == 1
        assert outcome.errors[0] == "Validation failed"


@pytest.mark.skipif(not REAL_IMPORTS_AVAILABLE, reason="Real imports not available")
@pytest.mark.asyncio
class TestInteractionEngine:
    """Tests for InteractionEngine class."""

    @pytest_asyncio.fixture
    async def engine(self):
        """Create an InteractionEngine instance."""
        config = InteractionEngineConfig(
            max_concurrent_interactions=2,
            enable_parallel_processing=False,
            memory_integration_enabled=False,
        )
        
        with patch.object(InteractionEngine, '_initialize_engine', AsyncMock()):
            engine = InteractionEngine(config=config)
            engine.is_initialized = True  # Mark as initialized
            yield engine

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test engine initialization."""
        config = InteractionEngineConfig()
        
        with patch.object(InteractionEngine, '_initialize_engine', AsyncMock()):
            engine = InteractionEngine(config=config)
            # Wait a bit for any async init
            await asyncio.sleep(0)
            
            assert engine.config == config
            assert engine.processing_active is False

    @pytest.mark.asyncio
    async def test_engine_stats_initialization(self):
        """Test engine stats are initialized."""
        with patch.object(InteractionEngine, '_initialize_engine', AsyncMock()):
            engine = InteractionEngine()
            # Wait a bit for any async init
            await asyncio.sleep(0)
            
            assert engine.engine_stats["total_interactions_processed"] == 0
            assert engine.engine_stats["successful_interactions"] == 0
            assert engine.engine_stats["failed_interactions"] == 0
            assert engine.engine_stats["average_processing_time"] == 0.0

    async def test_process_interaction_not_initialized(self, engine):
        """Test processing when not initialized."""
        engine.is_initialized = False
        engine._initialize_engine = AsyncMock()
        
        context = Mock()
        context.interaction_id = "int_001"
        
        # Should call initialize first
        with patch.object(engine, '_process_interaction_sync', AsyncMock(return_value=Mock())):
            await engine.process_interaction(context)
            engine._initialize_engine.assert_called_once()

    async def test_update_engine_stats_success(self, engine):
        """Test updating stats on success."""
        engine._update_engine_stats(True, 1.5)
        
        assert engine.engine_stats["total_interactions_processed"] == 1
        assert engine.engine_stats["successful_interactions"] == 1
        assert engine.engine_stats["average_processing_time"] == 1.5

    async def test_update_engine_stats_failure(self, engine):
        """Test updating stats on failure."""
        engine._update_engine_stats(False, 0.5)
        
        assert engine.engine_stats["total_interactions_processed"] == 1
        assert engine.engine_stats["failed_interactions"] == 1

    async def test_update_engine_stats_multiple(self, engine):
        """Test updating stats multiple times."""
        engine._update_engine_stats(True, 1.0)
        engine._update_engine_stats(True, 2.0)
        engine._update_engine_stats(False, 0.5)
        
        assert engine.engine_stats["total_interactions_processed"] == 3
        assert engine.engine_stats["successful_interactions"] == 2
        assert engine.engine_stats["failed_interactions"] == 1
        # Average: (1.0 + 2.0 + 0.5) / 3 = 1.166...
        assert engine.engine_stats["average_processing_time"] == pytest.approx(1.166, 0.01)

    def test_get_engine_status(self, engine):
        """Test getting engine status."""
        engine.is_initialized = True
        engine.processing_active = True
        engine.engine_stats["total_interactions_processed"] = 10
        
        status = engine.get_engine_status()
        
        assert status["engine_status"]["initialized"] is True
        assert status["engine_status"]["processing_active"] is True
        assert status["engine_status"]["total_interactions_processed"] == 10
        assert "queue_status" in status
        assert "processor_statistics" in status

    async def test_shutdown_engine(self, engine):
        """Test engine shutdown."""
        engine.queue_manager.stop_queue_processing = AsyncMock()
        engine.queue_manager.clear_queue = AsyncMock()
        
        result = await engine.shutdown_engine()
        
        assert result.success is True
        assert engine.processing_active is False
        assert engine.is_initialized is False

    async def test_validate_interaction_context(self, engine):
        """Test context validation."""
        context = Mock()
        
        # Mock validator
        engine.validator.validate_interaction_context = AsyncMock(
            return_value=Mock(success=True)
        )
        
        result = engine.validate_interaction_context(context)
        
        assert result is not None

    async def test_calculate_interaction_risk(self, engine):
        """Test risk calculation."""
        context = Mock()
        
        engine.validator.calculate_risk_assessment = Mock(
            return_value={"risk_score": 0.3, "risk_level": "Low"}
        )
        
        result = engine.calculate_interaction_risk(context)
        
        assert result["risk_score"] == 0.3

    async def test_calculate_interaction_risk_error(self, engine):
        """Test risk calculation with error."""
        context = Mock()
        
        engine.validator.calculate_risk_assessment = Mock(
            side_effect=Exception("Calculation failed")
        )
        
        result = engine.calculate_interaction_risk(context)
        
        assert result["risk_score"] == 0.5  # Default value
        assert "error" in result


@pytest.mark.skipif(not REAL_IMPORTS_AVAILABLE, reason="Real imports not available")
class TestFactoryFunctions:
    """Tests for factory functions."""

    @pytest.mark.asyncio
    async def test_create_interaction_engine(self):
        """Test creating interaction engine with defaults."""
        with patch.object(InteractionEngine, '_initialize_engine', AsyncMock()):
            engine = create_interaction_engine()
            # Wait a bit for any async init
            await asyncio.sleep(0)
            
            assert isinstance(engine, InteractionEngine)
            # Factory function uses 3 as default, not the class default of 5
            assert engine.config.max_concurrent_interactions == 3
            assert engine.config.memory_integration_enabled is True

    @pytest.mark.asyncio
    async def test_create_interaction_engine_custom(self):
        """Test creating interaction engine with custom config."""
        config = InteractionEngineConfig(
            max_concurrent_interactions=3,
            memory_integration_enabled=False,
        )
        
        with patch.object(InteractionEngine, '_initialize_engine', AsyncMock()):
            engine = create_interaction_engine(config=config)
            # Wait a bit for any async init
            await asyncio.sleep(0)
            
            assert engine.config.max_concurrent_interactions == 3
            assert engine.config.memory_integration_enabled is False

    def test_create_performance_optimized_config(self):
        """Test creating performance-optimized config."""
        config = create_performance_optimized_config()
        
        # Check the actual values from the real implementation
        assert config.max_concurrent_interactions >= 5  # At least default
        assert config.default_timeout_seconds == 180.0
        assert config.enable_parallel_processing is True
        assert config.priority_processing is True


# Tests for InteractionType
@pytest.mark.skipif(not REAL_IMPORTS_AVAILABLE, reason="Real imports not available")
class TestInteractionTypes:
    """Tests for interaction types."""

    def test_interaction_types(self):
        """Test all interaction types are defined."""
        assert InteractionType.DIALOGUE.value == "dialogue"
        assert InteractionType.COMBAT.value == "combat"
        assert InteractionType.COOPERATION.value == "cooperation"
        assert InteractionType.NEGOTIATION.value == "negotiation"
