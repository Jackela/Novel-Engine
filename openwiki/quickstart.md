# Novel Engine quickstart

Novel Engine **0.4.0** is a self-hosted, single-author writing studio. The authoritative store is SQLite, with repository documentation and configuration kept in version-controlled text files. The application requires **Node.js 24+**; the committed tooling specifies **pnpm 11.6.0**, and CI runs the server on Node 24 with the SPA workflow on Node 22 (`server/package.json`, `package.json`, `.github/workflows/ci.yml`). The Python stack of 0.3.x is retired at git tag `python-final`.

This page covers local operation, migration preparation, and the fastest checks after a change. The product specification is `openspec/specs/novel-engine/spec.md`.

## Install and start

The application reads `.env.local`; begin from the non-secret template rather than committing credentials. OS-specific commands are shown for both PowerShell (Windows) and POSIX shells (macOS/Linux); the `pnpm` commands are identical on both:

```powershell
Copy-Item .env.example .env.local
pnpm install --frozen-lockfile
pnpm --dir frontend build
pnpm --dir server build
pnpm --dir server cli serve
```

macOS/Linux equivalent:

```bash
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm --dir frontend build
pnpm --dir server build
pnpm --dir server cli serve
```

`serve` uses `API_HOST` and `API_PORT` unless overridden with `--host` and `--port`; the template defaults to `0.0.0.0:8000` (`.env.example`, `server/src/apps/cli/main.ts`). The TS server serves the built SPA assets and deep-link routes from `frontend/dist` and answers API routes under `/api` plus `/health/*` and `/version` (`server/src/shared/interface/http/spa_serving.ts`, `server/src/apps/api/app.ts`). Browse to `http://127.0.0.1:8000`.

For frontend-only development, run the backend above in one terminal and Vite in another:

```powershell
pnpm --dir frontend dev
```

Vite listens on port **5173** and proxies `/api` to `VITE_API_PROXY_TARGET`, which defaults to `http://127.0.0.1:8000`; proxy request timeouts are five minutes (`frontend/vite.config.ts`, `frontend/.env.example`). Keep `VITE_API_BASE_URL` empty to use relative `/api` requests through that proxy. If it is set, the frontend sends requests to that explicit base URL instead (`frontend/src/app/config.ts`, `frontend/src/app/api.ts`).

## First session

On a new database, the entry screen creates the local Owner account. Keep an unauthenticated service on loopback or a private network until this first setup is complete. The unauthenticated `POST /api/setup` compares every supplied `Origin` and `Referer` with the serving origin or an explicit configured non-wildcard CORS origin (or a supported localhost/127.0.0.1 port wildcard), rejecting cross-site requests with `403`; requests without browser origin metadata remain available to local bootstrap clients. Once an Owner exists, concurrent setup has one `201` winner and controlled `422` responses for later attempts. The API exposes setup state at `GET /api/setup` (`server/src/contexts/studio/interface/http/`).

The browser client uses cookie sessions (`novel_engine_session`) and sends credentials with API requests. Mutating requests include the `X-CSRF-Token` copied from the `novel_engine_csrf` cookie; setup, login, and guest-session creation are the explicit CSRF exemptions (`server/src/contexts/studio/interface/http/`, `frontend/src/app/api.ts`). Error responses use the unified envelope `{ "error": { code, message, details } }`. Guest sessions are 24-hour sandboxes isolated from Owner data; do not treat guest work as permanent.

Session tokens are HMAC-derived values keyed by the injected `SECURITY_SECRET_KEY`. In production and staging a non-default secret is mandatory; an unset secret rotates per start and invalidates sessions. Rotate the key as an intentional logout event (`server/src/shared/infrastructure/config/server_config.ts`).

## Studio routes

Inside a project, `/projects/:projectId/:section?` is route-driven. `review`, `history`, `export`, and `settings` each render their own project-level surface; History contains revision history only, while Export contains Markdown/DOCX/EPUB format actions, pending/error state, and recent export links. The top bar contains project identity and navigation only, so Review, Export, and Settings are not duplicated in a second menu (`frontend/src/features/studio/StudioPage.tsx`, `StudioTopbar.tsx`, `StudioInspector.tsx`).

The Studio keeps the editor first at tablet and phone widths. At 821–949px it switches to one column with the editor before navigation and Inspector; the same ordering is retained below 820px. Navigation and Inspector regions use accessible disclosure controls, icon/reorder controls are at least 44px square, and the supported layouts avoid horizontal overflow (`frontend/src/index.css`, `frontend/src/features/studio/StudioNavigator.tsx`, `StudioInspector.tsx`).

## Configuration and persistence

`.env.example` is the canonical configuration reference. Its important local defaults are:

- `DB_URL=sqlite:///./data/novel-engine.sqlite3`; only self-hosted SQLite URLs are accepted.
- `API_HOST=0.0.0.0`, `API_PORT=8000`.
- `LLM_PROVIDER=mock` and `LLM_MODEL=studio-copilot-v1`; DashScope and OpenAI-compatible providers require their respective configured API-key variables.
- `SECURITY_SECRET_KEY` and `SECURITY_CORS_ORIGINS`; production requires a non-default secret and explicit non-localhost CORS origins.
- `SECURITY_RATE_LIMIT=5/minute` for the authentication endpoints.

Configuration loads `.env.local` with process environment variables taking precedence (`server/src/shared/infrastructure/config/server_config.ts`). SQLite connections enable foreign keys and WAL mode (`server/src/shared/infrastructure/db/`).

For a containerized deployment, set a real `SECURITY_SECRET_KEY` and run:

```powershell
docker compose up --build
```

Compose mounts the named `novel-engine-data` volume at `/app/data`, maps host port 8000 to the single service, and configures a readiness health check on `/health/ready` (`compose.yaml`, `Dockerfile`).

## Migration and backup preparation

Before upgrading an existing 0.3.x installation, stop the running service and keep an explicit copy of the old `data/` directory (or run the old stack's `backup` command once). The 0.4.0 cutover is an empty-database switch by design: the TS server refuses to open a Python-era database file, so start 0.4.0 with a fresh data directory, create the Owner account, then re-import legacy workspaces (below). Data written after the cutover does not survive a rollback to the Python stack — this one-way door is stated in the v0.4.0 release notes.

The operational CLI prepares the database before `serve`: it backs up an existing file-backed SQLite store, applies Drizzle migrations, and recovers interrupted jobs (`server/src/shared/infrastructure/db/startup.ts`).

Legacy workspace import expects `story.yaml` and may include `manuscript/chapters/chapter-*.md`. Create the Owner first, then run:

```powershell
pnpm --dir server cli import --source path/to/legacy-workspace --owner <username>
```

The importer is read-only against its source and idempotent per principal (`server/src/apps/cli/legacy_import_command.ts`).

## Health and operational checks

With the service running, use:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health/live
Invoke-WebRequest http://127.0.0.1:8000/health/ready
Invoke-WebRequest http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8000/version
pnpm --dir server cli doctor
```

macOS/Linux equivalent (`curl -f` fails on non-2xx responses, matching `Invoke-WebRequest`'s behavior on error statuses):

```bash
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/version
pnpm --dir server cli doctor
```

- `/health/live` returns liveness without querying SQLite.
- `/health/ready` checks the authoritative SQLite store and returns HTTP 503 when it is unavailable.
- `/health` returns the detailed database component status.
- `/version` returns the application version, the Node runtime version, the environment, and `BUILD_SHA` when present.

These endpoints and the doctor output are defined in `server/src/apps/api/app.ts` and `server/src/apps/cli/main.ts`.

## Quick validation

For a focused local check after a frontend Studio change:

```powershell
pnpm --dir frontend lint
pnpm --dir frontend type-check
pnpm --dir frontend test:unit
pnpm --dir frontend build
pnpm --dir frontend test:e2e:smoke
```

The e2e suites start their own TS backend through the emitted CLI on a free loopback port, using a fresh temporary SQLite data directory and the mock LLM provider (`frontend/scripts/start-ts-e2e-stack.mjs`, `frontend/playwright.ts.config.ts`).

The Studio Playwright workflow also exercises the 1440, 1024, 949, 900, 800, and 375px viewports, checking editor-first ordering, no horizontal overflow, route-specific Export/History surfaces, APG tab keys, visible busy/disabled states, and reduced-motion behavior (`frontend/tests/e2e-ts/`).

For a focused backend check:

```powershell
pnpm --dir server type-check
pnpm --dir server lint
pnpm --dir server test
pnpm --dir server gates
```

`just validate` and `make validate` are available shortcuts, but they cover a subset of checks; neither is documented here as a complete project gate. Use the commands above or follow the CI workflow when reproducing its full validation sequence (`justfile`, `Makefile`, `.github/workflows/ci.yml`).

For the release-equivalent local gate, run the same layers as CI:

```powershell
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
pnpm --dir frontend test:e2e:ts
```

CI additionally runs the API-types drift check, React Doctor, a container persistence/deep-link smoke, and CodeQL; inspect `.github/workflows/ci.yml` and `.github/workflows/codeql.yml` when reproducing hosted gates. Treat any audit result as a baseline and rerun the full gate after source changes.
