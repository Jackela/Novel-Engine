# Ports & Adapters Matrix

| Context | Port | Adapter Implementation | Direction | Notes |
|---------|------|------------------------|-----------|-------|
| Simulation Orchestration | `DirectorAgent.turn_processor` | `src/director_agent.py` orchestrates turns | Inbound command | Consumes persona decisions, writes turn ledger events. |
| Simulation Orchestration | `EventBus.publish` | `src/event_bus.py` | Outbound event | Emits `CampaignCreated`, `TurnAdvanced`. |
| Persona Intelligence | `PersonaAgent.gemini_client` | HTTPX wrapper (to be refactored) | Outbound query | Applies retries, caching (Redis), tenant tagging. |
| Persona Intelligence | `PersonaAgent.decision_port` | Local strategy fallback | Inbound command | Ensures deterministic decisions when Gemini unavailable. |
| Narrative Delivery | `ChroniclerAgent.storage_gateway` | File/S3 writer | Outbound command | Persists narrative markdown and media pointers. |
| Narrative Delivery | `ExperienceAPI.fetch_campaign` | `apps/api/http/world_router.py` | Inbound query | Provides data to frontend dashboard. |
| Platform Operations | `FeatureFlagService.toggle` | LaunchDarkly SDK (planned) | Outbound command | Controls rollout states for contexts; audit logged. |
| Platform Operations | `SLORegistry.record` | Observability pipeline | Outbound event | Captures RED/USE metrics for dashboards. |

## Adapter Guidelines

- All adapters must log traceId/spanId and tenant metadata.
- External adapters (Gemini, LaunchDarkly) require ACL documentation managed
  alongside security/data-protection charters.
- Ports must remain domain-focused; infrastructure details live inside adapters.
