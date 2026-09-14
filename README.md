# Novel Engine

Novel Engine `0.7.0` is a self-hosted single-author novel writing IDE. SQLite is
the content authority and Markdown is the document syntax. One Node.js process
serves the Studio SPA and the JSON API.

[Documentation](docs/README.md) · [Contributing](CONTRIBUTING.md) ·
[Security](.github/SECURITY.md) · [License](LICENSE)

## For Writers

If you only want to write with Novel Engine — no development involved — start
with the writer guides: [getting started with Docker](openwiki/guides/getting-started.md)
covers installation to your first AI-assisted chapter, and
[provider setup](openwiki/guides/provider-setup.md) connects a real AI
provider such as DashScope or DeepSeek. The full journey is documented end to
end: [writing](openwiki/guides/writing-guide.md),
[exporting](openwiki/guides/exporting.md),
[backup and restore](openwiki/guides/backup-and-restore.md),
[upgrading](openwiki/guides/upgrading.md),
[troubleshooting](openwiki/guides/troubleshooting.md), and the
[FAQ](openwiki/guides/faq.md).

## First-Time Setup

Prerequisites: Node.js 24 and the pnpm version pinned in
[`package.json`](package.json) — get pnpm via `corepack enable` or
`npm install -g pnpm@11`. For Windows setup and development mode, see
the [quickstart](openwiki/quickstart.md).

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
Process environment variables always win over the file. `.env.local` and the
default SQLite `data/` directory resolve against the workspace root (the
checkout directory), not the current working directory, so `pnpm --dir server
cli serve` reads the root `.env.local` and stores data under `<workspace>/data/`.
Under Docker Compose the container instead receives provider settings from a
project-root `.env` file (or the shell environment) through the pass-through
declared in `compose.yaml`; see the [provider setup
guide](openwiki/guides/provider-setup.md).

| Variable | Default | Notes |
|---|---:|---|
| `APP_ENVIRONMENT` | `development` | Use `production` only with explicit secrets and CORS origins. |
| `DB_URL` | `sqlite:///./data/novel-engine.sqlite3` | Only SQLite is supported. |
| `API_HOST` | `0.0.0.0` | Bind address for `serve`. |
| `API_PORT` | `8000` | Listen port. |
| `API_MAX_ACTIVE_WORKFLOWS` | `4` | Global concurrent workflow capacity; integer 1–1024. |
| `API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT` | `2` | Per-project workflow capacity; must not exceed the global limit. |
| `SECURITY_SECRET_KEY` | sample value | Required in production; generate a unique value. |
| `SECURITY_CORS_ORIGINS` | localhost origins | Must be explicit and non-localhost in production. |
| `SECURITY_RATE_LIMIT` | `5/minute` | Auth endpoint rate limit. |
| `SECURITY_TRUSTED_PROXIES` | empty | Comma-separated trusted proxies (exact IP, CIDR, or host) for forwarded client identity. |
| `LLM_PROVIDER` | `mock` | `mock`, `dashscope`, or `openai_compatible`. |
| `LLM_MODEL` | `studio-copilot-v1` | Default model label for mock/local flows; intermediate model fallback for real providers. |
| `DASHSCOPE_API_KEY` | unset | Required when `LLM_PROVIDER=dashscope`. |
| `DASHSCOPE_TRANSPORT_MODE` | `multimodal_generation` | `text_generation`, `multimodal_generation`, or `responses`. |
| `DASHSCOPE_MODEL` | unset | DashScope generation model; falls back to `LLM_MODEL`, then `qwen3.5-flash`. |
| `DASHSCOPE_REVIEW_MODEL` | unset | DashScope model for AI review runs; falls back to the generation model. |
| `DASHSCOPE_API_BASE` | unset | Custom DashScope API base URL, for gateways mirroring the DashScope API. |
| `LLM_API_KEY` | unset | Required when `LLM_PROVIDER=openai_compatible`. |
| `OPENAI_API_KEY` | unset | Alias of `LLM_API_KEY`; `LLM_API_KEY` takes precedence when both are set. |
| `LLM_API_BASE` | unset | Base URL of the OpenAI-compatible endpoint (e.g. `https://api.openai.com/v1`). |
| `OPENAI_API_BASE` | unset | Alias of `LLM_API_BASE`; `LLM_API_BASE` takes precedence when both are set. |
| `OPENAI_COMPATIBLE_MODEL` | unset | OpenAI-compatible generation model; falls back to `LLM_MODEL`, then `gpt-4o-mini`. |
| `LLM_TIMEOUT` | `30` | Outbound provider request timeout in seconds (5–300). |
| `LLM_STREAM_FIRST_BYTE_TIMEOUT_MS` | `30000` | Streaming silence ceiling (ms) before the first proposal byte (1–300000). |
| `LLM_STREAM_IDLE_TIMEOUT_MS` | `60000` | Streaming silence ceiling (ms) between consecutive frames (1–300000). |
| `LLM_RETRY_ATTEMPTS` | `3` | Provider retry attempts (1–3). |
| `LLM_RETRY_DELAY` | `1` | Base retry delay in seconds (0.1–10). |
| `LLM_LOREBOOK_BUDGET_CHARACTERS` | `4000` | Character budget of the lorebook prompt section. |

Frontend-only variables live in `frontend/.env.example`:
`VITE_API_BASE_URL`, `VITE_API_TIMEOUT`, and `VITE_API_PROXY_TARGET`.

## Docker

Docker is the recommended way to run Novel Engine. Once v0.8.0 is published,
the quickest path needs no clone and no build: a prebuilt image on GHCR is
started by a single command (see [deploy/README.md](deploy/README.md) for the
walkthrough, upgrades, and hosting a demo server):

```bash
curl -fsSL https://raw.githubusercontent.com/Jackela/Novel-Engine/v0.8.0/deploy/compose.yaml | docker compose -f - up -d
```

Until that image is published — and any time you want to run from source —
use the clone path below. First get the code: clone this repository, or
download it via the **Code** → **Download ZIP** button on GitHub and unzip
it. Then, from the folder containing `compose.yaml` (the first start builds
the image and can take a few minutes):

```bash
docker compose up -d
```

Open `http://localhost:8000` in Chrome or Firefox and create the Owner
account on the setup screen, then log in. Safari works but has a known
rendering limitation in the frosted-glass visual style, so Chrome or Firefox
is recommended. No secret or other manual configuration is needed: on first
start the container generates a session secret into the `novel-engine-data`
volume, and because that volume persists, sessions keep working across
restarts. A healthcheck polls `/health/ready` inside the container.

The container runs with `restart: unless-stopped`, so it comes back on its
own after a crash or a machine reboot (unless you stopped it yourself). To
bring the studio up again after stopping it, run `docker compose up -d` in
the same folder.

If port 8000 is already taken by another application, create a
`compose.override.yaml` next to `compose.yaml` with this content and restart
with `docker compose up -d`; the studio then listens on port 8001 (the
`!override` tag replaces the default port mapping instead of adding to it;
requires Docker Compose v2.24+, which current Docker Desktop ships):

```yaml
services:
  novel-engine:
    ports: !override
      - "8001:8000"
```

Alternatively, edit `compose.yaml` and change `8000:8000` to `8001:8000`.

Your novels live in the `novel-engine-data` named volume: `docker compose
down` keeps it, `docker compose down -v` deletes it (permanently). The
built-in `mock` AI provider works out of the box; to generate real AI
proposals, set `LLM_PROVIDER` and its API key variable — see
[Configuration](#configuration).

## Commands

The operational CLI builds and runs through pnpm:

```bash
pnpm --dir server cli serve
pnpm --dir server cli doctor
pnpm --dir server cli backup
pnpm --dir server cli restore --input <backup-file>
```

`backup` writes a consistent online backup beneath `data/backups/` and prints
its path. `restore --input <backup-file>` verifies a backup file, backs up
the current database, then replaces it atomically. Both commands take
exclusive ownership of the data directory: stop the running server first.
Backups are never removed automatically. For the Docker equivalents, see the
[backup and restore guide](openwiki/guides/backup-and-restore.md).

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

`make validate` and `just validate` cover a subset of checks. CI defines the
full automated contract ([workflow](.github/workflows/ci.yml)): it additionally runs
the API-types drift check, React static diagnostics, Playwright workflows
against the TS backend, and a container persistence check.
See [CI gates](docs/agents/ci-gates.md) for failure runbooks and the
[quickstart](openwiki/quickstart.md#quick-validation) for browser prerequisites.

## Product Specification

[`openspec/specs/novel-engine/spec.md`](openspec/specs/novel-engine/spec.md) is
the product definition. Validate it with:

```bash
pnpm spec:validate
```

## Upgrading from 0.3.x (Python stack)

0.4.0 is the TypeScript rewrite cutover. The database schema is not migrated:
a Python-era database is unsupported and must not be reused as the new
`data/` directory. Back up or keep the old `data/` directory, start 0.4.0 with
a fresh data directory, create the Owner account, then re-import legacy
workspaces with the import command above. The pre-cutover Python stack remains
available at git tag `python-final`.
