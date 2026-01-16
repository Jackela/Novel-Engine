# Golden Standard Template Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate warnings/skips, wire real Postgres with in-process fakes, and make tests/builds clean with a single canonical config source.

**Architecture:** Hybrid testing with real Postgres (Docker Compose), in-memory fakes for Kafka/LLM, and deterministic SSE testing. Pytest config lives only in `pyproject.toml`. NPM warnings are removed via `.npmrc` plus dependency overrides when needed.

**Tech Stack:** Python 3.11, pytest, FastAPI, Docker Compose, Node.js, npm, TypeScript.

### Task 1: Canonicalize pytest config (remove pytest.ini)

**Files:**
- Modify: `pyproject.toml`
- Remove: `pytest.ini`

**Step 1: Move pytest.ini config into pyproject**
Copy the `pytest.ini` settings into `[tool.pytest.ini_options]` in `pyproject.toml`:
- `testpaths`, `python_files`, `python_classes`, `python_functions`
- `addopts` (include junitxml path)
- `timeout` + `timeout_method`
- `filterwarnings`
- `markers`

**Step 2: Delete pytest.ini**
Remove `pytest.ini` entirely.

**Step 3: Run pytest config check**
Run: `pytest --help | Select-String -Pattern "ini-options"`
Expected: pytest reads settings from `pyproject.toml` without warning.

**Step 4: Commit**
```bash
git add pyproject.toml pytest.ini
git commit -m "chore: consolidate pytest config into pyproject"
```

### Task 2: Hybrid infra – real Postgres + in-process fakes

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/helpers/postgres.py`
- Create: `src/contexts/ai/infrastructure/providers/mock_llm_provider.py`
- Modify: `src/core/event_bus.py` (or `src/contexts/shared/`)

**Step 1: Add Postgres test helper**
Implement a helper to:
- start Postgres using `docker compose -f docker/docker-compose.yaml up -d postgres`
- wait for readiness (`pg_isready`)
- expose connection URL via env (e.g., `POSTGRES_URL`)
- teardown/cleanup when tests finish

**Step 2: Wire pytest fixture**
Add `postgres_service` fixture (session scope) in `tests/conftest.py` that:
- uses the helper
- fails fast if Docker unavailable (no skip)

**Step 3: Implement InMemoryEventBus**
Implement stateful fake:
- `publish(event)` stores to `history` and notifies subscribers
- `subscribe(topic)` returns iterable queue
- `replay(from_index)`
- `clear()` and `stats()` for assertions

**Step 4: Implement MockLLMProvider**
Provide:
- `calls` history (prompt, params, timestamp)
- `set_responses([...])` deterministic outputs
- failure injection and optional delay

**Step 5: Commit**
```bash
git add tests/conftest.py tests/helpers/postgres.py src/core/event_bus.py src/contexts/ai/infrastructure/providers/mock_llm_provider.py
git commit -m "test: add hybrid infra with postgres + in-process fakes"
```

### Task 3: Remove skips by wiring fakes + missing endpoints

**Files:**
- Modify: `tests/test_ai_intelligence_integration.py`
- Modify: `tests/contract/knowledge/test_admin_api_contract.py`
- Modify: `tests/integration/knowledge/test_postgresql_repository.py`
- Modify: `tests/integration/test_world_api_integration.py`
- Modify: `tests/e2e/user_flows/test_world_building_flow.py`
- Modify: `apps/api/http/world_router.py`
- Modify: `src/api/main_api_server.py`

**Step 1: Replace skip guards**
Refactor tests to use the new fakes and Postgres fixture. Remove `pytest.mark.skip` and `pytest.skip` branches that were “TDD not implemented”.

**Step 2: Ensure world endpoints exist**
Implement missing world endpoints in `apps/api/http/world_router.py` and mount them in `src/api/main_api_server.py`.

**Step 3: Run targeted tests**
Run:
```
pytest tests/test_ai_intelligence_integration.py -v
pytest tests/integration/knowledge/test_postgresql_repository.py -v
pytest tests/integration/test_world_api_integration.py -v
pytest tests/e2e/user_flows/test_world_building_flow.py -v
```
Expected: all pass, no skips.

**Step 4: Commit**
```bash
git add tests/test_ai_intelligence_integration.py tests/contract/knowledge/test_admin_api_contract.py tests/integration/knowledge/test_postgresql_repository.py tests/integration/test_world_api_integration.py tests/e2e/user_flows/test_world_building_flow.py apps/api/http/world_router.py src/api/main_api_server.py
git commit -m "test: remove skips by wiring fakes and missing endpoints"
```

### Task 4: Fix SSE timeouts for tests

**Files:**
- Modify: `src/api/main_api_server.py`
- Modify: `tests/api/test_events_stream.py`

**Step 1: Add test interval override**
Read `SSE_EVENT_INTERVAL_MS` in the SSE generator when in testing mode and use it to control sleep.

**Step 2: Update tests to set interval**
Set env in test fixture and ensure the stream consumes a deterministic number of events, then closes cleanly.

**Step 3: Run SSE tests**
Run: `pytest tests/api/test_events_stream.py -v`
Expected: passes quickly without timeouts.

**Step 4: Commit**
```bash
git add src/api/main_api_server.py tests/api/test_events_stream.py
git commit -m "test: stabilize SSE timing for stream tests"
```

### Task 5: NPM warning cleanup + final verification

**Files:**
- Create: `.npmrc`
- Modify: `frontend/package.json`
- Modify: `package.json`
- Modify: `CLAUDE.md`

**Step 1: Add .npmrc**
Add `legacy-peer-deps=true` or explicit overrides.

**Step 2: Pin peer deps**
Use `overrides` in `frontend/package.json` to align `three` and `@monogrid/gainmap-js`.

**Step 3: Update metadata**
Update versions/authors in `pyproject.toml` + `package.json` as needed and add Ralph Loop details in `CLAUDE.md`.

**Step 4: Run validation**
Run:
```
pytest
cd frontend && npm run type-check
cd frontend && npm run lint:all
cd frontend && npm run build
```
Expected: all green, no warnings, no skips.

**Step 5: Commit**
```bash
git add .npmrc frontend/package.json package.json CLAUDE.md pyproject.toml
git commit -m "chore: align metadata and npm config for clean installs"
```
