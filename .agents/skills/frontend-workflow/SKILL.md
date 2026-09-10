---
name: frontend-workflow
description: Route Novel-Engine frontend/UI work to the right skills and hold the repo's UI stack facts. Use when building or changing Studio UI, writing or reviewing code under frontend/src, auditing or redesigning an interface, or changing DESIGN.md / design tokens.
---

# Frontend workflow

Root `DESIGN.md` is the design-language source of truth (schema: `@google/design.md`, tokens mirror `frontend/src/styles/base.css`). Read it before any UI change; a UI change that alters the visual language updates DESIGN.md in the same task.

## Stack facts

- React 19 + Vite + TypeScript; plain CSS split by feature under `frontend/src/styles/` (import order in `frontend/src/index.css` is normative — CSS is order-sensitive).
- BEM-ish naming: `feature-block__element--modifier`; the `ui-` prefix marks cross-feature primitives (`ui-command`, `ui-form-error`) and lives in `base.css`.
- Design tokens are `:root` custom properties in `frontend/src/styles/base.css` — the only place raw colors belong. Light mode only.
- Type: IBM Plex Sans Variable (self-hosted) for UI, `ui-serif` stack for the writing surface. Icons: lucide-react.
- No Tailwind, no component library, no animation library. Skills assuming otherwise need their stack-specific rules adapted.

## Routing

- **New feature / Studio UI change** — read DESIGN.md first, then apply `vercel-react-best-practices` (its `server-*` rules assume Next.js/RSC; this repo is a Vite SPA — skip them) and `vercel-composition-patterns`. Reuse `ui-` primitives and tokens; finish on the frontend validation scripts in root AGENTS.md.
- **UI audit / consistency pass** — `improve-ui` (user-level): read-only against the product source, at most three findings, each with contract/runtime/correction evidence; implementation plans land in `design-plans/` for a separate execution session.
- **UI code review** — `web-design-guidelines` (repo-level): fetches the current Web Interface Guidelines and reports `file:line` findings. For a11y-specific fixes follow `fixing-accessibility` (user-level).
- **Visual redesign of a surface** — `impeccable` (user-level), with DESIGN.md as the evidence base. It expects a PRODUCT.md and surface briefs; the repo has none yet, so a first run proposes `impeccable init` — treat creating those artifacts as its own authorized task.
- **Design-token or DESIGN.md change** — update via `create-design-md` conventions, then gate with `npx @google/design.md lint DESIGN.md` and `npx @google/design.md diff` against the previous version; regenerate deliberately, like the OpenAPI snapshot.
- **Browser verification** — the browser-use skills (main session only) against a locally running stack, or the Playwright suite in `frontend/`.
- **Landing or marketing pages** (none today) — `design-taste-frontend` (user-level). Its Tailwind + Next.js defaults are its own context; product UI consistency always routes through the DESIGN.md + `impeccable` path instead.
