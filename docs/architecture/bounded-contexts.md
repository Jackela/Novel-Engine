# Bounded Context Glossary

| Context | Purpose | Primary Aggregates | Key Owners | Downstream Consumers |
|---------|---------|--------------------|------------|----------------------|
| Simulation Orchestration | Manage campaign lifecycle and turn execution. | Campaign, Turn Ledger | Director Guild | Persona Intelligence, Narrative Delivery |
| Persona Intelligence | Shape persona decisions and integrate Gemini AI. | Persona module | Persona Engineering | Simulation Orchestration, Narrative Delivery |
| Narrative Delivery | Transform events into published narratives and media. | Narrative Chronicle, Media Asset | Chronicler Collective | Platform Operations, External Channels |
| Platform Operations | Provide feature flag, SLO, and governance infrastructure. | Platform Control Plane | Reliability Council | All contexts |

## Shared Vocabulary

- **Aggregate**: Consistent unit of change guarded by invariants.
- **Port**: Interface exposed by a context for external actors.
- **Adapter**: Implementation binding a port to infrastructure.
- **Anti-Corruption Layer (ACL)**: Translation boundary to legacy or third-party systems (e.g., Gemini API).

## Cross-Context Contracts

- Events between contexts must be serialized via `src/event_bus.py` with tenant metadata.
- Read models are materialized per context; direct cross-context database reads are prohibited.
