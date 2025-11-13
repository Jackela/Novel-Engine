# Design: enhance-experience-reporting

## Overview
We want better visibility into the demo CTA/offline flow without bloating CI time. We’ll add reporting/logging features on top of the existing Playwright runs and CI pipeline.

## Experience Report
- Leverage Playwright’s JSON output + a small Node script to emit a Markdown/HTML summary (`reports/experience-report.<md|html>`).
- Report highlights: landing CTA success, guest banner/summary strip assertions, offline indicator transitions (with timestamps), key screenshots.
- Wire the script via `npm run test:e2e:report` or as part of the existing Playwright command in CI.

## Observability Hooks
- Extend the connection indicator component (QuickActions/SummaryStrip) to log `console.info` events when status changes (`offline`, `online`, `live`). Later we can forward these to telemetry but start with console logs to satisfy spec.

## CI Split
- Add `npm run test:e2e:smoke` to run the CTA + offline tests only (expected <1 min). Default CI workflow for PRs runs smoke; nightly/merge uses full `npm run test:e2e`.
- Document the split in `README` + `docs/`.

## Documentation
- README / onboarding doc gains sections about running demo CTA flow locally, simulating offline (`page.context().setOffline` equivalent via scripts), and new env vars (`PLAYWRIGHT_VERIFY_ATTEMPTS`, etc.).
