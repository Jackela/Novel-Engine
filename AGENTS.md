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

# Original AGENTS.md Content

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

## Subagent-Driven Development Mode (Recommended)

For complex, multi-dimensional tasks, use **Subagent-Driven Development** with parallel brainstorming and implementation.

### When to Use

Use this mode when:
- Task has 3+ independent sub-tasks (security, CI/CD, docs, cleanup, etc.)
- Each sub-task can be worked on without shared state conflicts
- You want maximum parallelism and fresh context per task

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Parallel Brainstorming (Simultaneous)            │
│  ├── Dispatch N subagents, each with brainstorming skill   │
│  ├── Each explores their domain independently              │
│  └── Collects all approaches and recommendations           │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: Parallel Implementation (Same Branch)            │
│  ├── Create single feature branch                          │
│  ├── All subagents implement on SAME branch                │
│  ├── Each handles independent files/tasks                  │
│  └── Regular git push to share progress                    │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: Integration & Review                             │
│  ├── Final code review subagent validates ALL changes      │
│  ├── Create PR with comprehensive description              │
│  ├── Wait for CI to pass                                   │
│  └── Merge to main                                         │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Single Branch Strategy**
   - All subagents work on the same branch (e.g., `fix/github-best-practices`)
   - Avoid worktrees for multi-agent collaboration (too complex)
   - Regular `git pull` before committing to minimize conflicts

2. **Independent Task Domains**
   - Each subagent has clearly separated scope
   - No two subagents should modify the same files
   - If overlap unavoidable, coordinate through parent agent

3. **Fresh Context Per Task**
   - Each subagent starts with clean context
   - No context pollution from previous tasks
   - Parallel-safe execution

4. **Brainstorming Before Implementation**
   - Every subagent MUST use `brainstorming` skill first
   - Explore 2-3 approaches with trade-offs
   - Get approval before implementing

### Example: GitHub Best Practices Fix

```
Task: Fix all GitHub best practice issues

Dispatch 6 subagents in parallel:
├─ Security Agent      → .env handling, API key cleanup
├─ Dependabot Agent    → .github/dependabot.yml
├─ CI/CD Agent         → GitHub Actions version fixes
├─ Governance Agent    → CODE_OF_CONDUCT.md, .editorconfig
├─ Cleanup Agent       → Repository root cleanup
└─ README Agent        → CI badges, documentation

All on branch: fix/github-best-practices
Result: 18 files, 508 insertions, 157 deletions, 0 conflicts
```

### Success Criteria

- [ ] Each subagent used `brainstorming` skill before implementation
- [ ] All subagents worked on same branch
- [ ] No merge conflicts between subagent changes
- [ ] Final code review passed
- [ ] CI checks passed
- [ ] PR merged successfully

### vs. Sequential Execution

| Aspect | Subagent-Driven | Sequential |
|--------|-----------------|------------|
| Speed | ⚡ Parallel (N tasks in ~1x time) | 🐢 Sequential (N tasks in Nx time) |
| Context | ✅ Fresh per subagent | ⚠️ Polluted over time |
| Complexity | Medium (coordination) | Low |
| Best For | Multi-domain tasks | Single-domain tasks |

---

## Hierarchical Recursive Subagent Pattern (Advanced)

For complex features requiring deep refinement and strict quality gates, use **3-layer recursive subagent architecture** with embedded TDD cycles.

### Architecture Layers

```
Layer 1: Orchestrator Agent (You)
├── Coordinates overall feature delivery
├── Dispatches Layer 2 Feature Agents
├── Integrates results and handles conflicts
└── Ensures Definition of Done

Layer 2: Feature Agents (TDD Drivers)
├── Owns specific feature modules
├── Implements TDD Red-Green-Refactor cycle
├── Dispatches Layer 3 Specialist Agents for sub-tasks
└── Reports progress to Orchestrator

Layer 3: Specialist Agents (Granular Workers)
├── Test-First Agent: Writes failing tests
├── Implementation Agent: Makes tests pass
├── Refactor Agent: Improves code quality
└── Review Agent: Validates against standards
```

### TDD Cycle with Subagents

```
┌──────────────────────────────────────────────────────────────┐
│  RED Phase: Test-First Agent                                 │
│  ├── Analyze requirements                                    │
│  ├── Write failing test cases                                │
│  ├── Verify tests fail for right reason                      │
│  └── Commit: "test: add failing tests for X"                 │
├──────────────────────────────────────────────────────────────┤
│  GREEN Phase: Implementation Agent                           │
│  ├── Implement minimal code to pass tests                    │
│  ├── No refactoring yet, just make it work                   │
│  ├── Verify all tests pass                                   │
│  └── Commit: "feat: implement X to pass tests"               │
├──────────────────────────────────────────────────────────────┤
│  REFACTOR Phase: Refactor Agent                              │
│  ├── Improve code quality                                    │
│  ├── Ensure tests still pass                                 │
│  ├── Check against AGENTS.md standards                       │
│  └── Commit: "refactor: improve X quality"                   │
├──────────────────────────────────────────────────────────────┤
│  REVIEW Phase: Review Agent                                  │
│  ├── Verify spec compliance                                  │
│  ├── Check code quality                                      │
│  ├── Run test suite                                          │
│  └── Report: Approve / Request changes                       │
└──────────────────────────────────────────────────────────────┘
```

### Recursive Dispatch Pattern

When a Feature Agent encounters complex sub-tasks:

```python
# Feature Agent: EventService Implementation
Task: Implement EventService.create_event()

IF sub-task is complex:
    DISPATCH Test-First Agent:
        "Write tests for event creation validation"
    
    DISPATCH Implementation Agent:
        "Implement validation logic" 
    
    DISPATCH Refactor Agent:
        "Apply Result pattern, add structlog"
    
    INTEGRATE results
ELSE:
    Implement directly following TDD
```

### When to Use Recursive Pattern

**Use when**:
- Feature has >5 sub-components requiring individual TDD cycles
- Strict quality gates required (e.g., critical business logic)
- Multiple implementation approaches need exploration
- Code must meet multiple compliance criteria (architecture + quality + tests)

**Don't use when**:
- Simple config changes (overkill)
- Single-file modifications
- Time-critical hotfixes
- Task is purely exploratory

### Example: Complex Feature Implementation

```
Task: Implement Rumor Propagation Algorithm

Orchestrator (You)
├── Dispatch: "Architecture Agent"
│   ├── Design algorithm structure
│   └── Define interfaces
│
├── Dispatch: "Test-First Agent" 
│   ├── Write tests for 100/1000/10000 rumors
│   ├── Test truth perturbation
│   └── Test location-based spreading
│
├── Dispatch: "Implementation Agent"
│   └── RECURSIVE CALLS:
│       ├── Sub-Agent: "Adjacency Cache Implementation"
│       │   └── TDD: Cache structure → Implementation → Refactor
│       ├── Sub-Agent: "Propagation Logic"
│       │   └── TDD: Core algorithm → Implementation → Refactor
│       └── Sub-Agent: "Batch Processing"
│           └── TDD: Batch logic → Implementation → Refactor
│
├── Dispatch: "Performance Agent"
│   ├── Benchmark against targets
│   └── Profile and optimize
│
├── Dispatch: "Integration Agent"
│   ├── Wire into existing system
│   └── E2E tests
│
└── Dispatch: "Final Review Agent"
    ├── Verify all requirements
    ├── Check against spec
    └── Approve / Request changes
```

### Quality Gates per Layer

**Layer 3 (Specialist) Gates**:
- [ ] Tests written first (Red phase)
- [ ] Implementation passes tests (Green phase)
- [ ] Refactoring improves metrics (Refactor phase)
- [ ] No lint/type errors
- [ ] Follows project conventions

**Layer 2 (Feature) Gates**:
- [ ] All sub-components integrated
- [ ] Feature-level tests pass
- [ ] Documentation updated
- [ ] No integration issues

**Layer 1 (Orchestrator) Gates**:
- [ ] All features complete
- [ ] Full test suite passes
- [ ] CI/CD passes
- [ ] PR approved and merged

### Communication Protocol

**Between Layers**:
```markdown
## Feature Agent → Orchestrator Report

### Progress: 3/5 sub-tasks complete

#### Completed:
1. ✅ Adjacency Cache (TDD cycle complete)
   - Commit: abc1234
   - Tests: 12 passed
   - Coverage: 95%

#### In Progress:
2. 🔄 Propagation Logic (Green phase)
   - Tests written, implementing now
   - ETA: 30 minutes

#### Blocked:
3. ⏸️ Batch Processing
   - Blocked by: Need clarification on batch size
   - Question: Should we support dynamic batch sizing?
```

### Best Practices

1. **Max 3 Levels Deep**: Don't go beyond Layer 3 to avoid coordination overhead
2. **15-Minute Rule**: If a sub-task takes <15 min, don't dispatch a sub-agent
3. **Fresh Context**: Each dispatched agent gets clean context (no history pollution)
4. **Atomic Commits**: Each TDD phase = 1 commit
5. **Rollback Ready**: Each layer should be able to rollback independently
6. **Parallel Dispatch**: When sub-tasks are independent, dispatch in parallel

### Success Metrics

Track these metrics for recursive subagent effectiveness:
- **Cycle Time**: Red→Green→Refactor→Review duration
- **Defect Rate**: Bugs found after merge
- **Test Coverage**: Per-component coverage
- **Code Quality**: Lint/type errors per component
- **Coordination Overhead**: Time spent on inter-agent communication

---

## Superpowers System
<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers teach you new skills and capabilities.
Ensure the native skill discovery symlink exists, then restart Codex:
- `mkdir -p ~/.agents/skills`
- `ln -s ~/.codex/superpowers/skills ~/.agents/skills/superpowers`
See `~/.codex/superpowers/.codex/INSTALL.md` for details.
</EXTREMELY_IMPORTANT>
