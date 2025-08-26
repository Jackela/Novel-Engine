#!/usr/bin/env python3
"""
Test migration validation script

Validates the test migration process and ensures all tests are properly
organized without loss of functionality.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestMigrationValidator:
    """Validates test migration and organization."""
    
    def __init__(self):
        self.project_root = project_root
        self.tests_dir = self.project_root / "tests"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "validation_results": {},
            "migration_status": "unknown",
            "recommendations": []
        }
    
    def validate_directory_structure(self) -> Dict[str, bool]:
        """Validate the new directory structure exists."""
        required_dirs = [
            "tests/integration/api",
            "tests/integration/core", 
            "tests/integration/bridges",
            "tests/integration/frontend",
            "tests/integration/interactions",
            "tests/integration/agents",
            "tests/integration/components",
            "tests/unit/agents",
            "tests/unit/interactions", 
            "tests/unit/quality",
            "tests/performance"
        ]
        
        results = {}
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            results[dir_path] = full_path.exists() and full_path.is_dir()
            
            # Check for __init__.py files
            init_file = full_path / "__init__.py"
            results[f"{dir_path}/__init__.py"] = init_file.exists()
        
        return results
    
    def validate_pytest_discovery(self) -> Dict[str, any]:
        """Validate pytest can discover tests in new structure."""
        results = {}
        
        test_commands = [
            ("integration", ["python", "-m", "pytest", "--collect-only", "tests/integration/", "--quiet"]),
            ("unit", ["python", "-m", "pytest", "--collect-only", "tests/unit/", "--quiet"]),
            ("performance", ["python", "-m", "pytest", "--collect-only", "tests/performance/", "--quiet"]),
            ("all", ["python", "-m", "pytest", "--collect-only", "tests/", "--quiet"])
        ]
        
        for test_type, command in test_commands:
            try:
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True,
                    cwd=self.project_root
                )
                
                results[test_type] = {
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "tests_found": "collected" in result.stdout.lower()
                }
                
                if "collected" in result.stdout:
                    # Extract test count
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "collected" in line:
                            results[test_type]["test_count"] = line.strip()
                            break
                            
            except Exception as e:
                results[test_type] = {"error": str(e)}
        
        return results
    
    def validate_import_resolution(self) -> Dict[str, bool]:
        """Test that imports work correctly in new structure."""
        import_tests = [
            ("conftest", "from tests.conftest import pytest_configure"),
            ("fixtures", "from tests.fixtures import *"),
            ("integration_init", "import tests.integration"),
            ("unit_init", "import tests.unit"), 
            ("performance_init", "import tests.performance")
        ]
        
        results = {}
        for test_name, import_stmt in import_tests:
            try:
                exec(import_stmt)
                results[test_name] = True
            except Exception as e:
                results[test_name] = False
                results[f"{test_name}_error"] = str(e)
        
        return results
    
    def count_test_files(self) -> Dict[str, int]:
        """Count test files in various locations."""
        counts = {}
        
        # Count files in different directories
        locations = [
            ("legacy", self.tests_dir / "legacy"),
            ("root_tests", self.tests_dir / "root_tests"),
            ("unit_existing", self.tests_dir / "unit"),
            ("integration_existing", self.tests_dir / "integration"),
            ("performance_existing", self.tests_dir / "performance"),
            ("security_existing", self.tests_dir / "security"),
            ("root_level", self.tests_dir)
        ]
        
        for location_name, path in locations:
            if path.exists():
                if path.is_dir():
                    counts[location_name] = len([
                        f for f in path.rglob("test_*.py") 
                        if f.is_file() and not f.name.startswith("__")
                    ])
                else:
                    counts[location_name] = 0
            else:
                counts[location_name] = 0
        
        # Count root level test files
        root_test_files = [
            f for f in self.tests_dir.iterdir() 
            if f.is_file() and f.name.startswith("test_") and f.suffix == ".py"
        ]
        counts["root_level_files"] = len(root_test_files)
        
        return counts
    
    def analyze_test_distribution(self) -> Dict[str, List[str]]:
        """Analyze how tests should be distributed."""
        distribution = {
            "api_tests": [],
            "core_tests": [],
            "bridge_tests": [],
            "agent_tests": [],
            "interaction_tests": [],
            "performance_tests": [],
            "security_tests": [],
            "frontend_tests": [],
            "quality_tests": [],
            "unclassified": []
        }
        
        # Scan for all test files
        all_test_files = list(self.tests_dir.rglob("test_*.py"))
        
        for test_file in all_test_files:
            rel_path = str(test_file.relative_to(self.tests_dir))
            filename = test_file.name.lower()
            
            # Classify by filename patterns
            if "api" in filename or "server" in filename or "endpoint" in filename:
                distribution["api_tests"].append(rel_path)
            elif "director" in filename or "orchestrat" in filename or "config" in filename:
                distribution["core_tests"].append(rel_path)
            elif "bridge" in filename or "llm" in filename and "integration" in filename:
                distribution["bridge_tests"].append(rel_path)
            elif "agent" in filename or "persona" in filename or "character" in filename:
                distribution["agent_tests"].append(rel_path)
            elif "interaction" in filename or "equipment" in filename:
                distribution["interaction_tests"].append(rel_path)
            elif "performance" in filename or "async" in filename or "optimization" in filename:
                distribution["performance_tests"].append(rel_path)
            elif "security" in filename:
                distribution["security_tests"].append(rel_path)
            elif "frontend" in filename or "ui" in filename:
                distribution["frontend_tests"].append(rel_path)
            elif "quality" in filename or "testing_framework" in filename:
                distribution["quality_tests"].append(rel_path)
            else:
                distribution["unclassified"].append(rel_path)
        
        return distribution
    
    def run_validation(self) -> Dict[str, any]:
        """Run complete validation suite."""
        print("🔍 Running test migration validation...")
        
        # Directory structure validation
        print("📁 Validating directory structure...")
        self.results["validation_results"]["directory_structure"] = self.validate_directory_structure()
        
        # Pytest discovery validation
        print("🔍 Validating pytest discovery...")
        self.results["validation_results"]["pytest_discovery"] = self.validate_pytest_discovery()
        
        # Import resolution validation
        print("📦 Validating import resolution...")
        self.results["validation_results"]["import_resolution"] = self.validate_import_resolution()
        
        # File counting
        print("📊 Counting test files...")
        self.results["validation_results"]["test_file_counts"] = self.count_test_files()
        
        # Test distribution analysis
        print("🗂️ Analyzing test distribution...")
        self.results["validation_results"]["test_distribution"] = self.analyze_test_distribution()
        
        # Overall migration status
        self.determine_migration_status()
        
        return self.results
    
    def determine_migration_status(self):
        """Determine overall migration readiness."""
        dir_issues = sum(1 for v in self.results["validation_results"]["directory_structure"].values() if not v)
        pytest_issues = sum(1 for v in self.results["validation_results"]["pytest_discovery"].values() 
                          if isinstance(v, dict) and v.get("return_code", 0) != 0)
        import_issues = sum(1 for v in self.results["validation_results"]["import_resolution"].values() 
                          if isinstance(v, bool) and not v)
        
        total_issues = dir_issues + pytest_issues + import_issues
        
        if total_issues == 0:
            self.results["migration_status"] = "ready"
            self.results["recommendations"] = ["✅ Structure is ready for migration"]
        elif total_issues < 5:
            self.results["migration_status"] = "mostly_ready"
            self.results["recommendations"] = [
                f"⚠️ {total_issues} minor issues found",
                "📋 Review validation details and fix issues",
                "🚀 Migration can proceed with caution"
            ]
        else:
            self.results["migration_status"] = "needs_work"
            self.results["recommendations"] = [
                f"❌ {total_issues} issues found",
                "🔧 Fix structural issues before migration",
                "📋 Review directory structure and configuration"
            ]
    
    def save_results(self, output_file: str = None):
        """Save validation results to file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_migration_validation_{timestamp}.json"
        
        output_path = self.project_root / "validation_reports" / output_file
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"📄 Validation results saved to: {output_path}")
        return output_path
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*60)
        print("📋 TEST MIGRATION VALIDATION SUMMARY")
        print("="*60)
        
        print(f"Migration Status: {self.results['migration_status'].upper()}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        print("\n📊 TEST FILE COUNTS:")
        counts = self.results["validation_results"]["test_file_counts"]
        total_files = sum(counts.values())
        for location, count in counts.items():
            print(f"  {location}: {count} files")
        print(f"  TOTAL: {total_files} test files")
        
        print(f"\n📁 DIRECTORY STRUCTURE:")
        dir_results = self.results["validation_results"]["directory_structure"]
        passed = sum(1 for v in dir_results.values() if v)
        total = len(dir_results)
        print(f"  {passed}/{total} checks passed")
        
        print(f"\n🔍 PYTEST DISCOVERY:")
        pytest_results = self.results["validation_results"]["pytest_discovery"]
        for test_type, result in pytest_results.items():
            if isinstance(result, dict):
                status = "✅" if result.get("return_code", 1) == 0 else "❌"
                test_info = result.get("test_count", "No tests found")
                print(f"  {status} {test_type}: {test_info}")
        
        print(f"\n📋 RECOMMENDATIONS:")
        for rec in self.results["recommendations"]:
            print(f"  {rec}")
        
        print("\n" + "="*60)


def main():
    """Main validation function."""
    validator = TestMigrationValidator()
    
    try:
        results = validator.run_validation()
        validator.print_summary()
        output_path = validator.save_results()
        
        return results["migration_status"] == "ready"
        
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)