#!/usr/bin/env python3
"""
Character Application Layer

This package contains the application layer for the Character bounded context.
The application layer coordinates between the presentation layer and domain layer,
orchestrating business workflows and managing transactions.

Components:
- Commands: Represent user intentions to change character state
- Command Handlers: Execute business logic for commands
- Services: Application services that coordinate domain operations
- DTOs: Data transfer objects for external communication (future)

The application layer is responsible for:
- Orchestrating domain operations
- Managing transactions
- Enforcing application-level business rules
- Coordinating between domain and infrastructure layers
"""

from .commands.character_commands import (
    CreateCharacterCommand, UpdateCharacterStatsCommand,
    UpdateCharacterSkillCommand, LevelUpCharacterCommand,
    DeleteCharacterCommand, HealCharacterCommand, DamageCharacterCommand
)
from .commands.character_command_handlers import (
    CreateCharacterCommandHandler, UpdateCharacterStatsCommandHandler,
    UpdateCharacterSkillCommandHandler, LevelUpCharacterCommandHandler,
    DeleteCharacterCommandHandler, HealCharacterCommandHandler,
    DamageCharacterCommandHandler, CharacterCommandHandlerRegistry
)
from .services.character_application_service import CharacterApplicationService

__all__ = [
    # Commands
    "CreateCharacterCommand", "UpdateCharacterStatsCommand",
    "UpdateCharacterSkillCommand", "LevelUpCharacterCommand",
    "DeleteCharacterCommand", "HealCharacterCommand", "DamageCharacterCommand",
    
    # Command Handlers
    "CreateCharacterCommandHandler", "UpdateCharacterStatsCommandHandler",
    "UpdateCharacterSkillCommandHandler", "LevelUpCharacterCommandHandler",
    "DeleteCharacterCommandHandler", "HealCharacterCommandHandler",
    "DamageCharacterCommandHandler", "CharacterCommandHandlerRegistry",
    
    # Application Services
    "CharacterApplicationService",
]