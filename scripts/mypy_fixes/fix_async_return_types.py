#!/usr/bin/env python3
"""
Fix missing return type annotations for async methods.
Target: Methods like 'async def name(self):' -> 'async def name(self) -> None:'
"""

import re
from pathlib import Path

SRC_DIR = Path("/mnt/d/Code/Novel-Engine/src")

# Match async def method(self): (without return type)
ASYNC_SELF_PATTERN = re.compile(r'^(\s+)async def ([a-z_][a-z0-9_]*)\(self\):(?!\s*\n\s*->)', re.MULTILINE)

# Match async def method(self, ...): without return type
ASYNC_SELF_ARGS_PATTERN = re.compile(
    r'^(\s+)async def ([a-z_][a-z0-9_]*)\(self,\s*([^)]+)\):(?!\s*\n\s*->)',
    re.MULTILINE
)

# Match def method(self): without return type (for non-async)
DEF_SELF_PATTERN = re.compile(r'^(\s+)def ([a-z_][a-z0-9_]*)\(self\):(?!\s*\n\s*->)', re.MULTILINE)

def fix_file(filepath: Path) -> int:
    """Fix patterns in a file. Returns number of fixes."""
    content = filepath.read_text()
    original = content
    fixes = 0
    
    # Fix async def name(self):
    def repl_async_self(m):
        nonlocal fixes
        fixes += 1
        return f'{m.group(1)}async def {m.group(2)}(self) -> None:'
    content = ASYNC_SELF_PATTERN.sub(repl_async_self, content)
    
    # Fix async def name(self, args):
    def repl_async_args(m):
        nonlocal fixes
        fixes += 1
        return f'{m.group(1)}async def {m.group(2)}(self, {m.group(3)}) -> None:'
    content = ASYNC_SELF_ARGS_PATTERN.sub(repl_async_args, content)
    
    # Fix def name(self):
    def repl_def_self(m):
        nonlocal fixes
        fixes += 1
        return f'{m.group(1)}def {m.group(2)}(self) -> None:'
    content = DEF_SELF_PATTERN.sub(repl_def_self, content)
    
    if content != original:
        filepath.write_text(content)
        return fixes
    return 0

def main():
    total_fixes = 0
    files_modified = 0
    
    for filepath in SRC_DIR.rglob("*.py"):
        if "__pycache__" in str(filepath):
            continue
        if "test" in str(filepath).lower():
            continue
        try:
            fixes = fix_file(filepath)
            if fixes > 0:
                print(f"Fixed {fixes} in {filepath.relative_to(SRC_DIR)}")
                total_fixes += fixes
                files_modified += 1
        except Exception as e:
            print(f"Error in {filepath}: {e}")
    
    print(f"\nTotal files modified: {files_modified}")
    print(f"Total fixes: {total_fixes}")

if __name__ == "__main__":
    main()
