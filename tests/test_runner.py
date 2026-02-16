#!/usr/bin/env python3
"""
Novel Engine Test Runner
========================

Comprehensive test suite runner for all Novel Engine components.
Provides coverage reporting and performance benchmarking.
"""

import sys
import time

import pytest

pytestmark = pytest.mark.integration


def run_unit_tests():
    """Run unit tests for all components."""
    print("🧪 Running Unit Tests...")

    args = [
        "tests/",
        "-v",
        "--tb=short",
        "-m",
        "not slow and not integration",
        "--durations=10",
    ]

    result = pytest.main(args)
    return result == 0


def run_integration_tests():
    """Run integration tests."""
    print("🔗 Running Integration Tests...")

    args = ["tests/", "-v", "--tb=short", "-m", "integration", "--durations=10"]

    result = pytest.main(args)
    return result == 0


def run_all_tests():
    """Run all tests with coverage."""
    print("🚀 Running Complete Test Suite...")

    args = ["tests/", "-v", "--tb=short", "--durations=10"]

    result = pytest.main(args)
    return result == 0


def run_performance_tests():
    """Run performance benchmarks."""
    print("⚡ Running Performance Tests...")

    args = ["tests/", "-v", "--tb=short", "-m", "slow", "--durations=0"]

    result = pytest.main(args)
    return result == 0


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py [unit|integration|all|performance]")
        sys.exit(1)

    test_type = sys.argv[1].lower()

    start_time = time.time()

    if test_type == "unit":
        success = run_unit_tests()
    elif test_type == "integration":
        success = run_integration_tests()
    elif test_type == "all":
        success = run_all_tests()
    elif test_type == "performance":
        success = run_performance_tests()
    else:
        print(f"Unknown test type: {test_type}")
        sys.exit(1)

    end_time = time.time()
    duration = end_time - start_time

    print(f"\n{'='*50}")
    print(f"Test execution completed in {duration:.2f} seconds")

    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
