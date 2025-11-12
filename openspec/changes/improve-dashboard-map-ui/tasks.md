## 1. Implementation
- [x] Update `EmergentDashboardSimple` to attach richer metadata to `worldEntities`, render a detail panel that reacts to selection, and keep only one selected state at a time.
- [x] Introduce a timer-driven timestamp/telemetry label with `aria-live="polite"` so the "Live" indicator updates at least every 30 seconds even when no other renders happen.
- [x] Rework the duplicate quick-actions tile into a single run-state summary that reuses the existing start/pause/stop/refresh controls without duplicating focusable buttons.
- [x] Add React Testing Library coverage that simulates selecting different entities, asserts the detail panel content, and verifies the run-state summary reflects state transitions.

## 2. Validation
- [x] `cd frontend && npm test -- EmergentDashboardSimple`
