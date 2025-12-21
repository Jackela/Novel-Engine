# Data Protection & Privacy Commitments — Novel Engine

## Purpose

Document mandatory data handling, retention, and audit practices required by the
Novel Engine constitution (Principles III & V) and the Project Best-Practice
Refactor specification (FR-002, FR-004, NFR-003).

## 1. Data Classification

| Classification | Description                                   | Examples                                           | Handling Requirements                               |
|----------------|-----------------------------------------------|----------------------------------------------------|-----------------------------------------------------|
| P0 – System Metadata | Non-sensitive operational data              | Feature flags, build numbers, job status           | Standard logging, no special controls               |
| P1 – Narrative Content | Campaign logs, generated stories            | `demo_narratives/`, `campaign_log.md`              | Store in approved buckets; redact PII before export |
| P2 – Persona Profiles | Character sheets, decision weights          | `characters/engineer`, `contexts/world`            | Encrypt at rest, restrict to persona owners         |
| P3 – Tenant Identifiers | Customer names, tenant IDs, billing data      | `tenant_id` claims, billing configs                | Encrypt at rest, restrict access via ABAC           |
| P4 – Credentials / Secrets | API keys, service tokens, refresh tokens    | Gemini API key, OIDC client secrets                | Vault/KMS storage only, never committed              |

## 2. Storage & Encryption

- **At Rest**:
  - SQLite (dev) encrypted with SQLCipher (passphrase via `.env` or Vault).
  - PostgreSQL (production-ready) configured with Transparent Data Encryption.
  - Redis caches scoped per tenant with TLS and `AUTH` enforcement.
  - Object storage (S3/GCS) buckets require SSE-KMS, versioning, and MFA delete.
- **In Transit**: All services communicate over TLS 1.2+; mutual TLS for
  internal service-to-service traffic where available.

## 3. Retention & Deletion

- Campaign and narrative data retained for 180 days unless customer contract
  specifies otherwise.
- Persona profiles retained until persona is archived; archived profiles purged
  after 90 days.
- Access logs retained for 365 days to satisfy audit requirements.
- Implement deletion workflow via background job queue (idempotent) that
  removes data from primary storage, caches, and search indexes; log completion
  with trace ID.

## 4. Tenant Isolation & Access

- Dedicated schema (or database) per enterprise tenant; row-level filters for
  demo/internal tenants.
- Repository layer enforces tenant filter; queries without tenant context fail.
- S3 object layout uses prefix `tenant/{tenant_id}/...` to simplify lifecycle
  policies and access audits.

## 5. Backup, Recovery & Audit

- **Backups**: Daily snapshots with 7-day retention for dev, 30-day retention for
  staging/prod; additional PITR logs retained 15 days.
- **Recovery Objectives**: RPO 15 minutes, RTO 30 minutes as stated in plan.md.
- **Audit**:
  - Track all access/delete operations in structured logs with `traceId`,
    `userId`, `tenantId`.
  - Quarterly audit ensures encryption settings, lifecycle policies, and access
    controls match this document.
  - Produce summarized audit report stored in `reports/compliance/`.

## 6. Breach Response

- Detect anomalies using alerting rules on unusual read/write patterns.
- Incident response runbook (`docs/runbooks/incident-response.md`) includes
  breach notification template, data-owner contact list, and SLA for customer
  communication (within 24 hours).
- Post-incident review updates this document and `security-controls.md`
  as needed.

## 7. Developer Responsibilities

- No sensitive data in local logs or screenshots.
- Prefer synthetic or anonymized data in demos/tests; if real data required,
  store in isolated environment with approvals.
- Use `term_guard.py` pre-commit hook to block committing secrets.

## 8. Compliance Checklist (for T022 execution)

1. Confirm data classification table is current with latest features.
2. Verify encryption/retention settings in staging and production.
3. Review tenant isolation enforcement in repositories and caches.
4. Ensure deletion job and audit logging flows are documented.
5. Record review date and owner in `CHANGELOG.md`.
