# Novel Engine Code Conventions

## I. General Rules

1. **Read-First**: Before modifying code, read relevant CLAUDE.md and this file.
2. **No Magic**: No magic numbers, strings, or arbitrary CSS values.
3. **Tests Required**: New logic requires new tests. Broken tests must be fixed immediately.
4. **Explicit > Implicit**: Prefer explicit types, names, and configurations.

---

## II. Frontend Architecture

### Directory Structure

```
frontend/src/
├── app/                    # App entry, routing, providers
│   └── ProtectedLayout.tsx
├── components/
│   ├── ui/                 # shadcn/ui atoms (DO NOT MODIFY)
│   ├── composed/           # Complex layouts (AppShell, EditorLayout)
│   ├── editor/             # Tiptap extensions
│   ├── graph/              # React Flow utilities
│   └── narrative/          # Narrative editor components
├── features/               # Feature modules
│   └── {feature}/
│       ├── components/     # Feature-specific components
│       ├── hooks/          # Feature-specific hooks
│       ├── api/            # API client (e.g., characterApi.ts)
│       └── store/          # Feature Zustand store (if needed)
├── shared/
│   ├── components/
│   │   ├── layout/         # Sidebar, TopBar (used by AppShell)
│   │   ├── feedback/       # Toast, alerts
│   │   └── a11y/           # Accessibility helpers
│   └── hooks/              # Shared hooks
├── lib/
│   ├── api/                # API clients
│   └── utils.ts            # Utility functions
├── styles/
│   ├── tailwind.css        # Tailwind base + components
│   ├── editor.css          # Editor Canvas styles
│   └── tokens.ts           # TypeScript token exports
└── types/
    └── schemas.ts          # Zod schemas (match backend)
```

### State Management Hierarchy

| Priority | Type | Tool | Scope |
|----------|------|------|-------|
| 1 | Server State | TanStack Query | API data, caching |
| 2 | Global UI State | Zustand | Theme, sidebar, modals |
| 3 | Form State | React Hook Form | Form validation |
| 4 | Local State | useState | Temporary UI state only |

**Rules:**
- Never duplicate server state in Zustand
- Zustand stores: one per feature domain, not per component
- Avoid complex `useEffect` chains; prefer derived state

### Component Patterns

```tsx
// Named exports only
export function MyComponent({ title, onAction }: MyComponentProps) {
  // ...
}

// Props interface naming
interface MyComponentProps {
  title: string;
  onAction: () => void;
}

// Hooks extraction: logic > 10 lines → custom hook
function useMyComponentLogic() {
  // ...
}
```

### Import Order

```tsx
// 1. External packages
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

// 2. Internal shared
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

// 3. Feature-specific
import { useCharacters } from '@/features/characters/api/characterApi';

// 4. Relative
import { MyChildComponent } from './MyChildComponent';
import type { MyType } from './types';
```

---

## III. Backend Architecture (Hexagonal)

### Layer Structure

```
src/
├── api/
│   ├── routers/            # HTTP layer
│   │   └── {feature}_router.py
│   ├── schemas.py          # Pydantic schemas (SSOT)
│   └── main_api_server.py  # FastAPI app
├── contexts/
│   └── {context}/
│       ├── application/    # Use cases, orchestration
│       │   └── services/
│       ├── domain/         # Pure Python entities
│       │   ├── entities.py
│       │   └── value_objects.py
│       └── infrastructure/ # External integrations
│           ├── repositories/
│           └── adapters/
└── shared/                 # Cross-context utilities
```

### Layer Rules

| Layer | Allowed Dependencies | Responsibility |
|-------|---------------------|----------------|
| **Routers** | Schemas, Services | Parse request → Call service → Format response |
| **Services** | Domain, Repositories | Business orchestration, transactions |
| **Domain** | Nothing external | Pure business logic, entities, value objects |
| **Infrastructure** | Domain | Database, LLM, file system implementations |

**Forbidden:**
- Routers containing business logic
- Domain importing FastAPI, SQLAlchemy, or any framework
- Services directly accessing database (use repositories)

### Coding Style

```python
# Return Result patterns instead of raising
from typing import TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E')

@dataclass(frozen=True)
class Result(Generic[T, E]):
    value: T | None = None
    error: E | None = None

    @property
    def is_ok(self) -> bool:
        return self.error is None

# Docstrings explain "Why", not "What"
def calculate_relationship_score(events: list[Event]) -> float:
    """
    Why: Relationship strength degrades over time without interaction.
    The decay factor ensures inactive relationships don't dominate suggestions.
    """
    ...
```

### Logging

Use `structlog` with structured JSON:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "character_created",
    character_id=character.id,
    name=character.name,
    tenant_id=tenant_id,
)
```

---

## IV. Testing Strategy

### Test Pyramid

| Level | Location | Scope | Speed |
|-------|----------|-------|-------|
| Unit | `tests/unit/` | Domain logic, utilities | Fast |
| Integration | `tests/integration/` | Service + Repository | Medium |
| E2E | `frontend/tests/e2e/` | Full user flows | Slow |

### Markers (Required)

```python
import pytest

@pytest.mark.unit
def test_character_name_validation():
    ...

@pytest.mark.integration
def test_character_repository_save():
    ...

@pytest.mark.e2e
def test_character_creation_flow():
    ...
```

### Coverage Requirements

- Domain layer: > 80%
- Services: > 70%
- Routers: Integration tests for happy path

---

## V. Contract-First Protocol

### Schema Changes

1. Update `src/api/schemas.py` (Pydantic models)
2. Regenerate `docs/api/openapi.json`
3. Update `frontend/src/types/schemas.ts` (Zod schemas)

**Order matters**: Backend schemas are the source of truth.

### Import Rules

```
src/api → src/contexts  ✅ Allowed
src/contexts → src/api  ❌ Forbidden (enforced by import-linter)
```

---

## VI. Quality Gates

Before committing, you MUST run:

```bash
# Frontend
npm run type-check    # TypeScript strict mode
npm run lint:all      # ESLint + Stylelint

# Backend
pytest tests/unit     # Unit tests
pytest tests/integration  # Integration tests

# Full CI gate
npm run ci            # All checks
```

### Pre-commit Checklist

- [ ] Types pass (`npm run type-check`)
- [ ] Lint passes (`npm run lint:all`)
- [ ] Unit tests pass
- [ ] No console.log or print statements
- [ ] No hardcoded secrets or API keys
- [ ] CLAUDE.md updated if patterns discovered

---

## VII. Naming Conventions

### Files

| Type | Pattern | Example |
|------|---------|---------|
| Component | PascalCase | `CharacterCard.tsx` |
| Hook | camelCase with `use` | `useCharacters.ts` |
| API client | camelCase with `Api` | `characterApi.ts` |
| Store | camelCase with `Store` | `characterStore.ts` |
| Utility | camelCase | `formatDate.ts` |
| Test | `.test.ts` or `.spec.ts` | `CharacterCard.test.tsx` |

### Variables

| Type | Convention | Example |
|------|------------|---------|
| Component | PascalCase | `CharacterCard` |
| Function | camelCase | `calculateScore` |
| Constant | UPPER_SNAKE | `MAX_CHARACTERS` |
| Boolean | is/has/can prefix | `isLoading`, `hasError` |
| Event handler | on/handle prefix | `onSubmit`, `handleClick` |

---

## VIII. Git Workflow

### Commit Messages

```
feat: [STORY-ID] Short description

- Detail 1
- Detail 2

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Branch Naming

```
feat/{feature-name}      # New features
fix/{bug-description}    # Bug fixes
refactor/{scope}         # Refactoring
docs/{topic}             # Documentation
```

---

## Quick Reference

### DO
- Follow hexagonal architecture layers
- Use semantic tokens from DESIGN_SYSTEM.md
- Write tests for new logic
- Update CLAUDE.md with discovered patterns
- Keep components focused and small

### DON'T
- Put business logic in routers
- Import `src/api` from `src/contexts`
- Create God components (> 300 lines)
- Use `any` type without explicit approval
- Commit broken tests
