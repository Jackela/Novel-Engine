## Why

The existing authentication rate-limit contract applies to setup and login, but its admission hook keys on the raw URL pathname. The HTTP router also accepts equivalent percent-encoded spellings, so an unauthenticated client can bypass an exhausted bucket and still reach password verification or create an Owner/session with otherwise valid credentials. A fresh review of historical CodeQL alert 1972 reproduced the bypass through the complete buildApp.

## What Changes

- Use the authentication route actually matched by the router when selecting the existing per-client/method bucket.
- Preserve the onRequest admission stage, default five-per-minute limit, OPTIONS exemption, client identity policy, unified 429/Retry-After, and setup/CSRF/session rules.
- Add public API regressions for mixed encoded/canonical setup and login paths, no side effects after refusal, and database-free early admission.
- Record the review of all 14 historical alerts, retaining verified filesystem boundaries and distinguishing false positives from the real bypass.

## Impact

No new endpoint, dependency, migration, configuration, deployment behavior or principal model. Encoded spellings of existing endpoints now obey the same limit as their canonical spelling. Existing clients using admitted requests retain their behavior. No path-guard rewrite or blanket CodeQL suppression is introduced.
