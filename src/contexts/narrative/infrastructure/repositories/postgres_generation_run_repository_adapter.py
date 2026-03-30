"""PostgreSQL adapter for independent generation run resources."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import UUID

from src.contexts.narrative.application.ports.generation_run_repository_port import (
    GenerationRunRepositoryPort,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    GenerationRunResourceState,
)

T = TypeVar("T")


class PostgresGenerationRunRepositoryAdapter(GenerationRunRepositoryPort):
    """Persist generation run resources outside workspace state using PostgreSQL."""

    def __init__(self, connection_pool: Any) -> None:
        self._connection_pool = connection_pool

    async def _run(self, operation: Callable[[Any], Awaitable[T]]) -> T:
        async with self._connection_pool.acquire() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS story_generation_runs (
                    story_id UUID PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            return await operation(connection)

    async def get_by_story_id(
        self,
        story_id: str,
    ) -> GenerationRunResourceState | None:
        story_uuid = UUID(story_id)

        async def operation(connection: Any) -> GenerationRunResourceState | None:
            row = await connection.fetchrow(
                """
                SELECT payload
                FROM story_generation_runs
                WHERE story_id = $1
                """,
                story_uuid,
            )
            if row is None:
                return None
            return GenerationRunResourceState.from_dict(row["payload"])

        return await self._run(operation)

    async def save(self, state: GenerationRunResourceState) -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=True)
        story_uuid = UUID(state.story_id)

        async def operation(connection: Any) -> None:
            await connection.execute(
                """
                INSERT INTO story_generation_runs (story_id, payload, updated_at)
                VALUES ($1, $2::jsonb, NOW())
                ON CONFLICT (story_id) DO UPDATE SET
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
                """,
                story_uuid,
                payload,
            )

        await self._run(operation)

    async def delete(self, story_id: str) -> bool:
        story_uuid = UUID(story_id)

        async def operation(connection: Any) -> bool:
            result: str = await connection.execute(
                """
                DELETE FROM story_generation_runs
                WHERE story_id = $1
                """,
                story_uuid,
            )
            return bool(result and result != "DELETE 0")

        return await self._run(operation)


__all__ = ["PostgresGenerationRunRepositoryAdapter"]

