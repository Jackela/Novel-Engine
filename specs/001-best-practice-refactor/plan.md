# Implementation Plan: Project Best-Practice Refactor

**Branch**: `001-best-practice-refactor` | **Date**: 2025-10-29 | **Spec**: [specs/001-best-practice-refactor/spec.md](../001-best-practice-refactor/spec.md)
**Input**: Feature specification from `/specs/001-best-practice-refactor/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Refactor the Novel Engine project toward the newly ratified constitution by (1) publishing a bounded-context blueprint with aggregates, ports, and anti-corruption layers; (2) aligning experience API contracts, workflow gates, and QA processes with contract-first and testing discipline; and (3) delivering observability, rollout, and incident operation playbooks so production reliability matches best practices.

## Technical Context

**Language/Version**: Backend — Python 3.11 (FastAPI); Frontend — TypeScript 5.4 (React 18); Infrastructure scripting — Bash/PowerShell  
**Primary Dependencies**: FastAPI, Pydantic v2, Uvicorn, HTTPX, SQLAlchemy, Redis (async client), Celery/RQ (background jobs), React 18, Vite 7, React Query, Playwright  
**Storage**: Simulation Orchestration — SQLite (current) with planned PostgreSQL migration; Persona Intelligence — Redis cache for prompt responses; Narrative Delivery — Markdown campaign logs persisted to filesystem/S3; Platform Operations — configuration via YAML + env overrides  
**Testing**: Pytest + pytest-asyncio with Testcontainers for DB/Redis, Pact/Dredd for contract validation, Vitest for UI components, Playwright for E2E/UI, k6/Locust for load profiles  
**Target Platform**: Containerized deployment on Linux (Ubuntu 22.04 base) via Docker Compose locally and Kubernetes/Helm in production; CI via GitHub Actions mirroring prod image  
**Project Type**: Multi-surface platform (Python services, React frontend, automation agents, infrastructure scripts)  
**Performance Goals**: Simulation orchestration p95 turn execution < 2s, persona decision latency p95 < 700ms, API throughput target 300 RPS sustained with error budget 0.1%, frontend dashboard first meaningful paint < 3s on broadband  
**Constraints**: Enforce OTel tracing, structured JSON logs with traceId/spanId, RBAC via OIDC with JWT validation, idempotent write APIs, rate limiting per user/token, data residency in regional bucket, audit log retention 90 days  
**Scale/Scope**: Supports up to 25 concurrent campaigns, 10 personas per campaign, three tenant tiers (demo, enterprise, internal), automation agents (QA/AI validators) executing hourly reports

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Domain-Driven Narrative Core**: Bounded context blueprint to be captured in ADR-ARC-001. Aggregates: Campaign (Simulation Orchestration), Persona Machine Spirit (Persona Intelligence), Narrative Chronicle (Narrative Delivery), Platform Control Plane (Platform Operations). Ports include `DirectorAgent.turn_processor`, `PersonaAgent.gemini_client`, `ChroniclerAgent.storage_gateway`, `EventBus`. Anti-corruption layer defined for Gemini API and legacy CLI tools.  
- **Contract-First Experience APIs**: Produce OpenAPI fragment `contracts/openapi-refactor.yaml` documenting rate limits, idempotency keys, pagination for `/api/v1/campaigns`, `/api/v1/simulations`. No new endpoints, but existing contracts updated.  
- **Data Stewardship & Persistence Discipline**: Identify schema changes required for campaign metadata (PostgreSQL migration alignment), Redis cache TTL standards, multi-tenant row filters, RPO 15 minutes via snapshot, RTO 30 minutes via restore playbook.  
- **Quality Engineering & Testing Discipline**: Expand Pytest coverage for blueprint validation utilities, contract linting CI job, Pact tests for StoryForge API consumers, Playwright regression for dashboard, mutation testing on domain mappers.  
- **Operability, Security & Reliability**: Document OTel spans for each aggregate interaction, structured logging fields, rollout via LaunchDarkly feature flags, retries with exponential backoff on Gemini adapter, circuit breaker thresholds for EventBus, alerting thresholds for RED/USE metrics.

**Post-Phase 1 Design Status**: Research, data model, contracts, and quickstart artifacts satisfy the above gates with documented owners and deliverables; no violations identified, so Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── persona_agent.py              # Persona Intelligence context
├── director_agent.py             # Simulation Orchestration context
├── chronicler_agent.py           # Narrative Delivery context
├── event_bus.py                  # Platform Operations messaging port
├── services/                     # Domain services & adapters
└── shared_types.py               # Cross-context DTOs

apps/
├── api/                          # REST entrypoints (FastAPI routers)
└── workers/                      # Background job executors (Celery/RQ)

frontend/
├── src/
│   ├── components/               # UI components consuming Experience API
│   ├── pages/                    # Dashboard flows
│   └── services/                 # BFF client wrappers
└── tests/                        # Vitest + Playwright specs

specs/001-best-practice-refactor/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── openapi-refactor.yaml
```

**Structure Decision**: Leverage existing multi-surface layout: backend logic under `src/` (agents, services, domain models), API entrypoint under `api_server.py`, automation scripts in `scripts/` and `apps/`, frontend React app under `frontend/`, infrastructure manifests in `deploy/`, `k8s/`, and `terraform/`. Documentation artifacts for this feature reside in `specs/001-best-practice-refactor/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
