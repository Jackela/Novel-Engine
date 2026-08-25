# Novel Engine

Novel Engine `0.4.0` is a self-hosted single-author novel writing IDE. SQLite is
the content authority and Markdown is the document syntax. One Node.js process
serves the Studio SPA and the JSON API.

## First-Time Setup

Prerequisites: Node.js 24 (LTS) and pnpm 11.

```bash
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm --dir frontend build
pnpm --dir server build
pnpm --dir server cli serve
```

Open `http://127.0.0.1:8000`, create the local Owner account on the setup
screen, then log in. For local development the default AI provider is `mock`, so
AI proposal flows work without external credentials.

## Configuration

The canonical environment template is `.env.example`; copy it to `.env.local`.
Process environment variables always win over the file.

| Variable | Default | Notes |
|---|---:|---|
| `APP_ENVIRONMENT` | `development` | Use `production` only with explicit secrets and CORS origins. |
| `DB_URL` | `sqlite:///./data/novel-engine.sqlite3` | Only SQLite is supported. |
| `API_HOST` | `0.0.0.0` | Bind address for `serve`. |
| `API_PORT` | `8000` | Listen port. |
| `SECURITY_SECRET_KEY` | sample value | Required in production; generate a unique value. |
| `SECURITY_CORS_ORIGINS` | localhost origins | Must be explicit and non-localhost in production. |
| `SECURITY_RATE_LIMIT` | `5/minute` | Auth endpoint rate limit. |
| `LLM_PROVIDER` | `mock` | `mock`, `dashscope`, or `openai_compatible`. |
| `LLM_MODEL` | `studio-copilot-v1` | Default model label for mock/local flows. |
| `DASHSCOPE_API_KEY` | unset | Required when `LLM_PROVIDER=dashscope`. |
| `LLM_API_KEY` | unset | Required when `LLM_PROVIDER=openai_compatible`. |

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

The healthcheck polls `/health/ready` inside the container.

## Commands

The operational CLI builds and runs through pnpm:

```bash
pnpm --dir server cli -- --help
pnpm --dir server cli serve
pnpm --dir server cli doctor
pnpm --dir server cli backup
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

Run `pnpm --dir server cli import --source path/to/legacy-workspace --owner <username>`
after the Owner account has been created. The import is read-only against the
source and idempotent per principal.

## Validation

```bash
pnpm --dir server gates
pnpm --dir server type-check
pnpm --dir server lint
pnpm --dir server arch
pnpm --dir server test
pnpm spec:validate
pnpm --dir frontend lint
pnpm --dir frontend format:check
pnpm --dir frontend type-check
pnpm --dir frontend test:unit
pnpm --dir frontend build
```

`make validate` and `just validate` wrap the same gates. CI is the
authoritative full contract (`.github/workflows/ci.yml`): it additionally runs
the API-types drift check, React static diagnostics, Playwright workflows
against the TS backend, and a container persistence check.

## Product Specification

[`openspec/specs/novel-engine/spec.md`](openspec/specs/novel-engine/spec.md) is
the product definition. Validate it with:

```bash
pnpm spec:validate
```

## Upgrading from 0.3.x (Python stack)

0.4.0 is the TypeScript rewrite cutover. The database schema is not migrated:
the TS server refuses to open a Python-era database by design. Back up or keep
the old `data/` directory, start 0.4.0 with a fresh data directory, create the
Owner account, then re-import legacy workspaces with the import command above.
The pre-cutover Python stack remains available at git tag `python-final`.
