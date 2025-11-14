# Doc Refresh Plan (Flow Layout + Dev Bootstrap)

## Sources referencing blocking/legacy startup commands
- ✅ README.md & README.en.md now highlight `npm run dev:daemon` + `npm run dev:stop` (2025-11-12 refresh).
- ✅ docs/deployment/DEPLOYMENT_GUIDE.md and docs/implementation/implementation_workflow.md reference the unified daemon workflow with manual fallback notes.
- docs/COMPREHENSIVE_DOCUMENTATION.md still referenced `npm run dev` prior to this pass—keep auditing summary docs after each refresh.
- docs/developer-guide-accessibility.md top section tells engineers to "run `npm run dev`" before testing color contrast. Needs the new command plus pointer to screenshot evidence.

## Docs tied to pre-flow dashboard layout
- docs/design/DESIGN_FRONTEND_UX.md (sections 4.2–4.4) still references "tile-small/medium/large" grid ordering and the removed RunState card. Update to describe flow-based zones (Control Cluster, Streams, Signals, Pipeline) and semantic `data-role` markers.
- docs/design/UI_VISUAL_DESIGN_SPEC.md (lines ~290-430) defines `.bento-tile` variables and layout classes that no longer exist. Needs rewrite to cover adaptive flow tokens and composite panels.
- docs/reports/ux-validation/UX_VISUAL_DIAGNOSIS_REPORT.md + MOBILE_QUICKACTIONS_FIX_VALIDATION.md embed 2024 screenshots (vertical pillars). Replace with new captures from Chrome DevTools once flow layout proof is ready.
- docs/reports/ux-validation/UX_FIX_VALIDATION_REPORT.md Section "Quick Actions Component" still assumes Quick Actions is a standalone tile lacking run state. Update narrative + evidence with new composite card.

## Process / status metadata out of date
- docs/INDEX.md header still shows **Last Updated 2024-11-04**; bump after refresh and mention doc alignment spec.
- README badges/sections lack "Last Validated" row listing lint/type-check/vitest/Playwright/act runs. Add for traceability.
- No centralized location for screenshot assets; create `docs/assets/dashboard/` with metadata README.

## Next actions
1. Implement non-blocking bootstrap script.
2. Capture new dashboard screenshots via MCP after running the script.
3. Update documents listed above and link to assets.
4. Reflect verification commands + timestamp in README/docs.

## 2025-11-13 updates
- Added Playwright coverage for the documented flows (`tests/e2e/login-flow.spec.ts`, `tests/e2e/dashboard-interactions.spec.ts`) so README commands map to real specs.
- Realigned `tests/e2e/accessibility.spec.ts` with the flow-based dashboard experience and documented the temporary Axe rule suppressions (`color-contrast`, `list`, `scrollable-region-focusable`).
- `scripts/dev_env_daemon.sh` + MCP audit tooling now gate every Playwright suite; regression evidence (screenshots, traces) land back in `frontend/test-results/`.

## 2025-11-14 updates
- `README.md`/`README.en.md` now embed the `2025-11-14` flow screenshot, describe `scripts/mcp_chrome_runner.js`, and list the exact lint/vitest/Playwright/act commands run.
- `docs/assets/dashboard/README.md` lists the new desktop+laptop captures plus the CLI used to reproduce them; `docs/testing/uat/UAT_REAL_TESTING_RESULTS.md` references the same asset.
- 新增 `docs/coding-standards.md`，集中记录前后端 lint/测试/CI/LHCI/MCP 约定，并在 README 链接，方便审阅编码标准。
