from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Type, TypeVar

from pydantic import BaseModel

C = TypeVar("C", bound=BaseModel)
R = TypeVar("R")


class CommandHandler(ABC, Generic[C, R]):
    """Base class for command handlers."""

    @abstractmethod
    async def handle(self, command: C) -> R:
        """Handle the command and return a result."""
        pass


class CommandBus:
    """Simple in-memory command bus."""

    def __init__(self):
        self._handlers: Dict[Type[BaseModel], CommandHandler] = {}

    def register(self, command_type: Type[C], handler: CommandHandler[C, R]):
        """Register a handler for a command type."""
        self._handlers[command_type] = handler

    async def execute(self, command: C) -> R:
        """Execute a command using its registered handler."""
        command_type = type(command)
        handler = self._handlers.get(command_type)

        if not handler:
            raise ValueError(f"No handler registered for command type: {command_type.__name__}")

        return await handler.handle(command)
