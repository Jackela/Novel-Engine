#!/usr/bin/env python3
"""
Director Base Components
========================

Base interfaces and types for director components.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class ComponentInitializer(Protocol):
    """Protocol for components that need initialization."""

    async def initialize(self) -> bool:
        """Initialize the component."""
        ...

    async def cleanup(self) -> None:
        """Cleanup component resources."""
        ...


@dataclass
class ComponentStatus:
    """Status information for a component."""

    name: str
    initialized: bool
    last_activity: Optional[datetime]
    error_count: int
    status_message: str


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
