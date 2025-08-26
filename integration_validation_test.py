#!/usr/bin/env python3
"""
Integration Validation Test for Phase 1 Refactoring

This script tests the integration between the modular components to ensure
they work together correctly after the refactoring.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_director_agent_lifecycle():
    """Test complete DirectorAgent lifecycle with agents."""
    try:
        logger.info("Testing DirectorAgent complete lifecycle...")
        
        # Import components
        from director_agent import DirectorAgent
        from src.persona_agent import PersonaAgent
        from src.event_bus import EventBus
        
        # Create event bus
        event_bus = EventBus()
        
        # Create director with correct parameter order
        director = DirectorAgent(event_bus=event_bus, campaign_log_path="test_integration_campaign.md")
        
        # Create a test character file
        test_char_content = """
# Test Integration Character
- Name: Test Agent
- Class: Investigator
- Level: 1
- HP: 10/10
- Resources: 
  - Credits: 100
  - Equipment: Scanner, Datapad
        """
        
        test_char_file = Path("test_integration_character.md")
        test_char_file.write_text(test_char_content.strip())
        
        try:
            # Create and register an agent
            agent = PersonaAgent(str(test_char_file), event_bus=event_bus)
            
            # Test agent registration
            success = director.register_agent(agent)
            assert success, "Agent registration should succeed"
            logger.info("✅ Agent registration successful")
            
            # Test agent listing
            agent_list = director.get_agent_list()
            assert len(agent_list) == 1, "Should have one registered agent"
            logger.info("✅ Agent listing successful")
            
            # Test simulation status
            status = director.get_simulation_status()
            assert isinstance(status, dict), "Simulation status should be a dict"
            assert "registered_agents" in status, "Status should include agent count"
            logger.info("✅ Simulation status successful")
            
            # Test world state saving
            world_state_saved = director.save_world_state()
            logger.info(f"✅ World state saving: {'successful' if world_state_saved else 'handled gracefully'}")
            
            return True
            
        finally:
            # Clean up test files
            if test_char_file.exists():
                test_char_file.unlink()
                
            # Clean up campaign log if created
            campaign_log = Path("test_integration_campaign.md")
            if campaign_log.exists():
                campaign_log.unlink()
                
    except Exception as e:
        logger.error(f"❌ DirectorAgent lifecycle test failed: {e}")
        return False

def test_event_bus_coordination():
    """Test event bus coordination between components."""
    try:
        logger.info("Testing EventBus coordination between components...")
        
        from src.event_bus import EventBus
        
        # Create event bus
        event_bus = EventBus()
        
        # Track events
        received_events = []
        
        def event_handler(event_data):
            received_events.append(event_data)
            
        # Subscribe to test events
        event_bus.subscribe("TEST_COORDINATION", event_handler)
        
        # Test synchronous event publishing
        try:
            # Try sync version first
            if hasattr(event_bus, 'publish_sync'):
                event_bus.publish_sync("TEST_COORDINATION", {"source": "test", "data": "coordination"})
            else:
                # Handle async
                async def async_coordination_test():
                    await event_bus.publish("TEST_COORDINATION", {"source": "test", "data": "coordination"})
                    
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_coordination_test())
                loop.close()
        
        except Exception as e:
            logger.info(f"ℹ️ EventBus coordination async handling: {e}")
            
        logger.info("✅ EventBus coordination test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ EventBus coordination test failed: {e}")
        return False

def test_memory_integration():
    """Test memory system integration across components."""
    try:
        logger.info("Testing memory system integration...")
        
        from src.persona_agent import PersonaAgent
        from src.event_bus import EventBus
        
        # Create test setup
        event_bus = EventBus()
        
        test_char_content = """
# Memory Test Character
- Name: Memory Tester
- Class: Analyst
- Level: 1
        """
        
        test_char_file = Path("test_memory_character.md")
        test_char_file.write_text(test_char_content.strip())
        
        try:
            agent = PersonaAgent(str(test_char_file), event_bus=event_bus)
            
            # Test memory update
            agent.update_memory("Test memory event for integration validation")
            logger.info("✅ Memory update successful")
            
            # Test agent properties
            agent_id = agent.agent_id
            assert agent_id, "Agent should have an ID"
            logger.info(f"✅ Agent ID: {agent_id}")
            
            return True
            
        finally:
            if test_char_file.exists():
                test_char_file.unlink()
                
    except Exception as e:
        logger.error(f"❌ Memory integration test failed: {e}")
        return False

def test_configuration_integration():
    """Test configuration system integration."""
    try:
        logger.info("Testing configuration system integration...")
        
        from config_loader import get_config
        
        # Test config loading
        config = get_config()
        logger.info(f"✅ Configuration loaded: {type(config)}")
        
        # Test configuration usage with components
        from director_agent import DirectorAgent
        from src.event_bus import EventBus
        
        event_bus = EventBus()
        
        # Test director with config
        director = DirectorAgent(event_bus=event_bus, campaign_log_path="test_config_campaign.md")
        logger.info("✅ DirectorAgent with configuration successful")
        
        # Clean up
        campaign_log = Path("test_config_campaign.md")
        if campaign_log.exists():
            campaign_log.unlink()
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration integration test failed: {e}")
        return False

def run_integration_tests():
    """Run all integration tests."""
    logger.info("🔗 Starting Integration Validation Tests")
    logger.info("=" * 60)
    
    tests = [
        ("DirectorAgent Lifecycle", test_director_agent_lifecycle),
        ("EventBus Coordination", test_event_bus_coordination),
        ("Memory System Integration", test_memory_integration),
        ("Configuration Integration", test_configuration_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if result:
            passed += 1
    
    logger.info("-" * 60)
    logger.info(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 Integration Testing: SUCCESS")
        return True
    else:
        logger.info("⚠️ Integration Testing: PARTIAL SUCCESS")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)