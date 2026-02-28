## Why

Factions in the world simulation currently lack autonomous decision-making capabilities. While the Geopolitics and Time systems are now connected, there's no mechanism for factions to act on their own behalf based on their current state, resources, and relationships. This limits the simulation's ability to generate emergent narrative and strategic depth.

Enabling AI-driven faction decisions will create a living world where factions pursue their own goals, react to changing circumstances, and generate compelling narrative opportunities without manual intervention.

## What Changes

- **FactionIntent entity**: New domain entity capturing a faction's intended action with action type, target, rationale, and status
- **FactionDecisionService**: Application service that uses RAG (RetrievalService) to fetch relevant lore/relationships and calls LLM to generate possible intents
- **IntentGeneratedEvent**: Domain event emitted when a faction generates new intents
- **API endpoint**: `POST /api/world/factions/{id}/decide` to trigger AI decision-making
- **Frontend component**: `FactionIntelPanel.tsx` to display AI's thought process and chosen intents
- **LLM prompt templates**: Intent generation prompts integrated with existing LLM infrastructure

## Capabilities

### New Capabilities

- `faction-intent`: Domain entity and events for faction decision-making, including `FactionIntent` entity with action types (EXPAND, ATTACK, TRADE, SABOTAGE, STABILIZE) and `IntentGeneratedEvent`
- `faction-decision-service`: Application service that fetches faction context via RAG, generates intent options via LLM, and manages intent lifecycle
- `faction-intel-api`: API endpoint for triggering faction decisions and retrieving intent history
- `faction-intel-panel`: Frontend React component displaying AI reasoning and chosen intents

### Modified Capabilities

- `llm-world-generator`: Extend to support intent generation prompts (add intent-specific prompt templates)

## Impact

### Code
- `src/contexts/world/domain/entities/` - New `FactionIntent` entity
- `src/contexts/world/domain/events/` - New `IntentGeneratedEvent`
- `src/contexts/world/application/services/` - New `FactionDecisionService`
- `src/api/routers/` - New or extended faction router with decide endpoint
- `frontend/src/features/world/` - New `FactionIntelPanel` component

### APIs
- New: `POST /api/world/factions/{faction_id}/decide` - Trigger AI decision-making
- New: `GET /api/world/factions/{faction_id}/intents` - Get intent history

### Dependencies
- Existing `RetrievalService` for RAG context
- Existing LLM infrastructure for generation
- Geopolitics and Time systems (now connected via Operation Bridge)
