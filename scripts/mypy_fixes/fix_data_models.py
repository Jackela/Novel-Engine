#!/usr/bin/env python3
"""Fix type annotations in data_models.py"""

from pathlib import Path

filepath = Path("/mnt/d/Code/Novel-Engine/src/core/data_models.py")
content = filepath.read_text()

# Fix Character function signature
old_character = '''def Character(
    name=None, background=None, personality=None, skills=None, equipment=None, **kwargs
) -> None:'''

new_character = '''def Character(
    name: Optional[str] = None,
    background: Optional[str] = None,
    personality: Optional[str] = None,
    skills: Optional[List[str]] = None,
    equipment: Optional[List[str]] = None,
    **kwargs: Any
) -> Any:'''

content = content.replace(old_character, new_character)

# Fix ActionResult function signature
old_action = '''def ActionResult(
    success=True, description="", consequences=None, world_state_changes=None, **kwargs
) -> None:'''

new_action = '''def ActionResult(
    success: bool = True,
    description: str = "",
    consequences: Optional[List[Any]] = None,
    world_state_changes: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> Any:'''

content = content.replace(old_action, new_action)

# Fix FlexibleWorldState.__init__
old_init = '''    def __init__(
        self,
        current_location=None,
        time_period=None,
        weather=None,
        active_events=None,
        environmental_factors=None,
        **kwargs,
    ) -> None:'''

new_init = '''    def __init__(
        self,
        current_location: Optional[str] = None,
        time_period: Optional[str] = None,
        weather: Optional[str] = None,
        active_events: Optional[List[Any]] = None,
        environmental_factors: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:'''

content = content.replace(old_init, new_init)

filepath.write_text(content)
print("Fixed data_models.py")
