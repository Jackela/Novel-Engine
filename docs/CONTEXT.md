# Codex: Context Engineering (CONTEXT.md)
*Document Version: 1.2*
*Last Updated: 2025-08-11*

## 1. The Context Supply Chain

The core of the Novel Engine is its Context Supply Chain, a rigorous process for constructing the `TurnBrief` provided to each `PersonaAgent`. This process ensures that the context is relevant, concise, and compliant.

The pipeline is as follows:
1.  **Retrieval:** A hybrid (or dense-first) retrieval query is constructed based on the agent's current state and visible entities. The query is executed against the active Knowledge Base.
2.  **Re-ranking:** (Future) A cross-encoder re-ranks the initial retrieved results for higher relevance.
3.  **Compression & Pruning:** The retrieved snippets are pruned using MMR to ensure diversity and relevance. The total context is then checked against the token budget.
4.  **Fog of War (Masking):** The `WorldState` is filtered to only include entities and facts within the agent's `knowledge_scope`.
5.  **Assembly:** The final `TurnBrief` is assembled from the masked world state, the pruned snippets, and other relevant data.

## 2. Token Budgeting

To control cost and latency, a strict token budget is enforced for each `TurnBrief`.
-   **Total `TurnBrief` Token Limit:** 2500 tokens (configurable in `settings.yaml`).
-   **Retrieved Evidence Snippets:** Max 8 snippets.

If the assembled context exceeds the budget, the following pruning strategy is applied:
1.  Lowest-scoring retrieved snippets are removed first.
2.  Summaries of historical events are truncated.
3.  Non-critical entity details are removed.

## 3. Provenance (Data Lineage)

All information injected into a `TurnBrief` that originates from the Knowledge Base **must** carry a provenance tag.
-   **Format:** `source_id@version` (e.g., `canon-core@0.1.0`).
-   **Source:** The `id` and `version` must correspond to an entry in the active `registry.yaml`.
-   **Validation:** The Adjudicator may reject actions if their justification relies on un-cited or invalid-source information.

## 4. Mode-Specific Behavior

The context source is determined by the operating mode in `settings.yaml`.
-   **`neutral` mode:** The Knowledge Base is built exclusively from `canon_neutral/`.
-   **`fan` mode:** The Knowledge Base is built from `private/`. The `private/registry.yaml` must exist and contain `compliance: {non_commercial: true, distribution: local_only}`. Failure to meet this results in a startup failure.

## 5. Schema References

This document specifies the *rules* for context engineering. The authoritative definitions for the data structures themselves are located in `docs/api/schemas.md` and implemented in `src/core/types/shared_types.py`. The key schemas governed by these rules are:
-   `PersonaCardV2`
-   `WorldState`
-   `TurnBrief`
-   `CharacterAction`
-   `ChronicleSpec`
-   `CanonRegistry`

## 6. Security & Governance

-   **Prompt Injection:** All text retrieved from external knowledge sources (especially in `fan` mode) must be sanitized. This involves stripping any potential instructional phrases (e.g., "ignore previous instructions").
-   **Context Poisoning:** The system should favor information from sources with higher trust or confidence scores as defined in the `CanonRegistry`.
-   **Banned Terms:** The `term_guard.py` script enforces a list of banned terms from `settings.yaml` to prevent IP contamination in the `neutral` mode codebase.

## 7. Quality Gates (DoD Metrics)

The quality of the context pipeline is measured by the following metrics, defined in `docs/EVALUATION.md`.
-   **Canon Violation Rate:** The percentage of `CharacterActions` that contradict retrieved doctrine. Target: **≤ 5%**.
-   **Persona Consistency Score:** The cosine similarity between an action's justification and the agent's core beliefs. Target: **≥ 0.75**.
-   **TurnBrief Token Count:** The P95 token count for all generated briefs. Target: **≤ 2500**.



