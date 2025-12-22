## Route Inventory (FastAPI)

### Product API (canonical `/api/*`)
- `/api/auth/*` (register/login/refresh)
- `/api/characters/*`
- `/api/events/stream` (SSE)
- `/api/stories/*` (generate/status + WebSocket progress)
- `/api/narratives/*` and `/api/causality/*`
- `/api/context7/*`
- `/api/turns/*` and `/api/agents/*` (subjective reality)
- `/api/prompts/*`
- `/api/decision/*`
- `/api/orchestration/*`
- `/api/knowledge/*`

### Tooling / Observability API (monitoring service, not product clients)
- `/api/status`
- `/api/system`
- `/api/overview`
- `/api/dashboards/*`
- `/api/alerts/*`
- `/api/synthetic/*`
- `/api/logs/*`

### Non-product top-level (service health/ops)
- `/health`
- `/metrics`
- `/meta/system-status`

## `/api/v1` References Audit

### Must migrate (first-party product surface)
Completed migrations in code/docs/scripts so first-party clients use `/api/*` only:
- Code routes: `src/api/context7_integration_api.py`, `src/api/emergent_narrative_api.py`, `src/api/subjective_reality_api.py`
- Docs/templates/examples/scripts: `docs/REALTIME_PROGRESS_FEATURE.md`, `docs/PROJECT_DOCS.md`, `src/templates/enhanced_docs.html`, `scripts/performance_optimization.py`, `deploy/production/deploy.sh`
- OpenSpec (active change docs): `openspec/changes/enable-dashboard-live-api/*`, `openspec/changes/dashboard-data-routing-hygiene/*` (proposal/spec updated)

### Out of scope (third-party or historical)
These `/api/v1` occurrences are not part of the first-party product API surface:
- Third-party endpoints (Prometheus/Loki/Cortex): e.g. `/loki/api/v1/push`, `/api/v1/read`, `/api/v1/write`
- Kubernetes API proxy paths: e.g. `/api/v1/nodes/...`
- Archived OpenSpec history under `openspec/changes/archive/`
- Historical reversal note in `openspec/changes/dashboard-data-routing-hygiene/tasks.md` (documents the removal of versioned paths)
