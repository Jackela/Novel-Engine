#!/usr/bin/env python3
"""
Quick test script to validate the deployment fixes
"""

import asyncio
from datetime import datetime

import httpx
import pytest


@pytest.mark.asyncio
async def test_fixes():
    """Test the deployment fixes"""

    print("=" * 60)
    print("AI Testing Framework - Fix Validation")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Master Orchestrator Health (should not return 500)
        print("\n1. Testing Master Orchestrator Health...")
        try:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                if status in ["healthy", "degraded"]:
                    print(
                        f"   ✅ Orchestrator health: {status} (HTTP {response.status_code})"
                    )
                    results.append(
                        ("Orchestrator Health", True, f"Status: {status}")
                    )
                else:
                    print(
                        f"   ❌ Orchestrator health: {status} (unexpected status)"
                    )
                    results.append(
                        (
                            "Orchestrator Health",
                            False,
                            f"Unexpected status: {status}",
                        )
                    )
            else:
                print(f"   ❌ Orchestrator health: HTTP {response.status_code}")
                results.append(
                    (
                        "Orchestrator Health",
                        False,
                        f"HTTP {response.status_code}",
                    )
                )
        except Exception as e:
            print(f"   ❌ Orchestrator health: {e}")
            results.append(("Orchestrator Health", False, str(e)))

        # Test 2: Notification Service (should have channels configured)
        print("\n2. Testing Notification Service...")
        try:
            response = await client.get("http://localhost:8005/health")
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                deps = health_data.get("external_dependencies", {})
                channels = deps.get("notification_channels", "disconnected")

                if status in ["healthy", "degraded"]:
                    print(
                        f"   ✅ Notification service: {status}, channels: {channels}"
                    )
                    results.append(
                        (
                            "Notification Service",
                            True,
                            f"Status: {status}, Channels: {channels}",
                        )
                    )
                else:
                    print(f"   ❌ Notification service: {status}")
                    results.append(
                        ("Notification Service", False, f"Status: {status}")
                    )
            else:
                print(
                    f"   ❌ Notification service: HTTP {response.status_code}"
                )
                results.append(
                    (
                        "Notification Service",
                        False,
                        f"HTTP {response.status_code}",
                    )
                )
        except Exception as e:
            print(f"   ❌ Notification service: {e}")
            results.append(("Notification Service", False, str(e)))

        # Test 3: API Testing Service functionality
        print("\n3. Testing API Testing Service...")
        try:
            test_params = {
                "endpoint_url": "http://localhost:8002/health",
                "method": "GET",
                "expected_status": 200,
            }

            response = await client.post(
                "http://localhost:8002/test/single", params=test_params
            )

            if response.status_code == 200:
                result_data = response.json()
                test_passed = result_data.get("passed", False)
                if test_passed:
                    print(
                        "   ✅ API Testing service: Test execution successful"
                    )
                    results.append(
                        (
                            "API Testing Functionality",
                            True,
                            "Test execution successful",
                        )
                    )
                else:
                    print(
                        "   ⚠️  API Testing service: Test failed but service working"
                    )
                    results.append(
                        (
                            "API Testing Functionality",
                            True,
                            "Service working, test failed",
                        )
                    )
            else:
                print(f"   ❌ API Testing service: HTTP {response.status_code}")
                results.append(
                    (
                        "API Testing Functionality",
                        False,
                        f"HTTP {response.status_code}",
                    )
                )
        except Exception as e:
            print(f"   ❌ API Testing service: {e}")
            results.append(("API Testing Functionality", False, str(e)))

        # Test 4: Concurrent requests to Orchestrator
        print("\n4. Testing Concurrent Request Handling...")
        try:
            tasks = []
            for i in range(5):
                task = client.get("http://localhost:8000/health")
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(
                1
                for r in responses
                if not isinstance(r, Exception) and r.status_code == 200
            )
            success_rate = successful / len(responses)

            if success_rate >= 0.8:
                print(
                    f"   ✅ Concurrent handling: {success_rate:.0%} success ({successful}/5)"
                )
                results.append(
                    (
                        "Concurrent Handling",
                        True,
                        f"{success_rate:.0%} success",
                    )
                )
            else:
                print(
                    f"   ❌ Concurrent handling: {success_rate:.0%} success ({successful}/5)"
                )
                results.append(
                    (
                        "Concurrent Handling",
                        False,
                        f"{success_rate:.0%} success",
                    )
                )
        except Exception as e:
            print(f"   ❌ Concurrent handling: {e}")
            results.append(("Concurrent Handling", False, str(e)))

        # Test 5: Simple E2E workflow
        print("\n5. Testing E2E Workflow...")
        try:
            test_request = {
                "test_name": "Fix Validation E2E Test",
                "api_test_specs": [
                    {
                        "endpoint": "http://localhost:8000/health",
                        "method": "GET",
                        "expected_status": 200,
                    }
                ],
                "strategy": "sequential",
                "parallel_execution": False,
                "fail_fast": True,
                "quality_threshold": 0.5,
                "test_environment": "validation",
                "max_execution_time_minutes": 1,
            }

            response = await client.post(
                "http://localhost:8000/test/comprehensive",
                json=test_request,
                timeout=60.0,
            )

            if response.status_code == 200:
                result_data = response.json()
                overall_passed = result_data.get("overall_passed", False)
                overall_score = result_data.get("overall_score", 0.0)

                if overall_passed or overall_score > 0:
                    print(
                        f"   ✅ E2E Workflow: Success (Score: {overall_score:.2f})"
                    )
                    results.append(
                        ("E2E Workflow", True, f"Score: {overall_score:.2f}")
                    )
                else:
                    print(
                        f"   ⚠️  E2E Workflow: Partial success (Score: {overall_score:.2f})"
                    )
                    results.append(
                        ("E2E Workflow", False, f"Score: {overall_score:.2f}")
                    )
            else:
                print(f"   ❌ E2E Workflow: HTTP {response.status_code}")
                results.append(
                    ("E2E Workflow", False, f"HTTP {response.status_code}")
                )
        except Exception as e:
            print(f"   ❌ E2E Workflow: {e}")
            results.append(("E2E Workflow", False, str(e)))

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    success_rate = passed / total if total > 0 else 0

    for test_name, passed, details in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:8} | {test_name:30} | {details}")

    print("-" * 60)
    print(f"Overall: {passed}/{total} tests passed ({success_rate:.1%})")

    if success_rate >= 0.8:
        print("\n🎉 Deployment fixes validated successfully!")
        return True
    else:
        print("\n⚠️  Some issues remain. Please review the failed tests.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_fixes())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        exit(1)
