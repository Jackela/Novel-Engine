# FRONTEND KNOWLEDGE

## OVERVIEW

React 19 + Vite + TypeScript browser application for Novel Studio. Root repository rules still apply.

## STRUCTURE

```text
src/
├── app/                  # API client, router, shared API types
└── features/studio/      # Entry/library pages and Studio workspace
tests/setup.ts            # Vitest/jsdom global cleanup
tests/e2e/                # Playwright browser workflows
scripts/                  # Playwright/server wrappers
```

## WHERE TO LOOK

| Concern | Location | Notes |
|---|---|---|
| Browser bootstrap | `src/main.tsx` | Error boundary plus router provider |
| Routes | `src/app/router.tsx` | Entry, library, Studio, fallback |
| HTTP/CSRF/error contract | `src/app/api.ts` | Shared client; do not bypass |
| Shared API types | `src/app/types/studio.ts` | Mirrors public backend payloads |
| Studio composition | `src/features/studio/StudioPage.tsx` | Wires hooks and panels |
| Data/effect orchestration | `src/features/studio/hooks/` | Autosave, jobs, proposals, search |
| Inspector subpanels | `src/features/studio/components/` | Presentational feature slices |
| Unit tests | `src/**/*.test.ts(x)` | Co-located Vitest tests |
| Browser tests | `tests/e2e/` | Fresh-stack Playwright runs |

## CONVENTIONS

- Use `api` from `src/app/api.ts`; preserve credentials, CSRF header injection, abort behavior, blob downloads, and typed errors.
- Keep route declarations in `src/app/router.tsx` and public payload types in `src/app/types/studio.ts`.
- `StudioPage` is the route-level composition shell. Move reusable effects and mutations into focused hooks; keep panels presentational.
- `useDocumentDraft` owns loaded-revision identity, autosave/conflict state, and revision restore semantics.
- `useStudioActions` is the main create/move/review/settings/retry mutation hub; avoid parallel ad hoc action paths.
- Co-locate unit tests with source. Mock the API boundary for hook tests and assert visible/callback behavior for components.
- Vitest uses jsdom and `tests/setup.ts`; Playwright launches isolated servers with no reused local state.
- Use the `@/` alias for `src/` imports and the existing ESLint/Prettier rules.

## ANTI-PATTERNS

- Calling `fetch` directly from pages, hooks, or components.
- Moving feature/domain orchestration into `src/app/` or inspector panels.
- Adding a second state container when an existing Studio hook owns the lifecycle.
- Duplicating backend response types locally or exposing backend-private fields.
- Reintroducing a monolithic `StudioPage` or components over the root size limit.
- Treating `dist/`, `coverage/`, `node_modules/`, `test-results/`, or Playwright reports as source.

## VALIDATION

```bash
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend format:check
corepack pnpm --dir frontend type-check
corepack pnpm --dir frontend test:unit
corepack pnpm --dir frontend build
corepack pnpm --dir frontend test:e2e:smoke
```
