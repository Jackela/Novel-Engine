#!/usr/bin/env python3
"""
Simple Validation Test for Refactored DirectorAgent Architecture
"""

import sys
import traceback

def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")
    
    try:
        # Test core module imports
        from src.core.turn_manager import TurnManager
        print("PASS: TurnManager imported successfully")
        
        from src.core.narrative_processor import NarrativeProcessor
        print("PASS: NarrativeProcessor imported successfully")
        
        from src.core.iron_laws_processor import IronLawsProcessor
        print("PASS: IronLawsProcessor imported successfully")
        
        from src.core.simulation_coordinator import SimulationCoordinator
        print("PASS: SimulationCoordinator imported successfully")
        
        # Test that existing modules still work
        from src.core.campaign_logger import CampaignLogger
        print("PASS: CampaignLogger imported successfully")
        
        from src.core.world_state_manager import WorldStateManager
        print("PASS: WorldStateManager imported successfully")
        
        from src.core.agent_coordinator import AgentCoordinator
        print("PASS: AgentCoordinator imported successfully")
        
        print("SUCCESS: All core module imports successful!")
        return True
        
    except ImportError as e:
        print(f"FAIL: Import error: {e}")
        return False
    except Exception as e:
        print(f"FAIL: Unexpected error during imports: {e}")
        return False

def test_line_count():
    """Test that the refactored file is under 500 lines."""
    print("\nTesting line count...")
    
    try:
        with open('director_agent_refactored.py', 'r') as f:
            lines = f.readlines()
            line_count = len(lines)
        
        print(f"Refactored DirectorAgent line count: {line_count}")
        
        if line_count < 500:
            print(f"PASS: Line count {line_count} is under 500 lines target")
            return True
        else:
            print(f"FAIL: Line count {line_count} exceeds 500 lines target")
            return False
            
    except Exception as e:
        print(f"FAIL: Error checking line count: {e}")
        return False

def test_structure():
    """Test the basic structure of refactored modules."""
    print("\nTesting module structure...")
    
    try:
        # Check that new modules have expected classes
        from src.core.turn_manager import TurnManager
        from src.core.narrative_processor import NarrativeProcessor
        from src.core.iron_laws_processor import IronLawsProcessor
        from src.core.simulation_coordinator import SimulationCoordinator
        
        # Test that classes can be instantiated
        from src.event_bus import EventBus
        event_bus = EventBus()
        
        turn_manager = TurnManager(event_bus, 100)
        print("PASS: TurnManager instantiated")
        
        narrative_processor = NarrativeProcessor()
        print("PASS: NarrativeProcessor instantiated")
        
        iron_laws_processor = IronLawsProcessor()
        print("PASS: IronLawsProcessor instantiated")
        
        simulation_coordinator = SimulationCoordinator()
        print("PASS: SimulationCoordinator instantiated")
        
        print("SUCCESS: All module structures validated!")
        return True
        
    except Exception as e:
        print(f"FAIL: Structure test error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run validation tests."""
    print("=== DirectorAgent Refactoring Validation ===")
    
    tests = [
        ("Module Imports", test_imports),
        ("Line Count", test_line_count), 
        ("Module Structure", test_structure)
    ]
    
    passed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            print(f"PASS: {test_name}")
        else:
            print(f"FAIL: {test_name}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Passed: {passed}/{len(tests)} tests")
    
    if passed == len(tests):
        print("SUCCESS: All validations passed!")
        return True
    else:
        print("WARNING: Some validations failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)