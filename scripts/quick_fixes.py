#!/usr/bin/env python3
"""Quick fixes for automatic type corrections."""

import re
from pathlib import Path


def fix_init_return_types(file_path: Path) -> tuple[int, list[str]]:
    """Add -> None to __init__ methods that lack return type annotation."""
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes = []
    
    # Pattern to match __init__ without return type (not followed by ->)
    # Matches: def __init__(self, ...)  followed by :\n or : # comment\n
    pattern = r'(def __init__\([^)]*\))\s*:\s*\n'
    
    def replace_init(match):
        return f'{match.group(1)} -> None:\n'
    
    content = re.sub(pattern, replace_init, content)
    
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        count = len(re.findall(pattern, original_content))
        return count, [f"Fixed {count} __init__ in {file_path}"]
    
    return 0, []


def fix_any_typo(file_path: Path) -> tuple[int, list[str]]:
    """Fix lowercase 'any' used as type annotation to 'Any'."""
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes = []
    
    # Pattern to match lowercase 'any' as type annotation
    # Matches: : any or -> any followed by comma, colon, or end
    patterns = [
        (r':\s*any\s*([,:=\)])', r': Any\1'),  # Type annotation
        (r'->\s*any\s*([,:=\)\n])', r'-> Any\1'),  # Return type
        (r'Union\[any', r'Union[Any'),  # Union types
        (r'Optional\[any', r'Optional[Any'),  # Optional types
        (r'Dict\[([^,]+),\s*any\]', r'Dict[\1, Any]'),  # Dict value
        (r'List\[any\]', r'List[Any]'),  # List types
        (r'dict\[any', r'dict[Any'),  # Lowercase dict
        (r'list\[any', r'list[Any]'),  # Lowercase list
    ]
    
    for pattern, replacement in patterns:
        content, count = re.subn(pattern, replacement, content)
        if count > 0:
            fixes.append(f"Fixed {count} 'any' -> 'Any' in {file_path}")
    
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return len(fixes), fixes
    
    return 0, []


def add_missing_any_import(file_path: Path) -> tuple[int, list[str]]:
    """Add Any import from typing if Any is used but not imported."""
    content = file_path.read_text(encoding="utf-8")
    
    # Check if Any is used but not imported
    if 'Any' not in content or 'from typing import' not in content:
        return 0, []
    
    # Check if Any is already in imports
    if 'Any' in re.search(r'from typing import [^\n]+', content).group(0) if re.search(r'from typing import [^\n]+', content) else False:
        return 0, []
    
    # Add Any to existing typing import
    typing_import = re.search(r'(from typing import [^\n]+)', content)
    if typing_import and 'Any' not in typing_import.group(1):
        new_import = typing_import.group(1) + ', Any'
        content = content.replace(typing_import.group(1), new_import)
        file_path.write_text(content, encoding="utf-8")
        return 1, [f"Added Any import to {file_path}"]
    
    return 0, []


def main():
    src_dir = Path("src")
    
    init_fixes = 0
    any_fixes = 0
    import_fixes = 0
    fix_log = []
    
    # Find all Python files
    py_files = list(src_dir.rglob("*.py"))
    
    print(f"Scanning {len(py_files)} Python files...")
    
    for py_file in py_files:
        # Fix __init__ return types
        count, logs = fix_init_return_types(py_file)
        init_fixes += count
        fix_log.extend(logs)
        
        # Fix any -> Any
        count, logs = fix_any_typo(py_file)
        any_fixes += count
        fix_log.extend(logs)
    
    print(f"\n=== Quick Fixes Report ===")
    print(f"Files processed: {len(py_files)}")
    print(f"__init__ return types added: {init_fixes}")
    print(f"any -> Any fixes: {any_fixes}")
    print(f"Import fixes: {import_fixes}")
    
    # Save report
    report = f"""# Quick Fixes Report

## Summary
- Files processed: {len(py_files)}
- __init__ return types added: {init_fixes}
- any -> Any fixes: {any_fixes}
- Import fixes: {import_fixes}

## Fix Log
"""
    for log in fix_log[:100]:  # Limit log size
        report += f"- {log}\n"
    
    Path("quick_fixes_report.md").write_text(report, encoding="utf-8")
    print(f"\nReport saved to quick_fixes_report.md")


if __name__ == "__main__":
    main()
