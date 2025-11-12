## Task List

1. **Density Heuristics**
   - [x] Implement shared helper(s) to classify zones into relaxed/compact modes based on content size + thresholds.
   - [x] Emit semantic attributes (`data-density`, `data-volume`) via `DashboardZones` and pass density props to child panels.
2. **Control Cluster Adjustments**
   - [x] Update `QuickActions` and run summary layout to respond to density setting (spacing, typography, optional text elision).
   - [x] Ensure pipeline tile reflects density (e.g., condensed chip stack, optional virtualization when compact).
3. **Streams & Signals Panels**
   - [x] Make `NarrativeActivityPanel` shrink/expand via density (tabs vs. dual column, list height caps, scroll cues).
   - [x] Make `SystemSignalsPanel` adjust metrics/event presentation (chip size, virtualization) when density is compact.
4. **Styling Tokens**
   - [x] Extend dashboard CSS with attribute-based selectors for `data-density` (padding, type scale, chip/badge sizing).
   - [x] Add optional CSS variables so future AI routines can override density globally.
5. **Testing & Validation**
   - [x] Add unit tests for density helper(s) and zone props.
   - [x] Update Playwright specs/page object to assert density markers; run lint, type-check, vitest, Playwright suites, and `act` parity jobs.
