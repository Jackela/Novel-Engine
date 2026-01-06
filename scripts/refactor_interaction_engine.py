#!/usr/bin/env python3
"""
Automated refactoring script for interaction_engine.py

Extracts monolithic file (1495 lines) into 9 focused modules:
- models/interaction_models.py (100 lines): Core data models
- validators/interaction_validator.py (96 lines): Validation logic
- processors/phase_processor.py (170 lines): Phase processing
- processors/type_processors.py (170 lines): Type-specific handlers
- managers/state_manager.py (87 lines): State and memory management
- generators/content_generator.py (156 lines): Content generation
- utils/interaction_persistence.py (56 lines): Database and metrics
- interaction_engine.py (~300 lines): Core orchestration
- __init__.py: Public API exports
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def extract_lines(source_file: Path, start: int, end: int) -> list[str]:
    """Extract lines from source file (1-indexed)."""
    with open(source_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines[start - 1 : end]


def create_interaction_models(source_file: Path, target_dir: Path):
    """Create models/interaction_models.py with core data models."""
    models_dir = target_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Core interaction data models and enums.\n",
        '"""\n',
        "\n",
        "from dataclasses import dataclass, field\n",
        "from datetime import datetime\n",
        "from enum import Enum\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
    ]

    # Extract enums and dataclasses (52-151)
    content.extend(extract_lines(source_file, 52, 151))

    output_file = models_dir / "interaction_models.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")

    # Create __init__.py for models package
    init_file = models_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Interaction models package."""\n')
    logger.info(f"✅ Created {init_file}")


def create_interaction_validator(source_file: Path, target_dir: Path):
    """Create validators/interaction_validator.py with validation logic."""
    validators_dir = target_dir / "validators"
    validators_dir.mkdir(parents=True, exist_ok=True)

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Interaction context validation and prerequisite checking.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Any, Dict, List, Optional, Tuple\n",
        "\n",
        "from src.core.data_models import ErrorInfo\n",
        "\n",
        "from ..models.interaction_models import InteractionContext\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class InteractionValidator:\n",
        '    """Validates interaction contexts and prerequisites."""\n',
        "\n",
    ]

    # Extract validation methods (534-629)
    content.extend(extract_lines(source_file, 534, 629))

    output_file = validators_dir / "interaction_validator.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")

    # Create __init__.py
    init_file = validators_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Interaction validators package."""\n')
    logger.info(f"✅ Created {init_file}")


def create_phase_processor(source_file: Path, target_dir: Path):
    """Create processors/phase_processor.py with phase processing logic."""
    processors_dir = target_dir / "processors"
    processors_dir.mkdir(parents=True, exist_ok=True)

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Interaction phase processing and template initialization.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Any, Dict, List\n",
        "\n",
        "from src.core.data_models import StandardResponse\n",
        "from src.templates.dynamic_template_engine import TemplateType\n",
        "\n",
        "from ..models.interaction_models import (\n",
        "    InteractionContext,\n",
        "    InteractionPhase,\n",
        "    InteractionType,\n",
        ")\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class PhaseProcessor:\n",
        '    """Processes interaction phases and manages templates."""\n',
        "\n",
    ]

    # Extract phase processing (706-806)
    content.extend(extract_lines(source_file, 706, 806))
    content.append("\n")

    # Extract template initialization (1152-1221)
    content.extend(extract_lines(source_file, 1152, 1221))

    output_file = processors_dir / "phase_processor.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")

    # Create __init__.py
    init_file = processors_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Interaction processors package."""\n')
    logger.info(f"✅ Created {init_file}")


def create_type_processors(source_file: Path, target_dir: Path):
    """Create processors/type_processors.py with type-specific handlers."""
    processors_dir = target_dir / "processors"

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Type-specific interaction processors.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Any, Dict\n",
        "\n",
        "from src.core.data_models import StandardResponse\n",
        "\n",
        "from ..models.interaction_models import InteractionContext, InteractionOutcome\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class TypeProcessors:\n",
        '    """Handles type-specific interaction processing."""\n',
        "\n",
    ]

    # Extract type processors (810-979)
    content.extend(extract_lines(source_file, 810, 979))

    output_file = processors_dir / "type_processors.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_state_manager(source_file: Path, target_dir: Path):
    """Create managers/state_manager.py with state and memory management."""
    managers_dir = target_dir / "managers"
    managers_dir.mkdir(parents=True, exist_ok=True)

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "State and memory management for interactions.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from datetime import datetime\n",
        "from typing import Any, Dict, List\n",
        "\n",
        "from src.core.data_models import CharacterState, MemoryItem, MemoryType\n",
        "\n",
        "from ..models.interaction_models import InteractionContext, InteractionOutcome\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class StateManager:\n",
        '    """Manages state changes and memory updates."""\n',
        "\n",
    ]

    # Extract state management (981-1067)
    content.extend(extract_lines(source_file, 981, 1067))

    output_file = managers_dir / "state_manager.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")

    # Create __init__.py
    init_file = managers_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Interaction managers package."""\n')
    logger.info(f"✅ Created {init_file}")


def create_content_generator(source_file: Path, target_dir: Path):
    """Create generators/content_generator.py with content generation."""
    generators_dir = target_dir / "generators"
    generators_dir.mkdir(parents=True, exist_ok=True)

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Content generation for interactions.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
        "from src.core.data_models import CharacterState, MemoryItem\n",
        "from src.templates.context_renderer import ContextRenderer, RenderFormat\n",
        "from src.templates.dynamic_template_engine import TemplateContext, TemplateType\n",
        "\n",
        "from ..models.interaction_models import InteractionContext, InteractionType\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class ContentGenerator:\n",
        '    """Generates interaction content and context."""\n',
        "\n",
        "    def __init__(self, context_renderer: Optional[ContextRenderer] = None):\n",
        "        self.context_renderer = context_renderer\n",
        "\n",
    ]

    # Extract context generation (631-704)
    content.extend(extract_lines(source_file, 631, 704))
    content.append("\n")

    # Extract content generation (1069-1150)
    content.extend(extract_lines(source_file, 1069, 1150))

    output_file = generators_dir / "content_generator.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")

    # Create __init__.py
    init_file = generators_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Interaction generators package."""\n')
    logger.info(f"✅ Created {init_file}")


def create_interaction_persistence(source_file: Path, target_dir: Path):
    """Create utils/interaction_persistence.py with database and metrics."""
    utils_dir = target_dir / "utils"
    utils_dir.mkdir(parents=True, exist_ok=True)

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Interaction persistence and metrics tracking.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from datetime import datetime\n",
        "from typing import Any, Dict\n",
        "\n",
        "from src.database.context_db import ContextDatabase\n",
        "\n",
        "from ..models.interaction_models import InteractionOutcome\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class InteractionPersistence:\n",
        '    """Handles interaction storage and metrics."""\n',
        "\n",
        "    def __init__(self, db: ContextDatabase):\n",
        "        self.db = db\n",
        "\n",
    ]

    # Extract persistence (1223-1278)
    content.extend(extract_lines(source_file, 1223, 1278))

    output_file = utils_dir / "interaction_persistence.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")

    # Create __init__.py
    init_file = utils_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Interaction utilities package."""\n')
    logger.info(f"✅ Created {init_file}")


def create_engine_module(source_file: Path, target_dir: Path):
    """Create interaction_engine.py with core orchestration."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Interaction Engine - Core orchestration.\n",
        '"""\n',
        "\n",
        "import asyncio\n",
        "import logging\n",
        "from pathlib import Path\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
        "from src.core.data_models import CharacterState, ErrorInfo, StandardResponse\n",
        "from src.database.context_db import ContextDatabase\n",
        "from src.memory.layered_memory import LayeredMemorySystem\n",
        "from src.templates.character import CharacterTemplateManager\n",
        "from src.templates.context_renderer import ContextRenderer\n",
        "from src.templates.dynamic_template_engine import DynamicTemplateEngine\n",
        "\n",
        "from .generators.content_generator import ContentGenerator\n",
        "from .managers.state_manager import StateManager\n",
        "from .models.interaction_models import (\n",
        "    InteractionContext,\n",
        "    InteractionOutcome,\n",
        "    InteractionPriority,\n",
        "    InteractionType,\n",
        ")\n",
        "from .processors.phase_processor import PhaseProcessor\n",
        "from .processors.type_processors import TypeProcessors\n",
        "from .utils.interaction_persistence import InteractionPersistence\n",
        "from .validators.interaction_validator import InteractionValidator\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract main class and methods (153-532, 1280-1336)
    content.extend(extract_lines(source_file, 153, 532))
    content.append("\n")
    content.extend(extract_lines(source_file, 1280, 1336))

    output_file = target_dir / "interaction_engine.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_init_module(target_dir: Path):
    """Create __init__.py with public API exports."""
    content = '''#!/usr/bin/env python3
"""
Interaction Engine System

Modern modular interaction processing system.
"""

from .interaction_engine import InteractionEngine
from .models.interaction_models import (
    InteractionContext,
    InteractionOutcome,
    InteractionPhase,
    InteractionPriority,
    InteractionType,
)

__all__ = [
    'InteractionEngine',
    'InteractionType',
    'InteractionPriority',
    'InteractionContext',
    'InteractionPhase',
    'InteractionOutcome',
]
'''

    output_file = target_dir / "__init__.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"✅ Created {output_file}")


def main():
    """Main refactoring execution."""
    logger.info("🚀 Starting interaction_engine.py refactoring...")

    # Paths
    source_file = Path("src/interactions/interaction_engine.py")
    target_dir = Path("src/interactions/engine")

    # Validate source
    if not source_file.exists():
        logger.error(f"❌ Source file not found: {source_file}")
        return

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Created directory: {target_dir}")

    # Create all modules
    create_interaction_models(source_file, target_dir)
    create_interaction_validator(source_file, target_dir)
    create_phase_processor(source_file, target_dir)
    create_type_processors(source_file, target_dir)
    create_state_manager(source_file, target_dir)
    create_content_generator(source_file, target_dir)
    create_interaction_persistence(source_file, target_dir)
    create_engine_module(source_file, target_dir)
    create_init_module(target_dir)

    logger.info("✅ Refactoring complete!")
    logger.info("📊 Original: 1495 lines → Refactored: 9 focused modules")


if __name__ == "__main__":
    main()
