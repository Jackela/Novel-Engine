## ADDED Requirements

### Requirement: Telemetry dispatcher for connection indicator
The frontend MUST expose a `window.__novelEngineTelemetry` (or equivalent) emitter that receives connection-indicator events so observability pipelines can collect outage stats.

#### Scenario: Telemetry event emitted on status change
- **WHEN** the connection indicator transitions (e.g., ONLINE → OFFLINE)
- **THEN** an event `{ type: 'connection-indicator', status, previous, timestamp }` is emitted via the dispatcher in addition to console logs.
