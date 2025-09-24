#!/usr/bin/env python3
"""
F-String Syntax Error Fix Tool

Systematically identifies and fixes malformed f-strings that span multiple lines
and cause black parsing failures.
"""

import re
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import ast


class FStringSyntaxFixer:
    def __init__(self):
        self.patterns = {
            # Pattern 1: Simple multi-line f-string with single expression
            "simple_multiline": re.compile(
                r'f"([^"]*?)\{\s*\n\s*([^}]+?)\s*\n\s*\}([^"]*?)"',
                re.MULTILINE | re.DOTALL,
            ),
            # Pattern 2: Complex multi-line f-string with multiple expressions
            "complex_multiline": re.compile(
                r'f"([^"]*?)\{\s*\n\s*([^}]+?)\s*\}\s*([^"]*?)\{\s*\n\s*([^}]+?)\s*\}([^"]*?)"',
                re.MULTILINE | re.DOTALL,
            ),
            # Pattern 3: Function call spanning lines within f-string
            "function_multiline": re.compile(
                r'f"([^"]*?)\{\s*\n\s*([^.]+\.[^}]+?)\s*\n\s*\}([^"]*?)"',
                re.MULTILINE | re.DOTALL,
            ),
        }

        self.fixed_files = []
        self.error_files = []

    def detect_fstring_errors(self, file_path: str) -> List[Tuple[int, str]]:
        """Detect lines with f-string syntax errors."""
        errors = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Try to parse with AST to detect syntax errors
            try:
                ast.parse(content)
                return []  # No syntax errors
            except SyntaxError as e:
                if (
                    "f-string" in str(e).lower()
                    or "invalid syntax" in str(e).lower()
                ):
                    # Check if it's likely an f-string issue
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if 'f"' in line and "{" in line and "}" not in line:
                            errors.append((i, line.strip()))
                        elif "{" not in line and "}" in line and i > 1:
                            # Potential closing brace of multiline f-string
                            prev_lines = lines[max(0, i - 5) : i - 1]
                            for j, prev_line in enumerate(prev_lines):
                                if 'f"' in prev_line and "{" in prev_line:
                                    errors.append(
                                        (
                                            i - len(prev_lines) + j + 1,
                                            prev_line.strip(),
                                        )
                                    )
                                    break

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

        return errors

    def fix_simple_multiline_fstring(self, content: str) -> str:
        """Fix simple multiline f-strings."""

        def replace_func(match):
            prefix = match.group(1)
            expression = re.sub(r"\s+", " ", match.group(2).strip())
            suffix = match.group(3)
            return f'f"{prefix}{{{expression}}}{suffix}"'

        return self.patterns["simple_multiline"].sub(replace_func, content)

    def fix_complex_multiline_fstring(self, content: str) -> str:
        """Fix complex multiline f-strings with multiple expressions."""

        def replace_func(match):
            prefix = match.group(1)
            expr1 = re.sub(r"\s+", " ", match.group(2).strip())
            middle = match.group(3)
            expr2 = re.sub(r"\s+", " ", match.group(4).strip())
            suffix = match.group(5)
            return f'f"{prefix}{{{expr1}}}{middle}{{{expr2}}}{suffix}"'

        return self.patterns["complex_multiline"].sub(replace_func, content)

    def fix_function_multiline_fstring(self, content: str) -> str:
        """Fix f-strings with function calls spanning lines."""

        def replace_func(match):
            prefix = match.group(1)
            expression = re.sub(r"\s+", " ", match.group(2).strip())
            suffix = match.group(3)
            return f'f"{prefix}{{{expression}}}{suffix}"'

        return self.patterns["function_multiline"].sub(replace_func, content)

    def fix_manual_patterns(self, content: str) -> str:
        """Fix known manual patterns that regex might miss."""
        lines = content.split("\n")
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Look for f-string start with unclosed brace
            if 'f"' in line and line.count("{") > line.count("}"):
                # Found potential multiline f-string
                fstring_start = i
                brace_count = line.count("{") - line.count("}")
                collected_lines = [line]

                # Collect subsequent lines until braces balance
                j = i + 1
                while j < len(lines) and brace_count > 0:
                    next_line = lines[j]
                    collected_lines.append(next_line)
                    brace_count += next_line.count("{") - next_line.count("}")
                    j += 1

                if brace_count == 0:
                    # We have a complete multiline f-string, fix it
                    combined = " ".join(
                        line.strip() for line in collected_lines
                    )
                    # Clean up extra whitespace in expressions
                    combined = re.sub(r"\{\s+", "{", combined)
                    combined = re.sub(r"\s+\}", "}", combined)
                    combined = re.sub(r"\s+", " ", combined)

                    fixed_lines.append(combined)
                    i = j
                    continue

            fixed_lines.append(line)
            i += 1

        return "\n".join(fixed_lines)

    def fix_file(self, file_path: str) -> bool:
        """Fix f-string syntax errors in a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            content = original_content

            # Apply all fixing strategies
            content = self.fix_simple_multiline_fstring(content)
            content = self.fix_complex_multiline_fstring(content)
            content = self.fix_function_multiline_fstring(content)
            content = self.fix_manual_patterns(content)

            # Verify the fix worked by trying to parse
            try:
                ast.parse(content)

                # Only write if content changed and is valid
                if content != original_content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.fixed_files.append(file_path)
                    return True
                else:
                    return True  # File was already valid

            except SyntaxError as e:
                print(f"Fix failed for {file_path}: {e}")
                self.error_files.append((file_path, str(e)))
                return False

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.error_files.append((file_path, str(e)))
            return False

    def fix_all_files(self, file_list: List[str]) -> Dict[str, int]:
        """Fix f-string syntax errors in all provided files."""
        results = {"fixed": 0, "errors": 0, "skipped": 0}

        for file_path in file_list:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                results["skipped"] += 1
                continue

            print(f"Processing: {file_path}")

            if self.fix_file(file_path):
                results["fixed"] += 1
                print(f"  ✅ Fixed")
            else:
                results["errors"] += 1
                print(f"  ❌ Failed")

        return results


def extract_failing_files(failures_file: str) -> List[str]:
    """Extract file paths from black parsing failures."""
    files = []

    with open(failures_file, "r") as f:
        for line in f:
            if line.strip().startswith("error: cannot format"):
                # Extract file path - handle Windows paths with drive letters
                match = re.search(
                    r"error: cannot format ([A-Z]:[^:]+\.py):", line
                )
                if match:
                    file_path = match.group(1)
                    files.append(file_path)

    return files


def main():
    """Main execution function."""
    failures_file = "black_parsing_failures.txt"

    if not os.path.exists(failures_file):
        print(f"❌ Failures file not found: {failures_file}")
        return 1

    print("🔍 Extracting failing files...")
    failing_files = extract_failing_files(failures_file)
    print(f"Found {len(failing_files)} files with parsing failures")

    print("\n🔧 Initializing F-String Syntax Fixer...")
    fixer = FStringSyntaxFixer()

    print("\n🚀 Processing files...")
    results = fixer.fix_all_files(failing_files)

    print("\n📊 Summary:")
    print(f"  ✅ Fixed: {results['fixed']}")
    print(f"  ❌ Errors: {results['errors']}")
    print(f"  ⏭️ Skipped: {results['skipped']}")

    if fixer.error_files:
        print(f"\n❌ Files that failed to fix:")
        for file_path, error in fixer.error_files:
            print(f"  - {file_path}: {error}")

    if fixer.fixed_files:
        print(f"\n✅ Successfully fixed files:")
        for file_path in fixer.fixed_files[:10]:  # Show first 10
            print(f"  - {file_path}")
        if len(fixer.fixed_files) > 10:
            print(f"  ... and {len(fixer.fixed_files) - 10} more")

    return 0 if results["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
