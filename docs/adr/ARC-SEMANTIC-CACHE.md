# ADR: Semantic Cache Architecture and Governance

- Status: Draft
- Date: 2025-10-31
- Owner: Platform/Accelerators
- Related: specs/001-semantic-cache/spec.md, specs/001-semantic-cache/plan.md

## Context

We need to reduce LLM latency and cost without sacrificing correctness. The feature introduces caching at the entry layer with exact and semantic reuse, coordinator optimizations (batch/single-flight/replay), and provider fallbacks. Governance requires contract-first interfaces, data stewardship, test gating, observability, and workbook updates.

## Decision

Adopt a three-layer architecture:
- Entry caches: ExactCache → SemanticCache → Provider, write-on-completion for streaming
- Coordinator: batching, single-flight, replay, negative cache and backoff
- Keys: Unified KeyBuilder with bucketing; strict model/template/index/date boundaries
- Invalidation: tag-scoped, event-driven
- Observability: metrics publisher + budget linkage (saved_tokens, saved_cost)

## Consequences

- Pros: Significant latency/cost reduction; correctness boundaries; precise invalidation; observability
- Cons: Added complexity (keys/tags/events); semantic thresholds require tuning; operational metrics aggregation

## Alternatives Considered

- No semantic cache (exact only): lower recall and savings
- External vector DB at MVP: premature operational complexity
- WebSocket-only streaming: unnecessary complexity for server-initiated push

## Constitution Compliance

- Principle I: Resides in platform/accelerator context; no cross-context data access
- Principle II: Contract-first endpoints under `contracts/` with lint/pact gates
- Principle III: No sensitive raw prompts stored; tag-based retention and tenancy labels
- Principle IV: Automated suites include exact/semantic boundaries, events, streaming, single-flight; CI gating updated
- Principle V: Metrics endpoints, structured logs, feature flags, runbooks
- Principle VI: Plan, quickstart, workbook updates in the same release

## Migration / Rollout

- MVP: Exact + Semantic with conservative thresholds; canary rollout
- Enable events + replay + single-flight progressively; monitor metrics

## Links

- Spec: specs/001-semantic-cache/spec.md
- Plan: specs/001-semantic-cache/plan.md
- Contracts: specs/001-semantic-cache/contracts/cache-api.yaml
- Quickstart: specs/001-semantic-cache/quickstart.md
