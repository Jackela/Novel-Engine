#!/usr/bin/env python3
"""
Automated refactoring script for character_template_manager.py

Extracts monolithic file (1592 lines) into 11 focused modules:
- persona_models.py (87 lines): Data models and enums
- archetype_config.py (150 lines): Archetype configurations
- content_analyzer.py (147 lines): Content analysis and detection
- template_processor.py (103 lines): Template generation and processing
- speech_adapter.py (104 lines): Speech and format adaptation
- persona_persistence.py (70 lines): Persona file I/O
- learning_system.py (57 lines): Usage learning and optimization
- template_selector.py (53 lines): Template selection logic
- context_enhancer.py (155 lines): Context enhancement
- character_template_manager.py (400 lines): Core orchestration
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


def create_persona_models_module(source_file: Path, target_dir: Path):
    """Create persona_models.py with data models and enums."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Character persona data models and enums.\n",
        '"""\n',
        "\n",
        "from dataclasses import dataclass, field\n",
        "from datetime import datetime\n",
        "from enum import Enum\n",
        "from typing import Dict, List, Optional\n",
        "\n",
        "from src.templates.dynamic_template_engine import TemplateMetadata, TemplateType\n",
        "\n",
    ]

    # Extract models (lines 50-137)
    content.extend(extract_lines(source_file, 50, 137))

    output_file = target_dir / "persona_models.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_archetype_config_module(source_file: Path, target_dir: Path):
    """Create archetype_config.py with archetype configurations."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Character archetype configurations and preferences.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Dict, List\n",
        "\n",
        "from src.templates.context_renderer import RenderFormat, RenderingConstraints\n",
        "\n",
        "from .persona_models import CharacterArchetype, CharacterPersona\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class ArchetypeConfiguration:\n",
        '    """Manages archetype-specific configurations and preferences."""\n',
        "\n",
    ]

    # Extract archetype initialization (930-1003)
    content.extend(extract_lines(source_file, 930, 1003))

    # Extract format preferences (738-779)
    content.append("\n")
    content.extend(extract_lines(source_file, 738, 779))

    # Extract constraints (788-823)
    content.append("\n")
    content.extend(extract_lines(source_file, 788, 823))

    output_file = target_dir / "archetype_config.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_content_analyzer_module(source_file: Path, target_dir: Path):
    """Create content_analyzer.py with content analysis."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Content analysis and archetype detection.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Dict, List, Optional, Set, Tuple\n",
        "\n",
        "from src.templates.dynamic_template_engine import TemplateType\n",
        "\n",
        "from .persona_models import CharacterArchetype, CharacterPersona\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class ContentAnalyzer:\n",
        '    """Analyzes content to detect archetypes and extract traits."""\n',
        "\n",
    ]

    # Extract analysis methods (1145-1291)
    content.extend(extract_lines(source_file, 1145, 1291))

    output_file = target_dir / "content_analyzer.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_template_processor_module(source_file: Path, target_dir: Path):
    """Create template_processor.py with template processing."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Template generation and processing.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "import re\n",
        "from typing import Any, Dict, List, Set\n",
        "\n",
        "from src.templates.dynamic_template_engine import TemplateContext, TemplateType\n",
        "\n",
        "from .persona_models import CharacterPersona, CharacterTemplate\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class TemplateProcessor:\n",
        '    """Processes and generates character-specific templates."""\n',
        "\n",
    ]

    # Extract processing methods (1042-1144)
    content.extend(extract_lines(source_file, 1042, 1144))

    output_file = target_dir / "template_processor.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_speech_adapter_module(source_file: Path, target_dir: Path):
    """Create speech_adapter.py with speech adaptation."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Speech and format adaptation for personas.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "import re\n",
        "from typing import Dict\n",
        "\n",
        "from src.templates.context_renderer import RenderFormat\n",
        "\n",
        "from .persona_models import CharacterPersona\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class SpeechAdapter:\n",
        '    """Adapts speech patterns and formatting for personas."""\n',
        "\n",
    ]

    # Extract speech adaptation methods (825-928)
    content.extend(extract_lines(source_file, 825, 928))

    output_file = target_dir / "speech_adapter.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_persona_persistence_module(source_file: Path, target_dir: Path):
    """Create persona_persistence.py with file I/O."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Persona persistence and file I/O.\n",
        '"""\n',
        "\n",
        "import json\n",
        "import logging\n",
        "from pathlib import Path\n",
        "from typing import Dict, List\n",
        "\n",
        "from .persona_models import CharacterArchetype, CharacterPersona\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class PersonaPersistence:\n",
        '    """Handles persona file persistence and discovery."""\n',
        "\n",
        "    def __init__(self, personas_dir: Path):\n",
        "        self.personas_dir = personas_dir\n",
        "\n",
    ]

    # Extract persistence methods (1292-1361)
    content.extend(extract_lines(source_file, 1292, 1361))

    output_file = target_dir / "persona_persistence.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_learning_system_module(source_file: Path, target_dir: Path):
    """Create learning_system.py with learning logic."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Usage learning and optimization system.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from datetime import datetime\n",
        "from typing import Any, Dict\n",
        "\n",
        "from src.templates.context_renderer import RenderFormat\n",
        "from src.templates.dynamic_template_engine import TemplateContext\n",
        "\n",
        "from .persona_models import CharacterContextProfile\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class LearningSystem:\n",
        '    """Learns from usage patterns and optimizes template selection."""\n',
        "\n",
    ]

    # Extract learning methods (1362-1418)
    content.extend(extract_lines(source_file, 1362, 1418))

    output_file = target_dir / "learning_system.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_template_selector_module(source_file: Path, target_dir: Path):
    """Create template_selector.py with selection logic."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Template selection logic.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Optional\n",
        "\n",
        "from src.templates.dynamic_template_engine import TemplateContext, TemplateType\n",
        "\n",
        "from .persona_models import CharacterContextProfile, CharacterTemplate\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class TemplateSelector:\n",
        '    """Selects optimal templates based on context and persona."""\n',
        "\n",
    ]

    # Extract selection method (673-725)
    content.extend(extract_lines(source_file, 673, 725))

    output_file = target_dir / "template_selector.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_context_enhancer_module(source_file: Path, target_dir: Path):
    """Create context_enhancer.py with context enhancement."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Context enhancement for persona-specific rendering.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
        "from src.memory.layered_memory import LayeredMemorySystem\n",
        "from src.templates.context_renderer import RenderFormat, RenderingConstraints\n",
        "from src.templates.dynamic_template_engine import TemplateContext\n",
        "\n",
        "from .persona_models import CharacterPersona\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class ContextEnhancer:\n",
        '    """Enhances rendering context with persona-specific adaptations."""\n',
        "\n",
        "    def __init__(self, memory_system: Optional[LayeredMemorySystem] = None):\n",
        "        self.memory_system = memory_system\n",
        "\n",
    ]

    # Extract enhancement methods (625-779)
    content.extend(extract_lines(source_file, 625, 779))

    output_file = target_dir / "context_enhancer.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_manager_module(source_file: Path, target_dir: Path):
    """Create character_template_manager.py with core orchestration."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Character Template Manager - Core orchestration.\n",
        '"""\n',
        "\n",
        "import asyncio\n",
        "import logging\n",
        "from pathlib import Path\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
        "from src.core.data_models import ErrorInfo, MemoryItem, StandardResponse\n",
        "from src.memory.layered_memory import LayeredMemorySystem\n",
        "from src.templates.context_renderer import ContextRenderer, RenderFormat\n",
        "from src.templates.dynamic_template_engine import (\n",
        "    DynamicTemplateEngine,\n",
        "    TemplateContext,\n",
        "    TemplateType,\n",
        ")\n",
        "\n",
        "from .archetype_config import ArchetypeConfiguration\n",
        "from .content_analyzer import ContentAnalyzer\n",
        "from .context_enhancer import ContextEnhancer\n",
        "from .learning_system import LearningSystem\n",
        "from .persona_models import (\n",
        "    CharacterArchetype,\n",
        "    CharacterContextProfile,\n",
        "    CharacterPersona,\n",
        "    CharacterTemplate,\n",
        ")\n",
        "from .persona_persistence import PersonaPersistence\n",
        "from .speech_adapter import SpeechAdapter\n",
        "from .template_processor import TemplateProcessor\n",
        "from .template_selector import TemplateSelector\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract main class definition and __init__ (139-200)
    content.extend(extract_lines(source_file, 139, 200))

    # Extract public API methods
    content.append("\n")
    content.extend(extract_lines(source_file, 202, 623))  # Public methods

    # Extract archetype generation (1013-1040)
    content.append("\n")
    content.extend(extract_lines(source_file, 1013, 1040))

    # Extract manager queries (1419-1458)
    content.append("\n")
    content.extend(extract_lines(source_file, 1419, 1458))

    output_file = target_dir / "character_template_manager.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_init_module(target_dir: Path):
    """Create __init__.py with public API exports."""
    content = '''#!/usr/bin/env python3
"""
Character Template Management System

Modern modular character persona and template management.
"""

from .character_template_manager import CharacterTemplateManager
from .persona_models import (
    CharacterArchetype,
    CharacterContextProfile,
    CharacterPersona,
    CharacterTemplate,
)

__all__ = [
    'CharacterTemplateManager',
    'CharacterArchetype',
    'CharacterPersona',
    'CharacterTemplate',
    'CharacterContextProfile',
]
'''

    output_file = target_dir / "__init__.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"✅ Created {output_file}")


def main():
    """Main refactoring execution."""
    logger.info("🚀 Starting character_template_manager.py refactoring...")

    # Paths
    source_file = Path("src/templates/character_template_manager.py")
    target_dir = Path("src/templates/character")

    # Validate source
    if not source_file.exists():
        logger.error(f"❌ Source file not found: {source_file}")
        return

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Created directory: {target_dir}")

    # Create all modules
    create_persona_models_module(source_file, target_dir)
    create_archetype_config_module(source_file, target_dir)
    create_content_analyzer_module(source_file, target_dir)
    create_template_processor_module(source_file, target_dir)
    create_speech_adapter_module(source_file, target_dir)
    create_persona_persistence_module(source_file, target_dir)
    create_learning_system_module(source_file, target_dir)
    create_template_selector_module(source_file, target_dir)
    create_context_enhancer_module(source_file, target_dir)
    create_manager_module(source_file, target_dir)
    create_init_module(target_dir)

    logger.info("✅ Refactoring complete!")
    logger.info(f"📊 Original: 1592 lines → Refactored: 11 focused modules")


if __name__ == "__main__":
    main()
