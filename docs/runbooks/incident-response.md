# Incident Response Runbook

## Detection
- Alerts from Grafana/PagerDuty (see observability charter thresholds).
- Manual reports via reliability Slack channel.

## Roles
- Incident Commander (IC)
- Communications Lead
- Scribe
- Subject Matter Experts (context stewards)

## Triage Steps
1. IC acknowledges alert and assigns roles.
2. Validate metrics/dashboards to confirm incident.
3. Determine blast radius (tenants, personas, campaigns).
4. Decide on mitigation: rollback feature flag, disable service, or engage fallback.

## Rollback Procedures
- Feature flags: follow `docs/release/feature-flags.md` (toggle off, confirm metrics).
- Deployments: use `deploy/rollback.sh` (document version + traceId).
- Gemini ACL: switch to fallback heuristic by enabling `FAILSAFE_MODE` flag.

## Communication
- Post updates every 15 minutes in #reliability-updates.
- Notify affected stakeholders via status page template in `/docs/comms/refactor-briefing.md`.

## Post-Incident
- Record timeline in this runbook.
- Create postmortem in `reports/compliance/`.
- Update constitution workbook entry and relevant documentation.

