# Faction Intent

## Overview

Domain entity representing a faction's intended action, including action type, target, rationale, and lifecycle status.

## Requirements

### REQ-INTENT-001: FactionIntent Entity
The system SHALL provide a `FactionIntent` entity with the following attributes:
- `id`: Unique identifier
- `faction_id`: Reference to the faction
- `action_type`: One of EXPAND, ATTACK, TRADE, SABOTAGE, STABILIZE
- `target_id`: Optional reference to target (location, faction, resource)
- `rationale`: AI-generated explanation for the intent
- `priority`: Integer 1-3 (1 = highest)
- `status`: PROPOSED, SELECTED, EXECUTED, or REJECTED
- `created_at`: Timestamp of creation

### REQ-INTENT-002: Action Types
The system SHALL define the following action types:
- **EXPAND**: Increase territory or influence
- **ATTACK**: Military action against another faction
- **TRADE**: Economic exchange proposal
- **SABOTAGE**: Covert operation against rival
- **STABILIZE**: Internal consolidation, defensive posture

### REQ-INTENT-003: Intent Status Lifecycle
The system SHALL manage intent status with the following transitions:
- PROPOSED → SELECTED (user or AI selects this intent)
- SELECTED → EXECUTED (intent was acted upon)
- PROPOSED/SELECTED → REJECTED (intent was discarded)

### REQ-INTENT-004: IntentGeneratedEvent
The system SHALL emit an `IntentGeneratedEvent` when new intents are created:
- Event type: `faction.intent_generated`
- Payload: faction_id, intent_ids[], timestamp

### REQ-INTENT-005: Intent Storage
The system SHALL persist intents with the following constraints:
- Maximum 10 active (non-terminated) intents per faction
- Unlimited historical (EXECUTED/REJECTED) intents
- Intents older than 7 in-game days without action SHALL be auto-expired

## Scenarios

### Scenario: Generate Faction Intents
Given a faction "north-kingdom" with resources gold=500, food=50
When the decision service generates intents
Then 3 FactionIntent entities SHALL be created with action types appropriate to low food
And IntentGeneratedEvent SHALL be emitted

### Scenario: Select Intent
Given a faction with PROPOSED intents
When a user selects intent "intent-123"
Then intent "intent-123" status SHALL become SELECTED
And other intents remain PROPOSED

### Scenario: Auto-Expire Old Intents
Given a faction with PROPOSED intent created 8 in-game days ago
When the cleanup process runs
Then the intent status SHALL become REJECTED
