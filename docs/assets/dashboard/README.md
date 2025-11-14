# Dashboard Evidence Assets

| File | Viewport | Source | Notes |
| --- | --- | --- | --- |
| dashboard-flow-2025-11-14-condensed.png | Desktop 1440×900 | `node scripts/mcp_chrome_runner.js --viewport 1440x900 --screenshot docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png --metadata docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.json` | Condensed control band + telemetry row evidence |
| dashboard-flow-2025-11-14-laptop.png | Laptop 1366×768 | `node scripts/mcp_chrome_runner.js --viewport 1366x768` | Confirms flow layout under constrained width |
| dashboard-flow-2025-11-12.png | Desktop 1440px | Chrome DevTools (manual) | Legacy capture retained for before/after comparisons |

> Capture procedure: run `npm run dev:daemon`, then execute  
> `node scripts/mcp_chrome_runner.js --url http://127.0.0.1:3000/dashboard --viewport WIDTHxHEIGHT --screenshot docs/assets/dashboard/dashboard-flow-YYYY-MM-DD[SUFFIX].png --metadata docs/assets/dashboard/dashboard-flow-YYYY-MM-DD[SUFFIX].json`.  
> The script clicks the Demo CTA, waits for `data-role="control-cluster"` + `data-role="stream-feed"` to render, and stores PNG/JSON in this folder. For mobile evidence, pass the desired viewport (e.g., `428x926`) and append `-mobile` to the filename.
