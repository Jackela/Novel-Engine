# Novel Studio quickstart

Novel Studio **0.3.1** is a self-hosted, single-author writing studio. The authoritative store is SQLite, with repository documentation and configuration kept in version-controlled text files. The Python package requires **Python 3.11+**; the committed tooling specifies **pnpm 11.6.0**, and CI uses Python 3.12 and Node 22 (`pyproject.toml`, `package.json`, `.github/workflows/ci.yml`).

This page covers local operation, migration preparation, and the fastest checks after a change. The product specification is `openspec/specs/novel-studio/spec.md`.

## Install and start

The application reads `.env.local`; begin from the non-secret template rather than committing credentials:

```powershell
Copy-Item .env.example .env.local
uv sync --extra dev --extra test
corepack pnpm install --frozen-lockfile
corepack pnpm --dir frontend build
uv run novel-engine serve --reload
```

`novel-engine serve` uses `API_HOST` and `API_PORT` unless overridden with `--host` and `--port`; the template defaults to `0.0.0.0:8000` (`.env.example`, `src/apps/cli/novel_engine.py`). After the frontend build creates `frontend/dist/index.html`, the FastAPI app serves the built assets and SPA routes. A directory without that entry file returns the build-required JSON response instead. Browse to `http://127.0.0.1:8000` (`src/apps/api/main.py`).

For frontend-only development, run the backend above in one terminal and Vite in another:

```powershell
corepack pnpm --dir frontend dev
```

Vite listens on port **5173** and proxies `/api` to `VITE_API_PROXY_TARGET`, which defaults to `http://127.0.0.1:8000`; proxy request timeouts are five minutes (`frontend/vite.config.ts`, `frontend/.env.example`). Keep `VITE_API_BASE_URL` empty to use relative `/api` requests through that proxy. If it is set, the frontend sends requests to that explicit base URL instead (`frontend/src/app/config.ts`, `frontend/src/app/api.ts`).

## First session

On a new database, the entry screen creates the local Owner account. Keep an uninitialized service on loopback or a private network until this first setup is complete. The unauthenticated `POST /api/setup` compares every supplied `Origin` and `Referer` with the serving origin or an explicit configured non-wildcard CORS origin (or a supported localhost/127.0.0.1 port wildcard), rejecting cross-site requests with `403`; requests without browser origin metadata remain available to local bootstrap clients. Once an Owner exists, the SQLite repository performs an immediate transaction plus a second Owner-count check, so concurrent setup has one `201` winner and controlled `422` responses for later attempts. The API exposes setup state at `GET /api/setup` (`src/contexts/studio/interface/http/session_router.py`, `src/contexts/studio/infrastructure/repository/auth.py`, `src/apps/api/middleware/cors.py`).

The browser client uses cookie sessions (`novel_studio_session`) and sends credentials with API requests. Mutating requests include the `X-CSRF-Token` copied from the `novel_studio_csrf` cookie; setup, login, and guest-session creation are the explicit CSRF exemptions (`src/contexts/studio/interface/http/session_router.py`, `frontend/src/app/api.ts`). Owner login cookies have a 30-day max age. In production and staging both session cookies are marked `Secure`; local HTTP development leaves that attribute off so the browser can connect (`src/contexts/studio/interface/http/session_router.py`). Guest sessions are 24-hour sandboxes: startup and hourly cleanup delete the guest session's projects, jobs, reviews, and exports. Do not treat guest work as permanent (`src/contexts/studio/application/service_common.py`, `src/apps/api/runtime.py`).

Session lookup digests are HMAC-SHA256 values keyed by the injected `SECURITY_SECRET_KEY`, rather than bare hashes. The API runtime, CLI runtime, and test application pass the secret through `StudioServiceRegistry` into `AuthService`; application services do not read settings directly. Rotate the key as an intentional logout event: sessions created with the previous key no longer verify and users must sign in again. Cookie names, API payloads, and the CSRF header remain unchanged (`src/contexts/studio/domain/utils.py`, `src/contexts/studio/application/services/auth_service.py`, `src/contexts/studio/application/services/facade_base.py`).

## Studio routes

Inside a project, `/projects/:projectId/:section?` is route-driven. `review`, `history`, `export`, and `settings` each render their own project-level surface; History contains revision history only, while Export contains Markdown/DOCX/EPUB format actions, pending/error state, and recent export links. The top bar contains project identity and navigation only, so Review, Export, and Settings are not duplicated in a second menu (`frontend/src/features/studio/StudioPage.tsx`, `StudioTopbar.tsx`, `StudioInspector.tsx`).

The Studio keeps the editor first at tablet and phone widths. At 821–949px it switches to one column with the editor before navigation and Inspector; the same ordering is retained below 820px. Navigation and Inspector regions use accessible disclosure controls, icon/reorder controls are at least 44px square, and the supported layouts avoid horizontal overflow (`frontend/src/index.css`, `frontend/src/features/studio/StudioNavigator.tsx`, `StudioInspector.tsx`).

## Configuration and persistence

`.env.example` is the canonical configuration reference. Its important local defaults are:

- `APP_DATA_DIR=./data`; the Studio runtime uses it for application data.
- `DB_URL=sqlite:///./data/novel-engine.sqlite3`; only self-hosted SQLite URLs are accepted.
- `API_HOST=0.0.0.0`, `API_PORT=8000`, and `API_RELOAD=false`.
- `LLM_PROVIDER=mock` and `LLM_MODEL=studio-copilot-v1`; DashScope and OpenAI-compatible providers require their respective configured API-key variables.
- `SECURITY_SECRET_KEY` and `SECURITY_CORS_ORIGINS`; production requires a non-default secret and explicit non-localhost CORS origins.
- `MONITORING_METRICS_ENABLED=false`; when enabled, Prometheus startup uses the configured metrics port (default 9090).

Configuration loads `.env.local` with environment variables taking the usual settings precedence (`.env.example`, `src/shared/infrastructure/config/settings_base.py`, `src/shared/infrastructure/config/settings.py`, `src/shared/infrastructure/config/settings_sections.py`). SQLite connections enable foreign keys and WAL mode (`src/contexts/studio/infrastructure/database.py`).

For a containerized deployment, set a real `SECURITY_SECRET_KEY` and run:

```powershell
docker compose up --build
```

Compose mounts the named `novel-studio-data` volume at `/app/data`, maps host port 8000 to the service, and configures a readiness health check (`compose.yaml`).

## Migration and backup preparation

Before upgrading an existing installation, stop the running service and make an explicit backup:

```powershell
uv run novel-engine backup
```

For a file-backed SQLite database, this creates an online backup under a sibling `backups/` directory with a timestamped `.bak` filename. It does nothing when the database does not yet exist and rejects a database configuration that is not file-backed SQLite (`src/contexts/studio/infrastructure/database.py`, `src/apps/cli/novel_engine.py`).

The operational CLI prepares the database before `serve`, `import`, and `doctor`: it backs up an existing file-backed SQLite store and runs Alembic upgrades through `head`. Therefore, review the backup output and keep a copy before invoking those commands on an upgrade. The FastAPI lifespan only opens/initializes the runtime with schema creation and backup disabled; it is not the migration mechanism (`src/apps/cli/novel_engine.py`, `src/apps/api/runtime.py`).

Legacy workspace import expects `story.yaml` and may include `manuscript/chapters/chapter-*.md`. Create the Owner first, then run:

```powershell
uv run novel-engine import --source path/to/legacy-workspace --owner <username>
```

The importer is documented as not modifying its source workspace (`src/apps/cli/novel_engine.py`).

The web import API has a narrower boundary than the Owner CLI: its `source` value must name a real directory already below `data/imports`. Absolute paths, `..` traversal/path separators, symbolic links, and files are rejected; preview and import use the same check (`src/contexts/studio/interface/http/workflow_router.py`, `openspec/specs/novel-studio/spec.md`).

## Health and operational checks

With the service running, use:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health/live
Invoke-WebRequest http://127.0.0.1:8000/health/ready
Invoke-WebRequest http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8000/version
uv run novel-engine doctor
```

- `/health/live` returns liveness without querying SQLite.
- `/health/ready` checks the authoritative SQLite store and returns HTTP 503 when it is unavailable.
- `/health` returns the detailed database component status.
- `/version` returns the application version, Python version, environment, and `BUILD_SHA` when present.
- `doctor` runs the CLI preparation step, then reports SQLite `quick_check`, WAL journal mode, foreign-key status, database path, and whether an Owner exists.

These endpoints and the doctor output are defined in `src/apps/api/health.py` and `src/apps/cli/novel_engine.py`.

## Quick validation

For a focused local check after a frontend Studio change:

```powershell
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend type-check
corepack pnpm --dir frontend test:unit
corepack pnpm --dir frontend build
corepack pnpm --dir frontend test:e2e:smoke
```

The smoke suite starts its own backend on a free loopback port and Vite on `127.0.0.1:4273`, using a test SQLite data directory and the mock LLM provider (`frontend/scripts/start-e2e-stack.mjs`, `frontend/playwright.config.ts`).

The Studio Playwright workflow also exercises the 1440, 1024, 949, 900, 800, and 375px viewports, checking editor-first ordering, no horizontal overflow, route-specific Export/History surfaces, APG tab keys, visible busy/disabled states, and reduced-motion behavior (`frontend/tests/e2e/studio.spec.ts`).

For a focused backend check:

```powershell
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
uv run python scripts/qa/check_openapi_snapshot.py
```

`just validate` and `make validate` are available shortcuts, but they cover different subsets of checks; neither is documented here as a complete project gate. Use the commands above or follow the CI workflow when reproducing its full validation sequence (`justfile`, `Makefile`, `.github/workflows/ci.yml`).

For the release-equivalent local gate, run the same layers as CI:

```powershell
uv run python scripts/ai/regression_check.py --skip-file-count
uv run python scripts/qa/check_ssot.py
uv run python scripts/qa/check_repo_hygiene.py
uv run python scripts/qa/check_file_sizes.py
corepack pnpm spec:validate
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run bandit -r src
uv run mypy src tests
uv run lint-imports
uv run coverage run -m pytest -q
uv run coverage report --fail-under=88
uv run python scripts/qa/check_openapi_snapshot.py
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend format:check
corepack pnpm --dir frontend type-check
corepack pnpm --dir frontend test:unit
corepack pnpm --dir frontend build
corepack pnpm --dir frontend test:e2e:smoke
```

CI additionally runs React Doctor, a container persistence/deep-link smoke, and CodeQL; inspect `.github/workflows/ci.yml` and `.github/workflows/codeql.yml` when reproducing hosted gates. Treat any audit result as a baseline and rerun the full gate after source changes.
