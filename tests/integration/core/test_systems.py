#!/usr/bin/env python3
"""
Test Core Systems - Error Handling and Logging System Validation
================================================================

Validates the centralized error handling and structured logging systems.
Wave 6.3: Error Handling and Logging System Enhancement
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import core systems
from src.core.error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    get_error_handler,
    handle_error,
)
from src.core.logging_system import (
    LogContext,
    get_logger,
    with_context,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logging_system():
    """Test the structured logging system."""
    print("🧪 Testing Structured Logging System...")

    try:
        # Create logger
        logger = get_logger("test_logger")

        # Test basic logging
        logger.info("Testing basic logging functionality")
        logger.debug("Debug message test")
        logger.success("Success message test")
        logger.warning("Warning message test")

        # Test logging with context
        context = LogContext(
            component="test_component",
            operation="test_operation",
            session_id="test_session_123",
        )

        with with_context(logger, component="test_component", operation="context_test"):
            logger.info("Testing logging with context")
            logger.performance("Performance test", duration_ms=42.5)

        # Test error logging with None component (the fixed issue)
        logger.error(
            "Testing error logging with None component",
            context=LogContext(component=None, operation="test"),
        )

        # Test performance tracking
        with logger.track_performance("test_operation") as tracker:
            await asyncio.sleep(0.01)  # Simulate work
            tracker.add_metric("test_metric", 100)

        # Test audit logging
        logger.audit("Audit trail test", context=context)

        # Test security logging
        logger.security("Security event test", context=context)

        print("✅ Structured logging system working correctly")
        return True

    except Exception as e:
        print(f"❌ Logging system test failed: {e}")
        return False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_system():
    """Test the centralized error handling system."""
    print("🧪 Testing Centralized Error Handling System...")

    try:
        # Get error handler
        error_handler = get_error_handler()

        # Test basic error handling
        context = ErrorContext(
            component="test_component",
            operation="test_operation",
            user_id="test_user",
            session_id="test_session_123",
        )

        # Test different error types
        test_error = ValueError("Test validation error")
        error_record = await error_handler.handle_error(
            error=test_error,
            context=context,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
        )

        print(f"✅ Error handled: {error_record.error_id}")

        # Test network error (auto-retry)
        network_error = ConnectionError("Network connection failed")
        error_record2 = await handle_error(
            error=network_error, component="network_service", operation="api_call"
        )

        print(f"✅ Network error handled: {error_record2.error_id}")

        # Test error statistics
        stats = error_handler.get_error_statistics()
        print(f"✅ Error statistics: {stats['total_errors']} total errors")

        return True

    except Exception as e:
        print(f"❌ Error handling system test failed: {e}")
        return False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration():
    """Test integration between error handling and logging systems."""
    print("🧪 Testing Integration Between Core Systems...")

    try:
        # Create integrated logger
        logger = get_logger("integration_test")
        error_handler = get_error_handler()

        # Test error handling with logging
        context = ErrorContext(
            component="integration_test",
            operation="test_integration",
            metadata={"test_type": "integration"},
        )

        # Simulate application error
        try:
            # Intentional error for testing
            1 / 0
        except ZeroDivisionError as e:
            # Handle error through centralized system
            error_record = await error_handler.handle_error(e, context)

            # Log the error handling result
            logger.error(
                f"Error handled by centralized system: {error_record.error_id}",
                context=LogContext(
                    component="integration_test",
                    operation="error_integration",
                    correlation_id=error_record.error_id,
                ),
            )

        print("✅ Integration between systems working correctly")
        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


async def main():
    """Run all core system tests."""
    print("🚀 Starting Core Systems Validation\n")

    results = []

    # Test logging system
    logging_result = await test_logging_system()
    results.append(("Structured Logging", logging_result))
    print()

    # Test error handling system
    error_result = await test_error_handling_system()
    results.append(("Centralized Error Handling", error_result))
    print()

    # Test integration
    integration_result = await test_integration()
    results.append(("System Integration", integration_result))
    print()

    # Summary
    print("📊 Test Results Summary:")
    print("=" * 50)

    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if not result:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("🎉 All core systems working correctly!")
        print(
            "✅ Wave 6.3 Error Handling and Logging System Enhancement validation complete"
        )
        return True
    else:
        print("⚠️ Some tests failed - please review errors above")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
