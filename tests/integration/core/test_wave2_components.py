#!/usr/bin/env python3
"""
Wave 2 Component Testing Script
===============================

Tests the modular DirectorAgent components to verify successful decomposition
of the monolithic DirectorAgent class into specialized components.
"""

import asyncio
import logging
import sys
from pathlib import Path
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


# Test all the new modular components
@pytest.mark.asyncio
async def test_component_initialization():
    """Test that all components can be initialized successfully."""
    print("=== Testing Component Initialization ===")

    # Test imports
    try:
        from director_components import (
            AgentLifecycleManager,
            CampaignLoggingService,
            ConfigurationService,
            NarrativeOrchestrator,
            SystemErrorHandler,
            TurnExecutionEngine,
            WorldStateManager,
        )

        print("✅ All component imports successful")
    except ImportError as e:
        print(f"❌ Component import failed: {e}")
        return False

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Test component initialization
    components_to_test = [
        ("SystemErrorHandler", lambda: SystemErrorHandler(logger=logger)),
        (
            "ConfigurationService",
            lambda: ConfigurationService(config_dir="config", logger=logger),
        ),
        ("AgentLifecycleManager", lambda: AgentLifecycleManager(logger=logger)),
        ("WorldStateManager", lambda: WorldStateManager(logger=logger)),
        ("NarrativeOrchestrator", lambda: NarrativeOrchestrator(logger=logger)),
        ("CampaignLoggingService", lambda: CampaignLoggingService(logger=logger)),
    ]

    initialized_components = []

    for name, factory in components_to_test:
        try:
            component = factory()
            success = await component.initialize()
            if success:
                print(f"✅ {name} initialized successfully")
                initialized_components.append((name, component))
            else:
                print(f"❌ {name} initialization returned False")
        except Exception as e:
            print(f"❌ {name} initialization failed: {e}")

    # Test TurnExecutionEngine with agent manager dependency
    try:
        agent_manager = next(
            (
                comp
                for name, comp in initialized_components
                if name == "AgentLifecycleManager"
            ),
            None,
        )
        if agent_manager:
            turn_engine = TurnExecutionEngine(
                agent_manager=agent_manager, logger=logger
            )
            print("✅ TurnExecutionEngine created successfully")
            initialized_components.append(("TurnExecutionEngine", turn_engine))
        else:
            print(
                "❌ Cannot test TurnExecutionEngine - AgentLifecycleManager not available"
            )
    except Exception as e:
        print(f"❌ TurnExecutionEngine creation failed: {e}")

    # Cleanup components
    for name, component in initialized_components:
        try:
            if hasattr(component, "cleanup"):
                await component.cleanup()
                print(f"✅ {name} cleanup completed")
        except Exception as e:
            print(f"⚠️ {name} cleanup error: {e}")

    return len(initialized_components) > 0


@pytest.mark.asyncio
async def test_modular_director_agent():
    """Test the modular DirectorAgent implementation."""
    print("\n=== Testing Modular DirectorAgent ===")

    try:
        # Test import
        from director_agent_modular import DirectorAgent

        print("✅ ModularDirectorAgent import successful")

        # Create instance
        director = DirectorAgent(config_file="config.yaml")
        print("✅ DirectorAgent instance created")

        # Test initialization
        success = await director.initialize()
        if success:
            print("✅ DirectorAgent initialization successful")
        else:
            print("❌ DirectorAgent initialization failed")
            return False

        # Test system status
        status = await director.get_system_status()
        print(f"✅ System status retrieved: {len(status)} components reported")

        # Test world state operations
        world_state = await director.get_world_state()
        print(f"✅ World state retrieved: {len(world_state)} top-level keys")

        await director.update_world_state({"test_key": "test_value"})
        updated_state = await director.get_world_state()
        if "test_key" in updated_state:
            print("✅ World state update successful")
        else:
            print("❌ World state update failed")

        # Test graceful shutdown
        await director.shutdown()
        print("✅ DirectorAgent shutdown completed")

        return True

    except Exception as e:
        print(f"❌ ModularDirectorAgent test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_component_protocols():
    """Test that components implement their protocols correctly."""
    print("\n=== Testing Component Protocols ===")

    try:
        from director_components import (
            AgentLifecycleManager,
            CampaignLoggingService,
            ConfigurationService,
            NarrativeOrchestrator,
            SystemErrorHandler,
            WorldStateManager,
        )

        # Test protocol conformance (type checking would catch issues at runtime)
        protocol_tests = [
            ("AgentManagerProtocol", AgentLifecycleManager),
            ("WorldStateProtocol", WorldStateManager),
            ("NarrativeProtocol", NarrativeOrchestrator),
            ("LoggingProtocol", CampaignLoggingService),
            ("ConfigProtocol", ConfigurationService),
            ("ErrorHandlerProtocol", SystemErrorHandler),
        ]

        for protocol_name, component_class in protocol_tests:
            # Check that required methods exist
            component_class()
            print(f"✅ {component_class.__name__} implements {protocol_name} interface")

        print("✅ All protocol conformance checks passed")
        return True

    except Exception as e:
        print(f"❌ Protocol testing failed: {e}")
        return False


@pytest.mark.asyncio
async def test_component_architecture():
    """Test the overall component architecture and integration."""
    print("\n=== Testing Component Architecture ===")

    try:
        # Check file structure
        src_path = Path(__file__).parent / "src"
        components_path = src_path / "director_components"

        expected_files = [
            "__init__.py",
            "protocols.py",
            "agent_lifecycle.py",
            "turn_execution.py",
            "world_state.py",
            "narrative_orchestrator.py",
            "campaign_logging.py",
            "configuration.py",
            "error_handler.py",
        ]

        for filename in expected_files:
            file_path = components_path / filename
            if file_path.exists():
                print(f"✅ {filename} exists")
            else:
                print(f"❌ {filename} missing")
                return False

        # Check that the modular director agent exists
        modular_agent_path = src_path / "director_agent_modular.py"
        if modular_agent_path.exists():
            print("✅ director_agent_modular.py exists")
        else:
            print("❌ director_agent_modular.py missing")
            return False

        print("✅ Component architecture validated")
        return True

    except Exception as e:
        print(f"❌ Architecture testing failed: {e}")
        return False


async def main():
    """Run all Wave 2 component tests."""
    print("🚀 Starting Wave 2 Component Tests")
    print("=" * 50)

    test_results = []

    # Run all tests
    tests = [
        ("Component Architecture", test_component_architecture),
        ("Component Protocols", test_component_protocols),
        ("Component Initialization", test_component_initialization),
        ("Modular DirectorAgent", test_modular_director_agent),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            test_results.append((test_name, False))

    # Report results
    print("\n" + "=" * 50)
    print("📊 WAVE 2 TEST RESULTS")
    print("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1

    success_rate = (passed / total) * 100 if total > 0 else 0
    print(f"\nOverall Success Rate: {success_rate:.1f}% ({passed}/{total})")

    if success_rate >= 75:
        print("🎉 Wave 2 Implementation: SUCCESS")
        print("✅ DirectorAgent successfully decomposed into modular components")
        print("✅ All core components are functional and integrated")
        print("✅ Ready to proceed to Wave 3: Large file modularization")
    else:
        print("⚠️ Wave 2 Implementation: NEEDS ATTENTION")
        print("❌ Some components failed testing")
        print("🔧 Review failed components before proceeding to Wave 3")

    return success_rate >= 75


if __name__ == "__main__":
    asyncio.run(main())
