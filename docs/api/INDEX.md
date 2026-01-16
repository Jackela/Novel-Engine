# API Documentation

**Last Updated**: 2024-11-04  
**Status**: Current

**Navigation**: [Home](../../README.md) > [Docs](../index.md) > API

---

## Overview

Novel Engine provides a comprehensive API layer offering unified access to all system capabilities with consistent authentication, validation, and response patterns.

---

## API Architecture

```
Client Applications
        ↓
   API Gateway
   ↙    ↓    ↘
Story  Character  Campaign
Engine  Service   Manager
   ↘    ↓    ↙
  Platform Services
```

---

## 📚 API Documentation

### [API Reference](./API_REFERENCE.md) ⭐
**Comprehensive API documentation for REST and Python interfaces**

- **REST API**: HTTP/JSON endpoints for web/mobile applications
  - System health and monitoring endpoints
  - Character management (CRUD operations)
  - Story simulation execution
  - Campaign management
  - Chronicle generation
  
- **Python Framework API**: Direct Python integration
  - System Orchestrator
  - Multi-layer memory system
  - Dynamic template engine
  - Character interaction processor
  - Equipment management system

- **Topics**: Endpoints, data models, error handling, integration examples
- **Audience**: Developers, Integration Teams
- **Last Updated**: 2024-11-04

---

## Core API Principles

1. **RESTful Design** - Standard HTTP methods and resource-based URLs
2. **Consistent Responses** - Uniform response formats across all endpoints
3. **Authentication** - Secure authentication (JWT planned)
4. **Versioning** - Single stable API surface under `/api/*` (no path-based versioning)
5. **Documentation** - Living documentation with examples

---

## Quick Start

### REST API Example

```javascript
// Fetch character
const response = await fetch('http://localhost:8000/characters/krieg');
const character = await response.json();

// Run simulation
const simulation = await fetch('http://localhost:8000/simulations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    character_names: ['krieg', 'ork_warboss'],
    turns: 5,
    narrative_style': 'action'
  })
});
```

### Python API Example

```python
from src.core.system_orchestrator import SystemOrchestrator

orchestrator = SystemOrchestrator("data/app.db")
await orchestrator.startup()

result = await orchestrator.create_agent_context("agent_001")
```

---

## 🚧 Planned Documentation

The following API documentation is planned for future releases:

### Authentication Guide (Planned)
- JWT implementation
- API key management
- OAuth integration
- Role-based access control

### SDK Documentation (Planned)
- Python SDK
- JavaScript/TypeScript SDK
- Client library examples

### Integration Examples (Planned)
- Frontend integration
- Mobile app integration
- Third-party service integration

### API Versioning Guide (Planned)
- Version migration strategies
- Deprecated endpoint handling
- Breaking change policies

---

## API Standards

### Request/Response Format

**Success Response**:
```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2024-11-04T...",
    "version": "1.0.0"
  }
}
```

**Error Response**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "details": { ... }
  }
}
```

### Status Codes
- **200** - Success
- **201** - Created
- **400** - Bad Request
- **401** - Unauthorized
- **404** - Not Found
- **500** - Internal Server Error

---

## Related Documentation

### Architecture
- [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)
- [Ports & Adapters](../architecture/ports-adapters.md)

### Development
- [Quick Start](../QUICK_START.md)
- [Developer Guide](../onboarding/developer-guide.md)
- [Data Schemas](./schemas.md)

### Deployment
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [Operations Runbook](../operations/OPERATIONS_RUNBOOK.md)

---

**Maintained by**: Novel Engine API Team  
**License**: MIT
