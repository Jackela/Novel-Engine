# Faction Intel API

## Overview

REST API endpoints for triggering faction decision-making and retrieving intent history.

## Requirements

### REQ-API-001: Trigger Decision Endpoint
The system SHALL provide `POST /api/world/factions/{faction_id}/decide`:
- Request body: optional `{ "context_hints": ["focus:expansion"] }`
- Response: `{ "intents": [...], "generation_id": "uuid" }`
- Response codes: 200 (success), 404 (faction not found), 429 (rate limited)

### REQ-API-002: Get Intents Endpoint
The system SHALL provide `GET /api/world/factions/{faction_id}/intents`:
- Query params: `status`, `limit`, `offset`
- Response: `{ "intents": [...], "total": N, "has_more": bool }`
- Default limit: 20, max limit: 100

### REQ-API-003: Select Intent Endpoint
The system SHALL provide `POST /api/world/factions/{faction_id}/intents/{intent_id}/select`:
- Response: `{ "intent": {...}, "status": "SELECTED" }`
- Response codes: 200 (success), 404 (not found), 409 (already selected)

### REQ-API-004: Rate Limiting
The system SHALL rate-limit decision generation:
- Maximum 1 generation request per faction per 60 seconds
- 429 response with `Retry-After` header on limit exceeded

### REQ-API-005: Error Responses
All error responses SHALL include:
- `code`: Machine-readable error code
- `message`: Human-readable description
- `details`: Optional additional context

## Scenarios

### Scenario: Trigger Decision
Given faction "north-kingdom" exists
When POST /api/world/factions/north-kingdom/decide is called
Then response 200 with 3 intents SHALL be returned
And generation_id SHALL be unique

### Scenario: Rate Limited
Given faction "north-kingdom" had a decision generated 30 seconds ago
When POST /api/world/factions/north-kingdom/decide is called
Then response 429 SHALL be returned
And Retry-After header SHALL indicate remaining seconds

### Scenario: Get Intent History
Given faction "north-kingdom" has 5 past intents
When GET /api/world/factions/north-kingdom/intents?limit=3 is called
Then response 200 with 3 intents and has_more=true SHALL be returned
