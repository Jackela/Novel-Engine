#!/usr/bin/env python3
"""
Script to add type hints to character_interaction_processor.py systematically.
"""

import re
from pathlib import Path


def add_type_hints():
    file_path = Path("src/interactions/character_interaction_processor.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Define replacements for private methods
    replacements = [
        # Private methods that return None
        (
            r"async def _create_interaction_memories\(\s*self, outcome: InteractionOutcome, participants: List\[str\]\s*\):",
            "async def _create_interaction_memories(\n        self, outcome: InteractionOutcome, participants: List[str]\n    ) -> None:",
        ),
        (
            r"async def _process_equipment_interactions\(self, outcome: InteractionOutcome\):",
            "async def _process_equipment_interactions(self, outcome: InteractionOutcome) -> None:",
        ),
        (
            r"async def _save_interaction_outcome\(self, outcome: InteractionOutcome\):",
            "async def _save_interaction_outcome(self, outcome: InteractionOutcome) -> None:",
        ),
        (
            r"async def _apply_phase_outcomes\(\s*self,\s*outcome: InteractionOutcome,\s*character_states: Dict\[str, CharacterState\],\s*relationships: Dict\[Tuple\[str, str\], RelationshipData\],\s*\):",
            "async def _apply_phase_outcomes(\n        self,\n        outcome: InteractionOutcome,\n        character_states: Dict[str, CharacterState],\n        relationships: Dict[Tuple[str, str], RelationshipData],\n    ) -> None:",
        ),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Type hints added successfully to character_interaction_processor.py")


if __name__ == "__main__":
    add_type_hints()
