# MCP Manual Audit Plan (Chrome DevTools MCP)

This plan covers **all known routes, UI zones, and backend endpoints** in Novel Engine. Execute it sequentially to capture screenshots, DOM evidence, and behavioral notes with Chrome DevTools MCP.

---

## 0. Preflight

1. **Start services** (logs → `tmp/dev_env/*.log`):
   ```bash
   npm run dev:daemon
   ```
2. **Launch Chrome with remote debugging**:
   ```bash
   google-chrome \
     --remote-debugging-port=9222 \
     --user-data-dir=/tmp/mcp-chrome \
     --no-first-run --no-default-browser-check about:blank
   ```
3. **Record `browserWSEndpoint`** from `http://127.0.0.1:9222/json/version` and use it for all `chrome-devtools/*` calls.
4. **Artifact naming**: store screenshots under `docs/assets/audit/YYYYMMDD_<section>.png` and reference them in the final report.
   - Latest captures:
     - `docs/assets/audit/20251116_landing.png` (landing hero, CTAs)
     - `docs/assets/audit/20251116_dashboard_online_chip.png` (dashboard fold w/ API feed chips, ONLINE connection chip, demo perf badge)
     - `docs/assets/audit/20251116_dashboard_fold.png` (full fold reference)
     - `docs/assets/audit/20251116_map_network_v2.png` (world map + character networks tiles)
     - `docs/assets/audit/20251116_dashboard_api_metrics_live.png` (dashboard fold showing API metrics label)
     - `docs/assets/audit/20251115_dashboard_api_feed_polish_v4.png` (previous reference)

---

## 1. Route & Documentation Recon

| Route | Expected view | Source |
| --- | --- | --- |
| `/` | Landing page + CTA | `frontend/src/pages/LandingPage.tsx` |
| `/dashboard` | Protected dashboard | `frontend/src/components/dashboard/*` |
| `/login` | Placeholder view | `frontend/src/App.tsx` |
| `*` | Redirects to `/` | Router |

Before inspecting UI, skim:
- `docs/design/DESIGN_FRONTEND_UX.md` (layout intent)
- `openspec/specs/dashboard-layout/spec.md`
- `docs/coding-standards.md` (selectors & tooling expectations)

Summarize any requirements you need to verify (e.g., control band ≤180 px, `data-role` semantics).

---

## 2. Landing Page (`/`)

### 2.1 Accessibility & Structure
1. `chrome-devtools/new_page → http://127.0.0.1:3000/`.
2. Using MCP keyboard events:
   - `Tab` → confirm focus on “Skip to main content”.
   - `Enter` → verify focus moves to `#main-content`.
3. Inspect hero copy, CTA container (`data-testid="cta-container"`), and three feature bullet points. Capture screenshot `landing_hero.png`.

### 2.2 CTA Interactions
1. **View Demo**:
   - Click via MCP mouse and keyboard.
   - Expect `AuthContext.enterGuestMode()` to set `sessionStorage['novel-engine-guest-session']='1'` and redirect to `/dashboard`.
   - Validate session via MCP console.
2. **Request Access**: ensure `mailto:ops@novel-engine.ai` triggers (watch network entries).
3. Reload `/dashboard` to confirm guest auto-login.

### 2.3 Error & Login Routes
1. Open `/login`: verify placeholder message.
2. Navigate to `/foo/bar`: ensure redirect to `/`.
3. (Optional) Intentionally throw from console to ensure `ErrorBoundary` renders fallback UI.

Artifacts: screenshots + notes on navigation speed, focus states, text contrast.

---

## 3. Dashboard – Global Layout

### 3.1 Entry Checks
1. Confirm `ProtectedRoute` allowed guest access (no unexpected redirects).
2. Capture entire first fold screenshot `dashboard_fold_desktop.png`.
3. Using `document.querySelector('[data-testid="dashboard-layout"]')`, confirm `role="main"` / `tabIndex=-1`.

### 3.2 Navigation & Skip Link
1. Tab across header, skip link, summary strip, QuickActions, Stream zone, Map.
2. Record any missing `:focus-visible` styles.

---

## 4. Control Cluster (SummaryStrip + QuickActions)

### 4.1 SummaryStrip
1. Record `lastUpdate` before/after hitting Refresh.
2. Simulate offline via DevTools → verify chips switch to OFFLINE state.
3. Screenshot `dashboard_control_cluster.png`.

### 4.2 QuickActions
For each button (`play`, `pause`, `stop`, `refresh`, `save`, `settings`, `fullscreen`, `export`):
1. Trigger via MCP.
2. Record Snackbar message, pipeline status, and connection indicator text (from `[data-testid="connection-status"]`).
3. Check ARIA labels & focus outlines.

---

## 5. Streams, Pipeline, Timeline

### 5.1 Real-time Activity (`data-role="stream-feed"`)
1. Verify `dataset.density === 'condensed'` (desktop).
2. Scroll to ensure virtualization doesn’t clip content.
3. After a new event arrives (≈5s), capture screenshot `stream_activity.png`.

### 5.2 Turn Pipeline (`data-role="pipeline"`)
1. Click Play; watch chips update through all five phases.
2. Check `data-status` attributes (processing/completed) and live chip visibility.
3. Save screenshot mid-run `pipeline_live.png`.

### 5.3 Narrative Timeline
1. Inspect current turn indicator.
2. Ensure keyboard focus can reach timeline entries.

---

## 6. Spatial & Network Zones

### 6.1 World State Map (`data-role="hero-map"`)
1. Click each location marker and verify expanded character lists.
2. Validate stats chips (Total Characters, Active) match design.
3. Screenshot `world_state_map.png`.

### 6.2 Character Networks (`data-role="network-visuals"`)
1. Confirm chips show counts (characters, links, active).
2. Hover/focus cards; note trust bar behavior.
3. Capture `character_networks.png`.

---

## 7. System Signals & Analytics

1. Inspect Performance Metrics (health status text, metric rows).
2. Scroll Event Cascade / Analytics; ensure no overflow or broken charts.
3. Screenshot `system_signals.png`.

---

## 8. Accessibility & Keyboard Journey

1. Tab through entire dashboard; list any components without focus indicators.
2. Inspect `aria-live` regions (`[data-testid="live-indicator"]`) for connection announcements.
3. Validate skip link still visible from dashboard top.
4. Record issues with severity (Blocker/High/Medium/Low).

---

## 9. Backend & API Validation

Using shell outside MCP:
1. `curl http://127.0.0.1:8000/health` – log JSON to audit report.
2. Additional endpoints (see `api_server.py`):
   - `/api/characters` (primary feed)
   - `/api/characters/{id}`
   - `/characters` (legacy shim; keep for regression when API is down)
   - `/campaigns`
   - `/cache/metrics`
3. Cross-check UI data (e.g., character names on map) with `/api/v1/characters` payloads; confirm dashboard chips show “API feed” only when that endpoint succeeds.
4. Tail `tmp/dev_env/backend.log` during dashboard usage to catch errors.

---

## 10. Observability & Service Worker

1. Check console for Service Worker logs (`initializeMobileOptimizations`).
2. Trigger `navigator.onLine` false via DevTools Network Offline, observe UI reaction (control cluster chips, Snackbars).
3. Inspect `window.performance` metrics logged by `usePerformance`.

---

## 11. Documentation & Findings

1. For each section, record:
   - Screenshot path.
   - DOM snippets / console logs supporting observations.
   - Severity + suggested fix (file/component references).
2. Summarize issues in a table:
   | ID | Area | Severity | Description | Evidence | Proposed Fix |
3. Update `docs/testing/uat/UAT_REAL_TESTING_RESULTS.md` with:
   - Audit date/time
   - Commands used (daemon, MCP, curls)
   - Link to artifact folder
4. File issues or OpenSpec changes if new requirements emerge.

---

Follow this plan to perform a **complete**, multi-modal MPC audit of Novel Engine, ensuring no route or component is skipped. Capture everything so the team can act on the findings quickly.
