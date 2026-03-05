# Campaigns Context

## Overview
The Campaigns Context manages narrative campaigns and story arcs within the Novel Engine platform. It provides the structural framework for organizing characters, locations, and narrative events into cohesive storytelling experiences.

This context handles campaign lifecycle (creation, progression, completion), party management, and session tracking for tabletop RPG-style experiences or interactive fiction.

## Domain

### Aggregates
- **Campaign**: Root aggregate representing a complete narrative campaign
  - Maintains campaign state, participants, and progression
  - Enforces party composition rules
  - Tracks session history and milestones

### Entities
- **Session**: Represents a single play session within a campaign
  - Tracks session duration, participants, and outcomes
  - Links to generated narrative content

### Value Objects
- **CampaignId**: Unique identifier for campaigns
- **CampaignStatus**: Enumeration (PLANNING, ACTIVE, PAUSED, COMPLETED, ARCHIVED)
- **PartyComposition**: Rules for valid party configurations

### Domain Events
- **CampaignCreated**: When a new campaign is initialized
- **CampaignStarted**: When campaign transitions to ACTIVE
- **SessionCompleted**: When a play session ends
- **CampaignCompleted**: When campaign reaches conclusion
- **PartyCompositionChanged**: When players join or leave

## Application

### Services
- **CampaignApplicationService**: Main service for campaign operations
  - `create_campaign(name, description, settings)` - Create new campaign
  - `start_campaign(campaign_id)` - Activate campaign
  - `add_participant(campaign_id, character_id)` - Add character to party
  - `record_session(campaign_id, session_data)` - Log completed session
  - `complete_campaign(campaign_id, outcome)` - Mark campaign complete

### Commands
- **CreateCampaign**: Initialize new campaign
  - Handler: `CreateCampaignHandler`
  - Side effects: CampaignCreated event raised
  
- **StartCampaign**: Begin active play
  - Handler: `StartCampaignHandler`
  - Side effects: CampaignStarted event raised

- **AddParticipant**: Add character to campaign
  - Handler: `AddParticipantHandler`
  - Side effects: PartyCompositionChanged event raised

### Queries
- **GetCampaignSummary**: Retrieve campaign overview
  - Handler: `GetCampaignSummaryHandler`
  
- **ListActiveCampaigns**: Get all currently active campaigns
  - Handler: `ListActiveCampaignsHandler`

## Infrastructure

### Repositories
- **CampaignRepository**: Campaign persistence
  - Implementation: PostgreSQL with JSONB for flexible metadata
  
- **SessionRepository**: Session history storage
  - Implementation: PostgreSQL with temporal indexing

### External Services
- None specific to this context

## API

### REST Endpoints
- `POST /api/campaigns` - Create new campaign
- `GET /api/campaigns/{id}` - Get campaign details
- `PUT /api/campaigns/{id}/start` - Start campaign
- `POST /api/campaigns/{id}/participants` - Add participant
- `GET /api/campaigns/{id}/sessions` - List campaign sessions

### WebSocket Events
- `campaign.started` - Real-time campaign activation
- `campaign.session_started` - New session notification

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/campaigns/unit/ -v

# Integration tests
pytest tests/contexts/campaigns/integration/ -v

# All context tests
pytest tests/contexts/campaigns/ -v
```

### Test Coverage
Current coverage: To be measured
Target coverage: 80%

## Architecture Decision Records
- ADR-001: Campaign as aggregate root for narrative boundaries
- ADR-002: Party composition validation rules

## Integration Points

### Inbound
- Events consumed:
  - `CharacterCreated` from Character Context (auto-add to campaign option)
  - `WorldStateChanged` from World Context (affects campaign setting)

### Outbound
- Events published:
  - `CampaignCreated` - For dashboard updates
  - `CampaignStarted` - For orchestration initialization
  - `SessionCompleted` - For narrative generation triggers

### Dependencies
- **Domain**: Character Context (for party members)
- **Application**: World Context (for setting data)
- **Infrastructure**: PostgreSQL, Event Bus

## Development Guide

### Adding New Features
1. Extend domain model with new entities/value objects
2. Add application service methods
3. Implement repository methods if persistence needed
4. Add API endpoints
5. Write tests

### Common Tasks
- **Adding a new campaign type**: Extend `CampaignType` enum and validation rules
- **Adding party constraints**: Update `PartyComposition` validation logic

## Maintainer
Team: @campaigns-team
Contact: campaigns@example.com
