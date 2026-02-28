# Faction Decision Service

## Overview

Application service that orchestrates AI-driven decision-making for factions using RAG context retrieval and LLM generation.

## Requirements

### REQ-DECISION-001: Context Assembly
The service SHALL assemble decision context including:
- Faction's current resources (gold, food, military, etc.)
- Diplomatic relationships with other factions
- Territory control status
- Recent events (via RAG from RetrievalService)
- Relevant lore (via RAG from RetrievalService)

### REQ-DECISION-002: Intent Generation
The service SHALL generate exactly 3 intent options per decision cycle:
- Each intent with a different action type where possible
- Each intent with a unique target where applicable
- Each intent with AI-generated rationale (50-200 characters)
- Priority ranking 1-3

### REQ-DECISION-003: Low Resource Handling
The service SHALL prioritize survival actions when resources are low:
- If food < 100: SHALL NOT generate ATTACK intents
- If military < 50: SHALL NOT generate ATTACK or SABOTAGE intents
- If gold < 200: SHALL prioritize TRADE over EXPAND

### REQ-DECISION-004: RAG Integration
The service SHALL use RetrievalService to fetch:
- Last 5 events involving the faction
- Top 3 relevant lore entries about faction relationships
- Territory status for controlled locations

### REQ-DECISION-005: LLM Prompt Structure
The service SHALL construct prompts with:
- Faction identity and current state
- Resource summary with thresholds
- Action type definitions
- Context from RAG (events, lore)
- Output format specification (JSON schema)

### REQ-DECISION-006: Response Validation
The service SHALL validate LLM responses:
- Verify JSON structure matches schema
- Verify action_type is valid enum value
- Verify target_id references existing entity
- Reject and retry on validation failure (max 2 retries)

### REQ-DECISION-007: Fallback Behavior
The service SHALL provide fallback intents when LLM fails:
- Generate rule-based intents based on resource thresholds
- Log failure with error details
- Emit IntentGeneratedEvent with fallback flag

## Scenarios

### Scenario: Successful Intent Generation
Given faction "north-kingdom" with moderate resources
When FactionDecisionService.generate_intents() is called
Then 3 FactionIntent entities SHALL be created
And IntentGeneratedEvent SHALL be emitted
And each intent SHALL have unique rationale

### Scenario: Low Food Prioritizes Trade
Given faction "desert-tribe" with food=30, gold=500
When FactionDecisionService generates intents
Then no ATTACK intents SHALL be generated
And at least one TRADE or STABILIZE intent SHALL be generated

### Scenario: LLM Failure Falls Back
Given LLM service is unavailable
When FactionDecisionService generates intents
Then fallback rule-based intents SHALL be generated
And the event SHALL include fallback=true flag
