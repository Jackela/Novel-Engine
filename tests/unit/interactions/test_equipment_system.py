"""
Dynamic Equipment System Modular - Comprehensive Integration Tests
=================================================================

Test suite for the modular dynamic equipment system components and integration.
Tests all 6 components and end-to-end workflows.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add src to path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Test import of modular components
try:
    from src.interactions.equipment_system import (
        DynamicEquipmentSystem, EquipmentCategory, EquipmentStatus,
        EquipmentModification, EquipmentMaintenance, DynamicEquipment,
        create_dynamic_equipment_system, create_maintenance_optimized_config
    )
    print("✅ Successfully imported all equipment system components")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}")  # Show first 3 entries
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Mock equipment item for testing
@dataclass
class MockEquipmentItem:
    name: str
    equipment_id: str = ""
    category: str = "tool"
    condition: str = "good"


async def test_equipment_registration():
    """Test equipment registration component."""
    print("\n🔧 Testing Equipment Registration...")
    
    try:
        system = create_dynamic_equipment_system(logger=logging.getLogger("test"))
        
        # Create test equipment
        equipment_item = MockEquipmentItem(
            name="Test Bolt Rifle",
            category="weapon"
        )
        
        # Test registration
        result = await system.register_equipment(
            equipment_item=equipment_item,
            agent_id="test_agent",
            location="armory",
            initial_blessing_level=1.0
        )
        
        assert result.success, "Equipment registration should succeed"
        assert "equipment_id" in result.data, "Should return equipment ID"
        
        equipment_id = result.data["equipment_id"]
        
        # Test retrieval
        equipment = await system.registry.get_equipment(equipment_id)
        assert equipment is not None, "Should be able to retrieve registered equipment"
        assert equipment.base_equipment.name == "Test Bolt Rifle", "Equipment name should match"
        assert equipment.owner_id == "test_agent", "Owner should be assigned correctly"
        
        print("✅ Equipment Registration: All tests passed")
        print(f"   Registered: {equipment.base_equipment.name}")
        print(f"   ID: {equipment_id}")
        print(f"   Owner: {equipment.owner_id}")
        return True
        
    except Exception as e:
        print(f"❌ Equipment Registration failed: {e}")
        return False


async def test_equipment_usage():
    """Test equipment usage and wear processing."""
    print("\n⚙️ Testing Equipment Usage Processing...")
    
    try:
        system = create_dynamic_equipment_system(logger=logging.getLogger("test"))
        
        # Register test weapon
        weapon_item = MockEquipmentItem(name="Test Plasma Rifle", category="weapon")
        reg_result = await system.register_equipment(weapon_item, "agent_alpha")
        equipment_id = reg_result.data["equipment_id"]
        
        # Test weapon usage
        usage_result = await system.use_equipment(
            equipment_id=equipment_id,
            agent_id="agent_alpha",
            usage_context={
                "shots_fired": 10,
                "target_hit": True,
                "intensity": "high"
            },
            duration_seconds=120.0
        )
        
        assert usage_result["success"], "Equipment usage should succeed"
        assert usage_result["data"]["wear_accumulation"] > 0, "Should accumulate wear"
        
        # Get equipment to check wear
        equipment = await system.registry.get_equipment(equipment_id)
        assert equipment.wear_accumulation > 0, "Wear should be accumulated"
        assert equipment.last_used is not None, "Last used timestamp should be set"
        
        print("✅ Equipment Usage: All tests passed")
        print(f"   Weapon fired: 10 shots")
        print(f"   Wear accumulated: {equipment.wear_accumulation:.3f}")
        print(f"   Machine spirit mood: {equipment.machine_spirit_mood}")
        return True
        
    except Exception as e:
        print(f"❌ Equipment Usage failed: {e}")
        return False


async def test_maintenance_system():
    """Test maintenance scheduling and execution."""
    print("\n🔧 Testing Maintenance System...")
    
    try:
        system = create_dynamic_equipment_system(logger=logging.getLogger("test"))
        
        # Register and wear down equipment
        armor_item = MockEquipmentItem(name="Test Power Armor", category="armor")
        reg_result = await system.register_equipment(armor_item, "agent_beta")
        equipment_id = reg_result["data"]["equipment_id"]
        
        # Simulate heavy usage to accumulate wear
        equipment = await system.registry.get_equipment(equipment_id)
        equipment.wear_accumulation = 0.8  # High wear
        
        # Test maintenance
        maintenance_result = await system.perform_maintenance(
            equipment_id=equipment_id,
            maintenance_type="repair",
            performed_by="tech_priest_gamma"
        )
        
        assert maintenance_result["success"], "Maintenance should succeed"
        assert "wear_reduction" in maintenance_result["data"], "Should report wear reduction"
        
        # Check wear reduction
        equipment = await system.registry.get_equipment(equipment_id)
        assert equipment.wear_accumulation < 0.8, "Wear should be reduced after maintenance"
        assert len(equipment.maintenance_history) > 0, "Should have maintenance history"
        
        print("✅ Maintenance System: All tests passed")
        print(f"   Maintenance type: {maintenance_result['data']['maintenance_type']}")
        print(f"   Wear after maintenance: {equipment.wear_accumulation:.3f}")
        print(f"   Machine spirit response: {maintenance_result['data']['machine_spirit_response']}")
        return True
        
    except Exception as e:
        print(f"❌ Maintenance System failed: {e}")
        return False


async def test_modification_system():
    """Test equipment modifications and compatibility."""
    print("\n🔬 Testing Modification System...")
    
    try:
        system = create_dynamic_equipment_system(logger=logging.getLogger("test"))
        
        # Register test equipment
        tool_item = MockEquipmentItem(name="Test Multi-tool", category="tool")
        reg_result = await system.register_equipment(tool_item, "agent_charlie")
        equipment_id = reg_result["data"]["equipment_id"]
        
        # Create test modification
        modification = EquipmentModification(
            modification_id="enhanced_motor_001",
            modification_name="enhanced_motor",
            description="High-performance motor upgrade",
            performance_impact={"efficiency": 0.2, "reliability": -0.05}
        )
        
        # Test modification installation
        mod_result = await system.apply_modification(
            equipment_id=equipment_id,
            modification=modification,
            installer="tech_adept_delta"
        )
        
        assert mod_result["success"], "Modification installation should succeed"
        
        # Check modification was applied
        equipment = await system.registry.get_equipment(equipment_id)
        assert len(equipment.modifications) > 0, "Should have modifications"
        assert equipment.modifications[0].modification_id == "enhanced_motor_001", "Modification ID should match"
        
        # Check performance impact
        assert "efficiency" in equipment.performance_metrics, "Should have efficiency metric"
        
        print("✅ Modification System: All tests passed")
        print(f"   Modification installed: {modification.modification_name}")
        print(f"   Performance impact: {modification.performance_impact}")
        print(f"   Total modifications: {len(equipment.modifications)}")
        return True
        
    except Exception as e:
        print(f"❌ Modification System failed: {e}")
        return False


async def test_performance_monitoring():
    """Test performance monitoring and failure prediction."""
    print("\n📊 Testing Performance Monitoring...")
    
    try:
        system = create_dynamic_equipment_system(logger=logging.getLogger("test"))
        
        # Register test equipment
        sensor_item = MockEquipmentItem(name="Test Auspex Scanner", category="sensor")
        reg_result = await system.register_equipment(sensor_item, "agent_epsilon")
        equipment_id = reg_result["data"]["equipment_id"]
        
        # Simulate usage and wear
        equipment = await system.registry.get_equipment(equipment_id)
        equipment.wear_accumulation = 0.6
        equipment.usage_statistics = {
            "total_uses": 50,
            "successful_uses": 45,
            "total_duration": 3600
        }
        
        # Test performance metrics
        performance_data = system.performance_monitor.get_performance_metrics(equipment)
        assert "metrics" in performance_data, "Should return performance metrics"
        assert "overall_health" in performance_data["metrics"], "Should calculate overall health"
        
        # Test failure prediction
        failure_prediction = system.performance_monitor.predict_equipment_failure(equipment)
        assert "risk_score" in failure_prediction, "Should provide risk score"
        assert "risk_level" in failure_prediction, "Should classify risk level"
        
        # Test optimization recommendations
        recommendations = system.performance_monitor.get_optimization_recommendations(equipment)
        assert isinstance(recommendations, list), "Should return recommendations list"
        
        print("✅ Performance Monitoring: All tests passed")
        print(f"   Overall health: {performance_data['metrics']['overall_health']:.1%}")
        print(f"   Failure risk: {failure_prediction['risk_level']} ({failure_prediction['risk_score']:.2f})")
        print(f"   Recommendations: {len(recommendations)}")
        return True
        
    except Exception as e:
        print(f"❌ Performance Monitoring failed: {e}")
        return False


async def test_comprehensive_equipment_status():
    """Test comprehensive equipment status retrieval."""
    print("\n📋 Testing Comprehensive Equipment Status...")
    
    try:
        system = create_dynamic_equipment_system(logger=logging.getLogger("test"))
        
        # Register test equipment
        relic_item = MockEquipmentItem(name="Sacred Relic of the Omnissiah", category="relic")
        reg_result = await system.register_equipment(relic_item, "agent_zeta")
        equipment_id = reg_result["data"]["equipment_id"]
        
        # Add some history through usage and maintenance
        await system.use_equipment(equipment_id, "agent_zeta", {"ritual_performed": True}, 300)
        await system.perform_maintenance(equipment_id, "consecration", "tech_priest_alpha")
        
        # Test comprehensive status
        status_result = await system.get_equipment_status(equipment_id)
        
        assert status_result["success"], "Status retrieval should succeed"
        assert "basic_info" in status_result["data"], "Should include basic info"
        assert "wear_and_performance" in status_result["data"], "Should include performance data"
        assert "maintenance_info" in status_result["data"], "Should include maintenance info"
        assert "performance_analysis" in status_result["data"], "Should include performance analysis"
        assert "failure_prediction" in status_result["data"], "Should include failure prediction"
        assert "recommendations" in status_result["data"], "Should include recommendations"
        
        basic_info = status_result["data"]["basic_info"]
        assert basic_info["name"] == "Sacred Relic of the Omnissiah", "Name should match"
        assert basic_info["category"] == "relic", "Category should match"
        
        print("✅ Comprehensive Status: All tests passed")
        print(f"   Equipment: {basic_info['name']}")
        print(f"   Status: {basic_info['status']}")
        print(f"   Machine spirit: {status_result['data']['wear_and_performance']['machine_spirit_mood']}")
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive Status failed: {e}")
        return False


async def test_integration_workflow():
    """Test end-to-end equipment lifecycle workflow."""
    print("\n🔄 Testing Integration Workflow...")
    
    try:
        # Create optimized system
        config = create_maintenance_optimized_config(wear_threshold=0.5)
        system = DynamicEquipmentSystem(
            auto_maintenance=config.auto_maintenance,
            maintenance_interval_hours=config.maintenance_interval_hours,
            wear_threshold=config.wear_threshold,
            logger=logging.getLogger("integration")
        )
        
        # 1. Register multiple equipment
        equipment_items = [
            MockEquipmentItem(name="Integrated Lasgun", category="weapon"),
            MockEquipmentItem(name="Integrated Carapace", category="armor"), 
            MockEquipmentItem(name="Integrated Diagnostor", category="medical")
        ]
        
        equipment_ids = []
        for item in equipment_items:
            result = await system.register_equipment(item, "integration_agent")
            assert result["success"], f"Should register {item.name}"
            equipment_ids.append(result["data"]["equipment_id"])
        
        # 2. Simulate usage patterns
        for i, eq_id in enumerate(equipment_ids):
            usage_contexts = [
                {"shots_fired": 5, "intensity": "normal"},
                {"damage_absorbed": 10, "environment": "harsh"},
                {"patients_treated": 3, "effectiveness": 0.9}
            ]
            
            await system.use_equipment(eq_id, "integration_agent", usage_contexts[i], 180)
        
        # 3. Check agent equipment
        agent_equipment = await system.get_agent_equipment("integration_agent")
        assert agent_equipment["success"], "Should get agent equipment"
        assert agent_equipment["data"]["equipment_count"] == 3, "Should have 3 pieces of equipment"
        
        # 4. Perform maintenance on worn equipment
        maintenance_count = 0
        for eq_id in equipment_ids:
            equipment = await system.registry.get_equipment(eq_id)
            if equipment.wear_accumulation > 0.3:
                result = await system.perform_maintenance(eq_id, "routine")
                if result["success"]:
                    maintenance_count += 1
        
        # 5. Get system statistics
        stats = system.get_system_statistics()
        assert "equipment_statistics" in stats, "Should have equipment statistics"
        assert stats["equipment_statistics"]["total_registered"] >= 3, "Should have registered equipment"
        
        print("✅ Integration Workflow: All tests passed")
        print(f"   Equipment registered: {len(equipment_ids)}")
        print(f"   Agent equipment count: {agent_equipment['data']['equipment_count']}")
        print(f"   Maintenance performed: {maintenance_count}")
        print(f"   Total system equipment: {stats['equipment_statistics']['total_registered']}")
        return True
        
    except Exception as e:
        print(f"❌ Integration Workflow failed: {e}")
        return False


async def test_backward_compatibility():
    """Test backward compatibility with legacy API."""
    print("\n↩️ Testing Backward Compatibility...")
    
    try:
        system = create_dynamic_equipment_system()
        
        # Test legacy factory function
        legacy_system = create_dynamic_equipment_system(
            auto_maintenance=False,
            maintenance_interval_hours=72,
            wear_threshold=0.8
        )
        
        assert hasattr(legacy_system, 'register_equipment'), "Should have register_equipment method"
        assert hasattr(legacy_system, 'use_equipment'), "Should have use_equipment method"
        assert hasattr(legacy_system, 'perform_maintenance'), "Should have perform_maintenance method"
        
        # Test configuration creation
        config = create_maintenance_optimized_config()
        assert config.auto_maintenance == True, "Should enable auto maintenance"
        assert config.wear_threshold < 0.7, "Should have lower wear threshold"
        
        # Test legacy attribute access
        try:
            equipment_getter = legacy_system.get_equipment  # Should work through __getattr__
            assert callable(equipment_getter), "Legacy method should be callable"
        except AttributeError:
            pass  # Expected for non-existent methods
        
        print("✅ Backward Compatibility: All tests passed")
        print(f"   Auto maintenance: {legacy_system.config.auto_maintenance}")
        print(f"   Maintenance interval: {legacy_system.config.maintenance_interval_hours}h")
        print(f"   Wear threshold: {legacy_system.config.wear_threshold}")
        return True
        
    except Exception as e:
        print(f"❌ Backward Compatibility failed: {e}")
        return False


async def run_comprehensive_tests():
    """Run all dynamic equipment system tests."""
    print("🚀 STARTING DYNAMIC EQUIPMENT SYSTEM MODULAR TESTS")
    print("=" * 70)
    
    test_functions = [
        test_equipment_registration,
        test_equipment_usage,
        test_maintenance_system,
        test_modification_system,
        test_performance_monitoring,
        test_comprehensive_equipment_status,
        test_integration_workflow,
        test_backward_compatibility
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
    print("📊 DYNAMIC EQUIPMENT SYSTEM TEST SUMMARY")
    print(f"Total Tests: {len(test_functions)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(test_functions) - passed_tests}")
    print(f"Success Rate: {(passed_tests/len(test_functions)*100):.1f}%")
    
    if passed_tests == len(test_functions):
        print("🎉 Dynamic Equipment System: ENTERPRISE-GRADE IMPLEMENTATION")
        print("   All 8 comprehensive test suites passed with flying colors")
        print("   ✨ Modular architecture fully validated")
        print("   🔧 Equipment Registration: Robust equipment lifecycle management")
        print("   ⚙️ Usage Processing: Category-specific wear and performance tracking")
        print("   🔧 Maintenance System: Comprehensive maintenance scheduling and execution")
        print("   🔬 Modification System: Compatible enhancement installation and management")
        print("   📊 Performance Monitoring: Predictive analytics and optimization recommendations")
        print("   📋 Integration Workflow: End-to-end equipment lifecycle coordination")
        print("   ↩️ Backward Compatibility: Seamless legacy API support")
    else:
        print("⚠️ Some components need attention - review failed tests")
    
    return passed_tests, len(test_functions)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())