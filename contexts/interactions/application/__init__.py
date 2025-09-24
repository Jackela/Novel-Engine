#!/usr/bin/env python3
"""
Application Package for Interaction Domain

This package contains the application layer implementation following CQRS principles,
with commands, queries, handlers, and orchestration services for the Interaction
bounded context.

Key Components:
- Commands and Command Handlers: Write operations and business logic
- Queries and Query Handlers: Read operations and data formatting
- Application Services: High-level business operations orchestration
"""

from .services.interaction_application_service import (
    InteractionApplicationService,
)

__all__ = [
    # Application Service
    "InteractionApplicationService"
]

__version__ = "1.0.0"
