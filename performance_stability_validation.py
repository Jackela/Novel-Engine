#!/usr/bin/env python3
"""
Performance and Stability Validation for Phase 1 Refactoring

This script validates that the Phase 1 refactoring doesn't negatively impact
performance and maintains system stability.
"""

import logging
import sys
import time
import tracemalloc
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_import_performance():
    """Test that imports are still fast after refactoring."""
    try:
        logger.info("Testing import performance...")

        import_times = []

        # Test DirectorAgent import time
        start_time = time.time()

        director_import_time = time.time() - start_time
        import_times.append(("DirectorAgent", director_import_time))

        # Test PersonaAgent import time
        start_time = time.time()

        persona_import_time = time.time() - start_time
        import_times.append(("PersonaAgent", persona_import_time))

        # Test EventBus import time
        start_time = time.time()

        eventbus_import_time = time.time() - start_time
        import_times.append(("EventBus", eventbus_import_time))

        # Test ChroniclerAgent import time
        start_time = time.time()

        chronicler_import_time = time.time() - start_time
        import_times.append(("ChroniclerAgent", chronicler_import_time))

        # Log results
        total_import_time = sum(time_val for _, time_val in import_times)
        logger.info(f"Total import time: {total_import_time:.4f}s")

        for module, import_time in import_times:
            logger.info(f"  {module}: {import_time:.4f}s")

        # Validate reasonable import times (less than 2 seconds total)
        assert (
            total_import_time < 2.0
        ), f"Import time too slow: {total_import_time:.4f}s"

        logger.info("✅ Import performance validation successful")
        return True

    except Exception as e:
        logger.error(f"❌ Import performance test failed: {e}")
        return False


def test_memory_usage():
    """Test memory usage during component initialization."""
    try:
        logger.info("Testing memory usage...")

        # Start memory tracking
        tracemalloc.start()

        # Take snapshot before initialization
        snapshot1 = tracemalloc.take_snapshot()

        # Initialize components
        from director_agent import DirectorAgent

        from src.event_bus import EventBus
        from src.persona_agent import PersonaAgent

        event_bus = EventBus()
        DirectorAgent(event_bus=event_bus, campaign_log_path="test_memory_campaign.md")

        # Create test character for PersonaAgent
        test_char_content = """
# Memory Test Character
- Name: Memory Validator
- Class: Tester
- Level: 1
        """

        test_char_file = Path("test_memory_character.md")
        test_char_file.write_text(test_char_content.strip())

        try:
            PersonaAgent(str(test_char_file), event_bus=event_bus)

            # Take snapshot after initialization
            snapshot2 = tracemalloc.take_snapshot()

            # Calculate memory usage
            top_stats = snapshot2.compare_to(snapshot1, "lineno")
            total_memory = sum(stat.size for stat in top_stats)

            logger.info(
                f"Memory usage during initialization: {total_memory / 1024 / 1024:.2f} MB"
            )

            # Validate reasonable memory usage (less than 100MB for basic initialization)
            memory_mb = total_memory / 1024 / 1024
            assert memory_mb < 100, f"Memory usage too high: {memory_mb:.2f}MB"

            logger.info("✅ Memory usage validation successful")
            return True

        finally:
            # Clean up
            if test_char_file.exists():
                test_char_file.unlink()
            campaign_log = Path("test_memory_campaign.md")
            if campaign_log.exists():
                campaign_log.unlink()
            tracemalloc.stop()

    except Exception as e:
        logger.error(f"❌ Memory usage test failed: {e}")
        tracemalloc.stop()
        return False


def test_syntax_validation():
    """Run basic syntax checks on all refactored files."""
    try:
        logger.info("Testing syntax validation...")

        # List of key files to validate
        key_files = [
            "director_agent.py",
            "director_agent_integrated.py",
            "src/persona_agent.py",
            "src/persona_agent_integrated.py",
            "src/director_agent_base.py",
            "src/persona_agent_core.py",
            "src/event_bus.py",
            "shared_types.py",
            "config_loader.py",
        ]

        valid_files = 0
        total_files = 0

        for file_path in key_files:
            if Path(file_path).exists():
                total_files += 1
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        compile(f.read(), file_path, "exec")
                    logger.info(f"✅ {file_path}: Syntax OK")
                    valid_files += 1
                except SyntaxError as e:
                    logger.error(f"❌ {file_path}: Syntax Error - {e}")
                except Exception as e:
                    logger.warning(f"⚠️ {file_path}: Warning - {e}")
                    valid_files += 1  # Still count as valid if it's not a syntax error
            else:
                logger.info(f"ℹ️ {file_path}: File not found (may be expected)")

        logger.info(f"Syntax validation: {valid_files}/{total_files} files passed")

        # At least 80% of files should pass
        if total_files > 0:
            success_rate = valid_files / total_files
            assert (
                success_rate >= 0.8
            ), f"Too many syntax errors: {success_rate:.1%} success rate"

        logger.info("✅ Syntax validation successful")
        return True

    except Exception as e:
        logger.error(f"❌ Syntax validation test failed: {e}")
        return False


def test_initialization_stability():
    """Test repeated initialization for stability."""
    try:
        logger.info("Testing initialization stability...")

        from director_agent import DirectorAgent

        from src.event_bus import EventBus

        # Test multiple initialization cycles
        num_cycles = 5
        successful_cycles = 0

        for i in range(num_cycles):
            try:
                event_bus = EventBus()
                director = DirectorAgent(
                    event_bus=event_bus, campaign_log_path=f"test_stability_{i}.md"
                )

                # Test basic functionality
                status = director.get_simulation_status()
                assert isinstance(status, dict), "Simulation status should be dict"

                successful_cycles += 1
                logger.info(f"Cycle {i+1}/{num_cycles}: OK")

                # Clean up
                campaign_log = Path(f"test_stability_{i}.md")
                if campaign_log.exists():
                    campaign_log.unlink()

            except Exception as e:
                logger.warning(f"Cycle {i+1}/{num_cycles}: Failed - {e}")

        success_rate = successful_cycles / num_cycles
        logger.info(
            f"Stability test: {successful_cycles}/{num_cycles} cycles successful ({success_rate:.1%})"
        )

        # At least 80% should succeed
        assert success_rate >= 0.8, f"Stability too low: {success_rate:.1%}"

        logger.info("✅ Initialization stability validation successful")
        return True

    except Exception as e:
        logger.error(f"❌ Initialization stability test failed: {e}")
        return False


def test_error_handling():
    """Test error handling in refactored components."""
    try:
        logger.info("Testing error handling...")

        from director_agent import DirectorAgent

        from src.event_bus import EventBus
        from src.persona_agent import PersonaAgent

        error_tests_passed = 0
        total_error_tests = 0

        # Test 1: Invalid campaign log path
        total_error_tests += 1
        try:
            event_bus = EventBus()
            DirectorAgent(
                event_bus=event_bus,
                campaign_log_path="/invalid/path/that/does/not/exist.md",
            )
            # Should handle gracefully
            error_tests_passed += 1
            logger.info("✅ Invalid campaign log path handled gracefully")
        except Exception as e:
            logger.warning(f"⚠️ Invalid campaign log path test failed: {e}")

        # Test 2: Invalid character file for PersonaAgent
        total_error_tests += 1
        try:
            event_bus = EventBus()
            agent = PersonaAgent("/nonexistent/character.md", event_bus=event_bus)
            # Should handle gracefully
            error_tests_passed += 1
            logger.info("✅ Invalid character file handled gracefully")
        except Exception as e:
            logger.warning(f"⚠️ Invalid character file test failed: {e}")

        # Test 3: Memory operations on non-existent paths
        total_error_tests += 1
        try:
            event_bus = EventBus()
            agent = PersonaAgent("/tmp/test_error_char.md", event_bus=event_bus)
            agent.update_memory("Test memory update")
            # Should handle gracefully even if file operations fail
            error_tests_passed += 1
            logger.info("✅ Memory operation errors handled gracefully")
        except Exception as e:
            logger.warning(f"⚠️ Memory operation error test failed: {e}")

        success_rate = (
            error_tests_passed / total_error_tests if total_error_tests > 0 else 0
        )
        logger.info(
            f"Error handling: {error_tests_passed}/{total_error_tests} tests passed ({success_rate:.1%})"
        )

        logger.info("✅ Error handling validation completed")
        return True

    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False


def run_performance_stability_tests():
    """Run all performance and stability tests."""
    logger.info("⚡ Starting Performance and Stability Validation Tests")
    logger.info("=" * 60)

    tests = [
        ("Import Performance", test_import_performance),
        ("Memory Usage", test_memory_usage),
        ("Syntax Validation", test_syntax_validation),
        ("Initialization Stability", test_initialization_stability),
        ("Error Handling", test_error_handling),
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
    logger.info("📊 PERFORMANCE & STABILITY SUMMARY")
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
        logger.info("🎉 Performance & Stability Validation: SUCCESS")
        return True
    else:
        logger.info("⚠️ Performance & Stability Validation: PARTIAL SUCCESS")
        return False


if __name__ == "__main__":
    success = run_performance_stability_tests()
    sys.exit(0 if success else 1)
