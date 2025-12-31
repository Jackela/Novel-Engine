# Change: Refactor dashboard experience resilience

## Why
- Dashboard smoke/e2e flows rely on mock/guest data; current rendering can stall behind skeletons or missing panels, breaking reliability and accessibility during offline/fallback runs.
- World/pipeline tiles need consistent fallbacks so connection/offline indicators and map states stay assertable when APIs are degraded.

## What Changes
- Add deterministic fallback rendering for core dashboard panels (world map, pipeline, log) with time-bounded skeleton teardown.
- Ensure offline/guest contexts still surface connection/liveness state and dataset badges for testing and accessibility.
- Align smoke/e2e expectations around fallback data and loading timelines.

## Impact
- Affected specs: `dashboard-interactions`
- Affected code: dashboard panels (world map/pipeline/log), skeleton handling, smoke/e2e fixtures.
