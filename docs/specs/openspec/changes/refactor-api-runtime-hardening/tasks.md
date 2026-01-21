## 1. Implementation
- [x] 1.1 Confirm production entrypoint and scope (production_api_server.py vs src/api/main_api_server.py).
- [x] 1.2 Update SSE streaming to use async sleep and handle asyncio.CancelledError.
- [x] 1.3 Replace blocking sleeps in async handlers with awaitable equivalents.
- [x] 1.4 Fix security headers middleware wiring for production.
- [x] 1.5 Update auth endpoint to accept JSON body credentials and reject query params.
- [x] 1.6 Align CORS configuration to disallow wildcard origins when allow_credentials is true.
- [x] 1.7 Add/adjust tests for SSE behavior and auth input validation.
- [x] 1.8 Run full regression suite per OpenSpec validation gate.
