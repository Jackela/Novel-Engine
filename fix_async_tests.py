#!/usr/bin/env python3
"""
Fix async test functions by adding @pytest.mark.asyncio decorators
"""

import os
import re
from pathlib import Path


def fix_async_test_file(file_path):
    """Fix a single test file with async test functions."""
    print(f"Processing: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Check if file has async def test_ functions
    if "async def test_" not in content:
        print(f"  No async test functions found")
        return False

    # Add pytest import if not present
    if "import pytest" not in content:
        # Find the best place to add the import
        import_pattern = r"(import \w+.*\n)"
        matches = list(re.finditer(import_pattern, content))

        if matches:
            # Add after the last import
            last_import = matches[-1]
            insert_pos = last_import.end()
            content = content[:insert_pos] + "import pytest\n" + content[insert_pos:]
            print(f"  Added pytest import")
        else:
            # Add at the beginning after any docstrings or comments
            lines = content.split("\n")
            insert_line = 0
            for i, line in enumerate(lines):
                if (
                    line.strip().startswith('"""')
                    or line.strip().startswith("'''")
                    or line.strip().startswith("#")
                    or line.strip() == ""
                ):
                    continue
                else:
                    insert_line = i
                    break

            lines.insert(insert_line, "import pytest")
            content = "\n".join(lines)
            print(f"  Added pytest import at line {insert_line}")

    # Add @pytest.mark.asyncio decorator to async test functions
    # Pattern to match async test functions without the decorator
    pattern = r"(?<!@pytest\.mark\.asyncio\n)(?<!@pytest\.mark\.asyncio\r\n)^(async def test_[^(]+\([^)]*\):)$"

    def replace_func(match):
        return f"@pytest.mark.asyncio\n{match.group(1)}"

    # Apply the replacement
    new_content = re.sub(pattern, replace_func, content, flags=re.MULTILINE)

    # Count how many functions were fixed
    fixed_count = content.count("async def test_") - original_content.count(
        "@pytest.mark.asyncio"
    )

    if new_content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  Fixed {fixed_count} async test functions")
        return True
    else:
        print(f"  No changes needed")
        return False


def main():
    """Main function to fix all async test files."""
    project_root = Path(__file__).parent
    test_files = [
        "tests/integration/api/test_fixed_api.py",
        "tests/integration/bridges/test_multi_agent.py",
        "tests/integration/core/test_modular_components.py",
        "tests/integration/core/test_systems.py",
        "tests/integration/core/test_wave2_components.py",
        "tests/integration/interactions/test_simple.py",
        "tests/integration/test_character_context_integration.py",
        "tests/integration/test_e2e_turn_orchestration.py",
        "tests/performance/test_llm_performance.py",
        "tests/security/test_comprehensive_security.py",
        "tests/test_ai_intelligence_integration.py",
        "tests/test_enhanced_bridge.py",
        "tests/test_error_handler.py",
        "tests/test_logging_system.py",
        "tests/test_performance_optimizations.py",
        "tests/test_persona_core.py",
        "tests/test_quality_framework.py",
        "tests/test_security_framework.py",
        "tests/test_user_stories.py",
        "tests/unit/agents/test_director_refactored.py",
        "tests/unit/agents/test_persona_modular.py",
        "tests/unit/contexts/ai/application/test_execute_llm_service.py",
        "tests/unit/contexts/ai/domain/test_llm_provider_interface.py",
        "tests/unit/contexts/character/application/services/test_context_loader.py",
        "tests/unit/contexts/interactions/application/test_interaction_application_service.py",
    ]

    print("🚀 Starting async test function fixes...")
    print("=" * 60)

    fixed_files = 0
    total_files = 0

    for test_file in test_files:
        file_path = project_root / test_file
        if file_path.exists():
            total_files += 1
            if fix_async_test_file(file_path):
                fixed_files += 1
        else:
            print(f"File not found: {file_path}")

    print("=" * 60)
    print(f"✅ Fixed {fixed_files} out of {total_files} files")
    print("🧪 Run tests to verify the fixes!")


if __name__ == "__main__":
    main()
