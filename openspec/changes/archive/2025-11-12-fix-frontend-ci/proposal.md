# Fix frontend CI regressions

## Why
Recent CI runs surfaced deterministic failures:
- `npm run lint` currently trips 14 jsx-a11y errors and 1 TypeScript lint warning (see `frontend/src/components/AgentInterface.tsx:355,369`, `PerformanceOptimizer.tsx:327-347`, `NarrativeDisplay.tsx:238`, `Badge.tsx:97`, etc.) plus unused-var violations in `useFocusTrap` and `WebVitalsMonitor`. These break the shared CI entrypoint introduced by `ci-parity` and block deploys.
- `npm run test:e2e -- quick-e2e.spec.js` exits with “No tests found” because the repo doesn’t ship a `quick-e2e.spec` file, so the supposed smoke gate never executes.
We need the dashboard/frontend surface to satisfy accessibility lint rules and ensure the quick smoke Playwright command actually validates something so CI jobs go green.

## What Changes
- Bring every failing component up to the lint baseline by adding `htmlFor`+`id` pairs for labels, converting clickable `<div>`s into semantic buttons or adding keyboard handlers+roles, and handling unused vars via refactors.
- Add/update the quick Playwright smoke spec (or the npm script) so `npm run test:e2e -- quick-e2e.spec.js` actually targets an existing file containing at least one lightweight dashboard test.
- Document these expectations in a new `frontend-quality` capability so future contributions keep forms labeled, clickable surfaces keyboard accessible, and the quick smoke suite wired into CI.

## Impact
- Touches multiple frontend components (AgentInterface, PerformanceOptimizer, NarrativeDisplay, Badge, Step wizards, etc.) plus the Playwright tests folder.
- No backend impact; only TypeScript/React + Playwright assets change.
- Developers must rerun `npm run lint` and the quick Playwright command locally to verify compliance.
