#!/usr/bin/env python3
"""Fix type annotations in subjective_reality.py"""

from pathlib import Path

filepath = Path("/mnt/d/Code/Novel-Engine/src/core/subjective_reality.py")
content = filepath.read_text()

# Fix _process_recent_events - multiline signature
old = """    async def _process_recent_events(
        self, belief_model: BeliefModel, events: List[Dict]
    ):"""

new = """    async def _process_recent_events(
        self, belief_model: BeliefModel, events: List[Dict]
    ) -> None:"""

content = content.replace(old, new)

# Fix update_agent_knowledge
content = content.replace(
    "async def update_agent_knowledge(self, agent_id: str, new_information: List[Dict]):",
    "async def update_agent_knowledge(self, agent_id: str, new_information: List[Dict]) -> None:"
)

# Fix example_usage
content = content.replace(
    "async def example_usage():",
    "async def example_usage() -> None:"
)

filepath.write_text(content)
print("Fixed subjective_reality.py")
