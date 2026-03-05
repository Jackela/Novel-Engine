#!/usr/bin/env python3
"""
Fix missing return type annotations for async methods.
"""

import re
from pathlib import Path

SRC_DIR = Path("/mnt/d/Code/Novel-Engine/src")

# Patterns to fix: (pattern, replacement)
PATTERNS = [
    # Async methods with self but no return type
    (r'(\s)async def ([a-z_][a-z0-9_]*)\(self\):', r'\1async def \2(self) -> None:'),
    # Methods with self but no return type (not starting with _)
    (r'^(\s+)def ([a-z_][a-z0-9_]*)\(self\)(?!\s*->)(?!\s*:\s*\n)', r'\1def \2(self) -> None:'),
]

def fix_file(filepath: Path) -> int:
    """Fix patterns in a file. Returns number of fixes."""
    content = filepath.read_text()
    original = content
    fixes = 0
    
    for pattern, replacement in PATTERNS:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            fixes += 1
            content = new_content
    
    if content != original:
        filepath.write_text(content)
    
    return fixes

def main():
    total = 0
    for filepath in SRC_DIR.rglob("*.py"):
        if "__pycache__" in str(filepath):
            continue
        if "test" in str(filepath).lower():
            continue
        try:
            fixes = fix_file(filepath)
            if fixes > 0:
                print(f"Fixed {filepath}")
                total += fixes
        except Exception as e:
            print(f"Error in {filepath}: {e}")
    
    print(f"Total files modified: {total}")

if __name__ == "__main__":
    main()
