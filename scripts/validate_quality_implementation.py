#!/usr/bin/env python3
"""
Quality Implementation Validation Script
Validates that all quality enhancement components are properly implemented.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict


class QualityValidator:
    """Validates quality framework implementation."""

    def __init__(self):
        self.root_path = Path.cwd()
        self.results = {
            "overall_status": "unknown",
            "validations": {},
            "recommendations": [],
            "summary": {"total_checks": 0, "passed": 0, "failed": 0, "warnings": 0},
        }

    def log(self, message: str, level: str = "INFO"):
        """Log validation message."""
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}
        print(f"{symbols.get(level, 'ℹ️')} {message}")

    def validate_file_exists(self, file_path: str, description: str) -> bool:
        """Validate that a required file exists."""
        exists = (self.root_path / file_path).exists()
        status = "✅ EXISTS" if exists else "❌ MISSING"
        self.log(f"{description}: {status}")
        return exists

    def validate_directory_structure(self) -> Dict:
        """Validate required directory structure."""
        self.log("🏗️ Validating Directory Structure")

        required_dirs = [
            ("scripts", "Quality scripts directory"),
            ("tests", "Test directory"),
            ("src", "Source code directory"),
            ("docs", "Documentation directory"),
            (".github/workflows", "GitHub Actions workflows"),
        ]

        results = {}
        for dir_path, description in required_dirs:
            exists = self.validate_file_exists(dir_path, description)
            results[dir_path] = exists

        return results

    def validate_configuration_files(self) -> Dict:
        """Validate quality configuration files."""
        self.log("⚙️ Validating Configuration Files")

        config_files = [
            ("pytest.ini", "Pytest configuration"),
            (".coveragerc", "Coverage configuration"),
            ("pyproject.toml", "Project configuration"),
            (".pre-commit-config.yaml", "Pre-commit hooks"),
            ("mkdocs.yml", "Documentation configuration"),
        ]

        results = {}
        for file_path, description in config_files:
            exists = self.validate_file_exists(file_path, description)
            results[file_path] = exists

        return results

    def validate_quality_scripts(self) -> Dict:
        """Validate quality assurance scripts."""
        self.log("🔧 Validating Quality Scripts")

        scripts = [
            ("scripts/quality_gates.py", "Quality gates script"),
            ("scripts/run_tests.py", "Test runner script"),
            ("scripts/validate_quality_implementation.py", "This validation script"),
        ]

        results = {}
        for script_path, description in scripts:
            exists = self.validate_file_exists(script_path, description)
            if exists:
                # Check if script is executable
                full_path = self.root_path / script_path
                executable = os.access(full_path, os.X_OK) or script_path.endswith(".py")
                if not executable:
                    self.log(f"  Warning: {script_path} may not be executable", "WARNING")

            results[script_path] = exists

        return results

    def validate_test_framework(self) -> Dict:
        """Validate test framework implementation."""
        self.log("🧪 Validating Test Framework")

        test_files = [
            ("tests/test_quality_framework.py", "Quality framework tests"),
        ]

        results = {}
        for test_file, description in test_files:
            exists = self.validate_file_exists(test_file, description)
            results[test_file] = exists

        # Check for test discovery
        if (self.root_path / "tests").exists():
            test_count = len(list((self.root_path / "tests").glob("test_*.py")))
            self.log(f"Test files discovered: {test_count}")
            results["test_file_count"] = test_count

        return results

    def validate_documentation(self) -> Dict:
        """Validate documentation structure."""
        self.log("📚 Validating Documentation")

        doc_files = [
            ("docs/index.md", "Main documentation"),
            ("docs/development/quality.md", "Quality documentation"),
        ]

        results = {}
        for doc_file, description in doc_files:
            exists = self.validate_file_exists(doc_file, description)
            results[doc_file] = exists

        return results

    def validate_ci_cd_pipeline(self) -> Dict:
        """Validate CI/CD pipeline configuration."""
        self.log("🚀 Validating CI/CD Pipeline")

        pipeline_files = [
            (".github/workflows/quality_assurance.yml", "Quality assurance workflow"),
        ]

        results = {}
        for file_path, description in pipeline_files:
            exists = self.validate_file_exists(file_path, description)
            results[file_path] = exists

        return results

    def validate_dependencies(self) -> Dict:
        """Validate required dependencies."""
        self.log("📦 Validating Dependencies")

        required_packages = [
            ("pytest", "Test framework"),
            ("coverage", "Coverage analysis"),
            ("black", "Code formatting"),
            ("isort", "Import sorting"),
            ("flake8", "Code linting"),
        ]

        results = {}
        for package, description in required_packages:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import {package}"], capture_output=True, text=True
                )
                available = result.returncode == 0
                status = "✅ AVAILABLE" if available else "❌ MISSING"
                self.log(f"{description} ({package}): {status}")
                results[package] = available
            except Exception:
                results[package] = False
                self.log(f"{description} ({package}): ❌ ERROR", "ERROR")

        return results

    def validate_quality_thresholds(self) -> Dict:
        """Validate quality threshold configuration."""
        self.log("📊 Validating Quality Thresholds")

        results = {}

        # Check pytest configuration
        pytest_config = self.root_path / "pytest.ini"
        if pytest_config.exists():
            with open(pytest_config, "r") as f:
                content = f.read()
                has_coverage = "--cov=" in content
                has_threshold = "--cov-fail-under=" in content
                results["pytest_coverage_configured"] = has_coverage and has_threshold
                self.log(
                    f"Pytest coverage configuration: {'✅ CONFIGURED' if has_coverage and has_threshold else '⚠️ INCOMPLETE'}"
                )
        else:
            results["pytest_coverage_configured"] = False

        # Check pyproject.toml for tool configurations
        pyproject_config = self.root_path / "pyproject.toml"
        if pyproject_config.exists():
            with open(pyproject_config, "r") as f:
                content = f.read()
                has_black = "[tool.black]" in content
                has_isort = "[tool.isort]" in content
                has_mypy = "[tool.mypy]" in content
                results["tool_configurations"] = has_black and has_isort and has_mypy
                self.log(
                    f"Tool configurations: {'✅ COMPLETE' if has_black and has_isort and has_mypy else '⚠️ INCOMPLETE'}"
                )
        else:
            results["tool_configurations"] = False

        return results

    def generate_recommendations(self):
        """Generate improvement recommendations."""
        recommendations = []

        # Check validation results for missing components
        all_validations = self.results["validations"]

        if not all_validations.get("configuration_files", {}).get("pytest.ini", False):
            recommendations.append("Configure pytest.ini with coverage requirements")

        if not all_validations.get("configuration_files", {}).get("pyproject.toml", False):
            recommendations.append("Create pyproject.toml with tool configurations")

        if not all_validations.get("quality_scripts", {}).get("scripts/quality_gates.py", False):
            recommendations.append("Implement comprehensive quality gates script")

        if not all_validations.get("ci_cd_pipeline", {}).get(
            ".github/workflows/quality_assurance.yml", False
        ):
            recommendations.append("Set up GitHub Actions quality assurance workflow")

        # Check dependency availability
        dependencies = all_validations.get("dependencies", {})
        missing_deps = [pkg for pkg, available in dependencies.items() if not available]
        if missing_deps:
            recommendations.append(f"Install missing dependencies: {', '.join(missing_deps)}")

        # Check test coverage
        test_count = all_validations.get("test_framework", {}).get("test_file_count", 0)
        if test_count < 5:
            recommendations.append("Increase test coverage with more comprehensive test files")

        self.results["recommendations"] = recommendations

    def run_validation(self) -> bool:
        """Run complete validation suite."""
        self.log("🚀 Starting Quality Implementation Validation")

        validation_functions = [
            ("directory_structure", self.validate_directory_structure),
            ("configuration_files", self.validate_configuration_files),
            ("quality_scripts", self.validate_quality_scripts),
            ("test_framework", self.validate_test_framework),
            ("documentation", self.validate_documentation),
            ("ci_cd_pipeline", self.validate_ci_cd_pipeline),
            ("dependencies", self.validate_dependencies),
            ("quality_thresholds", self.validate_quality_thresholds),
        ]

        for category, validation_func in validation_functions:
            try:
                result = validation_func()
                self.results["validations"][category] = result

                # Count passed/failed for this category
                if isinstance(result, dict):
                    for key, value in result.items():
                        self.results["summary"]["total_checks"] += 1
                        if value:
                            self.results["summary"]["passed"] += 1
                        else:
                            self.results["summary"]["failed"] += 1

            except Exception as e:
                self.log(f"Validation failed for {category}: {str(e)}", "ERROR")
                self.results["validations"][category] = {"error": str(e)}
                self.results["summary"]["failed"] += 1

        # Generate recommendations
        self.generate_recommendations()

        # Determine overall status
        total = self.results["summary"]["total_checks"]
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]

        if total == 0:
            self.results["overall_status"] = "error"
        elif failed == 0:
            self.results["overall_status"] = "excellent"
        elif passed / total >= 0.8:
            self.results["overall_status"] = "good"
        elif passed / total >= 0.6:
            self.results["overall_status"] = "fair"
        else:
            self.results["overall_status"] = "poor"

        return self.results["overall_status"] in ["excellent", "good"]

    def print_summary(self):
        """Print validation summary."""
        summary = self.results["summary"]
        status = self.results["overall_status"]

        print("\n" + "=" * 60)
        print("🏁 QUALITY IMPLEMENTATION VALIDATION SUMMARY")
        print("=" * 60)

        print(f"Total Checks: {summary['total_checks']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")

        status_symbols = {
            "excellent": "🌟 EXCELLENT",
            "good": "✅ GOOD",
            "fair": "⚠️ FAIR",
            "poor": "❌ POOR",
            "error": "💥 ERROR",
        }

        print(f"Overall Status: {status_symbols.get(status, status.upper())}")

        if self.results["recommendations"]:
            print(f"\n📋 Recommendations ({len(self.results['recommendations'])}):")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"  {i}. {rec}")

        print("=" * 60)

    def save_report(self, output_file: str = "quality_validation_report.json"):
        """Save validation report to file."""
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        self.log(f"Validation report saved to {output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate quality implementation")
    parser.add_argument(
        "--report",
        default="quality_validation_report.json",
        help="Output file for validation report",
    )

    args = parser.parse_args()

    validator = QualityValidator()

    try:
        success = validator.run_validation()
        validator.print_summary()
        validator.save_report(args.report)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        validator.log("Validation interrupted by user", "WARNING")
        sys.exit(130)
    except Exception as e:
        validator.log(f"Validation failed: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
