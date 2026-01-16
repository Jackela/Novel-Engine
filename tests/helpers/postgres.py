#!/usr/bin/env python3
"""PostgreSQL test helper for hybrid integration tests."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class PostgresConfig:
    compose_file: Path
    service_name: str = "postgres"
    user: str = "novel_engine"
    password: str = "novel_engine_dev_password"
    db_name: str = "novel_engine_test"
    host: str = "localhost"
    port: int = 5432

    @property
    def url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db_name}"
        )


class PostgresService:
    """Manage a local Postgres container for tests."""

    def __init__(self, config: PostgresConfig) -> None:
        self.config = config

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            check=True,
            text=True,
            capture_output=True,
        )

    def start(self, timeout_seconds: int = 60) -> None:
        self._run(
            [
                "docker",
                "compose",
                "-f",
                str(self.config.compose_file),
                "up",
                "-d",
                self.config.service_name,
            ]
        )
        self._wait_until_ready(timeout_seconds=timeout_seconds)
        self._ensure_schema()

    def _wait_until_ready(self, timeout_seconds: int) -> None:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                self._run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(self.config.compose_file),
                        "exec",
                        "-T",
                        self.config.service_name,
                        "pg_isready",
                        "-U",
                        self.config.user,
                        "-d",
                        self.config.db_name,
                    ]
                )
                return
            except subprocess.CalledProcessError:
                time.sleep(2)
        raise RuntimeError("PostgreSQL did not become ready in time")

    def stop(self) -> None:
        self._run(
            [
                "docker",
                "compose",
                "-f",
                str(self.config.compose_file),
                "stop",
                self.config.service_name,
            ]
        )

    def _run_psql(self, sql: str) -> None:
        self._run(
            [
                "docker",
                "compose",
                "-f",
                str(self.config.compose_file),
                "exec",
                "-T",
                self.config.service_name,
                "psql",
                "-U",
                self.config.user,
                "-d",
                self.config.db_name,
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                sql,
            ]
        )

    def _ensure_schema(self) -> None:
        sql = """
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TABLE IF NOT EXISTS knowledge_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            knowledge_type VARCHAR(20) NOT NULL,
            owning_character_id VARCHAR(255),
            access_level VARCHAR(30) NOT NULL,
            allowed_roles TEXT[],
            allowed_character_ids TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by VARCHAR(255) NOT NULL,
            CONSTRAINT ck_knowledge_entries_content_not_empty CHECK (LENGTH(TRIM(content)) > 0),
            CONSTRAINT ck_knowledge_entries_valid_type CHECK (knowledge_type IN ('profile', 'objective', 'memory', 'lore', 'rules')),
            CONSTRAINT ck_knowledge_entries_valid_access_level CHECK (access_level IN ('public', 'role_based', 'character_specific')),
            CONSTRAINT ck_knowledge_entries_valid_timestamps CHECK (updated_at >= created_at),
            CONSTRAINT ck_knowledge_entries_role_based_requires_roles CHECK (
                access_level != 'role_based'
                OR (allowed_roles IS NOT NULL AND array_length(allowed_roles, 1) > 0)
            ),
            CONSTRAINT ck_knowledge_entries_character_specific_requires_ids CHECK (
                access_level != 'character_specific'
                OR (allowed_character_ids IS NOT NULL AND array_length(allowed_character_ids, 1) > 0)
            )
        );

        CREATE INDEX IF NOT EXISTS ix_knowledge_entries_owning_character_id
            ON knowledge_entries (owning_character_id);
        CREATE INDEX IF NOT EXISTS ix_knowledge_entries_access_level
            ON knowledge_entries (access_level);
        CREATE INDEX IF NOT EXISTS ix_knowledge_entries_knowledge_type
            ON knowledge_entries (knowledge_type);
        CREATE INDEX IF NOT EXISTS ix_knowledge_entries_created_at
            ON knowledge_entries (created_at);
        CREATE INDEX IF NOT EXISTS ix_knowledge_entries_updated_at
            ON knowledge_entries (updated_at);
        CREATE INDEX IF NOT EXISTS ix_knowledge_entries_allowed_roles
            ON knowledge_entries USING gin (allowed_roles);
        CREATE INDEX IF NOT EXISTS ix_knowledge_entries_allowed_character_ids
            ON knowledge_entries USING gin (allowed_character_ids);

        CREATE TABLE IF NOT EXISTS knowledge_audit_log (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id VARCHAR(255) NOT NULL,
            entry_id UUID NOT NULL REFERENCES knowledge_entries(id) ON DELETE CASCADE,
            change_type VARCHAR(20) NOT NULL,
            snapshot JSONB,
            CONSTRAINT ck_knowledge_audit_log_valid_change_type CHECK (
                change_type IN ('created', 'updated', 'deleted')
            )
        );

        CREATE INDEX IF NOT EXISTS ix_knowledge_audit_log_entry_id
            ON knowledge_audit_log (entry_id);
        CREATE INDEX IF NOT EXISTS ix_knowledge_audit_log_timestamp
            ON knowledge_audit_log (timestamp);
        CREATE INDEX IF NOT EXISTS ix_knowledge_audit_log_user_id
            ON knowledge_audit_log (user_id);
        CREATE INDEX IF NOT EXISTS ix_knowledge_audit_log_change_type
            ON knowledge_audit_log (change_type);

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_knowledge_entries_updated_at'
            ) THEN
                CREATE TRIGGER trigger_knowledge_entries_updated_at
                BEFORE UPDATE ON knowledge_entries
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END
        $$;
        """
        self._run_psql(sql)


def ensure_postgres_service() -> PostgresService:
    compose_file = Path("docker") / "docker-compose.yaml"
    if os.getenv("NOVEL_ENGINE_SKIP_SERVICES") == "1":
        pytest.skip("NOVEL_ENGINE_SKIP_SERVICES=1 set; skipping PostgreSQL setup.")

    if not shutil.which("docker"):
        pytest.skip("Docker is required for PostgreSQL integration tests.")

    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        pytest.skip("Docker Compose is required for PostgreSQL integration tests.")

    if not compose_file.exists():
        pytest.skip(f"Missing compose file: {compose_file}")

    config = PostgresConfig(compose_file=compose_file)
    service = PostgresService(config)
    try:
        service.start()
    except subprocess.CalledProcessError as exc:
        pytest.skip(f"PostgreSQL container startup failed: {exc}")
    os.environ["POSTGRES_URL"] = config.url
    return service
