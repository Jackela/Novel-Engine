## Implementation Tasks
1. Evidence & spec alignment
   - [ ] Capture MCP console logs/screenshots referencing `mcp__chrome-devtools__list_console_messages` msgid 42-43 and update `docs/mcp_manual_audit_plan.md` findings.
   - [ ] Validate `/api/v1/characters` contract with backend sample payload and attach to the change description.
2. Spec wiring
   - [ ] Update `openspec/specs/dashboard-interactions` with the routing + data-hygiene scenarios described here and run `openspec validate dashboard-data-routing-hygiene`.
3. Tests-first (TDD)
   - [ ] Extend `dashboard-accessibility.test.tsx` to assert only `/v1/characters` URLs are hit and the chips reflect the API source.
   - [ ] Modernize `AppRouterWarnings.test.tsx` so it mounts through `createRoot` and fails when router/act warnings reappear.
4. Implementation
   - [ ] Refactor `useDashboardCharactersDataset` to resolve the canonical `/api/v1/characters` base, drop legacy `/characters` fallbacks, and align the Vite proxy to rewrite `/v1/*` → `/api/v1/*`.
   - [ ] Swap the root router to `createBrowserRouter`/`RouterProvider` with `AppShell` so skip link + protected routes persist without console noise.
5. Validation & audit
   - [ ] Re-run `npm run lint`, `npm run type-check`, and full `npx vitest run`.
   - [ ] Execute an MCP dashboard audit to confirm console warnings are gone and datasets show “API feed” when live data is loaded.
