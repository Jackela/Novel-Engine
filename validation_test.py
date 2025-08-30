#!/usr/bin/env python3
"""
Validation Test for Refactored DirectorAgent Architecture

This script validates that the refactored DirectorAgent maintains
all public API methods and can be imported successfully.
"""

import sys
import traceback


def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")

    try:
        # Test core module imports
        from src.core.turn_manager import TurnManager

        print("✓ TurnManager imported successfully")

        from src.core.narrative_processor import NarrativeProcessor

        print("✓ NarrativeProcessor imported successfully")

        from src.core.iron_laws_processor import IronLawsProcessor

        print("✓ IronLawsProcessor imported successfully")

        from src.core.simulation_coordinator import SimulationCoordinator

        print("✓ SimulationCoordinator imported successfully")

        # Test that existing modules still work
        from src.core.campaign_logger import CampaignLogger

        print("✓ CampaignLogger imported successfully")

        from src.core.world_state_manager import WorldStateManager

        print("✓ WorldStateManager imported successfully")

        from src.core.agent_coordinator import AgentCoordinator

        print("✓ AgentCoordinator imported successfully")

        print("All core module imports successful!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during imports: {e}")
        traceback.print_exc()
        return False


def test_refactored_director():
    """Test that the refactored DirectorAgent can be imported and instantiated."""
    print("\nTesting refactored DirectorAgent...")

    try:
        # Import dependencies first
        # Try to import the refactored DirectorAgent
        from director_agent_refactored import DirectorAgent

        from src.event_bus import EventBus

        print("✓ Refactored DirectorAgent imported successfully")

        # Test instantiation
        event_bus = EventBus()
        director = DirectorAgent(event_bus=event_bus)
        print("✓ DirectorAgent instantiated successfully")

        # Test that key public methods exist
        public_methods = [
            "register_agent",
            "remove_agent",
            "run_turn",
            "log_event",
            "get_simulation_status",
            "get_agent_list",
            "save_world_state",
            "close_campaign_log",
            "generate_narrative_context",
        ]

        for method_name in public_methods:
            if hasattr(director, method_name):
                method = getattr(director, method_name)
                if callable(method):
                    print(f"✓ Method {method_name} exists and is callable")
                else:
                    print(f"❌ Method {method_name} exists but is not callable")
                    return False
            else:
                print(f"❌ Method {method_name} not found")
                return False

        # Test that key properties exist
        properties = [
            "current_turn_number",
            "total_actions_processed",
            "registered_agents",
            "world_state_data",
            "story_state",
        ]

        for prop_name in properties:
            if hasattr(director, prop_name):
                print(f"✓ Property {prop_name} exists")
            else:
                print(f"❌ Property {prop_name} not found")
                return False

        print("All public API methods and properties verified!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False


def test_factory_functions():
    """Test that factory functions work correctly."""
    print("\nTesting factory functions...")

    try:
        from director_agent_refactored import (
            create_director_with_agents,
            run_simulation_batch,
        )

        print("✓ Factory functions imported successfully")

        # Test director creation
        create_director_with_agents()
        print("✓ create_director_with_agents works")

        # Test that run_simulation_batch is callable
        if callable(run_simulation_batch):
            print("✓ run_simulation_batch is callable")
        else:
            print("❌ run_simulation_batch is not callable")
            return False

        return True

    except Exception as e:
        print(f"❌ Factory function test error: {e}")
        traceback.print_exc()
        return False


def validate_line_count():
    """Validate that the refactored file is under 500 lines."""
    print("\nValidating line count...")

    try:
        with open("director_agent_refactored.py", "r") as f:
            lines = f.readlines()
            line_count = len(lines)

        print(f"Refactored DirectorAgent line count: {line_count}")

        if line_count < 500:
            print(f"✓ Line count {line_count} is under 500 lines target")
            return True
        else:
            print(f"❌ Line count {line_count} exceeds 500 lines target")
            return False

    except Exception as e:
        print(f"❌ Error checking line count: {e}")
        return False


def main():
    """Run all validation tests."""
    print("=== DirectorAgent Refactoring Validation ===\n")

    tests = [
        ("Module Imports", test_imports),
        ("Refactored DirectorAgent", test_refactored_director),
        ("Factory Functions", test_factory_functions),
        ("Line Count Validation", validate_line_count),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")

    print("\n=== VALIDATION SUMMARY ===")
    print(f"Passed: {passed}/{total} tests")

    if passed == total:
        print("🎉 ALL VALIDATIONS PASSED! Refactoring successful.")
        return True
    else:
        print("⚠️  Some validations failed. Review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
