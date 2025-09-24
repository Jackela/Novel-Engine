#!/usr/bin/env python3
"""
Quality Gates Script for Novel Engine
Implements comprehensive code quality validation and enforcement.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, Tuple


class QualityGate:
    """Individual quality gate implementation."""

    def __init__(self, name: str, description: str, required: bool = True):
        self.name = name
        self.description = description
        self.required = required
        self.passed = False
        self.output = ""
        self.error = ""

    def run(self) -> bool:
        """Run the quality gate check. Override in subclasses."""
        raise NotImplementedError

    def report(self) -> Dict:
        """Generate quality gate report."""
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "passed": self.passed,
            "output": self.output,
            "error": self.error,
        }


class CoverageGate(QualityGate):
    """Test coverage quality gate."""

    def __init__(self, min_coverage: float = 90.0):
        super().__init__(
            "Test Coverage",
            f"Ensure test coverage is at least {min_coverage}%",
            required=True,
        )
        self.min_coverage = min_coverage

    def run(self) -> bool:
        """Run coverage analysis."""
        try:
            # Run tests with coverage
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--cov-report=json:coverage.json",
                    "--tb=no",
                    "-q",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            self.output = result.stdout
            if result.stderr:
                self.error = result.stderr

            # Parse coverage report
            if os.path.exists("coverage.json"):
                with open("coverage.json", "r") as f:
                    coverage_data = json.load(f)
                    total_coverage = coverage_data.get("totals", {}).get(
                        "percent_covered", 0
                    )

                self.passed = total_coverage >= self.min_coverage
                self.output += f"\nTotal Coverage: {total_coverage:.2f}%"

                if not self.passed:
                    self.error += f"\nCoverage {total_coverage:.2f}% is below minimum {self.min_coverage}%"

            else:
                self.passed = False
                self.error = "Coverage report not generated"

        except subprocess.TimeoutExpired:
            self.passed = False
            self.error = "Coverage analysis timed out"
        except Exception as e:
            self.passed = False
            self.error = f"Coverage analysis failed: {str(e)}"

        return self.passed


class LintingGate(QualityGate):
    """Code linting quality gate."""

    def __init__(self):
        super().__init__(
            "Code Linting",
            "Ensure code follows style guidelines",
            required=True,
        )

    def run(self) -> bool:
        """Run linting checks."""
        checks = []

        # Black formatting check
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "black",
                    "--check",
                    "--diff",
                    "src",
                    "tests",
                ],
                capture_output=True,
                text=True,
            )
            checks.append(
                ("Black", result.returncode == 0, result.stdout, result.stderr)
            )
        except FileNotFoundError:
            checks.append(("Black", False, "", "Black not installed"))

        # isort import sorting check
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "isort",
                    "--check-only",
                    "--diff",
                    "src",
                    "tests",
                ],
                capture_output=True,
                text=True,
            )
            checks.append(
                ("isort", result.returncode == 0, result.stdout, result.stderr)
            )
        except FileNotFoundError:
            checks.append(("isort", False, "", "isort not installed"))

        # Flake8 style check
        try:
            result = subprocess.run(
                [sys.executable, "-m", "flake8", "src", "tests"],
                capture_output=True,
                text=True,
            )
            checks.append(
                (
                    "Flake8",
                    result.returncode == 0,
                    result.stdout,
                    result.stderr,
                )
            )
        except FileNotFoundError:
            checks.append(("Flake8", False, "", "flake8 not installed"))

        # Compile results
        self.passed = all(passed for _, passed, _, _ in checks)
        self.output = "\n".join(
            f"{name}: {'✓' if passed else '✗'}"
            for name, passed, _, _ in checks
        )
        self.error = "\n".join(
            f"{name}: {stderr}"
            for name, passed, _, stderr in checks
            if not passed and stderr
        )

        return self.passed


class TypeCheckingGate(QualityGate):
    """Type checking quality gate."""

    def __init__(self):
        super().__init__(
            "Type Checking",
            "Ensure code passes static type checking",
            required=False,  # Optional for now
        )

    def run(self) -> bool:
        """Run MyPy type checking."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "mypy", "src"],
                capture_output=True,
                text=True,
            )

            self.passed = result.returncode == 0
            self.output = result.stdout
            self.error = result.stderr

        except FileNotFoundError:
            self.passed = False
            self.error = "MyPy not installed"

        return self.passed


class SecurityGate(QualityGate):
    """Security scanning quality gate."""

    def __init__(self):
        super().__init__(
            "Security Scan",
            "Ensure code passes security vulnerability scanning",
            required=True,
        )

    def run(self) -> bool:
        """Run security scans."""
        checks = []

        # Bandit security linting
        try:
            result = subprocess.run(
                [sys.executable, "-m", "bandit", "-r", "src", "-f", "json"],
                capture_output=True,
                text=True,
            )

            # Bandit returns non-zero if issues found, but that's expected
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    high_severity = sum(
                        1
                        for issue in bandit_data.get("results", [])
                        if issue.get("issue_severity") == "HIGH"
                    )
                    medium_severity = sum(
                        1
                        for issue in bandit_data.get("results", [])
                        if issue.get("issue_severity") == "MEDIUM"
                    )

                    bandit_passed = (
                        high_severity == 0
                    )  # No high severity issues
                    checks.append(
                        (
                            "Bandit",
                            bandit_passed,
                            f"High: {high_severity}, Medium: {medium_severity}",
                            "",
                        )
                    )
                except json.JSONDecodeError:
                    checks.append(
                        ("Bandit", False, "", "Failed to parse Bandit output")
                    )
            else:
                checks.append(("Bandit", True, "No issues found", ""))

        except FileNotFoundError:
            checks.append(("Bandit", False, "", "Bandit not installed"))

        # Safety dependency check
        try:
            result = subprocess.run(
                [sys.executable, "-m", "safety", "check", "--json"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                checks.append(("Safety", True, "No vulnerabilities found", ""))
            else:
                checks.append(("Safety", False, result.stdout, result.stderr))

        except FileNotFoundError:
            checks.append(("Safety", False, "", "Safety not installed"))

        # Compile results
        self.passed = all(passed for _, passed, _, _ in checks)
        self.output = "\n".join(
            f"{name}: {'✓' if passed else '✗'} - {output}"
            for name, passed, output, _ in checks
        )
        self.error = "\n".join(
            f"{name}: {error}"
            for name, passed, _, error in checks
            if not passed and error
        )

        return self.passed


class TestGate(QualityGate):
    """Test execution quality gate."""

    def __init__(self):
        super().__init__(
            "Test Execution",
            "Ensure all tests pass successfully",
            required=True,
        )

    def run(self) -> bool:
        """Run test suite."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--tb=short",
                    "-v",
                    "--maxfail=5",
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            self.passed = result.returncode == 0
            self.output = result.stdout
            self.error = result.stderr

            if not self.passed:
                # Extract failed test summary
                lines = result.stdout.split("\n")
                failed_tests = [line for line in lines if "FAILED" in line]
                if failed_tests:
                    self.error += "\n\nFailed Tests:\n" + "\n".join(
                        failed_tests[:10]
                    )

        except subprocess.TimeoutExpired:
            self.passed = False
            self.error = "Test execution timed out"
        except Exception as e:
            self.passed = False
            self.error = f"Test execution failed: {str(e)}"

        return self.passed


class QualityGateRunner:
    """Orchestrates quality gate execution."""

    def __init__(self):
        self.gates = [
            LintingGate(),
            TypeCheckingGate(),
            SecurityGate(),
            TestGate(),
            CoverageGate(),
        ]

    def run_all(self, fail_fast: bool = False) -> Tuple[bool, Dict]:
        """Run all quality gates."""
        print("🚀 Running Quality Gates for Novel Engine")
        print("=" * 50)

        results = {
            "overall_passed": True,
            "gates": {},
            "summary": {
                "total": len(self.gates),
                "passed": 0,
                "failed": 0,
                "required_failed": 0,
            },
        }

        for gate in self.gates:
            print(f"\n🔍 Running {gate.name}...")

            try:
                passed = gate.run()
                results["gates"][gate.name] = gate.report()

                if passed:
                    print(f"✅ {gate.name}: PASSED")
                    results["summary"]["passed"] += 1
                else:
                    status = "FAILED" if gate.required else "FAILED (Optional)"
                    print(f"❌ {gate.name}: {status}")
                    results["summary"]["failed"] += 1

                    if gate.required:
                        results["summary"]["required_failed"] += 1
                        results["overall_passed"] = False

                    if gate.error:
                        print(f"   Error: {gate.error[:200]}...")

                    if fail_fast and gate.required and not passed:
                        print("\n💥 Failing fast due to required gate failure")
                        break

            except Exception as e:
                print(f"💥 {gate.name}: ERROR - {str(e)}")
                results["gates"][gate.name] = {
                    "name": gate.name,
                    "passed": False,
                    "error": str(e),
                    "required": gate.required,
                }
                results["summary"]["failed"] += 1
                if gate.required:
                    results["summary"]["required_failed"] += 1
                    results["overall_passed"] = False

        # Final report
        print("\n📊 Quality Gates Summary")
        print(f"{'=' * 30}")
        print(f"Total Gates: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Required Failed: {results['summary']['required_failed']}")
        print(
            f"Overall Status: {'✅ PASSED' if results['overall_passed'] else '❌ FAILED'}"
        )

        return results["overall_passed"], results

    def generate_report(
        self, results: Dict, output_file: str = "quality_report.json"
    ):
        """Generate detailed quality report."""
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Detailed report saved to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run quality gates for Novel Engine"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first required gate failure",
    )
    parser.add_argument(
        "--report",
        default="quality_report.json",
        help="Output file for detailed report",
    )

    args = parser.parse_args()

    runner = QualityGateRunner()
    passed, results = runner.run_all(fail_fast=args.fail_fast)
    runner.generate_report(results, args.report)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
