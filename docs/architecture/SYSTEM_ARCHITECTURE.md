# Novel Engine System Architecture

**Version**: 2.0.0  
**Last Updated**: 2024-11-04  
**Status**: Current  
**Audience**: Technical Leads, Developers, Architects

**Navigation**: [Home](../../README.md) > [Docs](../index.md) > [Architecture](INDEX.md) > System Architecture

---

## Overview

Novel Engine is a production-ready AI-powered multi-agent narrative simulation system combining modern web technologies with advanced AI integration.

### Architecture Principles

1. **AI-First Design** - Real LLM integration with intelligent fallback systems
2. **Configuration-Driven** - Centralized configuration management with runtime flexibility  
3. **Event-Driven** - Actions trigger cascading updates across all components
4. **Production-Ready** - Thread-safe operations, comprehensive error handling
5. **Performance-Optimized** - Advanced caching, connection pooling, response compression
6. **Dual Reality** - Objective world state vs. subjective character perspectives
7. **Narrative-First Output** - Technical simulation generates compelling human-readable stories

---

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   AI Services   │
│   React/TS      │◄──►│   FastAPI       │◄──►│   Gemini API    │
│   Shadcn UI     │    │   Python 3.11   │    │   GPT Models    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       
         │                       ▼                       
         │              ┌─────────────────┐              
         │              │   Data Layer    │              
         └──────────────►│   File System   │              
                        │   JSON/YAML     │              
                        └─────────────────┘              
```

### System Tiers

**Frontend Tier**:
- **Framework**: React 18 with TypeScript
- **UI Library**: Shadcn UI + Tailwind CSS
- **State Management**: React Query + local state
- **Routing**: React Router v6
- **Build Tool**: Vite

**Backend Tier**:
- **API Framework**: FastAPI with async/await
- **Language**: Python 3.11 with type hints
- **AI Integration**: Gemini API + OpenAI GPT-4
- **Data Validation**: Pydantic schemas
- **Architecture**: Multi-agent orchestration

**Data Tier**:
- **Storage**: File-based (JSON/YAML)
- **Caching**: In-memory with TTL
- **State**: Pydantic models with validation
- **Backup**: Automated file versioning

**Infrastructure**:
- **Containerization**: Docker with multi-stage builds
- **Proxy**: Nginx with SSL termination
- **Monitoring**: Health checks and structured logging
- **Deployment**: Cloud-ready with CI/CD

---

## Multi-Agent System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Novel Engine Multi-Agent Simulator                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐   │
│  │   DirectorAgent │◄──►│   ConfigLoader   │◄──►│  PersonaAgent │   │
│  │  (Game Master)  │    │  (Configuration) │    │ (AI Character)│   │
│  └─────────────────┘    └──────────────────┘    └───────────────┘   │
│           │                       │                      │          │
│           │                       │                      ▼          │
│           ▼                       ▼              ┌──────────────┐    │
│  ┌─────────────────┐    ┌──────────────────┐    │  Gemini API  │    │
│  │  CampaignLog.md │    │   config.yaml    │    │ Integration  │    │
│  │   (Events Log)  │    │  (Settings DB)   │    │(Real AI/LLM) │    │
│  └─────────────────┘    └──────────────────┘    └──────────────┘    │
│           │                                              │          │
│           ▼                                              │          │
│  ┌─────────────────┐                            ┌───────▼─────────┐ │
│  │ ChroniclerAgent │                            │ Character Sheet │ │
│  │   (Narrative    │                            │   (Agent Soul)  │ │
│  │  Transcription) │                            │   Markdown File │ │
│  └─────────────────┘                            └─────────────────┘ │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │ Narrative.md    │                                                │
│  │ (Story Output)  │                                                │
│  └─────────────────┘                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Roles

**DirectorAgent (Orchestrator)**:
- **Role**: Story planning and coordination
- **Responsibilities**:
  - Narrative structure planning
  - Turn sequence management
  - Agent lifecycle management
  - Quality control and validation
  - Performance monitoring
  - Campaign persistence

**PersonaAgent (Character)**:
- **Role**: Character-specific behavior and decisions
- **Responsibilities**:
  - Character personality maintenance
  - Dialogue and action generation
  - Consistency with character traits
  - Relationship management
  - Memory and context tracking

**ChroniclerAgent (Narrator)**:
- **Role**: Narrative generation and storytelling
- **Responsibilities**:
  - Convert game state to prose
  - Maintain narrative coherence
  - Quality scoring and metrics
  - Style consistency

**EvaluationAgent (QA)**:
- **Role**: Story quality assessment
- **Responsibilities**:
  - Narrative coherence checking
  - Character consistency validation
  - Quality scoring and metrics
  - Improvement suggestions

---

## Core Components

### 1. DirectorAgent (Game Master)

**Implementation**: `director_agent.py`

**Key Methods**:
```python
class DirectorAgent:
    def __init__(self, world_state_file_path=None, campaign_log_path=None)
    def register_agent(self, agent: PersonaAgent) -> bool
    def run_turn() -> Dict[str, Any]
    def log_event(self, event_description: str) -> None
    def get_simulation_status() -> Dict[str, Any]
    def save_world_state(self, file_path=None) -> bool
    def close_campaign_log() -> None
```

**Turn Execution Process**:
1. Initialize turn with logging and timing
2. Iterate through all registered agents
3. Prepare agent-specific world state updates
4. Collect agent decisions via `decision_loop()`
5. Process actions and update world state
6. Log all events and outcomes
7. Return detailed turn summary with metrics

**Production Features**:
- Configuration integration via ConfigLoader
- Error resilience (continues when agents fail)
- Structured event logging with timestamps
- Memory management with configurable limits
- Thread-safe for concurrent execution
- Automatic campaign log creation

---

### 2. Configuration System

**Implementation**: `src/core/config/config_loader.py`, `config.yaml`

**Configuration Hierarchy**:
```yaml
system:
  mode: "production" | "development" | "testing"
  log_level: "INFO"
  
ai_services:
  provider: "gemini"
  model: "gemini-pro"
  temperature: 0.7
  max_tokens: 2048
  
performance:
  cache_ttl: 3600
  max_concurrent_agents: 10
  memory_limit_mb: 512
  
paths:
  characters: "./characters"
  campaigns: "./campaigns"
  templates: "./templates"
```

**Features**:
- Environment variable overrides
- Runtime configuration updates
- Thread-safe global access
- Validation on load
- Default fallbacks

---

### 3. Memory & Context System

**Layered Memory Architecture**:

```yaml
Working Memory:
  Capacity: 7±2 items (cognitive science)
  Purpose: Current focus and active context
  Lifetime: Single turn
  
Episodic Memory:
  Capacity: 1000 items per agent
  Purpose: Event-based memories with temporal context
  Lifetime: Campaign duration
  
Semantic Memory:
  Capacity: 5000 items per agent
  Purpose: Knowledge and factual information
  Lifetime: Persistent
  
Emotional Memory:
  Capacity: 500 items per agent
  Purpose: Emotionally-charged memories
  Lifetime: Weighted by intensity
```

**Memory Consolidation**:
- Automatic cleanup based on relevance
- LRU caching for frequent access
- Similarity-based retrieval
- Cross-agent memory sharing

---

### 4. API Layer

**FastAPI Server**: `api_server.py`, `production_api_server.py`

**Key Endpoints**:
- `GET /health` - System health check
- `GET /meta/system-status` - Detailed metrics
- `GET /characters` - List all characters
- `GET /characters/{name}` - Character details
- `POST /characters` - Create new character
- `POST /simulations` - Run story simulation
- `GET /simulations/{id}` - Simulation status
- `POST /chronicle` - Generate narrative

**Features**:
- Async/await throughout
- Pydantic validation
- Rate limiting
- Error handling
- Performance monitoring
- CORS configuration

---

## Data Flow

### Story Generation Flow

```
1. User Request → API Gateway
   ├── Validate request parameters
   ├── Load character definitions
   └── Initialize DirectorAgent

2. DirectorAgent → Simulation Setup
   ├── Register PersonaAgents
   ├── Load world state
   └── Initialize campaign log

3. Turn-Based Execution Loop:
   ├── DirectorAgent → Prepare context
   ├── PersonaAgent[1] → Generate decision
   ├── PersonaAgent[2] → Generate decision
   ├── DirectorAgent → Process actions
   ├── DirectorAgent → Update world state
   └── DirectorAgent → Log events

4. Narrative Generation:
   ├── ChroniclerAgent → Process event log
   ├── ChroniclerAgent → Generate prose
   └── ChroniclerAgent → Quality check

5. Response Assembly:
   ├── Compile story fragments
   ├── Add metadata and metrics
   └── Return to client
```

### Character Decision Flow

```
PersonaAgent.decision_loop():
1. Receive world state from DirectorAgent
2. Query episodic memory for relevant history
3. Query semantic memory for knowledge
4. Generate decision prompt
5. Call AI service (Gemini/GPT)
6. Parse AI response
7. Validate action legality
8. Return decision to DirectorAgent
```

---

## Performance Architecture

### Caching Strategy

**Multi-Layer Cache**:
```yaml
L1 - In-Memory Cache:
  Scope: Hot data (characters, config)
  TTL: 5 minutes
  Size: 100 MB
  
L2 - Semantic Cache:
  Scope: AI responses by similarity
  TTL: 1 hour
  Size: 500 MB
  
L3 - File System Cache:
  Scope: Generated narratives
  TTL: 24 hours
  Size: Unlimited
```

**Cache Invalidation**:
- Character updates → Clear L1 character cache
- Config changes → Clear all caches
- World state changes → Clear semantic cache
- Manual flush → API endpoint

### Connection Pooling

```python
AI Service Pool:
  Max Connections: 10
  Timeout: 30 seconds
  Retry: 3 attempts with exponential backoff
  
Database Pool:
  Max Connections: 20
  Idle Timeout: 300 seconds
  Connection Validation: On checkout
```

### Performance Targets

```yaml
Response Times:
  Health Check: < 50ms
  Character Query: < 200ms
  Story Generation: 30-180 seconds
  API Endpoints: < 500ms
  
Throughput:
  Concurrent Users: 100
  Requests/Second: 1000
  Story Generations/Hour: 50
  
Resources:
  Memory Usage: < 512 MB
  CPU Usage: < 50% average
  Disk I/O: < 100 MB/s
```

---

## Security Architecture

### Input Validation

```python
# All user input validated with Pydantic
class CharacterCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    description: str = Field(min_length=10, max_length=2000)
    
# File upload validation
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.txt', '.md', '.json', '.yaml'}
```

### Data Protection

- No personal data stored without consent
- Character data anonymized in logs
- API keys stored in environment variables
- Temporary files cleaned up after processing
- SQL injection prevention (parameterized queries)
- XSS protection (output encoding)

### Rate Limiting

```yaml
Default: 100 requests/minute/IP
Burst: 200 requests/5 minutes
Story Generation: 5 concurrent/user
```

---

## Deployment Architecture

### Container Strategy

```dockerfile
# Multi-stage build
Stage 1: Build frontend
  - Node.js 18
  - npm build
  - Optimize assets

Stage 2: Python backend
  - Python 3.11 slim
  - Install dependencies
  - Copy application code

Stage 3: Final image
  - Nginx + Python
  - Health checks
  - Monitoring agents
```

### Infrastructure

```yaml
Production Stack:
  Load Balancer: Nginx/HAProxy
  Application: Gunicorn + FastAPI
  Cache: Redis (optional)
  Storage: Persistent volumes
  Monitoring: Prometheus + Grafana
  Logging: ELK stack
```

---

## Scalability Patterns

### Horizontal Scaling

```yaml
Stateless Design:
  - No server-side sessions
  - Configuration in env variables
  - File system can be shared or S3
  
Load Distribution:
  - Round-robin across instances
  - Health-based routing
  - Sticky sessions not required
```

### Vertical Scaling

```yaml
Resource Limits:
  Memory: 512 MB - 4 GB
  CPU: 1 core - 8 cores
  Storage: 10 GB - 100 GB
  
Scaling Triggers:
  CPU > 70% for 5 minutes
  Memory > 80% for 5 minutes
  Request queue > 100
```

---

## Monitoring & Observability

### Health Checks

```python
# Liveness probe
GET /health
Returns: 200 if application running

# Readiness probe  
GET /meta/system-status
Returns: 200 if ready to serve traffic
```

### Metrics

```yaml
Application Metrics:
  - Request rate and latency
  - Error rate by endpoint
  - AI service response times
  - Cache hit rates
  - Memory usage
  
Business Metrics:
  - Story generations
  - Character creations
  - Active users
  - Quality scores
```

### Logging

```python
Structured Logging:
  Format: JSON
  Fields: timestamp, level, message, context
  Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
  Rotation: Daily, 7 day retention
```

---

## Technology Stack Summary

```yaml
Frontend:
  - React 18 + TypeScript
  - Shadcn UI + Tailwind CSS
  - Vite
  - React Query

Backend:
  - Python 3.11
  - FastAPI
  - Pydantic
  - aiosqlite

AI Services:
  - Google Gemini API
  - OpenAI GPT-4 (fallback)

Infrastructure:
  - Docker
  - Nginx
  - GitHub Actions (CI/CD)

Development:
  - pytest (testing)
  - black (formatting)
  - mypy (type checking)
  - Playwright (E2E testing)
```

---

## Related Documentation

- [API Reference](../api/API_REFERENCE.md)
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [Developer Guide](../onboarding/developer-guide.md)
- [Bounded Contexts](./bounded-contexts.md)
- [Context Mapping](./context-mapping.md)
- [Ports & Adapters](./ports-adapters.md)
- [Resiliency Patterns](./resiliency.md)

---

**Last Updated**: 2024-11-04  
**Maintained by**: Novel Engine Architecture Team  
**License**: MIT
