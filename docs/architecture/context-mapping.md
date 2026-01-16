# Module to Context Mapping

| Module / Path | Context | Notes |
|---------------|---------|-------|
| `src/director_agent.py` | Simulation Orchestration | Owns campaign lifecycle and turn processing. |
| `src/agents/persona_agent/agent.py` | Persona Intelligence | Interfaces with Gemini ACL for persona decisions. |
| `src/chronicler_agent.py` | Narrative Delivery | Produces narrative chronicles from turn ledger. |
| `src/core/event_bus.py` | Platform Operations | Shared messaging port; emits context-tagged events. |
| `apps/api/http/world_router.py` | Simulation Orchestration | Read/write API for world state slices and deltas. |
| `api_server.py` | Platform Operations | API gateway exposing health, simulations, and campaigns. |
| `frontend/src/` | Narrative Delivery | Dashboard experience consuming experience APIs. |
| `scripts/contracts/run-tests.sh` | Platform Operations | Automation for contract linting (governance). |

## Ownership Notes

- Each context has an assigned steward: Architecture Guild (Simulation),
  Persona Engineering, Chronicler Collective, Reliability Council.
- Shared utilities (e.g., `src/core/config/config_loader.py`) remain in platform foundation but
  must not leak context-specific invariants.


