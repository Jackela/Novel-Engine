"""
Direct Component Tests - Enhanced Multi-Agent Bridge
===================================================

Testing individual components directly without full module imports.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Direct import of components
try:
    # Test core types directly
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src/bridges/multi_agent_bridge'))
    
    from core.types import (
        RequestPriority, CommunicationType, DialogueState, 
        LLMCoordinationConfig, AgentDialogue, EnhancedWorldState
    )
    from performance.cost_tracker import CostTracker
    from performance.performance_budget import PerformanceBudget
    from performance.performance_metrics import PerformanceMetrics
    
    print("✅ Successfully imported all bridge components directly")
except ImportError as e:
    print(f"❌ Direct import failed: {e}")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)


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
        
        # Test optimization recommendations
        recommendations = cost_tracker.get_optimization_recommendations()
        assert isinstance(recommendations, list), "Should return recommendations list"
        
        print("✅ CostTracker: All tests passed")
        print(f"   Current cost: ${cost_tracker.current_turn_cost:.4f}")
        print(f"   Budget remaining: ${cost_tracker.get_remaining_turn_budget():.4f}")
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
        
        # Test budget availability checks
        budget_ok = budget.is_batch_budget_available(1.0)
        assert isinstance(budget_ok, bool), "Should return boolean for budget check"
        
        # Complete turn and get performance data
        perf_data = budget.complete_turn()
        assert 'total_turn_time' in perf_data, "Should return performance data"
        assert perf_data['batch_operations'] == 1, "Should track batch operations"
        assert perf_data['llm_operations'] == 1, "Should track LLM operations"
        
        # Test performance statistics
        stats = budget.get_performance_stats()
        assert 'total_turns' in stats, "Should include turn statistics"
        
        print("✅ PerformanceBudget: All tests passed")
        print(f"   Turn completed in {perf_data['total_turn_time']:.3f}s")
        print(f"   Budget utilization: {perf_data['budget_utilization']:.1f}%")
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
        
        metrics.record_coordination_event(
            coordination_type="negotiation", 
            participants=["agent2", "agent3"],
            quality_score=0.6,
            success=True
        )
        
        # Test turn metrics recording
        metrics.record_turn_metrics(turn_number=1, additional_metrics={
            'dialogue_count': 2,
            'successful_dialogues': 2
        })
        
        # Test comprehensive metrics
        comprehensive_metrics = metrics.get_comprehensive_metrics()
        assert 'coordination_metrics' in comprehensive_metrics, "Should include coordination metrics"
        assert 'system_health_score' in comprehensive_metrics, "Should include health score"
        assert 'optimization_recommendations' in comprehensive_metrics, "Should include recommendations"
        
        # Test agent interaction analysis  
        interaction_analysis = metrics.get_agent_interaction_analysis()
        assert 'total_interactions' in interaction_analysis, "Should analyze interactions"
        
        print("✅ PerformanceMetrics: All tests passed")
        print(f"   System health score: {comprehensive_metrics['system_health_score']:.1%}")
        print(f"   Total coordinations: {interaction_analysis['total_interactions']}")
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
        assert priority.value == 2, "Should have correct priority value"
        
        comm_type = CommunicationType.DIALOGUE
        assert comm_type.value == "dialogue", "Should have correct communication type"
        
        state = DialogueState.ACTIVE
        assert state.value == "active", "Should have correct dialogue state"
        
        # Test configuration dataclass
        config = LLMCoordinationConfig(
            max_cost_per_turn=0.05,
            enable_smart_batching=True,
            batch_timeout_ms=200
        )
        assert config.max_cost_per_turn == 0.05, "Should set cost limit"
        assert config.enable_smart_batching == True, "Should enable batching"
        assert config.batch_timeout_ms == 200, "Should set timeout"
        
        # Test dialogue dataclass
        from datetime import datetime
        dialogue = AgentDialogue(
            dialogue_id="test_001",
            communication_type=comm_type,
            participants=["agent1", "agent2"],
            initiator="agent1", 
            state=state,
            max_exchanges=5
        )
        assert dialogue.dialogue_id == "test_001", "Should create dialogue"
        assert len(dialogue.participants) == 2, "Should have participants"
        assert dialogue.max_exchanges == 5, "Should set max exchanges"
        
        # Test enhanced world state dataclass
        world_state = EnhancedWorldState(
            turn_number=42,
            base_world_state={"location": "test_location", "time": "noon"}
        )
        assert world_state.turn_number == 42, "Should create world state"
        assert world_state.base_world_state["location"] == "test_location", "Should store base state"
        assert isinstance(world_state.timestamp, datetime), "Should have timestamp"
        
        print("✅ Core Types: All tests passed")
        print(f"   Configuration: max_cost=${config.max_cost_per_turn}, batching={config.enable_smart_batching}")
        print(f"   Dialogue: {dialogue.participants[0]} → {dialogue.participants[1]} ({dialogue.communication_type.value})")
        print(f"   World State: Turn {world_state.turn_number} at {world_state.base_world_state['location']}")
        return True
        
    except Exception as e:
        print(f"❌ Core Types failed: {e}")
        return False


async def test_integration_workflow():
    """Test integrated workflow of components."""
    print("\n🔗 Testing Component Integration Workflow...")
    
    try:
        # Create integrated system
        cost_tracker = CostTracker(max_cost_per_turn=0.10)
        performance_budget = PerformanceBudget(max_turn_time_seconds=5.0)
        metrics = PerformanceMetrics(cost_tracker, performance_budget)
        
        # Simulate a turn workflow
        performance_budget.start_turn()
        
        # Simulate some operations
        cost_tracker.update_cost("dialogue_gen", 0.02, 100)
        performance_budget.record_batch_time(0.3)
        performance_budget.record_llm_time(0.8)
        
        cost_tracker.update_cost("coordination", 0.015, 75)
        performance_budget.record_llm_time(0.5)
        
        # Record coordination events
        metrics.record_coordination_event("dialogue", ["agent1", "agent2"], 0.9, True)
        metrics.record_coordination_event("negotiation", ["agent2", "agent3"], 0.7, True)
        
        # Complete turn
        turn_performance = performance_budget.complete_turn()
        metrics.record_turn_metrics(1, {
            'successful_coordinations': 2,
            'total_agents': 3
        })
        
        # Verify integrated data
        comprehensive_metrics = metrics.get_comprehensive_metrics()
        
        assert comprehensive_metrics['cost_efficiency']['total_cost'] > 0, "Should track costs"
        assert comprehensive_metrics['coordination_metrics']['total_coordinations'] == 2, "Should track coordinations"
        assert comprehensive_metrics['system_health_score'] > 0, "Should calculate health"
        
        print("✅ Integration Workflow: All tests passed")
        print(f"   Turn time: {turn_performance['total_turn_time']:.3f}s")
        print(f"   Total cost: ${comprehensive_metrics['cost_efficiency']['total_cost']:.4f}")
        print(f"   System health: {comprehensive_metrics['system_health_score']:.1%}")
        print(f"   Coordinations: {comprehensive_metrics['coordination_metrics']['total_coordinations']}")
        return True
        
    except Exception as e:
        print(f"❌ Integration Workflow failed: {e}")
        return False


async def run_component_tests():
    """Run all component tests."""
    print("🚀 STARTING ENHANCED MULTI-AGENT BRIDGE COMPONENT TESTS")
    print("=" * 70)
    
    test_functions = [
        test_core_types,
        test_cost_tracker, 
        test_performance_budget,
        test_performance_metrics,
        test_integration_workflow
    ]
    
    results = []
    passed_tests = 0
    
    for i, test_func in enumerate(test_functions, 1):
        try:
            result = await test_func()
            results.append(result)
            if result:
                passed_tests += 1
        except Exception as e:
            print(f"❌ TEST {i} CRITICAL FAILURE: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("📊 COMPONENT TEST SUMMARY")
    print(f"Total Tests: {len(test_functions)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(test_functions) - passed_tests}")
    print(f"Success Rate: {(passed_tests/len(test_functions)*100):.1f}%")
    
    if passed_tests == len(test_functions):
        print("🎉 Enhanced Multi-Agent Bridge Components: ROBUST IMPLEMENTATION")
        print("   All 5 test suites passed with flying colors")
        print("   ✨ Modular architecture fully validated")
        print("   📋 Core Types: Enums and dataclasses working perfectly")
        print("   💰 Cost Tracking: Budget management and optimization")
        print("   ⏱️ Performance Budget: Timing and resource management")
        print("   📊 Performance Metrics: Comprehensive analytics and health scoring")
        print("   🔗 Integration: Cross-component workflow coordination")
    else:
        print("⚠️ Some components need attention - review failed tests")
    
    return passed_tests, len(test_functions)


if __name__ == "__main__":
    asyncio.run(run_component_tests())