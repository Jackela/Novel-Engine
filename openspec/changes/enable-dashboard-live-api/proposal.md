# Proposal: Enable Dashboard Live API Integration

## Why
- The dashboard's RealTimeActivity component currently uses `useRealtimeEvents` hook which polls `/api/events` every 8 seconds, but this endpoint doesn't exist in any backend API server (api_server.py, production_api_server.py, or main_api_server.py), forcing fallback to demo/sample data.
- Current implementation seeds demo events with hardcoded `INITIAL_EVENTS` and interval-based simulation (every 5 seconds), showing "Live Feed (sample)" because the API endpoint returns errors.
- Performance metrics widget displays hardcoded demo data (responseTime, errorRate, requestsPerSecond) but should be reserved for developer/admin visibility only, showing Web Vitals monitoring rather than business metrics.
- Environment configuration is inconsistent: mix of `REACT_APP_*` (legacy Create React App) and `VITE_*` prefixes, with `VITE_DASHBOARD_EVENTS_ENDPOINT` referencing a non-existent endpoint.
- The dashboard-data-routing-hygiene change established `/api/v1/characters` as the canonical endpoint pattern, but events and metrics don't follow this versioning convention.
- Polling creates unnecessary backend load; real-time event streaming requires Server-Sent Events (SSE) or WebSocket for efficient live updates.
- Without proper error handling, users see sample data without clear indication that API integration failed, reducing trust in dashboard data.

## What Changes
1. **Backend SSE Endpoint** – Implement `/api/v1/events/stream` as a Server-Sent Events endpoint returning real-time event streams with payload: `{id, type, title, description, timestamp, characterName?, severity}`. Follow the `/api/v1/*` versioning pattern established by dashboard-data-routing-hygiene.

2. **Frontend SSE Integration** – Migrate `useRealtimeEvents` hook from HTTP polling to SSE subscription using EventSource API. Remove demo data fallback logic; show clear error state when API connection fails. Update RealTimeActivity component to display connection errors with actionable messages.

3. **Performance Metrics RBAC** – Add role-based visibility to PerformanceMetrics widget; only show to authenticated developers/admins. Continue displaying Web Vitals (LCP, FID, CLS, FCP, TTFB) for browser performance monitoring. Remove hardcoded demo metrics (responseTime, errorRate, etc.) from UI.

4. **Environment Config Standardization** – Migrate all dashboard environment variables to `VITE_*` prefix. Create comprehensive `.env.example` section documenting all dashboard endpoints: `VITE_DASHBOARD_EVENTS_ENDPOINT` (default: `/api/v1/events/stream`), `VITE_API_BASE_URL` (default: `http://localhost:8000`). Update Vite proxy configuration to map `/api/v1/*` → backend API server.

5. **Testing & Validation** – Add integration tests for SSE connection/reconnection scenarios, error state handling when API unavailable, role-based Performance widget visibility, and API endpoint contract validation. Extend dashboard-accessibility test suite to verify error messages are accessible.

## Impact
- Specs touched: Create new `realtime-events-api` (backend SSE), `realtime-events-frontend` (SSE integration), `dashboard-config-standards` (environment vars), `performance-metrics-rbac` (role visibility). Aligns with existing `dashboard-interactions` from dashboard-data-routing-hygiene.
- Code touched:
  - Backend: Create `/api/v1/events/stream` endpoint in main_api_server.py with SSE event generator
  - Frontend: `frontend/src/hooks/useRealtimeEvents.ts` (SSE migration), `frontend/src/components/dashboard/RealTimeActivity.tsx` (error UI), `frontend/src/components/dashboard/PerformanceMetrics.tsx` (RBAC check), `frontend/vite.config.ts` (proxy config)
  - Config: `.env.example` (dashboard section), remove `REACT_APP_*` references
  - Tests: New `frontend/src/hooks/__tests__/useRealtimeEvents.test.tsx`, extend `frontend/tests/integration/accessibility/` for error states
- Tooling: Run `npm run lint`, `npm run type-check`, full `npx vitest run`. Update UAT log to document SSE integration and error state testing.
- Dependencies: Builds on `dashboard-data-routing-hygiene` (canonical `/api/v1/*` pattern). Requires authentication/role system for Performance widget RBAC.

## Out of Scope
- WebSocket implementation (SSE sufficient for unidirectional event streaming)
- Backend system metrics endpoint (Performance widget stays Web Vitals only)
- Demo data fallback mode (error states only when API unavailable)
- Multiple API versions (single `/api/v1/*` pattern)
