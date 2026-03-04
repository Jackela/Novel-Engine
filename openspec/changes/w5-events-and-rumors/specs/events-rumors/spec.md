# Specification: Rumor Propagation Logic

## Domain Rules

### Truth Value with Perturbation
```markdown
## ADDED Requirements

- **Truth Perturbation**: When creating a rumor from an event, apply ±10% random perturbation to base truth value.
  
  #### Scenario: Global Event Creates High-Truth Rumor
  Given an event with ImpactScope.GLOBAL
  When a rumor is created from this event
  Then the truth_value should be between 80 and 100 (inclusive)
  
  #### Scenario: Regional Event Creates Medium-Truth Rumor
  Given an event with ImpactScope.REGIONAL
  When a rumor is created from this event
  Then the truth_value should be between 60 and 80 (inclusive)
  
  #### Scenario: Local Event Creates Lower-Truth Rumor
  Given an event with ImpactScope.LOCAL
  When a rumor is created from this event
  Then the truth_value should be between 40 and 60 (inclusive)
```

### Propagation Mechanics
```markdown
## ADDED Requirements

- **Tick-Based Propagation**: Rumors spread to adjacent locations on each time tick.

  #### Scenario: Rumor Spreads to Adjacent Location
  Given a rumor exists at Location A
  And Location B is adjacent to Location A
  When a time tick occurs
  Then the rumor should spread to Location B
  And the truth_value should decrease by TRUTH_DECAY_PER_HOP (10%)
  
  #### Scenario: Dead Rumor Cleanup
  Given a rumor with truth_value of 5
  When it spreads and truth_value becomes 0
  Then the rumor should be marked as dead
  And removed from active rumors
```

### Manual Event Creation
```markdown
## ADDED Requirements

- **Manual Event Creation**: Authors can manually create historical events.

  #### Scenario: Author Creates Historical Event
  Given an authenticated user
  When they POST to /api/world/events with event details
  Then a HistoryEvent should be created
  And optionally generate a rumor based on the event
  
  #### Scenario: Event with Significance Validation
  Given an event creation request
  When significance is LEGENDARY but narrative_importance < 30
  Then the request should be rejected with validation error
```

## API Contracts

### GET /api/world/events
```json
{
  "events": [
    {
      "id": "evt_abc123",
      "name": "The Sundering",
      "description": "A cataclysmic war that split the continent.",
      "event_type": "war",
      "significance": "world_changing",
      "date_description": "Year 1042 of the Third Age",
      "structured_date": {
        "year": 1042,
        "month": 5,
        "day": 14,
        "era_name": "Third Age"
      },
      "location_ids": ["loc_north", "loc_south"],
      "faction_ids": ["fac_kingdom", "fac_empire"],
      "is_secret": false
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### POST /api/world/events
Request:
```json
{
  "name": "Fall of the Northern Wall",
  "description": "The ancient defense crumbled under siege.",
  "event_type": "disaster",
  "significance": "major",
  "date_description": "The Year of Broken Shields",
  "structured_date": {
    "year": 1043,
    "month": 3,
    "day": 1
  },
  "location_ids": ["loc_wall"],
  "faction_ids": ["fac_defenders", "fac_invaders"],
  "impact_scope": "regional",
  "generate_rumor": true
}
```

### GET /api/world/locations/{id}/rumors
```json
{
  "location_id": "loc_tavern",
  "rumors": [
    {
      "id": "rum_01",
      "content": "Word spreads of conflict between two great powers. The Northern War...",
      "truth_value": 85,
      "veracity_label": "Confirmed",
      "days_circulating": 5,
      "origin_type": "event",
      "source_event_id": "evt_abc123"
    }
  ]
}
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| EVENT_NOT_FOUND | Event ID does not exist | 404 |
| INVALID_DATE_FORMAT | structured_date fields invalid | 422 |
| MISSING_IMPACT_SCOPE | Required for rumor generation | 422 |
| LOCATION_NOT_FOUND | Location ID does not exist | 404 |
