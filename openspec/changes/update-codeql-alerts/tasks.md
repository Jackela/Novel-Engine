## 1. Implementation
- [x] 1.1 Export and classify current CodeQL alerts (security vs quality, prod vs tests).
- [x] 1.2 Resolve security findings first and confirm safe cookie handling patterns.
- [x] 1.3 Fix Python quality alerts in src/ (unused imports, empty excepts, unreachable statements).
- [x] 1.4 Fix JavaScript/TypeScript quality alerts in frontend/ and related tests.
- [x] 1.5 Review tests/ alerts and decide between fixes vs justified suppressions.
- [x] 1.6 Add documented CodeQL suppressions for confirmed false positives.
- [x] 1.7 Update CodeQL workflow/config to reflect intended scope and exclusions.
- [x] 1.8 Run full regression and CodeQL analysis, confirm zero open alerts.
- [x] 1.9 Update docs/policy references if needed to reflect the new gate.
