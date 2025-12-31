## ADDED Requirements
### Requirement: Automated MCP dashboard capture
The project MUST provide a documented CLI script that launches headless Chrome, drives the landing CTA, captures the dashboard screenshot, and emits metadata for evidence tracking.

#### Scenario: Snapshot command succeeds
- **WHEN** developers run `node scripts/mcp_chrome_runner.js --url http://127.0.0.1:3000/dashboard`
- **THEN** the script auto-clicks the `data-testid="cta-demo"` button if the landing page is visible, waits for `data-role="control-cluster"` to render, and saves both a PNG and JSON file under `docs/assets/dashboard/`.
- **AND** the JSON records at minimum `title`, `url`, `connectionStatus`, `pipelinePhase`, and `viewport` so README/docs can reference the live layout state.
