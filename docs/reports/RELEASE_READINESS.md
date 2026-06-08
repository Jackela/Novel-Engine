# Release Readiness

Last reviewed: 2026-06-08

## Current Status

- `main` release head: `a6b9c177`
- GitHub CI: green on `main`
- CodeQL: green on `main`
- Code scanning open alerts: `0`
- Open PR queue: empty
- DashScope live UAT: accepted in workflow run `27112890876`
- Canonical evidence:
  - `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md`
  - `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json`

## Release Gate

The checked-in DashScope evidence is the current release acceptance baseline:

- target chapters: `20`
- drafted chapters: `20`
- export outcome: `exported`
- blockers: `0`
- export gate: `pass`

Before each release promotion, confirm the default branch still has green CI,
green CodeQL, `0` open code scanning alerts, and no unresolved dependency PRs.

## Deployment Surface

No deployment platform manifest is currently checked in. There is no `Dockerfile`,
`docker-compose.yml`, `vercel.json`, `fly.toml`, `render.yaml`, or `Procfile` in the
repository. Deployment validation is therefore configuration-first until a target
runtime is declared.

The backend runtime is the canonical FastAPI app in `src.apps.api.main:app`. The
frontend is a Vite build that expects its API origin from `VITE_API_BASE_URL`.

## Required Production Configuration

Production must not reuse `.env.example` defaults. Configure these in the real
deployment environment:

| Variable | Required value |
| --- | --- |
| `APP_ENVIRONMENT` | `production` |
| `SECURITY_SECRET_KEY` | Non-default high-entropy secret, never `change-me-*` |
| `DB_URL` | PostgreSQL URL, `postgresql://...` or `postgresql+asyncpg://...` |
| `SECURITY_CORS_ORIGINS` or `CORS_ALLOWED_ORIGINS` | Explicit HTTPS frontend origins only; no wildcard, localhost, or loopback origin |
| `API_DOCS_URL` | Non-default internal path or disabled |
| `API_REDOC_URL` | Non-default internal path or disabled |
| `API_OPENAPI_URL` | Non-default internal path or disabled |
| `APP_DATA_DIR` | Persistent writable storage for workspace manuscripts, artifacts, jobs, and exports |
| `VITE_API_BASE_URL` | Absolute HTTPS backend origin used by the deployed frontend |

The settings layer already rejects production startup when the secret is default,
the database is not PostgreSQL, CORS contains local/wildcard origins, or docs/OpenAPI
remain on default public paths.

## Provider Configuration

For DashScope-backed production writing:

| Variable | Required value |
| --- | --- |
| `LLM_PROVIDER` | `dashscope` |
| `DASHSCOPE_API_KEY` | Real DashScope API key |
| `DASHSCOPE_MODEL` | Optional model override; current accepted baseline used `qwen3.5-flash` |
| `DASHSCOPE_API_BASE` | Optional; default is DashScope native API base |
| `DASHSCOPE_TRANSPORT_MODE` | Optional; current accepted baseline uses `multimodal_generation` |
| `DASHSCOPE_REVIEW_MODEL` | Optional; defaults to the resolved DashScope model |
| `LLM_TIMEOUT` | Use a long enough provider timeout for chapter drafting; live UAT uses `180` seconds |
| `LLM_RETRY_ATTEMPTS` | Keep at least the default `3`; live UAT also has bounded chapter-level retry |

Optional OpenAI-compatible provider configuration remains supported through
`LLM_PROVIDER=openai_compatible`, `LLM_API_KEY`, `LLM_API_BASE`, and
`OPENAI_COMPATIBLE_MODEL`, but it was not the accepted live release baseline.

## Operational Checks

Run these before promoting a deployment:

```bash
uv lock --check
uv run pytest -q tests/apps/api/test_workspaces.py tests/apps/cli/test_novel_engine.py tests/scripts/test_run_dashscope_longform_uat.py tests/contract/test_text_generation_provider_contract.py tests/contexts/ai/infrastructure/test_text_generation_providers.py
npm --prefix frontend run type-check
npm --prefix frontend run audit:exports
```

After the environment is deployed:

- `GET /health/live` returns `200`.
- `GET /health/ready` returns `200` before accepting traffic.
- `GET /api/providers` shows the intended provider configured.
- Frontend auth/workspace flows use the deployed `VITE_API_BASE_URL`.
- A smoke workspace can be created, drafted, reviewed, and exported.
- Metrics exposure is intentionally configured if `MONITORING_METRICS_ENABLED=true`.

## Promotion Decision

Release code and evidence are ready as of `a6b9c177`. The remaining release risk is
external deployment configuration and platform operation, not repository code.
