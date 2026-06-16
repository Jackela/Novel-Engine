# Novel Studio

Novel Studio `0.3.0` is a self-hosted single-author novel writing IDE. SQLite is
the content authority and Markdown is the document syntax.

## First-Time Setup

```bash
copy .env.example .env.local
uv sync --extra dev --extra test
corepack pnpm install --frozen-lockfile
corepack pnpm --dir frontend build
uv run novel-engine serve --reload
```

Open `http://127.0.0.1:8000`, create the local Owner account on the setup
screen, then log in. For local development the default AI provider is `mock`, so
AI proposal flows work without external credentials.

## Configuration

The canonical environment template is `.env.example`; copy it to `.env.local`.

| Variable | Default | Notes |
|---|---:|---|
| `APP_ENVIRONMENT` | `development` | Use `production` only with explicit secrets and CORS origins. |
| `APP_DATA_DIR` | `./data` | Stores SQLite data, imports, exports, and backups. |
| `DB_URL` | `sqlite:///./data/novel-engine.sqlite3` | Only SQLite is supported. |
| `SECURITY_SECRET_KEY` | sample value | Required in production; generate a unique value. |
| `SECURITY_CORS_ORIGINS` | localhost origins | Must be explicit and non-localhost in production. |
| `LLM_PROVIDER` | `mock` | `mock`, `dashscope`, or `openai_compatible`. |
| `LLM_MODEL` | `studio-copilot-v1` | Default model label for mock/local flows. |
| `DASHSCOPE_API_KEY` | unset | Required when `LLM_PROVIDER=dashscope`. |
| `LLM_API_KEY` | unset | Required when `LLM_PROVIDER=openai_compatible`. |
| `MONITORING_METRICS_ENABLED` | `false` | Enable only when port `9090` is available. |

Frontend-only variables live in `frontend/.env.example`:
`VITE_API_BASE_URL`, `VITE_API_TIMEOUT`, and `VITE_API_PROXY_TARGET`.

## Docker

```bash
set SECURITY_SECRET_KEY=replace-with-a-long-random-secret
docker compose up --build
```

PowerShell users can use `$env:SECURITY_SECRET_KEY="replace-with-a-long-random-secret"`.
Docker Compose defaults `LLM_PROVIDER` to `mock`; set `LLM_PROVIDER`,
`DASHSCOPE_API_KEY`, or `LLM_API_KEY` explicitly to use a real provider.

## Commands

```bash
uv run novel-engine --help
uv run novel-engine serve --reload
uv run novel-engine doctor
uv run novel-engine backup
```

Legacy import expects a directory containing `story.yaml` and optional chapter
files under `manuscript/chapters/chapter-*.md`:

```text
legacy-workspace/
  story.yaml
  manuscript/
    chapters/
      chapter-001.md
```

Run `uv run novel-engine import --source path/to/legacy-workspace --owner <username>`
after the Owner account has been created.

## Validation

```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
uv run python scripts/qa/check_ssot.py
uv run python scripts/qa/check_repo_hygiene.py
uv run python scripts/qa/check_openapi_snapshot.py
corepack pnpm --dir frontend type-check
corepack pnpm --dir frontend test:unit
corepack pnpm --dir frontend build
```

On Windows without `make`, run the commands above directly. `pre-commit` and
`trunk` are optional local wrappers around the same gates.

## Product Specification

[`openspec/specs/novel-studio/spec.md`](openspec/specs/novel-studio/spec.md) is
the product definition. Validate it with:

```bash
corepack pnpm spec:validate
```
