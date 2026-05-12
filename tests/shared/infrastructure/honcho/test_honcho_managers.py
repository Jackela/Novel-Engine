"""Mocked Honcho manager behavior and error-mapping tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.shared.infrastructure.honcho import HonchoSettings
from src.shared.infrastructure.honcho.errors import HonchoClientError
from src.shared.infrastructure.honcho.message_handler import HonchoMessageHandler
from src.shared.infrastructure.honcho.session_manager import HonchoSessionManager
from src.shared.infrastructure.honcho.workspace_manager import HonchoWorkspaceManager


class _AsyncCall:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.result


class _Context:
    def to_openai(self) -> list[dict[str, Any]]:
        return [{"role": "user", "content": "hello"}]


def _classify_error(error: Exception) -> str:
    if isinstance(error, ConnectionError):
        return "CONNECTION_ERROR"
    if isinstance(error, TimeoutError):
        return "TIMEOUT_ERROR"
    if isinstance(error, HonchoClientError):
        return error.error_code
    return "UNKNOWN_ERROR"


def _workspace_manager(client: Any) -> HonchoWorkspaceManager:
    async def _get_client() -> Any:
        return client

    return HonchoWorkspaceManager(_get_client, _classify_error)


def _session_manager(client: Any) -> HonchoSessionManager:
    async def _get_client() -> Any:
        return client

    return HonchoSessionManager(_get_client, _classify_error)


def _message_handler(client: Any) -> HonchoMessageHandler:
    async def _get_client() -> Any:
        return client

    return HonchoMessageHandler(_get_client, _classify_error, HonchoSettings())


@pytest.mark.asyncio
async def test_workspace_manager_returns_existing_workspace() -> None:
    workspace = object()
    get = _AsyncCall(workspace)
    create = _AsyncCall(object())
    client = SimpleNamespace(workspaces=SimpleNamespace(get=get, create=create))

    result = await _workspace_manager(client).get_or_create_workspace("story-1")

    assert result is workspace
    assert get.calls == [(("story-1",), {})]
    assert create.calls == []


@pytest.mark.asyncio
async def test_workspace_manager_creates_missing_workspace() -> None:
    workspace = object()
    get = _AsyncCall(None)
    create = _AsyncCall(workspace)
    client = SimpleNamespace(workspaces=SimpleNamespace(get=get, create=create))

    result = await _workspace_manager(client).get_or_create_workspace("story-1")

    assert result is workspace
    assert create.calls == [
        ((), {"workspace_id": "story-1", "name": "story-1"}),
    ]


@pytest.mark.asyncio
async def test_workspace_manager_maps_get_and_create_errors() -> None:
    get_error = RuntimeError("broken get")
    client = SimpleNamespace(
        workspaces=SimpleNamespace(get=_AsyncCall(error=get_error), create=_AsyncCall())
    )

    with pytest.raises(HonchoClientError) as get_exc:
        await _workspace_manager(client).get_or_create_workspace("story-1")

    assert get_exc.value.error_code == "UNKNOWN_ERROR"
    assert get_exc.value.details is not None
    assert get_exc.value.details.operation == "get_workspace"

    create_error = TimeoutError("slow create")
    client = SimpleNamespace(
        workspaces=SimpleNamespace(get=_AsyncCall(None), create=_AsyncCall(error=create_error))
    )

    with pytest.raises(HonchoClientError) as create_exc:
        await _workspace_manager(client).get_or_create_workspace("story-1")

    assert create_exc.value.error_code == "TIMEOUT_ERROR"
    assert create_exc.value.details is not None
    assert create_exc.value.details.operation == "create_workspace"


@pytest.mark.asyncio
async def test_workspace_manager_gets_or_creates_peer() -> None:
    peer = object()
    get = _AsyncCall(None)
    create = _AsyncCall(peer)
    client = SimpleNamespace(peers=SimpleNamespace(get=get, create=create))

    result = await _workspace_manager(client).get_or_create_peer("story-1", "peer-1")

    assert result is peer
    assert get.calls == [(("story-1", "peer-1"), {})]
    assert create.calls == [
        ((), {"workspace_id": "story-1", "peer_id": "peer-1", "name": "peer-1"}),
    ]


@pytest.mark.asyncio
async def test_workspace_manager_maps_peer_errors() -> None:
    get_error = RuntimeError("peer get failed")
    client = SimpleNamespace(
        peers=SimpleNamespace(get=_AsyncCall(error=get_error), create=_AsyncCall())
    )

    with pytest.raises(HonchoClientError) as get_exc:
        await _workspace_manager(client).get_or_create_peer("story-1", "peer-1")

    assert get_exc.value.details is not None
    assert get_exc.value.details.operation == "get_peer"

    create_error = ConnectionError("peer create failed")
    client = SimpleNamespace(
        peers=SimpleNamespace(get=_AsyncCall(None), create=_AsyncCall(error=create_error))
    )

    with pytest.raises(HonchoClientError) as create_exc:
        await _workspace_manager(client).get_or_create_peer("story-1", "peer-1")

    assert create_exc.value.error_code == "CONNECTION_ERROR"
    assert create_exc.value.details is not None
    assert create_exc.value.details.operation == "create_peer"


@pytest.mark.asyncio
async def test_session_manager_creates_session_and_context() -> None:
    session = object()
    create = _AsyncCall(session)
    context = _AsyncCall(_Context())
    client = SimpleNamespace(sessions=SimpleNamespace(create=create, context=context))
    manager = _session_manager(client)

    created = await manager.create_session(
        "story-1",
        "peer-1",
        session_id="session-1",
        metadata={"kind": "test"},
    )
    openai_context = await manager.get_session_context("story-1", "session-1")

    assert created is session
    assert create.calls == [
        (
            (),
            {
                "workspace_id": "story-1",
                "peer_id": "peer-1",
                "session_id": "session-1",
                "metadata": {"kind": "test"},
            },
        )
    ]
    assert openai_context == [{"role": "user", "content": "hello"}]


@pytest.mark.asyncio
async def test_session_manager_maps_errors_and_empty_context() -> None:
    create_error = TimeoutError("session timeout")
    client = SimpleNamespace(
        sessions=SimpleNamespace(
            create=_AsyncCall(error=create_error),
            context=_AsyncCall(SimpleNamespace()),
        )
    )
    manager = _session_manager(client)

    with pytest.raises(HonchoClientError) as create_exc:
        await manager.create_session("story-1", "peer-1")

    assert create_exc.value.error_code == "TIMEOUT_ERROR"
    assert create_exc.value.details is not None
    assert create_exc.value.details.operation == "create_session"

    assert await manager.get_session_context("story-1", "session-1") == []

    context_error = RuntimeError("context failed")
    client.sessions.context = _AsyncCall(error=context_error)
    with pytest.raises(HonchoClientError) as context_exc:
        await manager.get_session_context("story-1", "session-1")

    assert context_exc.value.error_code == "UNKNOWN_ERROR"
    assert context_exc.value.details is not None
    assert context_exc.value.details.operation == "get_session_context"


@pytest.mark.asyncio
async def test_message_handler_adds_and_searches_messages() -> None:
    message = object()
    search_result = [object()]
    add = _AsyncCall(message)
    session_search = _AsyncCall(search_result)
    peer_search = _AsyncCall("unexpected shape")
    client = SimpleNamespace(
        messages=SimpleNamespace(create=add),
        sessions=SimpleNamespace(search=session_search),
        peers=SimpleNamespace(search=peer_search),
    )
    handler = _message_handler(client)

    added = await handler.add_message("story-1", "session-1", "hello")
    session_results = await handler.search_memories(
        "story-1",
        "peer-1",
        "query",
        session_id="session-1",
    )
    peer_results = await handler.search_memories("story-1", "peer-1", "query")

    assert added is message
    assert session_results == search_result
    assert peer_results == []
    assert add.calls[0][1]["metadata"] == {}
    assert session_search.calls[0][1]["top_k"] == 10
    assert peer_search.calls[0][1]["peer_id"] == "peer-1"


@pytest.mark.asyncio
async def test_message_handler_representation_and_chat_paths() -> None:
    session_representation = _AsyncCall(SimpleNamespace(content="session insight"))
    peer_representation = _AsyncCall(None)
    session_chat = _AsyncCall(SimpleNamespace(content="session answer"))
    peer_chat = _AsyncCall(SimpleNamespace(content="peer answer"))
    client = SimpleNamespace(
        sessions=SimpleNamespace(
            representation=session_representation,
            chat=session_chat,
        ),
        peers=SimpleNamespace(
            representation=peer_representation,
            chat=peer_chat,
        ),
    )
    handler = _message_handler(client)

    assert (
        await handler.get_peer_representation("story-1", "peer-1", "session-1")
        == "session insight"
    )
    assert await handler.get_peer_representation("story-1", "peer-1") == ""
    assert await handler.chat_with_peer("story-1", "peer-1", "query", "session-1") == (
        "session answer"
    )
    assert await handler.chat_with_peer("story-1", "peer-1", "query") == "peer answer"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_code"),
    [
        ("add_message", "CONNECTION_ERROR"),
        ("search_memories", "TIMEOUT_ERROR"),
        ("get_peer_representation", "UNKNOWN_ERROR"),
        ("chat_with_peer", "UNKNOWN_ERROR"),
    ],
)
async def test_message_handler_maps_operation_errors(
    operation: str,
    expected_code: str,
) -> None:
    error_by_operation = {
        "add_message": ConnectionError("add failed"),
        "search_memories": TimeoutError("search failed"),
        "get_peer_representation": RuntimeError("representation failed"),
        "chat_with_peer": RuntimeError("chat failed"),
    }
    error = error_by_operation[operation]
    client = SimpleNamespace(
        messages=SimpleNamespace(create=_AsyncCall(error=error)),
        sessions=SimpleNamespace(
            search=_AsyncCall(error=error),
            representation=_AsyncCall(error=error),
            chat=_AsyncCall(error=error),
        ),
        peers=SimpleNamespace(
            search=_AsyncCall(error=error),
            representation=_AsyncCall(error=error),
            chat=_AsyncCall(error=error),
        ),
    )
    handler = _message_handler(client)

    with pytest.raises(HonchoClientError) as exc_info:
        if operation == "add_message":
            await handler.add_message("story-1", "session-1", "hello")
        elif operation == "search_memories":
            await handler.search_memories("story-1", "peer-1", "query", session_id="s")
        elif operation == "get_peer_representation":
            await handler.get_peer_representation("story-1", "peer-1", "s")
        else:
            await handler.chat_with_peer("story-1", "peer-1", "query", "s")

    assert exc_info.value.error_code == expected_code
    assert exc_info.value.details is not None
    assert exc_info.value.details.operation == operation
