## 1. Specification

- [x] 1.1 Draft the surfaces, sessions, and operations deltas in the `novel-engine` capability
- [x] 1.2 `pnpm spec:validate` green

## 2. Implementation (per `/to-tickets` breakdown)

- [x] 2.1 Constant-time login (dummy hash), setup credential policy (10–72 UTF-8 bytes, username rules), duplicate-setup 422, and the concurrent-setup single-owner guard
- [x] 2.2 Lazy session expiry with server-side invalidation, last-seen refresh, and logout row-delete plus dual cookie clear returning 204
- [x] 2.3 Setup same-origin validation: Origin/Referer allowlist, null/userinfo/scheme/port rejections, origin-less clients allowed
- [x] 2.4 Authentication rate limiting: per-IP token bucket (5/min default) on setup/login/guest, 429 + Retry-After, trusted-proxy X-Forwarded-For resolution
- [x] 2.5 Production guards (non-default secret in prod/staging, forced SQLite, CORS wildcard and localhost ban) and the non-prod per-start random secret
- [x] 2.6 Configuration surface: `.env.local` loading, the single prefix family, `SECURITY_CORS_ORIGINS` as the only CORS name with aliases ignored, and the documented defaults
- [x] 2.7 Principal scoping on every query (owner_id / guest session_id) and the 24-hour guest cleanup at startup and hourly
- [x] 2.8 CLI commands: `serve` (backup before migrate), `import` (explicit source + owner), `backup`, and `doctor` with its integrity exit contract
- [x] 2.9 Frontend carried forward: entry flow, no-polling job list, in-memory drafts, 300s timeout with `VITE_API_TIMEOUT` override, section filtering, naming, export download, silent entry fallback — verify, do not rebuild

## 3. Verification

- [x] 3.1 Contract tests: constant-time login parity, setup policy/concurrency, lazy expiry, logout, origin checks, rate limiting including proxy trust
- [x] 3.2 Configuration tests: production guard startup refusals, alias-name inertness, default resolution, restart session invalidation
- [x] 3.3 CLI tests: serve backup-then-migrate order, import owner binding, backup output, doctor exit codes
- [x] 3.4 Browser workflow tests: entry three-branch flow, draft discard on switch/reload, job-list explicit-refresh-only, section filtering, generated naming, export filename, silent fallback
