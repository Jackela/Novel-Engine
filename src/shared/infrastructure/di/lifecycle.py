"""Lifecycle management for DI container.

This module provides utilities for managing the container lifecycle,
including startup initialization and graceful shutdown.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from src.shared.infrastructure.di.container import ApplicationContainer


@asynccontextmanager
async def container_lifespan(
    container: ApplicationContainer | None = None,
) -> AsyncGenerator[ApplicationContainer, None]:
    """Manage container lifecycle.

    This context manager handles:
    - Startup: Initialize all singletons (database pool, etc.)
    - Shutdown: Gracefully close all resources

    Args:
        container: Optional container instance. If None, uses global container.

    Yields:
        The initialized container instance.

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>>
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        >>>     async with container_lifespan() as container:
        >>>         app.state.container = container
        >>>         yield
        >>>
        >>> app = FastAPI(lifespan=lifespan)
    """
    from src.shared.infrastructure.di.providers import get_container

    if container is None:
        container = get_container()

    # Startup: Initialize all singletons
    try:
        # Initialize database pool
        db_pool = container.core.db_pool()
        await db_pool.initialize()

        # Initialize Honcho client (lazy initialization happens on first use)
        _ = container.core.honcho_client()

        # Initialize JWT manager
        _ = container.core.jwt_manager()

        yield container

    finally:
        # Shutdown: Close all resources
        try:
            db_pool = container.core.db_pool()
            await db_pool.close()
        except Exception:
            # Log error but don't raise during shutdown
            pass


async def initialize_container(
    container: ApplicationContainer | None = None,
) -> ApplicationContainer:
    """Initialize container and all its singletons.

    This function initializes all singleton services in the container.
    Call this during application startup.

    Args:
        container: Optional container instance. If None, uses global container.

    Returns:
        The initialized container instance.

    Example:
        >>> container = await initialize_container()
        >>> # Application is ready to use
    """
    from src.shared.infrastructure.di.providers import get_container

    if container is None:
        container = get_container()

    # Initialize database pool
    db_pool = container.core.db_pool()
    await db_pool.initialize()

    return container


async def shutdown_container(container: ApplicationContainer | None = None) -> None:
    """Shutdown container and release all resources.

    This function gracefully closes all resources managed by the container.
    Call this during application shutdown.

    Args:
        container: Optional container instance. If None, uses global container.

    Example:
        >>> await shutdown_container()
        >>> # All resources have been released
    """
    from src.shared.infrastructure.di.providers import get_container

    if container is None:
        container = get_container()

    try:
        # Close database pool
        db_pool = container.core.db_pool()
        await db_pool.close()
    except Exception:
        # Log error but don't raise during shutdown
        pass


def setup_fastapi_lifespan(app: Any) -> Any:
    """Set up FastAPI lifespan events for container management.

    Args:
        app: FastAPI application instance.

    Returns:
        The configured lifespan context manager.

    Example:
        >>> from fastapi import FastAPI
        >>> from src.shared.infrastructure.di.lifecycle import setup_fastapi_lifespan
        >>>
        >>> app = FastAPI()
        >>> lifespan = setup_fastapi_lifespan(app)
        >>> app.router.lifespan_context = lifespan
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: Any) -> AsyncGenerator[None, None]:
        async with container_lifespan():
            yield

    return lifespan
