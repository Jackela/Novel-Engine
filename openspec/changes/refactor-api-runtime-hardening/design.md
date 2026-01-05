## Context
- Production server uses middleware signatures that can bypass security headers.
- SSE stream uses blocking sleeps and does not explicitly handle asyncio.CancelledError.
- Auth endpoint accepts credentials via query params.
- CORS allows wildcard origins while enabling credentials.

## Goals / Non-Goals
- Goals: non-blocking SSE, reliable security headers, safer auth input, and CORS alignment with credentials.
- Non-Goals: redesigning API surface, introducing new auth providers, or refactoring unrelated endpoints.

## Decisions
- Use FastAPI-compatible middleware (BaseHTTPMiddleware or proper ASGI signature) for security headers.
- Convert blocking sleep calls in async endpoints to awaitable asyncio.sleep.
- Accept auth credentials via JSON body and reject query parameters.
- Require explicit allowed origins when allow_credentials is true.

## Risks / Trade-offs
- Tighter CORS may require updating deployment configs for allowed origins.
- Auth input change may require clients to update requests.

## Migration Plan
- Update server config defaults and documentation.
- Provide a temporary compatibility window if needed (documented in code and release notes).

## Open Questions
- Which server entrypoint is authoritative for production: production_api_server.py or src/api/main_api_server.py?
