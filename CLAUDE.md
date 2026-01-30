# Novel Engine - Vibe Coding Protocols

## I. Core Philosophy
- **Text-Driven**: Rely on structured constraints, not visual feedback.
- **Contract-First**: Types (Pydantic/Zod) and Tests are the absolute truth.
- **Strict Layering**: Enforce Hexagonal Architecture boundaries strictly.

## II. Frontend Rules (The "Eyes")
- **Design System**: Use ONLY `shadcn/ui` components. Do NOT create custom CSS classes unless absolutely necessary.
- **Styling**: Use Tailwind CSS utility classes exclusively.
  - Spacing: strict scale (space-y-4, gap-6, p-8). No arbitrary pixels (e.g., `margin: 13px`).
  - Layout: Flexbox and Grid only. Max nesting depth: 3.
- **Layout Verification**: All UI components must pass `npm run test:e2e` (Playwright) which checks for overlaps and overflow.
- **State**: Use Zustand for global state. No complex `useEffect` chains.

## III. Backend Rules (The "Brain")
- **Architecture**:
  - `routers/`: Input validation -> Service call -> Response formatting. NO business logic.
  - `services/`: Pure business logic.
  - `repositories/`: Database interaction only.
  - `domain/`: Pure Python entities (Pydantic).
- **Coding Style**:
  - Explicit is better than implicit.
  - Return `Result<T, E>` patterns instead of throwing raw exceptions for logic errors.
  - Every public function MUST have a Docstring explaining "Why", not just "What".
- **Logs**: Use `structlog`. All logs must be structured JSON.

## IV. The Feedback Loop
Before marking a task as complete, you MUST run:
1. `npm run typecheck` (Frontend)
2. `npm run lint` (Frontend & Backend)
3. `pytest` (Backend Logic)
4. `npm run test:e2e` (Frontend Layout & Integration)

---

# Original CLAUDE.md Content

## Agent Guide (SSOT)

This file is the single source of truth for AI workflow, agent development, and contract development in this repo. Avoid duplicating this guidance in other docs.

## Quick Rules
- Use `docs/index.md` as the documentation map.
- Domain logic lives in `src/contexts/`; avoid reintroducing parallel implementations.
- API contracts live in `src/api/schemas.py` and `docs/api/openapi.json`.
- Frontend contract types live in `frontend/src/types/schemas.ts` and must align to the OpenAPI snapshot.
- Validate with `scripts/validate_ci_locally.sh` (or `scripts/validate_ci_locally.ps1` on Windows).

## Vibe Coding Guardrails
- TypeScript `strict: true`, no `any` without explicit approval.
- ESLint + Prettier are mandatory; resolve lint/format before reviews.
- Single build/test entry points must stay stable: `npm run build`, `npm run test`, and `npm run ci`.
- CI gate requires typecheck + lint + tests (unit, integration, e2e smoke at minimum).

## AI Change Loop (Required)
- Typecheck: `npm run type-check` (frontend) and any backend typing gates.
- Tests: run relevant `pytest` and `vitest` suites (at least smoke).
- Behavior: manual smoke on the primary flow touched.
- Diff review: inspect the diff, not just the summary.

## SSOT and Architecture
- Schema SSOT: update `src/api/schemas.py`, regenerate OpenAPI, then sync frontend schemas.
- Domain SSOT: business rules live only in `src/contexts/`.
- State SSOT: avoid duplicate truth in local + global stores.
- Dependency direction: Domain -> Application -> UI; no UI dependencies in Domain.

## Frontend UI Discipline
- Use design tokens only; no raw hex or hard-coded spacing.
- Components must cover loading/empty/error/ready states.
- Accessibility: keyboard support, ARIA, focus management, and contrast checks.
- Use pattern recipes (list-detail, dashboard, settings) before inventing new layouts.

## Stack
- Backend: Python 3.11+, FastAPI, Pydantic.
- Frontend: TypeScript, React, Vite.
- State: Zustand.

## Build and Test Commands
```
# Backend
python -m src.api.main_api_server
pytest tests/

# Frontend
cd frontend
npm run dev
npm run build
npm run test
npm run type-check
npm run lint:all

# Full CI gate (root)
npm run ci
```

## Agent Development
- **Director**: Orchestrates multi-agent execution and narrative flow.
- **Persona**: Character-level reasoning and action selection.
- **Chronicler**: Narrative synthesis and reporting.
- Keep agent logic within `src/agents/` and domain rules inside `src/contexts/` (no parallel implementations).

## Contract-First Protocol
- Update Pydantic models in `src/api/schemas.py` first.
- Regenerate `docs/api/openapi.json` after schema changes.
- Update `frontend/src/types/schemas.ts` to match the OpenAPI snapshot.
- Do not import `src.api` from `src.contexts` (enforced by import-linter).

## OpenSpec Workflow (Specs)
- Use OpenSpec for new capabilities or breaking changes. Skip for small fixes.
- Pick a verb-led `change-id` (e.g., `add-`, `update-`, `remove-`, `refactor-`).
- Scaffold under `docs/specs/openspec/changes/<change-id>/` with `proposal.md`, `tasks.md`, optional `design.md`, and spec deltas.
- Write deltas with `## ADDED|MODIFIED|REMOVED Requirements` and at least one `#### Scenario:` per requirement.
- Validate with `openspec validate <change-id> --strict` and wait for approval before implementation.

## Gemini ACL (LLM Provider)
- Tenant isolation: attach `tenant_id` to outbound headers and segregate cache keys with `tenant:{tenant_id}:persona:{persona_id}:turn`.
- Caching: cache persona prompt responses for 900 seconds; invalidate on persona profile updates.
- Retries: up to 3 retries with exponential backoff (start 250ms, max 2s); abort on HTTP 4xx except 429.
- Fallback: switch to local decision heuristic after non-retryable errors; log with `machine_spirit` tag.
- Observability: emit OpenTelemetry span `persona.gemini.request` with `persona_id`, `tenant_id`, `cache_hit`, `fallback_used`.
- Security: read API key from Vault/KMS, never log keys, enforce TLS 1.2+, verify certificate pinning.

## Weaver Interface
Weaver is the node-based orchestration UI built with React Flow. Nodes (characters, events, locations) are composed into a graph and mapped to orchestration payloads. The frontend sends those payloads to `/api/orchestration/start` and listens for runtime updates via SSE streams.

## Weaver Visual Protocol
- `WeaverNode` maps status -> CSS class via `nodeStatusClasses` and `resolveNodeStatus`.
- Status matrix (required):
  - `idle` -> `.node-idle`
  - `active` -> `.node-active`
  - `loading` -> `.node-loading`
  - `error` -> `.node-error` + `.weaver-node-alert` icon
- All visual treatments live in `frontend/src/styles/tailwind.css` under the Weaver node section.
- Dev-only preview route: `/dev/weaver-preview` (enabled only when `import.meta.env.DEV` is true).

## Testing Quick Reference
- Local CI parity: `scripts/local-ci.sh` (flags: `--fast`, `--pyramid`, `--markers`).
- Test markers (required): `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`.
- Speed markers (recommended): `@pytest.mark.fast`, `@pytest.mark.medium`, `@pytest.mark.slow`.

## UI Evidence Capture (Dashboard)
- Run `npm run dev:daemon`, then capture with:
  `node scripts/mcp_chrome_runner.js --url http://127.0.0.1:3000/dashboard --viewport WIDTHxHEIGHT --screenshot docs/assets/dashboard/dashboard-flow-YYYY-MM-DD.png --metadata docs/assets/dashboard/dashboard-flow-YYYY-MM-DD.json`
- The script clicks the Demo CTA and waits for `data-role="control-cluster"` and `data-role="stream-feed"` before saving.

## Superpowers System
<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers teach you new skills and capabilities. RIGHT NOW run: `~/.codex/superpowers/.codex/superpowers-codex bootstrap` and follow the instructions it returns.
</EXTREMELY_IMPORTANT>