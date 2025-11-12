## Why
- MCP snapshot of `/login` (see `tmp/snapshots/home.json`) shows a single-card layout with only two inputs and no contextual guidance.
- Stakeholders asked to "Use mcp(chrome dev tools) to debug and improve the UI/UX", and the login entry point is the only unauthenticated surface users see.
- Current UX gaps:
  - No product framing or reassurance about why users should sign in.
  - Validation feedback is limited to a single alert banner.
  - No quick path to demo credentials or support when auth is misconfigured.

## What Changes
- Redesign the login page into a responsive split layout (hero panel + form panel) that introduces Novel Engine benefits and provides contextual help.
- Elevate the form with inline validation, helper text, and utility actions (password toggle, remember me, demo mode hints).
- Add structured support affordances (contact link, status chip) driven by existing config flags so operators can toggle messaging without code edits.

## Success Criteria
- Desktop view shows a two-column layout with hero copy on the left and the form on the right; narrow screens gracefully collapse to a single column.
- Users receive real-time validation feedback without scrolling, and the submit button communicates loading state.
- When `demoMode` is enabled, the UI surfaces demo credentials info inline; when disabled, a "Need access?" link guides users to support.
