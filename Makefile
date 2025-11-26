# Makefile for Novel-Engine Development and Testing
# Provides convenient commands for local development and CI simulation

.PHONY: help setup test test-ci test-unit test-integration test-e2e test-coverage test-watch \
        validate-markers test-pyramid speed-report ci-full pre-push \
        act-setup act-test act-ci act-ci-verbose act-list act-clean \
        docker-clean lint format type-check install upgrade clean quality ci-local

# Default target
help:
	@echo "Novel-Engine Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Install dependencies and setup development environment"
	@echo "  make install        - Install production dependencies only"
	@echo "  make upgrade        - Upgrade all dependencies to latest versions"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test           - Run tests locally with pytest"
	@echo "  make test-ci        - Run CI test suite (enhanced_bridge + character_system)"
	@echo "  make test-watch     - Run tests in watch mode (requires pytest-watch)"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "CI Parity Commands (match GitHub Actions):"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e       - Run E2E tests only"
	@echo "  make validate-markers - Validate all test pyramid markers"
	@echo "  make test-pyramid   - Check test pyramid score (>= 5.5)"
	@echo "  make speed-report   - Run speed regression check"
	@echo "  make ci-full        - Run full CI simulation locally"
	@echo "  make pre-push       - Quick pre-push verification"
	@echo ""
	@echo "ACT Local GitHub Actions:"
	@echo "  make act-setup      - Setup ACT for local GitHub Actions testing"
	@echo "  make act-test       - Run CI workflow with ACT (dry-run)"
	@echo "  make act-ci         - Run full CI workflow with ACT (live)"
	@echo "  make act-clean      - Clean ACT containers and artifacts"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linters (ruff, mypy)"
	@echo "  make format         - Format code with ruff"
	@echo "  make type-check     - Run type checking with mypy"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove Python cache and build artifacts"
	@echo "  make docker-clean   - Clean Docker containers and images"
	@echo ""

# ============================================
# Setup Commands
# ============================================

setup: install
	@echo "✓ Development environment ready"

install:
	@echo "Installing dependencies..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt -r requirements-test.txt
	@echo "✓ Dependencies installed"

upgrade:
	@echo "Upgrading dependencies..."
	pip install --upgrade -r requirements.txt -r requirements-test.txt
	pip freeze > requirements-frozen.txt
	@echo "✓ Dependencies upgraded (see requirements-frozen.txt)"

# ============================================
# Testing Commands
# ============================================

test:
	@echo "Running tests locally..."
	pytest -v

test-ci:
	@echo "Running CI test suite..."
	pytest -q tests/test_enhanced_bridge.py tests/test_character_system_comprehensive.py --junitxml=pytest-report.xml

test-watch:
	@echo "Running tests in watch mode..."
	ptw -- -v

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=src --cov-report=html --cov-report=term

# ============================================
# CI Parity Commands (match GitHub Actions)
# ============================================

test-unit:
	@echo "Running unit tests..."
	pytest -m "unit" --tb=short --durations=10

test-integration:
	@echo "Running integration tests..."
	pytest -m "integration" --tb=short --durations=10

test-e2e:
	@echo "Running E2E tests..."
	pytest -m "e2e" --tb=short --durations=10

validate-markers:
	@echo "Validating test markers..."
	python scripts/testing/validate-test-markers.py --all --verbose

test-pyramid:
	@echo "Checking test pyramid..."
	python scripts/testing/test-pyramid-monitor-fast.py --format json

speed-report:
	@echo "Running speed regression check..."
	python scripts/testing/test-speed-report.py

# Full CI simulation (matches GitHub Actions ci.yml)
ci-full: validate-markers test-pyramid test-unit test-integration test-e2e test-ci speed-report
	@echo "✓ Full CI simulation complete"

# Pre-push check (quick verification before pushing)
pre-push: validate-markers test-pyramid test-unit
	@echo "✓ Pre-push checks passed"

# ============================================
# ACT Local GitHub Actions Commands
# ============================================

act-setup:
	@echo "Setting up ACT for local GitHub Actions testing..."
	@echo ""
	@echo "1. Checking ACT installation..."
	@which act || (echo "❌ ACT not installed. Install with: winget install nektos.act" && exit 1)
	@echo "   ✓ ACT installed: $$(act --version)"
	@echo ""
	@echo "2. Checking Docker..."
	@docker info > /dev/null 2>&1 || (echo "❌ Docker not running. Start Docker Desktop." && exit 1)
	@echo "   ✓ Docker running: $$(docker --version)"
	@echo ""
	@echo "3. Creating .env from template if missing..."
	@test -f .env || cp .env.example .env
	@echo "   ✓ .env file ready"
	@echo ""
	@echo "4. Setup complete! Next steps:"
	@echo "   - Create .env.local with: echo 'GITHUB_TOKEN=ghp_your_token' > .env.local"
	@echo "   - Run: make act-test (dry-run) or make act-ci (live run)"
	@echo "   - See .claude/ACT_SETUP.md for detailed configuration"

act-test:
	@echo "Running ACT dry-run (no actual execution)..."
	act -W .github/workflows/ci.yml -j tests --dryrun

act-ci:
	@echo "Running full CI workflow with ACT..."
	@echo "This will execute the workflow in a Docker container..."
	act -W .github/workflows/ci.yml -j tests

act-ci-verbose:
	@echo "Running ACT with verbose output..."
	act -W .github/workflows/ci.yml -j tests --verbose

act-list:
	@echo "Listing available workflows and jobs..."
	act --list

act-clean:
	@echo "Cleaning ACT artifacts and containers..."
	rm -rf ./act-artifacts
	docker ps -a | grep "act-Tests-tests" | awk '{print $$1}' | xargs -r docker rm -f
	@echo "✓ ACT cleanup complete"

# ============================================
# Code Quality Commands
# ============================================

lint:
	@echo "Running linters..."
	@command -v ruff >/dev/null 2>&1 && ruff check src tests || echo "⚠ ruff not installed (pip install ruff)"
	@echo "✓ Linting complete"

format:
	@echo "Formatting code with ruff..."
	@command -v ruff >/dev/null 2>&1 && ruff format src tests || echo "⚠ ruff not installed (pip install ruff)"
	@echo "✓ Formatting complete"

type-check:
	@echo "Running type checks..."
	@command -v mypy >/dev/null 2>&1 && mypy src || echo "⚠ mypy not installed (pip install mypy)"
	@echo "✓ Type checking complete"

# ============================================
# Cleanup Commands
# ============================================

clean:
	@echo "Cleaning Python cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info
	rm -f pytest-report.xml pytest-report-validation.xml
	@echo "✓ Cleanup complete"

docker-clean:
	@echo "Cleaning Docker containers and images..."
	docker ps -a | grep "novel-engine\|act-" | awk '{print $$1}' | xargs -r docker rm -f
	docker images | grep "novel-engine\|catthehacker" | awk '{print $$3}' | xargs -r docker rmi
	@echo "✓ Docker cleanup complete"

# ============================================
# Quick Commands
# ============================================

# Quick test before commit
pre-commit: format lint test-ci
	@echo "✓ Pre-commit checks passed"

# Full quality check
quality: lint type-check test-coverage
	@echo "✓ Quality checks complete"

# Simulate full CI pipeline locally
ci-local: act-setup act-ci
	@echo "✓ Local CI simulation complete"
