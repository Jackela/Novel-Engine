# Interactions Context

## Overview
The Interactions Context manages social and strategic interactions between entities within the Novel Engine platform. It handles negotiations, dialogues, proposals, and conflict resolution through a structured session-based framework.

This context provides the domain model for multi-party interactions including negotiation phases, proposal submission, response tracking, and outcome determination. It supports use cases from simple dialogue to complex diplomatic negotiations.

## Domain

### Aggregates
- **NegotiationSession**: Root aggregate for managing interactions
  - Complete lifecycle: creation → party management → proposals → resolution
  - Enforces: minimum party requirements, role constraints, phase transitions
  - Supports: unanimous or majority agreement rules
  - Timeout handling with automatic termination

### Entities
- **None**: NegotiationSession aggregate manages all data.

### Value Objects
- **InteractionId**: Unique session identifier with UUID generation
- **NegotiationParty**: Represents a participant in negotiations
  - **PartyRole**: INITIATOR, RESPONDER, MEDIATOR, ADVISOR, OBSERVER
  - Authority levels: decision maker, binding authority
  - Compatibility checking between parties
  
- **NegotiationStatus**: Session state tracking
  - **NegotiationPhase**: PREPARATION, OPENING, BARGAINING, CLOSING, IMPLEMENTATION
  - **NegotiationOutcome**: PENDING, AGREEMENT_REACHED, PARTIAL_AGREEMENT, DEADLOCK, WITHDRAWAL, TIMEOUT
  - **TerminationReason**: MUTUAL_AGREEMENT, DEADLOCK, WITHDRAWAL, TIMEOUT_EXCEEDED, EXTERNAL
  
- **ProposalTerms**: Structured proposal with terms and conditions
  - Expiration tracking
  - Term importance scoring
  
- **ProposalResponse**: Party response to a proposal
  - Per-term responses: ACCEPT, REJECT, COUNTER, REQUEST_CLARIFICATION
  - Overall response: COMPLETE_ACCEPTANCE, PARTIAL_ACCEPTANCE, REJECTION, COUNTER_PROPOSAL
  - Acceptance percentage calculation

### Domain Events
- **NegotiationSessionCreated**: Session initialized
  - Contains: session_id, name, type, creator, configuration
  
- **PartyJoinedNegotiation**: New participant added
  - Contains: party_id, role, timestamp
  
- **PartyLeftNegotiation**: Participant removed
  - Contains: party_id, reason, timestamp
  
- **ProposalSubmitted**: New proposal offered
  - Contains: proposal_id, submitter, terms count, timestamp
  
- **ProposalResponseReceived**: Response recorded
  - Contains: proposal_id, responder, response type, acceptance percentage
  
- **NegotiationPhaseAdvanced**: Phase transition
  - Contains: from_phase, to_phase, forced flag
  
- **NegotiationCompleted**: Successful conclusion
  - Contains: outcome, final proposals, duration, participating parties
  
- **NegotiationTerminated**: Unsuccessful ending
  - Contains: outcome, reason, terminator, duration
  
- **SessionTimeoutWarning**: Approaching timeout
  - Contains: time remaining, expiration time

## Application

### Services
- **InteractionApplicationService**: Main interaction operations
  - `create_session(name, type, created_by, config)` - Initialize negotiation
  - `add_party(session_id, party)` - Add participant
  - `submit_proposal(session_id, proposal, submitted_by)` - Offer terms
  - `submit_response(session_id, response)` - Respond to proposal
  - `advance_phase(session_id, target_phase)` - Manual phase transition
  - `terminate_negotiation(session_id, outcome, reason)` - End session
  - `get_session_summary(session_id)` - Get comprehensive status

- **NegotiationService**: Domain logic for negotiation evaluation
  - Agreement calculation: unanimous vs. majority rules
  - Proposal scoring and ranking
  - Optimal outcome suggestion

### Commands
- **CreateNegotiationSession**: Initialize interaction
  - Handler: `CreateNegotiationSessionHandler`
  - Side effects: NegotiationSessionCreated event
  
- **AddPartyToNegotiation**: Add participant
  - Handler: `AddPartyHandler`
  - Validations: Capacity limits, compatibility checks
  
- **SubmitProposal**: Offer terms
  - Handler: `SubmitProposalHandler`
  - Side effects: Auto-phase advancement

### Queries
- **GetNegotiationStatus**: Current session state
  - Handler: `GetNegotiationStatusHandler`
  
- **ListActiveProposals**: Get current proposals
  - Handler: `ListActiveProposalsHandler`
  
- **GetPartyResponses**: Get responses for analysis
  - Handler: `GetPartyResponsesHandler`

## Infrastructure

### Repositories
- **NegotiationSessionRepository**: Session persistence
  - Implementation: `SQLAlchemyNegotiationSessionRepository`
  - Optimistic locking for concurrent modifications
  
- **ProposalRepository**: Proposal history storage
  - Immutable proposal records for audit trail

### External Services
- None directly; uses AI Context for sentiment analysis if needed

## API

### REST Endpoints
- `POST /api/interactions/negotiations` - Create session
- `GET /api/interactions/negotiations/{id}` - Get session status
- `POST /api/interactions/negotiations/{id}/parties` - Add party
- `POST /api/interactions/negotiations/{id}/proposals` - Submit proposal
- `POST /api/interactions/negotiations/{id}/responses` - Submit response
- `PUT /api/interactions/negotiations/{id}/phase` - Advance phase
- `POST /api/interactions/negotiations/{id}/terminate` - End session

### WebSocket Events
- `negotiation.phase_changed` - Real-time phase updates
- `negotiation.proposal_received` - New proposal notification

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/interactions/unit/ -v

# Integration tests
pytest tests/contexts/interactions/integration/ -v

# All context tests
pytest tests/contexts/interactions/ -v
```

### Test Coverage
Current coverage: 70%
Target coverage: 80%

## Architecture Decision Records
- ADR-001: NegotiationSession as aggregate for interaction boundaries
- ADR-002: Phase-based negotiation model
- ADR-003: Flexible agreement rules (unanimous vs. majority)

## Integration Points

### Inbound
- Events consumed:
  - `CharacterCreated` from Character Context (auto-add as party)
  - `WorldStateChanged` from World Context (affects negotiation context)

### Outbound
- Events published:
  - `NegotiationCompleted` - For narrative generation
  - `AgreementReached` - For contract/world state updates

### Dependencies
- **Domain**: None (pure domain)
- **Application**: Character Context (party identities)
- **Infrastructure**: PostgreSQL

## Development Guide

### Adding New Features
1. Extend domain model (phases, response types, etc.)
2. Add application service methods
3. Update repository if needed
4. Add API endpoints
5. Write tests

### Common Tasks
- **Adding negotiation types**: Extend session type enum and validation
- **Adding party roles**: Extend PartyRole enum and authority rules
- **Custom outcome logic**: Override `_has_sufficient_agreement()`

## Maintainer
Team: @interactions-team
Contact: interactions@example.com
