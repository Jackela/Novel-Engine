# Dashboard Evidence Assets

| File | Viewport | Source | Notes |
| --- | --- | --- | --- |
| dashboard-flow-2025-11-12.png | Desktop 1440px | Chrome DevTools (daemon stack) | Summary Strip + Control Cluster + Streams + Signals + Pipeline visible |

> Capture procedure: run `npm run dev:daemon`, open Chrome DevTools (MCP) to `http://127.0.0.1:3000`, wait for `data-role="control-cluster"` and `data-role="stream-feed"` to render, and use the screenshot tool. Save raw captures into this folder with the naming convention `dashboard-flow-YYYY-MM-DD[optional-suffix].png`. For mobile evidence, use Chrome's device toolbar and append `-mobile` to the filename when the capture succeeds.
