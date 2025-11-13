## ADDED Requirements

### Requirement: Connection indicator reflects offline recovery
The dashboard connection indicator MUST expose deterministic states (LIVE/ONLINE/STANDBY/OFFLINE) with `data-status` attributes so automated tests can assert behaviour during network interruptions and recovery.

#### Scenario: Offline transition and recovery
- **GIVEN** the dashboard renders the connection indicator (`data-testid="connection-status"`/`data-testid="live-indicator"`)
- **WHEN** network access drops (simulated via `page.context().setOffline(true)`)
- **THEN** the indicator switches to `data-status="offline"`, shows the OFFLINE label, and announces the change via `aria-live="polite"`
- **AND** once connectivity returns the indicator flips back to ONLINE/LIVE and the guest/summary strip timestamps resume updating.
