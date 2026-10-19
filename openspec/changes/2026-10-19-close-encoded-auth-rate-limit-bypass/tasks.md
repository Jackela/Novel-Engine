## 1. Review and reproduction

- [x] 1.1 Fix the current main comparison SHA and preserve ACP/unrelated state.
- [x] 1.2 Trace the 14 alert sources and guards, using SARIF and actual source.
- [x] 1.3 Reproduce the encoded-route bypass through complete buildApp and synthetic credentials/data.

## 2. Minimal repair

- [x] 2.1 Add failing public HTTP regressions and use the matched route identity for admission.
- [x] 2.2 Verify canonical/encoded/query spellings share a bucket while peer/method isolation and OPTIONS remain intact.
- [x] 2.3 Verify exhausted setup/login has no Owner/session side effect and database-free admission still runs early.

## 3. Integration evidence

- [ ] 3.1 Run the affected regressions and applicable full local gates, browser, and isolated container checks.
- [ ] 3.2 Independently review Standards, Spec, and alert dispositions; record exact candidate evidence and skips.
- [ ] 3.3 Record exact-SHA evidence, remaining acceptance boundaries, and the CI/archive handoff.

The change remains live until its implementation candidate passes CI. After
archival, the new final candidate must pass fresh exact-head checks before
merge; post-merge main CI precedes task-only recoverable cleanup.
