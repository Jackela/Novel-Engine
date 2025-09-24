#!/usr/bin/env python3
"""
Component Integration Test Suite.

Tests individual components and their integration for production readiness.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ComponentTestResult:
    """Result from a component test."""

    component: str
    success: bool
    duration: float
    message: str
    details: Dict[str, Any] = None


class ComponentIntegrationTester:
    """Test suite for component integration validation."""

    def __init__(self):
        self.results: List[ComponentTestResult] = []

    def log_result(self, result: ComponentTestResult):
        """Log and store test result."""
        self.results.append(result)
        status = "PASS" if result.success else "FAIL"
        logger.info(
            f"[{status}] {result.component}: {result.message} ({result.duration:.3f}s)"
        )

    def test_event_bus(self) -> ComponentTestResult:
        """Test EventBus component."""
        start_time = time.time()
        try:
            from src.event_bus import EventBus

            # Initialize EventBus
            event_bus = EventBus()

            # Test event publishing and subscribing
            received_events = []

            def event_handler(event_data):
                received_events.append(event_data)

            event_bus.subscribe("test_event", event_handler)
            event_bus.publish("test_event", {"test": "data"})

            # Give some time for event processing
            time.sleep(0.1)

            success = (
                len(received_events) == 1
                and received_events[0]["test"] == "data"
            )
            duration = time.time() - start_time

            return ComponentTestResult(
                "EventBus",
                success,
                duration,
                f"Event handling {'successful' if success else 'failed'}",
                {"events_received": len(received_events)},
            )
        except Exception as e:
            duration = time.time() - start_time
            return ComponentTestResult(
                "EventBus", False, duration, f"Error: {e}"
            )

    def test_character_factory(self) -> ComponentTestResult:
        """Test CharacterFactory component."""
        start_time = time.time()
        try:
            from character_factory import CharacterFactory

            from src.event_bus import EventBus

            # Initialize with EventBus
            event_bus = EventBus()
            character_factory = CharacterFactory(event_bus)

            # Test character listing
            characters = character_factory.list_available_characters()

            # Test character creation
            if characters:
                character = character_factory.create_character(characters[0])
                char_created = character is not None
            else:
                char_created = False

            success = len(characters) > 0 and char_created
            duration = time.time() - start_time

            return ComponentTestResult(
                "CharacterFactory",
                success,
                duration,
                f"Found {len(characters)} characters, creation {'successful' if char_created else 'failed'}",
                {
                    "character_count": len(characters),
                    "characters": characters[:3],
                },
            )
        except Exception as e:
            duration = time.time() - start_time
            return ComponentTestResult(
                "CharacterFactory", False, duration, f"Error: {e}"
            )

    def test_director_agent(self) -> ComponentTestResult:
        """Test DirectorAgent component."""
        start_time = time.time()
        try:
            from character_factory import CharacterFactory
            from director_agent import DirectorAgent

            from src.event_bus import EventBus

            # Initialize components
            event_bus = EventBus()
            director_agent = DirectorAgent(event_bus)
            character_factory = CharacterFactory(event_bus)

            # Test agent registration
            characters = character_factory.list_available_characters()
            if not characters:
                return ComponentTestResult(
                    "DirectorAgent",
                    False,
                    time.time() - start_time,
                    "No characters available for testing",
                )

            # Create and register a character
            character = character_factory.create_character(characters[0])
            registration_success = director_agent.register_agent(character)

            # Test agent listing
            registered_agents = director_agent.list_agents()

            success = registration_success and len(registered_agents) > 0
            duration = time.time() - start_time

            return ComponentTestResult(
                "DirectorAgent",
                success,
                duration,
                f"Agent registration {'successful' if registration_success else 'failed'}, {len(registered_agents)} agents",
                {"agents_registered": len(registered_agents)},
            )
        except Exception as e:
            duration = time.time() - start_time
            return ComponentTestResult(
                "DirectorAgent", False, duration, f"Error: {e}"
            )

    def test_chronicler_agent(self) -> ComponentTestResult:
        """Test ChroniclerAgent component."""
        start_time = time.time()
        try:
            from chronicler_agent import ChroniclerAgent

            # Initialize ChroniclerAgent
            chronicler = ChroniclerAgent()

            # Test basic functionality
            test_data = "Test narrative content for chronicler validation"
            result = chronicler.process_narrative(test_data)

            success = result is not None and len(str(result)) > 0
            duration = time.time() - start_time

            return ComponentTestResult(
                "ChroniclerAgent",
                success,
                duration,
                f"Narrative processing {'successful' if success else 'failed'}",
                {"result_length": len(str(result)) if result else 0},
            )
        except Exception as e:
            duration = time.time() - start_time
            return ComponentTestResult(
                "ChroniclerAgent", False, duration, f"Error: {e}"
            )

    def test_config_loader(self) -> ComponentTestResult:
        """Test configuration loading."""
        start_time = time.time()
        try:
            from config_loader import get_config

            # Test configuration loading
            config = get_config()

            # Verify config has expected structure
            has_required_keys = all(
                key in config for key in ["llm", "campaign_log"]
            )

            success = config is not None and has_required_keys
            duration = time.time() - start_time

            return ComponentTestResult(
                "ConfigLoader",
                success,
                duration,
                f"Configuration {'loaded successfully' if success else 'failed to load'}",
                {"config_keys": list(config.keys()) if config else []},
            )
        except Exception as e:
            duration = time.time() - start_time
            return ComponentTestResult(
                "ConfigLoader", False, duration, f"Error: {e}"
            )

    def test_memory_system(self) -> ComponentTestResult:
        """Test memory system components."""
        start_time = time.time()
        try:
            from src.memory.layered_memory import LayeredMemorySystem

            # Initialize memory system
            memory_system = LayeredMemorySystem()

            # Test memory operations
            test_memory = {
                "content": "Test memory content",
                "importance": 0.5,
                "timestamp": datetime.now(),
            }

            # Store memory
            memory_id = memory_system.store_memory("test_agent", test_memory)

            # Retrieve memory
            retrieved = memory_system.retrieve_memories("test_agent", limit=1)

            success = memory_id is not None and len(retrieved) > 0
            duration = time.time() - start_time

            return ComponentTestResult(
                "MemorySystem",
                success,
                duration,
                f"Memory operations {'successful' if success else 'failed'}",
                {
                    "memory_id": str(memory_id),
                    "retrieved_count": len(retrieved),
                },
            )
        except Exception as e:
            duration = time.time() - start_time
            return ComponentTestResult(
                "MemorySystem", False, duration, f"Error: {e}"
            )

    def test_simulation_integration(self) -> ComponentTestResult:
        """Test complete simulation integration."""
        start_time = time.time()
        try:
            from character_factory import CharacterFactory
            from director_agent import DirectorAgent

            from src.event_bus import EventBus

            # Initialize all components
            event_bus = EventBus()
            director_agent = DirectorAgent(event_bus)
            character_factory = CharacterFactory(event_bus)

            # Get characters
            characters = character_factory.list_available_characters()
            if len(characters) < 2:
                return ComponentTestResult(
                    "SimulationIntegration",
                    False,
                    time.time() - start_time,
                    "Insufficient characters for simulation test",
                )

            # Create and register characters
            agents = []
            for char_name in characters[:2]:
                character = character_factory.create_character(char_name)
                if character:
                    director_agent.register_agent(character)
                    agents.append(character)

            if len(agents) < 2:
                return ComponentTestResult(
                    "SimulationIntegration",
                    False,
                    time.time() - start_time,
                    "Failed to create required characters",
                )

            # Test simulation execution
            try:
                simulation_result = director_agent.run_simulation(
                    turns=1, timeout=30
                )
                simulation_success = simulation_result is not None
            except Exception as sim_error:
                logger.warning(f"Simulation execution failed: {sim_error}")
                simulation_success = False

            # Check if campaign log was updated
            campaign_log_updated = len(director_agent.get_campaign_log()) > 100

            success = len(agents) >= 2 and campaign_log_updated
            duration = time.time() - start_time

            return ComponentTestResult(
                "SimulationIntegration",
                success,
                duration,
                f"Integration test {'successful' if success else 'failed'} - {len(agents)} agents, simulation: {'ok' if simulation_success else 'failed'}",
                {
                    "agents_created": len(agents),
                    "simulation_executed": simulation_success,
                    "campaign_log_updated": campaign_log_updated,
                },
            )
        except Exception as e:
            duration = time.time() - start_time
            return ComponentTestResult(
                "SimulationIntegration", False, duration, f"Error: {e}"
            )

    def run_comprehensive_component_test(self) -> Dict[str, Any]:
        """Run complete component integration test suite."""
        logger.info("Starting comprehensive component integration testing...")
        test_start = time.time()

        # Run all component tests
        self.log_result(self.test_config_loader())
        self.log_result(self.test_event_bus())
        self.log_result(self.test_character_factory())
        self.log_result(self.test_director_agent())
        self.log_result(self.test_chronicler_agent())
        self.log_result(self.test_memory_system())
        self.log_result(self.test_simulation_integration())

        # Calculate metrics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        total_duration = time.time() - test_start
        success_rate = (passed_tests / total_tests) * 100

        # Determine readiness
        critical_components = [
            "ConfigLoader",
            "EventBus",
            "CharacterFactory",
            "DirectorAgent",
        ]
        critical_success = all(
            any(r.success for r in self.results if r.component == comp)
            for comp in critical_components
        )

        component_ready = success_rate >= 80.0 and critical_success

        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_duration_seconds": total_duration,
            "component_status": "READY" if component_ready else "NOT_READY",
            "component_ready": component_ready,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": success_rate,
            },
            "component_results": [
                {
                    "component": r.component,
                    "success": r.success,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details or {},
                }
                for r in self.results
            ],
            "critical_components": {
                comp: any(
                    r.success for r in self.results if r.component == comp
                )
                for comp in critical_components
            },
        }

        logger.info(
            f"Component testing complete: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)"
        )
        return report


def main():
    """Main execution function."""
    tester = ComponentIntegrationTester()

    # Run comprehensive component test
    report = tester.run_comprehensive_component_test()

    # Save report
    report_file = f"component_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("COMPONENT INTEGRATION TEST RESULTS")
    print("=" * 80)
    print(f"Component Status: {report['component_status']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(
        f"Tests Passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']}"
    )

    print("\nComponent Test Results:")
    for result in report["component_results"]:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"  {result['component']}: {status} - {result['message']}")

    print(f"\nReport saved to: {report_file}")

    if report["component_ready"]:
        print("\n🎉 COMPONENTS ARE INTEGRATION READY")
        return 0
    else:
        print("\n⚠️  COMPONENT INTEGRATION ISSUES DETECTED")
        return 1


if __name__ == "__main__":
    exit(main())
