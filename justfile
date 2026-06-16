# justfile — Novel-Engine AI Guardrails & Developer Commands
# Install just: https://github.com/casey/just

# Default recipe
_default:
    @just --list

# Create a git snapshot before AI session
snapshot msg="pre-ai-snapshot":
    git add -A
    git commit -m "{{ msg }}-$(date +%s)" || echo "Nothing to commit or already clean"

# Rollback to the last snapshot and clean untracked AI artifacts
rollback:
    git reset --hard HEAD~1
    git clean -fd
    uv sync --extra dev --extra test
    corepack pnpm install --frozen-lockfile
    corepack pnpm --dir frontend install --frozen-lockfile

# Kill all running AI processes (emergency brake)
kill-ai:
    pkill -f "codex" || true
    pkill -f "kimi" || true
    pkill -f "claude" || true
    echo "All AI processes terminated"

# Full panic: kill AI + rollback
panic: kill-ai rollback

# Regression checks after AI modifies code
check:
    @echo "=== Changed files ==="
    git diff --name-only
    @echo ""
    @echo "=== Deleted safety keywords ==="
    git diff | grep -E '^\-.*\b(raise|assert|validate|sanitize|escape|auth|permission)\b' || echo "None found"
    @echo ""
    @echo "=== New bare except patterns ==="
    git diff | grep -E '^\+.*except\s+Exception' || echo "None found"
    @echo ""
    @echo "=== New SQL string concatenation ==="
    git diff | grep -E '^\+.*f".*SELECT|INSERT|UPDATE|DELETE|MATCH' || echo "None found"

# Full validation (run after any significant change)
validate:
    uv run pytest -q
    uv run mypy src
    uv run ruff check src tests
    uv run bandit -r src
    uv run lint-imports
    corepack pnpm --dir frontend lint
    corepack pnpm --dir frontend type-check
    corepack pnpm --dir frontend test:unit
    corepack pnpm --dir frontend build
    corepack pnpm spec:validate
    uv run python scripts/qa/check_openapi_snapshot.py

# Backend-only validation
validate-backend:
    uv run pytest -q
    uv run mypy src
    uv run ruff check src tests
    uv run bandit -r src
    uv run lint-imports

# Frontend-only validation
validate-frontend:
    corepack pnpm --dir frontend lint
    corepack pnpm --dir frontend type-check
    corepack pnpm --dir frontend test:unit
    corepack pnpm --dir frontend build

# Run performance baseline tests (if they exist)
perf:
    uv run pytest tests/performance/ -v || echo "No performance tests found"
