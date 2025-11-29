# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Core Architectural Principles

All design and implementation MUST follow:

1. **Domain-Driven Design (DDD)**
   - Separate domain, application, infrastructure, and interface concerns.
   - Keep domain logic pure: no side effects, no framework dependencies.
   - All business rules must exist in one canonical place (SSOT).

2. **SOLID**
   - **Single Responsibility (SRP)**: each module has one reason to change.
     - Example: `AuthService` handles auth, `UserService` handles user data
     - Guideline: If a file exceeds 200 lines, consider splitting
   - **Open/Closed (OCP)**: extend via abstractions, avoid modifying stable code.
     - Example: Add new features via new components, not modifying existing ones
   - **Liskov Substitution (LSP)**: avoid inheritance that breaks substitutability.
   - **Interface Segregation (ISP)**: keep interfaces small and focused.
     - Example: `Clickable`, `Draggable` instead of `InteractiveElement`
   - **Dependency Inversion (DIP)**: high-level policies depend only on abstractions.
     - Example: Components depend on service interfaces, not implementations

3. **Single Source of Truth (SSOT)**
   - Never duplicate business rules, validation rules, constants, or domain logic.
   - When encountering duplicated logic, consolidate it.

   ### SSOT Canonical Sources
   | Concern | Canonical Source | Never Duplicate In |
   |---------|------------------|-------------------|
   | Design Tokens | `src/styles/tokens.ts` | TSX files, CSS files |
   | Theme Config | `src/styles/theme.ts` | Component styles |
   | Route Definitions | `src/App.tsx` | Navigation components |
   | API Endpoints | `src/services/api/` | Components directly |
   | Auth State | `src/store/authSlice.ts` | Local component state |
   | Type Definitions | `src/types/` | Inline type declarations |
   | Constants | `src/constants/` | Magic numbers/strings |

4. **Strong Typing**
   - Prefer explicit typedefs, value objects, enums, and structured data.
   - Avoid weakly-typed code (e.g., loose dictionaries, untyped objects).
   - All new APIs and modules must be fully type-annotated.

5. **Clear Boundaries**
   - Interfaces should describe "what" not "how".
   - Implementation details must stay behind abstractions.
   - Cross-layer leaks are strictly prohibited.

---

## 2. Code Quality & Structure

1. Code must be **simple, explicit, and intention-revealing**.
2. Avoid premature generalization, but maintain extensibility.
3. Write small, cohesive modules instead of large, multi-purpose files.
4. Always choose clarity over cleverness.
5. When refactoring:
   - Preserve behavior.
   - Improve naming, boundaries, and separation of concerns.

---

## 3. Testing Requirements (TDD / BDD)

All work MUST follow a test-first mindset:

1. **TDD Workflow (Red-Green-Refactor)**
   - **Red** → Write or update tests FIRST. The test should fail initially.
   - **Green** → Implement only enough code to satisfy tests.
   - **Refactor** → Clean up structure while keeping tests green.

2. **Test Layers**
   - Unit tests: pure modules, domain logic, helpers.
   - Integration tests: interactions between components or external systems.
   - E2E tests: full user/business flows across multiple layers.

3. **BDD Style**
   - Test scenarios MUST describe behavior: Given / When / Then.
   - Use `test.step()` in Playwright for clear phase separation.

4. **Coverage Expectations**
   - New or changed code MUST have appropriate test coverage.
   - Coverage threshold: 80% minimum for new code.
   - Coverage must never decrease.

5. **Test Principles**
   - Deterministic, isolated, readable.
   - Avoid mocking domain logic; apply mocks only at boundaries.
   - Treat flaky tests as defects to fix, not to skip.

### TDD Example Workflow

```
1. Identify requirement (from OpenSpec or user story)
2. Write failing test that describes expected behavior
3. Run test to confirm it fails (Red)
4. Write minimal code to make test pass (Green)
5. Refactor code while keeping tests green
6. Repeat for next requirement
```

### E2E Test File Template (Playwright)

```typescript
import { test, expect } from '@playwright/test';
import { PageObject } from './pages/PageObject';

/**
 * Feature Name E2E Test Suite
 *
 * OpenSpec: [change-id]
 * Spec: [spec-path]/spec.md
 */
test.describe('Feature Name E2E Tests', () => {
  test.describe('Scenario: Description from spec', () => {
    /**
     * Given: [precondition]
     * When: [action]
     * Then: [expected result]
     */
    test('should [expected behavior]', async ({ page }) => {
      await test.step('Given: [precondition]', async () => {
        // Setup
      });

      await test.step('When: [action]', async () => {
        // Action
      });

      await test.step('Then: [expected result]', async () => {
        // Assertion
      });
    });
  });
});
```

### Unit Test File Template (Vitest)

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { functionUnderTest } from './module';

describe('ModuleName', () => {
  describe('functionUnderTest', () => {
    it('should [expected behavior] given [condition]', () => {
      // Arrange
      const input = 'test';

      // Act
      const result = functionUnderTest(input);

      // Assert
      expect(result).toBe(expected);
    });
  });
});
```

---

## 4. CI & Quality Gates

All changes MUST satisfy:

1. All tests pass (unit, integration, E2E).
2. All linters, formatters, and type checkers pass.
3. No warnings should be silently ignored without strong justification.
4. Pipelines must remain fast, explicit, and easy to understand.
5. When modifying CI:
   - Keep jobs deterministic.
   - Never weaken existing quality gates.
   - Document changes in comments or README if necessary.

---

## 5. Sub-Agents Policy (MANDATORY)

Claude Code MUST proactively use sub-agents for specialized tasks.

### Mandatory Roles

- **architect** - Designs module boundaries, interfaces, and domain flows.
- **implementer** - Writes, modifies, and extends code following the architect's design.
- **qa-tester** - Designs, updates, and validates unit, integration, and E2E tests.
- **refactor** - Cleans code structure, applies SOLID/DDD, enforces boundaries.
- **claude-md-checker** - Ensures all work strictly adheres to this CLAUDE.md.

### Delegation Rules

1. For complex tasks, Claude MUST:
   - Identify relevant sub-agents.
   - Produce a delegation plan.
   - Assign each phase to the appropriate sub-agent.

2. Sub-agents are specialists:
   - Do NOT attempt to do their job in the main agent when a sub-agent exists.
   - Use the architect BEFORE the implementer.
   - Use qa-tester AFTER implementation but BEFORE finishing.
   - Use refactor when structural clarity is needed.

3. Sub-agents MUST be used early, not only at the end.

---

## 6. Workflow Model (Long-Running, Multi-Phase)

Claude Code MUST follow this execution model for all tasks:

### 1. PLAN
- Read the request.
- Summarize it in your own words.
- Generate a step-by-step plan with phases.
- Identify required sub-agents.

### 2. EXECUTE IN SMALL BATCHES
- Never dump large diffs.
- Modify only logically related files per batch.
- Verify after each batch.

### 3. USE CHECKPOINTS
- Before risky edits or cross-module refactoring, create checkpoints.
- Provide a rollback point if outputs diverge.

### 4. USE BACKGROUND TASKS
- Run long-running processes (e.g., servers, watchers) as background tasks.
- Keep the main agent responsive.

### 5. VALIDATE
- Run relevant tests.
- Run type checks.
- Run linters.
- If anything fails, fix before proceeding.

### 6. SUMMARIZE
- Provide a human-readable overview:
  - What changed?
  - Why?
  - How to test?
  - Potential risks?

---

## 7. Interaction Rules

Claude MUST always:

1. Ask clarifying questions when requirements seem ambiguous.
2. Propose alternatives when multiple solutions exist.
3. Avoid broad refactors unless explicitly requested.
4. Communicate intent before executing multi-file changes.
5. Produce concise, structured summaries instead of long essays.
6. Respect the existing project structure and patterns.

---

## 8. Non-Goals

Claude MUST NOT:

- Rewrite the entire architecture without explicit approval.
- Introduce new frameworks or libraries without justification.
- Duplicate logic across layers.
- Ignore or bypass any quality gates.
- Produce clever but unreadable solutions.

---

## 9. Project-Specific: Development Commands

### Unified Startup (Frontend + Backend)

```bash
npm run dev:daemon      # Start both frontend and backend
npm run dev:status      # Check running processes
npm run dev:stop        # Stop all processes
```

### Backend Only

```bash
cd /mnt/d/Code/novel-engine
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Only

```bash
cd frontend
npm run dev             # Vite dev server on :3000
npm run build           # Production build
npm run build:tokens    # Generate CSS from design tokens
```

### Testing

```bash
# Backend (pytest)
pytest -v                                    # All tests
pytest tests/test_security_framework.py     # Single file
pytest -k "test_iron_laws"                  # By pattern

# Frontend (Vitest + Playwright)
npm run test                                 # Unit tests
npm run test:e2e                            # Playwright E2E
npm run test:e2e:headed                     # With browser UI
```

### Quality Checks

```bash
# Frontend
npm run lint:all        # ESLint + Stylelint + hex scan
npm run type-check      # TypeScript
npm run tokens:check    # Design token verification

# Backend
bash scripts/validate_ci_locally.sh
```

---

## 10. Project-Specific: Multi-Agent Architecture

### Core Agents

| Agent | Location | Purpose |
|-------|----------|---------|
| **DirectorAgent** | `src/agents/director_agent_integrated.py` | Orchestrates narrative flow, manages turns, maintains campaign log |
| **PersonaAgent** | `src/agents/persona_agent_integrated.py` | Generates character decisions, assesses situations |
| **ChroniclerAgent** | `src/agents/chronicler_agent.py` | Transforms logs into dramatic narrative |

### Supporting Components

- **TurnOrchestrator** - Turn execution coordination
- **WorldStateCoordinator** - World state persistence
- **AgentLifecycleManager** - Iron Laws validation
- **EventBus** - Event-driven inter-agent communication

---

## 11. Project-Specific: Tech Stack

### Backend
- **Framework**: FastAPI + Pydantic
- **Async**: asyncio, aiohttp
- **Cache**: Redis (async)
- **Metrics**: Prometheus, OpenTelemetry

### Frontend
- **Framework**: React 18 + TypeScript
- **State**: Redux Toolkit + React Query
- **UI**: Material-UI v5 (MUI)
- **Animation**: Framer Motion
- **3D**: Three.js + React Three Fiber

### Real-time
- SSE at `/api/events/stream`
- WebSocket via Socket.io

---

## 12. Project-Specific: Design System (SSOT)

All styling follows Single Source of Truth:

1. **Token Definition**: `src/styles/tokens.ts`
2. **Generated CSS**: `src/styles/design-system.generated.css`
3. **Theme**: `src/styles/theme.ts`

### Workflow
```bash
# After editing tokens.ts
npm run build:tokens    # Regenerate CSS
npm run tokens:check    # Verify WCAG AA contrast
```

### Rules
- No hardcoded hex colors in TSX files
- Use `var(--token-name)` or theme values
- Run `npm run lint:tsx:hex` to detect violations

---

## 13. Project-Specific: OpenSpec (Spec-Driven Development)

### Change Workflow
1. **Create**: `openspec/changes/[change-id]/proposal.md`
2. **Implement**: Track in `tasks.md`, update specs
3. **Archive**: `openspec archive <id> --yes`

### Commands
```bash
openspec list                    # View active changes
openspec show [item]             # View details
openspec validate [id] --strict  # Validate thoroughly
```

### Structure
```
openspec/changes/[change-id]/
├── proposal.md      # Why, what, impact
├── tasks.md         # Implementation checklist
├── design.md        # Technical decisions (optional)
└── specs/[cap]/spec.md  # ADDED/MODIFIED/REMOVED
```

---

## 14. Project-Specific: API Endpoints

### Backend (FastAPI @ :8000)
- `GET /health` - Health check
- `GET /meta/system-status` - System status
- `GET /api/characters` - List characters
- `GET /api/characters/{id}` - Character details
- `GET /api/orchestration/status` - Pipeline status
- `POST /api/orchestration/start` - Start pipeline
- `GET /api/events/stream` - SSE events

### Frontend Proxy (Vite @ :3000)
Configured in `vite.config.ts` to proxy `/api`, `/meta`, `/health`, `/cache` to backend.

---

## 15. Project-Specific: Key File Locations

| Purpose | Path |
|---------|------|
| Backend entry | `api_server.py` |
| Backend agents | `src/agents/` |
| Frontend entry | `frontend/src/main.tsx` |
| Redux store | `frontend/src/store/` |
| API services | `frontend/src/services/api/` |
| Design tokens | `frontend/src/styles/tokens.ts` |
| E2E tests | `frontend/tests/e2e/` |
| OpenSpec | `openspec/` |
| CI workflows | `.github/workflows/` |
