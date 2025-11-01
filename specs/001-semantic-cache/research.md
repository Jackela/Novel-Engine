# Research Findings: Semantic Cache

**Date**: 2025-10-31  
**Context**: Resolve planning unknowns for the semantic caching feature.

## 1) Embedding Provider (MVP default)
- Decision: Use TF‑IDF fallback as default; keep provider pluggable
- Rationale: Zero external dependency, deterministic behavior, adequate for initial recall with the two‑threshold policy and guard checks; aligns with tech‑agnostic spec.
- Alternatives considered:
  - Sentence‑Transformers (SBERT): Higher quality embeddings, requires model/runtime mgmt
  - OpenAI Embeddings: High quality, adds network dependency and cost

## 2) Vector Index Backend
- Decision: In‑memory sparse vectors (TF‑IDF) with cosine similarity; pluggable index interface
- Rationale: Simple, fast for current scale; avoids premature external index adoption; consistent with MVP aims.
- Alternatives considered:
  - FAISS/Annoy/HNSW: Better scaling; increases operational complexity
  - External vector DB: Powerful but overkill for initial rollout

## 3) Event Bus for Invalidation
- Decision: In‑memory event bus; map events to tag‑scoped invalidations
- Rationale: Minimal moving parts; precise tag clearing meets freshness requirements; easy to later swap to Redis Pub/Sub.
- Alternatives considered:
  - Redis Pub/Sub: Enables cross‑process invalidation; adds infra dependency
  - Message broker (NATS/Kafka): Robust but unnecessary at current scope

## 4) Metrics Sink & Exposure
- Decision: Provide internal status/metrics endpoints and structured logs; keep metrics publisher pluggable
- Rationale: Satisfies observability gates and budget linkage; minimal surface area.
- Alternatives considered:
  - Direct Prometheus exporter: Useful later; not required to start

## 5) Stream Transport Policy (Replay)
- Decision: Default SSE for server‑initiated streaming; support WebSocket where already present; chunk cache write on chunks, finalize only on completion
- Rationale: SSE is widely supported and simple; preserves consistency via finalize‑on‑complete write policy.
- Alternatives considered:
  - WebSocket‑only: More flexible; higher complexity for simple server push

---

All Technical Context unknowns are now resolved for planning.
