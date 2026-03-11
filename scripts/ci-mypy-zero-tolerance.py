#!/usr/bin/env python3
"""
MyPy Zero Tolerance Check for Pre-Push Hook

This script enforces ZERO MyPy errors before allowing push.
If there are any MyPy errors, the push is blocked.
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
    
    # Count lines that contain error indicators
    error_lines = [line for line in result.stdout.split('\n') 
                   if line.strip() and ':' in line and not line.startswith(' ')]
    
    return len(error_lines), result.stdout

def main():
    print("=" * 70)
    print("🔒 MyPy ZERO TOLERANCE CHECK")
    print("=" * 70)
    print()
    print("Running mypy type checker...")
    print()
    
    error_count, output = get_mypy_error_count()
    
    if error_count == 0:
        print("✅ SUCCESS: MyPy reports ZERO errors!")
        print()
        print("Push is ALLOWED.")
        return 0
    else:
        print(f"❌ FAILURE: MyPy reports {error_count} errors!")
        print()
        print("MyPy Output (first 50 lines):")
        print("-" * 70)
        lines = output.split('\n')[:50]
        for line in lines:
            print(line)
        print("-" * 70)
        print()
        print("🚫 PUSH BLOCKED!")
        print()
        print("You MUST fix ALL MyPy errors before pushing.")
        print()
        print("To see all errors:")
        print("  mypy src/ --ignore-missing-imports")
        print()
        print("To fix errors:")
        print("  1. Run the MyPy fix agents")
        print("  2. Or fix manually with proper type annotations")
        print()
        print("⚠️  NO EXCEPTIONS - All MyPy errors must be fixed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
