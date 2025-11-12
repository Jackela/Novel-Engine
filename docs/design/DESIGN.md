# Codex: System Design (DESIGN.md)
*Document Version: 1.2*
*Last Updated: 2025-08-11*

## 1. Scope and Objective

**Objective:** To create a predictable, measurable, and eternally improvable Context Supply Chain for narrative generation. The system, known as the Novel Engine, is designed to produce emergent, high-quality narratives in a neutral grimdark setting.

**Out of Scope:**
-   Graphical user interfaces (the system provides an API for such frontends).
-   Real-time multiplayer interaction (the system is turn-based and asynchronous).
-   Distribution of any third-party intellectual property.

## 2. Architectural Vision

The system is a modular, multi-agent architecture orchestrated by a central Director. Its core principle is the separation of objective truth (WorldState) from subjective perception (TurnBrief).

**Component Manifest:**
-   **API Server:** The primary interface to the Engine. Exposes control and query endpoints.
-   **DirectorAgent:** The central orchestrator. Manages turns, agents, and the adjudication process.
-   **PersonaAgent:** An individual AI-driven character, operating on its subjective `TurnBrief`.
-   **ChroniclerAgent:** The Scribe. Transforms structured logs into narrative prose, without inventing facts.
-   **Knowledge Base (KB/RAG):** The repository of canon, doctrine, and lore. Provides context via retrieval.
-   **Adjudicator:** A rules engine within the Director that validates and resolves `CharacterActions`.
-   **LLMClient:** An abstraction layer for communicating with Large Language Models.
-   **Observability:** A logging and data-capture subsystem for replay and evaluation.

## 3. Key Interactions & Sequences

The core of the Engine is the **Turn Execution Sequence**, a five-stage liturgy:

1.  **Perception:** The Director generates a unique, context-aware `TurnBrief` for each `PersonaAgent`. This involves Fog of War masking and RAG retrieval.
2.  **Deliberation:** Each `PersonaAgent` receives its `TurnBrief` and uses its injected `LLMClient` to produce a structured `CharacterAction`.
3.  **Adjudication:** The Director receives all `CharacterActions` and uses the Adjudicator to validate them against the `WorldState` and system rules. Invalid actions are repaired or rejected.
4.  **Consequence:** The Director applies the effects of all validated actions to the `WorldState`, creating a new state for the next turn.
5.  **Chronicling:** (Can be asynchronous) The `ChroniclerAgent` processes the immutable `CampaignLog` of adjudicated actions to generate narrative.

## 4. API Contract Overview

| Route | Method | Request Model | Response Model |
| :--- | :--- | :--- | :--- |
| `/meta/policy` | GET | - | `PolicyResponse` |
| `/simulations/run` | POST | `SimulationRunRequest` | `SimulationRunResponse` |
| `/simulations/{id}/turn`| POST | `CharacterAction` | `TurnResponse` |
| `/characters` | GET | - | `List[PersonaCardV2]` |
| `/chronicle` | POST | `ChronicleRequest` | `ChronicleSpec` |

*Refer to `API.md` and `SCHEMAS.md` for detailed specifications.*

## 5. Data Flow Diagram

```mermaid
graph TD
    A[WorldState] -->|1. Masking (Fog of War)| B(Perception Stage);
    C[Knowledge Base] -->|2. RAG Retrieval| B;
    B -->|3. TurnBrief| D(Deliberation Stage / PersonaAgent);
    D -->|4. CharacterAction| E(Adjudication Stage / Director);
    A -->|5. Validation Against Rules| E;
    E -->|6. Adjudicated Events| F(Consequence Stage);
    F -->|7. Update| A;
    E -->|8. Write Log| G[CampaignLog];
    G -->|9. Read Log| H(Chronicling Stage / ChroniclerAgent);
    H -->|10. Narrative Output| I[ChronicleSpec];
```

## 6. Operating Modes

The Engine operates in one of three modes, configured in `settings.yaml`:
-   **`neutral` (Default):** Uses only the self-contained, original `canon_neutral/`. Safe for public distribution and CI.
-   **`fan` (Local-Only):** Requires user-provided assets in the `private/` directory and a compliant `private/registry.yaml`. The Engine will refuse to start if compliance conditions are not met.
-   **`empty` (Test):** Minimal mode for testing, uses mock data and bypasses the KB.

## 7. Non-Functional Constraints

-   **Performance:** P95 turn latency (4 agents) must be ≤ 5s. Token budgets per TurnBrief are strictly enforced.
-   **Observability:** All stages of the Turn Execution Sequence must be logged with structured data for replay.
-   **Security:** All inputs from external knowledge sources must be sanitized to prevent prompt injection.
-   **Replayability:** A given run (`run_id`) must be fully replayable from its logs for debugging and evaluation.

## 8. Versioning & Evolution

-   All schemas (`SCHEMAS.md`) and APIs (`API.md`) will be versioned.
-   The `LLMClient` and `Knowledge Base` interfaces are designed to be pluggable to allow for future extension.
