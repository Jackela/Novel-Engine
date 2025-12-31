# Proposal: Refactor Frontend API Layer + Make the App “Real Usable”

## Why
- The frontend currently contains multiple overlapping API layers (services + hooks) and mismatched endpoint assumptions, which makes it easy to regress integration when backend contracts change.
- Some user-facing areas still behave like demos (sample fallbacks, inconsistent error states) rather than a reliable product surface.
- Long-term refactors need a stable frontend foundation: one API client, predictable data-fetching patterns, and complete guest-first flows.

## What Changes
1. **Single API client (SSOT)**
   - Introduce one typed client wrapper used by all hooks/components; standardize base URL, headers, and error handling.
2. **Guest-first session bootstrap**
   - Make “start/resume guest session” a first-class part of app initialization so persistence survives refreshes.
3. **Real usable flows**
   - Ensure users can: enter as guest, manage characters, run a simulation/story, and reload the page without losing their workspace state.
4. **UX reliability**
   - Standardize loading/empty/error states and add actionable messages when backend is unavailable.

## Dependencies
- Depends on `standardize-api-surface` so frontend endpoints have a stable base.
- Benefits from `add-filesystem-guest-workspaces` so “usable flows” have durable persistence.

