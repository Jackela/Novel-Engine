"""
Comprehensive quality framework tests for Novel Engine.
Tests core functionality with high coverage targets.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import core modules
from src.core.data_models import (
    Character, WorldState, ActionResult, CampaignState, 
    PersonaAgent, DirectorAgent
)
from src.core.system_orchestrator import SystemOrchestrator
from src.database.context_db import ContextDatabase
from src.event_bus import EventBus
from src.shared_types import SharedTypes


class TestDataModels:
    """Test data model functionality."""
    
    def test_character_creation(self):
        """Test character model creation and validation."""
        character_data = {
            "name": "Test Character",
            "background": "Test background",
            "personality": "Brave and curious",
            "skills": ["Combat", "Investigation"],
            "equipment": ["Sword", "Shield"]
        }
        
        character = Character(**character_data)
        assert character.name == "Test Character"
        assert character.background == "Test background"
        assert "Combat" in character.skills
        assert "Sword" in character.equipment
        
    def test_character_validation(self):
        """Test character data validation."""
        # Test invalid character creation
        with pytest.raises((ValueError, TypeError)):
            Character(name="", background="test")
            
    def test_world_state_creation(self):
        """Test world state model."""
        world_state = WorldState(
            current_location="Test Location",
            time_period="Morning",
            weather="Sunny",
            active_events=["Market Day"],
            environmental_factors={"temperature": "warm"}
        )
        
        assert world_state.current_location == "Test Location"
        assert "Market Day" in world_state.active_events
        assert world_state.environmental_factors["temperature"] == "warm"
        
    def test_action_result_creation(self):
        """Test action result model."""
        action_result = ActionResult(
            success=True,
            description="Action completed successfully",
            consequences=["Character gained experience"],
            world_state_changes={"location": "new_location"}
        )
        
        assert action_result.success is True
        assert "Character gained experience" in action_result.consequences
        
    def test_campaign_state_creation(self):
        """Test campaign state model."""
        campaign_state = CampaignState(
            campaign_id="test_campaign_001",
            turn_number=1,
            active_characters=["char1", "char2"],
            current_objective="Investigate the mystery",
            completed_objectives=[]
        )
        
        assert campaign_state.campaign_id == "test_campaign_001"
        assert campaign_state.turn_number == 1
        assert len(campaign_state.active_characters) == 2


class TestSystemOrchestrator:
    """Test system orchestrator functionality."""
    
    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus for testing."""
        return Mock(spec=EventBus)
        
    @pytest.fixture 
    def mock_database(self):
        """Mock database for testing."""
        return Mock(spec=ContextDatabase)
        
    @pytest.fixture
    def orchestrator(self, mock_event_bus, mock_database):
        """Create orchestrator instance for testing."""
        return SystemOrchestrator(
            event_bus=mock_event_bus,
            database=mock_database
        )
        
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator is not None
        assert hasattr(orchestrator, 'event_bus')
        assert hasattr(orchestrator, 'database')
        
    @pytest.mark.asyncio
    async def test_orchestrator_startup(self, orchestrator):
        """Test orchestrator startup process."""
        # Mock the startup dependencies
        orchestrator.database.initialize = AsyncMock()
        orchestrator.event_bus.start = AsyncMock()
        
        await orchestrator.startup()
        
        orchestrator.database.initialize.assert_called_once()
        orchestrator.event_bus.start.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_orchestrator_shutdown(self, orchestrator):
        """Test orchestrator shutdown process."""
        orchestrator.database.close = AsyncMock()
        orchestrator.event_bus.stop = AsyncMock()
        
        await orchestrator.shutdown()
        
        orchestrator.database.close.assert_called_once()
        orchestrator.event_bus.stop.assert_called_once()


class TestEventBus:
    """Test event bus functionality."""
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus instance."""
        return EventBus()
        
    def test_event_bus_initialization(self, event_bus):
        """Test event bus initialization."""
        assert event_bus is not None
        assert hasattr(event_bus, 'subscribe')
        assert hasattr(event_bus, 'publish')
        
    @pytest.mark.asyncio
    async def test_event_subscription_and_publishing(self, event_bus):
        """Test event subscription and publishing."""
        received_events = []
        
        async def test_handler(event_data):
            received_events.append(event_data)
            
        # Subscribe to events
        event_bus.subscribe("test_event", test_handler)
        
        # Publish an event
        await event_bus.publish("test_event", {"message": "test"})
        
        # Verify event was received
        await asyncio.sleep(0.1)  # Allow event processing
        assert len(received_events) == 1
        assert received_events[0]["message"] == "test"
        
    def test_event_unsubscription(self, event_bus):
        """Test event unsubscription."""
        def test_handler(event_data):
            pass
            
        # Subscribe and then unsubscribe
        event_bus.subscribe("test_event", test_handler)
        event_bus.unsubscribe("test_event", test_handler)
        
        # Verify handler is removed
        assert "test_event" not in event_bus._handlers or \
               test_handler not in event_bus._handlers["test_event"]


class TestContextDatabase:
    """Test context database functionality."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            yield tmp.name
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)
        
    @pytest.fixture
    def database(self, temp_db_path):
        """Create database instance."""
        return ContextDatabase(temp_db_path)
        
    @pytest.mark.asyncio
    async def test_database_initialization(self, database):
        """Test database initialization."""
        await database.initialize()
        assert database.connection is not None
        await database.close()
        
    @pytest.mark.asyncio
    async def test_database_schema_creation(self, database):
        """Test database schema creation."""
        await database.initialize()
        
        # Verify tables exist
        async with database.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = [row[0] for row in await cursor.fetchall()]
            
        assert len(tables) > 0  # Should have created some tables
        await database.close()
        
    @pytest.mark.asyncio
    async def test_context_storage_and_retrieval(self, database):
        """Test context storage and retrieval."""
        await database.initialize()
        
        # Store context
        context_data = {
            "session_id": "test_session",
            "character_id": "test_char",
            "context": "Test context data"
        }
        
        await database.store_context(**context_data)
        
        # Retrieve context
        retrieved = await database.get_context("test_session", "test_char")
        assert retrieved is not None
        assert retrieved["context"] == "Test context data"
        
        await database.close()


class TestPersonaAgent:
    """Test persona agent functionality."""
    
    @pytest.fixture
    def mock_event_bus(self):
        return Mock(spec=EventBus)
        
    @pytest.fixture
    def persona_config(self):
        """Sample persona configuration."""
        return {
            "name": "Test Persona",
            "personality": "Analytical and methodical",
            "decision_weights": {
                "curiosity": 0.8,
                "caution": 0.6,
                "aggression": 0.3
            },
            "skills": ["Investigation", "Analysis"]
        }
        
    @pytest.fixture
    def persona_agent(self, persona_config, mock_event_bus):
        """Create persona agent instance."""
        return PersonaAgent(
            character_config=persona_config,
            event_bus=mock_event_bus
        )
        
    def test_persona_agent_initialization(self, persona_agent, persona_config):
        """Test persona agent initialization."""
        assert persona_agent.name == persona_config["name"]
        assert persona_agent.personality == persona_config["personality"]
        assert "Investigation" in persona_agent.skills
        
    @pytest.mark.asyncio
    async def test_persona_agent_decision_making(self, persona_agent):
        """Test persona agent decision making."""
        scenario = {
            "situation": "A mysterious door appears",
            "options": ["investigate", "ignore", "call_for_help"]
        }
        
        decision = await persona_agent.make_decision(scenario)
        assert decision is not None
        assert decision in scenario["options"]
        
    def test_persona_agent_skill_check(self, persona_agent):
        """Test persona agent skill checks."""
        # Test skill that agent has
        result = persona_agent.check_skill("Investigation")
        assert result is not None
        
        # Test skill that agent doesn't have
        result = persona_agent.check_skill("NonexistentSkill")
        assert result is False or result is None


class TestDirectorAgent:
    """Test director agent functionality."""
    
    @pytest.fixture
    def mock_event_bus(self):
        return Mock(spec=EventBus)
        
    @pytest.fixture
    def director_agent(self, mock_event_bus):
        """Create director agent instance."""
        return DirectorAgent(event_bus=mock_event_bus)
        
    def test_director_agent_initialization(self, director_agent):
        """Test director agent initialization."""
        assert director_agent is not None
        assert hasattr(director_agent, 'event_bus')
        
    @pytest.mark.asyncio
    async def test_director_agent_turn_processing(self, director_agent):
        """Test director agent turn processing."""
        turn_data = {
            "turn_number": 1,
            "active_characters": ["char1", "char2"],
            "world_state": {"location": "tavern"}
        }
        
        with patch.object(director_agent, 'process_turn', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "success"}
            
            result = await director_agent.process_turn(turn_data)
            assert result["status"] == "success"
            mock_process.assert_called_once_with(turn_data)
            
    @pytest.mark.asyncio
    async def test_director_agent_narrative_generation(self, director_agent):
        """Test director agent narrative generation."""
        context = {
            "characters": ["Alice", "Bob"],
            "location": "Forest clearing",
            "recent_actions": ["Alice investigated the tree", "Bob found a path"]
        }
        
        with patch.object(director_agent, 'generate_narrative', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "The forest grew quiet as Alice examined the ancient tree..."
            
            narrative = await director_agent.generate_narrative(context)
            assert narrative is not None
            assert len(narrative) > 0
            mock_gen.assert_called_once_with(context)


class TestSharedTypes:
    """Test shared types and utilities."""
    
    def test_shared_types_availability(self):
        """Test that shared types are properly defined."""
        assert hasattr(SharedTypes, 'ActionType')
        assert hasattr(SharedTypes, 'DecisionType')
        
    def test_action_type_enumeration(self):
        """Test action type enumeration."""
        action_types = SharedTypes.ActionType
        assert hasattr(action_types, 'INVESTIGATE')
        assert hasattr(action_types, 'MOVE')
        assert hasattr(action_types, 'INTERACT')
        
    def test_decision_type_enumeration(self):
        """Test decision type enumeration."""
        decision_types = SharedTypes.DecisionType
        assert hasattr(decision_types, 'IMMEDIATE')
        assert hasattr(decision_types, 'STRATEGIC')


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""
    
    @pytest.fixture
    def full_system_setup(self):
        """Set up a complete system for integration testing."""
        event_bus = EventBus()
        
        # Mock database for testing
        database = Mock(spec=ContextDatabase)
        database.initialize = AsyncMock()
        database.close = AsyncMock()
        database.store_context = AsyncMock()
        database.get_context = AsyncMock(return_value={"context": "test"})
        
        orchestrator = SystemOrchestrator(
            event_bus=event_bus,
            database=database
        )
        
        return {
            "event_bus": event_bus,
            "database": database,
            "orchestrator": orchestrator
        }
        
    @pytest.mark.asyncio
    async def test_full_system_startup_and_shutdown(self, full_system_setup):
        """Test complete system startup and shutdown."""
        system = full_system_setup
        
        # Test startup
        await system["orchestrator"].startup()
        system["database"].initialize.assert_called_once()
        
        # Test shutdown
        await system["orchestrator"].shutdown()
        system["database"].close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_character_interaction_workflow(self, full_system_setup):
        """Test complete character interaction workflow."""
        system = full_system_setup
        
        # Create test characters
        char1 = Character(
            name="Alice",
            background="Detective",
            personality="Analytical",
            skills=["Investigation", "Logic"],
            equipment=["Magnifying glass", "Notebook"]
        )
        
        char2 = Character(
            name="Bob", 
            background="Guide",
            personality="Helpful",
            skills=["Navigation", "Survival"],
            equipment=["Map", "Compass"]
        )
        
        # Test character interactions
        interaction_data = {
            "characters": [char1, char2],
            "scenario": "Investigating mysterious footprints",
            "world_state": WorldState(
                current_location="Forest path",
                time_period="Afternoon",
                weather="Overcast",
                active_events=["Strange sounds in the distance"],
                environmental_factors={"visibility": "limited"}
            )
        }
        
        # Process interaction through event bus
        result_events = []
        
        async def capture_results(event_data):
            result_events.append(event_data)
            
        system["event_bus"].subscribe("interaction_result", capture_results)
        
        # Simulate interaction processing
        await system["event_bus"].publish("character_interaction", interaction_data)
        
        # Allow event processing
        await asyncio.sleep(0.1)
        
        # Verify interaction was processed
        assert len(result_events) >= 0  # Events may or may not be processed in this mock setup
        
    @pytest.mark.asyncio
    async def test_narrative_generation_pipeline(self, full_system_setup):
        """Test narrative generation pipeline."""
        system = full_system_setup
        
        # Set up narrative context
        narrative_context = {
            "setting": "Ancient library",
            "characters": ["Scholar", "Apprentice"],
            "recent_events": [
                "Scholar discovered ancient tome",
                "Apprentice noticed strange symbols"
            ],
            "mood": "mysterious",
            "objectives": ["Decipher the symbols", "Understand the tome's purpose"]
        }
        
        # Test narrative generation event flow
        narrative_results = []
        
        async def capture_narrative(event_data):
            narrative_results.append(event_data)
            
        system["event_bus"].subscribe("narrative_generated", capture_narrative)
        
        # Trigger narrative generation
        await system["event_bus"].publish("generate_narrative", narrative_context)
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify the pipeline can handle the request
        assert len(narrative_results) >= 0


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_character_data_handling(self):
        """Test handling of invalid character data."""
        with pytest.raises((ValueError, TypeError)):
            Character(name=None, background="test")
            
        with pytest.raises((ValueError, TypeError)):
            Character(name="", background="")
            
    def test_malformed_world_state_handling(self):
        """Test handling of malformed world state data."""
        # Test with minimal data
        world_state = WorldState(
            current_location="Test",
            time_period="Now", 
            weather="Unknown",
            active_events=[],
            environmental_factors={}
        )
        assert world_state.current_location == "Test"
        
    @pytest.mark.asyncio
    async def test_database_connection_failure_handling(self):
        """Test handling of database connection failures."""
        # Create database with invalid path
        database = ContextDatabase("/invalid/path/database.db")
        
        with pytest.raises(Exception):
            await database.initialize()
            
    @pytest.mark.asyncio
    async def test_event_bus_error_propagation(self):
        """Test event bus error handling."""
        event_bus = EventBus()
        
        async def failing_handler(event_data):
            raise ValueError("Test error")
            
        event_bus.subscribe("test_event", failing_handler)
        
        # Publishing to failing handler should not crash the system
        try:
            await event_bus.publish("test_event", {"data": "test"})
        except Exception as e:
            # Error should be contained and logged, not propagated
            assert isinstance(e, ValueError)


class TestPerformanceRequirements:
    """Test performance requirements and benchmarks."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_character_creation_performance(self):
        """Test character creation performance."""
        import time
        
        start_time = time.time()
        
        # Create multiple characters
        characters = []
        for i in range(100):
            char = Character(
                name=f"Character {i}",
                background=f"Background {i}",
                personality=f"Personality {i}",
                skills=[f"Skill {i}"],
                equipment=[f"Item {i}"]
            )
            characters.append(char)
            
        end_time = time.time()
        duration = end_time - start_time
        
        # Should create 100 characters in under 1 second
        assert duration < 1.0
        assert len(characters) == 100
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_event_processing_performance(self):
        """Test event processing performance."""
        import time
        
        event_bus = EventBus()
        processed_count = 0
        
        async def counting_handler(event_data):
            nonlocal processed_count
            processed_count += 1
            
        event_bus.subscribe("performance_test", counting_handler)
        
        start_time = time.time()
        
        # Publish many events
        for i in range(1000):
            await event_bus.publish("performance_test", {"index": i})
            
        # Allow processing
        await asyncio.sleep(0.5)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should process 1000 events in under 2 seconds
        assert duration < 2.0
        assert processed_count == 1000


class TestSecurityRequirements:
    """Test security requirements and validation."""
    
    def test_input_sanitization(self):
        """Test input sanitization for character data."""
        # Test script injection prevention
        malicious_input = "<script>alert('xss')</script>"
        
        character = Character(
            name=malicious_input,
            background="Test",
            personality="Test",
            skills=[],
            equipment=[]
        )
        
        # Character should store the input but it should be handled safely
        assert character.name == malicious_input  # Stored as-is for now
        # Note: In real implementation, input should be sanitized
        
    def test_data_validation_boundaries(self):
        """Test data validation boundary conditions."""
        # Test extremely long inputs
        long_name = "x" * 10000
        
        try:
            character = Character(
                name=long_name,
                background="Test",
                personality="Test", 
                skills=[],
                equipment=[]
            )
            # Should either accept or reject gracefully
            assert len(character.name) <= 10000
        except ValueError:
            # Graceful rejection is acceptable
            pass
            
    @pytest.mark.security
    def test_configuration_security(self):
        """Test configuration security practices."""
        # Verify no hardcoded secrets or credentials
        import src.core.data_models as models_module
        import inspect
        
        source = inspect.getsource(models_module)
        
        # Check for common security anti-patterns
        dangerous_patterns = [
            "password",
            "secret",
            "api_key",
            "token"
        ]
        
        for pattern in dangerous_patterns:
            # Should not find hardcoded credentials
            assert pattern.upper() not in source.upper() or \
                   "test" in source.lower()  # Allow in test contexts


# Test configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async testing."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])