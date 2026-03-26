"""Tests for canonical dependency helpers."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

import src.apps.api.dependencies as dependency_module
from src.apps.api.dependencies import (
    CurrentUser,
    PaginationParams,
    get_authentication_service,
    get_current_user,
    get_current_user_optional,
    get_identity_service,
    get_jwt_manager,
    get_knowledge_service,
    get_pagination,
    require_permissions,
    require_roles,
    reset_knowledge_service,
)


def test_current_user_permissions_and_roles() -> None:
    user = CurrentUser(
        user_id="user-123",
        username="tester",
        email="tester@example.com",
        roles=["admin"],
        permissions=["stories:read"],
    )
    assert user.has_role("admin") is True
    assert user.has_permission("stories:read") is True
    assert user.has_permission("stories:write") is False


def test_pagination_params_are_normalized() -> None:
    params = PaginationParams(page=0, page_size=200, sort_order="invalid")
    assert params.page == 1
    assert params.page_size == 100
    assert params.sort_order == "asc"
    assert get_pagination(page=2, page_size=5).offset == 5


@pytest.mark.asyncio
async def test_current_user_optional_returns_none_without_credentials() -> None:
    assert await get_current_user_optional(None) is None


@pytest.mark.asyncio
async def test_current_user_dependencies_accept_valid_token() -> None:
    token = get_jwt_manager().create_access_token(
        user_id="user-123",
        username="tester",
        email="tester@example.com",
        roles=["user"],
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = await get_current_user_optional(credentials)
    assert user is not None
    assert user.user_id == "user-123"

    required_user = await get_current_user(credentials)
    assert required_user.user_id == "user-123"


@pytest.mark.asyncio
async def test_current_user_dependency_rejects_missing_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(None)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_service_factories_are_synchronous_and_reusable() -> None:
    assert inspect.iscoroutinefunction(get_authentication_service) is False
    assert inspect.iscoroutinefunction(get_identity_service) is False
    assert get_authentication_service() is get_authentication_service()
    assert get_identity_service() is get_identity_service()


@pytest.mark.asyncio
async def test_knowledge_service_factory_is_async_and_reusable() -> None:
    assert inspect.iscoroutinefunction(get_knowledge_service) is True
    first = await get_knowledge_service()
    second = await get_knowledge_service()
    assert first is second


@pytest.mark.asyncio
async def test_knowledge_service_uses_contract_adapter_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeKnowledgeRepository:
        def __init__(self, pool) -> None:
            self.pool = pool

    class FakeEmbeddingService:
        def __init__(self, api_key: str, model: str) -> None:
            self.api_key = api_key
            self.model = model

    class FakeChunkingService:
        def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

    class FakeChromaStore:
        def __init__(self, host: str, port: int) -> None:
            self.host = host
            self.port = port

    class FakeKnowledgeVectorStore:
        def __init__(self, store) -> None:
            self.store = store

    fake_settings = SimpleNamespace(
        is_testing=False,
        is_development=False,
        llm=SimpleNamespace(api_key="test-api-key"),
        vector_store=SimpleNamespace(host="localhost", port=8000),
        knowledge=SimpleNamespace(chunk_size=256, chunk_overlap=32),
    )

    async def fake_get_connection_pool():
        return SimpleNamespace(pool="pool")

    reset_knowledge_service()
    monkeypatch.setattr(dependency_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(
        dependency_module,
        "get_connection_pool",
        fake_get_connection_pool,
    )
    monkeypatch.setattr(
        dependency_module,
        "PostgresKnowledgeRepository",
        FakeKnowledgeRepository,
    )
    monkeypatch.setattr(
        dependency_module,
        "OpenAIEmbeddingService",
        FakeEmbeddingService,
    )
    monkeypatch.setattr(
        dependency_module,
        "RecursiveChunkingService",
        FakeChunkingService,
    )
    monkeypatch.setattr(
        dependency_module,
        "ChromaVectorStore",
        FakeChromaStore,
    )
    monkeypatch.setattr(
        dependency_module,
        "ChromaKnowledgeVectorStore",
        FakeKnowledgeVectorStore,
    )

    service = await get_knowledge_service()

    assert isinstance(service.knowledge_repo, FakeKnowledgeRepository)
    assert isinstance(service.vector_store, FakeKnowledgeVectorStore)
    assert isinstance(service.vector_store.store, FakeChromaStore)
    assert isinstance(service.embedding, FakeEmbeddingService)
    assert isinstance(service.chunking, FakeChunkingService)


def test_permission_and_role_factories_return_async_dependencies() -> None:
    permissions_dependency = require_permissions("stories:read")
    roles_dependency = require_roles("admin")

    assert inspect.iscoroutinefunction(permissions_dependency) is True
    assert inspect.iscoroutinefunction(roles_dependency) is True


@pytest.mark.asyncio
async def test_permission_dependency_allows_authorized_user() -> None:
    dependency = require_permissions("stories:read")
    user = CurrentUser(
        user_id="user-123",
        username="tester",
        email="tester@example.com",
        roles=["user"],
        permissions=["stories:read", "stories:write"],
    )

    assert await dependency(user=user) is user


@pytest.mark.asyncio
async def test_permission_dependency_rejects_missing_permission() -> None:
    dependency = require_permissions("stories:delete")
    user = CurrentUser(
        user_id="user-123",
        username="tester",
        email="tester@example.com",
        roles=["user"],
        permissions=["stories:read"],
    )

    with pytest.raises(HTTPException) as exc_info:
        await dependency(user=user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Permission denied: stories:delete"


@pytest.mark.asyncio
async def test_role_dependency_allows_authorized_user() -> None:
    dependency = require_roles("admin")
    user = CurrentUser(
        user_id="user-123",
        username="tester",
        email="tester@example.com",
        roles=["admin", "writer"],
        permissions=[],
    )

    assert await dependency(user=user) is user


@pytest.mark.asyncio
async def test_role_dependency_rejects_missing_role() -> None:
    dependency = require_roles("admin")
    user = CurrentUser(
        user_id="user-123",
        username="tester",
        email="tester@example.com",
        roles=["writer"],
        permissions=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        await dependency(user=user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Role required: admin"
