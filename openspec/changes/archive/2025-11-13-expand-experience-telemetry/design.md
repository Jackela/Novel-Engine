# Design: expand-experience-telemetry

## Reporting
- Extend the existing Node script to consume Playwright JSON and output:
  - `experience-report-<ts>.md` (existing)
  - `experience-report-<ts>.html` with summary badges/tables and screenshot thumbnails
  - optional JSON payload for future aggregations
- Use a simple template literal (or e.g., `marked`) to avoid heavy dependencies.
- Ensure GitHub Actions uploads both Markdown and HTML artifacts.

## Telemetry Dispatcher
- Introduce `window.__novelEngineTelemetry = { emit(event, payload) }` (if not present) and emit events such as `{ type: 'connection-indicator', status, previous, timestamp }`.
- Connection indicator component calls both `console.info` and `window.__novelEngineTelemetry.emit`.
- Future backend hook can subscribe to this dispatcher without changing UI components.

## Documentation
- README/onboarding sections show how to download the HTML report artifact, interpret pass/fail badges, and listen to telemetry events (e.g., via browser console `window.__novelEngineTelemetry.subscribe`).
