# PROJECT AUDIT REPORT: Novel-Engine / Novel Studio 0.3.0
**Auditor:** Linus-Style Project Auditor  
**Date:** 2026-06-16  
**Verdict:** 🟡 NEEDS WORK  
**Overall Score:** 58/100

## Executive Summary (The Linus Rant)

Look, the tests pass. The main user flow—write a project, ask the AI for a proposal, export the result—actually works. That puts this project head and shoulders above the usual hipster trash I have to review. Someone cared enough to build a real domain model, wire up SQLAlchemy 2.0, add CSRF, rate limiting, and a passing test suite. So it is not garbage.

But it is **not acceptable either**.

The single biggest problem is that this codebase lies to you. `AUDIT_REPORT.md` claims "zero remaining technical debt" while **thousands of lines of dead infrastructure rot on disk**: an entire outbox module, a circuit-breaker package, a generic health framework, a YAML config loader, and a Result-monad error handler that nobody imports. That is not "debt-free"; that is a cemetery with air-freshener sprayed on it.

The second problem is that the project swallows errors like a black hole. Critical paths catch bare `Exception`, log nothing useful, and persist "failed" jobs. You will discover problems only when users complain, because the code is too polite to crash.

The third problem is scale—and I do not mean "will it handle a million users." I mean **developer scale**. `services.py` is 1,962 lines. `repository.py` is 1,208 lines. `StudioPage.tsx` is 933 lines of React god-component. No AI guidance exists. A new contributor—or an AI—will touch one thing and break three others.

If this PR crossed my desk, I would not NAK it outright. I would send it back with a short list of critical fixes and a strongly worded lecture about honesty in documentation.

## Critical Findings (Fix These First or NAK)

| # | Issue | File/Location | Severity | Dimension | Fix Hint |
|---|-------|---------------|----------|-----------|----------|
| 1 | FTS5 search query is escaped only for double quotes; user input reaches SQLite FTS5 MATCH syntax | `src/contexts/studio/application/services.py:608` | CRITICAL | Security | Use a strict token allow-list or SQLite `quote()`-style sanitization; add malicious-input tests |
| 2 | `create_ai_proposal` catches bare `Exception`, persists a "failed" job, and swallows the traceback | `src/contexts/studio/application/services.py:1039` | CRITICAL | Error Handling | Catch only provider/HTTP/domain errors; log full traceback; let unexpected exceptions bubble |
| 3 | `retry_job` catches bare `Exception` and persists failure string, hiding real bugs | `src/contexts/studio/application/services.py:1282` | CRITICAL | Error Handling | Narrow exception types; do not turn programming errors into persisted job failures |
| 4 | `StudioDatabase()` singleton instantiated at module import time | `src/contexts/studio/infrastructure/database.py:136` | CRITICAL | Architecture | Replace with factory; instantiate only after config is ready |
| 5 | FastAPI app created at module import time, wiring settings and store on `import` | `src/apps/api/main.py:282` | CRITICAL | Architecture | Expose `create_application()` factory; call it only from `main()` / tests |
| 6 | Default LLM provider is `dashscope`, but all docs and Docker say `mock`; unconfigured default is advertised as default | `src/shared/infrastructure/config/settings.py:247` | CRITICAL | Doc-Project Consistency | Change code default to `mock`; align `LLM_MODEL` with docs |
| 7 | Entire `src/events/outbox.py` (440 lines) is dead, misleading, and references a retired "simulation engine" | `src/events/outbox.py` | CRITICAL | Dead Code | Delete or archive; update `AUDIT_REPORT.md` |
| 8 | `StudioPage.tsx` is a 933-line god component with ~20 states and ~15 effects | `frontend/src/features/studio/StudioPage.tsx` | CRITICAL | Code Quality | Split into `EditorPane`, `Navigator`, `Inspector`, `SearchPanel`, custom hooks |
| 9 | `services.py` facade is still 1,962 lines of delegation after claimed refactor | `src/contexts/studio/application/services.py` | CRITICAL | Architecture | Split into per-service modules; make the facade thin or remove it |
| 10 | `src/shared/interface/http/error_handlers.py` and `src/shared/application/result.py` are unused but documented as active | `src/shared/interface/http/error_handlers.py`, `src/shared/application/result.py` | CRITICAL | Dead Code | Delete or adopt consistently |

## Detailed Findings by Dimension

### 1. Functional Completeness

- **Finding F1:** Missing project and document delete endpoints.
  - **Evidence:** Verified route list in `src/contexts/studio/interface/http/router.py` lacks `DELETE /api/projects/{id}` and `DELETE /api/projects/{id}/documents/{id}`.
  - **Why it matters:** A content-management app that cannot delete its core entities is incomplete. Users will accumulate junk projects forever.
  - **Fix direction:** Add delete endpoints with ownership checks and cascade rules.

- **Finding F2:** Import CLI exists but is undocumented and requires a magic `story.yaml` legacy layout.
  - **Evidence:** `src/apps/cli/novel_engine.py` import command; `examples/demos/` only contains unrelated stale demos.
  - **Why it matters:** A CLI feature that fails cryptically unless you know an undocumented schema is not a feature.
  - **Fix direction:** Document the legacy workspace format or remove the import command until it has a real UX.

- **Finding F3:** Broken demo script `demo_chronicler_integration.py` imports `src.agents.chronicler_agent`, which does not exist.
  - **Evidence:** `examples/demos/demo_chronicler_integration.py:18`.
  - **Why it matters:** Committed examples that crash on first run make the project look abandoned.
  - **Fix direction:** Delete the demo or fix the import.

- **Finding F4:** Health check framework is over-designed and unused; only a hardcoded DB `SELECT 1` is wired.
  - **Evidence:** `src/shared/infrastructure/health/health_checker.py` unused; `src/apps/api/health.py` is the only wired implementation.
  - **Why it matters:** Dead abstractions create the illusion of operational maturity.
  - **Fix direction:** Delete the generic framework or replace `health.py` with it.

### 2. Functional Availability

- **Finding F5:** README is 35 lines and omits first-time setup essentials: `.env.local`, owner setup, LLM config, tests, Docker env vars.
  - **Evidence:** `README.md`.
  - **Why it matters:** A user can start the server but cannot authenticate or use AI without reading source.
  - **Fix direction:** Expand README with copy-paste setup steps and env var table.

- **Finding F6:** `docker compose up --build` fails out of the box because `SECURITY_SECRET_KEY` is required but README does not mention it.
  - **Evidence:** `compose.yaml:16` uses `${SECURITY_SECRET_KEY:?Set SECURITY_SECRET_KEY}`; `README.md` Docker instruction is one line.
  - **Why it matters:** Docker is supposed to be the easy path. Right now it is the trap door.
  - **Fix direction:** Document required env vars before the Docker command.

- **Finding F7:** CLI `--help` crashes in production mode without secrets.
  - **Evidence:** `APP_ENVIRONMENT=production uv run novel-engine --help` raises pydantic validation error.
  - **Why it matters:** Help should never require configuration.
  - **Fix direction:** Defer settings validation until a command actually runs; use lazy factories.

- **Finding F8:** Default LLM provider is `dashscope`, which is unconfigured by default, while docs claim `mock`.
  - **Evidence:** `src/shared/infrastructure/config/settings.py:247` vs `.env.example` and `README.md`.
  - **Why it matters:** The advertised default will fail for every new user.
  - **Fix direction:** Default to `mock` and document how to switch providers.

- **Finding F9:** `make` is referenced but unavailable on Windows; `pre-commit` and `trunk` are not installed by dependency sync.
  - **Evidence:** UserSim report.
  - **Why it matters:** Contributors on Windows or minimal environments cannot run the documented quality gates.
  - **Fix direction:** Document cross-platform alternatives; add `pre-commit` and `trunk` as dev deps or remove the configs.

- **Finding F10:** `MONITORING_METRICS_ENABLED` defaults to `true` in code but `false` in `.env.example`; fresh dev runs bind port 9090 and can fail.
  - **Evidence:** `settings.py:382` vs `.env.example`.
  - **Why it matters:** Silent port conflicts on startup are classic "works on my machine."
  - **Fix direction:** Align defaults; consider disabling metrics by default in dev.

### 3. Comments & Documentation

- **Finding D1:** `AUDIT_REPORT.md` claims "zero remaining technical debt" while massive dead code remains.
  - **Evidence:** `AUDIT_REPORT.md` vs. `src/events/outbox.py`, `src/shared/interface/http/`, `src/shared/infrastructure/circuit_breaker/`.
  - **Why it matters:** Lying documentation is worse than no documentation.
  - **Fix direction:** Rewrite `AUDIT_REPORT.md` honestly or remove the false claim.

- **Finding D2:** Dead modules contain elaborate docstrings describing active behavior.
  - **Evidence:** `src/events/outbox.py`, `src/shared/interface/http/error_handlers.py`, `src/shared/infrastructure/config/loader.py`.
  - **Why it matters:** Comments that describe code nobody calls are traps for future maintainers.
  - **Fix direction:** Delete the modules or rewrite docstrings to say "UNUSED — pending removal."

- **Finding D3:** No `TODO`, `FIXME`, `XXX`, or `HACK` markers, but the dead modules themselves are silent technical debt.
  - **Evidence:** Grep found none in `src/` or `frontend/src/`.
  - **Why it matters:** The absence of markers does not mean the absence of debt; it means debt is unlabeled.
  - **Fix direction:** Label dead code explicitly or remove it.

- **Finding D4:** `settings.py` comment on `DEFAULT_SECRET_KEY` implies simple override; production actually rejects the default.
  - **Evidence:** `src/shared/infrastructure/config/settings.py:17`.
  - **Why it matters:** Misleading comments cause 3 AM debugging sessions.
  - **Fix direction:** Rewrite the comment to describe the production validator and dev auto-generation.

- **Finding D5:** `metrics_middleware.py` comment says "Metrics server should be started separately"; it is actually started in FastAPI lifespan.
  - **Evidence:** `src/shared/infrastructure/middleware/metrics_middleware.py:15`.
  - **Why it matters:** Comments that contradict implementation are lies.
  - **Fix direction:** Fix the comment or move the server.

- **Finding D6:** No `AGENTS.md`, `CHANGELOG.md`, or AI guidance exists.
  - **Evidence:** Project root.
  - **Why it matters:** A project at version 0.3.0 should have a changelog and contributor guidance.
  - **Fix direction:** Add both.

### 4. Code Quality

- **Finding Q1:** Bare `except Exception` is everywhere in production code, swallowing real bugs.
  - **Evidence:** `services.py:1039`, `services.py:1282`, `database.py:124`, `health_checker.py:243`, `loader.py:79`, `apps/api/health.py:56`, `metrics_middleware.py:83`, `logging_middleware.py:72`, `dashscope_text_generation_provider.py:613`, `openai_compatible_text_generation_provider.py:134`.
  - **Why it matters:** You cannot debug what you cannot see. Programming errors become silent "unhealthy" or "failed" states.
  - **Fix direction:** Catch specific exception families; let unexpected errors crash and be logged with tracebacks.

- **Finding Q2:** `StudioPage.tsx` is 933 lines and violates every principle of component design.
  - **Evidence:** `frontend/src/features/studio/StudioPage.tsx`.
  - **Why it matters:** God components are impossible to test, review, or modify safely.
  - **Fix direction:** Extract `EditorPane`, `Navigator`, `Inspector`, `SearchPanel`, `JobsPanel`, and hooks (`useProject`, `useAutosave`, `useAIProposal`).

- **Finding Q3:** `services.py` is a 1,962-line facade over services that are themselves too large.
  - **Evidence:** `src/contexts/studio/application/services.py`.
  - **Why it matters:** The "refactor" moved code around without actually splitting responsibility.
  - **Fix direction:** Create per-service modules (`project_service.py`, `document_service.py`, etc.) and a thin coordinator.

- **Finding Q4:** `_coerce_value_to_schema` has ~20 branches and 18 return statements.
  - **Evidence:** `src/contexts/ai/infrastructure/providers/dashscope_text_generation_provider.py:79`.
  - **Why it matters:** Untestable, unreadable, and a bug factory for LLM output coercion.
  - **Fix direction:** Decompose into type-specific coercers with a registry.

- **Finding Q5:** `dashscope_text_generation_provider.py` falls back to `ast.literal_eval` on untrusted LLM output.
  - **Evidence:** `src/contexts/ai/infrastructure/providers/dashscope_text_generation_provider.py:502-510`.
  - **Why it matters:** Even "safe" eval is the wrong tool for remote data; malformed payloads pass through silently.
  - **Fix direction:** Fail on non-JSON output or use a strict, auditable JSON repair utility.

- **Finding Q6:** Ruff config is intentionally minimal and gives a false sense of quality.
  - **Evidence:** `pyproject.toml:117` selects only `E4/E7/E9/F/I`.
  - **Why it matters:** Complexity, broad exceptions, security, prints, and dead code are all disabled.
  - **Fix direction:** Add `C90`, `BLE`, `S`, `T20`, `ARG`, `PLR`, `SIM`, `UP`, `B`; fix or explicitly ignore with reasons.

- **Finding Q7:** Mypy errors exist in tests; CI likely runs `mypy src` only.
  - **Evidence:** UserSim/CodeGrinder report 7 errors in `tests/`.
  - **Why it matters:** Claiming strict mypy while exempting tests is hypocrisy.
  - **Fix direction:** Fix test types or explicitly exclude tests with documented justification; run `mypy src tests` in CI.

- **Finding Q8:** `AsyncClient` is lazily created and never explicitly closed.
  - **Evidence:** `src/contexts/ai/infrastructure/providers/dashscope_text_generation_provider.py:319-330`.
  - **Why it matters:** Resource leaks under load.
  - **Fix direction:** Use context managers or lifespan hooks and call `aclose()`.

- **Finding Q9:** Export hashing reads the entire file into memory.
  - **Evidence:** `src/contexts/studio/application/services.py:817`.
  - **Why it matters:** Large exports OOM the process.
  - **Fix direction:** Stream the file through SHA-256.

- **Finding Q10:** Copy-paste duplication in transport classes, job persistence, and retry handlers.
  - **Evidence:** CodeGrinder DRY findings.
  - **Why it matters:** Duplication means fixes happen in the wrong place.
  - **Fix direction:** Extract shared helpers and registries.

### 5. Architecture

- **Finding A1:** Module-level singletons for database and app prevent configuration injection and test isolation.
  - **Evidence:** `src/contexts/studio/infrastructure/database.py:136`, `src/apps/api/main.py:282`.
  - **Why it matters:** Tests have to hack `sys.modules` to reset state.
  - **Fix direction:** Use factories and dependency injection; never create stateful objects at import time.

- **Finding A2:** Several packages exist only as architectural fiction.
  - **Evidence:** `src/events/outbox.py`, `src/shared/interface/http/`, `src/shared/infrastructure/circuit_breaker/`, `src/shared/infrastructure/health/checks/`, `src/shared/infrastructure/config/loader.py`, `src/apps/workers/`.
  - **Why it matters:** They bloat the codebase and confuse everyone.
  - **Fix direction:** Delete or wire them into real behavior.

- **Finding A3:** `src/shared/application/result.py` Result monad is unused except by an unused error handler.
  - **Evidence:** CodeGrinder dead-code findings.
  - **Why it matters:** Carrying a 406-line abstraction nobody uses is premature abstraction hell.
  - **Fix direction:** Adopt it everywhere or delete it.

- **Finding A4:** `StudioStore` proxy uses `__getattr__` to hide real dependencies.
  - **Evidence:** `src/contexts/studio/application/services.py`.
  - **Why it matters:** Untyped, magic forwarding makes the code hard to reason about and refactor.
  - **Fix direction:** Inject concrete services into routers/handlers.

- **Finding A5:** Frontend has only 12 source files and 1 unit test file for a complex SPA.
  - **Evidence:** Scout report.
  - **Why it matters:** The UI architecture cannot support growth.
  - **Fix direction:** Split features into folders with co-located tests.

### 6. Documentation-Project Consistency

- **Finding C1:** Default LLM provider/model in code do not match `.env.example`, Docker, or README.
  - **Evidence:** `settings.py:247-250` vs `.env.example`.
  - **Why it matters:** The first-run experience is broken by default.
  - **Fix direction:** Align all defaults to `mock` and `studio-copilot-v1`.

- **Finding C2:** `config/env/.env.example` documents many settings the code ignores.
  - **Evidence:** `MONITORING_ENABLED`, `MONITORING_TRACING_ENABLED`, `HEALTH_TIMEOUT_SECONDS`, `LOG_FILE_PATH`, `LOG_MAX_BYTES`, `API_WORKERS`, `APP_DEBUG`, `DB_POOL_SIZE`, etc.
  - **Why it matters:** The env template is a wish list, not a contract.
  - **Fix direction:** Remove dead vars or implement them.

- **Finding C3:** Frontend env vars (`VITE_API_BASE_URL`, `VITE_API_TIMEOUT`, `VITE_API_PROXY_TARGET`) are undocumented.
  - **Evidence:** `frontend/src/app/config.ts`, `frontend/vite.config.ts`.
  - **Why it matters:** Frontend developers have to read Vite config to know how to point at the API.
  - **Fix direction:** Add a frontend `.env.example` and README section.

- **Finding C4:** Two `.env.example` files exist with different content.
  - **Evidence:** `.env.example` (root) and `config/env/.env.example`.
  - **Why it matters:** Users do not know which is authoritative.
  - **Fix direction:** Consolidate into one canonical template.

- **Finding C5:** OpenAPI snapshot is accurate and routes match implementation.
  - **Evidence:** DocDetective verified route lists.
  - **Why it matters:** This is the one area where documentation is honest.
  - **Fix direction:** Keep it up to date automatically in CI.

- **Finding C6:** `.envrc` references `CODEX_HOME` for a `.codex` directory that does not exist.
  - **Evidence:** `config/env/.envrc`.
  - **Why it matters:** Leftover from another project.
  - **Fix direction:** Remove or fix.

### 7. AI-Friendliness

- **Finding AI1:** No `AGENTS.md`, `CLAUDE.md`, `AI_CONTEXT.md`, or `.cursorrules` exists.
  - **Evidence:** AICoder report.
  - **Why it matters:** An AI has to reverse-engineer Clean Architecture, the proxy singleton, SSOT checks, and the toolchain.
  - **Fix direction:** Add `AGENTS.md` covering architecture, test commands, and hidden guardrails.

- **Finding AI2:** Backend files exceed any reasonable context window.
  - **Evidence:** `services.py` 1,962 lines, `repository.py` 1,208 lines.
  - **Why it matters:** An AI cannot keep the whole contract in context when editing.
  - **Fix direction:** Split into modules under 300 lines.

- **Finding AI3:** Global `studio_store` proxy singleton is a hidden convention.
  - **Evidence:** `src/contexts/studio/application/services.py`.
  - **Why it matters:** Easy for an AI to call before configuration and get cryptic runtime errors.
  - **Fix direction:** Document it as legacy; inject dependencies in new code.

- **Finding AI4:** Frontend `StudioPage.tsx` is a 933-line trap for AI edits.
  - **Evidence:** `frontend/src/features/studio/StudioPage.tsx`.
  - **Why it matters:** AI will "successfully" edit it while subtly breaking one of many side effects.
  - **Fix direction:** Decompose into hooks and components with isolated tests.

- **Finding AI5:** Hidden CI guardrails (`check_ssot.py`, `check_repo_hygiene.py`, `check_openapi_snapshot.py`) can fail even when tests pass.
  - **Evidence:** `scripts/qa/`.
  - **Why it matters:** An AI can pass tests and still break `make validate`.
  - **Fix direction:** Document these checks in `AGENTS.md` and provide a single offline validation command.

## The Fix Roadmap (For the Repair AI)

### Phase 1 (Critical)
1. Harden `DocumentService.search` FTS5 query building against injection.
2. Replace bare `except Exception` in `create_ai_proposal`, `retry_job`, and other production paths with specific exception types.
3. Remove module-level singletons for `StudioDatabase` and FastAPI `app`; use factories.
4. Change `LLMSettings.provider` default to `mock`; align `LLM_MODEL` with docs.
5. Delete or archive dead modules: `src/events/outbox.py`, `src/shared/interface/http/`, `src/shared/infrastructure/circuit_breaker/`, `src/shared/infrastructure/health/checks/`, `src/shared/infrastructure/config/loader.py` + YAML examples, empty `cache/`, `policies/`, `workers/`.
6. Delete broken demo `examples/demos/demo_chronicler_integration.py`.
7. Make CLI `--help` work in production without secrets (lazy settings validation).

### Phase 2 (Major)
1. Split `services.py` into per-service modules with a thin facade.
2. Split `repository.py` into focused query/command classes or modules.
3. Decompose `StudioPage.tsx` into components and custom hooks with tests.
4. Fix or delete the `result.py` monad and unused error handlers.
5. Add delete endpoints for projects and documents.
6. Document or remove the import CLI until it has a real UX.
7. Consolidate `.env.example` files and remove dead env vars.
8. Document frontend env vars and Vite dev workflow in README.
9. Fix mypy errors in tests and run `mypy src tests` in CI.
10. Widen ruff ruleset and fix or explicitly justify suppressions.

### Phase 3 (Polish)
1. Add `AGENTS.md` and `CHANGELOG.md`.
2. Rewrite `AUDIT_REPORT.md` honestly in English.
3. Add a file-size CI gate (~300 lines).
4. Close `AsyncClient` resources, use streaming SHA-256 for exports, and atomic file writes.
5. Clean `pyproject.toml` Black target versions and coverage omit list.
6. Remove committed `.coverage` and SQLite databases from repo.
7. Vendor or pin SRI hashes for Swagger UI assets.
8. Add unit tests for frontend features beyond `api.test.ts`.

## Linus' Final Words

This project is not hopeless. The tests pass, the domain model is sane, and someone clearly gave a damn about architecture. But **giving a damn is not enough**.

You cannot claim "zero technical debt" while dragging a graveyard of unused modules behind you. You cannot call yourself "well-tested" when your lint config deliberately ignores complexity and security. And you cannot expect real users—or AIs—to navigate a 933-line React component and a 1,962-line Python facade without breaking something.

Fix the critical issues first. Be honest about what is dead. Stop swallowing exceptions. Then we can talk about whether this is acceptable.

Now get to work.
