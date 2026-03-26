"""Dependency helpers for the canonical FastAPI application."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.contexts.identity.application.services.authentication_service import (
    AuthenticationService,
)
from src.contexts.identity.application.services.identity_service import (
    IdentityApplicationService,
)
from src.contexts.identity.domain.repositories.user_repository import UserRepository
from src.contexts.identity.infrastructure.repositories.in_memory_user_repository import (
    InMemoryUserRepository,
)
from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.infrastructure.repositories.postgres_knowledge_repository import (
    PostgresKnowledgeRepository,
)
from src.contexts.knowledge.infrastructure.runtime import (
    create_in_memory_knowledge_service,
)
from src.contexts.knowledge.infrastructure.services.openai_embedding_service import (
    OpenAIEmbeddingService,
)
from src.contexts.knowledge.infrastructure.services.recursive_chunking_service import (
    RecursiveChunkingService,
)
from src.contexts.knowledge.infrastructure.vectorStores.chroma_knowledge_vector_store import (
    ChromaKnowledgeVectorStore,
)
from src.contexts.knowledge.infrastructure.vectorStores.chroma_vector_store import (
    ChromaVectorStore,
)
from src.shared.infrastructure.auth.jwt_utils import JWTManager
from src.shared.infrastructure.config.settings import get_settings
from src.shared.infrastructure.logging.config import get_logger

if TYPE_CHECKING:
    import asyncpg

    from src.shared.infrastructure.persistence.connection_pool import (
        DatabaseConnectionPool,
    )
else:  # pragma: no cover - exercised implicitly in environments without asyncpg
    asyncpg = Any  # type: ignore[assignment]
    DatabaseConnectionPool = Any  # type: ignore[misc,assignment]

security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)

_connection_pool: DatabaseConnectionPool | None = None
_jwt_manager: JWTManager | None = None
_user_repository: UserRepository | None = None
_authentication_service: AuthenticationService | None = None
_identity_service: IdentityApplicationService | None = None
_knowledge_service: KnowledgeApplicationService | None = None


class _LazyConnectionPoolProxy:
    """Proxy that resolves the shared connection pool only when used."""

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        pool = await get_connection_pool()
        async with pool.acquire() as connection:
            yield connection


def get_jwt_manager() -> JWTManager:
    """Get or create the shared JWT manager."""
    global _jwt_manager
    if _jwt_manager is None:
        settings = get_settings()
        _jwt_manager = JWTManager(
            secret_key=settings.security.secret_key,
            algorithm=settings.security.algorithm,
            access_token_expire_minutes=settings.security.access_token_expire_minutes,
            refresh_token_expire_days=settings.security.refresh_token_expire_days,
        )
    return _jwt_manager


def reset_jwt_manager() -> None:
    """Reset the shared JWT manager."""
    global _jwt_manager
    _jwt_manager = None


async def get_connection_pool() -> DatabaseConnectionPool:
    """Get or create the shared database connection pool."""
    global _connection_pool
    if _connection_pool is None:
        from src.shared.infrastructure.persistence.connection_pool import (
            DatabaseConnectionPool,
        )

        settings = get_settings()
        _connection_pool = DatabaseConnectionPool(
            database_url=settings.database.url,
            max_connections=settings.database.pool_size
            + settings.database.max_overflow,
        )
        await _connection_pool.initialize()
        from src.apps.api.health import set_connection_pool

        set_connection_pool(_connection_pool)
    return _connection_pool


async def close_connection_pool() -> None:
    """Close the shared database connection pool."""
    global _connection_pool
    if _connection_pool is not None:
        await _connection_pool.close()
        _connection_pool = None


@asynccontextmanager
async def get_database_session() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a transactional database session."""
    pool = await get_connection_pool()
    async with pool.acquire() as connection:
        transaction = connection.transaction()
        await transaction.start()
        try:
            yield connection
            await transaction.commit()
        except Exception:
            await transaction.rollback()
            raise


async def get_database(
    request: Request,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency that yields a database connection."""
    del request
    async with get_database_session() as session:
        yield session


class CurrentUser:
    """Authenticated user data extracted from the JWT token."""

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: list[str],
        permissions: list[str],
    ) -> None:
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        """Check whether the user has a permission."""
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """Check whether the user has a role."""
        return role in self.roles


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser | None:
    """Return the current user, or ``None`` when authentication is absent/invalid."""
    if not credentials:
        return None

    try:
        payload = get_jwt_manager().verify_access_token(credentials.credentials)
    except Exception:
        return None

    return CurrentUser(
        user_id=payload.get("sub", ""),
        username=payload.get("username", ""),
        email=payload.get("email", ""),
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    """Return the current user or raise ``401``."""
    user = await get_current_user_optional(credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permissions(
    *permissions: str,
) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Build a permission-checking dependency."""
    async def check_permissions(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        for permission in permissions:
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}",
                )
        return user

    return check_permissions


def require_roles(*roles: str) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Build a role-checking dependency."""
    async def check_roles(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        for role in roles:
            if not user.has_role(role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role}",
                )
        return user

    return check_roles


class PaginationParams:
    """Pagination query parameters."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> None:
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order in {"asc", "desc"} else "asc"
        self.offset = (self.page - 1) * self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "asc",
) -> PaginationParams:
    """Return normalized pagination parameters."""
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def get_user_repository() -> UserRepository:
    """Get or create the user repository."""
    global _user_repository
    if _user_repository is None:
        settings = get_settings()
        url = settings.database.url

        # Canonical behavior:
        # - tests always use in-memory repositories
        # - development may use in-memory when not configured for PostgreSQL
        # - non-dev environments must be explicitly configured for PostgreSQL
        if settings.is_testing:
            logger.info("user_repository_mode", mode="in_memory_testing")
            _user_repository = InMemoryUserRepository(seed_demo_user=True)
            return _user_repository

        if settings.is_development and not url.startswith("postgresql"):
            logger.info("user_repository_mode", mode="in_memory_development")
            _user_repository = InMemoryUserRepository(seed_demo_user=True)
            return _user_repository

        if not url.startswith("postgresql"):
            raise RuntimeError(
                "Unsupported database configuration: set a PostgreSQL URL "
                "(prefix 'postgresql') or run in development/testing."
            )

        try:
            from src.contexts.identity.infrastructure.repositories.postgres_user_repository import (
                PostgresUserRepository,
            )
        except ModuleNotFoundError as exc:
            if exc.name == "asyncpg":
                raise RuntimeError(
                    "PostgreSQL repositories require 'asyncpg' to be installed."
                ) from exc
            raise

        _user_repository = PostgresUserRepository(_LazyConnectionPoolProxy())
    return _user_repository


def _resolve_authentication_service() -> AuthenticationService:
    """Resolve the shared authentication service instance."""
    global _authentication_service
    if _authentication_service is None:
        _authentication_service = AuthenticationService(
            get_user_repository(),
            get_jwt_manager(),
        )
    return _authentication_service


def get_authentication_service() -> AuthenticationService:
    """Get the shared authentication service."""
    return _resolve_authentication_service()


def _resolve_identity_service() -> IdentityApplicationService:
    """Resolve the shared identity application service instance."""
    global _identity_service
    if _identity_service is None:
        _identity_service = IdentityApplicationService(
            get_user_repository(),
            _resolve_authentication_service(),
        )
    return _identity_service


def get_identity_service() -> IdentityApplicationService:
    """Get the shared identity application service."""
    return _resolve_identity_service()


async def get_knowledge_service() -> KnowledgeApplicationService:
    """Get the shared knowledge application service."""
    global _knowledge_service
    if _knowledge_service is None:
        settings = get_settings()

        if settings.is_testing or settings.is_development:
            _knowledge_service = create_in_memory_knowledge_service(settings)
            return _knowledge_service

        if not settings.llm.api_key:
            raise RuntimeError(
                "LLM API key is required for knowledge services in staging/production"
            )

        pool = await get_connection_pool()
        chroma_store = ChromaVectorStore(
            host=settings.vector_store.host,
            port=settings.vector_store.port,
        )
        _knowledge_service = KnowledgeApplicationService(
            knowledge_repo=PostgresKnowledgeRepository(pool.pool),
            vector_store=ChromaKnowledgeVectorStore(chroma_store),
            embedding_service=OpenAIEmbeddingService(
                api_key=settings.llm.api_key,
                model="text-embedding-3-small",
            ),
            chunking_service=RecursiveChunkingService(
                chunk_size=settings.knowledge.chunk_size,
                chunk_overlap=settings.knowledge.chunk_overlap,
            ),
        )
    return _knowledge_service


def reset_identity_dependencies() -> None:
    """Reset identity-related dependency singletons for tests."""
    global _connection_pool, _jwt_manager, _user_repository
    global _authentication_service, _identity_service
    global _knowledge_service
    _connection_pool = None
    _jwt_manager = None
    _user_repository = None
    _authentication_service = None
    _identity_service = None
    _knowledge_service = None


def reset_knowledge_service() -> None:
    """Reset the shared knowledge application service."""
    global _knowledge_service
    _knowledge_service = None


__all__ = [
    "CurrentUser",
    "PaginationParams",
    "close_connection_pool",
    "get_authentication_service",
    "get_connection_pool",
    "get_current_user",
    "get_current_user_optional",
    "get_database",
    "get_database_session",
    "get_identity_service",
    "get_knowledge_service",
    "get_jwt_manager",
    "get_pagination",
    "get_user_repository",
    "require_permissions",
    "require_roles",
    "reset_identity_dependencies",
    "reset_knowledge_service",
    "reset_jwt_manager",
    "security",
]
