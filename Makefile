.PHONY: help install test lint cli-smoke format migration migrate migrate-down migrate-history

help:
	@echo "Novel Engine - Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make test            - Run tests"
	@echo "  make lint            - Run linters"
	@echo "  make cli-smoke       - Run local-first CLI tests"
	@echo "  make format          - Format code"
	@echo "  make migration       - Create new migration (use: make migration message='description')"
	@echo "  make migrate         - Apply all pending migrations"
	@echo "  make migrate-down    - Rollback one migration"
	@echo "  make migrate-history - Show migration history"

install:
	uv sync --extra dev --extra test --frozen

test:
	uv run pytest -q
	uv run pytest tests/unit/infrastructure tests/apps/api/test_health.py --cov=src/shared/infrastructure/auth --cov=src/shared/infrastructure/config --cov=src/shared/infrastructure/health --cov=src/shared/infrastructure/persistence --cov-report=term-missing --cov-fail-under=80 -q
	uv run pytest tests/shared/infrastructure/circuit_breaker tests/shared/infrastructure/middleware tests/apps/api/middleware --cov=src/shared/infrastructure/circuit_breaker --cov=src/shared/infrastructure/middleware --cov=src/apps/api/middleware --cov-report=term-missing --cov-fail-under=80 -q
	uv run pytest tests/shared/infrastructure/honcho tests/contexts/ai --cov=src/shared/infrastructure/honcho --cov=src.shared.infrastructure.health.checks.honcho_health_check --cov=src/contexts/ai/infrastructure/providers --cov-report=term-missing --cov-fail-under=80 -q

lint:
	uv run ruff check src/ tests/
	uv run mypy src/ tests/ --no-error-summary --show-column-numbers
	uv run python scripts/qa/check_repo_hygiene.py

cli-smoke:
	uv run pytest tests/apps/cli/test_novel_engine.py -q

format:
	uv run black src/ tests/
	uv run isort src/ tests/

# Database migrations
migration:
	uv run alembic revision --autogenerate -m "$(message)"

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-history:
	uv run alembic history --verbose
