# Quickstart: Implementing Type Safety and Styling SSOT

## What you’ll add

- `frontend/src/styles/tokens.ts` — typed design tokens (SSOT)
- `frontend/src/styles/theme.ts` — MUI theme derived from tokens
- `frontend/src/services/queries.ts` — standardized server-state hooks
- Build step to generate `frontend/src/styles/design-system.css` from `tokens.ts`
- Stricter TS config and ESLint rules; Stylelint with CSS-variable guard

## Commands

- Type check: `cd frontend && npm run type-check`
- Lint (JS/TS): `cd frontend && npm run lint`
- Tests (unit): `cd frontend && npm run test`
- Tests (e2e): `cd frontend && npm run test:e2e`

## Steps

1) Tokens and Theme
- Create `src/styles/tokens.ts` with color, typography, spacing, motion, elevation.
- Create `src/styles/theme.ts` that builds a MUI theme from tokens; remove inline hex in components.
- Add a small build script to emit `design-system.css` from `tokens.ts` (colors, spacing, typography as CSS vars).

2) TypeScript and ESLint
- In `tsconfig.json`, enable: isolatedModules, noImplicitReturns, noUncheckedIndexedAccess, exactOptionalPropertyTypes, useUnknownInCatchVariables, noFallthroughCasesInSwitch, noUnusedLocals, verbatimModuleSyntax.
- Extend ESLint to include `**/*.{ts,tsx}` with `@typescript-eslint` rules.

3) Server-State Standardization
- Add `src/services/queries.ts` with typed query hooks and stable keys:
  - Keys: `['characters','list']`, `['characters','detail',name]`, `['stories','generation',id]`, `['system','health']`, `['system','status']`
  - Hooks: `useCharactersQuery`, `useCharacterDetailsQuery`, `useGenerationStatusQuery`, `useHealthQuery`, `useSystemStatusQuery`
- Migrate read flows to use these hooks; remove custom APICache/dedup in `src/services/api.ts` for endpoints covered by hooks.
- Invalidate on writes by calling `queryClient.invalidateQueries(queryKeys.characters)` or specific keys.

4) CI Gates
- Ensure CI runs: type-check, lint (ESLint + Stylelint), unit tests; block on violations.

## Verification
- Changing a token updates component visuals without editing component code.
- Concurrent duplicate read requests dedupe to one network call via the standardized hooks.
- Type-check and lint fail on implicit any and color hex usage in component code.
