from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Any
from uuid import uuid4

import pytest

from src.shared.domain.base.aggregate import AggregateRoot
from src.shared.infrastructure.persistence.database import Database, DatabaseConnection
from src.shared.infrastructure.persistence.repository import (
    AggregateNotFoundException,
    ConcurrentModificationException,
    InMemoryRepository,
)
from src.shared.infrastructure.persistence.unit_of_work import (
    DatabaseUnitOfWork,
    TransactionRollbackException,
    UnitOfWorkFactory,
    UnitOfWorkResult,
    get_unit_of_work_factory,
    get_uow,
    set_unit_of_work_factory,
)


@dataclass(eq=False)
class ExampleAggregate(AggregateRoot):
    name: str = "example"


class RecordingConnection:
    async def execute(self, query: str, *args: Any) -> str:
        return "OK"

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        return []

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        return None

    async def fetchval(self, query: str, *args: Any) -> Any | None:
        return None

    async def execute_many(self, query: str, args_seq: list[tuple[Any, ...]]) -> None:
        return None


class RecordingContext(AbstractAsyncContextManager[DatabaseConnection]):
    def __init__(self, connection: RecordingConnection) -> None:
        self.connection = connection
        self.entered = False
        self.exit_args: tuple[type[BaseException] | None, BaseException | None] | None = None

    async def __aenter__(self) -> DatabaseConnection:
        self.entered = True
        return self.connection

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.exit_args = (exc_type, exc)


class RecordingDatabase(Database):
    def __init__(self) -> None:
        super().__init__("postgresql://user:secret@example.test/db")
        self.connection_context = RecordingContext(RecordingConnection())
        self.transaction_context = RecordingContext(RecordingConnection())

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def connection(self) -> AbstractAsyncContextManager[DatabaseConnection]:
        return self.connection_context

    def transaction(self) -> AbstractAsyncContextManager[DatabaseConnection]:
        return self.transaction_context


@pytest.mark.asyncio
async def test_in_memory_repository_crud_and_conversion_guards() -> None:
    repo: InMemoryRepository[ExampleAggregate, object] = InMemoryRepository()
    aggregate = ExampleAggregate(id=uuid4(), name="first")

    await repo.add(aggregate)
    assert await repo.get(aggregate.id) == aggregate
    assert await repo.exists(aggregate.id) is True
    assert await repo.get_all() == [aggregate]

    aggregate.name = "updated"
    await repo.update(aggregate)
    updated = await repo.get(aggregate.id)
    assert updated is not None
    assert updated.name == "updated"

    assert await repo.delete(aggregate.id) is True
    assert await repo.delete(aggregate.id) is False
    assert await repo.exists(aggregate.id) is False

    with pytest.raises(NotImplementedError):
        repo._to_aggregate({})
    with pytest.raises(NotImplementedError):
        repo._from_aggregate(aggregate)


def test_repository_exceptions_include_context() -> None:
    aggregate_id = uuid4()

    not_found = AggregateNotFoundException("Story", aggregate_id)
    conflict = ConcurrentModificationException("Story", aggregate_id, 1, 2)

    assert not_found.aggregate_type == "Story"
    assert not_found.id == aggregate_id
    assert "Story" in str(not_found)
    assert conflict.expected == 1
    assert conflict.actual == 2
    assert "expected version 1" in str(conflict)


@pytest.mark.asyncio
async def test_database_unit_of_work_sets_and_clears_repository_connections() -> None:
    db = RecordingDatabase()
    repo: InMemoryRepository[ExampleAggregate, object] = InMemoryRepository()
    uow = DatabaseUnitOfWork(db)
    uow.register_repository(repo)

    async with uow:
        assert uow.is_active is True
        assert repo.connection is db.connection_context.connection

    assert uow.is_active is False


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_on_context_exception() -> None:
    db = RecordingDatabase()
    uow = DatabaseUnitOfWork(db)

    with pytest.raises(ValueError, match="boom"):
        async with uow:
            raise ValueError("boom")

    assert uow.is_active is False
    with pytest.raises(RuntimeError, match="Cannot commit after rollback"):
        await uow.commit()


@pytest.mark.asyncio
async def test_transactional_unit_of_work_commits_and_rolls_back_transaction_context() -> None:
    db = RecordingDatabase()
    factory = UnitOfWorkFactory(db)

    async with factory.transaction() as uow:
        assert uow.is_active is True

    assert db.transaction_context.exit_args == (None, None)

    rollback_db = RecordingDatabase()
    rollback_uow = UnitOfWorkFactory(rollback_db).create(transactional=True)
    await rollback_uow.__aenter__()
    await rollback_uow.rollback()

    assert rollback_db.transaction_context.exit_args is not None
    exc_type, exc = rollback_db.transaction_context.exit_args
    assert exc_type is TransactionRollbackException
    assert isinstance(exc, TransactionRollbackException)


@pytest.mark.asyncio
async def test_unit_of_work_state_guards_and_factory_helpers() -> None:
    db = RecordingDatabase()
    factory = UnitOfWorkFactory(db)
    set_unit_of_work_factory(factory)

    non_transactional = get_uow(transactional=False)
    assert isinstance(non_transactional, DatabaseUnitOfWork)
    assert get_unit_of_work_factory() is factory

    async with non_transactional:
        pass

    with pytest.raises(RuntimeError, match="already committed"):
        await non_transactional.commit()


def test_unit_of_work_result_helpers() -> None:
    assert UnitOfWorkResult.success_result({"id": "1"}) == UnitOfWorkResult(
        success=True,
        data={"id": "1"},
    )
    assert UnitOfWorkResult.failure_result("failed") == UnitOfWorkResult(
        success=False,
        error="failed",
    )
