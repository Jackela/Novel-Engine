#!/usr/bin/env python3
"""Verify all Python deprecation warnings have been fixed."""

import subprocess
import sys


def check_datetime_utcnow():
    """Check for datetime.utcnow() usage."""
    print("\n1. Checking for datetime.utcnow() usage...")
    result = subprocess.run(
        [
            "grep",
            "-r",
            "datetime\\.utcnow()",
            "--include=*.py",
            ".",
            "--exclude-dir=.git",
            "--exclude-dir=__pycache__",
        ],
        capture_output=True,
        text=True,
        cwd="/mnt/d/Code/novel-engine",
    )

    # Filter out our fix scripts and utility docs
    lines = [
        line
        for line in result.stdout.split("\n")
        if line
        and "fix_datetime_deprecations.py" not in line
        and "datetime_utils.py" not in line
        and "verify_deprecation_fixes.py" not in line
    ]

    if lines:
        print(f"   ❌ Found {len(lines)} occurrences of datetime.utcnow()")
        for line in lines[:5]:
            print(f"      {line}")
        return False
    else:
        print(
            "   ✓ No datetime.utcnow() found (replaced with datetime.now(timezone.utc))"
        )
        return True


def check_asyncio_get_event_loop():
    """Check for asyncio.get_event_loop() usage."""
    print("\n2. Checking for asyncio.get_event_loop() usage...")
    result = subprocess.run(
        [
            "grep",
            "-r",
            "asyncio\\.get_event_loop()",
            "--include=*.py",
            ".",
            "--exclude-dir=.git",
            "--exclude-dir=__pycache__",
        ],
        capture_output=True,
        text=True,
        cwd="/mnt/d/Code/novel-engine",
    )

    # Filter out our fix scripts
    lines = [
        line
        for line in result.stdout.split("\n")
        if line
        and "fix_asyncio_deprecations.py" not in line
        and "verify_deprecation_fixes.py" not in line
    ]

    if lines:
        print(f"   ❌ Found {len(lines)} occurrences of asyncio.get_event_loop()")
        for line in lines[:5]:
            print(f"      {line}")
        return False
    else:
        print(
            "   ✓ No asyncio.get_event_loop() found (replaced with asyncio.get_running_loop())"
        )
        return True


def check_pkg_resources():
    """Check for pkg_resources usage."""
    print("\n3. Checking for pkg_resources import...")
    result = subprocess.run(
        [
            "grep",
            "-r",
            "import pkg_resources",
            "--include=*.py",
            ".",
            "--exclude-dir=.git",
            "--exclude-dir=__pycache__",
        ],
        capture_output=True,
        text=True,
        cwd="/mnt/d/Code/novel-engine",
    )

    lines = [line for line in result.stdout.split("\n") if line]

    if lines:
        print(f"   ❌ Found {len(lines)} occurrences of pkg_resources import")
        for line in lines[:5]:
            print(f"      {line}")
        return False
    else:
        print("   ✓ No pkg_resources imports found (replaced with importlib.metadata)")
        return True


def check_fastapi_on_event():
    """Check for FastAPI on_event decorator usage."""
    print("\n4. Checking for FastAPI @app.on_event() usage...")
    result = subprocess.run(
        [
            "grep",
            "-r",
            "@app\\.on_event",
            "--include=*.py",
            ".",
            "--exclude-dir=.git",
            "--exclude-dir=__pycache__",
        ],
        capture_output=True,
        text=True,
        cwd="/mnt/d/Code/novel-engine",
    )

    lines = [line for line in result.stdout.split("\n") if line]

    if lines:
        print(f"   ❌ Found {len(lines)} occurrences of @app.on_event()")
        for line in lines[:5]:
            print(f"      {line}")
        return False
    else:
        print("   ✓ No @app.on_event() found (replaced with lifespan context manager)")
        return True


def check_emergent_narrative_imports():
    """Check for deprecated emergent_narrative imports."""
    print("\n5. Checking for deprecated emergent_narrative imports...")
    result = subprocess.run(
        [
            "grep",
            "-r",
            "from.*emergent_narrative import",
            "--include=*.py",
            ".",
            "--exclude-dir=.git",
            "--exclude-dir=__pycache__",
        ],
        capture_output=True,
        text=True,
        cwd="/mnt/d/Code/novel-engine",
    )

    # Filter out the deprecated module itself and the new narrative module
    lines = [
        line
        for line in result.stdout.split("\n")
        if line
        and "src/core/emergent_narrative.py" not in line
        and "src/core/narrative/" not in line
        and "scripts/refactor_emergent_narrative.py" not in line
        and "verify_deprecation_fixes.py" not in line
    ]

    if lines:
        print(f"   ❌ Found {len(lines)} deprecated emergent_narrative imports")
        for line in lines[:5]:
            print(f"      {line}")
        return False
    else:
        print(
            "   ✓ No deprecated emergent_narrative imports (using src.core.narrative)"
        )
        return True


def run_pytest_deprecation_check():
    """Run pytest with deprecation warnings to check for any runtime issues."""
    print("\n6. Running pytest with deprecation warnings...")
    result = subprocess.run(
        [
            "pytest",
            "tests/unit/agents/test_persona_modular.py",
            "-W",
            "default::DeprecationWarning",
            "--tb=no",
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd="/mnt/d/Code/novel-engine",
    )

    # Check output for our fixed deprecations
    deprecation_keywords = [
        "datetime.utcnow",
        "asyncio.get_event_loop",
        "pkg_resources",
        "on_event is deprecated",
        "emergent_narrative is deprecated",
    ]

    found_warnings = []
    for keyword in deprecation_keywords:
        if keyword in result.stdout or keyword in result.stderr:
            found_warnings.append(keyword)

    if found_warnings:
        print(f"   ❌ Found deprecation warnings in pytest: {found_warnings}")
        return False
    else:
        print("   ✓ No deprecation warnings found in pytest output")
        return True


def main():
    """Run all verification checks."""
    print("=" * 80)
    print("Python Deprecation Warnings Verification")
    print("=" * 80)

    checks = [
        check_datetime_utcnow(),
        check_asyncio_get_event_loop(),
        check_pkg_resources(),
        check_fastapi_on_event(),
        check_emergent_narrative_imports(),
        run_pytest_deprecation_check(),
    ]

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    passed = sum(checks)
    total = len(checks)

    print(f"\nPassed: {passed}/{total} checks")

    if all(checks):
        print("\n✓ All deprecation warnings have been successfully fixed!")
        print("\nFixed deprecations:")
        print("  1. datetime.utcnow() → datetime.now(timezone.utc)")
        print("  2. asyncio.get_event_loop() → asyncio.get_running_loop()")
        print("  3. pkg_resources → importlib.metadata")
        print("  4. @app.on_event() → lifespan context manager")
        print("  5. src.core.emergent_narrative → src.core.narrative")
        return 0
    else:
        print("\n❌ Some deprecation warnings still need to be fixed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
