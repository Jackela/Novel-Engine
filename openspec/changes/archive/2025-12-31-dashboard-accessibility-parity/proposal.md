# Proposal: Dashboard Interaction Accessibility & Data Parity

## Why
- MCP audit evidence (devtools snapshot `mcp__chrome-devtools__take_snapshot` ids 8_85-8_219) shows the spatial, network, and timeline tiles render as pointer-only `div`s. Keyboard users cannot activate map markers, character cards, or timeline entries, violating the `dashboard-interactions` spec scenarios that require keyboard activation.
- Quick Actions leak the custom `active` prop down to native `<button>` elements (`frontend/src/components/dashboard/QuickActions.tsx:27-55`), triggering persistent React console warnings (`list_console_messages` msgid 141) and offering inconsistent focus outlines.
- Spatial/Network tiles still ship with hard-coded demo data (`WorldStateMapV2` locations array, `CharacterNetworks` `useState` stub) and never reconcile against `GET /characters` or related endpoints, so the UI cannot meet audit step §9 (API validation). The dashboard has effectively never rendered real payloads.

## Evidence
- MCP audit snapshot: `mcp__chrome-devtools__take_snapshot` ids 8_85-8_219
- Console warnings: `list_console_messages` msgid 141 (invalid DOM props)

## Acceptance Criteria
- Keyboard users can activate map markers, character cards, and timeline entries with Enter/Space; focus/ARIA states update without console warnings.
- Map + network tiles render API-sourced character data from `/api/characters` (with fallback data if offline), and show the correct “API feed” or “Demo data” badge.
- Quick Actions renders without leaking custom props and exposes consistent `:focus-visible` styling and `aria-pressed` state changes.

## What Changes
1. **Keyboard semantics** – Implement roving tab index/focus management for map markers, character cards, and timeline nodes. Support Space/Enter activation, `aria-selected`/`aria-expanded` states, and deterministic selectors so Playwright/MCP can assert them.
2. **QuickAction hygiene** – Prevent custom props from leaking to DOM, add explicit `:focus-visible` styles, and ensure telemetry buttons announce state changes via `aria-pressed` or text updates without console noise.
3. **API-backed data** – Replace the stubbed arrays in `WorldStateMapV2` and `CharacterNetworks` with data fetched from `/characters` (and supporting endpoints) so the UI reflects backend state. Provide fallbacks for offline/demo but keep markers/cards in sync with the payload (names, trust stats, etc.).
4. **Tests first** – Extend the dashboard interaction/unit tests (Vitest + Testing Library) to cover keyboard activation paths, `aria` attributes, and API wiring before implementing the fixes, honoring the TDD request.

## Impact
- Specs touched: `dashboard-interactions` (new accessible-interaction scenarios, backend data parity requirement).
- Code touched: `frontend/src/components/dashboard/{WorldStateMapV2,CharacterNetworks,NarrativeTimeline,QuickActions}.tsx`, shared hooks/services for `/characters`, related tests under `frontend/src/components/dashboard/__tests__` (or create `__tests__`).
- Tooling: Update mocks (MSW or local fixtures) used by tests; Playwright accessibility spec may need selectors for `aria-selected` states. Lint/type/test suites plus targeted Playwright `dashboard-accessibility` flow must run.
