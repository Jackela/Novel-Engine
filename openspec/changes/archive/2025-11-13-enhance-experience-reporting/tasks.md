## Task List

1. **Specs**
   - [x] Add frontend-quality requirement for generating a Markdown/HTML "Experience Report" after Playwright runs, with CTA/offline highlights.
   - [x] Extend devtools-audit spec to capture/log connection-state transitions (console + optional metrics hook).
   - [x] Extend process-management spec to define smoke vs. full Playwright CI tracks.
   - [x] Update docs-alignment spec to require README/onboarding coverage of demo CTA, offline simulation, and new env vars.
2. **Implementation**
   - [x] Implement the report generator (reuse Playwright reporters or custom script) and wire it into `npm run test:e2e`.
   - [x] Add connection indicator logging (console.info + future telemetry hook) whenever status changes.
   - [x] Add a fast smoke Playwright command/config + update CI workflows to use smoke for PRs, full for nightly/merge.
   - [x] Update README/onboarding docs with new instructions.
3. **Validation**
   - [x] Run lint/type-check/vitest.
   - [x] Run both Playwright smoke and full suites, and confirm the new report + logs appear.
