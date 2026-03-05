#!/usr/bin/env python3
"""Fix type annotations in memory_leak_fixes.py"""

from pathlib import Path

filepath = Path("/mnt/d/Code/Novel-Engine/src/performance_optimizations/memory_leak_fixes.py")
content = filepath.read_text()

# Fix static method
content = content.replace(
    "def fix_persona_agent_memory_leaks(persona_agent_instance) -> Dict[str, Any]:",
    "def fix_persona_agent_memory_leaks(persona_agent_instance: Any) -> Dict[str, Any]:"
)

# Fix __init__
content = content.replace(
    "def __init__(self, persona_agent_instance) -> None:",
    "def __init__(self, persona_agent_instance: Any) -> None:"
)

# Fix _check_cleanup_needs
content = content.replace(
    "def _check_cleanup_needs(self, agent) -> None:",
    "def _check_cleanup_needs(self, agent: Any) -> None:"
)

# Fix _check_memory_alerts
content = content.replace(
    "def _check_memory_alerts(self, stats: MemoryStats, agent) -> None:",
    "def _check_memory_alerts(self, stats: MemoryStats, agent: Any) -> None:"
)

# Fix apply_memory_fixes_to_persona_agent
content = content.replace(
    "def apply_memory_fixes_to_persona_agent(persona_agent_instance) -> bool:",
    "def apply_memory_fixes_to_persona_agent(persona_agent_instance: Any) -> bool:"
)

# Fix monitor_persona_agent_memory
content = content.replace(
    "def monitor_persona_agent_memory(persona_agent_instance) -> None:",
    "def monitor_persona_agent_memory(persona_agent_instance: Any) -> None:"
)

filepath.write_text(content)
print("Fixed memory_leak_fixes.py")
