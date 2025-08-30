#!/usr/bin/env python3
"""
UAT (User Acceptance Testing) Script for StoryForge AI
====================================================

Comprehensive automated testing script covering happy path, sad path,
and edge case scenarios from a user perspective.

Usage:
    python uat_test_script.py [--verbose] [--report-file output.json]
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


@dataclass
class UATestResult:
    """Results of a single UAT test case."""

    test_id: str
    test_name: str
    category: str  # happy_path, sad_path, edge_case
    description: str
    status: str  # PASS, FAIL, ERROR
    expected_status_code: int
    actual_status_code: int
    response_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    execution_time_ms: float
    timestamp: str


class StoryForgeUATester:
    """User Acceptance Testing suite for StoryForge AI."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.results: List[UATestResult] = []
        self.session = requests.Session()

    def log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"
        self.log(f"{method} {url}")
        return self.session.request(method, url, **kwargs)

    def run_test(
        self,
        test_id: str,
        test_name: str,
        category: str,
        description: str,
        expected_status: int,
        method: str = "GET",
        endpoint: str = "/",
        **request_kwargs,
    ) -> UATestResult:
        """Execute a single test case."""
        start_time = time.time()

        try:
            response = self.make_request(method, endpoint, **request_kwargs)
            execution_time = (time.time() - start_time) * 1000

            # Determine test status
            if response.status_code == expected_status:
                status = "PASS"
                error_message = None
            else:
                status = "FAIL"
                error_message = (
                    f"Expected status {expected_status}, got {response.status_code}"
                )

            # Parse response data
            try:
                response_data = response.json()
            except (ValueError, TypeError):
                response_data = {"raw_response": response.text}

            result = UATestResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                description=description,
                status=status,
                expected_status_code=expected_status,
                actual_status_code=response.status_code,
                response_data=response_data,
                error_message=error_message,
                execution_time_ms=round(execution_time, 2),
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = UATestResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                description=description,
                status="ERROR",
                expected_status_code=expected_status,
                actual_status_code=0,
                response_data=None,
                error_message=str(e),
                execution_time_ms=round(execution_time, 2),
                timestamp=datetime.now().isoformat(),
            )

        self.results.append(result)
        self.log(f"Test {test_id}: {result.status} ({result.execution_time_ms}ms)")
        return result

    def run_happy_path_tests(self) -> None:
        """Execute happy path test scenarios."""
        print("\n🟢 Running Happy Path UAT Tests...")

        # HP01: Root endpoint access
        self.run_test(
            "HP01",
            "Root Endpoint Access",
            "happy_path",
            "User accesses the root API endpoint to verify system is running",
            200,
            "GET",
            "/",
        )

        # HP02: Health check
        self.run_test(
            "HP02",
            "Health Check",
            "happy_path",
            "User checks system health status",
            200,
            "GET",
            "/health",
        )

        # HP03: Character listing
        self.run_test(
            "HP03",
            "Character Listing",
            "happy_path",
            "User retrieves list of available characters",
            200,
            "GET",
            "/characters",
        )

        # HP04: Individual character retrieval
        self.run_test(
            "HP04",
            "Character Retrieval",
            "happy_path",
            "User retrieves specific character details",
            200,
            "GET",
            "/characters/pilot",
        )

        # HP05: Story generation with valid parameters
        self.run_test(
            "HP05",
            "Story Generation",
            "happy_path",
            "User generates story with valid characters and parameters",
            200,
            "POST",
            "/simulations",
            json={
                "character_names": ["pilot", "engineer"],
                "turns": 3,
                "narrative_style": "epic",
            },
            headers={"Content-Type": "application/json"},
        )

    def run_sad_path_tests(self) -> None:
        """Execute sad path (error condition) test scenarios."""
        print("\n🔴 Running Sad Path UAT Tests...")

        # SP01: Nonexistent endpoint
        self.run_test(
            "SP01",
            "Nonexistent Endpoint",
            "sad_path",
            "User tries to access endpoint that doesn't exist",
            404,
            "GET",
            "/nonexistent",
        )

        # SP02: Nonexistent character
        self.run_test(
            "SP02",
            "Nonexistent Character",
            "sad_path",
            "User tries to retrieve character that doesn't exist",
            404,
            "GET",
            "/characters/nonexistent_character",
        )

        # SP03: Invalid character names in simulation
        self.run_test(
            "SP03",
            "Invalid Characters in Simulation",
            "sad_path",
            "User tries to generate story with nonexistent characters",
            404,
            "POST",
            "/simulations",
            json={
                "character_names": ["nonexistent1", "nonexistent2"],
                "turns": 3,
                "narrative_style": "epic",
            },
            headers={"Content-Type": "application/json"},
        )

        # SP04: Invalid narrative style
        self.run_test(
            "SP04",
            "Invalid Narrative Style",
            "sad_path",
            "User tries to use invalid narrative style",
            422,
            "POST",
            "/simulations",
            json={
                "character_names": ["pilot", "engineer"],
                "turns": 3,
                "narrative_style": "invalid_style",
            },
            headers={"Content-Type": "application/json"},
        )

        # SP05: Too few characters
        self.run_test(
            "SP05",
            "Insufficient Characters",
            "sad_path",
            "User tries to generate story with insufficient characters",
            422,
            "POST",
            "/simulations",
            json={"character_names": ["pilot"], "turns": 3, "narrative_style": "epic"},
            headers={"Content-Type": "application/json"},
        )

        # SP06: Invalid turns count
        self.run_test(
            "SP06",
            "Invalid Turns Count",
            "sad_path",
            "User tries to use invalid turns parameter",
            422,
            "POST",
            "/simulations",
            json={
                "character_names": ["pilot", "engineer"],
                "turns": 999,
                "narrative_style": "epic",
            },
            headers={"Content-Type": "application/json"},
        )

        # SP07: Malformed JSON
        self.run_test(
            "SP07",
            "Malformed Request",
            "sad_path",
            "User sends malformed JSON request",
            422,
            "POST",
            "/simulations",
            data="invalid json data",
            headers={"Content-Type": "application/json"},
        )

    def run_edge_case_tests(self) -> None:
        """Execute edge case test scenarios."""
        print("\n🟡 Running Edge Case UAT Tests...")

        # EC01: Minimum boundary conditions
        self.run_test(
            "EC01",
            "Minimum Boundary Test",
            "edge_case",
            "User generates story with minimum valid parameters",
            200,
            "POST",
            "/simulations",
            json={
                "character_names": ["pilot", "engineer"],
                "turns": 1,
                "narrative_style": "concise",
            },
            headers={"Content-Type": "application/json"},
        )

        # EC02: Maximum boundary conditions
        self.run_test(
            "EC02",
            "Maximum Boundary Test",
            "edge_case",
            "User generates story with maximum valid parameters",
            200,
            "POST",
            "/simulations",
            json={
                "character_names": ["pilot", "engineer", "scientist", "test"],
                "turns": 10,
                "narrative_style": "detailed",
            },
            headers={"Content-Type": "application/json"},
        )

        # EC03: Empty request body
        self.run_test(
            "EC03",
            "Empty Request Body",
            "edge_case",
            "User sends empty request to simulation endpoint",
            422,
            "POST",
            "/simulations",
            json={},
            headers={"Content-Type": "application/json"},
        )

        # EC04: Wrong HTTP method
        self.run_test(
            "EC04",
            "Wrong HTTP Method",
            "edge_case",
            "User uses GET instead of POST for simulation endpoint",
            405,
            "GET",
            "/simulations",
        )

        # EC05: Case sensitivity test
        self.run_test(
            "EC05",
            "Case Sensitivity",
            "edge_case",
            "User tries to access character with different case",
            404,
            "GET",
            "/characters/PILOT",
        )

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        if not self.results:
            return {"error": "No tests executed"}

        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "PASS"])
        failed_tests = len([r for r in self.results if r.status == "FAIL"])
        error_tests = len([r for r in self.results if r.status == "ERROR"])

        avg_execution_time = (
            sum(r.execution_time_ms for r in self.results) / total_tests
        )

        # Group by category
        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(asdict(result))

        return {
            "test_execution_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "pass_rate": f"{(passed_tests/total_tests*100):.1f}%",
                "average_execution_time_ms": round(avg_execution_time, 2),
            },
            "test_results_by_category": by_category,
            "detailed_results": [asdict(result) for result in self.results],
        }

    def print_summary(self) -> None:
        """Print test execution summary."""
        report = self.generate_report()
        summary = report["test_execution_summary"]

        print("\n" + "=" * 60)
        print("🧪 StoryForge AI - UAT Test Results Summary")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Errors: {summary['errors']}")
        print(f"📊 Pass Rate: {summary['pass_rate']}")
        print(f"⏱️  Avg Time: {summary['average_execution_time_ms']}ms")
        print("=" * 60)

        # Show failed/error tests
        if summary["failed"] > 0 or summary["errors"] > 0:
            print("\n❌ Failed/Error Tests:")
            for result in self.results:
                if result.status in ["FAIL", "ERROR"]:
                    print(
                        f"  {result.test_id}: {result.test_name} - {result.error_message}"
                    )

    def run_all_tests(self) -> None:
        """Execute all UAT test scenarios."""
        print("🚀 Starting StoryForge AI User Acceptance Testing")
        print(f"Testing endpoint: {self.base_url}")

        start_time = time.time()

        self.run_happy_path_tests()
        self.run_sad_path_tests()
        self.run_edge_case_tests()

        total_time = time.time() - start_time
        print(f"\n✨ All tests completed in {total_time:.2f} seconds")

        self.print_summary()


def main():
    """Main entry point for UAT script."""
    parser = argparse.ArgumentParser(description="StoryForge AI UAT Test Runner")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--report-file", "-r", type=str, help="Save detailed report to JSON file"
    )
    parser.add_argument(
        "--base-url",
        "-u",
        type=str,
        default="http://127.0.0.1:8000",
        help="Base URL for API testing",
    )

    args = parser.parse_args()

    # Create and run UAT tester
    tester = StoryForgeUATester(base_url=args.base_url, verbose=args.verbose)

    try:
        tester.run_all_tests()

        # Save report if requested
        if args.report_file:
            report = tester.generate_report()
            with open(args.report_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {args.report_file}")

        # Exit with appropriate code
        failed_or_error = len(
            [r for r in tester.results if r.status in ["FAIL", "ERROR"]]
        )
        sys.exit(0 if failed_or_error == 0 else 1)

    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
