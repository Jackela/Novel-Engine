#!/usr/bin/env python3
"""
CI Requirements Consistency Check Script

Verifies that pyproject.toml and requirements.txt are consistent.
This prevents the "works on my machine" problem caused by dependency drift.

Usage:
    python scripts/ci-check-requirements.py
    python scripts/ci-check-requirements.py --fix  # Auto-fix inconsistencies

Exit Codes:
    0 - All checks passed
    1 - Inconsistencies found
    2 - Error running check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set


class Dependency(NamedTuple):
    """Represents a parsed dependency."""
    name: str
    version: Optional[str]
    extras: Optional[str]
    specifier: str  # Original specifier for comparison

    def normalized_name(self) -> str:
        """Return normalized package name (lowercase with hyphens replaced by underscores)."""
        return self.name.lower().replace("-", "_").replace(".", "_")


class CheckResult(NamedTuple):
    """Result of a consistency check."""
    passed: bool
    message: str
    fixable: bool = False


class RequirementsChecker:
    """Checks consistency between dependency files."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_dependency(self, line: str) -> Optional[Dependency]:
        """Parse a dependency line into a Dependency object."""
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#") or line.startswith("-"):
            return None

        # Skip editable installs and URLs for comparison
        if line.startswith("-e") or "://" in line:
            return None

        # Handle extras like package[extra]>=1.0
        extras_match = re.match(r'^([a-zA-Z0-9._-]+)(?:\[([^\]]+)\])?(.*)$', line)
        if not extras_match:
            return None

        name = extras_match.group(1)
        extras = extras_match.group(2)
        version_spec = extras_match.group(3).strip() if extras_match.group(3) else ""

        # Clean up version specifier
        version = None
        if version_spec:
            # Remove comments
            version_spec = version_spec.split("#")[0].strip()
            # Extract version number for comparison
            version_match = re.search(r'[=<>~!]+\s*([0-9][0-9a-zA-Z._]*)', version_spec)
            if version_match:
                version = version_match.group(1)

        return Dependency(
            name=name,
            version=version,
            extras=extras,
            specifier=line
        )

    def parse_requirements_txt(self, filepath: Path) -> Dict[str, Dependency]:
        """Parse requirements.txt file and return dict of normalized name -> Dependency."""
        dependencies: Dict[str, Dependency] = {}

        if not filepath.exists():
            self.errors.append(f"Requirements file not found: {filepath}")
            return dependencies

        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                dep = self.parse_dependency(line)
                if dep:
                    normalized = dep.normalized_name()
                    if normalized in dependencies:
                        self.warnings.append(
                            f"Duplicate dependency in {filepath}:{line_num}: {dep.name}"
                        )
                    dependencies[normalized] = dep

        return dependencies

    def parse_pyproject_toml_dependencies(self) -> Dict[str, Dependency]:
        """Parse dependencies from pyproject.toml."""
        dependencies: Dict[str, Dependency] = {}
        pyproject_path = self.root_dir / "pyproject.toml"

        if not pyproject_path.exists():
            self.errors.append(f"pyproject.toml not found: {pyproject_path}")
            return dependencies

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)

        # Get project.dependencies
        project_deps = data.get("project", {}).get("dependencies", [])
        for dep_str in project_deps:
            dep = self.parse_dependency(dep_str)
            if dep:
                dependencies[dep.normalized_name()] = dep

        # Get optional dependencies (dev, test, etc.)
        optional_deps = data.get("project", {}).get("optional-dependencies", {})
        for group, deps in optional_deps.items():
            for dep_str in deps:
                dep = self.parse_dependency(dep_str)
                if dep:
                    normalized = dep.normalized_name()
                    # Only add if not already in main dependencies
                    if normalized not in dependencies:
                        dependencies[normalized] = dep

        return dependencies

    def check_file_exists(self, filepath: Path) -> CheckResult:
        """Check if a requirements file exists."""
        if filepath.exists():
            return CheckResult(True, f"✓ {filepath} exists")
        return CheckResult(False, f"✗ {filepath} not found", fixable=False)

    def check_consistency(
        self,
        txt_deps: Dict[str, Dependency],
        toml_deps: Dict[str, Dependency],
        txt_name: str
    ) -> List[CheckResult]:
        """Check consistency between requirements.txt and pyproject.toml."""
        results: List[CheckResult] = []

        # Check for packages in txt but not in toml
        only_in_txt = set(txt_deps.keys()) - set(toml_deps.keys())
        if only_in_txt:
            packages = [txt_deps[k].name for k in sorted(only_in_txt)]
            results.append(CheckResult(
                False,
                f"Packages in {txt_name} but not in pyproject.toml: {packages}",
                fixable=True
            ))

        # Check for packages in toml but not in txt
        only_in_toml = set(toml_deps.keys()) - set(txt_deps.keys())
        if only_in_toml:
            packages = [toml_deps[k].name for k in sorted(only_in_toml)]
            results.append(CheckResult(
                False,
                f"Packages in pyproject.toml but not in {txt_name}: {packages}",
                fixable=True
            ))

        # Check version mismatches
        common = set(txt_deps.keys()) & set(toml_deps.keys())
        for key in sorted(common):
            txt_dep = txt_deps[key]
            toml_dep = toml_deps[key]

            # Only compare if both have version specs
            if txt_dep.version and toml_dep.version:
                if txt_dep.version != toml_dep.version:
                    results.append(CheckResult(
                        False,
                        f"Version mismatch for {txt_dep.name}: "
                        f"{txt_name}={txt_dep.version}, pyproject.toml={toml_dep.version}",
                        fixable=True
                    ))

        return results

    def run_all_checks(self) -> bool:
        """Run all consistency checks. Returns True if all passed."""
        print("=" * 60)
        print("Requirements Consistency Check")
        print("=" * 60)

        all_passed = True

        # Check main requirements.txt
        req_path = self.root_dir / "requirements.txt"
        result = self.check_file_exists(req_path)
        print(f"\n{result.message}")
        if not result.passed:
            all_passed = False
        else:
            txt_deps = self.parse_requirements_txt(req_path)
            toml_deps = self.parse_pyproject_toml_dependencies()

            print(f"  Found {len(txt_deps)} dependencies in requirements.txt")
            print(f"  Found {len(toml_deps)} dependencies in pyproject.toml")

            results = self.check_consistency(txt_deps, toml_deps, "requirements.txt")
            for r in results:
                print(f"\n  {r.message}")
                if not r.passed:
                    all_passed = False

        # Check requirements directory
        req_dir = self.root_dir / "requirements"
        if req_dir.exists():
            for req_file in sorted(req_dir.glob("requirements*.txt")):
                result = self.check_file_exists(req_file)
                print(f"\n{result.message}")
                if result.passed:
                    txt_deps = self.parse_requirements_txt(req_file)
                    toml_deps = self.parse_pyproject_toml_dependencies()
                    results = self.check_consistency(
                        txt_deps, toml_deps, req_file.name
                    )
                    for r in results:
                        print(f"  {r.message}")
                        if not r.passed:
                            all_passed = False

        # Print warnings
        if self.warnings:
            print("\n" + "-" * 60)
            print("Warnings:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        # Print summary
        print("\n" + "=" * 60)
        if all_passed and not self.errors:
            print("✅ All consistency checks passed!")
        else:
            print("❌ Some consistency checks failed")
            print("\nTo fix: Run `make sync-requirements` or `uv pip compile`")
        print("=" * 60)

        return all_passed and not self.errors

    def generate_fix_suggestion(self) -> str:
        """Generate shell commands to fix inconsistencies."""
        return """
# To fix requirements inconsistencies, run:

# Option 1: Using uv (recommended, if installed)
uv pip compile pyproject.toml -o requirements.txt

# Option 2: Using pip-tools
pip-compile pyproject.toml -o requirements.txt

# Option 3: Manual sync (copy dependencies from pyproject.toml to requirements.txt)
# Edit requirements.txt to match pyproject.toml dependencies
"""


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check requirements file consistency"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Show fix suggestions (does not auto-fix)"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory"
    )

    args = parser.parse_args()

    if args.fix:
        print(RequirementsChecker(args.root).generate_fix_suggestion())
        return 0

    checker = RequirementsChecker(args.root)
    passed = checker.run_all_checks()

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
