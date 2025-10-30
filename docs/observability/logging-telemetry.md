# Logging & Telemetry Standards

## Structured Logging
- Format: JSON per line with keys `timestamp`, `level`, `service`, `tenantId`, `traceId`, `spanId`, `userId`, `message`.
- Redact secrets and PII; use field `redacted=true` when applicable.
- Logging library: Python `logging` with JSON formatter; frontend uses browser console for local only.

## Trace Instrumentation
- Use OpenTelemetry SDK; automatic instrumentation for FastAPI/HTTPX.
- Naming convention: `context.operation` (e.g., `persona.decision`, `narrative.publish`).
- Propagate headers (`traceparent`, `baggage`) across HTTP calls and event bus messages.

## Metrics Export
- Prometheus endpoints exposed under `/metrics` for backend services.
- Frontend metrics exported via browser beacons to analytics collector.
- Use RED/USE taxonomy defined in `docs/observability/charter.md`.

## Storage & Retention
- Logs retained 30 days in Loki (hot storage), 180 days in S3 archive.
- Traces retained 7 days for dev, 30 days for prod.
- Metrics retained 1 year for trend analysis.

## Validation Checklist
- [x] Logging configuration includes structured handler.
- [x] Trace context injected into logs (traceId/spanId).
- [x] Metrics endpoint secured with token-based auth.
- [x] Dashboards link to documentation for interpretation.

