# Proposal: reinforce-demo-entry-validation

## Why
- Chrome-only E2E currently bypasses the landing-to-dashboard journey via `SKIP_DASHBOARD_VERIFY`, so regressions in the demo CTA/guest flow can ship unnoticed.
- The new offline indicator and summary strip lack spec coverage; without requirements the UI could silently drop accessibility/ARIA cues that are part of the intended experience.
- Stakeholders asked for “严谨体验” (experience rigor) to guarantee visible cues (demo entry + offline state) always match the design baseline.

## What
1. Extend `frontend-quality` specs to require a Playwright path that starts at `/`, activates the “View Demo” CTA, observes the guest banner, and reaches the dashboard without manual flags.
2. Extend `dashboard-interactions` specs to cover the connection indicator/offline banner behaviour (ARIA, copy, state transitions) during network interruptions.
3. Track the implementation via tasks that add/adjust Playwright coverage and remove the remaining skips once the flows are reliable.

## Success Criteria
- New requirements appear in the relevant specs with scenarios describing the CTA journey and offline indicator behaviour.
- Tasks call out the Playwright updates plus any supporting code (e.g., deterministic selectors, offline banner state) needed to satisfy the specs.
- `openspec validate reinforce-demo-entry-validation --strict` passes.
