# Implementation Plan: Semantic Cache

**Branch**: `001-semantic-cache` | **Date**: 2025-10-31 | **Spec**: /mnt/d/Code/Novel-Engine/specs/001-semantic-cache/spec.md
**Input**: Feature specification from `/specs/001-semantic-cache/spec.md`

## Summary

Implement a three-layer caching capability to improve latency and reduce cost while preserving correctness: Entry caches (Exact/Semantic/Tool) at request ingress, Coordinator enhancements (batch/single-flight/replay), and Provider invocation. Keys are fully normalized with bucketing; semantic cache applies a two-threshold policy (High=0.92, Low=0.85) plus guard checks; invalidation is event-driven and tag‑scoped; streaming writes are finalized only on completion; observability and budget savings are reported end‑to‑end.

## Technical Context

**Language/Version**: Python (repository standard)  
**Primary Dependencies**: Internal modules (caching/bridge/agents); no new external services for MVP  
**Storage**: N/A (in-memory caches with optional persistence policy)  
**Testing**: pytest (unit, integration, contract)  
**Target Platform**: Linux server (current deployment baseline)  
**Project Type**: Single codebase with modular subsystems  
**Performance Goals**: Align with spec SC-001..SC-006 (hit rate ≥40%, P50/P95 reductions, single-flight ≥90%)  
**Constraints**: No cross-version reuse; write-on-completion for streaming; tag-precise invalidation  
**Scale/Scope**: Initial rollout within existing agent workloads; tune thresholds as traffic grows

Technical Unknowns to research and decide in Phase 0 (resolved in research.md):
- Embedding provider default for MVP → TF‑IDF fallback; pluggable
- Vector index backend policy for MVP → In‑memory sparse vectors; pluggable
- Event bus mechanism for invalidation → In‑memory bus; tag‑scoped
- Metrics sink exposure → Internal endpoints + logs; pluggable publisher
- Stream transport assumptions for replay → Default SSE; finalize on complete

## Constitution Check

Gate alignment (pre-design):
- **Domain-Driven Narrative Core**: Caching/coordination resides in platform/accelerator context. No cross-context data access; changes will be reflected via ADRs if boundaries shift. PASS
- **Contract-First Experience APIs**: If new external/status endpoints are added, contracts will be authored under `contracts/` prior to implementation and linted in CI. PASS
- **Data Stewardship & Persistence Discipline**: No sensitive raw prompts stored; tags govern retention; multi-tenant labels available in tags. PASS
- **Quality Engineering & Testing Discipline**: System tests for exact/semantic boundaries, events, streaming, single-flight, and negative cache planned; CI gating to be extended. PASS
- **Operability, Security & Reliability**: Expose metrics, add rate limiting/backoff; document runbooks and flags. PASS
- **Documentation & Knowledge Stewardship**: Quickstart, plan, contracts and workbook entries will be updated within the same release. PASS
- Constitution Gate Workbook Run Date: 2025-10-31 (to be recorded post-PR in `docs/governance/constitution-checks.md`)

## Project Structure

### Documentation (this feature)

```text
specs/001-semantic-cache/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)

```text
src/
├── caching/           # Cache SDK (interfaces, exact, semantic, tool, key builder, events)
├── bridge/            # Coordinator (batch, single-flight, replay)
├── agents/            # LLM client middleware integration
└── metrics/           # Metrics interfaces and in-memory publisher

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Single-repo modular subsystems; documentation under `specs/001-semantic-cache/` and contracts co-located there during planning.

## Complexity Tracking

No constitution violations anticipated at this stage.

## Constitution Re-check (post-design)

All gates remain satisfied after Phase 0/1 design:
- Contracts authored for internal endpoints under `specs/001-semantic-cache/contracts/`
- Data stewardship upheld (no sensitive raw prompts stored; tag-based control)
- Testing scope captured (exact/semantic boundaries, events, streaming, single-flight, negative cache)
- Operability covered (metrics endpoints, structured logs; flags documented in quickstart)
