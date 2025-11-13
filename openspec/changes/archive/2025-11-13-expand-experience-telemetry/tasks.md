## Task List

1. **Specs**
   - [ ] Update `frontend-quality` spec to require dual-format (Markdown + HTML) experience reports with summary tables/screenshot references.
   - [ ] Update `devtools-audit` spec with a requirement for broadcasting connection-indicator events to a telemetry dispatcher (window/global bus or API).
   - [ ] Update `docs-alignment` spec to document report download steps, HTML interpretation, and telemetry subscription APIs.
2. **Implementation**
   - [ ] Enhance the report generator to emit HTML (and optional JSON) alongside Markdown; ensure CI uploads both files.
   - [ ] Implement a telemetry dispatcher (e.g., `window.__novelEngineTelemetry.emit`) and wire connection indicator events to it, keeping console logs for backward compatibility.
   - [ ] Update README/onboarding docs with artifact download instructions, HTML report screenshots, and telemetry usage notes.
3. **Validation**
   - [ ] Run lint/type-check/vitest.
   - [ ] Run Playwright smoke + full suites to regenerate reports and confirm telemetry hooks behave (no console errors).
