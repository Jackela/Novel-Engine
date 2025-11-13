# Proposal: add-guest-access-entrypoint

## Why
- Current frontend immediately redirects to `/login`, which is unimplemented, blocking all demo exploration.
- Guest/demo mode already exists in AuthContext but isn’t exposed in the UI or landing flow.
- Stakeholders need a quick way to showcase the dashboard without wiring production auth yet.

## What
1. Add a lightweight landing screen (`/`) with product messaging and two CTAs: “View Demo” (uses guest session) and “Request Access”.
2. When guest mode is enabled, clicking “View Demo” authenticates the user via the existing guest token flow and routes to the dashboard without reloading.
3. Surface guest-state in the dashboard header (badge + tooltip) plus a dismissible info banner linking to docs.
4. Update Playwright smoke test to exercise the demo CTA.

## Success Criteria
- Demo CTA brings users to an interactive dashboard with no manual env edits.
- Guest badge/banner informs users they are in demo mode and can be dismissed for the session.
- Regression tests (npm lint/type-check/test + Playwright flow) pass.
