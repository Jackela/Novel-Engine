#!/usr/bin/env python3
"""
Script to update import statements after file reorganization.
Updates imports for files moved from root to src/ subdirectories.
"""

import re
from pathlib import Path

# Mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # Agents
    r"from director_agent import": "from src.agents.director_agent_integrated import",
    r"import director_agent": "import src.agents.director_agent as director_agent",
    r"from director_agent_integrated import": "from src.agents.director_agent_integrated import",
    r"import director_agent_integrated": "import src.agents.director_agent_integrated as director_agent_integrated",
    r"from chronicler_agent import": "from src.agents.chronicler_agent import",
    r"import chronicler_agent": "import src.agents.chronicler_agent as chronicler_agent",
    # Orchestrators
    r"from emergent_narrative_orchestrator import": "from src.orchestrators.emergent_narrative_orchestrator import",
    r"import emergent_narrative_orchestrator": "import src.orchestrators.emergent_narrative_orchestrator as emergent_narrative_orchestrator",
    r"from enhanced_multi_agent_bridge import": "from src.orchestrators.enhanced_multi_agent_bridge import",
    r"import enhanced_multi_agent_bridge": "import src.orchestrators.enhanced_multi_agent_bridge as enhanced_multi_agent_bridge",
    r"from enhanced_simulation_orchestrator import": "from src.orchestrators.enhanced_simulation_orchestrator import",
    r"import enhanced_simulation_orchestrator": "import src.orchestrators.enhanced_simulation_orchestrator as enhanced_simulation_orchestrator",
    r"from enterprise_multi_agent_orchestrator import": "from src.orchestrators.enterprise_multi_agent_orchestrator import",
    r"import enterprise_multi_agent_orchestrator": "import src.orchestrators.enterprise_multi_agent_orchestrator as enterprise_multi_agent_orchestrator",
    r"from parallel_agent_coordinator import": "from src.orchestrators.parallel_agent_coordinator import",
    r"import parallel_agent_coordinator": "import src.orchestrators.parallel_agent_coordinator as parallel_agent_coordinator",
    # Config
    r"from character_factory import": "from src.config.character_factory import",
    r"import character_factory": "import src.config.character_factory as character_factory",
    # Security
    r"from database_security import": "from src.security.database_security import",
    r"import database_security": "import src.security.database_security as database_security",
    r"from security_middleware import": "from src.security.security_middleware import",
    r"import security_middleware": "import src.security.security_middleware as security_middleware",
    r"from production_security_implementation import": "from src.security.production_security_implementation import",
    r"import production_security_implementation": "import src.security.production_security_implementation as production_security_implementation",
    # Performance
    r"from high_performance_concurrent_processor import": "from src.performance.high_performance_concurrent_processor import",
    r"import high_performance_concurrent_processor": "import src.performance.high_performance_concurrent_processor as high_performance_concurrent_processor",
    r"from production_performance_engine import": "from src.performance.production_performance_engine import",
    r"import production_performance_engine": "import src.performance.production_performance_engine as production_performance_engine",
    r"from scalability_framework import": "from src.performance.scalability_framework import",
    r"import scalability_framework": "import src.performance.scalability_framework as scalability_framework",
    r"from quality_gates import": "from src.performance.quality_gates import",
    r"import quality_gates": "import src.performance.quality_gates as quality_gates",
}


def update_file_imports(file_path: Path) -> tuple[bool, int]:
    """
    Update imports in a single file.

    Returns:
        (changed, num_replacements)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        replacements = 0

        for old_pattern, new_import in IMPORT_MAPPINGS.items():
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_import, content)
                replacements += 1

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, replacements

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Update imports in all Python files."""
    base_path = Path(__file__).parent.parent
    total_files_changed = 0
    total_replacements = 0

    # Search all Python files
    for py_file in base_path.rglob("*.py"):
        # Skip this script and __pycache__
        if py_file.name == "update_imports.py" or "__pycache__" in str(py_file):
            continue

        changed, replacements = update_file_imports(py_file)
        if changed:
            total_files_changed += 1
            total_replacements += replacements
            print(
                f"✓ Updated {py_file.relative_to(base_path)} ({replacements} replacements)"
            )

    print(
        f"\n✅ Complete: {total_files_changed} files updated, {total_replacements} total replacements"
    )


if __name__ == "__main__":
    main()
