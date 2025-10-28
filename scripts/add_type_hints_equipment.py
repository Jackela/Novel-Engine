#!/usr/bin/env python3
"""
Script to add type hints to equipment system modules.
"""

from pathlib import Path

def add_type_hints_to_system():
    file_path = Path("src/interactions/equipment/system.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add type hints to __init__
    content = content.replace(
        "    ):  # Weekly default",
        "    ) -> None:  # Weekly default"
    )
    
    # Add type hints to _load_equipment_templates
    content = content.replace(
        "    def _load_equipment_templates(self):",
        "    def _load_equipment_templates(self) -> None:"
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Type hints added successfully to equipment system.py")

if __name__ == "__main__":
    add_type_hints_to_system()
