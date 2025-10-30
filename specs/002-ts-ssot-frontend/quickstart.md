# Quickstart: Validate Styling SSOT and Type Safety

## Prerequisites
- Node.js 18+
- From repo root: `cd frontend && npm ci`

## Developer Loop
- Build tokens: `npm run build:tokens`
- Type-check: `npm run type-check`
- Lint all (TS/JS, styles, hex in TSX): `npm run lint:all`
- Token drift and contrast check: `npm run tokens:check`
- Run unit tests: `npm test`
- Run e2e (optional): `npm run test:e2e`

## Local Preview
- Start dev server: `npm run dev`
- Verify primary screens show consistent tokens-driven styles and unified loading/error states.

## Update Tokens
- Edit tokens under `frontend/src/styles/` (SSOT) and re-run `npm run build:tokens`.
- Confirm CSS variables and theme reflect changes; commit generated outputs.

