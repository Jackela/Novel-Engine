# Environment Flags for Mock/Stub Control

This project now fails fast instead of silently mocking critical dependencies. Use the flags below only for isolated tests or local scaffolding—production and standard dev runs should leave them unset.

- `ALLOW_MOCK_REDIS=true` — permits the in-memory Redis mock when `aioredis` is unavailable. Default: disabled (raise).
- `ALLOW_MOCK_GEOIP=true` — permits GeoIP stub if the `geoip2` package is missing. Default: disabled (raise).
- `ALLOW_MOCK_USER_AGENTS=true` — permits user-agent parsing stub if the `user-agents` package is missing. Default: disabled (raise).
- `CONTEXT7_ALLOW_MOCK=true` — allows Context7 API to return canned responses if no client/base URL is configured. Default: disabled (503).
- `CONTEXT7_BASE_URL` — HTTP endpoint for Context7 if a client is not injected; required for Context7 routes.

Related dependencies to install for normal operation:
- `aioredis`
- `geoip2`
- `user-agents`
- LLM provider credentials (for story/interaction generation)
