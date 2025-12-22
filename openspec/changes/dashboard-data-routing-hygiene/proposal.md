# Proposal: Dashboard Data & Routing Hygiene

## Why
- Latest MCP console capture (`chrome-devtools/list_console_messages` msgid 42-43 on dashboard page) still shows both React Router future-flag warnings even after the first accessibility pass. App router needs to opt into v7 flags via the supported `RouterProvider`/data-router APIs so the warnings disappear in dev/prod.
- The dashboard data hook currently cycles through `/characters` (legacy), multiple fallbacks, and localhost fallbacks. This duplicates network traffic, leaks “demo” source chips, and contradicts the backend contract that only `/api/characters` will be exposed going forward. MCP audit case §9 (API validation) now requires a single canonical endpoint.
- Our Vitest router warning harness (`frontend/src/__tests__/AppRouterWarnings.test.tsx`) still relied on `ReactDOMTestUtils.act`, re-triggering the deprecated-act warning we are trying to eliminate. We need a reliable regression test that fails if either warning reappears.

## What Changes
1. **Router Provider migration** – Replace the `BrowserRouter` wrapper with a `createBrowserRouter`/`RouterProvider` stack that opts into `v7_startTransition` and `v7_relativeSplatPath`. Keep skip-link + protected routes inside a shared `AppShell` so UX remains unchanged while console stays quiet.
2. **Canonical `/api/characters` feed** – Introduce an API-base resolver that always targets `/api/characters`, strip `/characters` fallbacks, and align the Vite proxy so `/api/*` forwards to the backend API server. Chips should show “API feed” unless the unified endpoint fails.
3. **TDD coverage** – Extend `dashboard-accessibility.test.tsx` to assert only `/api/characters` URLs are attempted and update the router-warning test to mount via `createRoot` (no deprecated act). This keeps the console clean and enforces the new API contract.

## Impact
- Specs touched: `dashboard-interactions` (data parity requirement + routing hygiene).
- Code touched: `frontend/src/hooks/useDashboardCharactersDataset.ts`, `frontend/vite.config.ts`, `frontend/src/App.tsx`, router warning spec + dashboard Vitest suites.
- Tooling: rerun `npm run lint`, `npm run type-check`, full `npx vitest run`. Update UAT log to note the `/api` unification.
