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
    pnpm install --frozen-lockfile
    pnpm --dir frontend install --frozen-lockfile

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
    git diff | grep -E '^\-.*\b(raise|assert|validate|sanitize|escape|auth|permission|guard)\b' || echo "None found"
    @echo ""
    @echo "=== New bare except patterns ==="
    git diff | grep -E '^\+.*except\s+Exception' || echo "None found"
    @echo ""
    @echo "=== New SQL string concatenation ==="
    git diff | grep -E '^\+.*f".*SELECT|INSERT|UPDATE|DELETE|MATCH' || echo "None found"

# Full validation (run after any significant change)
validate:
    pnpm --dir server gates
    pnpm --dir server type-check
    pnpm --dir server lint
    pnpm --dir server arch
    pnpm --dir server test
    pnpm --dir frontend lint
    pnpm --dir frontend type-check
    pnpm --dir frontend test:unit
    pnpm --dir frontend build
    pnpm spec:validate

# Server-only validation
validate-server:
    pnpm --dir server gates
    pnpm --dir server type-check
    pnpm --dir server lint
    pnpm --dir server arch
    pnpm --dir server test

# Frontend-only validation
validate-frontend:
    pnpm --dir frontend lint
    pnpm --dir frontend type-check
    pnpm --dir frontend test:unit
    pnpm --dir frontend build
