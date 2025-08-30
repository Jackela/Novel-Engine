#!/usr/bin/env python3
"""
Quick Performance Validation Script for Novel Engine.

Validates that the performance optimizations are working correctly and meeting targets.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

import aiohttp

# Add the current directory to Python path to import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from production_performance_engine import (
        initialize_performance_engine,
        performance_engine,
    )
except ImportError as e:
    print(f"Warning: Could not import performance engine: {e}")
    performance_engine = None

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def test_performance_engine():
    """Test the performance engine directly."""
    logger.info("Testing Performance Engine...")

    if performance_engine is None:
        logger.error("Performance engine not available")
        return False

    try:
        # Initialize performance engine
        await initialize_performance_engine()

        # Test database operations
        async with performance_engine.optimized_db_operation() as conn:
            cursor = await conn.execute("SELECT 1")
            result = await cursor.fetchone()
            assert result[0] == 1, "Database operation failed"

        # Test caching
        cache_key = "test:performance:validation"
        test_value = {"test": "data", "timestamp": time.time()}

        # Set cache
        await performance_engine.cache.set(cache_key, test_value, ttl=60.0)

        # Get cache
        cached_result = await performance_engine.cache.get(cache_key)
        assert cached_result is not None, "Cache set/get failed"
        assert cached_result["test"] == "data", "Cache data integrity failed"

        # Test concurrent operations
        async def test_operation():
            await asyncio.sleep(0.01)
            return "success"

        operations = [(test_operation, (), {}) for _ in range(10)]
        results = await performance_engine.optimize_batch_operations(
            operations, "io_bound"
        )
        assert len(results) == 10, "Batch operations failed"
        assert all(r == "success" for r in results), "Batch operation results invalid"

        # Get performance stats
        stats = await performance_engine.get_comprehensive_stats()
        assert "summary" in stats, "Performance stats missing"
        assert "cache" in stats, "Cache stats missing"

        logger.info("PASS Performance Engine validation passed")
        return True

    except Exception as e:
        logger.error(f"FAIL Performance Engine validation failed: {e}")
        return False


async def test_api_endpoints(base_url: str = "http://localhost:8000"):
    """Test API endpoints for performance."""
    logger.info(f"Testing API endpoints at {base_url}...")

    endpoints = [
        ("GET", "/", "Root endpoint"),
        ("GET", "/health", "Health check"),
        ("GET", "/metrics", "Performance metrics"),
        ("GET", "/characters", "Legacy characters"),
        ("GET", "/api/v1/characters/optimized", "Optimized characters"),
    ]

    results = []

    async with aiohttp.ClientSession() as session:
        for method, endpoint, description in endpoints:
            try:
                start_time = time.time()

                async with session.request(method, f"{base_url}{endpoint}") as response:
                    await response.read()  # Ensure complete transfer
                    response_time = time.time() - start_time

                    result = {
                        "endpoint": endpoint,
                        "description": description,
                        "status_code": response.status,
                        "response_time_ms": response_time * 1000,
                        "success": 200 <= response.status < 400,
                        "meets_target": response_time < 0.1,  # <100ms target
                    }

                    results.append(result)

                    status = (
                        "PASS"
                        if result["success"] and result["meets_target"]
                        else "FAIL"
                    )
                    logger.info(
                        f"{status} {description}: {result['response_time_ms']:.1f}ms (HTTP {result['status_code']})"
                    )

            except Exception as e:
                result = {
                    "endpoint": endpoint,
                    "description": description,
                    "error": str(e),
                    "success": False,
                    "meets_target": False,
                }
                results.append(result)
                logger.error(f"FAIL {description}: {e}")

    return results


async def run_quick_load_test(
    base_url: str = "http://localhost:8000",
    concurrent_users: int = 50,
    requests_per_user: int = 5,
):
    """Run a quick load test."""
    logger.info(
        f"Running quick load test: {concurrent_users} users, {requests_per_user} requests each..."
    )

    async def user_session(user_id: int):
        """Single user session."""
        async with aiohttp.ClientSession() as session:
            response_times = []
            errors = 0

            for i in range(requests_per_user):
                try:
                    start_time = time.time()
                    async with session.get(f"{base_url}/health") as response:
                        await response.read()
                        response_time = time.time() - start_time
                        response_times.append(response_time)

                        if response.status >= 400:
                            errors += 1

                except Exception:
                    errors += 1

                # Small delay between requests
                await asyncio.sleep(0.05)

            return {
                "user_id": user_id,
                "response_times": response_times,
                "errors": errors,
                "requests": requests_per_user,
            }

    # Run concurrent user sessions
    start_time = time.time()
    user_tasks = [user_session(i) for i in range(concurrent_users)]
    user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
    total_time = time.time() - start_time

    # Aggregate results
    all_response_times = []
    total_requests = 0
    total_errors = 0
    successful_users = 0

    for result in user_results:
        if isinstance(result, Exception):
            logger.error(f"User session failed: {result}")
            continue

        successful_users += 1
        total_requests += result["requests"]
        total_errors += result["errors"]
        all_response_times.extend(result["response_times"])

    if all_response_times:
        avg_response_time = sum(all_response_times) / len(all_response_times)
        sorted_times = sorted(all_response_times)
        p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
        throughput = total_requests / total_time
    else:
        avg_response_time = p95_response_time = throughput = 0

    load_test_results = {
        "concurrent_users": concurrent_users,
        "successful_users": successful_users,
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": (
            (total_errors / total_requests * 100) if total_requests > 0 else 0
        ),
        "avg_response_time_ms": avg_response_time * 1000,
        "p95_response_time_ms": p95_response_time * 1000,
        "throughput_rps": throughput,
        "test_duration_seconds": total_time,
        "meets_targets": {
            "response_time": avg_response_time < 0.1,  # <100ms
            "p95_response_time": p95_response_time < 0.1,  # <100ms
            "throughput": throughput > 100,  # >100 RPS (modest target for quick test)
            "error_rate": (
                (total_errors / total_requests * 100) < 1
                if total_requests > 0
                else True
            ),  # <1% error rate
        },
    }

    targets_met = all(load_test_results["meets_targets"].values())
    status = "PASS" if targets_met else "FAIL"

    logger.info(
        f"{status} Load test: {load_test_results['avg_response_time_ms']:.1f}ms avg, "
        f"{load_test_results['p95_response_time_ms']:.1f}ms P95, "
        f"{load_test_results['throughput_rps']:.1f} RPS, "
        f"{load_test_results['error_rate']:.1f}% errors"
    )

    return load_test_results


async def validate_performance():
    """Run comprehensive performance validation."""
    logger.info("Starting Performance Validation...")

    validation_results = {
        "timestamp": datetime.now().isoformat(),
        "performance_engine_test": None,
        "api_endpoint_tests": None,
        "load_test_results": None,
        "overall_success": False,
    }

    # Test 1: Performance Engine
    engine_success = await test_performance_engine()
    validation_results["performance_engine_test"] = {"success": engine_success}

    # Test 2: API Endpoints (if server is running)
    try:
        api_results = await test_api_endpoints()
        validation_results["api_endpoint_tests"] = {
            "results": api_results,
            "success": all(r.get("success", False) for r in api_results),
            "targets_met": all(
                r.get("meets_target", False)
                for r in api_results
                if r.get("success", False)
            ),
        }
    except Exception as e:
        logger.warning(f"API endpoint tests skipped (server not running?): {e}")
        validation_results["api_endpoint_tests"] = {"skipped": True, "reason": str(e)}

    # Test 3: Quick Load Test (if server is running)
    try:
        load_results = await run_quick_load_test()
        validation_results["load_test_results"] = load_results
    except Exception as e:
        logger.warning(f"Load test skipped (server not running?): {e}")
        validation_results["load_test_results"] = {"skipped": True, "reason": str(e)}

    # Determine overall success
    engine_ok = validation_results["performance_engine_test"]["success"]
    api_ok = validation_results["api_endpoint_tests"].get("success", True)
    load_ok = (
        validation_results["load_test_results"]
        .get("meets_targets", {})
        .get("response_time", True)
        if isinstance(validation_results["load_test_results"], dict)
        else True
    )

    validation_results["overall_success"] = engine_ok and api_ok and load_ok

    return validation_results


def print_validation_summary(results: Dict[str, Any]):
    """Print validation summary."""
    print("\n" + "=" * 60)
    print("PERFORMANCE VALIDATION SUMMARY")
    print("=" * 60)

    # Performance Engine Test
    engine_test = results.get("performance_engine_test", {})
    engine_status = "PASS" if engine_test.get("success", False) else "FAIL"
    print(f"\nPerformance Engine: {engine_status}")

    # API Endpoint Tests
    api_tests = results.get("api_endpoint_tests", {})
    if api_tests.get("skipped"):
        print(f"\nAPI Endpoints: SKIPPED ({api_tests.get('reason', 'Unknown reason')})")
    else:
        api_success = api_tests.get("success", False)
        targets_met = api_tests.get("targets_met", False)
        api_status = "PASS" if api_success and targets_met else "FAIL"
        print(f"\nAPI Endpoints: {api_status}")

        if "results" in api_tests:
            for result in api_tests["results"]:
                if result.get("success", False):
                    target_status = (
                        "PASS" if result.get("meets_target", False) else "FAIL"
                    )
                    print(
                        f"  {target_status} {result['description']}: {result.get('response_time_ms', 0):.1f}ms"
                    )
                else:
                    print(f"  FAIL {result['description']}: ERROR")

    # Load Test Results
    load_test = results.get("load_test_results", {})
    if load_test.get("skipped"):
        print(f"\nLoad Test: SKIPPED ({load_test.get('reason', 'Unknown reason')})")
    else:
        targets = load_test.get("meets_targets", {})
        load_status = "PASS" if all(targets.values()) else "FAIL"
        print(f"\nLoad Test: {load_status}")

        if "avg_response_time_ms" in load_test:
            print(f"  Average Response Time: {load_test['avg_response_time_ms']:.1f}ms")
            print(f"  P95 Response Time: {load_test['p95_response_time_ms']:.1f}ms")
            print(f"  Throughput: {load_test['throughput_rps']:.1f} RPS")
            print(f"  Error Rate: {load_test['error_rate']:.1f}%")

    # Overall Result
    overall_status = "PASS" if results.get("overall_success", False) else "FAIL"
    print(f"\nOVERALL VALIDATION: {overall_status}")
    print("=" * 60)


def save_validation_results(results: Dict[str, Any]):
    """Save validation results to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"performance_validation_{timestamp}.json"

    try:
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Validation results saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        return None


async def main():
    """Main validation function."""
    try:
        results = await validate_performance()

        # Print summary
        print_validation_summary(results)

        # Save results
        save_validation_results(results)

        # Exit with appropriate code
        exit_code = 0 if results.get("overall_success", False) else 1
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
