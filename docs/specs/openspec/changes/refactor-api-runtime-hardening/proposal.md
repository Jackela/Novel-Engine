# Change: Refactor API runtime hardening

## Why
Production and streaming endpoints have blocking calls, inconsistent security middleware wiring, and weak CORS/auth handling that can degrade performance or expose credentials.

## What Changes
- Enforce non-blocking SSE streaming and correct disconnect handling.
- Require baseline security headers on API responses.
- Require credential handling to avoid query-string auth parameters.
- Normalize production CORS to avoid wildcard origins with credentials.

## Impact
- Affected specs: api-surface, realtime-events-api
- Affected code: production_api_server.py, src/api/main_api_server.py, auth endpoints, SSE streaming
