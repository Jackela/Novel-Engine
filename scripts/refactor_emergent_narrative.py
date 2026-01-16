#!/usr/bin/env python3
"""
Automated refactoring script for emergent_narrative.py

Extracts large monolithic file into focused modules:
- types.py: Shared enums and dataclasses
- causal_graph.py: CausalGraph implementation
- negotiation.py: AgentNegotiationEngine
- narrative_coherence.py: NarrativeCoherenceEngine
- emergent_narrative.py: Main orchestrator

Maintains backward compatibility through __init__.py exports.
"""

import shutil
from pathlib import Path


def extract_lines(source_file: Path, start: int, end: int) -> list[str]:
    """Extract lines from source file (1-indexed)."""
    with open(source_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines[start - 1 : end]


def create_types_module(source_file: Path, target_dir: Path):
    """Create types.py with shared enums and dataclasses."""
    print("Creating types.py...")

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Shared types for emergent narrative system.\n",
        "\n",
        "Contains enums and dataclasses used across narrative modules.\n",
        '"""\n',
        "\n",
        "from dataclasses import dataclass, field\n",
        "from datetime import datetime, timedelta\n",
        "from enum import Enum\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
        "import logging\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract enums (lines 35-66)
    content.extend(extract_lines(source_file, 35, 66))
    content.append("\n")

    # Extract dataclasses (lines 68-344)
    content.extend(extract_lines(source_file, 68, 344))

    output_file = target_dir / "types.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)

    print(f"✅ Created {output_file}")


def create_causal_graph_module(source_file: Path, target_dir: Path):
    """Create causal_graph.py with CausalGraph class."""
    print("Creating causal_graph.py...")

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Causal graph for tracking event relationships.\n",
        "\n",
        "因果关系图 - 追踪行动-结果的链式关系\n",
        '"""\n',
        "\n",
        "import logging\n",
        "from collections import defaultdict\n",
        "from datetime import datetime, timedelta\n",
        "from typing import Any, Dict, List, Tuple\n",
        "\n",
        "import networkx as nx\n",
        "\n",
        "from .types import CausalEdge, CausalNode, CausalRelationType\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract CausalGraph class (lines 129-299)
    content.extend(extract_lines(source_file, 129, 299))

    output_file = target_dir / "causal_graph.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)

    print(f"✅ Created {output_file}")


def create_negotiation_module(source_file: Path, target_dir: Path):
    """Create negotiation.py with AgentNegotiationEngine."""
    print("Creating negotiation.py...")

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Multi-agent negotiation engine.\n",
        "\n",
        "多Agent协商引擎 - 冲突解决与合作机制\n",
        '"""\n',
        "\n",
        "import json\n",
        "import logging\n",
        "import uuid\n",
        "from datetime import datetime, timedelta\n",
        "from typing import Any, Dict, List, Optional\n",
        "\n",
        "from src.core.llm_service import LLMRequest, ResponseFormat, get_llm_service\n",
        "\n",
        "from .types import (\n",
        "    NegotiationProposal,\n",
        "    NegotiationResponse,\n",
        "    NegotiationSession,\n",
        "    NegotiationStatus,\n",
        ")\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract AgentNegotiationEngine class (lines 346-761)
    content.extend(extract_lines(source_file, 346, 761))

    output_file = target_dir / "negotiation.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)

    print(f"✅ Created {output_file}")


def create_narrative_coherence_module(source_file: Path, target_dir: Path):
    """Create narrative_coherence.py with NarrativeCoherenceEngine."""
    print("Creating narrative_coherence.py...")

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Narrative coherence engine for story consistency.\n",
        "\n",
        "叙事连贯性引擎 - 智能故事整合与一致性保证\n",
        '"""\n',
        "\n",
        "import json\n",
        "import logging\n",
        "from datetime import datetime, timedelta\n",
        "from typing import Any, Callable, Dict, List, Optional\n",
        "\n",
        "from src.core.llm_service import LLMRequest, ResponseFormat, get_llm_service\n",
        "\n",
        "from .causal_graph import CausalGraph\n",
        "from .types import CausalNode\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract NarrativeCoherenceEngine class (lines 763-1293)
    content.extend(extract_lines(source_file, 763, 1293))

    output_file = target_dir / "narrative_coherence.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)

    print(f"✅ Created {output_file}")


def create_emergent_narrative_module(source_file: Path, target_dir: Path):
    """Create refactored emergent_narrative.py with EmergentNarrativeEngine."""
    print("Creating emergent_narrative.py...")

    content = [
        "#!/usr/bin/env python3\n",
        '"""\n',
        "Main emergent narrative engine orchestrating all subsystems.\n",
        "\n",
        "涌现式叙事引擎主引擎 - 通过Agent间的真实交互和因果关系图，\n",
        "自然涌现出连贯的叙事，而非预设剧本。\n",
        '"""\n',
        "\n",
        "import logging\n",
        "import uuid\n",
        "from datetime import datetime, timedelta\n",
        "from typing import Any, Dict, List, Optional, Set, Tuple\n",
        "\n",
        "from src.core.llm_service import LLMRequest, ResponseFormat, get_llm_service\n",
        "\n",
        "from .causal_graph import CausalGraph\n",
        "from .narrative_coherence import NarrativeCoherenceEngine\n",
        "from .negotiation import AgentNegotiationEngine\n",
        "from .types import CausalEdge, CausalNode, CausalRelationType, EventPriority\n",
        "\n",
        "logger = logging.getLogger(__name__)\n",
        "\n",
    ]

    # Extract EmergentNarrativeEngine class and factory (lines 1295-2041)
    content.extend(extract_lines(source_file, 1295, 2041))

    output_file = target_dir / "emergent_narrative.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(content)

    print(f"✅ Created {output_file}")


def create_init_module(target_dir: Path):
    """Create __init__.py with backward-compatible exports."""
    print("Creating __init__.py...")

    content = '''#!/usr/bin/env python3
"""
涌现式叙事系统 (Emergent Narrative System)

Backward-compatible exports maintaining original API.

Milestone 2 Implementation: CausalGraph + Multi-Agent Negotiation + Narrative Coherence
"""

# Export all types
from .types import (
    CausalEdge,
    CausalNode,
    CausalRelationType,
    EventPriority,
    NegotiationProposal,
    NegotiationResponse,
    NegotiationSession,
    NegotiationStatus,
)

# Export main classes
from .causal_graph import CausalGraph
from .emergent_narrative import EmergentNarrativeEngine, create_emergent_narrative_engine
from .narrative_coherence import NarrativeCoherenceEngine
from .negotiation import AgentNegotiationEngine

__all__ = [
    # Types
    "CausalRelationType",
    "NegotiationStatus",
    "EventPriority",
    "CausalNode",
    "CausalEdge",
    "NegotiationProposal",
    "NegotiationResponse",
    "NegotiationSession",
    # Main classes
    "CausalGraph",
    "AgentNegotiationEngine",
    "NarrativeCoherenceEngine",
    "EmergentNarrativeEngine",
    # Factory
    "create_emergent_narrative_engine",
]
'''

    output_file = target_dir / "__init__.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Created {output_file}")


def create_legacy_wrapper(source_file: Path):
    """Create backward-compatible wrapper in original location."""
    print("Creating legacy wrapper...")

    content = '''#!/usr/bin/env python3
"""
涌现式叙事系统 (Emergent Narrative System)
=======================================

⚠️  DEPRECATED: This module has been refactored into separate modules.
    Please import from src.core.narrative instead.

Backward-compatible wrapper - imports still work but please migrate to:
    from src.core.narrative import EmergentNarrativeEngine, CausalGraph, etc.

New module structure:
- src.core.narrative.types - Shared enums and dataclasses
- src.core.narrative.causal_graph - CausalGraph implementation
- src.core.narrative.negotiation - AgentNegotiationEngine
- src.core.narrative.narrative_coherence - NarrativeCoherenceEngine
- src.core.narrative.emergent_narrative - Main orchestrator
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from src.core.emergent_narrative is deprecated. "
    "Please use: from src.core.narrative import EmergentNarrativeEngine, ...",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from new location for backward compatibility
from src.core.narrative import (
    AgentNegotiationEngine,
    CausalEdge,
    CausalGraph,
    CausalNode,
    CausalRelationType,
    EmergentNarrativeEngine,
    EventPriority,
    NarrativeCoherenceEngine,
    NegotiationProposal,
    NegotiationResponse,
    NegotiationSession,
    NegotiationStatus,
    create_emergent_narrative_engine,
)

__all__ = [
    "CausalRelationType",
    "NegotiationStatus",
    "EventPriority",
    "CausalNode",
    "CausalEdge",
    "NegotiationProposal",
    "NegotiationResponse",
    "NegotiationSession",
    "CausalGraph",
    "AgentNegotiationEngine",
    "NarrativeCoherenceEngine",
    "EmergentNarrativeEngine",
    "create_emergent_narrative_engine",
]
'''

    # Backup original file
    backup_file = source_file.parent / f"{source_file.stem}_backup.py"
    shutil.copy2(source_file, backup_file)
    print(f"📦 Backed up original to {backup_file}")

    # Write new wrapper
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Created legacy wrapper at {source_file}")


def main():
    """Execute refactoring."""
    print("=" * 60)
    print("Refactoring emergent_narrative.py (2041 lines)")
    print("=" * 60)

    source_file = Path("src/core/emergent_narrative.py")
    target_dir = Path("src/core/narrative")

    if not source_file.exists():
        print(f"❌ Source file not found: {source_file}")
        return

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created directory: {target_dir}\n")

    # Extract modules
    create_types_module(source_file, target_dir)
    create_causal_graph_module(source_file, target_dir)
    create_negotiation_module(source_file, target_dir)
    create_narrative_coherence_module(source_file, target_dir)
    create_emergent_narrative_module(source_file, target_dir)
    create_init_module(target_dir)
    create_legacy_wrapper(source_file)

    print("\n" + "=" * 60)
    print("✅ Refactoring complete!")
    print("=" * 60)
    print("\nNew module structure:")
    print("  src/core/narrative/")
    print("  ├── __init__.py          (backward-compatible exports)")
    print("  ├── types.py             (~160 lines)")
    print("  ├── causal_graph.py      (~185 lines)")
    print("  ├── negotiation.py       (~430 lines)")
    print("  ├── narrative_coherence.py (~545 lines)")
    print("  └── emergent_narrative.py  (~760 lines)")
    print("\nLegacy wrapper:")
    print("  src/core/emergent_narrative.py (backward-compatible)")
    print("\nBackup:")
    print("  src/core/emergent_narrative_backup.py (original file)")


if __name__ == "__main__":
    main()

