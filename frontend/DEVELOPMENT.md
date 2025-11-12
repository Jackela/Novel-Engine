# Novel Engine Frontend

## Quick Links

- Design System (SSOT): `frontend/DESIGN_SYSTEM.md`
- Feature Spec: `specs/002-ts-ssot-frontend/spec.md`
- Quickstart (tokens + checks): `specs/002-ts-ssot-frontend/quickstart.md`

## Local Development

From repo root:

```
cd frontend
npm ci
npm run build:tokens
npm run dev
```

## Quality Gates

- Type check: `npm run type-check`
- Lint all (TS/JS, styles, hex scan): `npm run lint:all`
- Token drift and contrast: `npm run tokens:check`

These run in CI and must pass for merges.
