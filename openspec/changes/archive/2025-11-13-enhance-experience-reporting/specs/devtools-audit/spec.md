## ADDED Requirements

### Requirement: Connection indicator logging hook
Whenever the UI connection indicator changes status (ONLINE/LIVE/STANDBY/OFFLINE), the frontend MUST emit a structured console log (and optional metrics hook) so experience reports and telemetry can trace outage frequency.

#### Scenario: Console log on offline transition
- **WHEN** the indicator switches to OFFLINE
- **THEN** the app logs `connection-indicator:offline` with timestamp and relevant context (e.g., pipeline status)
- **AND** when connectivity resumes, a matching `connection-indicator:online` log is emitted.
