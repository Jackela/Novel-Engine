# Data Model: Semantic Cache

## Entities

### CacheKey
- Dimensions: character_id, session_id?, provider, model_name, prompt_template_id, prompt_template_version, index_version, locale, tool_set_signature, stop_set_signature, temperature_bucket, top_p_bucket, max_tokens_bucket, date_partition
- Content hash: sha256(prompt_core_normalized)[0:32]
- Constraints: no PII in stored hash; stable canonicalization

### CacheEntry
- Fields: key, value, created_at, last_accessed, ttl_expires, hit_count, access_count, creation_cost
- Flags: complete (streaming finalized), sensitive (non-persistent)
- Tags: {character, tmpl, tmplv, idxv, model, locale, tool, session/date}

### SimilarityResult
- Fields: candidate_key, similarity_score (0..1), guard_checks {template_match, tools_match, len_delta_pct, keyword_overlap}
- Decision: accept|reject|guard_pass

### Event
- Types: PromptTemplateUpdated, CharacterUpdated, WorldStateChanged, IndexRebuilt, ModelConfigChanged
- Payload: source_id(s), version(s), emitted_at
- Mapping: to tag set for invalidation

### ChunkRecord
- Fields: exact_key, seq, offset, payload_fragment, ts, complete=false|true
- Policy: replay chunks to late subscribers; finalize on complete

### MetricsSnapshot
- Fields: ts, cache_exact_hits, cache_semantic_hits, cache_tool_hits, cache_size, evictions, invalidations, similarity_histogram, single_flight_merged, replay_hits, failures
- Economics: saved_tokens_est, saved_cost_est

## Relationships
- CacheEntry 1..* has Tags (tag strings)
- CacheKey 1..1 identifies CacheEntry
- Event 1..* maps to tags; invalidation filters entries by tag intersection
- ChunkRecord *..1 aggregates into one final CacheEntry when complete

## Rules
- No cross‑model/template/index reuse in semantic hits
- Two‑threshold policy: High=0.92 accept, Low=0.85 reject, gray zone requires guard checks (len Δ≤15%, keyword≥0.40, template/tools一致)
- Exact cache written only upon completion for streaming
