#!/usr/bin/env python3
"""
Script to add type hints to emergent_narrative.py systematically.
"""

import re
from pathlib import Path


def add_type_hints():
    file_path = Path("src/core/narrative/emergent_narrative.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Define replacements (method signatures that need type hints)
    replacements = [
        (
            r"async def _analyze_and_add_causal_relations\(self, event_node: CausalNode\):",
            "async def _analyze_and_add_causal_relations(self, event_node: CausalNode) -> None:",
        ),
        (
            r"async def generate_story_summary\(\s*self,\s*time_range: Tuple\[datetime, datetime\] = None,\s*agent_focus: List\[str\] = None,\s*\) -> Dict\[str, Any\]:",
            "async def generate_story_summary(\n        self,\n        time_range: Optional[Tuple[datetime, datetime]] = None,\n        agent_focus: Optional[List[str]] = None,\n    ) -> Dict[str, Any]:",
        ),
        (
            r"def create_emergent_narrative_engine\(llm_service=None\) -> EmergentNarrativeEngine:",
            "def create_emergent_narrative_engine(llm_service: Optional[LLMService] = None) -> EmergentNarrativeEngine:",
        ),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Type hints added successfully to emergent_narrative.py")


if __name__ == "__main__":
    add_type_hints()
