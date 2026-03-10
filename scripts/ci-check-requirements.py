#!/usr/bin/env python3
"""Check consistency between pyproject.toml and requirements.txt (production deps only)"""

import sys
import tomllib
from pathlib import Path

# 开发依赖列表 - 这些不需要在requirements.txt中
DEV_DEPS = {
    "bandit",
    "black",
    "coverage",
    "flake8",
    "import-linter",
    "isort",
    "mkdocs",
    "mkdocs-material",
    "mkdocstrings",
    "mypy",
    "pre-commit",
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "pytest-timeout",
    "safety",
    # test-specific deps
    "pytest-benchmark",
    "pytest-html",
    "pytest-mock",
    "pytest-xdist",
}


def parse_requirements(filepath):
    """Parse requirements.txt and return dict of {package: version_spec}"""
    packages = {}
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Handle version specifiers
                for sep in ["==", ">=", "<=", "~=", ">", "<", "!="]:
                    if sep in line:
                        name, version = line.split(sep, 1)
                        packages[name.strip().lower()] = line
                        break
                else:
                    packages[line.lower()] = line
    except FileNotFoundError:
        return None
    return packages


def check_consistency(name, req_file, pyproject_deps, is_main=False):
    """Check consistency for a requirements file"""
    req_packages = parse_requirements(req_file)
    if req_packages is None:
        print(f"  ✗ {name} not found")
        return False

    print(f"  ✓ {name} exists")
    print(f"    Found {len(req_packages)} dependencies")

    # For main requirements.txt, filter out dev deps from pyproject
    pyproject_prod = {k: v for k, v in pyproject_deps.items() if k not in DEV_DEPS}

    if is_main:
        # Check: production deps in pyproject should be in requirements.txt
        missing = set(pyproject_prod.keys()) - set(req_packages.keys())
        extra = set(req_packages.keys()) - set(pyproject_prod.keys())
    else:
        # For other requirements files, just check against all pyproject deps
        missing = set(req_packages.keys()) - set(pyproject_deps.keys())
        extra = set()

    has_issues = False
    if missing:
        print(f"    ⚠ Missing in {name}: {sorted(missing)}")
        has_issues = True
    if extra:
        print(f"    ℹ Extra in {name} (not in pyproject.toml): {sorted(extra)}")

    return not has_issues


def main():
    root = Path(__file__).parent.parent
    pyproject = root / "pyproject.toml"

    print("=" * 60)
    print("Requirements Consistency Check (Production Only)")
    print("=" * 60)
    print()

    # Parse pyproject.toml
    with open(pyproject, "rb") as f:
        pyproject_data = tomllib.load(f)

    pyproject_deps = {}
    for dep in pyproject_data.get("project", {}).get("dependencies", []):
        for sep in ["==", ">=", "<=", "~=", ">", "<"]:
            if sep in dep:
                name = dep.split(sep)[0].strip().lower()
                pyproject_deps[name] = dep
                break
        else:
            pyproject_deps[dep.lower()] = dep

    print(f"  Found {len(pyproject_deps)} total dependencies in pyproject.toml")
    print(f"  {len(DEV_DEPS)} development dependencies excluded from check")
    print()

    # Check main requirements.txt
    all_passed = True
    req_file = root / "requirements.txt"
    if not check_consistency(
        "requirements.txt", req_file, pyproject_deps, is_main=True
    ):
        all_passed = False

    print()

    if all_passed:
        print("✅ Production requirements are consistent")
        print()
        print("Note: Development dependencies should be installed via:")
        print("  pip install -r requirements-dev.txt")
        return 0
    else:
        print("❌ Production requirements mismatch")
        print()
        print("To fix: Update requirements.txt with missing packages")
        return 1


if __name__ == "__main__":
    sys.exit(main())
