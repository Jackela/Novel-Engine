# Security Controls Charter — Novel Engine

## Purpose

Establish mandatory authentication and authorization standards for Novel Engine
services in alignment with the project constitution (Principles II & V) and the
Project Best-Practice Refactor specification (FR-002, FR-003, FR-004).

## 1. Identity & Token Validation

- **Protocol**: All interactive clients authenticate via OIDC/OAuth 2.1 using
  short-lived access tokens (JWT) backed by the platform identity provider.
- **Validation Pipeline**:
  1. Verify JWT signature against JWKS endpoint (cached for 5 minutes).
  2. Confirm issuer (`iss`), audience (`aud`), and expiry (`exp`, `nbf`) claims.
  3. Enforce tenant scoping by matching `tenant_id` claim to requested resource.
  4. Attach validated claims to request context for downstream RBAC/ABAC checks.
- **Replay Mitigation**: Require TLS 1.2+ for all entrypoints, enforce
  `jti` claim uniqueness per tenant with Redis cache (5 minute retention).

## 2. RBAC / ABAC Matrix

| Role            | Description                                | Persona Coverage | Bound Context Permissions                          | Enforcement Mechanism                     |
|-----------------|--------------------------------------------|------------------|----------------------------------------------------|-------------------------------------------|
| `architect`     | Defines domain models & ADRs               | Platform Ops     | Read/write docs under `/docs/architecture`, propose ADRs | RBAC claim, gated by `architect:write` scope |
| `delivery_lead` | Owns contracts & workflow gates            | Narrative Delivery | Read/write `/docs/governance`, `/specs/*` templates | RBAC claim, `delivery:governance` scope     |
| `reliability`   | Operability and incident commander         | Platform Ops     | Read/write `/docs/observability`, `/docs/runbooks` | RBAC claim, `reliability:runbooks` scope   |
| `executor`      | Implements runtime changes (future work)   | Simulation Orchestration | Read-only governance docs, no write rights        | ABAC: `role=executor` → deny write         |
| `viewer`        | Read-only stakeholder                      | All              | View docs & APIs, no modifications                 | RBAC default, `viewer` scope               |

- **ABAC Extensions**: Additional policies derive from attributes
  (`tenant_id`, `campaign_id`, `environment`). Example: operations staff may
  only edit runbooks tagged with their tenant or environment prefix.
- **Decision Service**: Policies encoded via OPA (Open Policy Agent) deployed
  as a sidecar to API gateway; failure to retrieve policy = deny.

## 3. Rate Limiting & Idempotency

- **Buckets**: Limits enforced per tenant, user, and IP on `/api/*`.
  Default 120 requests/minute per user, 600/minute per tenant.
- **Headers**: Responses MUST include `X-RateLimit-Limit`,
  `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- **Idempotency**: All write requests require `Idempotency-Key` (16–64 chars).
  Keys stored per tenant/user for 24 hours with request hash to detect retries.
- **Backoff Guidance**: Clients must honor `Retry-After` header (seconds).

## 4. Session & Transport Controls

- Enforce HTTPS everywhere; HSTS set to 6 months.
- TLS cert rotation automated via ACME with 24 hour expiry alarms.
- Disable weak ciphers (TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 or better).
- Set secure cookies (if used) with `HttpOnly`, `SameSite=Strict`.

## 5. Audit & Monitoring Obligations

- **Logging**: Structured JSON logs include `traceId`, `spanId`, `userId`,
  `tenantId`, `scope`. Sensitive payloads redacted at source.
- **Alerting**: Failed auth attempts > 5/min/tenant trigger warning alert.
- **Reviews**: Quarterly access reviews reconcile RBAC membership with HR roster.

## 6. Required Artifacts & Owners

| Artifact                                     | Owner Role       | Location                                      | Refresh Cadence |
|----------------------------------------------|------------------|-----------------------------------------------|-----------------|
| Security controls charter (this document)    | Delivery Lead    | `docs/governance/security-controls.md`        | Quarterly       |
| OIDC / JWKS configuration record             | Platform Ops     | `configs/auth/oidc.yaml`                      | As needed       |
| RBAC/ABAC policy bundle                      | Platform Ops     | `deploy/policies/opa/`                        | Each release    |
| Rate-limit configuration                     | Platform Ops     | `configs/api/rate-limits.yaml`                | Quarterly       |
| Idempotency state retention plan             | Platform Ops     | `docs/governance/data-protection.md` (ref)    | Quarterly       |

## 7. Compliance Checklist (for T021 execution)

1. Update RBAC/ABAC table if roles changed.
2. Verify OIDC token validation pipeline matches current provider metadata.
3. Confirm rate-limit tiers documented in API policies match gateway config.
4. Ensure audit log expectations align with observability charter.
5. Record review date and sign-off in changelog (`CHANGELOG.md`).
