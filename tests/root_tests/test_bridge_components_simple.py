"""
Simple Component Tests for Enhanced Multi-Agent Bridge
=====================================================

Direct component testing without full module imports.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test individual components
try:
    from bridges.multi_agent_bridge.core.types import (
        RequestPriority, CommunicationType, DialogueState, 
        LLMCoordinationConfig, AgentDialogue, EnhancedWorldState
    )
    from bridges.multi_agent_bridge.performance.cost_tracker import CostTracker
    from bridges.multi_agent_bridge.performance.performance_budget import PerformanceBudget
    from bridges.multi_agent_bridge.performance.performance_metrics import PerformanceMetrics
    
    print("✅ Successfully imported all bridge components")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cost_tracker():
    """Test cost tracker component."""
    print("\n💰 Testing CostTracker Component...")
    
    try:
        cost_tracker = CostTracker(max_cost_per_turn=0.10, max_total_cost=1.0)
        
        # Test cost updates
        within_budget = cost_tracker.update_cost("dialogue", 0.03, 150)
        assert within_budget == True, "Should be within budget"
        
        # Test budget checks
        budget_available = cost_tracker.is_under_budget(0.05)
        assert budget_available == True, "Should have budget available"
        
        # Test statistics
        stats = cost_tracker.get_cost_efficiency_stats()
        assert stats['total_cost'] == 0.03, "Should track total cost"
        assert stats['current_turn_cost'] == 0.03, "Should track turn cost"
        
        print("✅ CostTracker: All tests passed")
        return True
        
    except Exception as e:
        print(f"❌ CostTracker failed: {e}")
        return False


async def test_performance_budget():
    """Test performance budget component."""
    print("\n⏱️ Testing PerformanceBudget Component...")
    
    try:
        budget = PerformanceBudget(max_turn_time_seconds=5.0)
        
        # Test turn timing
        budget.start_turn()
        remaining = budget.get_remaining_time()
        assert remaining > 0, "Should have remaining time"
        
        # Test batch time recording
        budget.record_batch_time(0.5)
        budget.record_llm_time(1.2)
        
        # Complete turn and get performance data
        perf_data = budget.complete_turn()
        assert 'total_turn_time' in perf_data, "Should return performance data"
        assert perf_data['batch_operations'] == 1, "Should track batch operations"
        
        print("✅ PerformanceBudget: All tests passed")
        return True
        
    except Exception as e:
        print(f"❌ PerformanceBudget failed: {e}")
        return False


async def test_performance_metrics():
    """Test performance metrics component."""
    print("\n📊 Testing PerformanceMetrics Component...")
    
    try:
        cost_tracker = CostTracker()
        performance_budget = PerformanceBudget()
        metrics = PerformanceMetrics(cost_tracker, performance_budget)
        
        # Test coordination event recording
        metrics.record_coordination_event(
            coordination_type="dialogue",
            participants=["agent1", "agent2"],
            quality_score=0.8,
            success=True
        )
        
        # Test metrics collection
        comprehensive_metrics = metrics.get_comprehensive_metrics()
        assert 'coordination_metrics' in comprehensive_metrics, "Should include coordination metrics"
        assert 'system_health_score' in comprehensive_metrics, "Should include health score"
        
        print("✅ PerformanceMetrics: All tests passed") 
        return True
        
    except Exception as e:
        print(f"❌ PerformanceMetrics failed: {e}")
        return False


async def test_core_types():
    """Test core data types."""
    print("\n📋 Testing Core Types...")
    
    try:
        # Test enums
        priority = RequestPriority.HIGH
        comm_type = CommunicationType.DIALOGUE
        state = DialogueState.ACTIVE
        
        # Test configuration
        config = LLMCoordinationConfig(
            max_cost_per_turn=0.05,
            enable_smart_batching=True
        )
        assert config.max_cost_per_turn == 0.05, "Should set cost limit"
        
        # Test dialogue creation
        from datetime import datetime
        dialogue = AgentDialogue(
            dialogue_id="test_001",
            communication_type=comm_type,
            participants=["agent1", "agent2"],
            initiator="agent1", 
            state=state
        )
        assert dialogue.dialogue_id == "test_001", "Should create dialogue"
        
        # Test enhanced world state
        world_state = EnhancedWorldState(
            turn_number=1,
            base_world_state={"location": "test"}
        )
        assert world_state.turn_number == 1, "Should create world state"
        
        print("✅ Core Types: All tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Core Types failed: {e}")
        return False


async def run_component_tests():
    """Run all component tests."""
    print("🚀 STARTING ENHANCED MULTI-AGENT BRIDGE COMPONENT TESTS")
    print("=" * 60)
    
    test_functions = [
        test_core_types,
        test_cost_tracker,
        test_performance_budget,
        test_performance_metrics
    ]
    
    results = []
    passed_tests = 0
    
    for test_func in test_functions:
        try:
            result = await test_func()
            results.append(result)
            if result:
                passed_tests += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} CRITICAL FAILURE: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 COMPONENT TEST SUMMARY")
    print(f"Total Tests: {len(test_functions)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(test_functions) - passed_tests}")
    print(f"Success Rate: {(passed_tests/len(test_functions)*100):.1f}%")
    
    if passed_tests == len(test_functions):
        print("🎉 Enhanced Multi-Agent Bridge Components: ROBUST IMPLEMENTATION")
        print("   All 4 core components working perfectly")
        print("   ✨ Modular architecture validated")
    else:
        print("⚠️ Some components need attention")
    
    return passed_tests, len(test_functions)


if __name__ == "__main__":
    asyncio.run(run_component_tests())