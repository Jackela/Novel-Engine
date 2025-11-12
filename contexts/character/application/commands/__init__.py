#!/usr/bin/env python3
"""
Character Application Commands

This package contains command objects and handlers for the Character
bounded context. Commands represent user intentions to modify character
state and are processed by their corresponding handlers.

Commands follow the Command pattern and include:
- CreateCharacterCommand: Create a new character
- UpdateCharacterStatsCommand: Update character statistics
- UpdateCharacterSkillCommand: Update character skill proficiency
- LevelUpCharacterCommand: Level up a character
- DeleteCharacterCommand: Delete a character
- HealCharacterCommand: Heal a character
- DamageCharacterCommand: Apply damage to a character

Each command has validation logic and is processed by a dedicated handler
that coordinates with the domain layer to execute the requested operation.
"""

from .character_command_handlers import (
    CharacterCommandHandlerRegistry,
    CreateCharacterCommandHandler,
    DamageCharacterCommandHandler,
    DeleteCharacterCommandHandler,
    HealCharacterCommandHandler,
    LevelUpCharacterCommandHandler,
    UpdateCharacterSkillCommandHandler,
    UpdateCharacterStatsCommandHandler,
)
from .character_commands import (
    CreateCharacterCommand,
    DamageCharacterCommand,
    DeleteCharacterCommand,
    HealCharacterCommand,
    LevelUpCharacterCommand,
    UpdateCharacterSkillCommand,
    UpdateCharacterStatsCommand,
)

__all__ = [
    # Commands
    "CreateCharacterCommand",
    "UpdateCharacterStatsCommand",
    "UpdateCharacterSkillCommand",
    "LevelUpCharacterCommand",
    "DeleteCharacterCommand",
    "HealCharacterCommand",
    "DamageCharacterCommand",
    # Command Handlers
    "CreateCharacterCommandHandler",
    "UpdateCharacterStatsCommandHandler",
    "UpdateCharacterSkillCommandHandler",
    "LevelUpCharacterCommandHandler",
    "DeleteCharacterCommandHandler",
    "HealCharacterCommandHandler",
    "DamageCharacterCommandHandler",
    "CharacterCommandHandlerRegistry",
]
