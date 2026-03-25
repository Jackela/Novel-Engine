.PHONY: help install test lint format migration migrate migrate-down migrate-history

help:
	@echo "Novel Engine - Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make test            - Run tests"
	@echo "  make lint            - Run linters"
	@echo "  make format          - Format code"
	@echo "  make migration       - Create new migration (use: make migration message='description')"
	@echo "  make migrate         - Apply all pending migrations"
	@echo "  make migrate-down    - Rollback one migration"
	@echo "  make migrate-history - Show migration history"

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

lint:
	ruff check src/ tests/
	mypy src/ --no-error-summary

format:
	black src/ tests/
	isort src/ tests/

# Database migrations
migration:
	alembic revision --autogenerate -m "$(message)"

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

migrate-history:
	alembic history --verbose
