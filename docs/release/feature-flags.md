# Feature Flag Rollout Manual

## Tooling

- LaunchDarkly is the primary flag platform (production/staging).
- Local development uses `.env.flags` mirrored from LaunchDarkly defaults.

## Rollout Process

1. **Plan**
   - Define rollout goal, metrics, and fallback plan.
   - Document in change request referencing ADR ARC-001 if architecture impact.
2. **Enable Canary**
   - Target internal tenant only.
   - Monitor for 30 minutes (errors, latency, user feedback).
3. **Progressive Exposure**
   - Increase exposure by 25% increments with 15-minute observation windows.
4. **Full Rollout**
   - Toggle to 100% after metrics stable and QA sign-off.

## Rollback

- Immediate rollback by toggling flag off.
- Document root cause in `docs/runbooks/incident-response.md`.
- Evaluate need for guardrail improvements.

## Audit & Governance

- All changes logged through LaunchDarkly change history.
- Weekly review of stale flags; archive flags older than 90 days.
- Feature flags referenced in release notes and onboarding guide.
