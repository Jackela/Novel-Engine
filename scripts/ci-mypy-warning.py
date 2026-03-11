#!/usr/bin/env python3
"""
MyPy Warning Script for Pre-Push Hook

This script shows MyPy status as a WARNING (not blocking).
Used during the gradual MyPy error reduction phase.
"""

import subprocess
import sys


def get_mypy_error_count():
    """Run mypy and count errors."""
    result = subprocess.run(
        ["mypy", "src/", "--ignore-missing-imports", "--no-error-summary"],
        capture_output=True,
        text=True
    )
    
    error_lines = [line for line in result.stdout.split('\n') 
                   if line.strip() and ':' in line and not line.startswith(' ')]
    
    return len(error_lines)

def main():
    print("=" * 70)
    print("⚠️  MyPy STATUS (WARNING - NOT BLOCKING)")
    print("=" * 70)
    
    error_count = get_mypy_error_count()
    
    # Target and progress
    TARGET = 0
    STARTING = 4412
    
    progress_pct = ((STARTING - error_count) / STARTING) * 100
    
    print(f"\nCurrent MyPy errors: {error_count}")
    print(f"Starting errors:     {STARTING}")
    print(f"Progress:            {progress_pct:.1f}% fixed")
    print(f"Target:              {TARGET} errors")
    print()
    
    if error_count == 0:
        print("🎉 EXCELLENT! MyPy has ZERO errors!")
        print("   The codebase is fully type-safe.")
        return 0
    elif error_count < 100:
        print("🟡 ALMOST THERE! Less than 100 errors remaining.")
        print("   Continue fixing to reach zero.")
    elif error_count < 500:
        print("🟡 GOOD PROGRESS! Less than 500 errors.")
        print("   Keep fixing type errors.")
    else:
        print("🔴 IN PROGRESS. Continue fixing type errors.")
    
    print()
    print("Note: MyPy errors are NOT blocking push right now.")
    print("      But please continue fixing them!")
    print()
    print("To see all errors: mypy src/ --ignore-missing-imports")
    print("To fix errors:     Use MyPy fix agents")
    print()
    
    # Always return 0 (not blocking)
    return 0

if __name__ == "__main__":
    sys.exit(main())
