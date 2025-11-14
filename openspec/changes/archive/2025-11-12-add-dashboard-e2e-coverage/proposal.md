# Add dashboard E2E coverage

## Why
The current Playwright quick smoke spec only checks that the dashboard shell renders. Large areas remain untested:
- Login flow success/failure paths.
- Key dashboard interactions (selecting map entities, toggling quick actions, verifying pipeline state updates).
- Accessibility checks for skip link / focus order.
Without these, regressions slip into CI undetected and we have no automated guarantee that the page remains functional across devices.

## What changes
1. Expand the E2E suite with targeted dashboard specs that exercise login, core tile interactions, and quick actions across desktop + tablet viewports.
2. Add coverage reporting (Playwright JSON + summary) so we can track how many critical scenarios run in CI.
3. Update the `frontend-quality` capability to codify these requirements.

## Impact
- Touches Playwright config, adds new specs, and possibly lightweight fixtures/mocks.
- Requires rerunning `npm run test:e2e -- quick-e2e.spec.js` (for smoke) and the new targeted spec.
