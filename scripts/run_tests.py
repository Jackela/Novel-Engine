#!/usr/bin/env python3
"""
Comprehensive test runner for Novel Engine
Provides multiple test execution modes with detailed reporting.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple


class TestRunner:
    """Comprehensive test runner with multiple execution modes."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = time.time()
        self.results = {
            "summary": {},
            "test_results": {},
            "coverage": {},
            "performance": {},
            "errors": [],
        }

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[{timestamp}] {level}:"
        print(f"{prefix} {message}")

    def run_command(
        self, command: List[str], description: str, timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """Run a command and return success status and output."""
        self.log(f"Running {description}...")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path.cwd(),
            )

            success = result.returncode == 0

            if self.verbose or not success:
                if result.stdout:
                    self.log(f"STDOUT: {result.stdout}")
                if result.stderr:
                    self.log(f"STDERR: {result.stderr}")

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"{description} timed out after {timeout}s"
            self.log(error_msg, "ERROR")
            self.results["errors"].append(error_msg)
            return False, "", error_msg

        except Exception as e:
            error_msg = f"{description} failed: {str(e)}"
            self.log(error_msg, "ERROR")
            self.results["errors"].append(error_msg)
            return False, "", error_msg

    def run_unit_tests(self) -> bool:
        """Run unit tests with coverage."""
        self.log("🧪 Running Unit Tests", "INFO")

        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=json:coverage.json",
            "--cov-report=xml:coverage.xml",
            "--junitxml=test-results.xml",
            "-v",
            "--tb=short",
            "--maxfail=10",
        ]

        if not self.verbose:
            command.append("-q")

        success, stdout, stderr = self.run_command(
            command, "Unit Tests", timeout=600
        )

        self.results["test_results"]["unit_tests"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        # Parse coverage results
        if os.path.exists("coverage.json"):
            try:
                with open("coverage.json", "r") as f:
                    coverage_data = json.load(f)
                    self.results["coverage"] = coverage_data.get("totals", {})
                    self.log(
                        f"Coverage: {self.results['coverage'].get('percent_covered', 0):.2f}%"
                    )
            except Exception as e:
                self.log(f"Failed to parse coverage data: {e}", "WARNING")

        return success

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        self.log("🔗 Running Integration Tests", "INFO")

        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "integration",
            "-v",
            "--tb=short",
            "--maxfail=5",
        ]

        if not self.verbose:
            command.append("-q")

        success, stdout, stderr = self.run_command(
            command, "Integration Tests", timeout=300
        )

        self.results["test_results"]["integration_tests"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        return success

    def run_api_tests(self) -> bool:
        """Run API tests."""
        self.log("🌐 Running API Tests", "INFO")

        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "api",
            "-v",
            "--tb=short",
            "--maxfail=5",
        ]

        if not self.verbose:
            command.append("-q")

        success, stdout, stderr = self.run_command(
            command, "API Tests", timeout=180
        )

        self.results["test_results"]["api_tests"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        return success

    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        self.log("⚡ Running Performance Tests", "INFO")

        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "performance",
            "--benchmark-only",
            "--benchmark-json=benchmark.json",
            "-v",
        ]

        success, stdout, stderr = self.run_command(
            command, "Performance Tests", timeout=300
        )

        self.results["test_results"]["performance_tests"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        # Parse performance results
        if os.path.exists("benchmark.json"):
            try:
                with open("benchmark.json", "r") as f:
                    benchmark_data = json.load(f)
                    self.results["performance"] = benchmark_data
                    self.log("Performance benchmarks completed")
            except Exception as e:
                self.log(f"Failed to parse benchmark data: {e}", "WARNING")

        return success

    def run_security_tests(self) -> bool:
        """Run security tests."""
        self.log("🔒 Running Security Tests", "INFO")

        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "security",
            "-v",
            "--tb=short",
        ]

        success, stdout, stderr = self.run_command(
            command, "Security Tests", timeout=180
        )

        self.results["test_results"]["security_tests"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        return success

    def run_smoke_tests(self) -> bool:
        """Run smoke tests for basic functionality."""
        self.log("💨 Running Smoke Tests", "INFO")

        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "smoke",
            "-v",
            "--tb=short",
            "--maxfail=1",
        ]

        success, stdout, stderr = self.run_command(
            command, "Smoke Tests", timeout=60
        )

        self.results["test_results"]["smoke_tests"] = {
            "success": success,
            "output": stdout,
            "error": stderr,
        }

        return success

    def run_all_tests(self) -> bool:
        """Run all test suites."""
        self.log("🚀 Running Complete Test Suite", "INFO")

        test_suites = [
            ("Smoke Tests", self.run_smoke_tests),
            ("Unit Tests", self.run_unit_tests),
            ("Integration Tests", self.run_integration_tests),
            ("API Tests", self.run_api_tests),
            ("Security Tests", self.run_security_tests),
            ("Performance Tests", self.run_performance_tests),
        ]

        results = []

        for suite_name, test_func in test_suites:
            try:
                success = test_func()
                results.append((suite_name, success))
                status = "✅ PASSED" if success else "❌ FAILED"
                self.log(f"{suite_name}: {status}")

                # Stop on smoke test failure
                if suite_name == "Smoke Tests" and not success:
                    self.log("Smoke tests failed, stopping execution", "ERROR")
                    break

            except Exception as e:
                self.log(f"{suite_name} failed with exception: {e}", "ERROR")
                results.append((suite_name, False))

        return all(success for _, success in results)

    def generate_report(self, output_file: str = "test_report.json"):
        """Generate comprehensive test report."""
        end_time = time.time()
        duration = end_time - self.start_time

        # Calculate summary
        total_suites = len(self.results["test_results"])
        passed_suites = sum(
            1
            for result in self.results["test_results"].values()
            if result.get("success", False)
        )

        self.results["summary"] = {
            "total_suites": total_suites,
            "passed_suites": passed_suites,
            "failed_suites": total_suites - passed_suites,
            "duration_seconds": round(duration, 2),
            "overall_success": passed_suites == total_suites,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "coverage_percent": self.results["coverage"].get(
                "percent_covered", 0
            ),
        }

        # Write detailed report
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        self.log(f"Detailed report saved to {output_file}")

    def print_summary(self):
        """Print test execution summary."""
        summary = self.results["summary"]

        print("\n" + "=" * 60)
        print("🏁 TEST EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total Test Suites: {summary['total_suites']}")
        print(f"Passed: {summary['passed_suites']}")
        print(f"Failed: {summary['failed_suites']}")
        print(f"Duration: {summary['duration_seconds']}s")

        if "coverage_percent" in summary:
            print(f"Coverage: {summary['coverage_percent']:.2f}%")

        status = (
            "✅ ALL TESTS PASSED"
            if summary["overall_success"]
            else "❌ SOME TESTS FAILED"
        )
        print(f"Overall Status: {status}")

        if self.results["errors"]:
            print(f"\n⚠️  Errors Encountered ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"  - {error}")

        print("=" * 60)

    def cleanup(self):
        """Clean up test artifacts."""
        artifacts = [
            "test-results.xml",
            "coverage.json",
            "coverage.xml",
            "benchmark.json",
            ".coverage",
            "__pycache__",
            ".pytest_cache",
        ]

        for artifact in artifacts:
            if os.path.exists(artifact):
                if os.path.isdir(artifact):
                    shutil.rmtree(artifact)
                else:
                    os.remove(artifact)

        self.log("Test artifacts cleaned up")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Novel Engine Test Runner")
    parser.add_argument(
        "--mode",
        choices=[
            "all",
            "unit",
            "integration",
            "api",
            "performance",
            "security",
            "smoke",
        ],
        default="all",
        help="Test execution mode",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--report",
        default="test_report.json",
        help="Output file for test report",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test artifacts after execution",
    )

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose)

    try:
        # Execute tests based on mode
        if args.mode == "all":
            success = runner.run_all_tests()
        elif args.mode == "unit":
            success = runner.run_unit_tests()
        elif args.mode == "integration":
            success = runner.run_integration_tests()
        elif args.mode == "api":
            success = runner.run_api_tests()
        elif args.mode == "performance":
            success = runner.run_performance_tests()
        elif args.mode == "security":
            success = runner.run_security_tests()
        elif args.mode == "smoke":
            success = runner.run_smoke_tests()
        else:
            runner.log(f"Unknown test mode: {args.mode}", "ERROR")
            sys.exit(1)

        # Generate reports
        runner.generate_report(args.report)
        runner.print_summary()

        # Cleanup if requested
        if args.cleanup:
            runner.cleanup()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        runner.log("Test execution interrupted by user", "WARNING")
        sys.exit(130)
    except Exception as e:
        runner.log(f"Test execution failed: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
