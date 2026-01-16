
# Novel Engine M1 - Project Documentation

**Version**: 2.0.0  
**Last Updated**: 2026-01-14  
**Status**: Golden Master  
**Maintainer**: Novel Engine Development Team

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Summary](#architecture-summary)
3. [System Components](#system-components)
4. [Domain Model](#domain-model)
5. [API Architecture](#api-architecture)
6. [Data Architecture](#data-architecture)
7. [Security Architecture](#security-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Development Workflow](#development-workflow)
10. [Quality Standards](#quality-standards)

---

## Project Overview

### Mission Statement
Novel Engine M1 transforms interactive storytelling through AI-driven narrative generation, character orchestration, and immersive campaign management. The system provides a comprehensive platform for creating, managing, and experiencing dynamic, personalized story campaigns.

### Core Objectives
- **Dynamic Storytelling**: AI-powered narrative generation with contextual coherence
- **Character Intelligence**: Sophisticated character agents with persistent memory and development
- **Campaign Management**: Comprehensive campaign orchestration and world state management
- **Scalable Architecture**: Modern microservices foundation ready for enterprise deployment
- **Developer Experience**: Clear APIs and comprehensive tooling for extensibility

### Key Stakeholders
- **End Users**: Story creators, campaign managers, and participants
- **Developers**: Internal development team and potential API consumers
- **Operations**: System administrators and deployment engineers
- **Business**: Product owners and strategic decision makers

---

## Architecture Summary

### Architectural Principles

#### 1. Functional Core, Imperative Shell
- **Predictability**: Core business logic is implemented as pure functions with no side effects.
- **Isolation**: State mutation and I/O (filesystem, network) are pushed to the "imperative shell" (e.g., API routers, persistence services).
- **Testability**: Pure core logic is easily verified via unit tests without complex mocking.

#### 2. Modular Monolith (M1 Phase)
- **Unified Runtime**: All services run within a single process/container for simplicity and performance.
- **Logical Boundaries**: Code is structured into strict domains (`src/contexts/`), simulating microservices boundaries without the network overhead.
- **Event Bus**: Internal communication uses an in-memory event bus (`src/core/event_bus.py`) rather than external message queues.

#### 3. Pragmatic Persistence (Filesystem-Backed)
- **Zero Database**: Persistence is handled via the filesystem (Markdown, YAML, JSON) for portability and simplicity.
- **Guest Workspaces**: Data is scoped to isolated filesystem workspaces, enabling "guest-first" usage.
- **Atomic Operations**: Ensure data integrity through atomic writes and schema versioning.

### Layered Architecture Model

```
┌─────────────────────────────────────────────────────┐
│                 Presentation Layer                   │
│           Web UI (React) | CLI Tools                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│               Application Services Layer             │
│          FastAPI Routers (src/api/routers)          │
│       Guest Session Manager | Workspace Store       │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│                Domain Contexts Layer                │
│  Characters | Narratives | Campaigns | Interactions │
│  Orchestration | Shared (Kernel)                    │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│               Infrastructure Layer                  │
│  Filesystem I/O | Event Bus | AI Service Adapter    │
└─────────────────────────────────────────────────────┘
```

---

## System Components

### Application Services (`src/api/`)

> **Note**: While the `apps/` directory exists for future microservice extraction, the current M1 implementation resides centrally in `src/api` and `src/agents`.

#### API Gateway (Logical)
**Purpose**: Central API routing and cross-cutting concerns.
**Implementation**: `src/api/app.py` acts as the gateway, aggregating all routers under the `/api` prefix.

**Responsibilities**:
- Request routing to appropriate domain routers.
- Global middleware (CORS, GZip, Error Handling).
- Session cookie management for Guest Mode.

#### Story Engine (`src/agents/`)
**Purpose**: Core narrative generation and orchestration.
**Implementation**: `DirectorAgent` and `ChroniclerAgent`.

**Responsibilities**:
- Dynamic story generation using AI models.
- Managing turn-based narrative flow.
- Transcribing simulation logs into readable formats.

#### Character Service (`src/contexts/character/`)
**Purpose**: Character lifecycle and logic.
**Implementation**: `src/api/routers/characters.py` and `CharacterFactory`.

**Responsibilities**:
- CRUD operations for character profiles (Markdown/YAML).
- Loading and instantiating `PersonaAgent` instances.

#### Campaign Manager (`apps/campaign-manager/`)
**Purpose**: Campaign orchestration, session management, and world state coordination

**Responsibilities**:
- Campaign lifecycle and configuration management
- Session orchestration and participant coordination
- World state management and persistence
- Campaign progression tracking and analytics
- Cross-session continuity and coherence

**Key Interfaces**:
- Campaign management and configuration APIs
- Session orchestration and real-time coordination
- World state query and update operations
- Campaign analytics and reporting endpoints
- Participant management and access control

#### Memory Service (`apps/memory-service/`)
**Purpose**: Centralized memory management with advanced retrieval capabilities

**Responsibilities**:
- Character and narrative memory storage and retrieval
- Memory search and similarity matching
- Cross-session memory persistence and optimization
- Memory analytics and relationship mapping
- Memory cleanup and archival management

**Key Interfaces**:
- Memory storage and retrieval operations
- Advanced search and similarity matching
- Memory relationship and analytics queries
- Memory optimization and cleanup endpoints
- Cross-service memory coordination interfaces

#### Monitoring (`apps/monitoring/`)
**Purpose**: System observability, health monitoring, and operational visibility

**Responsibilities**:
- System health monitoring and alerting
- Performance metrics collection and analysis
- Application observability and distributed tracing
- Operational dashboards and reporting
- Service dependency monitoring and mapping

**Key Interfaces**:
- Metrics collection and aggregation APIs
- Health check and service discovery endpoints
- Dashboard data and visualization services
- Alerting and notification management
- Trace collection and analysis interfaces

### Domain Contexts (`src/contexts/`)

#### Characters Domain (`src/contexts/character/`)
**Domain Scope**: Character-related business logic and behavior

**Core Concepts**:
- **Character**: Persistent entity with personality, memory, and development
- **Persona**: Behavioral template and character archetype
- **Agent**: Runtime instance of character behavior and decision-making
- **Relationship**: Inter-character connections and interaction history
- **Development**: Character growth and change over time

**Bounded Context Interfaces**:
- Character creation and lifecycle events
- Interaction requests and responses with other domains
- Memory storage and retrieval coordination
- Character development and progression tracking

#### Narratives Domain (`src/contexts/narratives/`)
**Domain Scope**: Story generation, plot development, and narrative coherence

**Core Concepts**:
- **Story**: Complete narrative with beginning, middle, and end
- **Plot**: Structured sequence of events and story progression
- **Event**: Individual story occurrence with context and consequences
- **Theme**: Narrative focus and thematic elements
- **Arc**: Character or story development trajectory

**Bounded Context Interfaces**:
- Story generation requests and narrative delivery
- Plot progression and event coordination
- Theme and quality validation interfaces
- Integration with character and campaign contexts

#### Campaigns Domain (`src/contexts/campaigns/`)
**Domain Scope**: Campaign management, sessions, and world state

**Core Concepts**:
- **Campaign**: Complete gaming experience with participants and world
- **Session**: Individual gameplay period with specific activities
- **World State**: Current condition of the game world and entities
- **Participant**: Users and characters involved in the campaign
- **Progression**: Campaign advancement and milestone tracking

**Bounded Context Interfaces**:
- Campaign lifecycle and session management
- World state synchronization and persistence
- Participant coordination and access management
- Integration with character and narrative contexts

#### Interactions Domain (`src/contexts/interactions/`)
**Domain Scope**: Character interactions, dialogue, and action processing

**Core Concepts**:
- **Interaction**: Communication or action between characters
- **Dialogue**: Conversational exchanges with context and intent
- **Action**: Character behaviors with consequences and effects
- **Outcome**: Results and effects of interactions
- **Context**: Situational information affecting interactions

**Bounded Context Interfaces**:
- Interaction processing and validation
- Dialogue generation and conversation management
- Action resolution and outcome calculation
- Context sharing with other domains

#### Orchestration Domain (`src/contexts/orchestration/`)
**Domain Scope**: Multi-agent coordination and system workflow management

**Core Concepts**:
- **Workflow**: Coordinated sequence of system operations
- **Coordination**: Multi-agent synchronization and communication
- **Resource**: System resources and their allocation
- **Policy**: Rules and constraints for system operations
- **Optimization**: Performance and efficiency improvements

**Bounded Context Interfaces**:
- Cross-domain workflow coordination
- Resource allocation and management
- Policy enforcement and compliance
- System optimization and performance monitoring

#### Shared Domain (`src/contexts/shared/`)
**Domain Scope**: Common domain concepts and cross-cutting utilities

**Core Concepts**:
- **Event**: Domain events for inter-context communication
- **Identity**: Common identification patterns across domains
- **Time**: Temporal concepts and scheduling
- **Location**: Spatial concepts and positioning
- **Communication**: Message passing and notification patterns

**Bounded Context Interfaces**:
- Common domain services and utilities
- Cross-context event handling and messaging
- Shared value objects and domain models
- Integration patterns and communication protocols

---

## Domain Model

### Core Domain Entities

#### Character Entity
```
Character (Aggregate Root)
├── Identity: CharacterId, Name, Type
├── Profile: Personality, Background, Attributes
├── Memory: Experiences, Relationships, Knowledge
├── Development: Growth, Skills, Achievements
└── Status: Current State, Health, Availability
```

#### Story Entity
```
Story (Aggregate Root)
├── Identity: StoryId, Title, Genre
├── Structure: Plot, Themes, Arcs
├── Content: Events, Scenes, Dialogue
├── Quality: Coherence, Engagement, Completeness
└── Context: Setting, Time, Participants
```

#### Campaign Entity
```
Campaign (Aggregate Root)
├── Identity: CampaignId, Name, Configuration
├── Participants: Characters, Users, Roles
├── World State: Environment, Conditions, History
├── Progress: Sessions, Milestones, Achievements
└── Analytics: Metrics, Reports, Insights
```

### Value Objects
- **PersonalityTraits**: Character personality dimensions
- **StoryThemes**: Narrative thematic elements
- **InteractionTypes**: Categories of character interactions
- **WorldLocation**: Spatial positioning and environment
- **TimeStamp**: Temporal references and scheduling

### Domain Services
- **CharacterDevelopmentService**: Character growth and progression
- **NarrativeCoherenceService**: Story quality and consistency
- **InteractionValidationService**: Interaction rules and constraints
- **MemoryRetrievalService**: Memory search and relationship mapping

---

## API Architecture

### API Design Principles

#### RESTful Design
- **Resource-Based URLs**: Clear, hierarchical resource naming
- **HTTP Methods**: Appropriate use of GET, POST, PUT, DELETE, PATCH
- **Status Codes**: Meaningful HTTP status codes for all responses
- **Content Negotiation**: Support for JSON, XML, and other formats

#### Contract-First Development
- **OpenAPI Specifications**: All APIs defined with OpenAPI 3.0
- **Code Generation**: Server stubs and client SDKs from specifications
- **Validation**: Automatic request/response validation
- **Documentation**: Living API documentation from contracts

#### API Versioning Strategy
- **API Base Path**: Single stable prefix under `/api/*`.
- **No Path Versioning**: Explicitly avoid `/api/v1` or `/api/v2` in the URL path for first-party clients.
- **Backward Compatibility**: Handle breaking changes via headers or evolutionary schema changes (e.g., optional fields).
- **Canonical Decision**: See `openspec/changes/archive/2025-12-22-standardize-api-surface` for details.

### API Gateway Architecture

```
External Clients
        ↓
   Load Balancer
        ↓
    API Gateway
    ↙    ↓    ↘
Auth   Rate   Request
Svc   Limit   Router
        ↓
Internal Services
```

#### Gateway Responsibilities
- **Authentication & Authorization**: Centralized security enforcement
- **Rate Limiting**: Request throttling and usage tracking
- **Request Routing**: Intelligent routing to appropriate services
- **Response Aggregation**: Combining responses from multiple services
- **Protocol Translation**: REST to GraphQL, HTTP to WebSocket

### Service API Specifications

#### Story Engine API Endpoints
```
POST /api/stories              # Create new story
GET  /api/stories/{id}         # Retrieve story
PUT  /api/stories/{id}         # Update story
DELETE /api/stories/{id}       # Delete story
POST /api/stories/{id}/events  # Add story event
GET  /api/stories/{id}/analysis # Story analysis
```

#### Character Service API Endpoints
```
POST /api/characters           # Create character
GET  /api/characters/{id}      # Retrieve character
PUT  /api/characters/{id}      # Update character
DELETE /api/characters/{id}    # Delete character
POST /api/characters/{id}/interactions # Process interaction
GET  /api/characters/{id}/memory # Character memory
```

#### Campaign Manager API Endpoints
```
POST /api/campaigns            # Create campaign
GET  /api/campaigns/{id}       # Retrieve campaign
PUT  /api/campaigns/{id}       # Update campaign
DELETE /api/campaigns/{id}     # Delete campaign
POST /api/campaigns/{id}/sessions # Start session
GET  /api/campaigns/{id}/state # World state
```

---

## Data Architecture

### Data Management Principles

#### Filesystem as Source of Truth
- **Human-Readable**: All critical data (Characters, Campaigns) is stored as Markdown (with YAML frontmatter) or JSON.
- **Git-Friendly**: The entire world state can be version-controlled using standard Git workflows.
- **Portability**: Workspaces are self-contained folders that can be easily zipped, shared, or backed up.

#### Logical Separation
- **Data Ownership**: Each domain context (`src/contexts/`) manages its own file schemas and directory structures.
- **No Shared Mutability**: Domains interact via the Event Bus or public Service Interfaces, never by directly modifying another domain's files.

### Data Models (Filesystem)

#### Character Service Data Model
```yaml
# characters/{id}/profile.md
---
name: "Aria"
faction: "Alliance"
role: "Pilot"
stats:
  piloting: 8
  diplomacy: 4
---

# Narrative content continues here...
Aria is a skilled pilot...
```

#### Story Engine Data Model
```json
// campaigns/{id}/session_log.json
{
  "id": "session_123",
  "turns": [
    {
      "id": "turn_1",
      "action": "...",
      "outcome": "..."
    }
  ]
}
```

### Data Synchronization Patterns

#### Event-Driven Updates
- **In-Memory Bus**: `src/core/event_bus.py` handles synchronous domain events.
- **SSE Streaming**: Real-time updates are pushed to the frontend via `/api/events/stream`.

---

## Security Architecture

### Security Principles

#### Zero Trust Architecture
- **Verify Everything**: No implicit trust based on network location
- **Least Privilege**: Minimum necessary permissions for all operations
- **Continuous Verification**: Ongoing validation of access and behavior
- **Assume Breach**: Design for compromise detection and containment

#### Defense in Depth
- **Multiple Layers**: Security controls at every architectural level
- **Redundant Controls**: Overlapping security mechanisms
- **Fail Secure**: Security failures result in denial rather than access
- **Monitoring Integration**: Security events integrated with monitoring

### Authentication and Authorization

#### Authentication Strategy
- **OAuth2/OpenID Connect**: Industry standard authentication
- **JWT Tokens**: Stateless token-based authentication
- **Multi-Factor Authentication**: Required for sensitive operations
- **API Keys**: Service-to-service authentication

#### Authorization Model
```
Subject → Role → Permission → Resource

Users/Services → Admin/User/Service → Read/Write/Delete → Characters/Stories/Campaigns
```

#### Permission Matrix
```
Resource      | Admin | User  | Service | Anonymous
------------- | ----- | ----- | ------- | ---------
Characters    | CRUD  | CR    | CRUD    | R (public)
Stories       | CRUD  | CRUD  | CRUD    | R (public)
Campaigns     | CRUD  | CRUD  | CR      | None
System Metrics| CRUD  | None  | R       | None
```

### Data Protection

#### Encryption Standards
- **Data at Rest**: AES-256 encryption for all persistent data
- **Data in Transit**: TLS 1.3 for all network communications
- **Key Management**: HashiCorp Vault for key rotation and management
- **PII Handling**: Special handling for personally identifiable information

#### Privacy Compliance
- **GDPR Compliance**: Data protection regulation compliance
- **Data Minimization**: Collect and store only necessary data
- **Right to be Forgotten**: Data deletion capabilities
- **Privacy by Design**: Privacy considerations in all development

---

## Deployment Architecture

### Deployment Principles

#### Infrastructure as Code
- **Version Controlled**: All infrastructure definitions in source control
- **Automated Deployment**: No manual deployment steps
- **Environment Consistency**: Identical deployment process across environments
- **Rollback Capability**: Quick and safe rollback procedures

#### Container-First Deployment
- **Docker Containers**: All services containerized
- **Kubernetes Orchestration**: Container orchestration and management
- **Helm Charts**: Kubernetes application packaging
- **GitOps**: Git-based deployment automation

### Environment Architecture

#### Development Environment
- **Local Development**: Docker Compose for local development
- **Shared Resources**: Shared databases and services for integration testing
- **Hot Reloading**: Fast feedback during development
- **Debug Capabilities**: Debugging tools and instrumentation

#### Staging Environment
- **Production Mirroring**: Identical to production configuration
- **Integration Testing**: End-to-end testing environment
- **Performance Testing**: Load and stress testing capabilities
- **Security Testing**: Vulnerability scanning and penetration testing

#### Production Environment
- **High Availability**: Multiple availability zones and redundancy
- **Auto Scaling**: Horizontal scaling based on demand
- **Monitoring Integration**: Comprehensive monitoring and alerting
- **Disaster Recovery**: Backup and recovery procedures

### Deployment Pipeline

```
Code Commit → Build → Test → Security Scan → Deploy to Staging → 
Integration Tests → Deploy to Production → Health Checks → Success
```

#### Pipeline Stages
1. **Source Control**: Git-based source control with branch protection
2. **Continuous Integration**: Automated build and unit testing
3. **Security Scanning**: Static analysis and vulnerability scanning
4. **Staging Deployment**: Automated deployment to staging environment
5. **Integration Testing**: End-to-end and performance testing
6. **Production Deployment**: Blue-green deployment with health checks
7. **Monitoring**: Post-deployment monitoring and alerting

---

## Development Workflow

### Development Methodology

#### Agile Development
- **Sprint Planning**: 2-week sprints with clear deliverables
- **Daily Standups**: Progress tracking and impediment resolution
- **Sprint Reviews**: Stakeholder feedback and demonstration
- **Retrospectives**: Continuous improvement and team learning

#### Feature Development Process
1. **Feature Planning**: Requirements analysis and technical design
2. **API Design**: Contract-first API specification
3. **Implementation**: Test-driven development with peer review
4. **Integration**: Service integration and end-to-end testing
5. **Deployment**: Automated deployment with monitoring
6. **Validation**: User acceptance testing and feedback

### Code Quality Standards

#### Code Review Process
- **Peer Reviews**: All code changes reviewed by team members
- **Automated Checks**: Linting, testing, and security scanning
- **Approval Requirements**: Minimum 2 approvals for production changes
- **Documentation Updates**: Documentation updated with code changes

#### Testing Strategy
```
Unit Tests (70%) → Integration Tests (20%) → E2E Tests (10%)
```

- **Unit Tests**: Individual component testing with mocking
- **Integration Tests**: Service integration and API contract testing
- **End-to-End Tests**: User workflow and system behavior testing
- **Performance Tests**: Load testing and performance regression detection

#### Quality Metrics
- **Code Coverage**: Minimum 80% code coverage for all services
- **Test Success Rate**: 99%+ test success rate in CI/CD
- **Performance Benchmarks**: Response time and throughput targets
- **Security Scanning**: Zero high-severity vulnerabilities

---

## Quality Standards

### Non-Functional Requirements

#### Performance Requirements
- **API Response Time**: 95th percentile < 200ms
- **Story Generation**: < 5 seconds for standard stories
- **Character Interaction**: < 1 second for standard interactions
- **System Throughput**: > 1000 requests per second
- **Database Queries**: < 100ms for 95% of queries

#### Scalability Requirements
- **Horizontal Scaling**: Support for 10x traffic increase
- **Data Growth**: Handle 100x data growth over 2 years
- **Concurrent Users**: Support for 10,000+ concurrent users
- **Geographic Distribution**: Multi-region deployment capability

#### Availability Requirements
- **System Uptime**: 99.9% availability (8.7 hours downtime/year)
- **Planned Maintenance**: < 4 hours per month
- **Recovery Time**: < 15 minutes for system recovery
- **Data Backup**: < 1 hour Recovery Point Objective (RPO)

#### Security Requirements
- **Authentication**: Multi-factor authentication for admin access
- **Authorization**: Role-based access control for all resources
- **Data Protection**: Encryption at rest and in transit
- **Audit Logging**: Complete audit trail for all system operations
- **Vulnerability Management**: Monthly security scans and updates

### Monitoring and Observability

#### Monitoring Strategy
- **Application Metrics**: Response times, error rates, throughput
- **Infrastructure Metrics**: CPU, memory, disk, network utilization
- **Business Metrics**: User engagement, story quality, system usage
- **Custom Metrics**: Domain-specific metrics and KPIs

#### Alerting Framework
- **Severity Levels**: Critical, Warning, Info classification
- **Escalation Procedures**: Automated escalation based on severity
- **Notification Channels**: Email, SMS, Slack integration
- **On-Call Procedures**: 24/7 on-call rotation for critical systems

#### Logging Standards
- **Structured Logging**: JSON format with consistent schema
- **Log Levels**: ERROR, WARN, INFO, DEBUG classification
- **Centralized Logging**: ELK stack for log aggregation and search
- **Retention Policy**: 90-day retention for operational logs

---

## Conclusion

This project documentation provides the foundational architecture and design principles for Novel Engine M1. The documentation will evolve as the system develops, maintaining alignment between architecture, implementation, and operational practices.

### Next Steps
1. **API Contract Development**: Complete OpenAPI specifications for all services
2. **Domain Event Catalog**: Comprehensive domain event documentation
3. **Implementation Planning**: Detailed implementation roadmap and timeline
4. **Team Onboarding**: Developer onboarding and training materials

### Maintenance
- **Quarterly Reviews**: Architecture review and documentation updates
- **Version Control**: All documentation changes tracked and reviewed
- **Stakeholder Feedback**: Regular feedback collection and incorporation
- **Continuous Improvement**: Documentation quality and completeness monitoring

---

**Document Version**: 1.0.0  
**Last Review**: 2025-08-26  
**Next Review**: 2025-11-26  
**Reviewers**: Architecture Team, Development Team, Operations Team



