#!/usr/bin/env python3
"""
Comprehensive f-string fix for all remaining issues.
"""

import os
import re
import ast


def find_multiline_fstrings(content):
    """Find all multiline f-strings in content."""
    lines = content.split("\n")
    issues = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if 'f"' in line and "{" in line:
            # Check if this line has unclosed braces
            open_braces = line.count("{")
            close_braces = line.count("}")

            if open_braces > close_braces:
                # Found potential multiline f-string
                brace_count = open_braces - close_braces
                fstring_lines = [line]
                start_line = i

                # Collect following lines until braces balance
                j = i + 1
                while j < len(lines) and brace_count > 0:
                    next_line = lines[j]
                    fstring_lines.append(next_line)
                    brace_count += next_line.count("{") - next_line.count("}")
                    j += 1

                if brace_count == 0:
                    issues.append(
                        {
                            "start_line": start_line,
                            "end_line": j - 1,
                            "lines": fstring_lines,
                        }
                    )
                    i = j
                    continue
        i += 1

    return issues


def fix_multiline_fstring(lines_list):
    """Fix a multiline f-string by combining it into a single line."""
    combined = ""

    for line in lines_list:
        stripped = line.strip()
        if stripped:
            combined += stripped + " "

    # Clean up the combined line
    combined = combined.strip()
    combined = re.sub(r"\s+", " ", combined)
    combined = re.sub(r"\{\s+", "{", combined)
    combined = re.sub(r"\s+\}", "}", combined)

    return combined


def fix_file(file_path):
    """Fix all f-string issues in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")

        # Find all multiline f-strings
        issues = find_multiline_fstrings(content)

        if not issues:
            return True  # No issues found

        # Fix issues from bottom to top to maintain line numbers
        for issue in reversed(issues):
            start_line = issue["start_line"]
            end_line = issue["end_line"]
            fstring_lines = issue["lines"]

            # Create fixed line
            fixed_line = fix_multiline_fstring(fstring_lines)

            # Get the indentation from the first line
            first_line = fstring_lines[0]
            indent = len(first_line) - len(first_line.lstrip())
            indented_fixed = " " * indent + fixed_line.lstrip()

            # Replace the multiline f-string with single line
            lines = (
                lines[:start_line] + [indented_fixed] + lines[end_line + 1 :]
            )

        content = "\n".join(lines)

        # Verify the fix works
        try:
            ast.parse(content)

            # Write the fixed content
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            else:
                return True  # No changes needed

        except SyntaxError as e:
            print(f"  Fix verification failed: {e}")
            return False

    except Exception as e:
        print(f"  Error processing file: {e}")
        return False


def main():
    """Fix all remaining f-string issues."""

    # Files that still have issues based on black output
    problematic_files = [
        "src/agent_lifecycle_manager.py",
        "src/agents/persona_agent/world_interpretation/world_interpreter.py",
        "src/agents/persona_agent/world_interpretation/memory_manager.py",
        "src/agents/persona_agent/decision_engine/goal_manager.py",
    ]

    fixed_count = 0
    failed_count = 0

    for file_path in problematic_files:
        full_path = os.path.join("D:\\Code\\Novel-Engine", file_path)
        if not os.path.exists(full_path):
            continue

        print(f"Fixing {file_path}...")

        if fix_file(full_path):
            print(f"  ✅ Fixed")
            fixed_count += 1
        else:
            print(f"  ❌ Failed")
            failed_count += 1

    print(f"\nResults: {fixed_count} fixed, {failed_count} failed")
    return failed_count


if __name__ == "__main__":
    exit(main())
