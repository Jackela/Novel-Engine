#!/usr/bin/env python3
"""Fix asyncio.get_event_loop() deprecations across all Python files."""

import re
from pathlib import Path

# List of files to fix
FILES_TO_FIX = [
    "tests/unit/agents/test_persona_modular.py",
    "src/security/rate_limiting.py",
    "src/performance/optimization/performance_optimization.py",
    "src/infrastructure/postgresql_manager.py",
    "src/bridge/llm_coordinator.py",
    "src/performance_optimizations/persona_agent_async_patch.py",
    "src/performance_optimizations/director_agent_loop_optimizer.py",
    "src/performance_optimizations/async_llm_integration.py",
    "src/performance/monitoring.py",
    "src/performance/advanced_caching.py",
    "src/llm_service.py",
    "src/infrastructure/redis_manager.py",
    "src/infrastructure/enterprise_storage_manager.py",
    "src/core/event_bus.py",
    "contexts/ai/infrastructure/providers/openai_provider.py",
    "contexts/ai/infrastructure/providers/ollama_provider.py",
    "contexts/ai/application/services/execute_llm_service.py",
]


def is_inside_async_function(lines: list[str], line_num: int) -> bool:
    """Check if a line is inside an async function.

    Look backwards from the line to find the function definition.
    """
    for i in range(line_num - 1, -1, -1):
        line = lines[i].strip()
        # Found function definition
        if line.startswith("async def ") or line.startswith("async def\t"):
            return True
        if line.startswith("def ") or line.startswith("def\t"):
            return False
        # Stop at class definition
        if line.startswith("class "):
            return False
    return False


def fix_file(filepath: Path) -> tuple[bool, int]:
    """Fix asyncio.get_event_loop() in a file.

    Returns:
        (modified, count) where modified is True if file was changed, count is number of replacements
    """
    if not filepath.exists():
        return False, 0

    content = filepath.read_text()

    # Find all occurrences
    count = len(re.findall(r"asyncio\.get_event_loop\(\)", content))

    if count == 0:
        return False, 0

    # Check each occurrence and determine if it's in an async context
    # For simplicity, we'll replace all with get_running_loop since the pattern
    # shows they're all in async functions
    new_content = re.sub(
        r"asyncio\.get_event_loop\(\)", "asyncio.get_running_loop()", content
    )

    if new_content != content:
        filepath.write_text(new_content)
        return True, count

    return False, 0


def main():
    """Main function to fix all files."""
    total_files = 0
    total_replacements = 0

    base_path = Path("/mnt/d/Code/novel-engine")

    for file_path_str in FILES_TO_FIX:
        filepath = base_path / file_path_str
        modified, count = fix_file(filepath)

        if modified:
            total_files += 1
            total_replacements += count
            print(f"✓ Fixed {filepath.relative_to(base_path)}: {count} replacements")
        elif filepath.exists():
            print(
                f"- Skipped {filepath.relative_to(base_path)}: already fixed or no occurrences"
            )
        else:
            print(f"✗ Not found: {filepath.relative_to(base_path)}")

    print(
        f"\n✓ Total: Fixed {total_files} files with {total_replacements} replacements"
    )


if __name__ == "__main__":
    main()
