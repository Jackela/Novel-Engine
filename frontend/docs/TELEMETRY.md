# Telemetry & Experience Reports

## Generating Reports
- `npm run test:e2e:smoke`: runs the smoke suite (< 1 minute) and writes Markdown + HTML + JSON reports to `frontend/reports/experience-report-*.{md,html,json}`.
- `npm run test:e2e`: runs the full suite and writes the same reports.
- In CI (GitHub Actions), both Markdown and HTML reports are uploaded as the `experience-report` artifact **and** a condensed CTA/offline table is appended to the GitHub job summary for quick review.

## HTML Summary (experience-report-*.html)
- Includes badges for Demo CTA flow and connection offline recovery.
- Lists duration and short descriptions for each scenario.
- Links to screenshots (when Playwright captures them).

## Downloading from CI
1. Open the workflow run (PR smoke or main nightly).
2. Scroll to "Artifacts" and download `experience-report`.
3. Extract to find `.md` and `.html` versions.

## Telemetry Dispatcher
```ts
window.__novelEngineTelemetry?.subscribe?.(event => {
  if (event.type === 'connection-indicator') {
    console.log('Connection status', event.payload);
  }
});
```
- Events include `status`, `previous`, `pipelineStatus`, `timestamp`.
- Use this hook to experiment with dashboards or automated alerts.
