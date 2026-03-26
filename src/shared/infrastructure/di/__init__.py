"""Dependency Injection module for Novel Engine.

This module provides a professional DI container implementation
using the dependency-injector library.

Example:
    >>> from src.shared.infrastructure.di import get_container, container_lifespan
    >>>
    >>> # Initialize container
    >>> container = get_container()
    >>>
    >>> # Use container in FastAPI
    >>> from fastapi import FastAPI
    >>> app = FastAPI(lifespan=container_lifespan)
    >>>
    >>> # Resolve dependencies
    >>> auth_service = container.identity.authentication_service()
"""

from src.shared.infrastructure.di.container import (
    ApplicationContainer,
    CoreContainer,
    IdentityContainer,
    KnowledgeContainer,
    NarrativeContainer,
    WorldContainer,
)
from src.shared.infrastructure.di.lifecycle import (
    container_lifespan,
    initialize_container,
    setup_fastapi_lifespan,
    shutdown_container,
)
from src.shared.infrastructure.di.providers import (
    get_authentication_service,
    get_container,
    get_current_user,
    get_database_connection,
    get_database_pool,
    get_honcho_client,
    get_jwt_manager,
    get_user_repository,
    reset_container,
)
from src.shared.infrastructure.di.validation import (
    ValidationError,
    check_circular_dependencies,
    get_container_graph,
    print_container_tree,
    validate_container,
)

__all__ = [
    # Containers
    "ApplicationContainer",
    "CoreContainer",
    "IdentityContainer",
    "KnowledgeContainer",
    "WorldContainer",
    "NarrativeContainer",
    # Lifecycle
    "container_lifespan",
    "initialize_container",
    "shutdown_container",
    "setup_fastapi_lifespan",
    # Providers
    "get_container",
    "reset_container",
    "get_database_pool",
    "get_database_connection",
    "get_jwt_manager",
    "get_user_repository",
    "get_authentication_service",
    "get_current_user",
    "get_honcho_client",
    # Validation
    "check_circular_dependencies",
    "validate_container",
    "ValidationError",
    "get_container_graph",
    "print_container_tree",
]
