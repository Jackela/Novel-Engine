# Observability Charter

## Objectives

- Provide end-to-end visibility across Simulation Orchestration, Persona Intelligence, Narrative Delivery, and Platform Operations.
- Meet constitution requirements for RED/USE metrics, structured logging, and trace coverage.
- Support incident response and continuous improvement of SLOs.

## Metrics (RED/USE)

| Context | Metric | Target | Notes |
|---------|--------|--------|-------|
| Simulation Orchestration | Request rate | Monitor per campaign | Derived from `/api/v1/simulations` submissions. |
| Simulation Orchestration | Error rate | < 1% | Failed turns, persona load errors. |
| Persona Intelligence | Latency (p95) | < 700ms | Includes Gemini ACL cache hit tracking. |
| Narrative Delivery | Story publish latency (p95) | < 2s | From event ingestion to file persistence. |
| Platform Operations | Feature flag toggle propagation | < 5s | Measured via LaunchDarkly webhook ack. |

## Telemetry Requirements

- **Traces**: 99% coverage for critical flows with traceId/spanId injection via middleware.
- **Logs**: JSON logs with fields `timestamp`, `level`, `service`, `tenantId`, `traceId`, `spanId`, `userId`.
- **Metrics Export**: Prometheus format scraped every 15 seconds; alerting configured in Grafana.
- **Dashboards**: One per context plus executive summary.

## Alert Thresholds

- Simulation error rate > 2% over 5 minutes → PagerDuty (SEV2).
- Persona latency > 900ms for 10 minutes → Slack reliability channel.
- Feature flag propagation > 10s → Investigate LaunchDarkly or queue backlog.

## Ownership

- Reliability Council maintains dashboards and alert tuning.
- Each context steward owns corresponding widget(s) and post-incident analysis.

## Review Cadence

- Quarterly review of metrics and thresholds.
- Update charter whenever new bounded context is introduced or metrics change.

## QA Tooling Prerequisites

- Python 3.11 or newer with `python3-venv`
- Docker daemon running locally (required for `act`)
- `act` CLI installed (`/usr/local/bin/act`)
- Playwright browsers installed via `python3 -m playwright install`
- Optional: use `.venv-ci` virtual environment created by `scripts/validate_ci_locally.sh`
