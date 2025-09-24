#!/usr/bin/env python3
"""
Fix remaining f-string issues that the automated tool couldn't handle.
"""

import ast
import re


def fix_file_manually(file_path, error_msg):
    """Fix specific f-string issues based on error message."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Extract line number from error message
        line_match = re.search(r"line (\d+)", error_msg)
        if not line_match:
            return False

        error_line = int(line_match.group(1))
        lines = content.split("\n")

        # Look for unclosed f-strings around the error line
        for i in range(
            max(0, error_line - 10), min(len(lines), error_line + 5)
        ):
            line = lines[i]
            if 'f"' in line and "{" in line:
                # Check if this is a multiline f-string that wasn't fixed
                if line.count("{") > line.count("}"):
                    # Find the complete f-string across multiple lines
                    fstring_lines = []
                    brace_count = 0
                    start_line = i

                    for j in range(i, min(len(lines), i + 10)):
                        current_line = lines[j]
                        fstring_lines.append(current_line)
                        brace_count += current_line.count(
                            "{"
                        ) - current_line.count("}")

                        if brace_count == 0:
                            # Found complete f-string, fix it
                            combined = " ".join(
                                line.strip() for line in fstring_lines
                            )
                            # Clean up the combined line
                            combined = re.sub(r"\s+", " ", combined)
                            combined = re.sub(r"\{\s+", "{", combined)
                            combined = re.sub(r"\s+\}", "}", combined)

                            # Replace the multiline f-string with single line
                            new_lines = (
                                lines[:start_line]
                                + [combined]
                                + lines[j + 1 :]
                            )
                            content = "\n".join(new_lines)
                            break
                    break

        # Additional fixes for specific patterns

        # Fix incomplete if/for/try blocks after f-string lines
        content = re.sub(
            r"(\s+)(if\s+[^:]+:)\s*\n\s*(\S)", r"\1\2\n\1    \3", content
        )
        content = re.sub(
            r"(\s+)(for\s+[^:]+:)\s*\n\s*(\S)", r"\1\2\n\1    \3", content
        )
        content = re.sub(
            r"(\s+)(try:)\s*\n\s*(\S)", r"\1\2\n\1    \3", content
        )
        content = re.sub(
            r"(\s+)(else:)\s*\n\s*(\S)", r"\1\2\n\1    \3", content
        )
        content = re.sub(
            r"(\s+)(elif\s+[^:]+:)\s*\n\s*(\S)", r"\1\2\n\1    \3", content
        )

        # Fix unexpected indents by normalizing whitespace
        lines = content.split("\n")
        fixed_lines = []
        for line in lines:
            if line.strip():
                # Normalize indentation but preserve relative structure
                stripped = line.lstrip()
                if stripped:
                    # Count original leading spaces
                    indent_count = len(line) - len(stripped)
                    # Ensure indent is multiple of 4
                    normalized_indent = (indent_count // 4) * 4
                    fixed_lines.append(" " * normalized_indent + stripped)
                else:
                    fixed_lines.append("")
            else:
                fixed_lines.append("")

        content = "\n".join(fixed_lines)

        # Test if the fix worked
        try:
            ast.parse(content)
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            return True  # File was already valid
        except SyntaxError:
            return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Fix the remaining problematic files."""
    remaining_files = [
        (
            "D:\\Code\\Novel-Engine\\src\\agents\\persona_agent\\world_interpretation\\world_interpreter.py",
            "expected an indented block after 'try' statement on line 316",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\agents\\persona_agent\\world_interpretation\\memory_manager.py",
            "expected an indented block after 'try' statement on line 181",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\core\\campaign_logger.py",
            "unexpected indent on line 130",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\core\\character_llm_integration.py",
            "expected an indented block after 'for' statement on line 246",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\api\\context7_integration_api.py",
            "expected an indented block after 'elif' statement on line 356",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\api\\logging_system.py",
            "expected an indented block after 'else' statement on line 416",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\agents\\persona_agent\\llm_integration\\llm_client.py",
            "unexpected indent on line 872",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\core\\error_handler.py",
            "unexpected indent on line 337",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\director_components\\turn_execution.py",
            "expected an indented block after 'if' statement on line 124",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\infrastructure\\postgresql_manager.py",
            "unexpected indent on line 75",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\core\\performance_cache.py",
            "invalid syntax on line 431",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\interactions\\equipment_system\\registry\\equipment_registry.py",
            "expected an indented block after 'if' statement on line 124",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\director_components\\world_state.py",
            "expected an indented block after 'try' statement on line 310",
        ),
        (
            "D:\\Code\\Novel-Engine\\src\\llm_service.py",
            "unexpected indent on line 453",
        ),
    ]

    fixed_count = 0
    failed_count = 0

    for file_path, error_msg in remaining_files:
        print(f"Fixing {file_path}...")
        if fix_file_manually(file_path, error_msg):
            print(f"  ✅ Fixed")
            fixed_count += 1
        else:
            print(f"  ❌ Failed")
            failed_count += 1

    print(f"\nResults: {fixed_count} fixed, {failed_count} failed")
    return failed_count


if __name__ == "__main__":
    exit(main())
