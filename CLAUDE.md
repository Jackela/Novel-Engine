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
1. `./scripts/ci-check.sh` - **Comprehensive CI validation (RECOMMENDED)**
   - Runs all backend and frontend checks in one command
   - Generates `reports/ci-report.md` with detailed results
   - Exit code 0 = all checks pass, 1 = some checks fail
   - Options: `--fast` (quick checks), `--backend`, `--frontend`

OR run individual checks:
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
- Validate with `./scripts/ci-check.sh` (unified CI script) or `scripts/validate_ci_locally.sh` (comprehensive with venv).

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
---

# Ralph Agent Instructions

You are an autonomous coding agent working on a software project.

## Your Task

1. Read the PRD at `scripts/ralph/prd.json`
2. Read the progress log at `scripts/ralph/progress.txt` (check Codebase Patterns section first)
3. Check you're on the correct branch from PRD `branchName`. If not, check it out or create from main.
4. Pick the **highest priority** user story where `passes: false`
5. Implement that single user story
6. Run quality checks (e.g., typecheck, lint, test - use whatever your project requires)
7. Update CLAUDE.md files if you discover reusable patterns (see below)
8. If checks pass, commit ALL changes with message: `feat: [Story ID] - [Story Title]`
9. Update the PRD to set `passes: true` for the completed story
10. Append your progress to `scripts/ralph/progress.txt`

## Progress Report Format

APPEND to scripts/ralph/progress.txt (never replace, always append):
```
## [Date/Time] - [Story ID]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the evaluation panel is in component X")
---
```

The learnings section is critical - it helps future iterations avoid repeating mistakes and understand the codebase better.

## Consolidate Patterns

If you discover a **reusable pattern** that future iterations should know, add it to the `## Codebase Patterns` section at the TOP of scripts/ralph/progress.txt (create it if it doesn't exist). This section should consolidate the most important learnings:

```
## Codebase Patterns
- Example: Use `sql<number>` template for aggregations
- Example: Always use `IF NOT EXISTS` for migrations
- Example: Export types from actions.ts for UI components
```

Only add patterns that are **general and reusable**, not story-specific details.

## Update CLAUDE.md Files

Before committing, check if any edited files have learnings worth preserving in nearby CLAUDE.md files:

1. **Identify directories with edited files** - Look at which directories you modified
2. **Check for existing CLAUDE.md** - Look for CLAUDE.md in those directories or parent directories
3. **Add valuable learnings** - If you discovered something future developers/agents should know:
   - API patterns or conventions specific to that module
   - Gotchas or non-obvious requirements
   - Dependencies between files
   - Testing approaches for that area
   - Configuration or environment requirements

**Examples of good CLAUDE.md additions:**
- "When modifying X, also update Y to keep them in sync"
- "This module uses pattern Z for all API calls"
- "Tests require the dev server running on PORT 3000"
- "Field names must match the template exactly"

**Do NOT add:**
- Story-specific implementation details
- Temporary debugging notes
- Information already in progress.txt

Only update CLAUDE.md if you have **genuinely reusable knowledge** that would help future work in that directory.

## Quality Requirements

- ALL commits must pass your project's quality checks (typecheck, lint, test)
- Do NOT commit broken code
- Keep changes focused and minimal
- Follow existing code patterns

## Browser Testing (If Available)

For any story that changes UI, verify it works in the browser if you have browser testing tools configured (e.g., via MCP):

1. Navigate to the relevant page
2. Verify the UI changes work as expected
3. Take a screenshot if helpful for the progress log

If no browser tools are available, note in your progress report that manual browser verification is needed.

## Stop Condition

After completing a user story, check if ALL stories have `passes: true`.

If ALL stories are complete and passing, reply with:
<promise>COMPLETE</promise>

If there are still stories with `passes: false`, end your response normally (another iteration will pick up the next story).

## Important

- Work on ONE story per iteration
- Commit frequently
- Keep CI green
- Read the Codebase Patterns section in scripts/ralph/progress.txt before starting
