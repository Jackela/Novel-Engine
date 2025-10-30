#!/usr/bin/env python3
"""
Automated refactoring script for dynamic_equipment_system.py

Extracts monolithic file (1709 lines) into 8 focused modules:
- models.py (150 lines): Data models and enums
- processors.py (150 lines): Category-specific usage processors
- analytics.py (175 lines): Performance calculations and predictions
- maintenance.py (155 lines): Maintenance operations
- modifications.py (95 lines): Modification system
- templates.py (80 lines): Template management
- system.py (750 lines): Main orchestrator
- __init__.py (20 lines): Public API exports
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


def create_models_module(source_file: Path, target_dir: Path):
    """Create models.py with data models and enums."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Equipment data models and enums.\n",
        '"""\n',
        "\n",
        "from dataclasses import dataclass, field\n",
        "from datetime import datetime\n",
        "from enum import Enum\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
        "from src.core.data_models import EquipmentItem\n",
        "\n",
    ]

    # Extract enums and dataclasses
    content.extend(extract_lines(source_file, 41, 156))

    output_file = target_dir / "models.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_processors_module(source_file: Path, target_dir: Path):
    """Create processors.py with category-specific usage processors."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Equipment category processors for usage tracking.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from typing import Dict, Tuple\n",
        "\n",
        "from src.core.data_models import StandardResponse\n",
        "\n",
        "from .models import DynamicEquipment, EquipmentCategory\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class EquipmentProcessorRegistry:\n",
        '    """Registry for category-specific equipment processors."""\n',
        "\n",
        "    def __init__(self):\n",
        "        self.processors = {}\n",
        "\n",
        "    def register_processor(self, category: EquipmentCategory, processor_func):\n",
        '        """Register a processor for a specific category."""\n',
        "        self.processors[category] = processor_func\n",
        "\n",
        "    def get_processor(self, category: EquipmentCategory):\n",
        '        """Get the processor for a category."""\n',
        "        return self.processors.get(category)\n",
        "\n",
        "\n",
    ]

    # Extract processor methods (896-1045)
    processor_methods = extract_lines(source_file, 896, 1045)

    # Convert methods to standalone functions (remove self parameter)
    for line in processor_methods:
        # Replace method signature
        if "def _process_" in line and "(self," in line:
            line = line.replace("(self,", "(")
        content.append(line)

    output_file = target_dir / "processors.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_analytics_module(source_file: Path, target_dir: Path):
    """Create analytics.py with performance calculations."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Equipment analytics and performance calculations.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "import random\n",
        "from datetime import datetime, timedelta\n",
        "from typing import Dict, Optional, Tuple\n",
        "\n",
        "from .models import DynamicEquipment, EquipmentCategory\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class EquipmentAnalyzer:\n",
        '    """Analyzes equipment performance and predicts failures."""\n',
        "\n",
    ]

    # Extract analytics methods (1047-1220)
    analytics_methods = extract_lines(source_file, 1047, 1220)

    # Methods are already indented in original file, just remove underscore prefix
    for line in analytics_methods:
        if "def _" in line:
            line = line.replace("def _", "def ")
        content.append(line)

    output_file = target_dir / "analytics.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_maintenance_module(source_file: Path, target_dir: Path):
    """Create maintenance.py with maintenance operations."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Equipment maintenance system.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "import random\n",
        "from datetime import datetime, timedelta\n",
        "from typing import Dict, List, Tuple\n",
        "\n",
        "from .models import DynamicEquipment, EquipmentMaintenance\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class MaintenanceEngine:\n",
        '    """Handles equipment maintenance operations."""\n',
        "\n",
    ]

    # Extract maintenance methods (1263-1415)
    maintenance_methods = extract_lines(source_file, 1263, 1415)

    # Methods are already indented, just remove underscore prefix
    for line in maintenance_methods:
        if "def _" in line:
            line = line.replace("def _", "def ")
        content.append(line)

    output_file = target_dir / "maintenance.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_modifications_module(source_file: Path, target_dir: Path):
    """Create modifications.py with modification system."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Equipment modification system.\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from datetime import datetime\n",
        "from typing import Dict, Tuple\n",
        "\n",
        "from .models import DynamicEquipment, EquipmentModification\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class ModificationEngine:\n",
        '    """Handles equipment modifications and upgrades."""\n',
        "\n",
    ]

    # Extract modification methods (1417-1510)
    modification_methods = extract_lines(source_file, 1417, 1510)

    # Methods are already indented, just remove underscore prefix
    for line in modification_methods:
        if "def _" in line:
            line = line.replace("def _", "def ")
        content.append(line)

    output_file = target_dir / "modifications.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_templates_module(source_file: Path, target_dir: Path):
    """Create templates.py with template management."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Equipment template management.\n",
        '"""\n',
        "\n",
        "import json\n",
        "import logging\n",
        "from datetime import datetime, timedelta\n",
        "from pathlib import Path\n",
        "from typing import Dict, Optional\n",
        "\n",
        "from src.core.data_models import EquipmentItem\n",
        "\n",
        "from .models import DynamicEquipment, EquipmentCategory\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
        "\n",
        "class TemplateManager:\n",
        '    """Manages equipment templates and configurations."""\n',
        "\n",
        "    def __init__(self):\n",
        "        self.templates: Dict[str, EquipmentItem] = {}\n",
        "\n",
    ]

    # Extract template methods (already indented)
    content.extend(extract_lines(source_file, 1222, 1227))
    content.append("\n")
    content.extend(extract_lines(source_file, 1229, 1261))
    content.append("\n")

    # Extract load templates method (1512-1531)
    load_method = extract_lines(source_file, 1512, 1531)
    for line in load_method:
        if "def _" in line:
            line = line.replace("def _", "def ")
        content.append(line)

    output_file = target_dir / "templates.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_system_module(source_file: Path, target_dir: Path):
    """Create system.py with main orchestrator."""
    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Dynamic Equipment System - Main orchestrator.\n",
        '"""\n',
        "\n",
        "import asyncio\n",
        "import logging\n",
        "from datetime import datetime, timedelta\n",
        "from pathlib import Path\n",
        "from typing import Any, Dict, List, Optional, Tuple\n",
        "\n",
        "from src.core.data_models import (\n",
        "    EquipmentCondition,\n",
        "    EquipmentItem,\n",
        "    ErrorInfo,\n",
        "    StandardResponse,\n",
        ")\n",
        "from src.database.context_db import ContextDatabase\n",
        "\n",
        "from .analytics import EquipmentAnalyzer\n",
        "from .maintenance import MaintenanceEngine\n",
        "from .models import (\n",
        "    DynamicEquipment,\n",
        "    EquipmentCategory,\n",
        "    EquipmentMaintenance,\n",
        "    EquipmentModification,\n",
        "    EquipmentStatus,\n",
        ")\n",
        "from .modifications import ModificationEngine\n",
        "from .processors import EquipmentProcessorRegistry\n",
        "from .templates import TemplateManager\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract main class (158-892) and statistics (1533-1552)
    content.extend(extract_lines(source_file, 158, 892))
    content.append("\n")
    content.extend(extract_lines(source_file, 1533, 1552))

    output_file = target_dir / "system.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)
    logger.info(f"✅ Created {output_file} ({len(content)} lines)")


def create_init_module(target_dir: Path):
    """Create __init__.py with public API exports."""
    content = '''#!/usr/bin/env python3
"""
Dynamic Equipment System

Refactored modular equipment management system.
"""

from .models import (
    DynamicEquipment,
    EquipmentCategory,
    EquipmentMaintenance,
    EquipmentModification,
    EquipmentStatus,
)
from .system import DynamicEquipmentSystem

__all__ = [
    'DynamicEquipmentSystem',
    'EquipmentCategory',
    'EquipmentStatus',
    'EquipmentModification',
    'EquipmentMaintenance',
    'DynamicEquipment',
]
'''

    output_file = target_dir / "__init__.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"✅ Created {output_file}")


def main():
    """Main refactoring execution."""
    logger.info("🚀 Starting dynamic_equipment_system.py refactoring...")

    # Paths
    source_file = Path("src/interactions/dynamic_equipment_system.py")
    target_dir = Path("src/interactions/equipment")

    # Validate source
    if not source_file.exists():
        logger.error(f"❌ Source file not found: {source_file}")
        return

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Created directory: {target_dir}")

    # Create all modules
    create_models_module(source_file, target_dir)
    create_processors_module(source_file, target_dir)
    create_analytics_module(source_file, target_dir)
    create_maintenance_module(source_file, target_dir)
    create_modifications_module(source_file, target_dir)
    create_templates_module(source_file, target_dir)
    create_system_module(source_file, target_dir)
    create_init_module(target_dir)

    logger.info("✅ Refactoring complete!")
    logger.info(f"📊 Original: 1709 lines → Refactored: 8 focused modules")


if __name__ == "__main__":
    main()
